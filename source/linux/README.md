# Linux setup (experimental, X11 only)

Macro Duck is developed and tested on Windows. Linux support is X11 only;
Wayland is not supported for global hotkeys/foreground detection.

1. Install Python 3.10+ and Tk:
   ```
   sudo apt install python3 python3-tk python3-venv
   ```
2. Install X11 helpers:
   ```
   sudo apt install xdotool wmctrl
   ```
3. Create a venv and install dependencies:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   (The `keyboard` library needs root or udev access to `/dev/input`.)
4. Copy these files from the `linux` folder into your app folder:
   - `context.py`   -> into `app/` (replaces the Windows version)
   - `autostart.py` -> into `app/` (replaces the Windows version)
   - `main.py`      -> top level (replaces the Windows version)
5. Run with `python main.py`.

Notes:
- Foreground detection uses `xdotool`/`wmctrl` (X11).
- Autostart uses `~/.config/autostart/macro-duck.desktop`.
- Global trigger key may require running as root.
- The hardware button works the same as on Windows: after flashing the
  firmware, pick the board's port (typically `/dev/ttyACM0` or `/dev/ttyUSB0`)
  in the top bar.
- Your user needs dialout group access for the serial port:
  ```
  sudo usermod -aG dialout $USER
  ```
  (log out and back in for it to take effect)
