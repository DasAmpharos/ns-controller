"""`Pico`: talk to the ns-controller firmware over its serial link.

    with Pico("/dev/serial/by-id/usb-Raspberry_Pi_Debug_Probe...") as pico:
        print(pico.status())
        pico.run([Keyframe(0, State(button_bits(["A"]))), Keyframe(100_000, NEUTRAL)])

Every command is acknowledged; a missing reply is resent with the same sequence number (the Pico replays its reply
without re-running the command), and after `retries` resends the link counts as down. A heartbeat PING keeps the
Pico's safety release from firing while the brain is idle. If the Pico reboots (BOOT message), the next command
says HELLO again first.
"""

from __future__ import annotations

import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from loguru import logger

from nsctl import protocol as p
from nsctl.protocol import Keyframe, State


class LinkError(Exception):
    pass


class BusyError(LinkError):
    """A macro is playing; SET_STATE / MACRO_LOAD / MACRO_RUN have to wait for it (or ABORT it)."""


@dataclass(frozen=True)
class Hello:
    proto: int
    fw_hash: int
    max_keyframes: int
    text: str


@dataclass(frozen=True)
class Status:
    flags: int
    uptime_ms: int
    macro_id: int
    macro_index: int

    @property
    def names(self) -> list[str]:
        return [n for i, n in enumerate(p.FLAG_NAMES) if self.flags >> i & 1]

    @property
    def ready(self) -> bool:
        """Talking to a Switch that has finished the Pro Controller handshake and isn't asleep."""
        mounted_and_handshake = 0b0101
        return self.flags & mounted_and_handshake == mounted_and_handshake and not self.flags & 0b0010

    @classmethod
    def unpack(cls, payload: bytes) -> Status:
        return cls(*struct.unpack("<BIHH", payload[:9]))


@dataclass(frozen=True)
class MacroDone:
    macro_id: int
    result: str  # completed | aborted | safety
    start_us: int
    duration_us: int


