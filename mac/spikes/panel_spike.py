"""Spike A: a plain-text sticky that sits at desktop level and shows on all Spaces.

Throwaway. Run: python panel_spike.py [seconds]   (default 60)
"""
import sys

import Quartz
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
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
from Foundation import NSTimer

WIDTH, HEIGHT = 220, 140


def make_sticky(text: str, category: str | None, x: float, y: float) -> NSPanel:
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
    # Above desktop icons, below normal windows.
    panel.setLevel_(Quartz.CGWindowLevelForKey(Quartz.kCGDesktopIconWindowLevelKey) + 1)
    panel.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces
        | NSWindowCollectionBehaviorStationary
        | NSWindowCollectionBehaviorIgnoresCycle
    )

    label = NSTextField.alloc().initWithFrame_(NSMakeRect(10, 10, WIDTH - 20, HEIGHT - 20))
    label.setStringValue_(text if not category else f"[{category}]\n{text}")
    label.setEditable_(False)
    label.setSelectable_(False)
    label.setBezeled_(False)
    label.setDrawsBackground_(False)
    label.setFont_(NSFont.systemFontOfSize_(15))
    label.setTextColor_(NSColor.blackColor())
    panel.contentView().addSubview_(label)
    panel.orderFrontRegardless()
    return panel


def main() -> None:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # no Dock icon

    frame = NSScreen.mainScreen().visibleFrame()
    top = frame.origin.y + frame.size.height
    panels = [
        make_sticky("Buy milk and call the dentist", "Shopping", frame.origin.x + 60, top - HEIGHT - 60),
        make_sticky("Send the quarterly report to finance", "Work", frame.origin.x + 60 + WIDTH + 20, top - HEIGHT - 60),
    ]
    for p in panels:
        print("level", p.level(), "behavior", p.collectionBehavior(), "windowNumber", p.windowNumber(), flush=True)

    NSTimer.scheduledTimerWithTimeInterval_repeats_block_(seconds, False, lambda _t: app.terminate_(None))
    app.run()


if __name__ == "__main__":
    main()
