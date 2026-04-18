"""
engine_bridge.py
Loads the compiled C++ engine.so and wraps it in a clean Python API.
Python never needs to know about the C++ internals — just calls these methods.
"""
import ctypes, os, sys
from dataclasses import dataclass
from enum import IntEnum

# ── Action types (must match C++ ActionType enum) ─────────────────
class ActionType(IntEnum):
    NONE         = 0
    MOUSE_MOVE   = 1
    LEFT_CLICK   = 2
    RIGHT_CLICK  = 3
    DOUBLE_CLICK = 4
    SCROLL_UP    = 5
    SCROLL_DOWN  = 6
    KEY_ENTER    = 7
    KEY_ESCAPE   = 8
    KEY_SPACE    = 9
    DWELL_CLICK  = 10
    OPEN_KB      = 11

@dataclass
class Action:
    type:      ActionType
    x:         float = 0.0
    y:         float = 0.0
    magnitude: float = 0.0
    label:     str   = "NONE"

    def is_none(self):
        return self.type == ActionType.NONE

def parse_action(raw: bytes) -> Action:
    """Parse 'TYPE|x|y|magnitude|label' string from C++ engine."""
    try:
        parts = raw.decode().split("|")
        return Action(
            type      = ActionType(int(parts[0])),
            x         = float(parts[1]),
            y         = float(parts[2]),
            magnitude = float(parts[3]),
            label     = parts[4] if len(parts) > 4 else "NONE"
        )
    except Exception:
        return Action(type=ActionType.NONE)

# ── Engine wrapper ─────────────────────────────────────────────────
class FreeFaceEngine:
    def __init__(self, lib_path: str = "./engine.so"):
        if not os.path.exists(lib_path):
            raise FileNotFoundError(
                f"C++ engine not found at {lib_path}\n"
                f"Run: make   (in project root)")

        self._lib = ctypes.CDLL(lib_path)
        self._setup_signatures()
        self._eng = self._lib.ff_create()
        if not self._eng:
            raise RuntimeError("Failed to create FreeFaceEngine instance")

    def _setup_signatures(self):
        lib = self._lib
        lib.ff_create.restype         = ctypes.c_void_p
        lib.ff_destroy.argtypes       = [ctypes.c_void_p]
        lib.ff_process.restype        = ctypes.c_char_p
        lib.ff_process.argtypes       = [ctypes.c_void_p,
                                          ctypes.POINTER(ctypes.c_float),
                                          ctypes.c_int]
        lib.ff_start_calibration.argtypes = [ctypes.c_void_p]
        lib.ff_calibrating.restype    = ctypes.c_int
        lib.ff_calibrating.argtypes   = [ctypes.c_void_p]
        lib.ff_calib_progress.restype = ctypes.c_int
        lib.ff_calib_progress.argtypes= [ctypes.c_void_p]
        lib.ff_calib_total.restype    = ctypes.c_int
        lib.ff_calib_total.argtypes   = [ctypes.c_void_p]
        lib.ff_load_profile.restype   = ctypes.c_int
        lib.ff_load_profile.argtypes  = [ctypes.c_void_p, ctypes.c_char_p]
        lib.ff_save_profile.restype   = ctypes.c_int
        lib.ff_save_profile.argtypes  = [ctypes.c_void_p, ctypes.c_char_p]
        for fn in ['ff_set_gaze','ff_set_blink','ff_set_head',
                   'ff_set_expression','ff_set_dwell']:
            getattr(lib, fn).argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.ff_frame_count.restype    = ctypes.c_int
        lib.ff_frame_count.argtypes   = [ctypes.c_void_p]
        lib.ff_blink_count.restype    = ctypes.c_int
        lib.ff_blink_count.argtypes   = [ctypes.c_void_p]
        lib.ff_is_fatigued.restype    = ctypes.c_int
        lib.ff_is_fatigued.argtypes   = [ctypes.c_void_p]
        lib.ff_dwell_progress.restype = ctypes.c_float
        lib.ff_dwell_progress.argtypes= [ctypes.c_void_p]

    def process(self, landmarks: list[list[float]]) -> Action:
        """
        landmarks: list of 478 [x, y, z] points from MediaPipe
        Returns: Action object
        """
        flat = [v for pt in landmarks for v in pt]
        arr  = (ctypes.c_float * len(flat))(*flat)
        raw  = self._lib.ff_process(self._eng, arr, len(flat))
        return parse_action(raw)

    def start_calibration(self):
        self._lib.ff_start_calibration(self._eng)

    def is_calibrating(self) -> bool:
        return bool(self._lib.ff_calibrating(self._eng))

    def calib_progress(self) -> tuple[int, int]:
        """Returns (current_frames, total_frames)"""
        return (self._lib.ff_calib_progress(self._eng),
                self._lib.ff_calib_total(self._eng))

    def load_profile(self, path: str) -> bool:
        return bool(self._lib.ff_load_profile(self._eng, path.encode()))

    def save_profile(self, path: str) -> bool:
        return bool(self._lib.ff_save_profile(self._eng, path.encode()))

    def set_gaze      (self, on: bool): self._lib.ff_set_gaze      (self._eng, int(on))
    def set_blink     (self, on: bool): self._lib.ff_set_blink     (self._eng, int(on))
    def set_head      (self, on: bool): self._lib.ff_set_head      (self._eng, int(on))
    def set_expression(self, on: bool): self._lib.ff_set_expression(self._eng, int(on))
    def set_dwell     (self, on: bool): self._lib.ff_set_dwell     (self._eng, int(on))

    @property
    def frame_count   (self) -> int:   return self._lib.ff_frame_count(self._eng)
    @property
    def blink_count   (self) -> int:   return self._lib.ff_blink_count(self._eng)
    @property
    def is_fatigued   (self) -> bool:  return bool(self._lib.ff_is_fatigued(self._eng))
    @property
    def dwell_progress(self) -> float: return self._lib.ff_dwell_progress(self._eng)

    def __del__(self):
        if hasattr(self, '_eng') and self._eng:
            self._lib.ff_destroy(self._eng)
