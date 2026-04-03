import pygame

from player import Player
from projectiles import Bullet
from enemies import InterceptorDrone
from level_manager import LevelData
from ui import UI
from audio import AudioManager
from state_manager import StateManager
from visual_assets import VisualAssets
from settings import BG_DARK, GRID, SCREEN_WIDTH, SCREEN_HEIGHT


class Game:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.screen_rect = screen.get_rect()

        self.ui = UI()
        self.audio = AudioManager()
        self.audio.load()
        self.state = StateManager()
        self.visual_assets = VisualAssets()

        self.current_level_id = 1
        self.level: LevelData | None = None
        self.player: Player | None = None
        self.bullets: list[Bullet] = []
        self.interact_held = False
        self.interact_pressed = False
        self.message = ""
        self.message_timer = 0.0

        self.loading_timer = 0.0
        self.loading_duration = 1.2
        self.loading_title = ""

        self.load_level(self.current_level_id)

    def start_transition(self, title: str, duration: float = 1.1) -> None:
        self.loading_title = title
        self.loading_duration = duration
        self.loading_timer = duration

    def load_level(self, level_id: int) -> None:
        self.current_level_id = level_id
        self.level = LevelData(level_id, self.visual_assets)
        self.player = Player(
            self.level.player_spawn.x,
            self.level.player_spawn.y,
            self.visual_assets.get_player_animations(),
        )
        self.bullets.clear()
        self.message = ""
        self.message_timer = 0.0
        self.interact_held = False
        self.interact_pressed = False
        self.start_transition(f"Loading {self.level.name}", 1.05)

    def restart_level(self) -> None:
        self.load_level(self.current_level_id)
        self.state.set_playing()

    def next_level(self) -> None:
        if self.current_level_id < 3:
            self.load_level(self.current_level_id + 1)
            self.state.set_playing()
        else:
            self.state.set_ending()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if self.state.is_menu() and event.key == pygame.K_RETURN:
                self.state.set_playing()
                if self.level:
                    self.start_transition(f"Loading {self.level.name}", 1.05)

            elif self.state.is_playing():
                if event.key in (pygame.K_e, pygame.K_SPACE):
                    self.interact_held = True
                    self.interact_pressed = True
                elif event.key == pygame.K_r:
                    self.restart_level()

            elif self.state.is_game_over():
                if event.key == pygame.K_r:
                    self.restart_level()

            elif self.state.is_ending():
                if event.key == pygame.K_ESCAPE:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_e, pygame.K_SPACE):
                self.interact_held = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.state.is_playing() and event.button == 1 and self.player and not self.player.is_dead:
                if self.loading_timer > 0:
                    return
                bullet_data = self.player.shoot()
                if bullet_data:
                    self.bullets.append(Bullet(**bullet_data))
                    self.audio.play("shoot")

    def update(self, dt: float) -> None:
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

        if not self.state.is_playing():
            self.interact_pressed = False
            return

        assert self.level is not None
        assert self.player is not None

        if self.loading_timer > 0:
            self.loading_timer -= dt
            self.interact_pressed = False
            return

        self.player.update(dt, self.level.walls)

        changed_room, door_message, level_exit = self.level.process_room_transitions(self.player)
        if door_message:
            self.message = door_message
            self.message_timer = 1.4
        if level_exit:
            self.next_level()
            self.interact_pressed = False
            return
        if changed_room:
            self.bullets.clear()
            self.start_transition(f"Entering {self.level.current_room.name}", 0.5)
            self.interact_pressed = False
            return

        triggered, log_text = self.level.try_interact(self.player, dt, self.interact_held)
        if triggered:
            self.audio.play("interact")
            if log_text:
                self.audio.play_log(log_text)
                self.message = log_text
                self.message_timer = 3.6

        self.level.update_level_events(dt, self.player)
        status_message = self.level.consume_status_message()
        if status_message:
            self.message = status_message
            self.message_timer = 3.0

        for bullet in self.bullets:
            bullet.update(dt, self.level.walls, self.screen_rect)

        for enemy in self.level.enemies:
            enemy.update(dt, self.player, self.level.walls)

            if enemy.rect.colliderect(self.player.rect):
                enemy.on_touch_player(self.player)

            if isinstance(enemy, InterceptorDrone):
                if enemy.explode_if_needed(self.player):
                    self.audio.play("hit")

        for bullet in self.bullets:
            if not bullet.alive:
                continue
            for enemy in self.level.enemies:
                if not enemy.alive:
                    continue
                if enemy.rect.collidepoint(bullet.pos.x, bullet.pos.y):
                    hit_dir = pygame.Vector2(bullet.vel.x, bullet.vel.y)
                    enemy.take_damage(bullet.damage, hit_dir)
                    bullet.alive = False
                    self.audio.play("hit")
                    break

        self.bullets = [bullet for bullet in self.bullets if bullet.alive]
        self.level.enemies = [enemy for enemy in self.level.enemies if enemy.alive]

        if self.player.is_dead:
            self.audio.play("death")
            self.state.set_game_over()

        if self.level.check_complete(self.player, self.interact_pressed):
            self.next_level()

        self.interact_pressed = False

    def draw_background(self) -> None:
        if self.state.is_menu() or not self.level:
            self.screen.fill(BG_DARK)
            for x in range(0, SCREEN_WIDTH, 48):
                pygame.draw.line(self.screen, GRID, (x, 0), (x, SCREEN_HEIGHT))
            for y in range(0, SCREEN_HEIGHT, 48):
                pygame.draw.line(self.screen, GRID, (0, y), (SCREEN_WIDTH, y))
            return

        self.screen.blit(self.visual_assets.get_level_background(self.current_level_id), (0, 0))

    def draw(self) -> None:
        self.draw_background()

        if self.state.is_menu():
            self.ui.draw_menu(self.screen)
            return

        assert self.level is not None
        assert self.player is not None

        self.level.draw_environment(self.screen)

        for bullet in self.bullets:
            bullet.draw(self.screen)

        for enemy in self.level.enemies:
            enemy.draw(self.screen)

        self.player.draw(self.screen)

        self.ui.draw_health_bar(self.screen, self.player.health, self.player.max_health)
        level_title = f"{self.level.name} / {self.level.current_room.name}"
        self.ui.draw_objective(self.screen, level_title, self.level.update_objective_text())

        prompt = self.level.get_prompt(self.player)
        if prompt and self.state.is_playing():
            self.ui.draw_prompt(self.screen, prompt)

        if self.message:
            self.ui.draw_prompt(self.screen, self.message)

        if self.state.is_game_over():
            self.ui.draw_game_over(self.screen)

        if self.state.is_ending():
            self.ui.draw_ending(self.screen)

        if self.state.is_playing() and self.loading_timer > 0:
            self.ui.draw_loading_transition(
                self.screen,
                self.loading_title,
                self.loading_timer,
                self.loading_duration,
            )
