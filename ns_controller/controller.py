import threading
import time
from typing import Final

from loguru import logger

from ns_controller import spi_rom_data
from ns_controller.pb.ns_controller_pb2 import ControllerState, Button


class Controller:
    def __init__(self):
        self.state = ControllerState()

        self.fp = None
        self.stop_comm: Final = threading.Event()
        self.stop_counter: Final = threading.Event()
        self.stop_input = threading.Event()  # Not Final - gets recreated on 0x05
        self.count = 0

    def connect(self, path: str):
        if self.fp is not None:
            raise Exception('Already connected')

        self.fp = open(path, 'r+b', buffering=0)

        self.stop_comm.clear()
        self.stop_counter.clear()
        self.stop_input.clear()

        self.start_counter()

        # Reset magic packet
        self.write(0x81, 0x03, bytes([]))
        self.write(0x81, 0x01, bytes([0x00, 0x03]))

        def run_comm_thread():
            buf = bytearray(128)

            try:
                while True:
                    # Check stop signal like Go's select with default
                    if self.stop_comm.is_set():
                        return

                    try:
                        n = self.fp.readinto(buf)
                        logger.info(f"read: {buf[:n].hex()}")
                    except Exception as e:
                        logger.error(f"Read error: {e}")
                        continue

                    match buf[0]:
                        case 0x80:
                            match buf[1]:
                                case 0x01:
                                    self.write(0x81, buf[1], bytes([
                                        0x00, 0x03, 0x00, 0x00, 0x5e, 0x00, 0x53, 0x5e
                                    ]))
                                case 0x02 | 0x03:
                                    self.write(0x81, buf[1], bytes([]))
                                case 0x04:
                                    self.start_input_report()
                                case 0x05:
                                    self.stop_input.set()
                                    # Wait briefly for thread to stop, then recreate event
                                    time.sleep(0.001)
                                    self.stop_input = threading.Event()
                        case 0x01:
                            match buf[10]:
                                case 0x01:
                                    self.uart(True, buf[10], bytes([
                                        0x03, 0x01
                                    ]))
                                case 0x02:
                                    self.uart(True, buf[10], bytes([
                                        0x03, 0x48, 0x03, 0x02, 0x5e, 0x53, 0x00, 0x5e, 0x00, 0x00, 0x03, 0x01
                                    ]))
                                case 0x03 | 0x08 | 0x30 | 0x38 | 0x40 | 0x41 | 0x48:
                                    self.uart(True, buf[10], bytes([]))
                                case 0x04:
                                    self.uart(True, buf[10], bytes([]))
                                case 0x10:
                                    data = spi_rom_data.get(buf[12])
                                    if data:
                                        self.uart(True, buf[10], buf[11:16] + data[buf[11]:buf[11] + buf[15]])
                                        logger.info(
                                            f"Read SPI address: {buf[12]:02x}{buf[11]:02x}[{buf[15]}] {data[buf[11]:buf[11] + buf[15]]}")
                                    else:
                                        self.uart(False, buf[10], bytes([]))
                                        logger.info(f"Unknown SPI address: {buf[12]:02x}[{buf[15]}]")
                                case 0x21:
                                    self.uart(True, buf[10], bytes([
                                        0x01, 0x00, 0xff, 0x00, 0x03, 0x00, 0x05, 0x01
                                    ]))
                                case _:
                                    logger.info(f"UART unknown request {buf[10]} {buf}")
                        case 0x00 | 0x10:
                            pass
                        case _:
                            logger.info(f"unknown request {buf[0]}")
            except Exception as e:
                logger.exception(f"Communication thread crashed: {e}")
                raise

        comm_thread = threading.Thread(target=run_comm_thread, daemon=True)
        comm_thread.start()

    def write(self, ack: int, cmd: int, buf: bytes):
        data = bytes([ack, cmd]) + buf + bytes(62 - len(buf))
        try:
            self.fp.write(data)
            logger.info(f"write: {data.hex()}")
            if ack == 0x30:
                logger.info(f"input report: {self.get_input_buffer().hex()}")
        except Exception as e:
            logger.error(f"Failed to write to device: {e}")
            raise

    def start_counter(self):
        def run_counter():
            while not self.stop_counter.is_set():
                time.sleep(0.005)  # 5ms
                self.count = (self.count + 1) & 0xFF  # Wrap at 256 like uint8

        counter_thread = threading.Thread(target=run_counter, daemon=True)
        counter_thread.start()

    def start_input_report(self):
        def run_input_report():
            while not self.stop_input.is_set():
                time.sleep(0.03)  # 30ms
                self.write(0x30, self.count, self.get_input_buffer())

        input_report_thread = threading.Thread(target=run_input_report, daemon=True)
        input_report_thread.start()

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

        def pack_shorts(x: int, y: int) -> tuple[int, int, int]:
            """Pack two 12-bit values into 3 bytes (Nintendo Switch format)."""
            return (
                x & 0xFF,
                ((y << 4) & 0xF0) | ((x >> 8) & 0x0F),
                (y >> 4) & 0xFF
            )

        # Named 'left' to match button byte position (Go calls this 'left')
        left = (
                bit(0, bool(self.state.buttons >> Button.Y & 1)) |
                bit(1, bool(self.state.buttons >> Button.X & 1)) |
                bit(2, bool(self.state.buttons >> Button.B & 1)) |
                bit(3, bool(self.state.buttons >> Button.A & 1)) |
                bit(6, bool(self.state.buttons >> Button.R & 1)) |
                bit(7, bool(self.state.buttons >> Button.ZR & 1))
        )
        center = (
                bit(0, bool(self.state.buttons >> Button.MINUS & 1)) |
                bit(1, bool(self.state.buttons >> Button.PLUS & 1)) |
                bit(2, bool(self.state.buttons >> Button.R_STICK & 1)) |
                bit(3, bool(self.state.buttons >> Button.L_STICK & 1)) |
                bit(4, bool(self.state.buttons >> Button.HOME & 1)) |
                bit(5, bool(self.state.buttons >> Button.CAPTURE & 1))
        )
        # Named 'right' to match button byte position (Go calls this 'right')
        right = (
                bit(0, bool(self.state.buttons >> Button.DPAD_DOWN & 1)) |
                bit(1, bool(self.state.buttons >> Button.DPAD_UP & 1)) |
                bit(2, bool(self.state.buttons >> Button.DPAD_RIGHT & 1)) |
                bit(3, bool(self.state.buttons >> Button.DPAD_LEFT & 1)) |
                bit(6, bool(self.state.buttons >> Button.L & 1)) |
                bit(7, bool(self.state.buttons >> Button.ZL & 1))
        )

        lx = int(round((1 + self.state.ls.x) * 2047.5))
        ly = int(round((1 + self.state.ls.y) * 2047.5))
        rx = int(round((1 + self.state.rs.x or 0.0) * 2047.5))
        ry = int(round((1 + self.state.rs.y or 0.0) * 2047.5))

        left_stick = pack_shorts(lx, ly)
        right_stick = pack_shorts(rx, ry)

        return bytes([0x81, left, center, right, left_stick[0], left_stick[1],
                      left_stick[2], right_stick[0], right_stick[1], right_stick[2], 0x00])

    def close(self):
        if self.fp is None:
            logger.info("Already closed")
            return
        self.stop_counter.set()
        self.stop_comm.set()
        self.stop_input.set()

        self.fp.close()
        self.fp = None
