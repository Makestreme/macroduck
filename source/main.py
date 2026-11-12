"""Macro Duck (Windows) — entry point.

Run:  python main.py
"""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SOUND_DIR = os.path.join(BASE_DIR, "sounds")

# Portable runtime: point Tcl/Tk at the bundled runtime (python\tcl)
# before CustomTkinter/Tk loads anything.
_PY_HOME = os.path.dirname(sys.executable)
if os.path.isdir(os.path.join(_PY_HOME, "tcl", "tcl8.6")):
    os.environ.setdefault("TCL_LIBRARY", os.path.join(_PY_HOME, "tcl", "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", os.path.join(_PY_HOME, "tcl", "tk8.6"))
import ctypes
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("macro_duck.app")
from app.config import Config
from app.engine import MacroEngine
from app.ui import App


def main():
    cfg = Config(CONFIG_PATH)
    engine = MacroEngine(cfg, SOUND_DIR, status_cb=lambda s: None)

    ui = App(engine)
    # (App.__init__ wires engine.status_cb before any auto-connect)

    from app import sounds  # placeholder tones if missing
    threading.Thread(target=sounds.ensure_placeholder_tones,
                     args=(SOUND_DIR,), daemon=True).start()

    ui.root.mainloop()


if __name__ == "__main__":
    main()
