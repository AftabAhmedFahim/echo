import math
import random
import pygame

from animation import Animator, AnimationClip
from settings import (
    RED,
    ORANGE,
    PURPLE,
    YELLOW,
    PATROL_SPEED,
    SEEKER_SPEED,
    HEAVY_SPEED,
    HEAVY_TURN_RATE,
    INTERCEPTOR_SPEED,
    PATROL_HEALTH,
    SEEKER_HEALTH,
    HEAVY_HEALTH,
    INTERCEPTOR_HEALTH,
    ENEMY_CONTACT_DAMAGE,
    INTERCEPTOR_EXPLOSION_DAMAGE,
    INTERCEPTOR_EXPLOSION_RADIUS,
    BOSS_HEALTH,
    BOSS_SPEED,
    BOSS_CONTACT_DAMAGE,
    BOSS_DASH_SPEED,
    BOSS_DASH_DURATION,
    BOSS_DASH_COOLDOWN,
)
from projectiles import EnemyBullet

class Enemy:
    def __init__(
        self,
        x: float,
        y: float,
        radius: int,
        health: int,
        color: tuple[int, int, int],
        animations: dict[str, AnimationClip] | None = None,
        contact_damage: int = ENEMY_CONTACT_DAMAGE,
    ):
        self.pos = pygame.Vector2(x, y)
        self.radius = radius
        self.max_health = health
        self.health = health
        self.color = color
        self.alive = True
        self.contact_cooldown = 0.0
        self.contact_damage = contact_damage
        self.angle = 0.0
        self.animator = Animator(animations, "idle") if animations else None
        self.projectiles: list[EnemyBullet] = []
        self.fire_cooldown = 0.0
        self.hover_timer = random.uniform(0, 2 * math.pi)
        self.hover_offset = 0.0
        self.sprite_flip_x = False
        self.facing_right = True

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.pos.x - self.radius),
            int(self.pos.y - self.radius),
            self.radius * 2,
            self.radius * 2,
        )

    def update(self, dt: float, player, walls: list[pygame.Rect]) -> None:
        if self.contact_cooldown > 0:
            self.contact_cooldown -= dt
        
        self.hover_timer += dt * 3.5
        self.hover_offset = math.sin(self.hover_timer) * 8.0
        
        if self.animator:
            self.animator.update(dt)

    def set_visual_state(self, moving: bool) -> None:
        if not self.animator:
            return
        if moving:
            self.animator.set_state("move")
        else:
            self.animator.set_state("idle")

    def move_with_walls(self, motion: pygame.Vector2, dt: float, walls: list[pygame.Rect]) -> None:
        self.pos.x += motion.x * dt
        rect = self.rect
        for wall in walls:
            if rect.colliderect(wall):
                if motion.x > 0:
                    self.pos.x = wall.left - self.radius
                elif motion.x < 0:
                    self.pos.x = wall.right + self.radius
                rect = self.rect

        self.pos.y += motion.y * dt
        rect = self.rect
        for wall in walls:
            if rect.colliderect(wall):
                if motion.y > 0:
                    self.pos.y = wall.top - self.radius
                elif motion.y < 0:
                    self.pos.y = wall.bottom + self.radius
                rect = self.rect

    def on_touch_player(self, player) -> None:
        if self.contact_cooldown <= 0:
            player.take_damage(self.contact_damage)
            self.contact_cooldown = 0.8

    def take_damage(self, amount: int, hit_direction: pygame.Vector2 | None = None) -> None:
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def draw_health(self, surface: pygame.Surface) -> None:
        width = self.radius * 2
        x = int(self.pos.x - self.radius)
        y = int(self.pos.y - self.radius - 10)
        pygame.draw.rect(surface, (40, 40, 40), (x, y, width, 5))
        fill = int(width * (self.health / self.max_health))
        pygame.draw.rect(surface, (60, 220, 90), (x, y, fill, 5))

    def _draw_sprite(self, surface: pygame.Surface) -> bool:
        if not self.animator:
            return False
        frame = self.animator.get_frame()
        if self.sprite_flip_x:
            drawn = frame if self.facing_right else pygame.transform.flip(frame, True, False)
        else:
            angle_degrees = -math.degrees(self.angle)
            drawn = pygame.transform.rotozoom(frame, angle_degrees, 1.0)

        # Apply hover offset to the visual rendering only, not collision
        rect = drawn.get_rect(center=(int(self.pos.x), int(self.pos.y + self.hover_offset)))
        surface.blit(drawn, rect)
        return True

    def draw(self, surface: pygame.Surface) -> None:
        if not self._draw_sprite(surface):
            pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)
        self.draw_health(surface)