class Pico:
    def __init__(
        self,
        port,  # noqa: ANN001 - path, or an object with read(n)/write(b) (tests)
        baud: int = 1_000_000,
        *,
        retry_s: float = 0.1,
        retries: int = 3,
        heartbeat_s: float = 0.5,
        on_log: Callable[[str], None] | None = None,
        on_status: Callable[[Status], None] | None = None,
    ) -> None:
        if isinstance(port, str):
            import serial

            port = serial.Serial(port, baud, timeout=0.02)
        self._port = port
        self.retry_s, self.retries, self.heartbeat_s = retry_s, retries, heartbeat_s
        self.on_log = on_log or (lambda text: logger.debug("pico: {}", text))
        self.on_status = on_status
        self.last_status: Status | None = None
        self.boots = 0

        self._decoder = p.Decoder()
        self._lock = threading.Lock()  # one request on the wire at a time
        self._reply_ready = threading.Event()
        self._waiting_seq = 0
        self._reply: p.Frame | None = None
        self._seq = 0
        self._macro_id = 0
        self._done: dict[int, MacroDone] = {}
        self._done_cond = threading.Condition()
        self._need_hello = False
        self._last_tx = 0.0
        self._closed = threading.Event()

        self._reader = threading.Thread(target=self._read_loop, daemon=True, name="nsctl-reader")
        self._reader.start()
        self.info = self.hello()
        self._heartbeat = threading.Thread(target=self._heartbeat_loop, daemon=True, name="nsctl-heartbeat")
        self._heartbeat.start()

    def __enter__(self) -> Pico:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._closed.is_set():
            return
        try:
            self.abort()  # never leave a button held
        except LinkError:
            pass
        self._closed.set()
        self._reader.join(timeout=1)
        close = getattr(self._port, "close", None)
        if close:
            close()

    # ── receiving ─────────────────────────────────────────────────────────────

    def _read_loop(self) -> None:
        while not self._closed.is_set():
            try:
                # read(256) would wait out the whole timeout for a short reply: take one byte (or time out),
                # then whatever else has already arrived.
                data = self._port.read(1)
                waiting = getattr(self._port, "in_waiting", 0)
                if data and waiting:
                    data += self._port.read(waiting)
            except Exception as e:  # noqa: BLE001 - serial unplugged etc.
                logger.error("nsctl: serial read failed: {}", e)
                time.sleep(0.5)
                continue
            for frame in self._decoder.feed(data or b""):
                self._dispatch(frame)

    def _dispatch(self, f: p.Frame) -> None:
        if f.seq and f.type in (p.ACK, p.HELLO_REPLY, p.STATUS):
            if f.seq == self._waiting_seq:
                self._reply = f
                self._reply_ready.set()
        elif f.type == p.MACRO_DONE:
            mid, result, lo, hi, duration = struct.unpack("<HBIII", f.payload[:15])
            done = MacroDone(mid, p.RESULT_NAMES.get(result, str(result)), lo | hi << 32, duration)
            with self._done_cond:
                self._done[mid] = done
                self._done_cond.notify_all()
        elif f.type == p.STATUS_CHANGED:
            self.last_status = Status.unpack(f.payload)
            if self.on_status:
                self.on_status(self.last_status)
        elif f.type == p.BOOT:
            fw, reason = struct.unpack("<IB", f.payload[:5])
            self.boots += 1
            self._need_hello = True
            logger.warning(
                "nsctl: Pico booted ({}): {}", p.RESET_NAMES.get(reason, reason), f.payload[5:].decode(errors="replace")
            )
            with self._done_cond:
                self._done_cond.notify_all()  # anything waiting on a macro has lost it
        elif f.type == p.LOG:
            self.on_log(f.payload[1:].decode(errors="replace"))

    # ── requests ──────────────────────────────────────────────────────────────

    def _next_seq(self) -> int:
        self._seq = self._seq % 255 + 1
        return self._seq

    def _exchange(self, type_: int, payload: bytes) -> p.Frame:
        seq = self._next_seq()
        wire = p.encode(type_, seq, payload)
        for _ in range(self.retries + 1):
            self._reply_ready.clear()
            self._waiting_seq = seq
            self._port.write(wire)
            self._last_tx = time.monotonic()
            if self._reply_ready.wait(self.retry_s):
                self._waiting_seq = 0
                return self._reply
        self._waiting_seq = 0
        raise LinkError(f"no reply from the Pico to 0x{type_:02x} after {self.retries + 1} tries")

    def _request(self, type_: int, payload: bytes = b"") -> p.Frame:
        if self._closed.is_set():
            raise LinkError("link closed")
        with self._lock:
            if self._need_hello and type_ != p.HELLO:
                self._need_hello = False
                self._parse_hello(self._exchange(p.HELLO, struct.pack("<H", p.PROTO_VERSION)))
            return self._exchange(type_, payload)

    def _ack(self, type_: int, payload: bytes = b"") -> None:
        f = self._request(type_, payload)
        status = f.payload[0] if f.type == p.ACK and f.payload else -1
        if status == 0:
            return
        name = p.ACK_NAMES.get(status, f"unexpected reply 0x{f.type:02x}")
        raise (BusyError if status == 1 else LinkError)(f"Pico refused 0x{type_:02x}: {name}")

    def _parse_hello(self, f: p.Frame) -> Hello:
        proto, fw, max_kf = struct.unpack("<HIH", f.payload[:8])
        info = Hello(proto, fw, max_kf, f.payload[8:].decode(errors="replace"))
        if proto != p.PROTO_VERSION:
            raise LinkError(f"Pico speaks protocol {proto}, nsctl {p.PROTO_VERSION}: update one of them")
        return info

    def _heartbeat_loop(self) -> None:
        while not self._closed.wait(self.heartbeat_s / 2):
            if time.monotonic() - self._last_tx >= self.heartbeat_s:
                try:
                    self.ping()
                except LinkError as e:
                    logger.warning("nsctl: heartbeat failed: {}", e)

    # ── commands ──────────────────────────────────────────────────────────────

    def hello(self) -> Hello:
        with self._lock:
            self._need_hello = False
            return self._parse_hello(self._exchange(p.HELLO, struct.pack("<H", p.PROTO_VERSION)))

    def ping(self) -> None:
        self._ack(p.PING)

    def status(self) -> Status:
        f = self._request(p.GET_STATUS)
        self.last_status = Status.unpack(f.payload)
        return self.last_status

    def set_state(self, state: State) -> None:
        self._ack(p.SET_STATE, state.pack())

    def abort(self) -> None:
        self._ack(p.ABORT)

    def reboot(self, bootsel: bool = False) -> None:
        self._ack(p.REBOOT, bytes([1 if bootsel else 0]))

    def start(self, keyframes: list[Keyframe]) -> int:
        """Upload a macro and start it; returns its id. The Pico plays it on its own clock."""
        if not keyframes:
            raise ValueError("empty macro")
        if len(keyframes) > self.info.max_keyframes:
            raise ValueError(f"{len(keyframes)} keyframes; the Pico holds {self.info.max_keyframes}")
        self._macro_id = self._macro_id % 0xFFFF + 1
        mid = self._macro_id
        with self._done_cond:
            self._done.pop(mid, None)
        for payload in p.macro_load_payloads(mid, keyframes):
            self._ack(p.MACRO_LOAD, payload)
        self._ack(p.MACRO_RUN, struct.pack("<H", mid))
        return mid

    def wait(self, macro_id: int, timeout: float) -> MacroDone:
        deadline = time.monotonic() + timeout
        boots = self.boots
        with self._done_cond:
            while macro_id not in self._done:
                remaining = deadline - time.monotonic()
                if self.boots != boots:
                    raise LinkError(f"Pico rebooted while macro {macro_id} was playing")
                if remaining <= 0:
                    raise LinkError(f"macro {macro_id} didn't finish within {timeout:.1f}s")
                self._done_cond.wait(remaining)
            return self._done.pop(macro_id)

    def run(self, keyframes: list[Keyframe], timeout: float | None = None) -> MacroDone:
        """Play a macro and wait for it to finish."""
        mid = self.start(keyframes)
        return self.wait(mid, timeout if timeout is not None else keyframes[-1].t_us / 1e6 + 2.0)
