"""Menu-bar app: hotkey -> record -> upload -> sticky. Keeps no notes of its own."""
import os
import threading
from pathlib import Path

import objc
from AppKit import (
    NSAlert,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSObject,
    NSStatusBar,
    NSTextField,
    NSVariableStatusItemLength,
)
from Foundation import NSTimer
from PyObjCTools import AppHelper

from stick import settings
from stick.api import ApiClient, ApiError, new_note_id
from stick.hotkey import HotkeyListener
from stick.recorder import DENIED_MESSAGE, Recorder, ensure_permission
from stick.sticky import StickyBoard
from stick.sync import launch_sync


def alert(title: str, message: str) -> None:
    box = NSAlert.alloc().init()
    box.setMessageText_(title)
    box.setInformativeText_(message)
    box.runModal()


class MenuTarget(NSObject):
    """Receives menu clicks. Selector-style names (trailing underscore) must live here."""

    def initWithController_(self, controller):
        self = objc.super(MenuTarget, self).init()  # noqa: PLW0642 (PyObjC idiom)
        self.controller = controller
        return self

    def openSettings_(self, _sender) -> None:
        self.controller.open_settings()

    def quit_(self, _sender) -> None:
        NSApplication.sharedApplication().terminate_(None)


class Controller:
    def __init__(self) -> None:
        self.recorder = Recorder()
        self.board = StickyBoard()
        self.client = ApiClient(settings.get_backend_url())
        self.hotkey = HotkeyListener(self.toggle)
        self.busy = 0  # uploads in flight
        self.menu_target = MenuTarget.alloc().initWithController_(self)

    # ---- menu bar ----
    def build_menu(self) -> None:
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.item.button().setTitle_("📝")
        menu = NSMenu.alloc().init()
        self.status_line = menu.addItemWithTitle_action_keyEquivalent_("Ready", None, "")
        self.status_line.setEnabled_(False)
        menu.addItem_(NSMenuItem.separatorItem())
        settings_item = menu.addItemWithTitle_action_keyEquivalent_(
            "Backend URL…", "openSettings:", ""
        )
        settings_item.setTarget_(self.menu_target)
        quit_item = menu.addItemWithTitle_action_keyEquivalent_("Quit", "quit:", "q")
        quit_item.setTarget_(self.menu_target)
        self.item.setMenu_(menu)

    def set_status(self, text: str) -> None:
        self.status_line.setTitle_(text)

    def open_settings(self) -> None:
        box = NSAlert.alloc().init()
        box.setMessageText_("Backend URL")
        box.addButtonWithTitle_("Save")
        box.addButtonWithTitle_("Cancel")
        field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 300, 24))
        field.setStringValue_(settings.get_backend_url())
        box.setAccessoryView_(field)
        if box.runModal() == 1000:  # first button
            settings.set_backend_url(str(field.stringValue()))
            self.client = ApiClient(settings.get_backend_url())
            self.sync()

    # ---- launch sync ----
    def sync(self) -> None:
        client = self.client

        def work() -> None:
            try:
                notes = launch_sync(client)
            except ApiError as exc:
                AppHelper.callAfter(self.set_status, exc.message)
                return
            AppHelper.callAfter(self._synced, notes)

        threading.Thread(target=work, daemon=True).start()

    def _synced(self, notes) -> None:
        self.board.show_all(notes)
        self.set_status("Ready")

    # ---- recording ----
    def toggle(self) -> None:
        AppHelper.callAfter(self._toggle)

    def _toggle(self) -> None:
        if self.recorder.recording:
            self._stop()
        else:
            ensure_permission(self._permission_done)

    def _permission_done(self, granted: bool) -> None:
        if not granted:
            self.set_status("Microphone access is off")
            alert("Microphone access is off", DENIED_MESSAGE)
            return
        try:
            self.recorder.start()
        except RuntimeError as exc:
            self.set_status(str(exc))
            return
        self.item.button().setTitle_("🔴")
        self.set_status("Recording… press the hotkey again to stop")

    def _stop(self) -> None:
        audio = self.recorder.stop()
        self.item.button().setTitle_("📝")
        self.upload(audio, new_note_id())  # the id exists before any upload attempt

    def upload(self, audio: Path, note_id: str) -> None:
        client = self.client
        self.busy += 1
        self.set_status("Transcribing…")

        def work() -> None:
            try:
                note = client.upload_voice(note_id, audio)
            except ApiError as exc:
                AppHelper.callAfter(self._upload_failed, exc.message)
                return
            AppHelper.callAfter(self._uploaded, note)

        threading.Thread(target=work, daemon=True).start()

    def _uploaded(self, note) -> None:
        self.busy -= 1
        self.board.show(note)
        self.set_status("Ready" if not self.busy else "Transcribing…")

    def _upload_failed(self, message: str) -> None:
        self.busy -= 1
        self.set_status(message)


def main() -> None:
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # no Dock icon
    controller = Controller()
    controller.build_menu()
    if not controller.hotkey.start():
        controller.set_status("Hotkey not available (check Input Monitoring)")
    controller.sync()
    quit_after = os.environ.get("STICK_QUIT_AFTER")  # for smoke tests
    if quit_after:
        NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            float(quit_after), False, lambda _t: app.terminate_(None)
        )
    AppHelper.runEventLoop(installInterrupt=True)
