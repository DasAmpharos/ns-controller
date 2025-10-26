#!/usr/bin/env python3
"""
Simple example client for ns-controller

This script connects to the Raspberry Pi running ns-controller and
demonstrates sending button presses to the Nintendo Switch.

Usage:
    python example_client.py
    python example_client.py --host 192.168.1.100
    python example_client.py --host raspberrypi.local --port 9000
"""

import time
import argparse
from ns_controller.client import Client
from ns_controller.controller import ControllerState, Buttons


def main():
    parser = argparse.ArgumentParser(description="Simple ns-controller client example")
    parser.add_argument(
        "--host",
        default="raspberrypi.local",
        help="Hostname or IP address of the Raspberry Pi (default: raspberrypi.local)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="TCP port of ns-controller server (default: 9000)"
    )
    args = parser.parse_args()

    print("=================================")
    print("NS-Controller Example Client")
    print("=================================")
    print(f"Connecting to {args.host}:{args.port}...")
    print()

    client = Client(host=args.host, port=args.port)

    try:
        # Test connection with ping
        print("[1/6] Testing connection...")
        response = client.ping()
        print(f"  ✓ Server responded: {response}")
        print()

        # Example 1: Press A button
        print("[2/6] Pressing L+R button...")
        state = ControllerState()
        state.set_button(Buttons.L, True)
        state.set_button(Buttons.R, True)
        client.send_state(state, down=0.1, up=0.1)
        print("  ✓ A button pressed for 0.1s")
        time.sleep(0.5)
        print()

        # Example 2: Press B button
        print("[3/6] Pressing B button...")
        state = ControllerState()
        state.set_button(Buttons.B, True)
        client.send_state(state, down=0.1, up=0.1)
        print("  ✓ B button pressed for 0.1s")
        time.sleep(0.5)
        print()

        # Example 3: Press multiple buttons simultaneously
        print("[4/6] Pressing A + B together...")
        state = ControllerState()
        state.set_button(Buttons.A, True)
        state.set_button(Buttons.B, True)
        client.send_state(state, down=0.2, up=0.1)
        print("  ✓ A + B pressed for 0.2s")
        time.sleep(0.5)
        print()

        # Example 4: D-Pad navigation
        print("[5/6] Navigating with D-Pad (Down, Right, Up, Left)...")
        for button in [Buttons.DPAD_DOWN, Buttons.DPAD_RIGHT, Buttons.DPAD_UP, Buttons.DPAD_LEFT]:
            state = ControllerState()
            state.set_button(button, True)
            client.send_state(state, down=0.1, up=0.1)
            print(f"  ✓ Pressed {button.name}")
            time.sleep(0.3)
        print()

        # Example 5: Run a simple macro
        print("[6/6] Running a simple macro (A spam)...")
        macro = """
# Spam A button 5 times
LOOP 5
    A 0.1s
    0.1s
"""
        client.start_macro(macro)
        print("  ✓ Macro started")
        print("  (Running 5x A button presses...)")

        # Wait for macro to complete
        time.sleep(1.2)  # 5 * (0.1 + 0.1) + buffer

        # Check macro status
        status = client.get_macro_status()
        if status and not status.get("running"):
            print("  ✓ Macro completed")
        print()

        print("=================================")
        print("All examples completed!")
        print("=================================")
        print()
        print("Try these commands:")
        print("  - Press HOME: state.press(Buttons.HOME)")
        print("  - Press PLUS: state.press(Buttons.PLUS)")
        print("  - Move stick: state.ls = StickPosition(x=100, y=0)")
        print()

    except ConnectionRefusedError:
        print(f"✗ Error: Could not connect to {args.host}:{args.port}")
        print()
        print("Make sure:")
        print("  1. The Raspberry Pi is powered on")
        print("  2. ns-controller service is running")
        print("  3. You're on the same network")
        print("  4. Correct hostname/IP address")
        print()
        print("Check status on Pi:")
        print("  sudo systemctl status ns-controller")
        return 1

    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

