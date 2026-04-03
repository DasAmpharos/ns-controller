# Copilot Instructions

## Project Overview

`ns-controller` emulates a Nintendo Switch Pro Controller over USB HID (via `/dev/hidg0` on a Raspberry Pi), controlled by a gRPC server. Automation scripts use `NsControllerClient` to send macro sequences for tasks like shiny hunting in Pokémon games.

## Commands

```bash
# Install dependencies
poetry install

# Run the gRPC server (on the Pi)
poetry run python -m ns_controller.server [--mock] [--hid-path /dev/hidg0] [--port 50051] [--gamepad /dev/input/eventX]

# Run the state configurator UI (Streamlit, typically on the capture machine)
poetry run streamlit run ns_shiny_hunter/tools/configurator.py

# Regenerate protobuf files after editing protos/ns_controller.proto
make proto

# Lint / format
poetry run ruff check .
poetry run ruff format .
```

There is no automated test suite. `bin/test.py` is a manual frame-analysis sanity check for OpenCV/pytesseract.

## Architecture

### Data flow

```
Automation script (main.py or ns_shiny_hunter/**/)
  → NsControllerClient (ns_controller/client.py)
    → NsControllerTransport  (two implementations)
        NsControllerNativeTransport  – direct HID write on the Pi
        NsControllerGrpcTransport    – sends gRPC calls to a remote server
          → NsControllerServicer (ns_controller/server.py)
            → EnhancedControllerState (ns_controller/state.py)
              → Controller (ns_controller/controller.py)
                → /dev/hidg0 (USB HID gadget, appears as Pro Controller)
```

### Key modules

| Module | Role |
|---|---|
| `ns_controller/server.py` | gRPC servicer + Click CLI entry point |
| `ns_controller/controller.py` | USB HID writer; spawns three threads (counter 5 ms, comm, input-report 8 ms keepalive) |
| `ns_controller/state.py` | `EnhancedControllerState` wraps protobuf `ControllerState`; mutations fire an immediate HID report via callback |
| `ns_controller/client.py` | `NsControllerClient` (context manager) + fluent `MacroBuilder` |
| `ns_controller/macro_executor.py` | Executes macros server-side with monotonic-clock scheduling |
| `ns_controller/gamepad_input.py` | Reads a physical gamepad via `evdev` and forwards inputs as controller state |
| `ns_shiny_hunter/` | Game-specific automation scripts (BDSP, Legends ZA) + frame grabber/analyser |
| `ns_shiny_hunter/roi.py` | `ROI` dataclass — resolution-agnostic (relative 0.0–1.0); use `from_pixels`/`to_pixels` |
| `ns_shiny_hunter/tools/configurator.py` | Streamlit UI for defining states visually and exporting `frames.py` / `config.json` |
| `protos/ns_controller.proto` | Single source of truth for gRPC service and all message types |
| `ns_controller/pb/` | Generated files – **do not edit by hand**; regenerate with `make proto` |

### Macro timing

`MacroExecutor` uses `time.monotonic()` with a hybrid sleep (coarse + spin-wait) to achieve <1 ms scheduling accuracy. Named marks (`AddMark` / `WaitUntil`) allow branching relative to arbitrary reference points.

## Conventions

### Linting (Ruff, configured in `pyproject.toml`)
- Line length: **120**
- Python target: **3.11**
- Active rule sets: `E`, `F`, `I` (imports), `B` (bugbear), `UP` (pyupgrade), `C90` (complexity ≤ 20)

### Patterns
- **Transport abstraction**: new input backends implement `NsControllerTransport` in `client_transport.py`.
- **MacroBuilder is fluent**: chain calls (`builder.click(...).wait(...).hold(...)`) and pass the built `Macro` proto to `client.run_macro()`.
- **Button state is a bitmask**: `Button` enum values are bit positions inside a `uint64`; don't store button state as separate booleans.
- **Stick positions**: `Position(x, y)` with range −1.0 – 1.0 (centre = 0.0).
- **Logging**: use `loguru`'s `logger` everywhere; never `print()` in library code.
- **Threading coordination**: use `threading.Event` for cancellation/shutdown signals, not busy-loops or `time.sleep`-polling.
- **Context managers**: `NsControllerClient` is a context manager; always use `with` to ensure cleanup.
- **ROI coordinates**: always store as `ROI` (relative 0.0–1.0 via `ns_shiny_hunter/roi.py`), not as hardcoded pixel tuples. Scale to pixels at use-time with `roi.to_pixels(frame_w, frame_h)`.
- **New shiny-hunter scripts**: subclass the pattern used in `ns_shiny_hunter/legends_za/` — a `run()` method that loops, calls `client.run_macro()`, then uses `FrameGrabber` + `Frame` to check the result.

## Adding a New Script

1. **Run the configurator** on the capture machine: `poetry run streamlit run ns_shiny_hunter/tools/configurator.py`
2. Connect to your video source (device index or path/URL), freeze a frame for each game state you need to detect.
3. Draw ROI rectangles, choose a pipeline preset (Text/Dialog is the default), capture the reference image, tune the threshold until the live match score is stable.
4. Export as **Python** (produces `frames.py` + `refs/*.jpg`) or **JSON** (`config.json` + `refs/*.jpg`).
5. Drop the export into your new script's directory and implement the `run()` loop against the generated `ReferenceFrameEnum`.
