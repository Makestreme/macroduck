"""Audio feedback engine using pygame.mixer (low-latency MP3 playback)."""
import os
import threading

import pygame

class AudioEngine:
    def __init__(self, sound_dir):
        self.sound_dir = sound_dir
        self.enabled = True
        self._lock = threading.Lock()
        self._sounds = {}
        try:
            pygame.mixer.init()
        except pygame.error:
            pass
        self.reload()

    def reload(self):
        with self._lock:
            self._sounds = {}
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                for g in ("single", "double", "long"):
                    for ext in (".mp3", ".wav"):
                        path = os.path.join(self.sound_dir, g + ext)
                        if os.path.isfile(path):
                            snd = pygame.mixer.Sound(path)
                            snd.set_volume(0.7)
                            self._sounds[g] = snd
                            break
            except pygame.error:
                pass

    def play(self, gesture: str):
        if not self.enabled:
            return
        with self._lock:
            snd = self._sounds.get(gesture)
        if snd:
            snd.play()

    def close(self):
        try:
            pygame.mixer.stop()
            pygame.mixer.quit()
        except pygame.error:
            pass
