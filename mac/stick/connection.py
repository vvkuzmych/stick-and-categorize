"""Watches the backend and reports online/offline. No AppKit here, so it is easy to test."""
import threading
from collections.abc import Callable

OFFLINE_INTERVAL = 3.0  # seconds between checks while the backend is down
ONLINE_INTERVAL = 15.0  # seconds between checks while it is up


class ConnectionMonitor:
    """Calls `on_change(online)` on the first check and whenever the state flips."""

    def __init__(
        self,
        check: Callable[[], bool],
        on_change: Callable[[bool], None],
        offline_interval: float = OFFLINE_INTERVAL,
        online_interval: float = ONLINE_INTERVAL,
    ) -> None:
        self._check = check
        self._on_change = on_change
        self._offline_interval = offline_interval
        self._online_interval = online_interval
        self._online: bool | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()

    def step(self) -> float:
        """One check. Returns how long to wait before the next one."""
        try:
            online = bool(self._check())
        except Exception:  # noqa: BLE001 (a broken check must not kill the loop)
            online = False
        if online != self._online:
            self._online = online
            self._on_change(online)
        return self._online_interval if online else self._offline_interval

    def check_now(self) -> None:
        """Skip the wait, e.g. after the backend URL changed."""
        self._wake.set()

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            wait = self.step()
            self._wake.wait(wait)
            self._wake.clear()
