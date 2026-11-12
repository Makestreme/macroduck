"""Serial link: reads gesture events from the MacroDuck hardware trigger button.

Firmware sends one line per gesture: "TAP_1", "TAP_2" or "TAP_HOLD" (115200 baud).
"""
import threading
import time

import serial
from serial.tools import list_ports

TAP_NAMES = {"TAP_1": "single", "TAP_2": "double", "TAP_HOLD": "long"}
BAUD = 115200
RETRY_DELAY_S = 2.0


def list_com_ports():
    """Return [(device, description), ...] for available COM ports."""
    return [(p.device, p.description) for p in list_ports.comports()]


class SerialLink:
    """Background reader for one COM port. on_gesture(name) fires per message."""

    def __init__(self, on_gesture, status_cb=None):
        self.on_gesture = on_gesture            # fn(gesture_name: str)
        self.status_cb = status_cb or (lambda *a: None)
        self.want = None   # port to keep connected to (None = disconnected)
        self.port = None   # currently open port
        self._ser = None
        self._last_unknown = 0.0   # throttle for "unknown data" status messages
        self._last_data = 0.0      # monotonic time of last received byte
        self._last_open_fail = 0.0 # throttle for "cannot open" status messages
        self._warned_silent = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def connect(self, port_name):
        """Switch reader to port_name ('' or None disconnects)."""
        self.want = port_name or None

    def disconnect(self):
        self.want = None

    def _close(self):
        try:
            if self._ser is not None:
                self._ser.close()
        except Exception:
            pass
        self._ser = None
        self.port = None

    def _open(self):
        try:
            self._ser = serial.Serial(self.want, BAUD, timeout=1)
        except (OSError, serial.SerialException):
            self._ser = None
            # Retried every 2s — only report once per 10s to avoid spam.
            if time.monotonic() - self._last_open_fail > 10.0:
                self._last_open_fail = time.monotonic()
                self.status_cb(f"Hardware: cannot open {self.want} "
                               f"(port in use or missing?)")
            return False
        self.port = self.want
        self.status_cb(f"Hardware connected on {self.want}")
        # Give ESP32-class boards time to finish their reset/boot sequence
        # triggered by the port being opened, before we start reading.
        time.sleep(2.0)
        # Ping the board: current firmware answers with "READY", which proves
        # the link is live. Older firmware stays silent (see no-data warning).
        try:
            self._ser.reset_input_buffer()
            self._ser.write(b"PING\n")
            self._ser.flush()
        except (OSError, serial.SerialException):
            pass
        self._last_data = time.monotonic()
        self._warned_silent = False
        return True

    def _run(self):
        while True:
            if self.port != self.want:
                self._close()
                if self.want and not self._open():
                    self._wait()
                    continue
            if self._ser is None:
                self._wait()
                continue
            try:
                raw = self._ser.readline()
            except (OSError, serial.SerialException):
                self._close()
                self.status_cb("Hardware disconnected")
                continue
            now = time.monotonic()
            if raw:
                self._last_data = now
                self._warned_silent = False
            elif not self._warned_silent and now - self._last_data > 10.0:
                # Connected but ZERO bytes received (not even the PING reply).
                self._warned_silent = True
                self.status_cb(f"Hardware: no data from {self.port} — reflash the "
                               f"firmware / check the serial port")
            line = raw.decode("ascii", "ignore").strip()
            up = line.upper()
            if up.startswith("READY") or up.startswith("PIN="):
                if up.startswith("READY"):
                    self.status_cb(f"Hardware ready on {self.port}")
                continue
            name = TAP_NAMES.get(up)
            if name and self.port == self.want:
                self.on_gesture(name)
            elif line and self.port == self.want:
                # Non-empty data that isn't a recognized gesture message.
                # Surface it (throttled) so baud/wiring issues aren't silent.
                now = time.monotonic()
                if now - self._last_unknown > 2.0:
                    self._last_unknown = now
                    self.status_cb(f"Hardware: unexpected data {raw!r} "
                                   f"(check baud {BAUD} and firmware)")

    @staticmethod
    def _wait():
        time.sleep(RETRY_DELAY_S)
