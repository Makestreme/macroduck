"""Start-with-OS registration.

Windows implementation (default). For macOS/Linux, replace this file with the
version from src/macos/ or src/linux/ (see README).
"""
import os
import sys


def apply(enabled, status_cb=None):
    cb = status_cb or (lambda _s: None)
    if sys.platform != "win32":
        cb("Startup toggle is only implemented on Windows")
        return
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        if enabled:
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(pythonw):
                pythonw = sys.executable
            main_py = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                  "..", "main.py"))
            cmd = f'"{pythonw}" "{main_py}"'
            winreg.SetValueEx(key, "MacroDuck", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, "MacroDuck")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        cb("Startup " + ("enabled" if enabled else "disabled"))
    except Exception as e:
        cb(f"Startup toggle failed: {e}")
