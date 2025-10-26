import asyncio
import functools
from enum import IntEnum
from pathlib import Path
from types import MappingProxyType
from typing import Final

from loguru import logger
from pydantic import BaseModel, Field


class Buttons(IntEnum):
    A = 0
    B = 1
    X = 2
    Y = 3
    L = 4
    R = 5
    ZL = 6
    ZR = 7
    DPAD_UP = 8
    DPAD_DOWN = 9
    DPAD_LEFT = 10
    DPAD_RIGHT = 11
    LS = 12
    RS = 13
    PLUS = 14
    MINUS = 15
    CAPTURE = 16
    HOME = 17


class StickPosition(BaseModel):
    x: float = 0.0
    y: float = 0.0


class ControllerState(BaseModel):
    buttons: int = 0  # Bitmask for buttons
    ls: StickPosition = Field(default_factory=StickPosition)
    rs: StickPosition = Field(default_factory=StickPosition)

    def set_button(self, button: Buttons, pressed: bool):
        if pressed:
            self.buttons |= 1 << button.value
        else:
            self.buttons &= ~(1 << button.value)

    def is_pressed(self, button: Buttons) -> bool:
        return bool(self.buttons & (1 << button.value))


@functools.cache
def load_spi_rom_data() -> MappingProxyType[int, bytes]:
    directory = Path(__file__).parent / "spi_rom_data"

    data = {}
    for bin_file in directory.glob("*.bin"):
        key = int(bin_file.stem, 16)
        data[key] = bin_file.read_bytes()
    return MappingProxyType(data)


