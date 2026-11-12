"""Start-with-OS registration (macOS) via LaunchAgent."""
import os
import plistlib
import subprocess
import sys


LABEL = "com.macroduck.app"
AGENTS_DIR = os.path.expanduser("~/Library/LaunchAgents")
PLIST_PATH = os.path.join(AGENTS_DIR, LABEL + ".plist")


def apply(enabled, status_cb=None):
    cb = status_cb or (lambda _s: None)
    try:
        os.makedirs(AGENTS_DIR, exist_ok=True)
        if enabled:
            python = sys.executable
            # main.py lives next to this folder's parent (src/)
            main_py = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                  "..", "main.py"))
            plist = {
                "Label": LABEL,
                "ProgramArguments": [python, main_py],
                "RunAtLoad": True,
                "KeepAlive": False,
            }
            with open(PLIST_PATH, "wb") as f:
                plistlib.dump(plist, f)
            try:
                subprocess.run(["launchctl", "load", PLIST_PATH],
                               check=False, capture_output=True)
            except Exception:
                pass
            cb("Startup enabled")
        else:
            try:
                subprocess.run(["launchctl", "unload", PLIST_PATH],
                               check=False, capture_output=True)
            except Exception:
                pass
            if os.path.exists(PLIST_PATH):
                os.remove(PLIST_PATH)
            cb("Startup disabled")
    except Exception as e:
        cb(f"Startup toggle failed: {e}")
