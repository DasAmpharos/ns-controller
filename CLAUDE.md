# ns-controller: Pico controller firmware + nsctl

Part of Dylan's Nintendo Switch shiny-hunting automation. A **brain** (Linux box with a capture card, running vision
and hunt scripts: the `ns-shiny-hunter` repo) drives this repo's **controller emulator**: a Raspberry Pi Pico 2 W
that appears to the Switch as a wired Pro Controller. The old setup sent each press and release over Wi-Fi as
separate gRPC calls; dropped or late packets caused missed and stuck inputs. This repo replaces it.

| Path | What it is |
|---|---|
| `firmware/` | C firmware (Pico SDK 2.2.0 + TinyUSB): Pro Controller over USB, framed serial link, keyframe player. Build, flash and test commands in `firmware/README.md` |
| `nsctl/` | Python package: the brain side of the link (`client.py`, `protocol.py`) and the `nsctl` CLI (`status`, `ping`, `press`, `monitor`, `reboot`) |
| `docs/protocol.md` | The brain ↔ Pico serial protocol (v1), as implemented |
| `ns_controller/`, `bin/`, root `pyproject.toml` | The old Python gRPC server for the Pi Zero USB gadget (to be removed, see open items) |

ns-shiny-hunter depends on nsctl as a uv git dependency (`subdirectory = "nsctl"`, branch `main`, commit pinned by
its `uv.lock`). After changing nsctl: push here, then `uv lock --upgrade-package nsctl` in ns-shiny-hunter.

## Design (settled; don't re-litigate without a reason)

- **Controller = Raspberry Pi Pico 2 W** (any RP2040/RP2350 Pico builds), C firmware, Pro Controller over USB
  (VID `057e`, PID `2009`). The Pico's Wi-Fi is not used.
- **Brain ↔ Pico link = UART** at 1 Mbaud, framed with COBS + CRC16. No network, no gRPC/protobuf.
- **Macros are compiled on the brain into a flat keyframe timeline**; the Pico only plays it on its hardware timer.
  Everything timing-critical is on the Pico, all logic in Python on the brain.
- **Reliability rules on the Pico:** safety release after 2 s of silence (a dead brain can't leave a button held),
  hardware watchdog, one macro at a time, full states only (a resend can't double a press), `BOOT` on every reset.
- **Fallback:** if Pico emulation ever fails on a console, a Pi Zero W runs a small Go daemon speaking the same
  serial protocol over GPIO UART and writing `/dev/hidg0` (start from branch `go-server`). Brain code wouldn't change.

## Hardware

- Pico 2 W: firmware build `-DPICO_BOARD=pico2_w` → `firmware/build-pico2w/`. Powered by, and plugged into, the
  Switch dock's USB.
- Raspberry Pi Debug Probe: its UART is the link (Pico GP0 TX → probe RX, GP1 RX ← probe TX, GND; never VCC), seen
  on the brain as `/dev/serial/by-id/usb-Raspberry_Pi_Debug_Probe__CMSIS-DAP__E665D0C59B5F1031-if01`. Its SWD side
  can flash the Pico. Firmware logs travel on the same link (`LOG` frames; `nsctl monitor` prints them).
- Console: **Switch 2** (confirmed 2026-11-13). Switch 1 support is assumed but not yet tested with the Pico.
- The brain is the homelab ThinkCentre M715q (`homelab.lan`); its deploy installs `/usr/local/bin/nsctl` (refuses
  while a hunt is using the port).

## Decisions log

- 2026-11-02: stale branches archived as tags: `archive/presplit-brain` (`8af2cc5`, last commit with the old brain
  code), `archive/python-server` (`c09f524`), `archive/go-server` (`25bf2ab`), `archive/{bdsp,frame-refactor,legacy,
  sync,usb-gadget,wip}`. Remote branches: `main`, `go-server` (the Go port of the server, the Zero W fallback base).
- 2026-11-02: Pico SDK pinned to 2.2.0, installed at `~/.pico-sdk/sdk/2.2.0` (only the `tinyusb` and `cyw43-driver`
  submodules); `firmware/CMakeLists.txt` finds it there. Renovate watches the pin.
- 2026-11-02: the firmware's handshake deviates from the Python/Go ports in two places: unknown UART subcommands get
  a plain ACK, and unmapped SPI reads return 0xFF. Everything else matches byte for byte (golden vectors recorded
  from the Python `Controller`, `firmware/test/`).
- 2026-11 (Phase 2): the serial protocol, keyframe player, safety release and watchdog are implemented and drive
  the user's Switch 2 in production hunts. nsctl replies return as soon as they arrive (0.6 ms round trip).
- 2026-11-23: the `firmware` branch was fast-forwarded into `main`; Renovate configured (`renovate.json`: weekly
  grouped minor/patch, lock file maintenance, Pico SDK custom manager). The protocol spec moved here from the
  ns-automation coordination repo (now retired) and was corrected to match the code.

## Open items

- Remove the gRPC era from `main`: `ns_controller/`, protos, `bin/install.sh` + USB gadget script, the root
  `pyproject.toml`/`uv.lock` (ns-shiny-hunter's `legacy/` still uses the gRPC client via tag `archive/presplit-brain`,
  which stays). Reusable bits are already ported: the descriptor hex, handshake and SPI blobs live in `firmware/src/`.
- Update the docs: `firmware/README.md` still describes the Phase 1 spike ("no brain link yet"); the root `README.md`,
  `INSTALL.md` and `.github/copilot-instructions.md` describe the old server (some of it never existed: TCP port
  9000, FastAPI, poetry).
- Test on a Switch 1, including sleep/wake and dock vs. direct.
- Timing precision for GBA RNG macros: align keyframe playback to USB host polls so each edge lands in a predictable
  poll; compare `bInterval` 1 vs 8 on both consoles.
- Burn-in: press every button on **System Settings → Controllers → Test Input Devices** and verify via the capture
  card, then a 24 h reset loop.
- Gamepad passthrough in the nsctl CLI (`nsctl gamepad /dev/input/eventX`) was planned; not built.

## Working rules

- Ask before pushing, force-pushing, deleting branches, or creating/changing anything on GitHub.
- Python: uv, ruff (line length 120, rules E,F,I,B,UP,C90), `loguru` in library code, not `print()`.
- Keep `docs/protocol.md` in step with `firmware/src/link.h` and `nsctl/nsctl/protocol.py`; bump the protocol
  version on both sides for incompatible changes.
- Record new decisions in the log above.
