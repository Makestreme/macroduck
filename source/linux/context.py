"""Foreground window context detection (Linux, X11 only) via xdotool."""
import os
import subprocess


EXCLUDE_NAMES = {"", "Desktop", "gnome-shell", "plasmashell"}


def _run(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def get_foreground_process():
    wid = _run(["xdotool", "getactivewindow"])
    if not wid:
        return None
    pid_raw = _run(["xdotool", "getwindowpid", wid])
    title = _run(["xdotool", "getwindowname", wid])
    try:
        pid = int(pid_raw)
    except ValueError:
        pid = 0
    name = ""
    if pid:
        try:
            with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as f:
                name = f.read().strip()
        except OSError:
            name = ""
    if not name:
        # fallback: basename of /proc/pid/exe
        try:
            name = os.path.basename(os.readlink(f"/proc/{pid}/exe"))
        except OSError:
            name = ""
    if not name or name in EXCLUDE_NAMES:
        return None
    return {"exe": name, "pid": pid, "title": title}


def list_running_apps():
    out = _run(["wmctrl", "-lx"])
    result = []
    seen = set()
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        _wid, _desktop, wm_class, title = parts[0], parts[1], parts[2], parts[3]
        name = wm_class.split(".")[-1].lower()
        if not name or name in EXCLUDE_NAMES:
            continue
        if name in seen:
            continue
        seen.add(name)
        result.append({"exe": name, "title": title})
    result.sort(key=lambda d: d["title"].lower())
    return result
