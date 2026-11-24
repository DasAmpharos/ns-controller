# Brain ↔ Pico serial protocol, v1

Implemented by the firmware (`firmware/src/link.c`, host-tested in `firmware/test/test_link.c`) and by `nsctl`
(`nsctl/nsctl/protocol.py`, `client.py`). Bump `LINK_PROTO_VERSION` (firmware) and `PROTO_VERSION` (nsctl) together
on any incompatible change; `HELLO` refuses a mismatch.

## Physical layer

- UART0 on the Pico (GP0 = TX, GP1 = RX), 3.3 V logic, 8N1, **1,000,000 baud**, no flow control.
- Brain side: the Raspberry Pi Debug Probe's UART (`/dev/serial/by-id/usb-Raspberry_Pi_Debug_Probe_*-if01`), or any
  3.3 V USB-serial adapter (FTDI: udev rule `latency_timer=1`, the default 16 ms adds latency). Wiring: Pico GP0 →
  probe/adapter RX, GP1 ← TX, GND ↔ GND. Never connect VCC.
- The same wire carries the firmware's log (`LOG` frames), so there is no separate debug UART.

## Framing

```
wire:   COBS( type:u8 | seq:u8 | payload:bytes | crc16:u16le ) | 0x00
```

- COBS-encoded, `0x00` terminates each frame. Max decoded frame: 256 bytes (payload ≤ 252).
- CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, xorout 0) over `type|seq|payload`.
- Bad CRC or malformed COBS: the frame is dropped silently and counted (`bad_frames` in the firmware's stats log);
  the sender's resend covers it.
- All multi-byte integers little-endian.

## Reliability

- Every brain → Pico command gets exactly one reply: an `ACK`, or a typed reply carrying the same `seq`.
- `nsctl` resends the identical frame (same `seq`) after 100 ms without a reply, 3 times, then raises `LinkError`
  (the caller reconnects with a new `HELLO`).
- The Pico remembers the last `seq` and the reply it sent; a repeated `seq` gets the stored reply again **without
  re-executing**. `HELLO` is never de-duplicated (it is how a brain re-syncs). `seq` wraps 1..255; 0 marks
  unsolicited Pico messages.
- Commands carry full state, never deltas, so a resend can't double a press.
- `nsctl` sends `PING` when it has sent nothing for 500 ms (the heartbeat that holds off the safety release).

## Data types

```
State (12 bytes):
  buttons: u32   bit i = Button i (layout below); bits 20-31 reserved = 0
  lx, ly, rx, ry: u16 each, 12-bit value (0..4095), centre 2048

Keyframe (16 bytes):
  delta_us: u32  time after the previous keyframe (first keyframe: after MACRO_RUN is accepted)
  state:    State
```

Button bits (same as the old gRPC proto enum, so old code maps 1:1):
`A0 B1 X2 Y3 L4 R5 ZL6 ZR7 LSTICK8 RSTICK9 PLUS10 MINUS11 HOME12 CAPTURE13 DUP14 DDOWN15 DLEFT16 DRIGHT17 SL18 SR19`

Stick conversion from the old float range: `raw = round((v + 1) * 2047.5)`, clamped to 0..4095.

## Messages: brain → Pico

| Type | Name | Payload | Reply |
|---|---|---|---|
| 0x01 | `HELLO` | `proto_version:u16` | `HELLO_REPLY` |
| 0x02 | `PING` | none | `ACK` |
| 0x03 | `GET_STATUS` | none | `STATUS` (same `seq`) |
| 0x10 | `SET_STATE` | `State` | `ACK` (`BUSY` while a macro runs) |
| 0x20 | `MACRO_LOAD` | `macro_id:u16, total:u16, offset:u16, count:u8, Keyframe[count]` | `ACK` |
| 0x21 | `MACRO_RUN` | `macro_id:u16` | `ACK` (`MACRO_INCOMPLETE` unless all `total` keyframes are loaded) |
| 0x22 | `ABORT` | none | `ACK`; the macro stops, state → neutral, `MACRO_DONE(result=ABORTED)` follows |
| 0x30 | `REBOOT` | `bootsel:u8` (1 = reboot into the USB bootloader, for flashing) | `ACK`, then reboot |

`MACRO_LOAD`: up to 15 keyframes per frame, `total` ≤ 2048. Chunks must arrive in order (`offset` = keyframes
loaded so far; a gap → `BAD_ARG`). Loading a new `macro_id` discards a partly loaded one. Loading while a macro runs
→ `BUSY`.

## Messages: Pico → brain

| Type | Name | Payload |
|---|---|---|
| 0x80 | `ACK` | `status:u8` |
| 0x81 | `HELLO_REPLY` | `proto_version:u16, fw_version:u32, max_keyframes:u16, fw_text:utf8` |
| 0x82 | `STATUS` | `flags:u8, uptime_ms:u32, macro_id:u16, macro_index:u16` |
| 0x83 | `MACRO_DONE` (seq 0) | `macro_id:u16, result:u8 (0=COMPLETED, 1=ABORTED, 2=SAFETY), start_us:u64, duration_us:u32` |
| 0x84 | `BOOT` (seq 0) | `fw_version:u32, reset_reason:u8 (0=power on, 1=watchdog, 2=REBOOT command), fw_text:utf8` |
| 0x85 | `STATUS_CHANGED` (seq 0) | same as `STATUS`; sent on any flag change |
| 0x8F | `LOG` (seq 0) | `level:u8 (1 = info), utf8 text`; always on, dropped rather than delay a reply when the TX buffer is full |

`fw_version` is the first 32 bits of the firmware's git hash; `fw_text` is e.g.
`ns-controller 0.2.0+d97e518 (pico2_w)`.

`STATUS.flags`: bit0 USB mounted, bit1 host suspended (Switch asleep), bit2 Pro Controller handshake complete,
bit3 input reports flowing, bit4 macro running, bit5 safety release active.

ACK status: `0 OK, 1 BUSY, 2 BAD_ARG, 3 UNKNOWN_TYPE, 4 VERSION_MISMATCH, 5 MACRO_INCOMPLETE, 6 NOT_READY`.

## Pico behaviour rules

1. **Safety release:** once a brain has been heard, no valid frame for 2,000 ms and no macro running → state =
   neutral, flag bit5 set (cleared by the next valid frame). A running macro is allowed to finish; it ends neutral.
2. **Macro end:** after the last keyframe's state is applied, the Pico sends `MACRO_DONE(COMPLETED)`. If the Switch
   stops polling mid-macro (unplugged, asleep), the macro stops with `MACRO_DONE(ABORTED)`.
3. **One macro at a time.** `SET_STATE`, `MACRO_LOAD`, `MACRO_RUN` while one runs → `BUSY`. `ABORT` always works.
4. **Watchdog:** hardware watchdog 1,000 ms, fed from the main loop. After a watchdog reset, `BOOT` says so.
5. **Report timing:** an input report on every state change (next available IN transfer) and at least every 8 ms.

## Brain-side compile rules (`MacroBuilder.build()`)

`MacroBuilder` lives in ns-shiny-hunter (`ns_shiny_hunter/controller.py`); its Pico backend (`pico.py`) sends the
keyframes with nsctl. The action set compiles to absolute times, then to deltas:
- `click(btns, down_ms)`: press at t, release at t+down_ms, then gap.
- `repeat_click(btns, count, down_ms, gap_ms)`, `hold`, `spam(interval)` (40% down / 60% up, as in the old executor).
- `wait(ms)`: advance t.
- `mark(name)` / `mark=` on actions: record t. `wait_until(mark, offset)`: t = max(t, mark + offset).
- `set_stick(stick, x, y, duration_ms)`: set, and if duration > 0 re-centre after it.
- Keyframes with identical timestamps merge, no-op keyframes are dropped, and every macro ends neutral (inputs that
  must stay held use `Switch.holding()`, which sends `SET_STATE`).
