"""Foreground window context detection (Windows) via win32 API."""
import ctypes
import ctypes.wintypes as wt
import os

user32 = ctypes.WinDLL("user32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

EXCLUDE_EXES = {
    "explorer.exe", "textinputhost.exe", "shellexperiencehost.exe",
    "searchhost.exe", "startmenuexperiencehost.exe", "applicationframehost.exe",
    "systemsettings.exe", "opentab.exe",
}


def get_foreground_process() -> dict | None:
    """Return {'exe': name, 'pid': int, 'title': str} for the foreground window."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    # Skip our own window so we don't capture ourselves after recordings.
    pid = wt.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None

    title_len = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(title_len + 1)
    user32.GetWindowTextW(hwnd, buf, title_len + 1)
    title = buf.value

    exe = None
    # Try QueryFullProcessImageName
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if h:
        size = wt.DWORD(2048)
        path_buf = ctypes.create_unicode_buffer(2048)
        if kernel32.QueryFullProcessImageNameW(h, 0, path_buf, ctypes.byref(size)):
            exe = os.path.basename(path_buf.value)
        kernel32.CloseHandle(h)
    if not exe:
        exe = _exe_by_pid_psapi(pid.value)
    if not exe:
        return None
    return {"exe": exe, "pid": pid.value, "title": title}


def _exe_by_pid_psapi(pid: int) -> str | None:
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        buf = ctypes.create_unicode_buffer(2048)
        size = wt.DWORD(2048)
        if psapi.GetModuleFileNameExW(h, None, buf, ctypes.byref(size)) or buf.value:
            return os.path.basename(buf.value)
    finally:
        kernel32.CloseHandle(h)
    return None


def list_running_apps() -> list[dict]:
    """Enumerate visible top-level windows -> distinct apps, sorted by title."""
    result = []
    seen = set()

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindowLongW(hwnd, -20) & 0x80:  # WS_EX_TOOLWINDOW
            return True
        # Has an owner window (dialog etc.) -> skip
        title_len = user32.GetWindowTextLengthW(hwnd)
        if title_len == 0:
            return True
        buf = ctypes.create_unicode_buffer(title_len + 1)
        user32.GetWindowTextW(hwnd, buf, title_len + 1)
        title = buf.value
        if title.lower() in ("program manager", "windows input experience"):
            return True
        pid = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        info = _exe_by_pid_psapi(pid.value)
        if not info:
            return True
        exe = info.lower()
        if exe in EXCLUDE_EXES or exe.startswith(("python", "py.")):
            return True
        key = exe
        if key not in seen:
            seen.add(key)
            result.append({"exe": exe, "title": title})
        return True

    user32.EnumWindows(cb, 0)
    result.sort(key=lambda d: d["title"].lower())
    return result
