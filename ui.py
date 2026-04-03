import math
import pygame

from settings import WHITE, GREEN, RED, PANEL, BLACK, SCREEN_WIDTH, SCREEN_HEIGHT


class UI:
    def __init__(self):
        self.font_small = pygame.font.Font(None, 28)
        self.font_medium = pygame.font.Font(None, 38)
        self.font_large = pygame.font.Font(None, 64)

    def draw_panel_text(self, surface: pygame.Surface, text: str, x: int, y: int, color=WHITE) -> None:
        img = self.font_small.render(text, True, color)
        surface.blit(img, (x, y))

    def draw_health_bar(self, surface: pygame.Surface, current: int, maximum: int) -> None:
        x, y, w, h = 20, 20, 240, 24
        pygame.draw.rect(surface, PANEL, (x, y, w, h), border_radius=4)
        fill = int(w * (current / maximum))
        pygame.draw.rect(surface, GREEN if current > maximum * 0.35 else RED, (x, y, fill, h), border_radius=4)
        pygame.draw.rect(surface, WHITE, (x, y, w, h), 2, border_radius=4)
        self.draw_panel_text(surface, f"HP: {current}/{maximum}", x + 8, y + 2)

    def draw_objective(self, surface: pygame.Surface, level_name: str, objective: str) -> None:
        title = self.font_medium.render(level_name, True, WHITE)
        surface.blit(title, (20, 58))
        obj = self.font_small.render(objective, True, WHITE)
        surface.blit(obj, (20, 96))

    def draw_prompt(self, surface: pygame.Surface, text: str) -> None:
        box = pygame.Rect(SCREEN_WIDTH // 2 - 160, SCREEN_HEIGHT - 70, 320, 40)
        pygame.draw.rect(surface, PANEL, box, border_radius=8)
        pygame.draw.rect(surface, WHITE, box, 2, border_radius=8)
        txt = self.font_small.render(text, True, WHITE)
        surface.blit(txt, (box.x + 15, box.y + 10))

    def draw_menu(self, surface: pygame.Surface) -> None:
        title = self.font_large.render("ECHO PROTOCOL", True, WHITE)
        info = self.font_medium.render("Press ENTER to Begin", True, WHITE)
        help_1 = self.font_small.render("WASD Move  |  Mouse Aim  |  Left Click Shoot", True, WHITE)
        help_2 = self.font_small.render("E or SPACE Interact  |  R Restart Level", True, WHITE)

        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        surface.blit(info, info.get_rect(center=(SCREEN_WIDTH // 2, 320)))
        surface.blit(help_1, help_1.get_rect(center=(SCREEN_WIDTH // 2, 390)))
        surface.blit(help_2, help_2.get_rect(center=(SCREEN_WIDTH // 2, 430)))

    def draw_game_over(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        title = self.font_large.render("SYSTEM FAILURE", True, RED)
        info = self.font_medium.render("Press R to restart level", True, WHITE)

        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 280)))
        surface.blit(info, info.get_rect(center=(SCREEN_WIDTH // 2, 360)))

    def draw_ending(self, surface: pygame.Surface) -> None:
        title = self.font_large.render("BROADCAST COMPLETE", True, GREEN)
        info = self.font_medium.render("ECHO restored the network.", True, WHITE)
        sub = self.font_small.render("Press ESC to quit.", True, WHITE)

        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 260)))
        surface.blit(info, info.get_rect(center=(SCREEN_WIDTH // 2, 340)))
        surface.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 400)))

    def draw_loading_transition(
        self,
        surface: pygame.Surface,
        title: str,
        timer: float,
        duration: float,
    ) -> None:
        if timer <= 0:
            return

        progress = 1.0 - (timer / max(0.001, duration))
        alpha = int(220 * (1.0 - min(1.0, progress)))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 12, 18, alpha))
        surface.blit(overlay, (0, 0))

        center = pygame.Vector2(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40)
        angle = pygame.time.get_ticks() * 0.010
        ring_radius = 28
        for idx in range(8):
            dot_angle = angle + idx * (math.tau / 8)
            x = int(center.x + math.cos(dot_angle) * ring_radius)
            y = int(center.y + math.sin(dot_angle) * ring_radius)
            brightness = 90 + idx * 18
            pygame.draw.circle(surface, (brightness, brightness, 255), (x, y), 4)

        title_img = self.font_medium.render(title, True, WHITE)
        loading_img = self.font_small.render("Synchronizing systems...", True, WHITE)
        surface.blit(title_img, title_img.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))
        surface.blit(loading_img, loading_img.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 18)))
