"""Windows bits (copied from NEM Trader's backend/system.py): one copy only, keep the PC awake while downloading,
Edge as a back-up window, message boxes.
"""
import ctypes
import os
import subprocess
import sys
from pathlib import Path

APP_NAME = "Weather"
FROZEN = getattr(sys, "frozen", False)
_mutex = None   # kept open for the life of the program


def single_instance():
    global _mutex
    if sys.platform != "win32":
        return True
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\WeatherECMWFSingleInstance")
    return ctypes.windll.kernel32.GetLastError() != 183   # 183 = ERROR_ALREADY_EXISTS


def stay_awake(on):
    """While a refresh downloads: stop the PC going to sleep (the screen may still turn off). Per calling thread."""
    if sys.platform == "win32":
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))


def unblock_program_files():
    """Remove Windows' "came from the internet" mark from the program's DLLs (else .NET won't load the window's DLL)."""
    if not FROZEN or sys.platform != "win32":
        return 0
    n = 0
    for f in Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).rglob("*.dll"):
        try:
            os.remove(f"{f}:Zone.Identifier")
            n += 1
        except OSError:
            pass
    return n


def find_edge():
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        if base:
            p = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if p.exists():
                return str(p)
    return None


def open_in_edge(url, profile):
    """Back-up when the built-in window can't start: the same screen in an Edge app window. Waits until it is closed."""
    edge = find_edge()
    if not edge:
        return False
    subprocess.Popen([edge, f"--app={url}", f"--user-data-dir={profile}", "--no-first-run",
                      "--disable-features=Translate", "--start-maximized"]).wait()
    return True


def message(text, title=APP_NAME):
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)
    else:
        print(text)
