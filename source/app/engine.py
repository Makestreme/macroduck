"""MacroEngine: ties together keyboard hook, gesture recognizer, context
lookup, audio feedback and config."""

import threading
import time

import keyboard

from . import actions, context, serial_link
from .audio import AudioEngine
from .config import Config
from .gesture import Gesture, GestureRecognizer

GESTURE_NAMES = {Gesture.SINGLE: "single", Gesture.DOUBLE: "double", Gesture.LONG: "long"}


class MacroEngine:
    def __init__(self, config: Config, sound_dir: str, status_cb=None):
        self.cfg = config
        self.status_cb = status_cb or (lambda *a, **k: None)  # fn(text) for UI status line
        self.audio = AudioEngine(sound_dir)
        self.recognizer = GestureRecognizer(on_gesture=self._on_gesture)
        self.enabled = True               # master engine switch
        self.applied_hook = None          # (trigger_key, test_mode) currently hooked
        self._hook_lock = threading.Lock()
        self.link = serial_link.SerialLink(self._on_device_gesture, status_cb=self.status)
        self.apply_settings()

    # ---------------- engine plumbing ----------------
    def status(self, text: str):
        self.status_cb(text)

    def apply_settings(self):
        s = self.cfg.settings
        self.audio.enabled = s["sound_enabled"]
        self.recognizer.set_timings(
            s.get("double_tap_window_ms", 250), s.get("long_press_threshold_ms", 550))
        trigger = s["trigger_key"].lower()
        test_mode = bool(s.get("test_mode", True))
        state = (trigger, test_mode)
        if state != self.applied_hook:
            with self._hook_lock:
                if self.applied_hook is not None:
                    try:
                        keyboard.unhook_key(self.applied_hook[0])
                    except (KeyError, ValueError):
                        pass
                self.applied_hook = None
                if test_mode:
                    # Test mode ON: swallow the trigger key so it acts as a
                    # gesture simulator instead of its normal function.
                    try:
                        keyboard.hook_key(trigger, self._on_key_event, suppress=True)
                        self.applied_hook = state
                    except (ValueError, OSError):
                        self.applied_hook = None
                # Test mode OFF: no hook at all — the key passes through
                # normally and gestures come only from the hardware button.

    # ---------------- hook callback ----------------
    def _on_key_event(self, event: keyboard.KeyboardEvent):
        if not self.enabled:
            return
        s = self.cfg.settings
        if not s.get("test_mode", True):
            # Test mode off: gestures come from the hardware button over serial.
            return
        t = time.monotonic() * 1000.0
        if event.event_type == keyboard.KEY_DOWN:
            # Only on the initial press (event.scan_code works for auto-repeat)
            self.recognizer.on_trigger_down(t)
        else:
            self.recognizer.on_trigger_up(t)

    # ---------------- gesture -> dispatch ----------------
    def _on_gesture(self, g: Gesture):
        self._dispatch(GESTURE_NAMES[g])

    def _on_device_gesture(self, name: str):
        """Gesture received from the hardware trigger button (serial)."""
        if self.enabled and not self.cfg.settings.get("test_mode", True):
            self._dispatch(name)

    def _dispatch(self, name: str):
        fg = context.get_foreground_process()
        if not fg:
            self.audio.play(name)
            self.status("No foreground window detected")
            return
        exe_full = fg["exe"]
        exe = exe_full.lower()
        prof = self.cfg.profile_for(exe)
        action = prof["actions"].get(name, "")
        if not prof["enabled_gestures"].get(name, True):
            action = ""
        self.audio.play(name)
        if action:
            actions.send_hotkey(action)
            self.status(f"{name.upper()} -> {exe_full}: {action}")
        else:
            self.status(f"{name} in {exe_full}: (no action)")

    # ---------------- recorder support ----------------
    def enable_trigger_passthrough(self):
        """While recording shortcuts we must not swallow the trigger key."""
        self.enabled = False

    def restore(self):
        self.enabled = True

    # ---------------- recording helpers ----------------
    @staticmethod
    def record_shortcut(prompt_cb, done_cb):
        """Hook all keys; capture a SEQUENCE of combos until Enter/Esc/mouse.
        Returns a finish() callable so callers can stop via mouse click."""
        captured = {"hook": None, "seq": [], "finished": False}

        def finish(cancel=False):
            if captured["finished"]:
                return
            captured["finished"] = True
            try:
                if captured["hook"] is not None:
                    keyboard.unhook(captured["hook"])
                for hid in captured.get("suppress_ids", []):
                    try:
                        keyboard.remove_hotkey(hid)
                    except Exception:
                        pass
            except Exception:
                pass
            captured["hook"] = None
            if cancel:
                prompt_cb("Cancelled")
                done_cb(None)
                return
            text = ", ".join(captured["seq"])
            prompt_cb(text if text else "")
            done_cb(text if text else None)

        def handler(event):
            if captured["finished"]:
                return
            if event.event_type != keyboard.KEY_DOWN:
                return
            if keyboard.is_pressed("esc"):
                finish(cancel=True)
                return
            if event.name == "enter":
                finish()
                return
            if event.name in ("ctrl", "shift", "alt", "windows"):
                return
            combo = event.name
            keys_now = set()
            for k in ("ctrl", "shift", "alt", "windows"):
                if k != combo and keyboard.is_pressed(k):
                    keys_now.add(k)
            entries = sorted(keys_now) + [combo]
            text = "+".join(entries)
            captured["seq"].append(text)
            prompt_cb(" → ".join(captured["seq"]) +
                      "   (Enter to finish, Esc to cancel)")

        captured["hook"] = keyboard.hook(handler)
        # Prevent Alt+Tab from switching apps while recording
        suppress_ids = []
        try:
            suppress_ids.append(keyboard.add_hotkey(
                "alt+tab", lambda: None, suppress=True))
        except Exception:
            pass
        prompt_cb("Press keys… Enter to finish, Esc to cancel")
        captured["suppress_ids"] = suppress_ids
        return finish