class Controller:
    def __init__(self):
        self.fp = None
        self.spi_rom_data = load_spi_rom_data()
        self.state = ControllerState()

        self.tasks = []
        self.stop_comms: Final = asyncio.Event()
        self.stop_counter: Final = asyncio.Event()
        self.stop_input: Final = asyncio.Event()
        self.count = 0

    async def connect(self, path: str):
        if self.fp is not None:
            raise Exception("Already connected")

        self.fp = open(path, "r+b", buffering=0)

        self.stop_comms.clear()
        self.stop_counter.clear()
        self.stop_input.clear()

        await self.start_counter()

        # Reset magic packet
        self.write(0x81, 0x03, bytes([]))
        self.write(0x81, 0x01, bytes([0x00, 0x03]))

        await self.start_comms()

    async def start_counter(self):
        async def run_counter():
            while not self.stop_counter.is_set():
                await asyncio.sleep(0.005)  # 5ms
                self.count += 1

        task = asyncio.create_task(run_counter())
        self.tasks.append(task)

    async def start_input_report(self):
        async def run_input_report():
            while not self.stop_input.is_set():
                await asyncio.sleep(0.03)  # 30ms
                self.write(0x30, self.count, self.get_input_buffer())

        task = asyncio.create_task(run_input_report())
        self.tasks.append(task)

    async def start_comms(self):
        async def run_comms():
            buf = bytearray(128)

            while not self.stop_comms.is_set():
                event_loop = asyncio.get_event_loop()
                n = await event_loop.run_in_executor(None, self.fp.readinto, buf)
                logger.info("read: %s %s", buf[:n].hex(), None)

                match buf[0]:
                    case 0x01:
                        await self.handle_0x01(buf)
                    case 0x80:
                        await self.handle_0x80(buf)
                    case 0x00 | 0x10:
                        self.handle_noop(buf)
                    case _:
                        logger.info("unknown request %s", buf[0])

        task = asyncio.create_task(run_comms())
        self.tasks.append(task)

    def handle_noop(self, _: bytearray):
        # No action required for 0x00 or 0x10
        pass

    async def handle_0x01(self, buf: bytearray):
        match buf[10]:
            case 0x01:
                self.uart(True, buf[10], bytes([0x03, 0x01]))
            case 0x02:
                self.uart(
                    True,
                    buf[10],
                    bytes([0x03, 0x48, 0x03, 0x02, 0x5E, 0x53, 0x00, 0x5E, 0x00, 0x00, 0x03, 0x01]),
                )
            case 0x03 | 0x08 | 0x30 | 0x38 | 0x40 | 0x41 | 0x48:
                self.uart(True, buf[10], bytes([]))
            case 0x04:
                self.uart(True, buf[10], bytes([]))
            case 0x10:
                data = self.spi_rom_data.get(buf[12], None)
                if data:
                    self.uart(True, buf[10], buf[11:16] + data[buf[11] : buf[11] + buf[15]])
                    logger.info(
                        "Read SPI address: %02x%02x[%d] %s",
                        buf[12],
                        buf[11],
                        buf[15],
                        data[buf[11] : buf[11] + buf[15]],
                    )
                else:
                    self.uart(False, buf[10], bytes([]))
                    logger.info("Unknown SPI address: %02x[%d]", buf[12], buf[15])
            case 0x21:
                self.uart(True, buf[10], bytes([0x01, 0x00, 0xFF, 0x00, 0x03, 0x00, 0x05, 0x01]))
            case _:
                logger.info("UART unknown request %s %s", buf[10], buf)

    async def handle_0x80(self, buf: bytearray):
        match buf[1]:
            case 0x01:
                self.write(0x81, buf[1], bytes([0x00, 0x03, 0x00, 0x00, 0x5E, 0x00, 0x53, 0x5E]))
            case 0x02 | 0x03:
                self.write(0x81, buf[1], bytes([]))
            case 0x04:
                await self.start_input_report()
            case 0x05:
                self.stop_input.set()
                self.stop_input.clear()
            case _:
                logger.info("Unknown 0x80 subcommand: %s", buf[1])

    def write(self, ack: int, cmd: int, buf: bytes):
        data = bytes([ack, cmd]) + buf + bytes(62 - len(buf))
        self.fp.write(data)

        logger.info("write: %s", data.hex())
        if ack == 0x30:
            logger.info("input report: %s", self.get_input_buffer().hex())

    def uart(self, ack: bool, sub_cmd: int, data: bytes):
        ack_byte = 0x00
        if ack:
            ack_byte = 0x80
            if len(data) > 0:
                ack_byte |= sub_cmd

        input_buffer = self.get_input_buffer()
        combined_data = input_buffer + bytes([ack_byte, sub_cmd]) + data
        self.write(0x21, self.count, combined_data)

    def get_input_buffer(self) -> bytes:
        def bit(position: int, condition: bool) -> int:
            return (1 << position) if condition else 0

        def pack_shorts(x: int, y: int) -> tuple[int, int, int, int]:
            return (x & 0xFF), (x >> 8), (y & 0xFF), (y >> 8)

        rhs = (
            bit(0, self.state.is_pressed(Buttons.Y))
            | bit(1, self.state.is_pressed(Buttons.X))
            | bit(2, self.state.is_pressed(Buttons.B))
            | bit(3, self.state.is_pressed(Buttons.A))
            | bit(6, self.state.is_pressed(Buttons.R))
            | bit(7, self.state.is_pressed(Buttons.ZR))
        )
        center = (
            bit(0, self.state.is_pressed(Buttons.MINUS))
            | bit(1, self.state.is_pressed(Buttons.PLUS))
            | bit(2, self.state.is_pressed(Buttons.RS))
            | bit(3, self.state.is_pressed(Buttons.LS))
            | bit(4, self.state.is_pressed(Buttons.HOME))
            | bit(5, self.state.is_pressed(Buttons.CAPTURE))
        )
        lhs = (
            bit(0, self.state.is_pressed(Buttons.DPAD_DOWN))
            | bit(1, self.state.is_pressed(Buttons.DPAD_UP))
            | bit(2, self.state.is_pressed(Buttons.DPAD_RIGHT))
            | bit(3, self.state.is_pressed(Buttons.DPAD_LEFT))
            | bit(6, self.state.is_pressed(Buttons.L))
            | bit(7, self.state.is_pressed(Buttons.ZL))
        )
        ls = pack_shorts(int(round((1 + self.state.ls.x) * 2047.5)), int(round((1 + self.state.ls.y) * 2047.5)))
        rs = pack_shorts(int(round((1 + self.state.rs.x) * 2047.5)), int(round((1 + self.state.rs.y) * 2047.5)))
        return bytes([0x81, rhs, center, lhs, ls[0], ls[1], ls[2], rs[0], rs[1], rs[2], 0x00])

    async def close(self):
        if self.fp is None:
            logger.info("Already closed")
            return

        self.stop_counter.set()
        self.stop_comms.set()
        self.stop_input.set()

        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.fp.close()
        self.fp = None
