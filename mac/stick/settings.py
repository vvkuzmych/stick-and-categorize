from Foundation import NSUserDefaults

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
_KEY = "backend_url"


def get_backend_url() -> str:
    return NSUserDefaults.standardUserDefaults().stringForKey_(_KEY) or DEFAULT_BACKEND_URL


def set_backend_url(url: str) -> None:
    NSUserDefaults.standardUserDefaults().setObject_forKey_(url.strip(), _KEY)


_POSITIONS_KEY = "sticky_positions"


class PositionStore:
    """Where the user left each sticky, kept on this Mac only (a position belongs to a screen, not a note)."""

    def _all(self) -> dict:
        return dict(NSUserDefaults.standardUserDefaults().dictionaryForKey_(_POSITIONS_KEY) or {})

    def get(self, note_id: str) -> tuple[float, float] | None:
        value = self._all().get(note_id)
        return (float(value[0]), float(value[1])) if value else None

    def set(self, note_id: str, x: float, y: float) -> None:
        positions = self._all()
        positions[note_id] = [x, y]
        NSUserDefaults.standardUserDefaults().setObject_forKey_(positions, _POSITIONS_KEY)

    def forget(self, note_id: str) -> None:
        positions = self._all()
        if positions.pop(note_id, None) is not None:
            NSUserDefaults.standardUserDefaults().setObject_forKey_(positions, _POSITIONS_KEY)
