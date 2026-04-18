"""
windows_compat.py
FreeFace compatibility shim for Windows.

On Windows:
  - engine.so  → engine.dll  (different extension)
  - pynput works the same
  - MediaPipe works the same
  - tkinter (virtual keyboard) works the same
  - screeninfo works the same

Differences handled here:
  1. DLL path resolution
  2. Mouse/keyboard elevated permissions warning
  3. Webcam backend selection (DSHOW is more reliable on Windows)
"""
import sys, os, ctypes, platform

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS   = platform.system() == "Darwin"
IS_LINUX   = platform.system() == "Linux"

def get_engine_lib_name() -> str:
    """Returns correct shared library name for this OS."""
    if IS_WINDOWS: return "engine.dll"
    if IS_MACOS:   return "engine.dylib"
    return "engine.so"          # Linux

def get_webcam_backend():
    """Returns best OpenCV backend for this OS."""
    import cv2
    if IS_WINDOWS: return cv2.CAP_DSHOW    # DirectShow = more reliable on Win
    return cv2.CAP_ANY

def check_admin_windows():
    """
    On Windows, pynput needs elevated privileges to control the mouse
    when certain apps (admin apps, UAC dialogs) are focused.
    This doesn't affect normal use — just warns the user.
    """
    if not IS_WINDOWS:
        return
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            print("[WARN] FreeFace is not running as Administrator.")
            print("       Mouse control may not work over elevated windows (UAC dialogs).")
            print("       For full control: right-click cmd.exe → Run as Administrator")
    except Exception:
        pass

def get_makefile_command() -> str:
    """Returns the correct build command for this OS."""
    if IS_WINDOWS:
        return "build_windows.bat"
    return "make"
