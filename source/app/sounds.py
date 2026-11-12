"""Generate short placeholder feedback tones (WAV) if none exist.
Put your own MP3s (single.mp3, double.mp3, long.mp3) into ./sounds to override.
"""
import math
import os
import struct
import wave

# freq, duration(ms) per beep
TONES = {
    "single": (880, 70),
    "double": (1200, 60),
    "long": (520, 220),
}


def _write_tone(path, freq, ms):
    rate = 22050
    n = int(rate * ms / 1000)
    frames = bytearray()
    for i in range(n):
        env = min(1.0, i / (rate * 0.005 + 1.0), (n - i) / (rate * 0.02 + 1.0))
        v = int(env * 0.4 * 32767 * math.sin(2 * math.pi * freq * i / rate))
        frames += struct.pack("<h", v)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def ensure_placeholder_tones(sound_dir: str):
    os.makedirs(sound_dir, exist_ok=True)
    for name, (freq, ms) in TONES.items():
        path = os.path.join(sound_dir, name + ".wav")
        if not os.path.isfile(path):
            try:
                _write_tone(path, freq, ms)
            except OSError:
                pass
