"""Where a new sticky goes. Pure code: no AppKit, so it is tested without a screen."""
from dataclasses import dataclass

GAP = 16
CASCADE_STEP = 30


@dataclass(frozen=True)
class Rect:
    x: float
    y: float  # AppKit origin is bottom-left
    w: float
    h: float

    def intersects(self, other: "Rect") -> bool:
        return not (
            self.x + self.w <= other.x
            or other.x + other.w <= self.x
            or self.y + self.h <= other.y
            or other.y + other.h <= self.y
        )


def next_position(area: Rect, size: tuple[float, float], taken: list[Rect]) -> tuple[float, float]:
    """First free spot, filling rows left to right from the top-left of `area`.

    If the area is full, cascade from the top-left so stickies stay reachable.
    """
    w, h = size
    top = area.y + area.h
    y = top - GAP - h
    while y >= area.y:
        x = area.x + GAP
        while x + w <= area.x + area.w:
            if not any(Rect(x, y, w, h).intersects(t) for t in taken):
                return x, y
            x += w + GAP
        y -= h + GAP
    n = len(taken)
    offset = CASCADE_STEP * (n % 10)
    return area.x + GAP + offset, top - GAP - h - offset
