"""`nsctl`: poke the Pico from a terminal.

nsctl status | ping | monitor | press A [B ...] [--hold 0.1] | reboot [--bootsel] | ports
"""

from __future__ import annotations

import glob
import os
import sys
import time

import click
from loguru import logger

from nsctl.client import LinkError, Pico
from nsctl.protocol import NEUTRAL, Keyframe, State, button_bits

PORT_PATTERNS = ("*Debug_Probe*", "*CP210*", "*FT232*", "*FTDI*", "*USB-Serial*", "*UART*")


def find_ports() -> list[str]:
    seen: list[str] = []
    for pattern in PORT_PATTERNS:
        for path in sorted(glob.glob(f"/dev/serial/by-id/{pattern}")):
            if path not in seen:
                seen.append(path)
    return seen


def default_port() -> str | None:
    env = os.environ.get("NSCTL_PORT")
    if env:
        return env
    ports = find_ports()
    return ports[0] if ports else None


@click.group()
@click.option("--port", default=default_port, show_default="NSCTL_PORT or the first Debug Probe / USB-serial adapter")
@click.option("--baud", default=1_000_000, show_default=True)
@click.option("-v", "--verbose", is_flag=True, help="Show Pico log lines and link debugging.")
@click.pass_context
def main(ctx: click.Context, port: str | None, baud: int, verbose: bool) -> None:
    """Talk to the ns-controller Pico firmware."""
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO", format="<level>{message}</level>")
    ctx.obj = {"port": port, "baud": baud}


def connect(ctx: click.Context, **kwargs) -> Pico:  # noqa: ANN003
    port = ctx.obj["port"]
    if not port:
        raise click.ClickException("no serial port found; pass --port or set NSCTL_PORT (see `nsctl ports`)")
    try:
        return Pico(port, ctx.obj["baud"], **kwargs)
    except LinkError as e:
        raise click.ClickException(f"{port}: {e}") from None
    except OSError as e:
        raise click.ClickException(f"{port}: {e} (permissions? `sudo usermod -aG dialout $USER`)") from None


@main.command()
def ports() -> None:
    """List likely serial ports."""
    for path in find_ports():
        click.echo(path)


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Firmware version and controller status."""
    with connect(ctx) as pico:
        st = pico.status()
        click.echo(
            f"firmware : {pico.info.text} (protocol {pico.info.proto}, up to {pico.info.max_keyframes} keyframes)"
        )
        click.echo(f"uptime   : {st.uptime_ms / 1000:.1f} s")
        click.echo(f"status   : {', '.join(st.names) or 'nothing connected'}")
        click.echo(f"ready    : {'yes' if st.ready else 'no (needs a Switch that finished the handshake, awake)'}")


@main.command()
@click.option("-n", "--count", default=20, show_default=True)
@click.pass_context
def ping(ctx: click.Context, count: int) -> None:
    """Round-trip time of the link."""
    with connect(ctx) as pico:
        times = []
        for _ in range(count):
            t = time.perf_counter()
            pico.ping()
            times.append((time.perf_counter() - t) * 1000)
        times.sort()
        click.echo(f"{count} pings: median {times[len(times) // 2]:.2f} ms, max {times[-1]:.2f} ms")


@main.command()
@click.pass_context
def monitor(ctx: click.Context) -> None:
    """Print the Pico's log and status changes until Ctrl-C."""
    pico = connect(
        ctx,
        on_log=lambda text: click.echo(text),
        on_status=lambda st: click.echo(f"[status] {', '.join(st.names) or '-'}"),
    )
    click.echo(f"# {pico.info.text}: {', '.join(pico.status().names)}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        pico.close()


@main.command()
@click.argument("buttons", nargs=-1, required=True)
@click.option("--hold", default=0.1, show_default=True, help="Seconds to hold.")
@click.option("--repeat", default=1, show_default=True)
@click.option("--gap", default=0.2, show_default=True, help="Seconds between repeats.")
@click.pass_context
def press(ctx: click.Context, buttons: tuple[str, ...], hold: float, repeat: int, gap: float) -> None:
    """Press buttons together (A B X Y L R ZL ZR PLUS MINUS HOME CAPTURE LSTICK RSTICK UP DOWN LEFT RIGHT)."""
    try:
        bits = button_bits(buttons)
    except ValueError as e:
        raise click.BadParameter(str(e)) from None
    keyframes, t = [], 0
    for _ in range(repeat):
        keyframes += [Keyframe(t, State(bits)), Keyframe(t + round(hold * 1e6), NEUTRAL)]
        t += round((hold + gap) * 1e6)
    with connect(ctx) as pico:
        if not pico.status().ready:
            click.echo("warning: the Pico isn't talking to an awake Switch; the press goes nowhere", err=True)
        done = pico.run(keyframes)
        click.echo(
            f"{'+'.join(b.upper() for b in buttons)} x{repeat}: {done.result} in {done.duration_us / 1000:.1f} ms"
        )


@main.command()
@click.option("--bootsel", is_flag=True, help="Reboot into the USB bootloader (for copying a .uf2).")
@click.pass_context
def reboot(ctx: click.Context, bootsel: bool) -> None:
    """Reboot the Pico."""
    pico = connect(ctx)
    pico.reboot(bootsel)
    click.echo("rebooting" + (" into the USB bootloader" if bootsel else ""))


if __name__ == "__main__":
    main()
