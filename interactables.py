import math
import pygame

from settings import GREEN, YELLOW, ORANGE, CYAN, PURPLE, HOLD_INTERACT_TIME, INTERACT_RANGE


class Interactable:
    def __init__(self, x: int, y: int, width: int, height: int, label: str):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.active = False
        self.completed = False
        self.hold_progress = 0.0
        self.requires_hold = False

    def can_interact(self, player) -> bool:
        return self.rect.centerx - INTERACT_RANGE <= player.pos.x <= self.rect.centerx + INTERACT_RANGE and \
               self.rect.centery - INTERACT_RANGE <= player.pos.y <= self.rect.centery + INTERACT_RANGE

    def interact(self, dt: float, holding: bool) -> bool:
        if self.completed:
            return False

        if self.requires_hold:
            if holding:
                self.hold_progress += dt
                if self.hold_progress >= HOLD_INTERACT_TIME:
                    self.completed = True
                    self.active = True
                    return True
            else:
                self.hold_progress = 0.0
        else:
            self.completed = True
            self.active = True
            return True

        return False

    def reset_progress(self) -> None:
        self.hold_progress = 0.0

    def draw(self, surface: pygame.Surface) -> None:
        color = GREEN if self.completed else YELLOW
        pygame.draw.rect(surface, color, self.rect, border_radius=6)

    def get_prompt(self) -> str:
        if self.requires_hold:
            return f"Hold E - {self.label}"
        return f"Press E - {self.label}"


class Conduit(Interactable):
    def __init__(self, x: int, y: int, index: int):
        super().__init__(x, y, 34, 34, f"Activate Conduit {index}")
        self.index = index

    def draw(self, surface: pygame.Surface) -> None:
        color = CYAN if self.completed else (80, 130, 220)
        pygame.draw.rect(surface, color, self.rect, border_radius=4)


class SequenceSwitch(Interactable):
    def __init__(self, x: int, y: int, index: int):
        super().__init__(x, y, 40, 26, f"Flip Switch {index}")
        self.index = index
        self.allowed = False

    def draw(self, surface: pygame.Surface) -> None:
        if self.completed:
            color = GREEN
        elif self.allowed:
            color = ORANGE
        else:
            color = (100, 100, 100)
        pygame.draw.rect(surface, color, self.rect, border_radius=4)


class Antenna(Interactable):
    def __init__(self, x: int, y: int, index: int):
        super().__init__(x, y, 24, 70, f"Align Antenna {index}")
        self.index = index
        self.requires_hold = True

    def draw(self, surface: pygame.Surface) -> None:
        color = GREEN if self.completed else CYAN
        pygame.draw.rect(surface, color, self.rect)
        if not self.completed:
            progress_ratio = min(1.0, self.hold_progress / HOLD_INTERACT_TIME)
            pygame.draw.rect(surface, (40, 40, 40), (self.rect.x, self.rect.y - 8, self.rect.width, 5))
            pygame.draw.rect(surface, GREEN, (self.rect.x, self.rect.y - 8, int(self.rect.width * progress_ratio), 5))


class MessageFragment(Interactable):
    def __init__(self, x: int, y: int, text: str):
        super().__init__(x, y, 30, 30, "Recover Message Fragment")
        self.text = text

    def draw(self, surface: pygame.Surface) -> None:
        color = (180, 220, 255) if self.completed else (50, 150, 255)
        pygame.draw.circle(surface, color, self.rect.center, self.rect.width // 2)

class WeaponPickup(Interactable):
    def __init__(self, x: int, y: int, weapon_type: str):
        super().__init__(x, y, 24, 24, f"Pick up {weapon_type}")
        self.weapon_type = weapon_type
        self.requires_hold = False

    def draw(self, surface: pygame.Surface) -> None:
        if self.completed:
            return
        pygame.draw.rect(surface, PURPLE, self.rect, border_radius=4)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2, border_radius=4)

class Obstacle:
    def __init__(self, x: int, y: int, width: int, height: int, texture_id: str):
        self.rect = pygame.Rect(x, y, width, height)
        self.texture_id = texture_id

    def draw(self, surface: pygame.Surface, visuals) -> None:
        texture = visuals.get_prop_texture(self.texture_id)
        if texture:
            scaled = pygame.transform.scale(texture, (self.rect.width, self.rect.height))
            surface.blit(scaled, self.rect)
        else:
            pygame.draw.rect(surface, (100, 100, 110), self.rect)
            pygame.draw.rect(surface, (60, 60, 70), self.rect, 2)


class Portal:
    """Animated exit portal that appears when a level is completed.
    The player enters the next level by walking into the portal.
    """

    SIZE = 96  # display size in pixels (square)
    FPS = 9.0  # animation speed, one cycle per second
    INTERACT_RADIUS = 52  # how close the player centre must be to trigger

    def __init__(self, cx: int, cy: int, frames: list[pygame.Surface]):
        self.frames = frames
        self._frame_idx = 0.0
        self.rect = pygame.Rect(0, 0, self.SIZE, self.SIZE)
        self.rect.center = (cx, cy)
        self._time = 0.0  # used for glow pulse

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if self.frames:
            self._frame_idx = (self._frame_idx + dt * self.FPS) % len(self.frames)
        self._time += dt

    def player_entered(self, player) -> bool:
        """Return True when the player's centre is within the trigger radius."""
        px, py = int(player.pos.x), int(player.pos.y)
        cx, cy = self.rect.center
        dx, dy = px - cx, py - cy
        return (dx * dx + dy * dy) <= self.INTERACT_RADIUS ** 2

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        if self.frames:
            frame = self.frames[int(self._frame_idx) % len(self.frames)]
            surface.blit(frame, self.rect)
        else:
            # Fallback: glowing purple circle
            pygame.draw.circle(surface, (120, 60, 220), self.rect.center, self.SIZE // 2)
            pygame.draw.circle(surface, (200, 140, 255), self.rect.center, self.SIZE // 2, 3)

        # Animated outer glow ring
        pulse = 0.5 + 0.5 * math.sin(self._time * 4.0)
        radius = int(self.SIZE // 2 + 6 + 8 * pulse)
        alpha = int(80 + 100 * pulse)
        glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (180, 100, 255, alpha), (radius, radius), radius)
        surface.blit(glow_surf, glow_surf.get_rect(center=self.rect.center))

        # Label above the portal
        font = pygame.font.SysFont(None, 22)
        label = font.render(">> PORTAL  Enter to advance <<", True, (220, 180, 255))
        surface.blit(label, label.get_rect(centerx=self.rect.centerx, bottom=self.rect.top - 6))