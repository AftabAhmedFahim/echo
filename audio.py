import os
import pygame


class AudioManager:
    def __init__(self):
        self.enabled = True
        self.sounds = {}
        self.last_log_text = ""

        try:
            pygame.mixer.get_init()
        except pygame.error:
            self.enabled = False

    def _load_sound(self, path: str):
        if not self.enabled:
            return None
        if not os.path.exists(path):
            return None
        try:
            return pygame.mixer.Sound(path)
        except pygame.error:
            return None

    def load(self) -> None:
        self.sounds["shoot"] = self._load_sound("assets/sounds/shoot.wav")
        self.sounds["hit"] = self._load_sound("assets/sounds/hit.wav")
        self.sounds["interact"] = self._load_sound("assets/sounds/interact.wav")
        self.sounds["death"] = self._load_sound("assets/sounds/death.wav")

    def play(self, name: str) -> None:
        sound = self.sounds.get(name)
        if sound:
            sound.play()

    def play_log(self, text: str) -> None:
        self.last_log_text = text