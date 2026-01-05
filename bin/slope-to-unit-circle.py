import math

import click


@click.command()
@click.argument("slope_x", type=int)
@click.argument("slope_y", type=int)
def slope_to_unit_circle(slope_x: int, slope_y: int):
    """
    Convert slope pixel coordinates to normalized circle coordinates.
    The slope line from center to edge is treated as the radius.

    Args:
        slope_x: Horizontal pixel position (0 to width)
        slope_y: Vertical pixel position (0 to height)

    Returns:
        (x, y) tuple where values are in range [-1, 1] on unit circle
    """
    magnitude = math.sqrt(slope_x ** 2 + slope_y ** 2)
    if magnitude == 0:
        raise ValueError("Cannot normalize a zero-length vector.")
    ux, uy = slope_x / magnitude, slope_y / magnitude
    click.echo(f"Unit circle coordinates: ({ux:.3f}, {uy:.3f})")


if __name__ == '__main__':
    slope_to_unit_circle()
