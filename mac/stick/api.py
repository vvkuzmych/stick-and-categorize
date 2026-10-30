"""The only code that talks HTTP to the backend. Standard library only."""
import json
import mimetypes
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

TIMEOUT_SECONDS = 60  # a voice upload includes transcription
RETRIES = 2


class ApiError(Exception):
    """The backend answered with an error. `message` is safe to show to the user."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class BackendUnreachable(ApiError):
    pass


@dataclass(frozen=True)
class Note:
    id: str
    text: str
    category: str | None
    created_at: datetime

    @classmethod
    def from_json(cls, data: dict) -> "Note":
        return cls(
            id=data["id"],
            text=data["text"],
            category=data.get("category"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


def new_note_id() -> str:
    return str(uuid.uuid4())


def multipart(fields: dict[str, str], file_field: str, path: Path) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
        f'filename="{path.name}"\r\nContent-Type: {mime}\r\n\r\n'.encode()
        + path.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_notes(self) -> list[Note]:
        return [Note.from_json(n) for n in self._request("GET", "/notes")]

    def upload_voice(self, note_id: str, audio: Path) -> Note:
        """Retries reuse `note_id`, so a retry cannot create a duplicate sticky."""
        body, content_type = multipart({"id": note_id}, "audio", audio)
        last: ApiError | None = None
        for _ in range(RETRIES + 1):
            try:
                return Note.from_json(
                    self._request("POST", "/notes/voice", body, {"Content-Type": content_type})
                )
            except BackendUnreachable as exc:
                last = exc
        assert last is not None
        raise last

    def _request(self, method: str, path: str, body: bytes | None = None, headers=None):
        request = urllib.request.Request(
            self.base_url + path, data=body, method=method, headers=headers or {}
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise ApiError(_detail(exc), exc.code) from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            raise BackendUnreachable(f"Cannot reach the backend at {self.base_url}.") from exc


def _detail(exc: urllib.error.HTTPError) -> str:
    try:
        detail = json.load(exc)["detail"]
        return detail if isinstance(detail, str) else f"Backend error {exc.code}."
    except (ValueError, KeyError, TypeError):
        return f"Backend error {exc.code}."
