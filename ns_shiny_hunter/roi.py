from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ROI:
    """Resolution-agnostic region of interest stored as relative coordinates (0.0–1.0).

    Coordinates are expressed as fractions of the frame dimensions so that a single ROI
    definition works correctly across different capture resolutions (e.g. 720p vs 1080p).
    """

    x: float
    y: float
    w: float
    h: float

    @classmethod
    def from_pixels(cls, x: int, y: int, w: int, h: int, frame_w: int, frame_h: int) -> ROI:
        """Create an ROI from absolute pixel coordinates at a known frame resolution."""
        return cls(x / frame_w, y / frame_h, w / frame_w, h / frame_h)

    def to_pixels(self, frame_w: int, frame_h: int) -> tuple[int, int, int, int]:
        """Return (x, y, w, h) in absolute pixels for the given frame resolution."""
        return (
            round(self.x * frame_w),
            round(self.y * frame_h),
            round(self.w * frame_w),
            round(self.h * frame_h),
        )

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> ROI:
        return cls(d["x"], d["y"], d["w"], d["h"])
