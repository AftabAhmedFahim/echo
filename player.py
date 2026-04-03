import math
import pygame

from animation import Animator, AnimationClip
from settings import (
    PLAYER_SIZE,
    PLAYER_SPEED,
    PLAYER_MAX_HEALTH,
    PLAYER_FIRE_COOLDOWN,
    PLAYER_BULLET_SPEED,
    PLAYER_BULLET_DAMAGE,
    PLAYER_RESPAWN_INVULN,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)


class Player:
    def __init__(self, x: float, y: float, animations: dict[str, AnimationClip] | None = None):
        self.spawn_pos = pygame.Vector2(x, y)
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        self.radius = PLAYER_SIZE // 2
        self.max_health = PLAYER_MAX_HEALTH
        self.health = PLAYER_MAX_HEALTH
        self.fire_cooldown = 0.0
        self.invuln_timer = 0.0
        self.is_dead = False
        self.facing_angle = 0.0
        self.attack_anim_timer = 0.0
        self.animator = Animator(animations, "idle") if animations else None

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.pos.x - self.radius),
            int(self.pos.y - self.radius),
            self.radius * 2,
            self.radius * 2,
        )

    def update(self, dt: float, walls: list[pygame.Rect]) -> None:
        if self.is_dead:
            return

        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)

        if keys[pygame.K_w]:
            move.y -= 1
        if keys[pygame.K_s]:
            move.y += 1
        if keys[pygame.K_a]:
            move.x -= 1
        if keys[pygame.K_d]:
            move.x += 1

        if move.length_squared() > 0:
            move = move.normalize()

        self.vel = move * PLAYER_SPEED
        self._move_axis(self.vel.x * dt, 0, walls)
        self._move_axis(0, self.vel.y * dt, walls)

        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        aim = mouse_pos - self.pos
        if aim.length_squared() > 0:
            self.facing_angle = math.atan2(aim.y, aim.x)

        self.pos.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.pos.y))

        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt
        if self.invuln_timer > 0:
            self.invuln_timer -= dt
        if self.attack_anim_timer > 0:
            self.attack_anim_timer -= dt

        if self.animator:
            if self.attack_anim_timer > 0:
                self.animator.set_state("attack")
            elif self.vel.length_squared() > 0.1:
                self.animator.set_state("move")
            else:
                self.animator.set_state("idle")
            self.animator.update(dt)

    def _move_axis(self, dx: float, dy: float, walls: list[pygame.Rect]) -> None:
        self.pos.x += dx
        rect = self.rect
        for wall in walls:
            if rect.colliderect(wall):
                if dx > 0:
                    self.pos.x = wall.left - self.radius
                elif dx < 0:
                    self.pos.x = wall.right + self.radius
                rect = self.rect

        self.pos.y += dy
        rect = self.rect
        for wall in walls:
            if rect.colliderect(wall):
                if dy > 0:
                    self.pos.y = wall.top - self.radius
                elif dy < 0:
                    self.pos.y = wall.bottom + self.radius
                rect = self.rect

    def can_shoot(self) -> bool:
        return (not self.is_dead) and self.fire_cooldown <= 0

    def shoot(self):
        if not self.can_shoot():
            return None

        direction = pygame.Vector2(math.cos(self.facing_angle), math.sin(self.facing_angle))
        self.fire_cooldown = PLAYER_FIRE_COOLDOWN
        self.attack_anim_timer = 0.16
        return {
            "x": self.pos.x + direction.x * (self.radius + 8),
            "y": self.pos.y + direction.y * (self.radius + 8),
            "vx": direction.x * PLAYER_BULLET_SPEED,
            "vy": direction.y * PLAYER_BULLET_SPEED,
            "damage": PLAYER_BULLET_DAMAGE,
        }

    def take_damage(self, amount: int) -> None:
        if self.invuln_timer > 0 or self.is_dead:
            return

        self.health -= amount
        self.invuln_timer = 0.2
        if self.health <= 0:
            self.health = 0
            self.is_dead = True

    def respawn(self) -> None:
        self.pos = self.spawn_pos.copy()
        self.health = self.max_health
        self.fire_cooldown = 0.0
        self.invuln_timer = PLAYER_RESPAWN_INVULN
        self.is_dead = False
        self.attack_anim_timer = 0.0
        if self.animator:
            self.animator.set_state("idle", restart=True)

    def draw(self, surface: pygame.Surface) -> None:
        if self.animator:
            frame = self.animator.get_frame()
            angle_degrees = -math.degrees(self.facing_angle)
            rotated = pygame.transform.rotozoom(frame, angle_degrees, 1.0)
            rect = rotated.get_rect(center=(int(self.pos.x), int(self.pos.y)))

            if self.invuln_timer > 0 and int(self.invuln_timer * 20) % 2 == 0:
                rotated = rotated.copy()
                rotated.set_alpha(140)
            surface.blit(rotated, rect)
            return

        pygame.draw.circle(surface, (70, 150, 255), (int(self.pos.x), int(self.pos.y)), self.radius)
        gun_tip = (
            int(self.pos.x + math.cos(self.facing_angle) * (self.radius + 10)),
            int(self.pos.y + math.sin(self.facing_angle) * (self.radius + 10)),
        )
        pygame.draw.line(surface, (230, 240, 255), (int(self.pos.x), int(self.pos.y)), gun_tip, 4)
