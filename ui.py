import pygame
import math

from settings import WHITE, GREEN, RED, PANEL, BLACK, SCREEN_WIDTH, SCREEN_HEIGHT

CYAN       = (0, 255, 255)
CYAN_DIM   = (0, 120, 140)
ACCENT     = (80, 200, 255)
ACCENT_DIM = (30, 80, 110)
NAVY_TRANSPARENT = (8, 16, 32, 220)


class UI:
    def __init__(self):
        self.font_small  = pygame.font.Font(None, 26)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_large  = pygame.font.Font(None, 62)
        self.font_title  = pygame.font.Font(None, 96)

    def _draw_button(self, surface: pygame.Surface, rect: pygame.Rect, text: str, highlight: bool = False) -> None:
        mouse_pos = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse_pos) or highlight

        # Filled background — brighter when hovered
        bg_color = (18, 48, 72) if hover else (10, 24, 40)
        pygame.draw.rect(surface, bg_color, rect, border_radius=6)

        # Left accent bar
        bar_color = CYAN if hover else ACCENT_DIM
        pygame.draw.rect(surface, bar_color, (rect.left, rect.top + 6, 4, rect.height - 12), border_radius=2)

        # Outer border
        border_color = CYAN if hover else (30, 70, 100)
        pygame.draw.rect(surface, border_color, rect, 2 if hover else 1, border_radius=6)

        # Glow overlay when hovered
        if hover:
            glow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            glow.fill((0, 200, 255, 22))
            surface.blit(glow, rect)

        # Text — offset slightly right to account for accent bar
        text_color = WHITE if hover else (160, 210, 240)
        txt_surf = self.font_medium.render(text, True, text_color)
        txt_rect = txt_surf.get_rect(midleft=(rect.left + 20, rect.centery))
        surface.blit(txt_surf, txt_rect)

        # Chevron arrow on the right when hovered
        if hover:
            ax = rect.right - 22
            ay = rect.centery
            pts = [(ax, ay - 7), (ax + 8, ay), (ax, ay + 7)]
            pygame.draw.lines(surface, CYAN, False, pts, 2)

    def _draw_cyber_panel(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        c = 35  # Chamfer distance
        points = [
            (rect.left + c, rect.top),
            (rect.right - c, rect.top),
            (rect.right, rect.top + c),
            (rect.right, rect.bottom - c),
            (rect.right - c, rect.bottom),
            (rect.left + c, rect.bottom),
            (rect.left, rect.bottom - c),
            (rect.left, rect.top + c),
        ]
        bg = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        # Translucent highly saturated back
        pygame.draw.polygon(bg, (4, 12, 24, 230), points)
        
        # Subdued geometric background grid
        for i in range(rect.top + 15, rect.bottom, 28):
            pygame.draw.line(bg, (0, 220, 255, 14), (rect.left + 8, i), (rect.right - 8, i))
        for j in range(rect.left + 15, rect.right, 28):
            pygame.draw.line(bg, (0, 220, 255, 14), (j, rect.top + 8), (j, rect.bottom - 8))

        # Layered dimensional sci-fi borders
        pygame.draw.polygon(bg, (0, 80, 120, 150), points, 6)
        pygame.draw.polygon(bg, CYAN, points, 2)
        
        # Tech alignment markings on corners
        pygame.draw.line(bg, WHITE, (rect.left + c + 10, rect.top), (rect.left + c + 120, rect.top), 4)
        pygame.draw.line(bg, WHITE, (rect.left, rect.top + c + 10), (rect.left, rect.top + c + 80), 4)
        
        surface.blit(bg, (0, 0))

    def get_menu_buttons(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect]:
        # Right panel buttons — vertically stacked
        bx = SCREEN_WIDTH // 2 + 60
        bw, bh = 340, 54
        start_rect    = pygame.Rect(bx, 310, bw, bh)
        settings_rect = pygame.Rect(bx, 385, bw, bh)
        controls_rect = pygame.Rect(bx, 460, bw, bh)
        exit_rect     = pygame.Rect(bx, 535, bw, bh)
        return start_rect, settings_rect, controls_rect, exit_rect

    def get_controls_buttons(self) -> tuple[pygame.Rect]:
        center_x = SCREEN_WIDTH // 2 - 160
        back_rect = pygame.Rect(center_x, 580, 320, 48)
        return (back_rect,)

    def get_settings_buttons(self) -> tuple[pygame.Rect, pygame.Rect]:
        center_x = SCREEN_WIDTH // 2 - 200
        music_rect = pygame.Rect(center_x, 480, 400, 52)
        back_rect = pygame.Rect(center_x, 550, 400, 52)
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

    def _draw_menu_background(self, surface: pygame.Surface) -> None:
        """Dark gradient background with subtle hex-grid scanlines."""
        surface.fill((6, 10, 18))
        # Horizontal scanlines
        for y in range(0, SCREEN_HEIGHT, 4):
            alpha = 18 if y % 8 == 0 else 8
            line = pygame.Surface((SCREEN_WIDTH, 1), pygame.SRCALPHA)
            line.fill((0, 180, 255, alpha))
            surface.blit(line, (0, y))
        # Vertical accent lines
        divider_x = SCREEN_WIDTH // 2 + 20
        pygame.draw.line(surface, (0, 60, 90), (divider_x, 60), (divider_x, SCREEN_HEIGHT - 60), 1)

    def draw_menu(self, surface: pygame.Surface, visuals=None) -> None:
        # --- Background ---
        if visuals:
            bg = visuals.get_menu_background()
            if bg:
                surface.blit(bg, (0, 0))
            else:
                self._draw_menu_background(surface)
        else:
            self._draw_menu_background(surface)

        # ── LEFT PANEL  (logo + lore) ──────────────────────────────────────
        lx = 80
        divider_x = SCREEN_WIDTH // 2 + 20

        # Subtle left-panel tint
        left_bg = pygame.Surface((divider_x - lx - 20, SCREEN_HEIGHT - 80), pygame.SRCALPHA)
        left_bg.fill((0, 30, 55, 60))
        surface.blit(left_bg, (lx - 10, 40))

        # Game title — two lines for impact
        t1 = self.font_title.render("ECHO", True, CYAN)
        t2 = self.font_large.render("PROTOCOL", True, (160, 220, 255))
        surface.blit(t1, t1.get_rect(topleft=(lx, 90)))
        surface.blit(t2, t2.get_rect(topleft=(lx, 175)))

        # Horizontal accent line under title
        pygame.draw.line(surface, CYAN, (lx, 248), (divider_x - 40, 248), 2)
        pygame.draw.line(surface, ACCENT_DIM, (lx, 252), (divider_x - 40, 252), 1)

        # Version / subtitle tag
        ver = self.font_small.render("v1.0  //  STATION DEFENCE SIM", True, (60, 130, 160))
        surface.blit(ver, (lx, 262))

        # Lore block
        lore_lines = [
            "A catastrophic incident has caused the",
            "station AI to collapse. All security",
            "drones are compromised and hostile.",
            "",
            "You are the last functional unit.",
            "Recover the mission logs and",
            "shut down the rogue core.",
        ]
        ly = 310
        for line in lore_lines:
            if line == "":
                ly += 10
                continue
            col = (100, 160, 200) if ly < 360 else (70, 120, 160)
            txt = self.font_small.render(line, True, col)
            surface.blit(txt, (lx, ly))
            ly += 28

        # Status badge at bottom of left panel
        badge_y = SCREEN_HEIGHT - 120
        pygame.draw.rect(surface, (0, 40, 60), (lx - 4, badge_y, 260, 30), border_radius=4)
        pygame.draw.rect(surface, ACCENT_DIM, (lx - 4, badge_y, 260, 30), 1, border_radius=4)
        status = self.font_small.render("SYSTEM STATUS:  ONLINE", True, GREEN)
        surface.blit(status, (lx + 6, badge_y + 6))

        # ── RIGHT PANEL  (buttons) ────────────────────────────────────────
        rx = divider_x + 40
        rw = SCREEN_WIDTH - rx - 60

        # Right-panel header
        hdr = self.font_medium.render("MAIN MENU", True, (80, 160, 200))
        surface.blit(hdr, hdr.get_rect(topleft=(rx, 230)))
        pygame.draw.line(surface, ACCENT_DIM, (rx, 266), (rx + rw, 266), 1)

        start_button, settings_button, controls_button, exit_button = self.get_menu_buttons()
        self._draw_button(surface, start_button,    "Play")
        self._draw_button(surface, settings_button, "Settings")
        self._draw_button(surface, controls_button, "Controls")
        self._draw_button(surface, exit_button,     "Exit")

        # Right-panel footer hint
        hint = self.font_small.render("Press Enter to Play", True, (50, 90, 110))
        surface.blit(hint, hint.get_rect(topleft=(rx, 614)))

    def draw_controls(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 290, 170, 580, 460)
        self._draw_cyber_panel(surface, panel)

        title = self.font_large.render("CONTROLS", True, CYAN)
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
        import random
        # Full screen deep vignette
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 5, 15, 215))
        surface.blit(overlay, (0, 0))

        # Massive cinematic configuration panel
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 400, 100, 800, 540)
        self._draw_cyber_panel(surface, panel)

        # High-tech headers
        title = self.font_large.render("SYSTEM AUDIO CONFIGURATION", True, CYAN)
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, panel.top + 60)))

        sub = self.font_medium.render("MAIN OUTPUT ROUTING CHANNELS", True, (120, 180, 255))
        surface.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, panel.top + 130)))

        # Holographic Audio Visualizer Display
        vis_bg = pygame.Rect(SCREEN_WIDTH // 2 - 250, panel.top + 180, 500, 120)
        pygame.draw.rect(surface, (0, 20, 40), vis_bg, border_radius=6)
        pygame.draw.rect(surface, CYAN_DIM, vis_bg, 2, border_radius=6)
        
        wave_y = vis_bg.centery
        for i in range(120):
            amp = random.randint(10, 45) if music_enabled else 3
            x = vis_bg.left + 15 + i * 4
            color = CYAN if music_enabled else (80, 80, 80)
            pygame.draw.line(surface, color, (x, wave_y - amp), (x, wave_y + amp), 2)

        # Status output
        status_text = "STATUS: [ ACTIVE BROADCAST ]" if music_enabled else "STATUS: [ SILENT OP ]"
        status = self.font_medium.render(status_text, True, GREEN if music_enabled else RED)
        surface.blit(status, status.get_rect(center=(SCREEN_WIDTH // 2, vis_bg.bottom + 40)))

        music_rect, back_rect = self.get_settings_buttons()
        self._draw_button(surface, music_rect, "TOGGLE MUSIC CHANNELS")
        self._draw_button(surface, back_rect, "RETURN TO ECHO DATABASE")

    def draw_pause(self, surface: pygame.Surface, music_enabled: bool) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 200, 170, 400, 400)
        self._draw_cyber_panel(surface, panel)

        title = self.font_large.render("SYSTEM PAUSED", True, CYAN)
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
        overlay.fill((20, 0, 0, 185))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 250, 200, 500, 260)
        self._draw_cyber_panel(surface, panel)

        # Override border color specifically to red for game over
        pygame.draw.rect(surface, RED, panel, 3, border_radius=8)

        title = self.font_large.render("SYSTEM FAILURE", True, RED)
        info = self.font_medium.render("Press Enter to Restart Subroutines", True, WHITE)
        sub = self.font_small.render("All drone chassis compromised.", True, WHITE)

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
