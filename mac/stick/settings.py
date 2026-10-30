from Foundation import NSUserDefaults

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
_KEY = "backend_url"


def get_backend_url() -> str:
    return NSUserDefaults.standardUserDefaults().stringForKey_(_KEY) or DEFAULT_BACKEND_URL


def set_backend_url(url: str) -> None:
    NSUserDefaults.standardUserDefaults().setObject_forKey_(url.strip(), _KEY)
