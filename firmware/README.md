# ns-controller firmware (Phase 1 spike)

C firmware (Pico SDK 2.2.0 + TinyUSB) that makes a Raspberry Pi Pico (2) W appear to a Nintendo Switch as a wired
Pro Controller. This spike only proves the USB side. It enumerates, completes the Switch handshake and streams
input reports. **Press the Pico's BOOTSEL button to play a built-in test** (see below). There is no brain link yet.

| File | What it is |
|---|---|
| `src/procon.c` | Handshake (`0x80` commands), UART subcommands, SPI flash reads, input report packing. Hardware-free |
| `src/procon_data.c` | HID report descriptor + SPI flash pages, generated from the old gadget/Python sources |
| `src/usb_descriptors.c` | Device/config/string descriptors (VID `057e`, PID `2009`) |
| `src/main.c` | Main loop: TinyUSB, reply queue, 8 ms input reports, BOOTSEL tests, LED, watchdog |
| `src/player.c` | Keyframe player (hardware-free); plays the test sequences now, brain macros in Phase 2 |
| `sequences/*.txt` | Test sequences in nxbt macro format, compiled at build time by `tools/macro2c.py` |
| `src/log.c` | Non-blocking UART log (ring buffer, never stalls USB) |
| `test/` | Host unit tests; golden vectors recorded from the Python `Controller` that worked on the consoles |

## Build

Needs `gcc-arm-none-eabi`, `cmake`, and the Pico SDK 2.2.0 with the `tinyusb` and `cyw43-driver` submodules.
CMake finds the SDK at `$PICO_SDK_PATH` or `~/.pico-sdk/sdk/2.2.0`:

```sh
git clone --depth 1 --branch 2.2.0 https://github.com/raspberrypi/pico-sdk ~/.pico-sdk/sdk/2.2.0
git -C ~/.pico-sdk/sdk/2.2.0 submodule update --init --depth 1 lib/tinyusb lib/cyw43-driver

cmake -S . -B build-pico2w -DPICO_BOARD=pico2_w && cmake --build build-pico2w -j   # Pico 2 W
cmake -S . -B build && cmake --build build -j     # Pico W (default); pico / pico2 for boards without wireless
cmake -S test -B build-test && cmake --build build-test && ctest --test-dir build-test --output-on-failure
```

Regenerate the golden vectors with `../../ns-shiny-hunter/.venv/bin/python test/gen_vectors.py > test/vectors.h`.
This needs the gRPC-era `ns_controller` package.

## Flash

Hold **BOOTSEL** while plugging the Pico into a computer. It mounts as `RP2350` (Pico 2 W) or `RPI-RP2` (Pico W).
Copy the matching `ns_controller_fw.uf2` onto it and it reboots into the firmware.

## Test sequences (BOOTSEL)

Once the LED is solid (connected to the Switch), tap the BOOTSEL button:

| Presses | Sequence | Start on | What it does |
|---|---|---|---|
| 1 | `input-test` (19 s) | System Settings → Controllers and Sensors → Test Input Devices → Test Controller Buttons | Every button except HOME/CAPTURE one at a time (L+R together too), then each stick in a circle. B, MINUS and PLUS come last because they may leave the screen |
| 2 | `nxbt-demo` (25 s) | HOME → Controllers → Change Grip/Order | nxbt's own demo macro, verbatim: backs out to HOME, opens System Settings → Controllers and Sensors and circles each stick on the stick screen. **Switch 1 menu layout**; on a Switch 2 it will wander |

Any press while a sequence is playing stops it and releases everything. The log shows `test: playing ...` and
`test: ... done`. To add a sequence, drop an nxbt-format file into `sequences/` (number prefix = press count) and
rebuild.

## Logs (strongly recommended)

USB-serial adapter **set to 3.3 V**: Pico **GP0 (pin 1) → adapter RX**, Pico **GND (pin 3) → adapter GND**.
Do not connect VCC, because the Pico is powered by the Switch. Then run `picocom -b 115200 /dev/ttyUSB0` (or `tio`).

A healthy connection logs roughly this:

```
     0.012 ns-controller firmware 0.1.0-spike+<hash> (pico_w)
     0.240 usb: configured by host (mount #1)
     ...   rx [64] 80 01 ...      / tx [64] 81 01 00 03 ...   (status, handshake, baud, handshake)
     ...   usb 80 04: input reports on
     ...   sub 02: device info / sub 10: spi read 0x6000 ... / sub 30: player lights 0x01
     ...   test: playing 'input-test' (54 keyframes, 18.800 s)
    10.000 stats: mounted=1 suspended=0 reports=1 lights=0x01 rx=... replies=... inputs=... tests=...
```

The first line after a hang says `rebooted by WATCHDOG`.

## LED

| Pattern | Meaning |
|---|---|
| Fast blink (5 Hz) | Not configured by a host (no USB, or enumeration failed) |
| Slow blink (1 Hz) | Configured, waiting for the Switch to start input reports (handshake stuck?) |
| Solid | Input reports flowing; blinks off while a test holds a button |
| Short flash every 2 s | USB suspended (console asleep) |

## Player 1

Single-player games (FireRed/LeafGreen, ...) only read player 1. If your Joy-Cons are connected, the Pico joins as
player 2 and its presses are ignored even though the log shows them being sent. Fix: HOME -> Controllers -> Change
Grip/Order, then press L+R on the Pico (`nsctl press L R`) and A to confirm.

## Console test checklist

Before you start:
- On each console, turn on **System Settings → Controllers and Sensors → Pro Controller Wired Communication**.
- With the Joy-Cons, open **Controllers and Sensors → Test Input Devices → Test Controller Buttons**, where an A
  press is harmless and visible.
- Then plug in the Pico and wait for a solid LED.

For each setup (Switch 1 docked via dock USB-A, Switch 1 handheld via USB-C OTG adapter, Switch 2 docked,
Switch 2 handheld):

1. **Enumerates:** the LED goes from fast blink to slow blink to solid. Log shows `usb: configured`.
2. **Handshake:** log shows `input reports on`, the SPI reads, and `player lights`. A player LED is assigned on screen.
3. **Input:** press BOOTSEL once. Every button shows on the test screen exactly once, then both sticks circle.
   Nothing stays held afterwards. Repeat a few times. On a Switch 1, also try the nxbt demo (2 presses).
4. **Sleep/wake:** put the console to sleep for at least 1 minute, then wake it with the Joy-Cons. Log shows
   `suspend`, then `resume` (and possibly a fresh handshake). The input test works again afterwards.
5. **Replug:** unplug and replug the Pico while the console is on. It comes back without touching the console.
6. **Cold start:** power the console fully off, plug in the Pico, power on. It is picked up after boot.
7. **Dock/undock** (docked setups): undock and redock with the Pico connected. Pokémon Automation reports this
   can reset or hang Pico boards; note whether it recovers on its own.

Record the result and any odd log lines per setup. If the handshake stalls, the last `rx`/`tx` lines show where.
