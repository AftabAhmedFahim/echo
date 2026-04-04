import math
import os
import pygame

from animation import AnimationClip
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


class VisualAssets:
    def __init__(self):
        self._background_cache: dict[object, pygame.Surface] = {}
        self._animation_cache: dict[str, dict[str, AnimationClip]] = {}

        self.background_files = {
            1: "assets/backgrounds/level_1.png",
            2: "assets/backgrounds/level_2.png",
            3: "assets/backgrounds/level_3.png",
        }
        self.room_background_files = {
            (3, "command_core"): "assets/backgrounds/level_3_boss.png",
        }
        self.base_entity_files = {
            "player": "assets/sprites/player.png",
            "drone": "assets/sprites/drone.png",
        }

    def get_level_background(self, level_id: int, room_id: str | None = None) -> pygame.Surface:
        cache_key = (level_id, room_id or "")
        if cache_key not in self._background_cache:
            # Room-specific background overrides level defaults (used for Level 3 final boss room).
            image_path = self.room_background_files.get((level_id, room_id or ""))
            if image_path is None:
                image_path = self.background_files.get(level_id, "")

            image = self._load_image(image_path, (SCREEN_WIDTH, SCREEN_HEIGHT))
            if image is not None:
                self._background_cache[cache_key] = image
            else:
                self._background_cache[cache_key] = self._build_fallback_background(level_id)

        return self._background_cache[cache_key]

    def get_wall_texture(self) -> pygame.Surface:
        if "wall_texture" not in self._background_cache:
            wall_tile = self._load_image("assets/backgrounds/sci_fi_wall.png", None)
            wall_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            if wall_tile:
                tile_w, tile_h = wall_tile.get_size()
                new_size = (int(tile_w * 0.6), int(tile_h * 0.6))
                wall_tile = pygame.transform.scale(wall_tile, new_size)
                tile_w, tile_h = wall_tile.get_size()
                
                for x in range(0, SCREEN_WIDTH, tile_w):
                    for y in range(0, SCREEN_HEIGHT, tile_h):
                        wall_surf.blit(wall_tile, (x, y))
            else:
                wall_surf.fill((60, 65, 75))
            self._background_cache["wall_texture"] = wall_surf
        return self._background_cache["wall_texture"]

    def get_menu_background(self) -> pygame.Surface | None:
        cache_key = "menu_bg"
        if cache_key not in self._background_cache:
            img = self._load_image("assets/menu_bg.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
            if img:
                self._background_cache[cache_key] = img
        return self._background_cache.get(cache_key)

    def get_prop_texture(self, texture_id: str) -> pygame.Surface | None:
        cache_key = f"prop_{texture_id}"
        if cache_key not in self._background_cache:
            image = self._load_image(f"assets/props/{texture_id}.png")
            if image is None:
                image = self._load_image(f"assets/{texture_id}.png")
            if image:
                self._background_cache[cache_key] = image
            else:
                return None
        return self._background_cache[cache_key]

    def get_player_animations(self) -> dict[str, AnimationClip]:
        if "player" in self._animation_cache:
            return self._animation_cache["player"]

        state_defs = {"idle": 1, "move": 8, "pickup": 6}
        directions = ["up", "down", "left", "right"]
        clips = {}
        for state, base_frames in state_defs.items():
            for d in directions:
                key = f"{state}_{d}"
                disk_frames = self._load_state_frames_from_disk("player", key, (64, 64))
                if disk_frames:
                    fps = 10.0 if state == "move" else 6.0
                    clips[key] = AnimationClip(disk_frames, fps=fps, loop=(state != "pickup"))
                else:
                    clips[key] = AnimationClip([pygame.Surface((64, 64))], fps=1)

        self._animation_cache["player"] = clips
        return clips

    def get_enemy_animations(self, enemy_kind: str) -> dict[str, AnimationClip]:
        config = {
            "patrol": ((48, 48), (220, 95, 95)),
            "seeker": ((42, 42), (255, 170, 90)),
            "heavy": ((64, 64), (180, 130, 255)),
            "interceptor": ((38, 38), (240, 220, 110)),
            "boss": ((96, 96), (255, 95, 120)),
            "drone": ((54, 54), (200, 200, 200)),
        }
        size, color = config.get(enemy_kind, ((44, 44), (200, 200, 200)))
        
        # Override key for the core high-quality drone assets
        # Every enemy now uses the new "drone" animated disk-frames.
        return self._get_entity_animation_set("drone", size, color)

    def _get_entity_animation_set(
        self,
        key: str,
        target_size: tuple[int, int],
        fallback_color: tuple[int, int, int],
    ) -> dict[str, AnimationClip]:
        # Include size in cache key so each enemy type gets its own correctly-sized frames
        cache_key = f"{key}_{target_size[0]}x{target_size[1]}"
        if cache_key in self._animation_cache:
            return self._animation_cache[cache_key]

        state_defs = {
            "idle": {"fps": 6.0, "frames": 6},
            "move": {"fps": 10.0, "frames": 8},
            "attack": {"fps": 14.0, "frames": 6},
        }

        clips: dict[str, AnimationClip] = {}

        # Check for demo.png sprite sheet first
        sheet_path = os.path.join("assets", "sprites", "demo.png")
        if os.path.exists(sheet_path):
            clips = self._load_from_sprite_sheet(sheet_path, target_size)
            self._animation_cache[cache_key] = clips
            return clips

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

        self._animation_cache[cache_key] = clips
        return clips

    def _load_from_sprite_sheet(self, path: str, target_size: tuple[int, int]) -> dict[str, AnimationClip]:
        sheet = pygame.image.load(path).convert_alpha()
        sw, sh = sheet.get_size()
        cols, rows = 8, 5
        fw, fh = sw // cols, sh // rows
        
        state_names = ["idle", "move", "attack", "hurt", "death"]
        clips: dict[str, AnimationClip] = {}
        
        for r in range(min(len(state_names), rows)):
            frames = []
            for c in range(cols):
                rect = pygame.Rect(c * fw, r * fh, fw, fh)
                frame = sheet.subsurface(rect)
                if target_size:
                    frame = pygame.transform.smoothscale(frame, target_size)
                frames.append(frame)
            
            state = state_names[r]
            fps = 10.0 if state == "move" else 8.0
            clips[state] = AnimationClip(frames, fps=fps, loop=True)
            
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

    def _load_image(
        self, path: str, target_size: tuple[int, int] | None = None, colorkey: tuple[int, int, int] | None = None
    ) -> pygame.Surface | None:
        if not path or not os.path.exists(path):
            return None
        try:
            image = pygame.image.load(path).convert_alpha()
            if colorkey is not None:
                image.set_colorkey(colorkey)
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

        # Render complex native robotic geometries
        if key == "seeker":
            # Stealth Swept-wing Fighter frame (orange)
            pts = [(w, h // 2), (0, h), (w // 4, h // 2), (0, 0)]
            pygame.draw.polygon(surface, color, pts)
            pygame.draw.polygon(surface, (255, 200, 100), pts, 2)
            pygame.draw.circle(surface, (0, 255, 255), (w // 2, h // 2), 4)

        elif key == "heavy":
            # Bulky Octagonal Tank hull (purple)
            hull = [(w//4, 0), (w*3//4, 0), (w, h//4), (w, h*3//4), (w*3//4, h), (w//4, h), (0, h*3//4), (0, h//4)]
            pygame.draw.polygon(surface, color, hull)
            pygame.draw.polygon(surface, (50, 50, 60), hull, 3) 
            pygame.draw.rect(surface, (80, 80, 90), (w//2, h//2 - 6, w//2, 12)) # Heavy Cannon
            pygame.draw.circle(surface, (255, 255, 0), (w//2, h//2), 6) # Heat Core

        elif key == "interceptor":
            # Spiked hazard payload frame (yellow)
            pts = [(w, h//2), (w*3//4, h*3//4), (w//2, h), (w//4, h*3//4), (0, h//2), (w//4, h//4), (w//2, 0), (w*3//4, h//4)]
            pygame.draw.polygon(surface, (50, 50, 50), pts)
            pygame.draw.polygon(surface, color, pts, 3)
            pygame.draw.circle(surface, (255, 100, 0), (w//2, h//2), 6) # Explosive Payload

        elif key == "boss":
            # Massive dreadnought hull (red/purple)
            hull = [(w, h//2), (w*3//4, h), (w//4, h*3//4), (0, h*3//4), (0, h//4), (w//4, h//4), (w*3//4, 0)]
            pygame.draw.polygon(surface, color, hull)
            pygame.draw.polygon(surface, (80, 30, 40), hull, 4)
            pygame.draw.circle(surface, (0, 255, 255), (w*3//4, h//2), 10) # Main visual sensor
            pygame.draw.circle(surface, (0, 255, 255), (w//2, h//4 + 8), 6)
            pygame.draw.circle(surface, (0, 255, 255), (w//2, h*3//4 - 8), 6)

        else:
            # Patrol hovercraft frame (red)
            pygame.draw.rect(surface, color, (w//4, h//4, w//2, h//2), border_radius=4)
            pygame.draw.rect(surface, (100, 100, 110), (w//4, 0, w//2, h//4)) # Top thruster pod
            pygame.draw.rect(surface, (100, 100, 110), (w//4, h*3//4, w//2, h//4)) # Bottom thruster pod
            pygame.draw.circle(surface, (0, 255, 255), (w//2 + 4, h//2), 5) # Forward optic lens

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
