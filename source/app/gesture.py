"""Gesture state machine: single tap, double tap, long press from a trigger key.

Runs on top of a suppressed global keyboard hook. Callbacks fire on a worker
thread (the hook thread), so handlers must be fast / dispatch elsewhere.
"""
import threading
from enum import Enum, auto


class Gesture(Enum):
    SINGLE = auto()
    DOUBLE = auto()
    LONG = auto()


class GestureRecognizer:
    def __init__(self, on_gesture):
        self.on_gesture = on_gesture            # fn(Gesture)
        self._double_ms = 250
        self._long_ms = 550
        self._lock = threading.RLock()
        self._reset()

    # --- timing settings from UI ---
    def set_timings(self, double_ms: int, long_ms: int):
        with self._lock:
            self._double_ms = double_ms
            self._long_ms = long_ms

    def _reset(self):
        self.state = "idle"     # idle | down1 | waiting2 | down2
        self.timer = None
        self.long_fired = False
        self.down_time = 0.0

    # --- events from hook ---
    def on_trigger_down(self, time_ms: float):
        with self._lock:
            st = self.state
            if st == "idle":
                self.state = "down1"
                self.down_time = time_ms
                self.long_fired = False
                self._arm_long()
            elif st == "waiting2":
                self.state = "down2"
                self.down_time = time_ms
                self._cancel_timer()
                self._arm_long()
            else:
                # down1/down2 without release -> ignore repeats
                pass

    def on_trigger_up(self, time_ms: float):
        with self._lock:
            if self.state in ("down1", "down2"):
                self._cancel_timer()
            else:
                self._reset()
                return
            if self.long_fired:
                self._reset()
                return
            held = time_ms - self.down_time
            st = self.state
            self._reset()
            if held <= self._long_ms:
                if st == "down1":
                    # candidate single; wait for 2nd tap
                    self.state = "waiting2"
                    self._arm_double()
                else:
                    # second quick release = DOUBLE
                    self._fire(Gesture.DOUBLE)
            # long press already fired via timer

    def _arm_long(self):
        with self._lock:
            self._cancel_timer()
            self.timer = threading.Timer(self._long_ms / 1000.0, self._long_expired)
            self.timer.daemon = True
            self.timer.start()

    def _arm_double(self):
        with self._lock:
            self._cancel_timer()
            self.timer = threading.Timer(
                self._double_ms / 1000.0, self._double_expired)
            self.timer.daemon = True
            self.timer.start()

    def _cancel_timer(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def _long_expired(self):
        with self._lock:
            if self.state in ("down1", "down2"):
                self.long_fired = True
                self.timer = None
                self._fire(Gesture.LONG)
                # remain "held" until release resets us

    def _double_expired(self):
        with self._lock:
            if self.state == "waiting2":
                self.state = "idle"
                self.timer = None
                self._fire(Gesture.SINGLE)

    def _fire(self, g: Gesture):
        cb = self.on_gesture
        if cb:
            cb(g)
