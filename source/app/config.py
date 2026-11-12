"""Configuration persistence: profiles, settings, JSON storage."""
import copy
import json
import os
import threading

DEFAULT_PROFILE = {
    "enabled_gestures": {"single": True, "double": True, "long": True},
    "actions": {
        "single": "",
        "double": "",
        "long": "",
    },
}

DEFAULT_CONFIG = {
    "settings": {
        "sound_enabled": True,
        "test_mode": False,
        "trigger_key": "right ctrl",
        "double_tap_window_ms": 250,
        "long_press_threshold_ms": 550,
        "esp_port": "",
        "start_with_windows": False,
    },
    "profiles": {},  # exe_name -> DEFAULT_PROFILE copy
    "default_profile": dict(DEFAULT_PROFILE),
}


class Config:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.data = json.loads(json.dumps(DEFAULT_CONFIG))
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self.lock:
                self.data = data
            self._migrate()
        except (OSError, json.JSONDecodeError):
            self.save()

    def save(self):
        with self.lock:
            snapshot = copy.deepcopy(self.data)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def _migrate(self):
        with self.lock:
            self.data.setdefault("settings", dict(DEFAULT_CONFIG["settings"]))
            self.data["settings"].setdefault("sound_enabled", True)
            self.data["settings"].setdefault("test_mode", False)
            self.data["settings"].setdefault("trigger_key", "right ctrl")
            self.data["settings"].setdefault("double_tap_window_ms", 250)
            self.data["settings"].setdefault("long_press_threshold_ms", 550)
            self.data["settings"].setdefault("esp_port", "")
            self.data["settings"].setdefault("start_with_windows", False)
            self.data.setdefault("profiles", {})
            self.data.setdefault("default_profile", dict(DEFAULT_PROFILE))
            for prof in list(self.data["profiles"].values()) + [self.data["default_profile"]]:
                prof.setdefault("enabled_gestures", {"single": True, "double": True, "long": True})
                prof.setdefault("actions", {"single": "", "double": "", "long": ""})

    # ---------- settings ----------
    @property
    def settings(self):
        return self.data["settings"]

    def set_setting(self, key, value):
        with self.lock:
            self.data["settings"][key] = value
        self.save()

    # ---------- profiles ----------
    def profile_for(self, exe_name):
        with self.lock:
            return self.data["profiles"].get(exe_name) or self.data["default_profile"]

    def is_default_profile(self, exe_name):
        with self.lock:
            return exe_name not in self.data["profiles"]

    def all_profiles(self):
        with self.lock:
            return dict(self.data["profiles"])

    def set_profile(self, exe_name, profile):
        with self.lock:
            self.data["profiles"][exe_name] = profile
        self.save()

    def set_default_profile(self, profile):
        with self.lock:
            self.data["default_profile"] = profile
        self.save()

    def delete_profile(self, exe_name):
        with self.lock:
            self.data["profiles"].pop(exe_name, None)
        self.save()
