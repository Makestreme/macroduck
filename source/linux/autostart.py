"""Start-with-OS registration (Linux) via XDG autostart."""
import os
import sys


AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
DESKTOP_PATH = os.path.join(AUTOSTART_DIR, "macro-duck.desktop")


def apply(enabled, status_cb=None):
    cb = status_cb or (lambda _s: None)
    try:
        os.makedirs(AUTOSTART_DIR, exist_ok=True)
        if enabled:
            python = sys.executable
            main_py = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                  "..", "main.py"))
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Macro Duck\n"
                f"Exec={python} {main_py}\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            with open(DESKTOP_PATH, "w", encoding="utf-8") as f:
                f.write(content)
            cb("Startup enabled")
        else:
            if os.path.exists(DESKTOP_PATH):
                os.remove(DESKTOP_PATH)
            cb("Startup disabled")
    except Exception as e:
        cb(f"Startup toggle failed: {e}")
