import random
from dataclasses import dataclass, field
from typing import Callable
import pygame

from enemies import PatrolDrone, SeekerDrone, HeavyDrone, InterceptorDrone, FinalBoss
from interactables import Conduit, SequenceSwitch, Antenna, AudioLog
from settings import LEVEL_NAMES, SCREEN_WIDTH, SCREEN_HEIGHT, PANEL

LEVEL_EXIT = "__level_exit__"


@dataclass
class Door:
    rect: pygame.Rect
    target_room: str
    target_spawn: pygame.Vector2 | None
    label: str
    lock_condition: Callable[["LevelData"], bool] | None = None
    locked_text: str = "Access denied"
    exit_gate: bool = False

    def is_locked(self, level: "LevelData") -> bool:
        if self.lock_condition is None:
            return False
        return self.lock_condition(level)


@dataclass
class RoomData:
    room_id: str
    name: str
    spawn_point: pygame.Vector2
    walls: list[pygame.Rect] = field(default_factory=list)
    interactables: list = field(default_factory=list)
    audio_logs: list[AudioLog] = field(default_factory=list)
    enemies: list = field(default_factory=list)
    doors: list[Door] = field(default_factory=list)
    spawn_points: list[tuple[int, int]] = field(default_factory=list)


class WaveSpawner:
    def __init__(self, enemy_factory: Callable[[str, int, int], object]):
        self.enemy_factory = enemy_factory
        self.active = False
        self.timer = 0.0
        self.spawn_interval = 1.8
        self.interval_decay = 0.0
        self.min_interval = 0.6
        self.remaining: list[str] = []
        self.target_room_id = ""
        self.spawn_points: list[tuple[int, int]] = []
        self.spawned_enemies: list = []
        self.finished_spawning = False

    def start(
        self,
        enemy_types: list[str],
        target_room_id: str,
        spawn_points: list[tuple[int, int]],
        initial_delay: float = 0.6,
        spawn_interval: float = 1.8,
        interval_decay: float = 0.0,
        min_interval: float = 0.6,
    ) -> None:
        self.active = True
        self.timer = initial_delay
        self.spawn_interval = spawn_interval
        self.interval_decay = interval_decay
        self.min_interval = min_interval
        self.remaining = enemy_types[:]
        self.target_room_id = target_room_id
        self.spawn_points = spawn_points[:]
        self.spawned_enemies.clear()
        self.finished_spawning = False

    def update(self, dt: float, rooms: dict[str, RoomData]) -> None:
        if not self.active:
            return
        if self.target_room_id not in rooms:
            self.active = False
            return

        self.timer -= dt
        if self.timer <= 0 and self.remaining:
            enemy_type = self.remaining.pop(0)
            x, y = random.choice(self.spawn_points)
            enemy = self.enemy_factory(enemy_type, x, y)
            rooms[self.target_room_id].enemies.append(enemy)
            self.spawned_enemies.append(enemy)

            self.spawn_interval = max(self.min_interval, self.spawn_interval - self.interval_decay)
            self.timer = self.spawn_interval

        if not self.remaining:
            self.finished_spawning = True

    def is_complete(self) -> bool:
        return self.finished_spawning and all(not enemy.alive for enemy in self.spawned_enemies)