class PatrolDrone(Enemy):
    def __init__(self, x: float, y: float, animations: dict[str, AnimationClip] | None = None):
        super().__init__(x, y, 16, PATROL_HEALTH, RED, animations=animations)
        self.start_pos = pygame.Vector2(x, y)
        self.direction = random.choice(
            [pygame.Vector2(1, 0), pygame.Vector2(-1, 0)]
        )
        self.patrol_range = random.randint(80, 150)
        self.charge_range = 220

    def update(self, dt: float, player, walls: list[pygame.Rect]) -> None:
        super().update(dt, player, walls)
        to_player = player.pos - self.pos
        distance = to_player.length() if to_player.length_squared() > 0 else 0

        if distance < self.charge_range:
            motion = to_player.normalize() * (PATROL_SPEED * 1.45) if distance > 0 else pygame.Vector2()
            attacking = True
        else:
            offset = self.pos - self.start_pos
            if offset.length() > self.patrol_range:
                self.direction *= -1
            motion = self.direction * PATROL_SPEED
            attacking = False

        if motion.length_squared() > 0:
            self.angle = math.atan2(motion.y, motion.x)
            
        old_pos = self.pos.copy()
        self.move_with_walls(motion, dt, walls)
        
        # If patrolling and hit a wall, flip patrol direction immediately
        if not attacking:
            if (motion.x != 0 and abs(self.pos.x - old_pos.x) < 0.05) or \
               (motion.y != 0 and abs(self.pos.y - old_pos.y) < 0.05):
                self.direction *= -1
                self.start_pos = self.pos.copy() # Reset patrol anchor entirely
        
        self.set_visual_state(moving=motion.length_squared() > 0.1)


class SeekerDrone(Enemy):
    def __init__(self, x: float, y: float, animations: dict[str, AnimationClip] | None = None):
        super().__init__(x, y, 14, SEEKER_HEALTH, ORANGE, animations=animations)

    def update(self, dt: float, player, walls: list[pygame.Rect]) -> None:
        super().update(dt, player, walls)
        to_player = player.pos - self.pos
        motion = to_player.normalize() * SEEKER_SPEED if to_player.length_squared() > 0 else pygame.Vector2()
        if motion.length_squared() > 0:
            self.angle = math.atan2(motion.y, motion.x)
        self.move_with_walls(motion, dt, walls)
        self.set_visual_state(moving=motion.length_squared() > 0.1)

    def draw(self, surface: pygame.Surface) -> None:
        if not self._draw_sprite(surface):
            points = [
                (self.pos.x + math.cos(self.angle) * 18, self.pos.y + math.sin(self.angle) * 18),
                (self.pos.x + math.cos(self.angle + 2.5) * 14, self.pos.y + math.sin(self.angle + 2.5) * 14),
                (self.pos.x + math.cos(self.angle - 2.5) * 14, self.pos.y + math.sin(self.angle - 2.5) * 14),
            ]
            pygame.draw.polygon(surface, self.color, points)
        self.draw_health(surface)


class HeavyDrone(Enemy):
    def __init__(self, x: float, y: float, animations: dict[str, AnimationClip] | None = None):
        super().__init__(x, y, 20, HEAVY_HEALTH, PURPLE, animations=animations)
        self.facing = pygame.Vector2(1, 0)

    def update(self, dt: float, player, walls: list[pygame.Rect]) -> None:
        super().update(dt, player, walls)
        to_player = player.pos - self.pos
        distance = to_player.length() if to_player.length_squared() > 0 else 0.0
        motion = to_player.normalize() * HEAVY_SPEED if to_player.length_squared() > 0 else pygame.Vector2()
        if motion.length_squared() > 0:
            desired_facing = motion.normalize()
            blend = min(1.0, dt * HEAVY_TURN_RATE)
            self.facing = self.facing.lerp(desired_facing, blend)
            if self.facing.length_squared() > 0:
                self.facing = self.facing.normalize()
                self.angle = math.atan2(self.facing.y, self.facing.x)
        self.move_with_walls(motion, dt, walls)
        self.set_visual_state(moving=motion.length_squared() > 0.1)

        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt
        
        if self.fire_cooldown <= 0 and to_player.length_squared() > 0 and distance < 200:
            self.fire_cooldown = 2.0
            direction = to_player.normalize()
            for angle_offset in [-0.15, 0, 0.15]:
                shoot_dir = pygame.Vector2(math.cos(self.angle + angle_offset), math.sin(self.angle + angle_offset))
                self.projectiles.append(EnemyBullet(self.pos.x, self.pos.y, shoot_dir.x * 200, shoot_dir.y * 200, 15))

    def take_damage(self, amount: int, hit_direction: pygame.Vector2 | None = None) -> None:
        # Damage only from behind.
        if hit_direction is None or self.facing.length_squared() == 0:
            return

        incoming = hit_direction.normalize()
        front_dot = self.facing.dot(-incoming)
        # Block only near-direct frontal hits so side shots can still damage it.
        if front_dot > 0.75:
            return

        super().take_damage(amount, hit_direction)

    def draw(self, surface: pygame.Surface) -> None:
        if not self._draw_sprite(surface):
            pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)
            shield_tip = self.pos + self.facing * 24
            pygame.draw.line(surface, YELLOW, self.pos, shield_tip, 6)
        self.draw_health(surface)


