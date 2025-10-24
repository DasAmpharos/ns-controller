# ns-controller

A Python library and API for controlling a Nintendo Switch controller via HID. Provides a FastAPI REST interface and CLI for emulating button presses, DPad, and stick movements.

## Features
- Control Nintendo Switch controller state from Python
- REST API for updating controller state
- Emulate button presses, DPad, and analog stick movements
- CLI for quick usage

## Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management.

```fish
# Clone the repository
$ git clone <repo-url>
$ cd ns-controller-python

# Install dependencies
$ poetry install
```

## Usage

### CLI

Run the CLI to start the controller interface:

```fish
$ poetry run ns-controller-python --filepath /dev/hidg0
```

- `--filepath`: Path to the HID device (default: `/dev/hidg0`).

### API

The CLI starts a FastAPI server with the following endpoint:

- `POST /update`
  - Body: JSON representing the new controller state (see below)
  - Query params: `down` (float, default 0.1), `up` (float, default 0.1)

Example request:
```json
{
  "buttons": {"a": true, "b": false, ...},
  "dpad": {"up": false, "down": true, ...},
  "sticks": {
    "ls": {"x": 0, "y": 0, "pressed": false},
    "rs": {"x": 0, "y": 0, "pressed": false}
  }
}
```

The controller will update to the new state for `down` seconds, then revert for `up` seconds.

## Development

- All source code is in `ns_controller/`.
- Main entry point: `ns_controller/cli.py`
- Controller logic: `ns_controller/controller.py`
- Dependencies: fastapi, loguru, click, pydantic

## Contributing

Pull requests and issues are welcome! Please open an issue to discuss major changes.

## License

MIT License

## Contact

Author: Dylan Meadows (<dylmeadows@gmail.com>)

