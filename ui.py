import pygame

from settings import WHITE, GREEN, RED, PANEL, BLACK, SCREEN_WIDTH, SCREEN_HEIGHT


class UI:
    def __init__(self):
        self.font_small = pygame.font.Font(None, 28)
        self.font_medium = pygame.font.Font(None, 38)
        self.font_large = pygame.font.Font(None, 64)

    def _draw_button(self, surface: pygame.Surface, rect: pygame.Rect, text: str) -> None:
        pygame.draw.rect(surface, PANEL, rect, border_radius=8)
        pygame.draw.rect(surface, WHITE, rect, 2, border_radius=8)
        label = self.font_medium.render(text, True, WHITE)
        surface.blit(label, label.get_rect(center=rect.center))

    def get_menu_buttons(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect]:
        center_x = SCREEN_WIDTH // 2 - 160
        start_rect = pygame.Rect(center_x, 330, 320, 48)
        settings_rect = pygame.Rect(center_x, 400, 320, 48)
        controls_rect = pygame.Rect(center_x, 470, 320, 48)
        exit_rect = pygame.Rect(center_x, 540, 320, 48)
        return start_rect, settings_rect, controls_rect, exit_rect

    def get_controls_buttons(self) -> tuple[pygame.Rect]:
        center_x = SCREEN_WIDTH // 2 - 160
        back_rect = pygame.Rect(center_x, 580, 320, 48)
        return (back_rect,)

    def get_settings_buttons(self) -> tuple[pygame.Rect, pygame.Rect]:
        center_x = SCREEN_WIDTH // 2 - 160
        music_rect = pygame.Rect(center_x, 350, 320, 48)
        back_rect = pygame.Rect(center_x, 420, 320, 48)
        return music_rect, back_rect

    def get_pause_buttons(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        center_x = SCREEN_WIDTH // 2 - 160
        continue_rect = pygame.Rect(center_x, 310, 320, 48)
        menu_rect = pygame.Rect(center_x, 380, 320, 48)
        music_rect = pygame.Rect(center_x, 450, 320, 48)
        return continue_rect, menu_rect, music_rect

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

    def draw_lives(self, surface: pygame.Surface, current: int, maximum: int) -> None:
        x, y = SCREEN_WIDTH - 280, 20
        pygame.draw.rect(surface, PANEL, (x, y, 260, 24), border_radius=4)
        pygame.draw.rect(surface, WHITE, (x, y, 260, 24), 2, border_radius=4)
        hearts = " ".join(["♥"] * max(0, current))
        text = self.font_small.render(f"Lives: {hearts}", True, RED)
        surface.blit(text, (x + 10, y + 2))

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
        info = self.font_medium.render("Click START to Begin", True, WHITE)
        help_1 = self.font_small.render("Use the menu below to continue", True, WHITE)
        help_2 = self.font_small.render("Choose an option below", True, WHITE)
        start_button, settings_button, controls_button, exit_button = self.get_menu_buttons()

        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        surface.blit(info, info.get_rect(center=(SCREEN_WIDTH // 2, 315)))
        surface.blit(help_1, help_1.get_rect(center=(SCREEN_WIDTH // 2, 560)))
        surface.blit(help_2, help_2.get_rect(center=(SCREEN_WIDTH // 2, 600)))
        self._draw_button(surface, start_button, "Start")
        self._draw_button(surface, settings_button, "Settings")
        self._draw_button(surface, controls_button, "Controls")
        self._draw_button(surface, exit_button, "Exit")

    def draw_controls(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 290, 170, 580, 460)
        pygame.draw.rect(surface, BLACK, panel, border_radius=14)
        pygame.draw.rect(surface, WHITE, panel, 2, border_radius=14)

        title = self.font_large.render("CONTROLS", True, WHITE)
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 210)))

        lines = [
            "WASD - Move",
            "Mouse - Aim",
            "Left Click - Shoot",
            "E or SPACE - Interact",
            "R - Restart level",
            "ESC - Pause or go back",
        ]

        y = 290
        for line in lines:
            text = self.font_medium.render(line, True, WHITE)
            surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, y)))
            y += 46

        back_rect = self.get_controls_buttons()[0]
        self._draw_button(surface, back_rect, "Back")

    def draw_settings(self, surface: pygame.Surface, music_enabled: bool) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 290, 170, 580, 320)
        pygame.draw.rect(surface, BLACK, panel, border_radius=14)
        pygame.draw.rect(surface, WHITE, panel, 2, border_radius=14)

        title = self.font_large.render("SETTINGS", True, WHITE)
        status = self.font_medium.render(f"Music: {'On' if music_enabled else 'Off'}", True, WHITE)
        music_rect, back_rect = self.get_settings_buttons()

        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        surface.blit(status, status.get_rect(center=(SCREEN_WIDTH // 2, 300)))
        self._draw_button(surface, music_rect, "Music Off" if music_enabled else "Music On")
        self._draw_button(surface, back_rect, "Back")

    def draw_pause(self, surface: pygame.Surface, music_enabled: bool) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        title = self.font_large.render("GAME PAUSED", True, WHITE)
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 230)))

        continue_rect, menu_rect, music_rect = self.get_pause_buttons()
        self._draw_button(surface, continue_rect, "Continue")
        self._draw_button(surface, menu_rect, "Main Menu")
        self._draw_button(surface, music_rect, "Music Off" if music_enabled else "Music On")

        hint = self.font_small.render("Use the buttons below", True, WHITE)
        surface.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 540)))

    def draw_level_transition(self, surface: pygame.Surface, progress: float) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 110))
        surface.blit(overlay, (0, 0))

        door_width = SCREEN_WIDTH // 2
        closed_offset = int(door_width * min(1.0, max(0.0, progress)))

        left_rect = pygame.Rect(-closed_offset, 0, door_width, SCREEN_HEIGHT)
        right_rect = pygame.Rect(SCREEN_WIDTH - door_width + closed_offset, 0, door_width, SCREEN_HEIGHT)

        pygame.draw.rect(surface, PANEL, left_rect)
        pygame.draw.rect(surface, PANEL, right_rect)
        pygame.draw.rect(surface, WHITE, left_rect, 3)
        pygame.draw.rect(surface, WHITE, right_rect, 3)

        center_x = SCREEN_WIDTH // 2
        scan_rect = pygame.Rect(center_x - 6, 0, 12, SCREEN_HEIGHT)
        glow = pygame.Surface((12, SCREEN_HEIGHT), pygame.SRCALPHA)
        glow.fill((120, 200, 255, 90))
        surface.blit(glow, scan_rect)

        title = self.font_large.render("ACCESS COMPLETE", True, WHITE)
        sub = self.font_medium.render("Opening route...", True, WHITE)
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 280)))
        surface.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 340)))

    def draw_game_over(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        title = self.font_large.render("GAME OVER", True, RED)
        info = self.font_medium.render("Press Enter to go to the Main Menu", True, WHITE)
        sub = self.font_small.render("All lives lost.", True, WHITE)

        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 270)))
        surface.blit(info, info.get_rect(center=(SCREEN_WIDTH // 2, 350)))
        surface.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 395)))

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

        title_img = self.font_large.render(title, True, WHITE)
        surface.blit(title_img, title_img.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
