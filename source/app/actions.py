"""Dispatch: send configured hotkey combinations via injected keystrokes."""
import threading
import time

import keyboard


def send_hotkey(combo: str):
    """combo like 'ctrl+shift+s' or a sequence 'ctrl+a, delete'. Non-blocking."""
    if not combo:
        return
    parts = [p.strip() for p in combo.split(",") if p.strip()]
    if not parts:
        return

    def _run():
        for i, part in enumerate(parts):
            if i:
                time.sleep(0.08)
            keyboard.send(part)

    threading.Thread(target=_run, daemon=True).start()