import pygame

from player import Player
from projectiles import Bullet, EnemyBullet
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
        self.max_lives = 3
        self.lives_left = self.max_lives
        self.level: LevelData | None = None
        self.player: Player | None = None
        self.bullets: list[Bullet] = []
        self.enemy_bullets: list[EnemyBullet] = []
        self.interact_held = False
        self.interact_pressed = False
        self.message = ""
        self.message_timer = 0.0

        self.loading_timer = 0.0
        self.loading_duration = 1.2
        self.loading_title = ""
        self.transition_timer = 0.0
        self.transition_duration = 1.1
        self.transition_target_level: int | None = None
        self.transition_final = False

        self.load_level(self.current_level_id)

    def start_transition(self, title: str, duration: float = 1.1) -> None:
        self.loading_title = title
        self.loading_duration = duration
        self.loading_timer = duration

    def load_level(
        self,
        level_id: int,
        show_loading: bool = True,
        loading_title: str | None = None,
        loading_duration: float = 2.0,
    ) -> None:
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
        self.transition_timer = 0.0
        self.transition_target_level = None
        self.transition_final = False
        if show_loading:
            self.loading_title = loading_title or f"LEVEL {level_id}"
            self.loading_duration = loading_duration
            self.loading_timer = loading_duration
        else:
            self.loading_timer = 0.0

    def restart_level(self) -> None:
        self.load_level(self.current_level_id)
        self.state.set_playing()

    def start_new_game(self) -> None:
        self.lives_left = self.max_lives
        self.load_level(1, show_loading=True, loading_title="LEVEL 1", loading_duration=2.0)
        self.state.set_playing()

    def go_to_menu(self) -> None:
        self.state.set_menu()

    def toggle_music(self) -> None:
        self.audio.toggle_music()

    def begin_level_transition(self, target_level: int | None, final: bool = False) -> None:
        self.state.set_transition()
        self.transition_timer = self.transition_duration
        self.transition_target_level = target_level
        self.transition_final = final
        self.loading_timer = 0.0
        self.message = ""
        self.message_timer = 0.0
        self.interact_held = False
        self.interact_pressed = False
        self.audio.play_slide()

    def finish_level_transition(self) -> None:
        if self.transition_final or self.transition_target_level is None:
            self.state.set_ending()
        else:
            self.load_level(
                self.transition_target_level,
                show_loading=True,
                loading_title=f"LEVEL {self.transition_target_level}",
                loading_duration=2.0,
            )
            self.state.set_playing()

        self.transition_timer = 0.0
        self.transition_target_level = None
        self.transition_final = False

    def handle_player_death(self) -> None:
        if self.lives_left > 1:
            self.lives_left -= 1
            self.load_level(self.current_level_id, show_loading=False)
            self.state.set_playing()
            self.message = "Life lost"
            self.message_timer = 1.4
            return

        self.lives_left = 0
        self.state.set_game_over()

    def next_level(self) -> None:
        if self.current_level_id < 3:
            self.begin_level_transition(self.current_level_id + 1)
        else:
            self.begin_level_transition(None, final=True)

    def check_button_click(self, mouse_pos: tuple[int, int], button_rect: pygame.Rect) -> bool:
        return button_rect.collidepoint(mouse_pos)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if self.state.is_menu() and event.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

            elif self.state.is_menu() and event.key == pygame.K_RETURN:
                self.start_new_game()

            elif self.state.is_playing():
                if event.key in (pygame.K_e, pygame.K_SPACE):
                    self.interact_held = True
                    self.interact_pressed = True
                elif event.key == pygame.K_ESCAPE:
                    self.state.set_pause()
                elif event.key == pygame.K_r:
                    self.restart_level()

            elif self.state.is_settings():
                if event.key == pygame.K_ESCAPE:
                    self.state.set_menu()

            elif self.state.is_controls():
                if event.key == pygame.K_ESCAPE:
                    self.state.set_menu()

            elif self.state.is_pause():
                if event.key == pygame.K_ESCAPE:
                    self.state.set_playing()

            elif self.state.is_game_over():
                if event.key == pygame.K_RETURN:
                    self.state.set_menu()

            elif self.state.is_ending():
                if event.key == pygame.K_ESCAPE:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_e, pygame.K_SPACE):
                self.interact_held = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button != 1:
                return

            mouse_pos = event.pos

            if self.state.is_menu():
                start_rect, settings_rect, controls_rect, exit_rect = self.ui.get_menu_buttons()
                if self.check_button_click(mouse_pos, start_rect):
                    self.start_new_game()
                elif self.check_button_click(mouse_pos, settings_rect):
                    self.state.set_settings()
                elif self.check_button_click(mouse_pos, controls_rect):
                    self.state.set_controls()
                elif self.check_button_click(mouse_pos, exit_rect):
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                return

            if self.state.is_settings():
                music_rect, back_rect = self.ui.get_settings_buttons()
                if self.check_button_click(mouse_pos, music_rect):
                    self.toggle_music()
                elif self.check_button_click(mouse_pos, back_rect):
                    self.state.set_menu()
                return

            if self.state.is_controls():
                back_rect = self.ui.get_controls_buttons()[0]
                if self.check_button_click(mouse_pos, back_rect):
                    self.state.set_menu()
                return

            if self.state.is_pause():
                continue_rect, menu_rect, music_rect = self.ui.get_pause_buttons()
                if self.check_button_click(mouse_pos, continue_rect):
                    self.state.set_playing()
                elif self.check_button_click(mouse_pos, menu_rect):
                    self.go_to_menu()
                elif self.check_button_click(mouse_pos, music_rect):
                    self.toggle_music()
                return

            if self.state.is_playing() and self.player and not self.player.is_dead:
                if self.loading_timer > 0:
                    return
                bullet_list = self.player.shoot()
                if bullet_list:
                    for b_data in bullet_list:
                        self.bullets.append(Bullet(**b_data))
                    self.audio.play("shoot")

    def update(self, dt: float) -> None:
        if self.state.is_transition():
            self.transition_timer -= dt
            if self.transition_timer <= 0:
                self.finish_level_transition()
            return

        if not self.state.is_playing():
            self.interact_pressed = False
            return

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

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
            self.enemy_bullets.clear()
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

        for bullet in self.enemy_bullets:
            bullet.update(dt, self.level.walls, self.screen_rect)
            if bullet.rect.colliderect(self.player.rect):
                bullet.alive = False
                self.player.take_damage(bullet.damage)
                self.audio.play("hit")

        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]

        for enemy in self.level.enemies:
            enemy.update(dt, self.player, self.level.walls)

            if hasattr(enemy, "projectiles") and enemy.projectiles:
                self.enemy_bullets.extend(enemy.projectiles)
                enemy.projectiles.clear()

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
            self.handle_player_death()
            if self.state.is_game_over():
                return
            return

        if self.level.check_complete(self.player, self.interact_pressed):
            self.next_level()

        self.interact_pressed = False

    def draw_background(self) -> None:
        if self.state.is_menu() or self.state.is_settings() or self.state.is_controls() or not self.level:
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

        if self.state.is_settings():
            self.ui.draw_menu(self.screen)
            self.ui.draw_settings(self.screen, self.audio.music_enabled)
            return

        if self.state.is_controls():
            self.ui.draw_menu(self.screen)
            self.ui.draw_controls(self.screen)
            return

        assert self.level is not None
        assert self.player is not None

        self.level.draw_environment(self.screen, self.visual_assets.get_wall_texture())

        for obs in self.level.current_room.obstacles:
            obs.draw(self.screen, self.visual_assets)

        for bullet in self.bullets:
            bullet.draw(self.screen)

        for bullet in self.enemy_bullets:
            bullet.draw(self.screen)

        for enemy in self.level.enemies:
            enemy.draw(self.screen)

        self.player.draw(self.screen)

        self.ui.draw_health_bar(self.screen, self.player.health, self.player.max_health)
        self.ui.draw_lives(self.screen, self.lives_left, self.max_lives)
        level_title = f"{self.level.name} / {self.level.current_room.name}"
        self.ui.draw_objective(self.screen, level_title, self.level.update_objective_text())

        prompt = self.level.get_prompt(self.player)
        if prompt and self.state.is_playing():
            self.ui.draw_prompt(self.screen, prompt)

        if self.message:
            self.ui.draw_prompt(self.screen, self.message)

        if self.state.is_game_over():
            self.ui.draw_game_over(self.screen)

        if self.state.is_pause():
            self.ui.draw_pause(self.screen, self.audio.music_enabled)

        if self.state.is_ending():
            self.ui.draw_ending(self.screen)

        if self.state.is_transition():
            progress = 1.0 - (self.transition_timer / max(0.001, self.transition_duration))
            self.ui.draw_level_transition(self.screen, progress)

        if self.state.is_playing() and self.loading_timer > 0:
            self.ui.draw_loading_transition(
                self.screen,
                self.loading_title,
                self.loading_timer,
                self.loading_duration,
            )
