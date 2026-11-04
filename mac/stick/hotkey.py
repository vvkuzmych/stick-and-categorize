"""Global hotkey: Ctrl+Option+R. Uses Carbon RegisterEventHotKey, so no Input Monitoring permission."""
import ctypes
import ctypes.util
from collections.abc import Callable

KEY_R = 15
CONTROL_KEY = 0x1000
OPTION_KEY = 0x0800
K_EVENT_CLASS_KEYBOARD = 0x6B657962  # 'keyb'
K_EVENT_HOTKEY_PRESSED = 5
HOTKEY_SIGNATURE = 0x5354434B  # 'STCK'

_carbon = ctypes.CDLL(ctypes.util.find_library("Carbon"))


class _EventTypeSpec(ctypes.Structure):
    _fields_ = [("eventClass", ctypes.c_uint32), ("eventKind", ctypes.c_uint32)]


class _EventHotKeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("id", ctypes.c_uint32)]


_HANDLER = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

_carbon.GetApplicationEventTarget.restype = ctypes.c_void_p
_carbon.InstallEventHandler.argtypes = [
    ctypes.c_void_p, _HANDLER, ctypes.c_uint32, ctypes.POINTER(_EventTypeSpec),
    ctypes.c_void_p, ctypes.c_void_p,
]
_carbon.RegisterEventHotKey.argtypes = [
    ctypes.c_uint32, ctypes.c_uint32, _EventHotKeyID, ctypes.c_void_p,
    ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p),
]


class HotkeyListener:
    def __init__(self, on_toggle: Callable[[], None]) -> None:
        self._on_toggle = on_toggle
        self._handler = _HANDLER(self._on_event)  # keep a reference, or it is freed
        self._ref = ctypes.c_void_p()

    def start(self) -> bool:
        spec = _EventTypeSpec(K_EVENT_CLASS_KEYBOARD, K_EVENT_HOTKEY_PRESSED)
        status = _carbon.InstallEventHandler(
            _carbon.GetApplicationEventTarget(), self._handler, 1, ctypes.byref(spec), None, None
        )
        if status != 0:
            return False
        status = _carbon.RegisterEventHotKey(
            KEY_R, CONTROL_KEY | OPTION_KEY, _EventHotKeyID(HOTKEY_SIGNATURE, 1),
            _carbon.GetApplicationEventTarget(), 0, ctypes.byref(self._ref),
        )
        return status == 0

    def _on_event(self, _call_ref, _event, _user_data) -> int:
        self._on_toggle()
        return 0
