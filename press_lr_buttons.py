#!/usr/bin/env python3
"""
Simple script to press L and R shoulder buttons on Nintendo Switch

Usage:
    python press_lr_buttons.py
    python press_lr_buttons.py --host 192.168.1.100
"""

import argparse
import time

from ns_controller.client import Client
from ns_controller.protocol import ControllerInput


def main():
    parser = argparse.ArgumentParser(description="Press L and R shoulder buttons")
    parser.add_argument(
        "--host",
        default="raspberrypi.local",
        help="Hostname or IP of the Raspberry Pi (default: raspberrypi.local)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="TCP port (default: 9000)"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.5,
        help="How long to hold the buttons in seconds (default: 0.1)"
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=1,
        help="How long to wait after releasing in seconds (default: 0.1)"
    )
    args = parser.parse_args()

    print(f"Connecting to {args.host}:{args.port}...")

    try:
        client = Client(host=args.host, port=args.port)

        # Test connection
        response = client.ping()
        print(f"✓ Server responded: {response}")
        print()

        # Press L button
        print(f"Pressing L+R buttons for {args.duration}s...")
        controller_input = ControllerInput()
        controller_input.buttons.l = True
        controller_input.buttons.r = True
        client.send_input(controller_input, down=args.duration, up=args.wait)
        print("✓ L+R buttons pressed")
        time.sleep(0.5)

        print()
        print("Done! All button presses completed successfully.")

    except ConnectionRefusedError:
        print(f"✗ Error: Could not connect to {args.host}:{args.port}")
        print()
        print("Make sure:")
        print("  1. The Raspberry Pi is powered on")
        print("  2. ns-controller service is running:")
        print("     ssh pi@raspberrypi.local")
        print("     sudo systemctl status ns-controller")
        print("  3. You're on the same network")
        return 1

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

