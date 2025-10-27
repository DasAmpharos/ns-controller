import asyncio
import functools
import logging
from pathlib import Path
from types import MappingProxyType
from typing import Final

from .protocol import ControllerInput


@functools.cache
def load_spi_rom_data() -> MappingProxyType[int, bytes]:
    directory = Path(__file__).parent / "spi_rom_data"
    return MappingProxyType({
        int(bin_file.stem, 16): bin_file.read_bytes()
        for bin_file in directory.glob("*.bin")
    })


class Controller:
    logger: Final = logging.getLogger(__name__)
    SPI_ROM_DATA: Final = load_spi_rom_data()

    def __init__(self):
        self._fp = None
        self._input = ControllerInput()

        self._tasks = []
        self._stop_comms: Final = asyncio.Event()
        self._stop_counter: Final = asyncio.Event()
        self._stop_input: Final = asyncio.Event()
        self._count = 0

    def get_input(self) -> ControllerInput:
        return self._input

    def set_input(self, new_input: ControllerInput):
        self._input = new_input

    async def connect(self, path: str):
        if self._fp is not None:
            raise Exception("Already connected")

        self._fp = open(path, "r+b", buffering=0)

        self._stop_comms.clear()
        self._stop_counter.clear()
        self._stop_input.clear()

        await self.start_counter()

        # Reset magic packet
        self.write(0x81, 0x03, bytes([]))
        self.write(0x81, 0x01, bytes([0x00, 0x03]))

        await self.start_comms()

    async def start_counter(self):
        async def run_counter():
            while not self._stop_counter.is_set():
                await asyncio.sleep(0.005)  # 5ms
                self._count += 1

        task = asyncio.create_task(run_counter())
        self._tasks.append(task)

    async def start_input_report(self):
        async def run_input_report():
            while not self._stop_input.is_set():
                await asyncio.sleep(0.03)  # 30ms
                self.write(0x30, self._count, self.get_input_buffer())

        task = asyncio.create_task(run_input_report())
        self._tasks.append(task)

    async def start_comms(self):
        async def run_comms():
            buf = bytearray(128)

            while not self._stop_comms.is_set():
                event_loop = asyncio.get_event_loop()
                n = await event_loop.run_in_executor(None, self._fp.readinto, buf)
                self.logger.info("read:%s", buf[:n].hex())

                match buf[0]:
                    case 0x01:
                        await self.handle_0x01(buf)
                    case 0x80:
                        await self.handle_0x80(buf)
                    case 0x00 | 0x10:
                        self.handle_noop(buf)
                    case _:
                        self.logger.error("unknown request %s", buf[0])

        task = asyncio.create_task(run_comms())
        self._tasks.append(task)

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
                data = self.SPI_ROM_DATA.get(buf[12], None)
                if data:
                    self.uart(True, buf[10], buf[11:16] + data[buf[11]: buf[11] + buf[15]])
                    self.logger.info(
                        "Read SPI address: %02x%02x[%d] %s",
                        buf[12],
                        buf[11],
                        buf[15],
                        data[buf[11]: buf[11] + buf[15]],
                    )
                else:
                    self.uart(False, buf[10], bytes([]))
                    self.logger.info("Unknown SPI address: %02x[%d]", buf[12], buf[15])
            case 0x21:
                self.uart(True, buf[10], bytes([0x01, 0x00, 0xFF, 0x00, 0x03, 0x00, 0x05, 0x01]))
            case _:
                self.logger.error("UART unknown request %s %s", buf[10], buf)

    async def handle_0x80(self, buf: bytearray):
        match buf[1]:
            case 0x01:
                self.write(0x81, buf[1], bytes([0x00, 0x03, 0x00, 0x00, 0x5E, 0x00, 0x53, 0x5E]))
            case 0x02 | 0x03:
                self.write(0x81, buf[1], bytes([]))
            case 0x04:
                await self.start_input_report()
            case 0x05:
                self._stop_input.set()
                self._stop_input.clear()
            case _:
                self.logger.error("Unknown 0x80 subcommand: %s", buf[1])

    def write(self, ack: int, cmd: int, buf: bytes):
        data = bytes([ack, cmd]) + buf + bytes(62 - len(buf))
        self._fp.write(data)

        self.logger.info("write: %s", data.hex())
        if ack == 0x30:
            self.logger.info("input report: %s", self.get_input_buffer().hex())

    def uart(self, ack: bool, sub_cmd: int, data: bytes):
        ack_byte = 0x00
        if ack:
            ack_byte = 0x80
            if len(data) > 0:
                ack_byte |= sub_cmd

        input_buffer = self.get_input_buffer()
        combined_data = input_buffer + bytes([ack_byte, sub_cmd]) + data
        self.write(0x21, self._count, combined_data)

    def get_input_buffer(self) -> bytes:
        def bit_input(p_input: bool, position: int) -> int:
            return (1 << position) if p_input else 0

        def pack_shorts(x: int, y: int) -> tuple[int, int, int, int]:
            return (x & 0xFF), (x >> 8), (y & 0xFF), (y >> 8)

        rhs = (
            bit_input(self._input.buttons.y, 0)
            | bit_input(self._input.buttons.x, 1)
            | bit_input(self._input.buttons.b, 2)
            | bit_input(self._input.buttons.a, 3)
            | bit_input(self._input.buttons.r, 6)
            | bit_input(self._input.buttons.zr, 7)
        )
        center = (
            bit_input(self._input.buttons.minus, 0)
            | bit_input(self._input.buttons.plus, 1)
            | bit_input(self._input.sticks.right.pressed, 2)
            | bit_input(self._input.sticks.left.pressed, 3)
            | bit_input(self._input.buttons.home, 4)
            | bit_input(self._input.buttons.capture, 5)
        )
        lhs = (
            bit_input(self._input.dpad.down, 0)
            | bit_input(self._input.dpad.up, 1)
            | bit_input(self._input.dpad.right, 2)
            | bit_input(self._input.dpad.left, 3)
            | bit_input(self._input.buttons.l, 6)
            | bit_input(self._input.buttons.zl, 7)
        )
        ls = pack_shorts(int(round((1 + self._input.sticks.left.x) * 2047.5)),
                         int(round((1 + self._input.sticks.left.y) * 2047.5)))
        rs = pack_shorts(int(round((1 + self._input.sticks.right.x) * 2047.5)),
                         int(round((1 + self._input.sticks.right.y) * 2047.5)))
        return bytes([0x81, rhs, center, lhs, ls[0], ls[1], ls[2], rs[0], rs[1], rs[2], 0x00])

    async def close(self):
        if self._fp is None:
            self.logger.warning("Already closed")
            return

        self._stop_counter.set()
        self._stop_comms.set()
        self._stop_input.set()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._fp.close()
        self._fp = None