class InterceptorDrone(Enemy):
    def __init__(self, x: float, y: float, animations: dict[str, AnimationClip] | None = None):
        super().__init__(x, y, 12, INTERCEPTOR_HEALTH, YELLOW, animations=animations)
        self.exploded = False
        self.sprite_flip_x = True

    def update(self, dt: float, player, walls: list[pygame.Rect]) -> None:
        super().update(dt, player, walls)
        to_player = player.pos - self.pos
        motion = to_player.normalize() * INTERCEPTOR_SPEED if to_player.length_squared() > 0 else pygame.Vector2()
        if motion.length_squared() > 0:
            self.angle = math.atan2(motion.y, motion.x)
            if motion.x > 0.01:
                self.facing_right = True
            elif motion.x < -0.01:
                self.facing_right = False
        self.move_with_walls(motion, dt, walls)
        self.set_visual_state(moving=motion.length_squared() > 0.1)

    def explode_if_needed(self, player) -> bool:
        if self.exploded or not self.alive:
            return False

        distance = self.pos.distance_to(player.pos)
        if distance <= self.radius + player.radius + 10:
            if distance <= INTERCEPTOR_EXPLOSION_RADIUS:
                player.take_damage(INTERCEPTOR_EXPLOSION_DAMAGE)
            self.exploded = True
            self.alive = False
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        if not self._draw_sprite(surface):
            pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)
            pulse = int(6 + (pygame.time.get_ticks() % 400) / 100)
            pygame.draw.circle(surface, (255, 230, 150), (int(self.pos.x), int(self.pos.y)), self.radius + pulse, 1)
        self.draw_health(surface)


class FinalBoss(Enemy):
    def __init__(self, x: float, y: float, animations: dict[str, AnimationClip] | None = None):
        super().__init__(
            x,
            y,
            radius=34,
            health=BOSS_HEALTH,
            color=(250, 95, 125),
            animations=animations,
            contact_damage=BOSS_CONTACT_DAMAGE,
        )
        self.dash_timer = 0.0
        self.dash_cooldown = 1.8
        self.dash_velocity = pygame.Vector2(0, 0)

    def update(self, dt: float, player, walls: list[pygame.Rect]) -> None:
        super().update(dt, player, walls)
        to_player = player.pos - self.pos
        distance = to_player.length() if to_player.length_squared() > 0 else 0.0

        self.dash_cooldown -= dt
        dashing = False

        if self.dash_timer > 0:
            self.dash_timer -= dt
            motion = self.dash_velocity
            dashing = True
        else:
            motion = pygame.Vector2(0, 0)
            if to_player.length_squared() > 0:
                motion = to_player.normalize() * BOSS_SPEED
                self.angle = math.atan2(motion.y, motion.x)

            if self.dash_cooldown <= 0 and distance < 320 and to_player.length_squared() > 0:
                self.dash_timer = BOSS_DASH_DURATION
                self.dash_cooldown = BOSS_DASH_COOLDOWN
                self.dash_velocity = to_player.normalize() * BOSS_DASH_SPEED
                motion = self.dash_velocity
                dashing = True

        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt

        if self.fire_cooldown <= 0 and self.dash_timer <= 0 and distance < 450 and to_player.length_squared() > 0:
            self.fire_cooldown = 1.2
            for angle_offset in [-0.25, -0.12, 0, 0.12, 0.25]:
                shoot_dir = pygame.Vector2(math.cos(self.angle + angle_offset), math.sin(self.angle + angle_offset))
                self.projectiles.append(EnemyBullet(self.pos.x, self.pos.y, shoot_dir.x * 220, shoot_dir.y * 220, 20))

        if motion.length_squared() > 0:
            self.angle = math.atan2(motion.y, motion.x)
        self.move_with_walls(motion, dt, walls)
        self.set_visual_state(moving=motion.length_squared() > 0.1 or dashing)

    def on_touch_player(self, player) -> None:
        if self.contact_cooldown <= 0:
            player.take_damage(self.contact_damage)
            self.contact_cooldown = 0.45
