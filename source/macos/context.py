"""Foreground window context detection (macOS) via osascript/System Events."""
import os
import subprocess


EXCLUDE_NAMES = {
    "Finder", "Dock", "SystemUIServer", "WindowServer", "loginwindow",
}


def _run_osascript(script: str) -> str:
    try:
        out = subprocess.check_output(["osascript", "-e", script],
                                     text=True, stderr=subprocess.DEVNULL).strip()
        return out
    except Exception:
        return ""


def get_foreground_process():
    script = (
        'tell application "System Events"\n'
        'set fp to first application process whose frontmost is true\n'
        'set pid to unix id of fp\n'
        'set nm to name of fp\n'
        'try\n'
        'set ttl to name of front window of fp\n'
        'on error\n'
        'set ttl to ""\n'
        'end try\n'
        'return (pid as text) & "\t" & nm & "\t" & ttl\n'
        'end tell'
    )
    raw = _run_osascript(script)
    if not raw or "\t" not in raw:
        return None
    parts = raw.split("\t", 2)
    if len(parts) < 2:
        return None
    try:
        pid = int(parts[0])
    except ValueError:
        pid = 0
    name = parts[1].strip()
    title = parts[2].strip() if len(parts) > 2 else ""
    if not name or name in EXCLUDE_NAMES:
        return None
    return {"exe": name, "pid": pid, "title": title}


def list_running_apps():
    script = (
        'tell application "System Events"\n'
        'set out to ""\n'
        'repeat with p in (every process whose visible is true)\n'
        'set out to out & (name of p) & "\n"\n'
        'end repeat\n'
        'return out\n'
        'end tell'
    )
    raw = _run_osascript(script)
    result = []
    seen = set()
    for line in raw.splitlines():
        name = line.strip()
        if not name or name in EXCLUDE_NAMES:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append({"exe": name, "title": name})
    result.sort(key=lambda d: d["title"].lower())
    return result
