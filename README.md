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
