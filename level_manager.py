import random
from dataclasses import dataclass, field
from typing import Callable
import pygame

from enemies import PatrolDrone, SeekerDrone, HeavyDrone, InterceptorDrone, FinalBoss
from interactables import Conduit, SequenceSwitch, Antenna, MessageFragment, WeaponPickup, Obstacle
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
    message_fragments: list[MessageFragment] = field(default_factory=list)
    obstacles: list[Obstacle] = field(default_factory=list)
    enemies: list = field(default_factory=list)
    doors: list["Door"] = field(default_factory=list)
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
        self.player_spawn = pygame.Vector2(144, 144)
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
        return self.current_room.walls + [obs.rect for obs in self.current_room.obstacles]

    @property
    def interactables(self) -> list:
        return self.current_room.interactables

    @property
    def message_fragments(self) -> list[MessageFragment]:
        return self.current_room.message_fragments

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
            (96, 96),
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
        hub = self._create_room("hub", "Conduit Hub", (921, 518))
        north = self._create_room("north", "Cooling Junction", (768, 800))
        west = self._create_room("west", "Power Relay", (200, 500))
        east = self._create_room("east", "Signal Channel", (1300, 500))
        south = self._create_room("south", "Maintenance Loop", (768, 200))

        # Hub is fully segmented by dense servers
        hub.obstacles.extend([
            Obstacle(300, 400, 96, 256, "scifi_server"),
            Obstacle(1100, 400, 96, 256, "scifi_server"),
            Obstacle(600, 200, 256, 96, "scifi_server"),
            Obstacle(400, 560, 256, 96, "scifi_server"),
        ])
        hub.message_fragments.append(MessageFragment(732, 420, "Fragment 1/3: ERROR. Critical impact detected. Unknown lifeform breached sector 7... AI friend/foe protocols overwritten."))
        hub.enemies.extend([
            self._spawn_enemy("patrol", 604, 518),
            self._spawn_enemy("seeker", 1252, 518),
            self._spawn_enemy("patrol", 400, 700),
            self._spawn_enemy("patrol", 800, 200),
            self._spawn_enemy("patrol", 800, 700),
        ])
        
        # Unique spawn points shifted away from geometry to fix overlapping
        top_spwn = pygame.Vector2(768, 140)
        bot_spwn = pygame.Vector2(768, 724)
        left_spwn = pygame.Vector2(200, 432)
        right_spwn = pygame.Vector2(1200, 432)

        hub.doors = [
            Door(pygame.Rect(729, 40, 76, 36), "north", bot_spwn, "To Cooling Junction"),
            Door(pygame.Rect(729, 787, 76, 36), "south", top_spwn, "To Maintenance Loop"),
            Door(pygame.Rect(40, 393, 36, 76), "west", right_spwn, "To Power Relay"),
            Door(pygame.Rect(1459, 393, 36, 76), "east", left_spwn, "To Signal Channel"),
        ]

        for room, conduit_pos, enemies in [
            (north, (744, 200), [("patrol", 480, 432), ("seeker", 1080, 288)]),
            (west, (300, 408), [("heavy", 828, 264), ("patrol", 1032, 624)]),
            (east, (1100, 408), [("seeker", 432, 264), ("interceptor", 840, 600)]),
            (south, (744, 600), [("patrol", 552, 336), ("seeker", 1032, 576)]),
        ]:
            # Add sprawling crates in wings
            room.obstacles.extend([
                Obstacle(450, 250, 128, 128, "scifi_crate"),
                Obstacle(950, 250, 128, 128, "scifi_crate"),
                Obstacle(850, 650, 128, 128, "scifi_crate"),
            ])
            conduit = Conduit(conduit_pos[0], conduit_pos[1], len(self.all_conduits) + 1)
            room.interactables.append(conduit)
            self.all_conduits.append(conduit)

            for kind, ex, ey in enemies:
                room.enemies.append(self._spawn_enemy(kind, ex, ey))

        north.doors = [Door(pygame.Rect(729, 787, 76, 36), "hub", pygame.Vector2(768, 100), "Back To Hub")]
        south.doors = [Door(pygame.Rect(729, 40, 76, 36), "hub", pygame.Vector2(768, 700), "Back To Hub")]
        east.doors = [Door(pygame.Rect(40, 393, 36, 76), "hub", pygame.Vector2(1400, 430), "Back To Hub")]
        west.doors = [Door(pygame.Rect(1459, 393, 36, 76), "hub", pygame.Vector2(100, 430), "Back To Hub")]

        self.objective_text = "Activate all conduits and clear hostiles"

    def _build_level_two(self) -> None:
        self.current_room_id = "main_hall"
        main = self._create_room("main_hall", "Reactor Checkpoint", (129, 518))
        lab_sector = self._create_room("lab_sector", "Research Labs", (760, 800))
        cargo_bay = self._create_room("cargo_bay", "Cargo Storage", (200, 200))

        # Core checkpoint filled with server blocks for cover
        main.obstacles.extend([
            Obstacle(300, 200, 96, 256, "scifi_server"),
            Obstacle(300, 560, 96, 256, "scifi_server"),
            Obstacle(900, 400, 192, 96, "scifi_server"),
            Obstacle(1150, 400, 192, 96, "scifi_server"),
        ])
        main.enemies.extend([
            self._spawn_enemy("patrol", 600, 218),
            self._spawn_enemy("patrol", 600, 618),
            self._spawn_enemy("heavy", 800, 200),
            self._spawn_enemy("seeker", 1339, 518),
        ])
        main.message_fragments.append(MessageFragment(132, 552, "Fragment 2/3: WARNING. All security drones hijacked. Core overrides initiated by ... [CORRUPTED]"))

        # Complex cargo bay maze
        cargo_bay.obstacles.extend([
            Obstacle(500, 300, 128, 128, "scifi_crate"),
            Obstacle(628, 300, 128, 128, "scifi_crate"),
            Obstacle(500, 428, 128, 128, "scifi_crate"),
            Obstacle(1000, 150, 128, 128, "scifi_crate"),
            Obstacle(1128, 500, 128, 128, "scifi_crate"),
        ])
        switch_1 = SequenceSwitch(1300, 600, 1)
        switch_1.allowed = True
        switch_2 = SequenceSwitch(600, 150, 2)
        switch_2.allowed = True
        cargo_bay.interactables.extend([switch_1, switch_2])
        self.all_switches.extend([switch_1, switch_2])
        cargo_bay.enemies.extend([
            self._spawn_enemy("heavy", 800, 400),
            self._spawn_enemy("interceptor", 400, 800),
            self._spawn_enemy("seeker", 1200, 200),
        ])

        # Research labs
        lab_sector.walls.extend([
            pygame.Rect(400, 400, 600, 40),
            pygame.Rect(680, 200, 40, 200),
        ])
        switch_3 = SequenceSwitch(800, 700, 3)
        switch_3.allowed = True
        switch_4 = SequenceSwitch(400, 200, 4)
        switch_4.allowed = True
        lab_sector.interactables.extend([switch_3, switch_4])
        self.all_switches.extend([switch_3, switch_4])
        lab_sector.enemies.extend([
            self._spawn_enemy("patrol", 300, 300),
            self._spawn_enemy("heavy", 1100, 700),
            self._spawn_enemy("seeker", 1200, 400),
        ])

        main.doors = [
            Door(pygame.Rect(729, 40, 76, 36), "cargo_bay", pygame.Vector2(760, 750), "To Cargo Bay"),
            Door(pygame.Rect(729, 787, 76, 36), "lab_sector", pygame.Vector2(760, 100), "To Research Labs"),
            Door(
                pygame.Rect(1450, 400, 50, 100),
                LEVEL_EXIT,
                None,
                "Final Gate",
                lock_condition=lambda level: not level.all_switches_active(),
                locked_text="Gate locked: activate every switch",
                exit_gate=True,
            ),
        ]
        cargo_bay.doors = [Door(pygame.Rect(729, 787, 76, 36), "main_hall", pygame.Vector2(760, 100), "Back To Checkpoint")]
        lab_sector.doors = [Door(pygame.Rect(729, 40, 76, 36), "main_hall", pygame.Vector2(760, 750), "Back To Checkpoint")]

        self.objective_text = "Activate all 4 access switches in Cargo and Labs"

    def _build_level_three(self) -> None:
        self.current_room_id = "array_field"
        array_field = self._create_room("array_field", "Antenna Field", (172, 518))
        command_core = self._create_room("command_core", "Command Core", (760, 800))

        # Massive staggered antenna field barricaded by huge servers blocking direct movement
        array_field.obstacles.extend([
            Obstacle(300, 300, 96, 256, "scifi_server"),
            Obstacle(800, 400, 256, 96, "scifi_server"),
            Obstacle(1100, 100, 96, 256, "scifi_server"),
            Obstacle(1100, 600, 96, 128, "scifi_server"),
        ])
        array_field.interactables = [
            Antenna(200, 150, 1),
            Antenna(600, 700, 2),
            Antenna(1350, 450, 3),
        ]
        self.all_antennas = list(array_field.interactables)
        array_field.message_fragments.append(MessageFragment(800, 200, "Fragment 3/3: FATAL. The rogue proxy is broadcasting its virus. Destroy the Boss Drone to stop the override!"))
        array_field.enemies.extend([
            self._spawn_enemy("seeker", 600, 200),
            self._spawn_enemy("patrol", 1000, 300),
            self._spawn_enemy("heavy", 800, 600),
            self._spawn_enemy("interceptor", 1200, 150),
        ])
        array_field.doors = [
            Door(
                pygame.Rect(1440, 360, 36, 144),
                "command_core",
                pygame.Vector2(200, 450),
                "Blast Door",
                lock_condition=lambda level: not level.command_door_unlocked,
                locked_text="Blast door sealed. Survive the assault first.",
            )
        ]

        # The core is a massive arena separated by crate clusters against Boss attacks
        command_core.obstacles.extend([
            Obstacle(300, 200, 128, 128, "scifi_crate"),
            Obstacle(300, 600, 128, 128, "scifi_crate"),
            Obstacle(1100, 200, 128, 128, "scifi_crate"),
            Obstacle(1100, 600, 128, 128, "scifi_crate"),
            Obstacle(700, 400, 128, 128, "scifi_crate"),
        ])
        command_core.doors = []
        command_core.spawn_points = [
            (200, 200),
            (200, 700),
            (1300, 200),
            (1300, 700),
            (760, 150),
            (760, 750),
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
        self.final_boss = self._spawn_enemy("boss", 1411, 518)
        boss_room.enemies.append(self.final_boss)
        boss_room.enemies.extend([
            self._spawn_enemy("heavy", 1296, 316),
            self._spawn_enemy("interceptor", 1296, 720),
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

        for log in room.message_fragments:
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
                triggered = obj.interact(dt, False)
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

            if isinstance(obj, WeaponPickup):
                if holding:
                    continue
                triggered = obj.interact(dt, False)
                if triggered:
                    player.play_pickup()
                    player.weapon_module = obj.weapon_type
                    return True, f"Equipped {obj.weapon_type.capitalize()}"
                continue

            if holding:
                triggered = obj.interact(dt, False)
                if triggered:
                    return True, None

        return False, None

    def get_prompt(self, player) -> str | None:
        room = self.current_room

        for log in room.message_fragments:
            if not log.completed and log.can_interact(player):
                return log.get_prompt()

        for obj in room.interactables:
            if not obj.completed and obj.can_interact(player):
                return obj.get_prompt()

        for door in room.doors:
            if door.rect.inflate(43, 43).colliderect(player.rect):
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

    def draw_environment(self, surface: pygame.Surface, wall_texture: pygame.Surface | None = None) -> None:
        room = self.current_room

        for wall in room.walls:
            if wall_texture:
                surface.blit(wall_texture, wall, area=wall)
                pygame.draw.rect(surface, (200, 160, 50), wall, 2)
            else:
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

        for log in room.message_fragments:
            log.draw(surface)
