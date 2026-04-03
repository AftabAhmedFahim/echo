import math
import os
import pygame

from animation import AnimationClip
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


class VisualAssets:
    def __init__(self):
        self._background_cache: dict[int, pygame.Surface] = {}
        self._animation_cache: dict[str, dict[str, AnimationClip]] = {}

        self.background_files = {
            1: "assets/backgrounds/level_1.png",
            2: "assets/backgrounds/level_2.png",
            3: "assets/backgrounds/level_3.png",
        }
        self.base_entity_files = {
            "player": "assets/sprites/player.png",
            "patrol": "assets/sprites/patrol_drone.png",
            "seeker": "assets/sprites/seeker_drone.png",
            "heavy": "assets/sprites/heavy_drone.png",
            "interceptor": "assets/sprites/interceptor_drone.png",
            "boss": "assets/sprites/final_boss.png",
        }

    def get_level_background(self, level_id: int) -> pygame.Surface:
        if level_id not in self._background_cache:
            path = self.background_files.get(level_id, "")
            background = self._load_image(path, (SCREEN_WIDTH, SCREEN_HEIGHT))
            if background is None:
                background = self._build_fallback_background(level_id)
            self._background_cache[level_id] = background
        return self._background_cache[level_id]

    def get_player_animations(self) -> dict[str, AnimationClip]:
        return self._get_entity_animation_set("player", (48, 48), (80, 190, 255))

    def get_enemy_animations(self, enemy_kind: str) -> dict[str, AnimationClip]:
        config = {
            "patrol": ((44, 44), (220, 95, 95)),
            "seeker": ((42, 42), (255, 170, 90)),
            "heavy": ((56, 56), (180, 130, 255)),
            "interceptor": ((38, 38), (240, 220, 110)),
            "boss": ((96, 96), (255, 95, 120)),
        }
        size, color = config.get(enemy_kind, ((44, 44), (200, 200, 200)))
        return self._get_entity_animation_set(enemy_kind, size, color)

    def _get_entity_animation_set(
        self,
        key: str,
        target_size: tuple[int, int],
        fallback_color: tuple[int, int, int],
    ) -> dict[str, AnimationClip]:
        if key in self._animation_cache:
            return self._animation_cache[key]

        state_defs = {
            "idle": {"fps": 6.0, "frames": 6},
            "move": {"fps": 10.0, "frames": 8},
            "attack": {"fps": 14.0, "frames": 6},
        }

        clips: dict[str, AnimationClip] = {}
        for state, cfg in state_defs.items():
            disk_frames = self._load_state_frames_from_disk(key, state, target_size)
            if disk_frames:
                clips[state] = AnimationClip(disk_frames, fps=cfg["fps"], loop=True)
                continue

            base = self._load_image(self.base_entity_files.get(key, ""), target_size)
            if base is None:
                base = self._build_fallback_sprite(key, target_size, fallback_color)
            frames = self._animate_from_base(base, state, cfg["frames"], key == "boss")
            clips[state] = AnimationClip(frames, fps=cfg["fps"], loop=True)

        self._animation_cache[key] = clips
        return clips

    def _load_state_frames_from_disk(
        self,
        entity_key: str,
        state: str,
        target_size: tuple[int, int],
    ) -> list[pygame.Surface]:
        directory = os.path.join("assets", "sprites", entity_key, state)
        if not os.path.isdir(directory):
            return []

        frame_files = sorted(
            name for name in os.listdir(directory)
            if name.lower().endswith((".png", ".jpg", ".jpeg"))
        )
        frames: list[pygame.Surface] = []
        for file_name in frame_files:
            path = os.path.join(directory, file_name)
            img = self._load_image(path, target_size)
            if img is not None:
                frames.append(img)
        return frames

    def _load_image(self, path: str, target_size: tuple[int, int] | None = None) -> pygame.Surface | None:
        if not path or not os.path.exists(path):
            return None
        try:
            image = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return None

        if target_size is not None:
            image = pygame.transform.smoothscale(image, target_size)
        return image

    def _animate_from_base(
        self,
        base: pygame.Surface,
        state: str,
        frame_count: int,
        heavy_pulse: bool = False,
    ) -> list[pygame.Surface]:
        frames: list[pygame.Surface] = []
        w, h = base.get_size()

        for idx in range(frame_count):
            phase = (idx / max(1, frame_count - 1)) * math.tau
            scale = 1.0
            glow_strength = 0.0

            if state == "idle":
                scale = 1.0 + 0.03 * math.sin(phase)
                glow_strength = 0.07
            elif state == "move":
                scale = 1.0 + 0.07 * math.sin(phase)
                glow_strength = 0.15 + 0.05 * math.sin(phase + 1.2)
            elif state == "attack":
                scale = 1.0 + (0.11 if heavy_pulse else 0.09) * math.sin(phase * 1.5)
                glow_strength = 0.35 + 0.10 * math.sin(phase * 2.0)

            frame = pygame.Surface((w, h), pygame.SRCALPHA)
            scaled_w = max(2, int(w * scale))
            scaled_h = max(2, int(h * scale))
            scaled = pygame.transform.smoothscale(base, (scaled_w, scaled_h))
            frame.blit(scaled, scaled.get_rect(center=(w // 2, h // 2)))

            if glow_strength > 0:
                glow = pygame.Surface((w, h), pygame.SRCALPHA)
                alpha = int(255 * min(0.5, glow_strength))
                glow.fill((255, 255, 255, alpha))
                frame.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

            frames.append(frame)

        return frames

    def _build_fallback_sprite(
        self,
        key: str,
        size: tuple[int, int],
        color: tuple[int, int, int],
    ) -> pygame.Surface:
        w, h = size
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        center = pygame.Vector2(w / 2, h / 2)

        if key == "seeker":
            points = [
                (center.x, 5),
                (w - 6, h - 8),
                (6, h - 8),
            ]
            pygame.draw.polygon(surface, color, points)
        elif key == "heavy":
            pygame.draw.circle(surface, color, (int(center.x), int(center.y)), min(w, h) // 2 - 3)
            pygame.draw.rect(surface, (245, 220, 100), (w // 2 - 5, 6, 10, h - 12), border_radius=4)
        elif key == "interceptor":
            pygame.draw.circle(surface, color, (int(center.x), int(center.y)), min(w, h) // 2 - 4)
            pygame.draw.circle(surface, (255, 245, 200), (int(center.x), int(center.y)), min(w, h) // 2 - 10, 2)
        elif key == "boss":
            pygame.draw.circle(surface, color, (int(center.x), int(center.y)), min(w, h) // 2 - 2)
            pygame.draw.circle(surface, (255, 220, 200), (int(center.x), int(center.y)), min(w, h) // 2 - 16, 4)
        else:
            pygame.draw.circle(surface, color, (int(center.x), int(center.y)), min(w, h) // 2 - 4)

        return surface

    def _build_fallback_background(self, level_id: int) -> pygame.Surface:
        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        gradients = {
            1: ((24, 32, 42), (38, 62, 82)),
            2: ((28, 22, 18), (66, 44, 26)),
            3: ((12, 20, 36), (56, 22, 42)),
        }
        top, bottom = gradients.get(level_id, ((20, 24, 32), (36, 44, 60)))

        for y in range(SCREEN_HEIGHT):
            t = y / max(1, SCREEN_HEIGHT - 1)
            color = (
                int(top[0] + (bottom[0] - top[0]) * t),
                int(top[1] + (bottom[1] - top[1]) * t),
                int(top[2] + (bottom[2] - top[2]) * t),
            )
            pygame.draw.line(surface, color, (0, y), (SCREEN_WIDTH, y))

        for x in range(0, SCREEN_WIDTH, 96):
            pygame.draw.line(surface, (255, 255, 255, 20), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 96):
            pygame.draw.line(surface, (255, 255, 255, 16), (0, y), (SCREEN_WIDTH, y))

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 10, 42))
        surface.blit(overlay, (0, 0))
        return surface
