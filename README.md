# Macro Duck

Context-aware universal macro app. Map gestures: single tap, double tap, long press, from a physical button to app-specific hotkey combinations, based on whatever window is focused.

## What this site offers

- **Setup guide**: full video walkthrough (wiring, flashing, using the app)
- **Firmware flashing**: one-click flash for ESP32-C3 and ESP32-S3 boards, straight from the browser
- **Windows app**: portable download, no Python installation needed

## Flashing

Open the site in Chrome or Edge, plug your board in over USB, and click **Install** on your board's card; the browser will ask you to pick the board's port. Firefox and Safari do not support browser flashing.

Boards that aren't listed can be flashed manually with the Arduino IDE using the downloadable sketch, its card explains the three steps.

## The Windows app

Unzip anywhere and double-click `launch.bat`. The app ships with its own Python runtime, so nothing else needs to be installed.

- **Test Mode ON**: the selected keyboard key acts as the trigger (no hardware needed, good for testing)
- **Test Mode OFF**: real use: gestures come from the hardware button over USB serial

Profiles and settings live in `config.json` next to the app, so the folder is fully portable.

## Running from source (no zip)

If you'd rather not download the zip, you can run the app straight from its Python files. Everything lives in the [`source`](source/) folder — a few files at the top level, the `app` package, the `sounds` folder with the duck sounds, and `linux` / `macos` folders for those platforms. Keep that layout as-is.

### Windows

1. **Install Python** — get Python 3.10+ from [python.org](https://www.python.org/downloads/). On the first installer screen, tick **"Add python.exe to PATH"** before clicking Install.
2. **Download the files** — in the [`source`](source/) folder above, download `main.py`, `config.json`, and `requirements.txt` into a new folder on your computer, plus everything in the [`app`](source/app/) and [`sounds`](source/sounds/) subfolders into `app` and `sounds` folders next to them.
3. **Install the requirements** — open a terminal in your new folder (on Windows: type `cmd` in the folder's address bar and press Enter) and run:
   ```
   pip install -r requirements.txt
   ```
4. **Start the app**:
   ```
   python main.py
   ```

Your `config.json` is created next to the files and can be edited by hand or through the app.

### Linux (experimental, X11 only)

Follow the guide in [`source/linux/README.md`](source/linux/README.md). Short version: install Tk plus `xdotool` and `wmctrl`, then drop the three files from the `linux` folder into your app folder — `main.py` at the top level, and `context.py` and `autostart.py` inside `app/`, replacing the Windows versions. Wayland is not supported.

### macOS (experimental)

Follow the guide in [`source/macos/README.md`](source/macos/README.md). Short version: replace the same three files using the `macos` folder, and grant Accessibility permission (System Settings -> Privacy & Security) so the app can send key events and read the focused app.
