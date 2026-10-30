"""Sticky windows: one borderless NSPanel per note, plain text only."""
import Quartz
from AppKit import (
    NSBackingStoreBuffered,
    NSColor,
    NSFont,
    NSMakeRect,
    NSPanel,
    NSScreen,
    NSTextField,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorIgnoresCycle,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)

from stick.api import Note
from stick.placement import Rect, next_position

WIDTH, HEIGHT = 220, 140


def make_panel(note: Note, x: float, y: float) -> NSPanel:
    panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(x, y, WIDTH, HEIGHT),
        NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
        NSBackingStoreBuffered,
        False,
    )
    panel.setBackgroundColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(1.0, 0.95, 0.55, 1.0))
    panel.setHasShadow_(True)
    panel.setOpaque_(True)
    panel.setReleasedWhenClosed_(False)
    # Above desktop icons, below normal windows, on every Space.
    panel.setLevel_(Quartz.CGWindowLevelForKey(Quartz.kCGDesktopIconWindowLevelKey) + 1)
    panel.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces
        | NSWindowCollectionBehaviorStationary
        | NSWindowCollectionBehaviorIgnoresCycle
    )
    label = NSTextField.alloc().initWithFrame_(NSMakeRect(10, 10, WIDTH - 20, HEIGHT - 20))
    label.setStringValue_(f"[{note.category}]\n{note.text}" if note.category else note.text)
    label.setEditable_(False)
    label.setSelectable_(False)
    label.setBezeled_(False)
    label.setDrawsBackground_(False)
    label.setFont_(NSFont.systemFontOfSize_(15))
    label.setTextColor_(NSColor.blackColor())
    panel.contentView().addSubview_(label)
    panel.orderFrontRegardless()
    return panel


class StickyBoard:
    """Draws stickies and remembers which notes are already on screen."""

    def __init__(self) -> None:
        self._panels: dict[str, NSPanel] = {}

    def show(self, note: Note) -> None:
        if note.id in self._panels:
            return
        frame = NSScreen.mainScreen().visibleFrame()
        area = Rect(frame.origin.x, frame.origin.y, frame.size.width, frame.size.height)
        taken = [Rect(f.origin.x, f.origin.y, f.size.width, f.size.height)
                 for f in (p.frame() for p in self._panels.values())]
        x, y = next_position(area, (WIDTH, HEIGHT), taken)
        self._panels[note.id] = make_panel(note, x, y)

    def show_all(self, notes: list[Note]) -> None:
        for note in notes:
            self.show(note)
