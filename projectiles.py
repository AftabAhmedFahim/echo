import pygame

from settings import CYAN


class Bullet:
    def __init__(self, x: float, y: float, vx: float, vy: float, damage: int):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(vx, vy)
        self.damage = damage
        self.radius = 4
        self.alive = True

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.pos.x - self.radius),
            int(self.pos.y - self.radius),
            self.radius * 2,
            self.radius * 2,
        )

    def update(self, dt: float, walls: list[pygame.Rect], screen_rect: pygame.Rect) -> None:
        if not self.alive:
            return

        self.pos += self.vel * dt

        if not screen_rect.collidepoint(self.pos.x, self.pos.y):
            self.alive = False
            return

        for wall in walls:
            if wall.collidepoint(self.pos.x, self.pos.y):
                self.alive = False
                return

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, CYAN, (int(self.pos.x), int(self.pos.y)), self.radius)