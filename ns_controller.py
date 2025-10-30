import logging
import threading
import time
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final


class NsController:
    @dataclass
    class InputStruct:
        @dataclass
        class ButtonStruct:
            a: bool = False
            b: bool = False
            x: bool = False
            y: bool = False
            # shoulders
            l: bool = False
            r: bool = False
            # triggers
            zl: bool = False
            zr: bool = False

            minus: bool = False
            plus: bool = False
            home: bool = False
            capture: bool = False

        @dataclass
        class StickStruct:
            @dataclass
            class Axis:
                x: int = 0
                y: int = 0
                pressed: bool = False

            left: Axis = field(default_factory=Axis)
            right: Axis = field(default_factory=Axis)

        @dataclass
        class DpadStruct:
            up: bool = False
            down: bool = False
            left: bool = False
            right: bool = False

        buttons: ButtonStruct = field(default_factory=ButtonStruct)
        sticks: StickStruct = field(default_factory=StickStruct)
        dpad: DpadStruct = field(default_factory=DpadStruct)

    SPI_ROM_DATA: Final = MappingProxyType({
        0x60: bytes([
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0x03, 0xa0, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x02, 0xff, 0xff, 0xff, 0xff,
            0xf0, 0xff, 0x89, 0x00, 0xf0, 0x01, 0x00, 0x40, 0x00, 0x40, 0x00, 0x40, 0xf9, 0xff, 0x06, 0x00,
            0x09, 0x00, 0xe7, 0x3b, 0xe7, 0x3b, 0xe7, 0x3b, 0xff, 0xff, 0xff, 0xff, 0xff, 0xba, 0x15, 0x62,
            0x11, 0xb8, 0x7f, 0x29, 0x06, 0x5b, 0xff, 0xe7, 0x7e, 0x0e, 0x36, 0x56, 0x9e, 0x85, 0x60, 0xff,
            0x32, 0x32, 0x32, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0x50, 0xfd, 0x00, 0x00, 0xc6, 0x0f, 0x0f, 0x30, 0x61, 0x96, 0x30, 0xf3, 0xd4, 0x14, 0x54, 0x41,
            0x15, 0x54, 0xc7, 0x79, 0x9c, 0x33, 0x36, 0x63, 0x0f, 0x30, 0x61, 0x96, 0x30, 0xf3, 0xd4, 0x14,
            0x54, 0x41, 0x15, 0x54, 0xc7, 0x79, 0x9c, 0x33, 0x36, 0x63, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
        ]),
        0x80: bytes([
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xb2, 0xa1, 0xbe, 0xff, 0x3e, 0x00, 0xf0, 0x01, 0x00, 0x40,
            0x00, 0x40, 0x00, 0x40, 0xfe, 0xff, 0xfe, 0xff, 0x08, 0x00, 0xe7, 0x3b, 0xe7, 0x3b, 0xe7, 0x3b,
        ])
    })

    def __init__(self):
        self.logger: Final = logging.getLogger(self.__class__.__name__)
        self.inputs = self.InputStruct()

        self.fp = None
        self.stop_communicate: Final = threading.Event()
        self.stop_counter: Final = threading.Event()
        self.stop_input: Final = threading.Event()
        self.count = 0

    def connect(self, path: str):
        if self.fp is not None:
            raise Exception('Already connected')

        self.fp = open(path, 'r+b', buffering=0)

        self.stop_communicate.clear()
        self.stop_counter.clear()
        self.stop_input.clear()

        self.start_counter()

        # Reset magic packet
        self.write(0x81, 0x03, bytes([]))
        self.write(0x81, 0x01, bytes([0x00, 0x03]))

        def run_communication_thread():
            buf = bytearray(128)

            while not self.stop_communicate.is_set():
                n = self.fp.readinto(buf)
                self.logger.info("read: %s %s", buf[:n].hex(), None)

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
                                self.stop_input.clear()
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
                                data = self.SPI_ROM_DATA.get(buf[12], None)
                                if data:
                                    self.uart(True, buf[10], buf[11:16] + data[buf[11]:buf[11] + buf[15]])
                                    self.logger.info("Read SPI address: %02x%02x[%d] %s", buf[12], buf[11], buf[15],
                                                     data[buf[11]:buf[11] + buf[15]])
                                else:
                                    self.uart(False, buf[10], bytes([]))
                                    self.logger.info("Unknown SPI address: %02x[%d]", buf[12], buf[15])
                            case 0x21:
                                self.uart(True, buf[10], bytes([
                                    0x01, 0x00, 0xff, 0x00, 0x03, 0x00, 0x05, 0x01
                                ]))
                            case _:
                                self.logger.info("UART unknown request %s %s", buf[10], buf)
                        break
                    case 0x00 | 0x10:
                        pass
                    case _:
                        logging.info("unknown request %s", buf[0])

        communication_thread = threading.Thread(target=run_communication_thread, daemon=True)
        communication_thread.start()

    def write(self, ack: int, cmd: int, buf: bytes):
        data = bytes([ack, cmd]) + buf + bytes(62 - len(buf))
        self.fp.write(data)

        self.logger.info("write: %s", data.hex())
        if ack == 0x30:
            self.logger.info("input report: %s", self.get_input_buffer().hex())

    def start_counter(self):
        def run_counter():
            while not self.stop_counter.is_set():
                time.sleep(0.005)  # 5ms
                self.count += 1

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
        left = (self.bit_input(self.inputs.buttons.y, 0) |
                self.bit_input(self.inputs.buttons.x, 1) |
                self.bit_input(self.inputs.buttons.b, 2) |
                self.bit_input(self.inputs.buttons.a, 3) |
                self.bit_input(self.inputs.buttons.r, 6) |
                self.bit_input(self.inputs.buttons.zr, 7))

        center = (self.bit_input(self.inputs.buttons.minus, 0) |
                  self.bit_input(self.inputs.buttons.plus, 1) |
                  self.bit_input(self.inputs.sticks.right.pressed, 2) |
                  self.bit_input(self.inputs.sticks.left.pressed, 3) |
                  self.bit_input(self.inputs.buttons.home, 4) |
                  self.bit_input(self.inputs.buttons.capture, 5))

        right = (self.bit_input(self.inputs.dpad.down, 0) |
                 self.bit_input(self.inputs.dpad.up, 1) |
                 self.bit_input(self.inputs.dpad.right, 2) |
                 self.bit_input(self.inputs.dpad.left, 3) |
                 self.bit_input(self.inputs.buttons.l, 6) |
                 self.bit_input(self.inputs.buttons.zl, 7))

        lx = int(round((1 + self.inputs.sticks.left.x) * 2047.5))
        ly = int(round((1 + self.inputs.sticks.left.y) * 2047.5))
        rx = int(round((1 + self.inputs.sticks.right.x) * 2047.5))
        ry = int(round((1 + self.inputs.sticks.right.x) * 2047.5))

        left_stick = self.pack_shorts(lx, ly)
        right_stick = self.pack_shorts(rx, ry)

        return bytes([0x81, left, center, right, left_stick[0], left_stick[1],
                      left_stick[2], right_stick[0], right_stick[1], right_stick[2], 0x00])

    @staticmethod
    def bit_input(condition, position) -> int:
        return (1 << position) if condition else 0

    @staticmethod
    def pack_shorts(x, y):
        return [(x & 0xFF), (x >> 8), (y & 0xFF), (y >> 8)]

    def close(self):
        if self.fp is None:
            logging.info("Already closed")
            return
        self.stop_counter.set()
        self.stop_communicate.set()
        self.stop_input.set()

        self.fp.close()
        self.fp = None
