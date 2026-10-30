"""Global hotkey: Ctrl+Option+Space. Needs the Input Monitoring permission."""
from collections.abc import Callable

from AppKit import (
    NSEvent,
    NSEventMaskKeyDown,
    NSEventModifierFlagCommand,
    NSEventModifierFlagControl,
    NSEventModifierFlagOption,
    NSEventModifierFlagShift,
)

KEY_SPACE = 49
WANTED = NSEventModifierFlagControl | NSEventModifierFlagOption
FORBIDDEN = NSEventModifierFlagCommand | NSEventModifierFlagShift


class HotkeyListener:
    def __init__(self, on_toggle: Callable[[], None]) -> None:
        self._on_toggle = on_toggle
        self._monitor = None

    def start(self) -> bool:
        self._monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSEventMaskKeyDown, self._on_key
        )
        return self._monitor is not None

    def _on_key(self, event) -> None:
        if event.keyCode() != KEY_SPACE:
            return
        if (event.modifierFlags() & (WANTED | FORBIDDEN)) != WANTED:
            return
        self._on_toggle()
