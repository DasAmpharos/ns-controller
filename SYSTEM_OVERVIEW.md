# Nintendo Switch Controller - System Overview

## ✅ Implemented Features

### Single Input/Macro at a Time
- **Enforced at server level**: Normal inputs are blocked when a macro is running
- **Check**: `handle_normal()` returns error if macro is active
- **Single client**: Only one TCP client can connect at a time

### Macro Features
- ✅ **Infinite loops**: Set `repeat=None` to run until stopped
- ✅ **Pause/Resume**: Separate pause event that doesn't stop the macro
- ✅ **Stop**: Stops macro and resets controller to neutral state
- ✅ **NXBT syntax**: Full support for NXBT macro format
- ✅ **Persistent storage**: Macros saved as JSON files with source text

### Streamlit UI Features
- ✅ **Create macros**: NXBT text input with syntax examples
- ✅ **Edit macros**: Load existing macros and update them
- ✅ **Delete macros**: Remove unwanted macros
- ✅ **Run macros**: Start with infinite or specific repeat count
- ✅ **Pause/Resume**: Control macro execution
- ✅ **Stop macros**: Halt running macros
- ✅ **Status display**: Real-time macro state (running/paused/stopped)
- ✅ **Auto-refresh**: UI updates every 2s when macro is running
- ✅ **Controller state**: View current button/stick positions

## Architecture

```
┌─────────────────┐
│   Streamlit UI  │ (Port 8501)
│   (client.py)   │
└────────┬────────┘
         │ TCP
         ▼
┌─────────────────┐
│   TCP Server    │ (Port 9000)
│   (server.py)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Controller    │ (/dev/hidg0)
│ (controller.py) │
└─────────────────┘
```

## Message Types

| Type | Description |
|------|-------------|
| `PING` | Health check |
| `NORMAL` | Single input (blocked if macro running) |
| `GET_STATE` | Get current controller state |
| `MACRO_START` | Start a macro (text or JSON) |
| `MACRO_STOP` | Stop running macro |
| `PAUSE_MACRO` | Pause without stopping |
| `RESUME_MACRO` | Resume paused macro |
| `LIST_MACROS` | Get all saved macro names |
| `LOAD_MACRO` | Load macro by name |
| `SAVE_MACRO` | Save macro (NXBT text or JSON) |
| `DELETE_MACRO` | Delete macro by name |
| `GET_MACRO_STATUS` | Check if macro is running/paused |

## NXBT Macro Syntax

### Basic Examples

```python
# Single button press
B 0.1s
0.1s

# Multiple buttons simultaneously
A B 0.5s

# Analog stick (X and Y from -100 to +100)
L_STICK@+000+100 0.5s

# Loops
LOOP 10
    A 0.1s
    0.1s
```

### Button Names
- `A`, `B`, `X`, `Y`
- `L`, `R`, `ZL`, `ZR`
- `PLUS`, `MINUS`
- `HOME`, `CAPTURE`
- `DPAD_UP`, `DPAD_DOWN`, `DPAD_LEFT`, `DPAD_RIGHT`
- `L_STICK_PRESS`, `R_STICK_PRESS`

## Usage

### Start Server (Normal Mode)
```bash
python -m ns_controller.cli --ui
```

### Start Server (Mock Mode for Testing)
```bash
python -m ns_controller.cli --mock --ui
```

### Disable UI (Headless)
```bash
python -m ns_controller.cli --no-ui
```

### Access UI
Open browser to: `http://<raspberry-pi-ip>:8501`

## Performance Optimizations for Pi Zero W

### CLI
- ✅ Optional UI with `--no-ui` flag
- ✅ Streamlit configured with:
  - `--server.headless true` (no auto-browser)
  - `--server.runOnSave false` (no file watcher)
  - `--browser.gatherUsageStats false` (no telemetry)
- ✅ Efficient signal handling (no busy-wait loops)
- ✅ Proper subprocess cleanup

### Server
- ✅ Single client enforcement (prevents resource exhaustion)
- ✅ Async I/O (non-blocking)
- ✅ Efficient pause implementation (event-based, not polling)

### Controller
- ✅ Asyncio for non-blocking operations
- ✅ Bitmask for button state (compact memory)

## Macro Execution Flow

1. **Start Macro**
   - Server checks if another macro is running → stops it
   - Creates `MacroRunner` instance
   - Spawns async task with repeat count (or `None` for infinite)

2. **During Execution**
   - Each step: set controller state → sleep duration → reset
   - Check `stop_event` before each step
   - Wait while `pause_event` is set
   - Loop continues until stopped or repeat count reached

3. **Stop Macro**
   - Set `stop_event`
   - Cancel task
   - Reset controller to neutral state

4. **Pause/Resume**
   - Pause: Set `pause_event` (loop waits)
   - Resume: Clear `pause_event` (loop continues)

## File Structure

```
ns_controller/
├── __init__.py
├── cli.py              # Entry point with CLI flags
├── server.py           # TCP server & MacroRunner
├── controller.py       # Controller state & HID interface
├── macro_parser.py     # NXBT syntax parser
├── client.py           # Streamlit UI
├── mock_server.py      # Mock for testing
├── macros/             # Saved macros (JSON)
│   └── example_spam_a.json
└── spi_rom_data/       # Switch calibration data
    ├── 0x60.bin
    └── 0x80.bin
```

## Testing

Run the test suite:
```bash
python test_macro_parser.py
```

Tests cover:
- Simple button presses
- Multiple buttons
- Stick input (neutral, directional, diagonal)
- Loops (simple and nested)
- Comments
- All button mappings

## Notes

- **Single input enforcement**: Prevents conflicts between manual inputs and macros
- **Infinite macros**: Perfect for farming/grinding scenarios
- **Pause feature**: Allows temporary suspension without losing progress
- **NXBT compatibility**: Existing NXBT macros should work with minimal changes
- **Storage format**: Macros stored with original source text for easy editing