class LevelData:
    def __init__(self, level_id: int, visual_assets):
        self.visual_assets = visual_assets
        self.level_id = level_id
        self.name = LEVEL_NAMES[level_id]
        self.rooms: dict[str, RoomData] = {}
        self.current_room_id = ""
        self.player_spawn = pygame.Vector2(100, 100)
        self.objective_text = ""

        self.active_spawners: list[WaveSpawner] = []
        self.room_transition_cooldown = 0.0
        self.locked_feedback_cooldown = 0.0
        self._status_message = ""

        self.all_conduits: list[Conduit] = []
        self.all_switches: list[SequenceSwitch] = []
        self.all_antennas: list[Antenna] = []

        self.array_assault_started = False
        self.command_door_unlocked = False
        self.boss_spawned = False
        self.final_boss: FinalBoss | None = None
        self.boss_support_timer = 4.5

        self._build()

    @property
    def current_room(self) -> RoomData:
        return self.rooms[self.current_room_id]

    @property
    def walls(self) -> list[pygame.Rect]:
        return self.current_room.walls

    @property
    def interactables(self) -> list:
        return self.current_room.interactables

    @property
    def audio_logs(self) -> list[AudioLog]:
        return self.current_room.audio_logs

    @property
    def enemies(self) -> list:
        return self.current_room.enemies

    @enemies.setter
    def enemies(self, value: list) -> None:
        self.current_room.enemies = value

    def _build(self) -> None:
        if self.level_id == 1:
            self._build_level_one()
        elif self.level_id == 2:
            self._build_level_two()
        elif self.level_id == 3:
            self._build_level_three()

        self.player_spawn = self.current_room.spawn_point.copy()

    def _base_walls(self) -> list[pygame.Rect]:
        border = 22
        return [
            pygame.Rect(0, 0, SCREEN_WIDTH, border),
            pygame.Rect(0, SCREEN_HEIGHT - border, SCREEN_WIDTH, border),
            pygame.Rect(0, 0, border, SCREEN_HEIGHT),
            pygame.Rect(SCREEN_WIDTH - border, 0, border, SCREEN_HEIGHT),
        ]

    def _default_spawn_points(self) -> list[tuple[int, int]]:
        return [
            (80, 80),
            (SCREEN_WIDTH - 80, 80),
            (80, SCREEN_HEIGHT - 80),
            (SCREEN_WIDTH - 80, SCREEN_HEIGHT - 80),
            (SCREEN_WIDTH // 2, 90),
            (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 90),
        ]

    def _spawn_enemy(self, enemy_type: str, x: int, y: int):
        if enemy_type == "patrol":
            return PatrolDrone(x, y, self.visual_assets.get_enemy_animations("patrol"))
        if enemy_type == "seeker":
            return SeekerDrone(x, y, self.visual_assets.get_enemy_animations("seeker"))
        if enemy_type == "heavy":
            return HeavyDrone(x, y, self.visual_assets.get_enemy_animations("heavy"))
        if enemy_type == "interceptor":
            return InterceptorDrone(x, y, self.visual_assets.get_enemy_animations("interceptor"))
        if enemy_type == "boss":
            return FinalBoss(x, y, self.visual_assets.get_enemy_animations("boss"))
        return PatrolDrone(x, y, self.visual_assets.get_enemy_animations("patrol"))

    def _create_room(self, room_id: str, name: str, spawn_point: tuple[int, int]) -> RoomData:
        room = RoomData(
            room_id=room_id,
            name=name,
            spawn_point=pygame.Vector2(spawn_point),
            walls=self._base_walls(),
            spawn_points=self._default_spawn_points(),
        )
        self.rooms[room_id] = room
        return room

    def _build_level_one(self) -> None:
        self.current_room_id = "hub"
        hub = self._create_room("hub", "Conduit Hub", (640, 360))
        north = self._create_room("north", "Cooling Junction", (640, 610))
        west = self._create_room("west", "Power Relay", (1140, 360))
        east = self._create_room("east", "Signal Channel", (140, 360))
        south = self._create_room("south", "Maintenance Loop", (640, 120))

        hub.walls.extend([
            pygame.Rect(360, 220, 560, 30),
            pygame.Rect(360, 470, 560, 30),
            pygame.Rect(620, 280, 40, 160),
        ])
        hub.audio_logs.append(AudioLog(610, 350, "Log: Conduit sectors desynced. Re-route from each chamber."))
        hub.enemies.extend([
            self._spawn_enemy("patrol", 420, 360),
            self._spawn_enemy("seeker", 870, 360),
        ])
        hub.doors = [
            Door(pygame.Rect(608, 34, 64, 30), "north", pygame.Vector2(640, 630), "To Cooling Junction"),
            Door(pygame.Rect(608, 656, 64, 30), "south", pygame.Vector2(640, 94), "To Maintenance Loop"),
            Door(pygame.Rect(34, 328, 30, 64), "east", pygame.Vector2(1160, 360), "To Signal Channel"),
            Door(pygame.Rect(1216, 328, 30, 64), "west", pygame.Vector2(120, 360), "To Power Relay"),
        ]

        for room, conduit_pos, enemies in [
            (north, (620, 110), [("patrol", 400, 360), ("seeker", 900, 240)]),
            (west, (160, 340), [("heavy", 690, 220), ("patrol", 860, 520)]),
            (east, (1080, 340), [("seeker", 360, 220), ("interceptor", 700, 500)]),
            (south, (620, 560), [("patrol", 460, 280), ("seeker", 860, 480)]),
        ]:
            room.walls.extend([
                pygame.Rect(290, 180, 30, 360),
                pygame.Rect(960, 180, 30, 360),
            ])
            conduit = Conduit(conduit_pos[0], conduit_pos[1], len(self.all_conduits) + 1)
            room.interactables.append(conduit)
            self.all_conduits.append(conduit)

            for kind, ex, ey in enemies:
                room.enemies.append(self._spawn_enemy(kind, ex, ey))

        north.doors = [Door(pygame.Rect(608, 656, 64, 30), "hub", pygame.Vector2(640, 100), "Back To Hub")]
        south.doors = [Door(pygame.Rect(608, 34, 64, 30), "hub", pygame.Vector2(640, 620), "Back To Hub")]
        east.doors = [Door(pygame.Rect(34, 328, 30, 64), "hub", pygame.Vector2(1160, 360), "Back To Hub")]
        west.doors = [Door(pygame.Rect(1216, 328, 30, 64), "hub", pygame.Vector2(120, 360), "Back To Hub")]

        self.objective_text = "Activate all conduits and clear hostiles"

    def _build_level_two(self) -> None:
        self.current_room_id = "main_hall"
        main = self._create_room("main_hall", "Reactor Hallway", (90, 360))
        branch_a = self._create_room("branch_a", "Switch Room A", (640, 620))
        branch_b = self._create_room("branch_b", "Switch Room B", (640, 100))
        branch_c = self._create_room("branch_c", "Switch Room C", (640, 620))
        branch_d = self._create_room("branch_d", "Switch Room D", (640, 100))

        main.walls.extend([
            pygame.Rect(80, 150, 1120, 32),
            pygame.Rect(80, 540, 1120, 32),
            pygame.Rect(250, 180, 24, 180),
            pygame.Rect(490, 360, 24, 180),
            pygame.Rect(730, 180, 24, 180),
            pygame.Rect(970, 360, 24, 180),
        ])
        main.enemies.extend([
            self._spawn_enemy("patrol", 340, 360),
            self._spawn_enemy("seeker", 660, 360),
            self._spawn_enemy("heavy", 930, 360),
        ])
        main.audio_logs.append(AudioLog(110, 460, "Log: Gate unlock requires all branch switches online."))
        main.doors = [
            Door(pygame.Rect(260, 196, 54, 44), "branch_a", pygame.Vector2(640, 600), "Path A"),
            Door(pygame.Rect(500, 480, 54, 44), "branch_b", pygame.Vector2(640, 120), "Path B"),
            Door(pygame.Rect(740, 196, 54, 44), "branch_c", pygame.Vector2(640, 600), "Path C"),
            Door(pygame.Rect(980, 480, 54, 44), "branch_d", pygame.Vector2(640, 120), "Path D"),
            Door(
                pygame.Rect(1188, 292, 46, 136),
                LEVEL_EXIT,
                None,
                "Final Gate",
                lock_condition=lambda level: not level.all_switches_active(),
                locked_text="Gate locked: activate every switch",
                exit_gate=True,
            ),
        ]

        for room, switch_idx, switch_pos, enemies in [
            (branch_a, 1, (620, 560), [("patrol", 460, 300), ("seeker", 900, 450)]),
            (branch_b, 2, (620, 110), [("interceptor", 430, 240), ("seeker", 840, 360)]),
            (branch_c, 3, (620, 560), [("heavy", 740, 300), ("patrol", 980, 500)]),
            (branch_d, 4, (620, 110), [("seeker", 340, 260), ("interceptor", 1000, 430)]),
        ]:
            room.walls.extend([
                pygame.Rect(260, 200, 34, 320),
                pygame.Rect(980, 200, 34, 320),
                pygame.Rect(520, 280, 240, 26),
            ])
            switch = SequenceSwitch(switch_pos[0], switch_pos[1], switch_idx)
            switch.allowed = True
            room.interactables.append(switch)
            self.all_switches.append(switch)

            for kind, ex, ey in enemies:
                room.enemies.append(self._spawn_enemy(kind, ex, ey))

        branch_a.doors = [Door(pygame.Rect(608, 34, 64, 30), "main_hall", pygame.Vector2(340, 300), "Back To Hall")]
        branch_b.doors = [Door(pygame.Rect(608, 656, 64, 30), "main_hall", pygame.Vector2(560, 420), "Back To Hall")]
        branch_c.doors = [Door(pygame.Rect(608, 34, 64, 30), "main_hall", pygame.Vector2(820, 300), "Back To Hall")]
        branch_d.doors = [Door(pygame.Rect(608, 656, 64, 30), "main_hall", pygame.Vector2(1060, 420), "Back To Hall")]

        self.objective_text = "Activate all branch switches and reach the gate"

    def _build_level_three(self) -> None:
        self.current_room_id = "array_field"
        array_field = self._create_room("array_field", "Antenna Field", (120, 360))
        command_core = self._create_room("command_core", "Command Core", (140, 360))

        array_field.walls.extend([
            pygame.Rect(300, 140, 32, 430),
            pygame.Rect(620, 70, 32, 260),
            pygame.Rect(620, 390, 32, 260),
            pygame.Rect(920, 140, 32, 430),
        ])
        array_field.interactables = [
            Antenna(170, 100, 1),
            Antenna(640, 100, 2),
            Antenna(1080, 100, 3),
        ]
        self.all_antennas = list(array_field.interactables)
        array_field.audio_logs.append(AudioLog(120, 620, "Log: Antenna uplink unstable. Expect immediate reinforcements."))
        array_field.enemies.extend([
            self._spawn_enemy("seeker", 430, 350),
            self._spawn_enemy("patrol", 830, 350),
        ])
        array_field.doors = [
            Door(
                pygame.Rect(1216, 300, 30, 120),
                "command_core",
                pygame.Vector2(120, 360),
                "Blast Door",
                lock_condition=lambda level: not level.command_door_unlocked,
                locked_text="Blast door sealed. Survive the assault first.",
            )
        ]

        command_core.walls.extend([
            pygame.Rect(350, 120, 32, 470),
            pygame.Rect(700, 120, 32, 470),
            pygame.Rect(350, 320, 380, 26),
        ])
        command_core.doors = []
        command_core.spawn_points = [
            (260, 160),
            (260, 560),
            (1140, 160),
            (1140, 560),
            (640, 150),
            (640, 570),
        ]

        self.objective_text = "Align all antennas and survive the final assault"

    def all_switches_active(self) -> bool:
        return bool(self.all_switches) and all(sw.completed for sw in self.all_switches)

    def consume_status_message(self) -> str:
        msg = self._status_message
        self._status_message = ""
        return msg

    def start_wave(
        self,
        enemy_types: list[str],
        room_id: str,
        initial_delay: float = 0.6,
        spawn_interval: float = 1.6,
        interval_decay: float = 0.0,
        min_interval: float = 0.6,
    ) -> None:
        room = self.rooms[room_id]
        spawner = WaveSpawner(self._spawn_enemy)
        spawner.start(
            enemy_types=enemy_types,
            target_room_id=room_id,
            spawn_points=room.spawn_points,
            initial_delay=initial_delay,
            spawn_interval=spawn_interval,
            interval_decay=interval_decay,
            min_interval=min_interval,
        )
        self.active_spawners.append(spawner)

    def update_level_events(self, dt: float, player) -> None:
        if self.room_transition_cooldown > 0:
            self.room_transition_cooldown -= dt
        if self.locked_feedback_cooldown > 0:
            self.locked_feedback_cooldown -= dt

        for spawner in self.active_spawners:
            spawner.update(dt, self.rooms)
        self.active_spawners = [sp for sp in self.active_spawners if not sp.is_complete()]

        if self.level_id == 3:
            self._update_level_three_assault(dt, player)

    def _update_level_three_assault(self, dt: float, player) -> None:
        if self.array_assault_started and not self.command_door_unlocked:
            field_clear = not self.active_spawners and len([e for e in self.rooms["array_field"].enemies if e.alive]) == 0
            if field_clear:
                self.command_door_unlocked = True
                self._status_message = "Field clear. Breach the command core."

        if self.current_room_id != "command_core":
            return
        if not self.boss_spawned or not self.final_boss or not self.final_boss.alive:
            return

        self.boss_support_timer -= dt
        if self.boss_support_timer <= 0:
            support_enemies = [enemy for enemy in self.rooms["command_core"].enemies if enemy.alive and enemy is not self.final_boss]
            if len(support_enemies) < 6:
                support_type = random.choice(["seeker", "interceptor", "patrol"])
                x, y = random.choice(self.rooms["command_core"].spawn_points)
                self.rooms["command_core"].enemies.append(self._spawn_enemy(support_type, x, y))

            health_ratio = self.final_boss.health / self.final_boss.max_health
            self.boss_support_timer = 4.0 if health_ratio > 0.55 else 2.8

    def process_room_transitions(self, player) -> tuple[bool, str | None, bool]:
        if self.room_transition_cooldown > 0:
            return False, None, False

        room = self.current_room
        for door in room.doors:
            if not door.rect.colliderect(player.rect):
                continue

            if door.is_locked(self):
                if self.locked_feedback_cooldown <= 0:
                    self.locked_feedback_cooldown = 0.8
                    return False, door.locked_text, False
                return False, None, False

            if door.target_room == LEVEL_EXIT:
                return False, None, True

            self.current_room_id = door.target_room
            if door.target_spawn is not None:
                player.pos = door.target_spawn.copy()
            self.room_transition_cooldown = 0.35
            self._on_room_enter(self.current_room_id)
            return True, None, False

        return False, None, False

    def _on_room_enter(self, room_id: str) -> None:
        if self.level_id != 3 or room_id != "command_core":
            return
        if self.boss_spawned:
            return

        boss_room = self.rooms["command_core"]
        self.final_boss = self._spawn_enemy("boss", 980, 360)
        boss_room.enemies.append(self.final_boss)
        boss_room.enemies.extend([
            self._spawn_enemy("heavy", 900, 220),
            self._spawn_enemy("interceptor", 900, 500),
        ])
        self.boss_spawned = True
        self.boss_support_timer = 4.5
        self._status_message = "Core guardian deployed. Survive and destroy it."

    def _start_antenna_wave(self, activated_count: int) -> None:
        if activated_count == 1:
            self.start_wave(
                ["seeker", "patrol", "interceptor"],
                "array_field",
                initial_delay=0.4,
                spawn_interval=1.35,
            )
            return

        if activated_count == 2:
            self.start_wave(
                ["seeker", "interceptor", "heavy", "patrol", "seeker"],
                "array_field",
                initial_delay=0.3,
                spawn_interval=1.05,
                interval_decay=0.03,
                min_interval=0.72,
            )
            return

        self.array_assault_started = True
        self.start_wave(
            [
                "interceptor",
                "seeker",
                "patrol",
                "interceptor",
                "heavy",
                "seeker",
                "interceptor",
                "patrol",
                "heavy",
                "seeker",
                "interceptor",
                "patrol",
            ],
            "array_field",
            initial_delay=0.25,
            spawn_interval=0.85,
            interval_decay=0.035,
            min_interval=0.48,
        )
        self.start_wave(
            ["seeker", "interceptor", "seeker", "interceptor", "heavy", "patrol"],
            "array_field",
            initial_delay=3.0,
            spawn_interval=0.75,
            interval_decay=0.02,
            min_interval=0.5,
        )
        self._status_message = "Final antenna aligned. Assault intensity critical."

    def update_objective_text(self) -> str:
        if self.level_id == 1:
            done = sum(1 for conduit in self.all_conduits if conduit.completed)
            enemies_left = sum(1 for room in self.rooms.values() for enemy in room.enemies if enemy.alive)
            return f"Conduits online: {done}/4  |  Hostiles remaining: {enemies_left}"

        if self.level_id == 2:
            done = sum(1 for switch in self.all_switches if switch.completed)
            if done < len(self.all_switches):
                return f"Branch switches activated: {done}/4"
            return "All switches active. Move through the end gate."

        if self.level_id == 3:
            antennas_done = sum(1 for antenna in self.all_antennas if antenna.completed)
            if antennas_done < 3:
                return f"Align antennas: {antennas_done}/3"
            if self.array_assault_started and not self.command_door_unlocked:
                enemies_left = sum(1 for enemy in self.rooms["array_field"].enemies if enemy.alive)
                return f"Hold the array. Remaining attackers: {enemies_left}"
            if not self.boss_spawned:
                return "Breach the command core"
            if self.final_boss and self.final_boss.alive:
                return f"Destroy final boss: {self.final_boss.health}/{self.final_boss.max_health}"
            return "Boss neutralized. Finish remaining hostiles."

        return self.objective_text

    def try_interact(self, player, dt: float, holding: bool) -> tuple[bool, str | None]:
        room = self.current_room

        for log in room.audio_logs:
            if log.can_interact(player) and holding:
                triggered = log.interact(dt, True)
                if triggered:
                    return True, log.text

        for obj in room.interactables:
            if not obj.can_interact(player):
                if getattr(obj, "requires_hold", False):
                    obj.reset_progress()
                continue

            if isinstance(obj, Antenna):
                if not holding:
                    obj.reset_progress()
                    continue
                triggered = obj.interact(dt, True)
                if triggered:
                    activated_count = sum(1 for antenna in self.all_antennas if antenna.completed)
                    self._start_antenna_wave(activated_count)
                    return True, f"Antenna {obj.index} aligned"
                continue

            if isinstance(obj, SequenceSwitch):
                if not holding:
                    continue
                triggered = obj.interact(dt, False)
                if triggered and self.all_switches_active():
                    self._status_message = "All switches active. Final gate unlocked."
                if triggered:
                    return True, f"Switch {obj.index} active"
                continue

            if holding:
                triggered = obj.interact(dt, False)
                if triggered:
                    return True, None

        return False, None

    def get_prompt(self, player) -> str | None:
        room = self.current_room

        for log in room.audio_logs:
            if not log.completed and log.can_interact(player):
                return log.get_prompt()

        for obj in room.interactables:
            if not obj.completed and obj.can_interact(player):
                return obj.get_prompt()

        for door in room.doors:
            if door.rect.inflate(36, 36).colliderect(player.rect):
                if door.is_locked(self):
                    return door.locked_text
                if door.target_room == LEVEL_EXIT:
                    return "Cross gate to enter final stage"
                return f"Move through door - {door.label}"

        return None

    def check_complete(self, player, interact_pressed: bool) -> bool:
        if self.level_id == 1:
            all_conduits_done = all(conduit.completed for conduit in self.all_conduits)
            all_enemies_down = all(not enemy.alive for room in self.rooms.values() for enemy in room.enemies)
            return all_conduits_done and all_enemies_down

        if self.level_id == 2:
            return False

        if self.level_id == 3:
            if not self.boss_spawned:
                return False
            if self.final_boss and self.final_boss.alive:
                return False
            return all(not enemy.alive for enemy in self.rooms["command_core"].enemies)

        return False

    def draw_environment(self, surface: pygame.Surface) -> None:
        room = self.current_room

        for wall in room.walls:
            pygame.draw.rect(surface, PANEL, wall)

        for door in room.doors:
            locked = door.is_locked(self)
            if door.exit_gate:
                color = (70, 90, 70) if not locked else (120, 70, 60)
            else:
                color = (70, 170, 220) if not locked else (90, 90, 100)
            pygame.draw.rect(surface, color, door.rect, border_radius=5)
            pygame.draw.rect(surface, (30, 30, 30), door.rect, 2, border_radius=5)

        for obj in room.interactables:
            obj.draw(surface)

        for log in room.audio_logs:
            log.draw(surface)
