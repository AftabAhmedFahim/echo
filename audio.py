import os
import math
import struct
import pygame


class AudioManager:
    def __init__(self):
        self.enabled = True
        self.sounds = {}
        self.last_log_text = ""
        self.music_enabled = True
        self.music_path = "assets/sounds/ambient.wav"
        self.slide_sound = None
        self.ending_sigh_sound = None

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
        self.slide_sound = self._create_slide_sound()
        self.ending_sigh_sound = self._load_sound("assets/sounds/ending_sigh.wav") or self._create_ending_sigh_sound()

        if self.music_enabled:
            self.play_music()

    def _create_slide_sound(self):
        if not self.enabled:
            return None

        mixer_state = pygame.mixer.get_init()
        if not mixer_state:
            return None

        frequency, sample_size, channels = mixer_state
        if sample_size not in (-16, 16):
            return None

        duration = 0.42
        frame_count = int(frequency * duration)
        buffer = bytearray()

        for index in range(frame_count):
            progress = index / max(1, frame_count - 1)
            envelope = (1.0 - progress) ** 1.8
            frequency_sweep = 760 - (420 * progress)
            sample = int(math.sin(progress * math.tau * frequency_sweep * duration) * 12000 * envelope)
            packed = struct.pack("<h", sample)
            if channels == 2:
                buffer.extend(packed)
                buffer.extend(packed)
            else:
                buffer.extend(packed)

        try:
            return pygame.mixer.Sound(buffer=bytes(buffer))
        except pygame.error:
            return None

    def _create_ending_sigh_sound(self):
        if not self.enabled:
            return None

        mixer_state = pygame.mixer.get_init()
        if not mixer_state:
            return None

        frequency, sample_size, channels = mixer_state
        if sample_size not in (-16, 16):
            return None

        duration = 1.55
        frame_count = int(frequency * duration)
        buffer = bytearray()

        for index in range(frame_count):
            t = index / max(1, frequency)
            progress = index / max(1, frame_count - 1)
            envelope = (math.sin(progress * math.pi) ** 0.8) * (1.0 - progress * 0.28)

            sweep_hz = 150 - 82 * progress
            wobble_hz = 2.6 + 1.4 * progress
            wobble = math.sin(2 * math.pi * wobble_hz * t)
            carrier = math.sin(2 * math.pi * (sweep_hz + 12 * wobble) * t)
            undertone = math.sin(2 * math.pi * 38 * t + 0.7) * 0.4
            sample = int((carrier * 0.68 + undertone * 0.32) * 10500 * envelope)

            packed = struct.pack("<h", sample)
            if channels == 2:
                buffer.extend(packed)
                buffer.extend(packed)
            else:
                buffer.extend(packed)

        try:
            return pygame.mixer.Sound(buffer=bytes(buffer))
        except pygame.error:
            return None

    def play(self, name: str) -> None:
        sound = self.sounds.get(name)
        if sound:
            sound.play()

    def play_log(self, text: str) -> None:
        self.last_log_text = text

    def play_music(self) -> None:
        if not self.enabled or not self.music_enabled:
            return
        if not os.path.exists(self.music_path):
            return
        try:
            pygame.mixer.music.load(self.music_path)
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass

    def stop_music(self) -> None:
        if not self.enabled:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

    def set_music_enabled(self, enabled: bool) -> None:
        if self.music_enabled == enabled:
            return
        self.music_enabled = enabled
        if self.music_enabled:
            self.play_music()
        else:
            self.stop_music()

    def toggle_music(self) -> None:
        self.set_music_enabled(not self.music_enabled)

    def play_slide(self) -> None:
        if self.slide_sound:
            self.slide_sound.play()

    def play_ending_sigh(self) -> None:
        if self.ending_sigh_sound:
            self.ending_sigh_sound.play()
