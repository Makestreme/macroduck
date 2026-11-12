# macOS setup (experimental)

Macro Duck is developed and tested on Windows. To run on macOS:

1. Install Python 3.10+ from python.org (includes Tk).
2. Create a venv and install dependencies:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   (The `keyboard` library needs Accessibility permission; grant it in
   System Settings -> Privacy & Security -> Accessibility.)
3. Copy these files from the `macos` folder into your app folder:
   - `context.py`   -> into `app/` (replaces the Windows version)
   - `autostart.py` -> into `app/` (replaces the Windows version)
   - `main.py`      -> top level (replaces the Windows version)
4. Run with `python main.py`.

Notes:
- Foreground detection uses `osascript`/System Events.
- Autostart uses a LaunchAgent in `~/Library/LaunchAgents`.
- Icon uses `iconphoto` (PNG); `.icns` not required.
- Test Mode keyboard trigger needs Accessibility permission.
- The hardware button works the same as on Windows: after flashing the
  firmware, pick the board's port (typically `/dev/cu.usbmodem*`) in the top
  bar (use `/dev/cu.*`, not `/dev/tty.*`, so the port doesn't wait for DCD).
