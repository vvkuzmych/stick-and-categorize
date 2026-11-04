"""Sticky windows: one borderless NSPanel per note, plain text only."""
from collections.abc import Callable
from typing import Protocol

import objc
import Quartz
from AppKit import (
    NSBackingStoreBuffered,
    NSButton,
    NSColor,
    NSFont,
    NSMakeRect,
    NSNotificationCenter,
    NSObject,
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
from stick.placement import Rect, is_reachable, next_position

WIDTH, HEIGHT = 220, 140
DELETE_BUTTON = 22


class DeleteTarget(NSObject):
    """Receives the click on a sticky's delete icon."""

    def initWithCallback_(self, callback):
        self = objc.super(DeleteTarget, self).init()  # noqa: PLW0642 (PyObjC idiom)
        self.callback = callback
        return self

    def delete_(self, _sender) -> None:
        self.callback()


def make_panel(note: Note, x: float, y: float, target: DeleteTarget) -> NSPanel:
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
    panel.setMovableByWindowBackground_(True)  # borderless windows cannot be dragged otherwise
    # Above desktop icons, below normal windows, on every Space.
    panel.setLevel_(Quartz.CGWindowLevelForKey(Quartz.kCGDesktopIconWindowLevelKey) + 1)
    panel.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces
        | NSWindowCollectionBehaviorStationary
        | NSWindowCollectionBehaviorIgnoresCycle
    )
    label = NSTextField.alloc().initWithFrame_(NSMakeRect(10, 10, WIDTH - 20 - DELETE_BUTTON, HEIGHT - 20))
    label.setStringValue_(f"[{note.category}]\n{note.text}" if note.category else note.text)
    label.setEditable_(False)
    label.setSelectable_(False)
    label.setBezeled_(False)
    label.setDrawsBackground_(False)
    label.setFont_(NSFont.systemFontOfSize_(15))
    label.setTextColor_(NSColor.blackColor())
    panel.contentView().addSubview_(label)
    button = NSButton.alloc().initWithFrame_(
        NSMakeRect(WIDTH - DELETE_BUTTON - 4, HEIGHT - DELETE_BUTTON - 4, DELETE_BUTTON, DELETE_BUTTON)
    )
    button.setTitle_("✕")
    button.setBordered_(False)
    button.setToolTip_("Delete this note")
    button.setTarget_(target)
    button.setAction_("delete:")
    panel.contentView().addSubview_(button)
    panel.orderFrontRegardless()
    return panel


NSWindowDidMoveNotification = "NSWindowDidMoveNotification"


class Positions(Protocol):
    def get(self, note_id: str) -> tuple[float, float] | None: ...
    def set(self, note_id: str, x: float, y: float) -> None: ...
    def forget(self, note_id: str) -> None: ...


class StickyBoard:
    """Draws stickies and remembers which notes are already on screen."""

    def __init__(self, on_delete: Callable[[str], None], positions: Positions) -> None:
        self._on_delete = on_delete  # asked to delete a note; the board only draws
        self._positions = positions
        self._observers: dict[str, object] = {}  # drag listeners, removed with the sticky
        self._panels: dict[str, NSPanel] = {}
        self._targets: dict[str, DeleteTarget] = {}  # keeps the click handlers alive

    def show(self, note: Note) -> None:
        if note.id in self._panels:
            return
        note_id = note.id
        x, y = self._saved_position(note_id) or self._free_position()
        target = DeleteTarget.alloc().initWithCallback_(lambda: self._on_delete(note_id))
        self._targets[note_id] = target
        panel = make_panel(note, x, y, target)
        self._panels[note_id] = panel
        self._observers[note_id] = NSNotificationCenter.defaultCenter().addObserverForName_object_queue_usingBlock_(
            NSWindowDidMoveNotification, panel, None, lambda _n: self._moved(note_id, panel)
        )

    def _moved(self, note_id: str, panel: NSPanel) -> None:
        origin = panel.frame().origin
        self._positions.set(note_id, origin.x, origin.y)

    def _saved_position(self, note_id: str) -> tuple[float, float] | None:
        saved = self._positions.get(note_id)
        if saved is None:
            return None
        screens = [Rect(f.origin.x, f.origin.y, f.size.width, f.size.height)
                   for f in (s.visibleFrame() for s in NSScreen.screens())]
        return saved if is_reachable(Rect(saved[0], saved[1], WIDTH, HEIGHT), screens) else None

    def _free_position(self) -> tuple[float, float]:
        frame = NSScreen.mainScreen().visibleFrame()
        area = Rect(frame.origin.x, frame.origin.y, frame.size.width, frame.size.height)
        taken = [Rect(f.origin.x, f.origin.y, f.size.width, f.size.height)
                 for f in (p.frame() for p in self._panels.values())]
        return next_position(area, (WIDTH, HEIGHT), taken)

    def remove(self, note_id: str) -> None:
        panel = self._panels.pop(note_id, None)
        self._targets.pop(note_id, None)
        observer = self._observers.pop(note_id, None)
        if observer is not None:
            NSNotificationCenter.defaultCenter().removeObserver_(observer)
        self._positions.forget(note_id)
        if panel is not None:
            panel.close()

    def show_all(self, notes: list[Note]) -> None:
        # Stickies the user placed first, so an automatic spot never takes theirs.
        for note in sorted(notes, key=lambda n: self._positions.get(n.id) is None):
            self.show(note)
