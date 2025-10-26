import asyncio
import json
import struct
from asyncio import StreamReader, StreamWriter
from enum import IntEnum
from pathlib import Path
from typing import Any

from .controller import Buttons, Controller, ControllerState, StickPosition
from .macro_parser import parse_macro

STATE_STRUCT = struct.Struct("20B4i2d")


def unpack_state(data: bytes) -> tuple[ControllerState, float, float]:
    unpacked = STATE_STRUCT.unpack(data)
    buttons = 0
    for i, pressed in enumerate(unpacked[:18]):
        if pressed:
            buttons |= 1 << i
    ls_x, ls_y, rs_x, rs_y = unpacked[18:22]
    if unpacked[22]:
        buttons |= 1 << Buttons.LS.value
    if unpacked[23]:
        buttons |= 1 << Buttons.RS.value
    down = unpacked[24]
    up = unpacked[25]
    state = ControllerState(
        buttons=buttons,
        ls=StickPosition(x=ls_x, y=ls_y),
        rs=StickPosition(x=rs_x, y=rs_y),
    )
    return state, down, up


class Macro:
    def __init__(self, steps: list[dict[str, Any]]):
        self.steps: list[dict[str, Any]] = steps


class MacroRunner:
    def __init__(self, controller: Controller):
        self.controller: Controller = controller
        self.stop_event: asyncio.Event = asyncio.Event()
        self.pause_event: asyncio.Event = asyncio.Event()
        self.task: asyncio.Task | None = None

    async def run(self, macro: Macro, repeat: int | None = None) -> None:
        self.stop_event.clear()
        self.pause_event.clear()
        count = 0
        # Run indefinitely if repeat is None, otherwise run repeat times
        while repeat is None or count < repeat:
            for step in macro.steps:
                # Check if we should stop
                if self.stop_event.is_set():
                    # Reset controller to neutral state
                    self.controller.state = ControllerState()
                    return

                # Wait while paused
                while self.pause_event.is_set():
                    if self.stop_event.is_set():
                        self.controller.state = ControllerState()
                        return
                    await asyncio.sleep(0.01)

                # Execute step
                previous_state = self.controller.state
                self.controller.state = step["state"]
                await asyncio.sleep(step["duration"])
                self.controller.state = previous_state
            count += 1

    def start(self, macro: Macro, repeat: int | None = None) -> None:
        self.task = asyncio.create_task(self.run(macro, repeat))

    def stop(self) -> None:
        self.stop_event.set()
        if self.task:
            self.task.cancel()

    def pause(self) -> None:
        self.pause_event.set()

    def resume(self) -> None:
        self.pause_event.clear()

    def is_running(self) -> bool:
        return self.task is not None and not self.task.done()

    def is_paused(self) -> bool:
        return self.pause_event.is_set()


class MessageType(IntEnum):
    PING = 0
    NORMAL = 1
    GET_STATE = 2
    MACRO_START = 3
    MACRO_STOP = 4
    PAUSE_MACRO = 5
    RESUME_MACRO = 6
    LIST_MACROS = 7
    LOAD_MACRO = 8
    SAVE_MACRO = 9
    DELETE_MACRO = 10
    GET_MACRO_STATUS = 11


