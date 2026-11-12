"""Modern UI built with CustomTkinter."""
import os
import queue
import time
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

from . import context, serial_link, autostart
from .engine import MacroEngine

# Bump when diagnosing: if the title bar doesn't show this, you are running
# a different/older copy of the app than the one being edited.
VERSION = "v2 2026-11-11"
LOG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "run.log"))

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

GESTURES = ("single", "double", "long")
LABELS = {"single": "Single Smack", "double": "Double Smack", "long": "Long Press"}

TRIGGER_CHOICES = ["right ctrl", "left ctrl", "right alt", "left alt",
                   "right shift", "left shift", "f9", "f10", "f11", "f12",
                   "scroll lock", "pause"]

ESP_OFF = "off"

BG = "#181825"
BG_CARD = "#1e1e2e"
BG_RAISE = "#262637"
FG = "#cdd6f4"
FG_DIM = "#7f849c"
ACCENT = "#89b4fa"
GREEN = "#a6e3a1"
SELECT = "#45475a"


class App:
    def __init__(self, engine: MacroEngine):
        self.engine = engine
        self.cfg = engine.cfg
        self.current_exe = None
        self._status_queue = queue.Queue()
        self._timing_after = None
        self._recording_widget = None
        self._entries = []
        self._raw_labels = []

        self.root = ctk.CTk()
        self.root.title(f"Macro Duck {VERSION}")
        self.root.geometry("920x700")
        self.root.minsize(800, 600)
        self._apply_window_icon()

        # Wire the status sink BEFORE any auto-connect so startup messages
        # ("Hardware connected on …", "Hardware: cannot open …") are not dropped.
        engine.status_cb = self.set_status
        self.set_status(f"Macro Duck {VERSION} started")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        autostart.apply(self.cfg.settings.get("start_with_windows", False),
                       status_cb=self.set_status)
        saved_port = self.cfg.settings.get("esp_port")
        if saved_port:
            self.engine.link.connect(saved_port)
            self._esp_refresh_btn()
        self.root.after(100, self._poll_status)
        self.root.after(1500, self._refresh_front_active)

    def _apply_window_icon(self):
        """Use the duck logo for the window and taskbar icon."""
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
        ico = os.path.join(base, "macroduck.ico")
        png = os.path.join(base, "macroduck.png")
        try:
            if os.path.exists(ico):
                self.root.iconbitmap(ico)
                return
            if os.path.exists(png):
                self.root.iconphoto(True, tk.PhotoImage(master=self.root, file=png))
        except Exception:
            pass  # cosmetic only — never block startup over the icon

    def _build_ui(self):
        outer = ctk.CTkFrame(self.root, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        # top bar
        top = ctk.CTkFrame(outer, fg_color=BG_CARD, corner_radius=12)
        top.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(top, text="SOUND", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=FG_DIM).pack(side="left", padx=(14, 4), pady=10)
        self.sound_var = ctk.BooleanVar(value=self.cfg.settings["sound_enabled"])
        self.sound_btn = ctk.CTkButton(top, text="ON" if self.sound_var.get() else "OFF",
                                       width=60, height=28, corner_radius=14,
                                       fg_color="#2a4d3a" if self.sound_var.get() else BG_RAISE,
                                       text_color=GREEN if self.sound_var.get() else FG_DIM,
                                       hover_color="#3a6b52", command=self.on_sound_toggle)
        self.sound_btn.pack(side="left", padx=(0, 16), pady=10)

        ctk.CTkLabel(top, text="TEST MODE", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=FG_DIM).pack(side="left", padx=(0, 4))
        self.test_var = ctk.BooleanVar(value=self.cfg.settings["test_mode"])
        self.test_btn = ctk.CTkButton(top, text="ON" if self.test_var.get() else "OFF",
                                     width=60, height=28, corner_radius=14,
                                     fg_color="#2a4d3a" if self.test_var.get() else BG_RAISE,
                                     text_color=GREEN if self.test_var.get() else FG_DIM,
                                     hover_color="#3a6b52", command=self.on_test_toggle)
        self.test_btn.pack(side="left", padx=(0, 16), pady=10)

        ctk.CTkLabel(top, text="STARTUP", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=FG_DIM).pack(side="left", padx=(0, 4))
        self.startup_var = ctk.BooleanVar(value=self.cfg.settings["start_with_windows"])
        self.startup_btn = ctk.CTkButton(top, text="ON" if self.startup_var.get() else "OFF",
                                        width=60, height=28, corner_radius=14,
                                        fg_color="#2a4d3a" if self.startup_var.get() else BG_RAISE,
                                        text_color=GREEN if self.startup_var.get() else FG_DIM,
                                        hover_color="#3a6b52", command=self.on_startup_toggle)
        self.startup_btn.pack(side="left", padx=(0, 16), pady=10)

        ctk.CTkLabel(top, text="TRIGGER", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=FG_DIM).pack(side="left", padx=(0, 4))
        self.trigger_var = ctk.StringVar(value=self.cfg.settings["trigger_key"])
        self.trigger_cb = ctk.CTkComboBox(top, values=TRIGGER_CHOICES, width=130,
                                          variable=self.trigger_var,
                                          command=lambda _: self.on_trigger_change())
        self.trigger_cb.pack(side="left", padx=(0, 16), pady=10)

        self.esp_port_var = ctk.StringVar(value=self.cfg.settings.get("esp_port") or ESP_OFF)
        self.esp_cb = ctk.CTkComboBox(top, values=self._esp_ports(), width=110,
                                      state="readonly", variable=self.esp_port_var,
                                      command=lambda _v: self._on_port_change())
        self.esp_cb.pack(side="right", padx=(0, 6), pady=10)
        ctk.CTkButton(top, text="⟳", width=28, command=self._esp_refresh).pack(
            side="right", padx=(0, 6), pady=10)
        self.esp_connect_btn = ctk.CTkButton(top, text="CONNECT", width=100,
                                             command=self._esp_connect)
        self.esp_connect_btn.pack(side="right", padx=(0, 12), pady=10)

        self.fore_lbl = ctk.CTkLabel(top, text="foreground: -", text_color=FG_DIM,
                                    font=ctk.CTkFont(size=10))
        self.fore_lbl.pack(side="right", padx=14, pady=10)

        # body
        body = ctk.CTkFrame(outer, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # left apps card
        apps_card = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=12)
        apps_card.pack(side="left", fill="y", padx=(0, 12))

        ctk.CTkLabel(apps_card, text="APPLICATIONS", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=FG_DIM).pack(anchor="w", padx=14, pady=(12, 6))

        self.search_var = ctk.StringVar()
        search = ctk.CTkEntry(apps_card, textvariable=self.search_var, width=200,
                              placeholder_text="Filter apps…")
        search.pack(padx=14, pady=(0, 8), fill="x")
        search.bind("<KeyRelease>", lambda e: self._filter_apps(self.search_var.get()))

        self.app_scroll = ctk.CTkScrollableFrame(apps_card, width=230, height=420,
                                                fg_color=BG_RAISE, corner_radius=8)
        self.app_scroll.pack(padx=14, pady=(0, 8), fill="both", expand=True)

        btns = ctk.CTkFrame(apps_card, fg_color="transparent")
        btns.pack(padx=14, pady=(0, 12), fill="x")
        ctk.CTkButton(btns, text="Refresh", width=90, command=self._refresh_apps).pack(side="left")
        ctk.CTkButton(btns, text="Remove", width=90, fg_color="#5a2a35", hover_color="#7a3a45",
                      command=self._remove_profile).pack(side="left", padx=8)

        # right profile card
        prof_card = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=12)
        prof_card.pack(side="left", fill="both", expand=True)

        self.prof_title = ctk.CTkLabel(prof_card, text="Select an application",
                                       font=ctk.CTkFont(size=16, weight="bold"))
        self.prof_title.pack(anchor="w", padx=16, pady=(14, 2))
        self.prof_sub = ctk.CTkLabel(prof_card, text="Gestures below apply only to this app.",
                                     text_color=FG_DIM, font=ctk.CTkFont(size=11))
        self.prof_sub.pack(anchor="w", padx=16, pady=(0, 12))

        self.gesture_rows = {}
        for g in GESTURES:
            row = ctk.CTkFrame(prof_card, fg_color=BG_RAISE, corner_radius=8)
            row.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(row, text=LABELS[g], width=120, anchor="w",
                         font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=12, pady=10)

            ctk.CTkLabel(row, text="", width=52).pack(side="left", padx=(0, 8), pady=10)
            combo_lbl = ctk.CTkLabel(row, text="(not set)", anchor="w", text_color=FG_DIM,
                                    font=ctk.CTkFont(family="Consolas", size=11))
            combo_lbl.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=10)
            rec_btn = ctk.CTkButton(row, text="Record", width=80,
                                    command=lambda g=g: self.start_recording(g))
            rec_btn.pack(side="left", padx=(0, 4), pady=10)
            ctk.CTkButton(row, text="✕", width=36, fg_color="#5a2a35", hover_color="#7a3a45",
                          command=lambda g=g: self.clear_action(g)).pack(side="left", padx=(0, 12), pady=10)
            self.gesture_rows[g] = {"label": combo_lbl, "record_btn": rec_btn}

        # timing card
        timing = ctk.CTkFrame(prof_card, fg_color=BG_RAISE, corner_radius=8)
        timing.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(timing, text="TIMING", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=FG_DIM).pack(anchor="w", padx=12, pady=(10, 6))

        self._timing_row(timing, "Double-tap window", "double_tap_window_ms", 150, 500, "dbl")
        self._timing_row(timing, "Long-press threshold", "long_press_threshold_ms", 300, 1000, "long")

        ctk.CTkLabel(timing, text="Changes apply instantly and save automatically.",
                     text_color=FG_DIM, font=ctk.CTkFont(size=10)).pack(anchor="w", padx=12, pady=(6, 10))

        ctk.CTkLabel(prof_card, text=(
            "Trigger key + gesture sends the recorded combo to the focused app.  "
            "★ = has profile   ⚙ = default for everything else.\n"
            "Record captures modifier+key. Test mode off disables the keyboard "
            "simulator for the trigger key."),
            text_color=FG_DIM, font=ctk.CTkFont(size=10), justify="left").pack(
            anchor="w", padx=16, pady=(8, 14))

        # status bar
        self.status = ctk.CTkLabel(outer, text="Ready", text_color=FG_DIM,
                                   font=ctk.CTkFont(size=10), anchor="w")
        self.status.pack(fill="x", pady=(8, 0))

        self._refresh_apps()

    def _timing_row(self, parent, title, setting, lo, hi, tag):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row, text=title, width=150, anchor="w").pack(side="left")
        slider = ctk.CTkSlider(row, from_=lo, to=hi, width=200,
                               command=lambda _v: self.on_timing())
        slider.set(self.cfg.settings[setting])
        slider.pack(side="left", padx=8)
        lbl = ctk.CTkLabel(row, text=str(self.cfg.settings[setting]), width=40)
        lbl.pack(side="left")
        if tag == "dbl":
            self.dbl_slider, self.dbl_lbl = slider, lbl
            self.dbl_setting = setting
        else:
            self.long_slider, self.long_lbl = slider, lbl
            self.long_setting = setting

    # ---- status ----
    def _poll_status(self):
        try:
            while True:
                self.status.configure(text=self._status_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(150, self._poll_status)

    def set_status(self, text):
        # Mirror to run.log so we always have ground truth about what the
        # app did, even if the on-screen label is stale or unreadable.
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {text}\n")
        except OSError:
            pass
        self._status_queue.put(text)

    def _refresh_front_active(self):
        try:
            fg = context.get_foreground_process()
            if fg:
                self.fore_lbl.configure(text=f"{fg['title'][:38]}  ·  {fg['exe']}")
            else:
                self.fore_lbl.configure(text="foreground: -")
            self._esp_refresh_btn()   # keep CONNECT/DISCONNECT label in sync
        finally:
            # Reschedule even if a callback raised — otherwise one error
            # silently kills all foreground/button updates (seen in logs).
            self.root.after(1000, self._refresh_front_active)

    # ---- apps ----
    def _refresh_apps(self):
        self._entries = []
        self._raw_labels = []
        cfg_exes = self.cfg.all_profiles()
        entries = [("default", "⚙   Default Profile")]
        for e in sorted(cfg_exes):
            entries.append((e, "★   " + e))
        for info in context.list_running_apps():
            if info["exe"] in cfg_exes:
                continue
            entries.append((info["exe"], "     " + info["exe"]))
        for exe, display in entries:
            self._entries.append(exe)
            self._raw_labels.append(display)
        self._render_app_list()
        # selection handled on click

    def _render_app_list(self, filter_text=""):
        for w in self.app_scroll.winfo_children():
            w.destroy()
        text = filter_text.lower().strip()
        for exe, label in zip(self._entries, self._raw_labels):
            if text and text not in label.lower() and text not in exe.lower():
                continue
            btn = ctk.CTkButton(self.app_scroll, text=label, anchor="w",
                                fg_color="transparent", text_color=FG,
                                hover_color=SELECT, corner_radius=6,
                                command=lambda e=exe: self._load_profile(e))
            btn.pack(fill="x", pady=2, padx=4)

    def _filter_apps(self, text):
        self._render_app_list(text)

    # ---- profile ----
    def _load_profile(self, exe):
        self.current_exe = exe
        is_default = self.cfg.is_default_profile(exe)
        prof = self.cfg.profile_for(exe)
        self.prof_title.configure(text="Default Profile" if is_default else exe)
        self.prof_sub.configure(
            text="Used by every app without its own profile."
            if is_default else "Gestures below apply only to this app.")
        for g in GESTURES:
            action = prof["actions"].get(g, "")
            self._set_action_label(g, action)

    def _set_action_label(self, g, action):
        lbl = self.gesture_rows[g]["label"]
        if action:
            lbl.configure(text=action, text_color=ACCENT)
        else:
            lbl.configure(text="(not set)", text_color=FG_DIM)

    def _set_profile(self, prof):
        if self.current_exe == "default":
            self.cfg.set_default_profile(prof)
        else:
            self.cfg.set_profile(self.current_exe, prof)

    def clear_action(self, g):
        if self.current_exe is None or self._recording_widget:
            return
        prof = self.cfg.profile_for(self.current_exe)
        prof = {k: (dict(v) if isinstance(v, dict) else v) for k, v in prof.items()}
        prof["actions"][g] = ""
        self._set_profile(prof)
        self._set_action_label(g, "")

    def start_recording(self, g):
        if self.current_exe is None:
            messagebox.showinfo("No app selected", "Select an application first.")
            return
        if self._recording_widget:
            return
        self.engine.enable_trigger_passthrough()
        lbl = self.gesture_rows[g]["label"]
        lbl.configure(text="●  press keys…  (Enter to finish, Esc to cancel)", text_color=GREEN)
        self._recording_widget = lbl
        rec_btn = self.gesture_rows[g]["record_btn"]
        rec_btn.configure(text="End recording", command=lambda: stop())

        def finish(text):
            prof = self.cfg.profile_for(self.current_exe)
            prof = {k: (dict(v) if isinstance(v, dict) else v) for k, v in prof.items()}
            prof["actions"][g] = text or ""
            self._set_profile(prof)
            self._set_action_label(g, text or "")
            self._recording_widget = None
            self.engine.restore()
            self._refresh_apps()
            rec_btn.configure(text="Record", command=lambda g=g: self.start_recording(g))

        def done(text):
            self.root.after(0, lambda: finish(text))

        stop = MacroEngine.record_shortcut(lambda m: self._rec_prompt(g, m), done)

    def _rec_prompt(self, g, msg):
        try:
            self.gesture_rows[g]["label"].configure(text=msg)
        except Exception:
            pass

    # ---- hardware serial ----
    def _esp_ports(self):
        return [ESP_OFF] + [dev for dev, _desc in serial_link.list_com_ports()]

    def _esp_refresh(self):
        self.esp_cb.configure(values=self._esp_ports())
        self._esp_refresh_btn()

    def _esp_refresh_btn(self):
        """Label reflects the ACTUAL link state, not just the selection."""
        sel = self.esp_port_var.get().strip() or ESP_OFF
        link = self.engine.link
        if sel != ESP_OFF and link.port == sel:
            state = ("DISCONNECT", "#5a2a35", "#7a3a45")
        elif sel != ESP_OFF and link.want == sel:
            state = ("CONNECTING…", BG_RAISE, SELECT)
        else:
            state = ("CONNECT", "#1f6aa5", "#1f538d")   # theme default blue
        if state == getattr(self, "_esp_btn_state", None):
            return                      # unchanged — avoid redrawing every tick
        self._esp_btn_state = state
        self.esp_connect_btn.configure(text=state[0], fg_color=state[1],
                                       hover_color=state[2])

    def _on_port_change(self):
        """Selecting a port in the dropdown connects to it immediately."""
        sel = self.esp_port_var.get().strip() or ESP_OFF
        if sel != ESP_OFF and self.engine.link.want != sel:
            self.cfg.set_setting("esp_port", sel)
            self.engine.link.connect(sel)
            self.set_status(f"Hardware: connecting to {sel}…")
        self._esp_refresh_btn()

    def _esp_connect(self):
        sel = self.esp_port_var.get().strip() or ESP_OFF
        link = self.engine.link
        if sel == ESP_OFF:
            link.disconnect()
            self.cfg.set_setting("esp_port", "")
            self.set_status("Pick a COM port first, then press CONNECT")
        elif link.port == sel or link.want == sel:
            # True connection state says we're (being) connected → disconnect.
            link.disconnect()
            self.cfg.set_setting("esp_port", "")
            self.set_status("Hardware disconnected")
        else:
            self.cfg.set_setting("esp_port", sel)
            link.connect(sel)
            self.set_status(f"Hardware: connecting to {sel}…")
        self._esp_refresh_btn()

    # ---- settings ----
    def on_sound_toggle(self):
        new_val = not self.sound_var.get()
        self.sound_var.set(new_val)
        if new_val:
            self.sound_btn.configure(text="ON", fg_color="#2a4d3a", text_color=GREEN, hover_color="#3a6b52")
        else:
            self.sound_btn.configure(text="OFF", fg_color=BG_RAISE, text_color=FG_DIM, hover_color=SELECT)
        self.engine.audio.enabled = new_val
        self.cfg.set_setting("sound_enabled", new_val)

    def on_test_toggle(self):
        new_val = not self.test_var.get()
        self.test_var.set(new_val)
        if new_val:
            self.test_btn.configure(text="ON", fg_color="#2a4d3a", text_color=GREEN, hover_color="#3a6b52")
        else:
            self.test_btn.configure(text="OFF", fg_color=BG_RAISE, text_color=FG_DIM, hover_color=SELECT)
        self.cfg.set_setting("test_mode", new_val)
        self.engine.apply_settings()

    def on_startup_toggle(self):
        new_val = not self.startup_var.get()
        self.startup_var.set(new_val)
        if new_val:
            self.startup_btn.configure(text="ON", fg_color="#2a4d3a", text_color=GREEN, hover_color="#3a6b52")
        else:
            self.startup_btn.configure(text="OFF", fg_color=BG_RAISE, text_color=FG_DIM, hover_color=SELECT)
        self.cfg.set_setting("start_with_windows", new_val)
        autostart.apply(new_val, status_cb=self.set_status)

    def on_trigger_change(self, _e=None):
        self.cfg.set_setting("trigger_key", self.trigger_var.get())
        self.engine.apply_settings()

    def on_timing(self, _e=None):
        if not (hasattr(self, "dbl_lbl") and hasattr(self, "long_lbl")):
            return
        self.dbl_lbl.configure(text=str(int(self.dbl_slider.get())))
        self.long_lbl.configure(text=str(int(self.long_slider.get())))
        if self._timing_after:
            try:
                self.root.after_cancel(self._timing_after)
            except Exception:
                pass
        self._timing_after = self.root.after(600, self._commit_timing)

    def _commit_timing(self):
        d, l = int(self.dbl_slider.get()), int(self.long_slider.get())
        self.cfg.set_setting(self.dbl_setting, d)
        self.cfg.set_setting(self.long_setting, l)
        self.engine.recognizer.set_timings(d, l)

    def _remove_profile(self):
        if not self.current_exe or self.current_exe == "default":
            messagebox.showinfo("Nothing to remove",
                                "Default profile cannot be removed.\n"
                                "Select a star-marked app first.")
            return
        if messagebox.askyesno("Confirm", f"Remove profile for {self.current_exe}?"):
            self.cfg.delete_profile(self.current_exe)
            self.current_exe = None
            self._refresh_apps()
            self.prof_title.configure(text="Select an application")
            self.prof_sub.configure(text="Gestures below apply only to this app.")

    def _on_close(self):
        try:
            self.engine.link.disconnect()
            self.engine.audio.close()
        finally:
            self.root.destroy()
            os._exit(0)