import click
import numpy as np


@click.command()
@click.argument("slope_x", type=int)
@click.argument("slope_y", type=int)
def slope_to_circle_coords(slope_x: int, slope_y: int):
    """
    Convert slope pixel coordinates to normalized circle coordinates.
    The slope line from center to edge is treated as the radius.

    Args:
        slope_x: Horizontal pixel position (0 to width)
        slope_y: Vertical pixel position (0 to height)

    Returns:
        (x, y) tuple where values are in range [-1, 1] on unit circle
    """
    # Center coordinates
    center_x = 0
    center_y = 0

    # Vector from center to point
    dx = slope_x - center_x
    dy = slope_y - center_y

    # Calculate maximum possible radius (distance from center to corner)
    max_radius = np.sqrt(slope_x ** 2 + slope_y ** 2)

    # Normalize by maximum radius
    x = dx / max_radius
    y = dy / max_radius

    # Clamp to unit circle if magnitude exceeds 1
    magnitude = np.sqrt(x ** 2 + y ** 2)
    if magnitude > 1.0:
        x /= magnitude
        y /= magnitude

    print(f'Converted slope ({slope_x}, {slope_y}) to circle coords ({x:.3f}, {y:.3f})')

if __name__ == '__main__':
    slope_to_circle_coords()