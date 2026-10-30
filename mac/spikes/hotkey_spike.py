"""Spike A: a global hotkey (Ctrl+Option+Space) that toggles "recording" while in the background.

Throwaway. Run: python hotkey_spike.py [seconds]   (default 60)
macOS may ask for Input Monitoring permission for the terminal or app.
"""
import sys

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSEvent,
    NSEventMaskKeyDown,
    NSEventModifierFlagControl,
    NSEventModifierFlagOption,
)
from Foundation import NSTimer

KEY_SPACE = 49
WANTED = NSEventModifierFlagControl | NSEventModifierFlagOption
COMMAND_SHIFT = (1 << 20) | (1 << 17)  # must not be held

recording = False


def on_key(event) -> None:
    global recording
    if event.keyCode() != KEY_SPACE:
        return
    if (event.modifierFlags() & (WANTED | COMMAND_SHIFT)) != WANTED:
        return
    recording = not recording
    print("recording START" if recording else "recording STOP", flush=True)


def main() -> None:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(NSEventMaskKeyDown, on_key)
    print("monitor installed:", monitor is not None, "- press Ctrl+Option+Space", flush=True)
    NSTimer.scheduledTimerWithTimeInterval_repeats_block_(seconds, False, lambda _t: app.terminate_(None))
    app.run()


if __name__ == "__main__":
    main()
