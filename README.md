nf# ns-controller

A Python library and API for controlling a Nintendo Switch controller via HID. Provides a FastAPI REST interface and CLI for emulating button presses, DPad, and stick movements.

## Features

- **USB HID Emulation**: Emulates a Nintendo Switch Pro Controller over USB
- **Binary TCP Protocol**: Fast and efficient controller state updates
- **Streamlit Web UI**: Control the Switch from any device on your network
- **Macro Support**: Write macros using NXBT syntax with loop support
- **Macro Management**: Save, load, and organize macros via UI or API
- **Asyncio-based**: High performance, non-blocking server architecture
- **Auto-start Service**: Runs automatically on Raspberry Pi boot
- **Mock Mode**: Test without hardware for development

## Installation

### Raspberry Pi (Recommended)

For Raspberry Pi installation with automatic USB gadget setup and systemd service:

```bash
# Clone the repository
git clone <repo-url> ns-controller
cd ns-controller

# Run the install script
sudo ./install.sh

# Reboot
sudo reboot
```

After reboot, the controller will be ready to use. Access the Streamlit UI at `http://<pi-ip>:8501`

See [INSTALL.md](INSTALL.md) for detailed installation instructions, troubleshooting, and configuration options.

### Manual/Development Installation

This project uses pip and virtual environments for dependency management.

```bash
# Clone the repository
git clone <repo-url> ns-controller
cd ns-controller

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### After Installation

If you used the install script, the service starts automatically on boot. Simply:

1. Connect your Raspberry Pi to the Nintendo Switch via USB
2. Access the Streamlit UI from any browser: `http://<pi-ip>:8501`
3. Use the UI to control the Switch or manage macros

### Manual Run

Run the server manually:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the server
python -m ns_controller.cli --filepath /dev/hidg0 --host 0.0.0.0 --port 9000
```

Options:
- `--filepath`: Path to the HID device (default: `/dev/hidg0`)
- `--host`: TCP server host (default: `0.0.0.0`)
- `--port`: TCP server port (default: `9000`)
- `--mock`: Run in mock mode (no HID device required)

### TCP Protocol

The server uses a binary protocol over TCP on port 9000. See the client implementation in `ns_controller/client.py` for details.

Message types supported:
- `PING/PONG`: Health check
- `NORMAL`: Send controller state
- `GET_STATE`: Get current controller state
- `MACRO_START/STOP`: Control macro execution
- `PAUSE_MACRO/RESUME_MACRO`: Pause/resume running macros
- `LIST_MACROS/LOAD_MACRO/SAVE_MACRO/DELETE_MACRO`: Macro management

### Streamlit UI

The Streamlit UI provides:
- Button controls for all Pro Controller buttons
- Analog stick controls
- Macro editor with NXBT syntax support
- Macro management (save, load, delete)
- Macro execution controls (start, stop, pause, resume)

## Development

- All source code is in `ns_controller/`.
- Main entry point: `ns_controller/cli.py`
- Controller logic: `ns_controller/controller.py`
- Dependencies: fastapi, loguru, click, pydantic

## Dependency updates

Renovate keeps both uv projects (`uv.lock` and `nsctl/uv.lock`), the Pico SDK version in
`firmware/CMakeLists.txt` and the GitHub Actions pins current, with **no pull requests**. It runs daily from
`.github/workflows/renovate.yml` and starts updates on Saturdays: routine Python updates share one
`renovate/...` branch, and releases must be a week old. It merges a branch into `main` itself after CI passes
there. CI covers nsctl's lint, both locked installs, the firmware host tests, and the firmware built for the
Pico W and Pico 2 W. An update that fails stays on its branch and shows on the Dependency Dashboard issue.
Settings are in `renovate.json5`.

A new Pico SDK opens a pull request instead: install that version under `~/.pico-sdk/sdk/` before merging it,
since the local build looks for the SDK there.

One-time setup: the workflow needs the repository secret `RENOVATE_TOKEN`, a fine-grained personal access
token (github.com/settings/personal-access-tokens) with access to this repository and **Contents**,
**Pull requests**, **Issues**, **Commit statuses** and **Workflows** set to *Read and write*. One token
can serve every repository that runs Renovate (homelab, gmail-cleanup and the others): give it access to
this one, then `gh secret set RENOVATE_TOKEN --repo DasAmpharos/ns-controller` and run the workflow once from the
Actions tab. The token expires (at most a year): when the workflow starts failing, make a new one and set it
again.

## Contributing

Pull requests and issues are welcome! Please open an issue to discuss major changes.

## License

MIT License

## Contact

Author: Dylan Meadows (<dylmeadows@gmail.com>)