class Server:
    MACRO_DIR = "macros"

    def __init__(self, controller: Controller):
        self.controller: Controller = controller
        self.macro_runner: MacroRunner | None = None
        self.active_client: bool = False

    async def client_connected(self, reader: StreamReader, writer: StreamWriter) -> None:
        if self.active_client:
            writer.write(b"ERR:Only one client allowed")
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return
        self.active_client = True
        await self.handle_client(reader, writer)

    async def handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        try:
            while True:
                header = await reader.readexactly(1)
                msg_type = MessageType(header[0])
                match msg_type:
                    case MessageType.PING:
                        await self.handle_ping(writer)
                    case MessageType.NORMAL:
                        await self.handle_normal(reader, writer)
                    case MessageType.GET_STATE:
                        await self.handle_get_state(writer)
                    case MessageType.MACRO_START:
                        await self.handle_macro_start(reader, writer)
                    case MessageType.MACRO_STOP:
                        await self.handle_macro_stop(writer)
                    case MessageType.PAUSE_MACRO:
                        await self.handle_pause_macro(writer)
                    case MessageType.RESUME_MACRO:
                        await self.handle_resume_macro(writer)
                    case MessageType.LIST_MACROS:
                        await self.handle_list_macros(writer)
                    case MessageType.LOAD_MACRO:
                        await self.handle_load_macro(reader, writer)
                    case MessageType.SAVE_MACRO:
                        await self.handle_save_macro(reader, writer)
                    case MessageType.DELETE_MACRO:
                        await self.handle_delete_macro(reader, writer)
                    case MessageType.GET_MACRO_STATUS:
                        await self.handle_get_macro_status(writer)
                    case _:
                        await self.handle_unknown(writer)
        except asyncio.IncompleteReadError:
            pass
        except Exception as e:
            writer.write(b"ERR:" + str(e).encode())
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            self.active_client = False

    async def handle_ping(self, writer: StreamWriter) -> None:
        writer.write(b"PONG")
        await writer.drain()

    async def handle_normal(self, reader: StreamReader, writer: StreamWriter) -> None:
        # Check if a macro is currently running
        if self.macro_runner and self.macro_runner.is_running():
            writer.write(b"ERR:Macro is running, stop it first")
            await writer.drain()
            return

        data = await reader.readexactly(STATE_STRUCT.size)
        new_state, down, up = unpack_state(data)
        previous_state = self.controller.state
        self.controller.state = new_state
        await asyncio.sleep(down)
        self.controller.state = previous_state
        await asyncio.sleep(up)
        writer.write(b"OK")
        await writer.drain()

    async def handle_macro_start(self, reader: StreamReader, writer: StreamWriter) -> None:
        macro_json_len_bytes = await reader.readexactly(4)
        macro_json_len = int.from_bytes(macro_json_len_bytes, "big")
        macro_json = await reader.readexactly(macro_json_len)
        macro_data = json.loads(macro_json.decode())

        # Parse macro text if it's a string, otherwise use steps from dict
        if isinstance(macro_data, str):
            # It's NXBT macro text
            parsed_steps = parse_macro(macro_data)
            steps = []
            for macro_step in parsed_steps:
                steps.append({
                    "state": macro_step.state,
                    "duration": macro_step.duration
                })
            repeat = None  # Default to infinite for text macros
        else:
            # It's a dict with steps and optional repeat
            steps = []
            for step in macro_data["steps"]:
                if "raw" in step:
                    state, down, up = unpack_state(bytes.fromhex(step["raw"]))
                    # Combine down and up into single duration
                    steps.append({"state": state, "duration": down + up})
                elif isinstance(step, dict) and "state" in step:
                    # Already in correct format
                    steps.append(step)
                else:
                    # Convert old format (down/up) to new format (duration)
                    duration = step.get("down", 0) + step.get("up", 0)
                    steps.append({"state": step["state"], "duration": duration})
            repeat = macro_data.get("repeat")

        # Stop any currently running macro
        if self.macro_runner and self.macro_runner.is_running():
            self.macro_runner.stop()
            await asyncio.sleep(0.1)  # Give it time to stop

        self.macro_runner = MacroRunner(self.controller)
        self.macro_runner.start(Macro(steps), repeat)
        writer.write(b"MACRO_STARTED")
        await writer.drain()

    async def handle_macro_stop(self, writer: StreamWriter) -> None:
        if self.macro_runner:
            self.macro_runner.stop()
            self.macro_runner = None
        writer.write(b"MACRO_STOPPED")
        await writer.drain()

    async def handle_pause_macro(self, writer: StreamWriter) -> None:
        if self.macro_runner and self.macro_runner.is_running() and not self.macro_runner.is_paused():
            self.macro_runner.pause()
            writer.write(b"MACRO_PAUSED")
        else:
            writer.write(b"ERR:No macro running or already paused")
        await writer.drain()

    async def handle_resume_macro(self, writer: StreamWriter) -> None:
        if self.macro_runner and self.macro_runner.is_running() and self.macro_runner.is_paused():
            self.macro_runner.resume()
            writer.write(b"MACRO_RESUMED")
        else:
            writer.write(b"ERR:No paused macro")
        await writer.drain()

    async def handle_list_macros(self, writer: StreamWriter) -> None:
        macro_dir = Path(__file__).parent / self.MACRO_DIR
        macro_dir.mkdir(exist_ok=True)
        macros = [f.stem for f in macro_dir.glob("*.json")]
        writer.write(json.dumps(macros).encode())
        await writer.drain()

    async def handle_load_macro(self, reader: StreamReader, writer: StreamWriter) -> None:
        macro_name_len_bytes = await reader.readexactly(2)
        macro_name_len = int.from_bytes(macro_name_len_bytes, "big")
        macro_name = (await reader.readexactly(macro_name_len)).decode()
        macro_path = Path(__file__).parent / self.MACRO_DIR / f"{macro_name}.json"
        try:
            macro_json = macro_path.read_text()
            writer.write(macro_json.encode())
        except FileNotFoundError:
            writer.write(b"ERR:Macro not found")
        await writer.drain()

    async def handle_save_macro(self, reader: StreamReader, writer: StreamWriter) -> None:
        macro_name_len_bytes = await reader.readexactly(2)
        macro_name_len = int.from_bytes(macro_name_len_bytes, "big")
        macro_name = (await reader.readexactly(macro_name_len)).decode()
        macro_json_len_bytes = await reader.readexactly(4)
        macro_json_len = int.from_bytes(macro_json_len_bytes, "big")
        macro_text = (await reader.readexactly(macro_json_len)).decode()

        # Try to parse as NXBT macro text syntax
        try:
            parsed_steps = parse_macro(macro_text)
            # Convert to storable format
            steps = []
            for macro_step in parsed_steps:
                steps.append({
                    "state": {
                        "buttons": macro_step.state.buttons,
                        "ls": {"x": macro_step.state.ls.x, "y": macro_step.state.ls.y},
                        "rs": {"x": macro_step.state.rs.x, "y": macro_step.state.rs.y}
                    },
                    "duration": macro_step.duration
                })
            macro_obj = {"steps": steps, "source": macro_text}
            macro_json = json.dumps(macro_obj, indent=2)
        except Exception:
            # Not NXBT text, try as JSON
            try:
                macro_obj = json.loads(macro_text)
                macro_json = json.dumps(macro_obj, indent=2)
            except Exception:
                writer.write(b"ERR:Invalid macro format")
                await writer.drain()
                return

        # Save to file
        macro_dir = Path(__file__).parent / self.MACRO_DIR
        macro_dir.mkdir(exist_ok=True)
        macro_path = macro_dir / f"{macro_name}.json"
        macro_path.write_text(macro_json)

        writer.write(b"MACRO_SAVED")
        await writer.drain()

    async def handle_delete_macro(self, reader: StreamReader, writer: StreamWriter) -> None:
        macro_name_len_bytes = await reader.readexactly(2)
        macro_name_len = int.from_bytes(macro_name_len_bytes, "big")
        macro_name = (await reader.readexactly(macro_name_len)).decode()
        macro_path = Path(__file__).parent / self.MACRO_DIR / f"{macro_name}.json"
        try:
            macro_path.unlink()
            writer.write(b"MACRO_DELETED")
        except FileNotFoundError:
            writer.write(b"ERR:Macro not found")
        await writer.drain()

    async def handle_get_macro_status(self, writer: StreamWriter) -> None:
        status = {
            "running": self.macro_runner.is_running() if self.macro_runner else False,
            "paused": self.macro_runner.is_paused() if self.macro_runner else False
        }
        writer.write(json.dumps(status).encode())
        await writer.drain()

    async def handle_get_state(self, writer: StreamWriter) -> None:
        state = {
            "buttons": self.controller.state.buttons,
            "ls": {"x": self.controller.state.ls.x, "y": self.controller.state.ls.y},
            "rs": {"x": self.controller.state.rs.x, "y": self.controller.state.rs.y}
        }
        writer.write(json.dumps(state).encode())
        await writer.drain()

    async def handle_unknown(self, writer: StreamWriter) -> None:
        writer.write(b"ERR:Unknown message type")
        await writer.drain()
