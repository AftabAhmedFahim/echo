import random
from dataclasses import dataclass, field
from typing import Callable
import pygame

from enemies import PatrolDrone, SeekerDrone, HeavyDrone, InterceptorDrone, FinalBoss
from interactables import Conduit, SequenceSwitch, Antenna, MessageFragment, WeaponPickup, Obstacle, Portal
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

        # Portal (level-exit mechanic)
        self.portal: Portal | None = None
        self.portal_active: bool = False
        self._portal_spawned: bool = False  # one-shot guard

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

        # Hub: three staggered server banks split the room into S-shaped lanes.
        # All objects separated by ≥20 px. No crate clusters touching each other.
        hub.obstacles.extend([
            Obstacle(296, 160, 112, 272, "scifi_server"),   # left-top pillar
            Obstacle(1144, 432, 112, 272, "scifi_server"),  # right-bottom pillar
            Obstacle(576, 496, 240, 96, "scifi_server"),    # centre-low bar
            Obstacle(700, 240, 240, 96, "scifi_server"),    # upper-right bar  (right=940, server_Rtop x=1016 → gap=76 ✓)
            Obstacle(440, 656, 96, 144, "scifi_server"),    # left lower accent
            Obstacle(1016, 168, 96, 144, "scifi_server"),   # right upper accent
        ])
        # Isolated crates (each 20 px away from each other and from servers)
        hub.obstacles.extend([
            Obstacle(200, 680, 64, 64, "scifi_crate"),   # far-left low A
            Obstacle(200, 764, 64, 64, "scifi_crate"),   # far-left low B  (680+64+20=764)
            Obstacle(1290, 168, 64, 64, "scifi_crate"),  # far-right high A
            Obstacle(1290, 252, 64, 64, "scifi_crate"),  # far-right high B (168+64+20=252)
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

        # Wing room conduit positions — each placed in a clear open quadrant
        # far from all obstacles (obstacles span x=280-1208, conduits placed outside)
        wing_conduit_positions = {
            "north": (760, 680),   # bottom-centre open corridor
            "west":  (760, 150),   # top-centre clear strip
            "east":  (760, 650),   # bottom-centre clear strip
            "south": (760, 150),   # top-centre clear strip
        }
        for room, room_id, enemies in [
            (north, "north", [("patrol", 480, 432), ("seeker", 1080, 288)]),
            (west,  "west",  [("heavy", 828, 264), ("patrol", 1032, 624)]),
            (east,  "east",  [("seeker", 432, 264), ("interceptor", 840, 600)]),
            (south, "south", [("patrol", 552, 336), ("seeker", 1032, 576)]),
        ]:
            # Wing rooms: two mirrored server walls flanking a centre open lane.
            # Crates placed individually in corners, each ≥20 px from servers/conduit.
            room.obstacles.extend([
                Obstacle(296, 216, 144, 112, "scifi_server"),   # left-top wall
                Obstacle(296, 472, 144, 112, "scifi_server"),   # left-bot wall
                Obstacle(1096, 216, 144, 112, "scifi_server"),  # right-top wall
                Obstacle(1096, 472, 144, 112, "scifi_server"),  # right-bot wall
                Obstacle(672, 300, 192, 80, "scifi_server"),    # centre horizontal bar
            ])
            # Isolated crate accents — 20 px from servers, 20 px between each other
            room.obstacles.extend([
                Obstacle(476, 216, 80, 80, "scifi_crate"),   # slot between left & crate col (296+144+36=476)
                Obstacle(476, 480, 80, 80, "scifi_crate"),   # lower mirror
                Obstacle(916, 216, 80, 80, "scifi_crate"),   # right slot
                Obstacle(916, 480, 80, 80, "scifi_crate"),   # lower mirror
            ])
            cx, cy = wing_conduit_positions[room_id]
            conduit = Conduit(cx, cy, len(self.all_conduits) + 1)
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

        # Reactor checkpoint: staggered server columns create a zigzag battle lane.
        # Every object has ≥20 px gap from its neighbours.
        main.obstacles.extend([
            Obstacle(248, 168, 96, 296, "scifi_server"),   # left column top
            Obstacle(248, 584, 96, 192, "scifi_server"),   # left column bot  (168+296+120 gap → 584)
            Obstacle(632, 296, 240, 96, "scifi_server"),   # mid-left slab
            Obstacle(632, 536, 240, 96, "scifi_server"),   # mid-right slab   (296+96+144 gap → 536)
            Obstacle(1072, 168, 96, 208, "scifi_server"),  # right column top
            Obstacle(1072, 496, 96, 240, "scifi_server"),  # right column bot  (168+208+120 gap → 496)
        ])
        # Crate accents: placed individually with ≥20 px separation from all servers
        main.obstacles.extend([
            Obstacle(408, 168, 80, 80, "scifi_crate"),    # top-mid A  (248+96+64=408)
            Obstacle(408, 496, 80, 80, "scifi_crate"),    # bot-mid A
            Obstacle(944, 616, 80, 80, "scifi_crate"),    # bot-right A (1072-80-48=944)
            Obstacle(944, 716, 64, 64, "scifi_crate"),    # bot-right B (616+80+20=716)
        ])
        main.enemies.extend([
            self._spawn_enemy("patrol", 600, 218),
            self._spawn_enemy("patrol", 600, 618),
            self._spawn_enemy("heavy", 800, 200),
            self._spawn_enemy("seeker", 1339, 518),
        ])
        main.message_fragments.append(MessageFragment(132, 552, "Fragment 2/3: WARNING. All security drones hijacked. Core overrides initiated by ... [CORRUPTED]"))

        # Cargo bay: two separate C-shaped walls, each internally connected,
        # but with a clear passage between them. All rects ≥20 px apart.
        # Left C: top bar (x=296,y=184,w=128) + left post + bottom bar
        # Right C: mirror on right half
        cargo_bay.obstacles.extend([
            Obstacle(296, 184, 256, 96, "scifi_crate"),   # left-C top bar
            Obstacle(296, 300, 96, 96, "scifi_crate"),    # left-C left post (184+96+20=300)
            Obstacle(296, 456, 256, 96, "scifi_crate"),   # left-C bot bar   (300+96+60 gap=456)
            Obstacle(840, 496, 256, 96, "scifi_crate"),   # right-C top bar  (wide gap between C's)
            Obstacle(1080, 496, 96, 96, "scifi_crate"),   # right-C right post (840+256+... wait, 840+256=1096 > 1080 overlap)
        ])
        # ↑ Recalculate: right-C top bar x=840 w=256 → right=1096. post x=1080 → overlap.
        # Fix: right-C top bar narrowed and post placed clear.
        # Let me redo cargo cleanly:
        cargo_bay.obstacles.clear()
        cargo_bay.obstacles.extend([
            # Left C-shape (open right side)
            Obstacle(296, 184, 240, 88, "scifi_crate"),   # top rail
            Obstacle(296, 292, 80, 80, "scifi_crate"),    # left post   (184+88+20=292)
            Obstacle(296, 460, 240, 88, "scifi_crate"),   # bot rail    (292+80+88 gap=460)
            # Right C-shape (open left side)
            Obstacle(880, 296, 240, 88, "scifi_crate"),   # top rail
            Obstacle(1040, 404, 80, 80, "scifi_crate"),   # right post  (296+88+20=404)
            Obstacle(880, 504, 240, 88, "scifi_crate"),   # bot rail    (404+80+20=504)
            # Server dividers — linking the two C-shapes visually
            Obstacle(600, 184, 96, 96, "scifi_server"),   # top divider (296+240+64 gap=600)
            Obstacle(600, 504, 96, 96, "scifi_server"),   # bot divider
        ])
        # Accent crates — far corners, each isolated
        cargo_bay.obstacles.extend([
            Obstacle(200, 580, 64, 64, "scifi_crate"),    # far-left low
            Obstacle(200, 664, 64, 64, "scifi_crate"),    # below  (580+64+20=664)
            Obstacle(1240, 184, 64, 64, "scifi_crate"),   # far-right high
            Obstacle(1240, 268, 64, 64, "scifi_crate"),   # below  (184+64+20=268)
        ])
        # Switches — placed in clear open areas far from obstacles
        switch_1 = SequenceSwitch(1340, 680, 1)   # far right-bottom corner
        switch_1.allowed = True
        switch_2 = SequenceSwitch(480, 700, 2)    # left bottom open strip
        switch_2.allowed = True
        cargo_bay.interactables.extend([switch_1, switch_2])
        self.all_switches.extend([switch_1, switch_2])
        cargo_bay.enemies.extend([
            self._spawn_enemy("heavy", 800, 400),
            self._spawn_enemy("interceptor", 400, 800),
            self._spawn_enemy("seeker", 1200, 200),
        ])

        # Research labs: four isolated server terminals at room corners +
        # two crate barricades on mid-edges. All ≥20 px from walls/switches.
        lab_sector.walls.extend([
            pygame.Rect(400, 400, 600, 40),
            pygame.Rect(680, 200, 40, 200),
        ])
        lab_sector.obstacles.extend([
            Obstacle(296, 216, 96, 96, "scifi_server"),    # TL terminal
            Obstacle(1144, 216, 96, 96, "scifi_server"),   # TR terminal
            Obstacle(296, 552, 96, 96, "scifi_server"),    # BL terminal
            Obstacle(1144, 552, 96, 96, "scifi_server"),   # BR terminal
            Obstacle(200, 390, 104, 80, "scifi_crate"),    # left mid barricade (clear of wall at y=400+40=440; crate bottom = 390+80=470 → overlaps wall! fix: 200,312)
        ])
        # Fix: left barricade must not overlap wall_h (y=400..440): place at y=312 (bottom=312+80=392 → clear)
        lab_sector.obstacles.clear()
        lab_sector.obstacles.extend([
            Obstacle(296, 216, 96, 96, "scifi_server"),    # TL terminal
            Obstacle(1144, 216, 96, 96, "scifi_server"),   # TR terminal
            Obstacle(296, 552, 96, 96, "scifi_server"),    # BL terminal
            Obstacle(1144, 552, 96, 96, "scifi_server"),   # BR terminal
            Obstacle(200, 128, 104, 68, "scifi_crate"),    # left mid-barricade  (bottom=196, server_TL top=216 → gap=20 ✓, clear of wall_h)
            Obstacle(1232, 128, 104, 68, "scifi_crate"),   # right mid-barricade
        ])
        # Switches — switch_4 clear of wall_v (x=680..720) and wall_h (y=400..440)
        switch_3 = SequenceSwitch(820, 700, 3)   # below wall_h, right quadrant
        switch_3.allowed = True
        switch_4 = SequenceSwitch(480, 120, 4)   # top-left open area, clear of wall_v
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

        # Antenna field: staggered server towers + isolated crate pockets.
        # Three corridors (top/centre/bottom) with clear flanking paths.
        # Every rect ≥20 px from its neighbours and from antennas.
        array_field.obstacles.extend([
            Obstacle(264, 184, 112, 288, "scifi_server"),   # left tall tower
            Obstacle(536, 536, 224, 96, "scifi_server"),    # lower-centre bar   (264+112+160=536)
            Obstacle(764, 184, 256, 96, "scifi_server"),    # upper-centre bar
            Obstacle(984, 416, 96, 256, "scifi_server"),    # right-mid tower    (764+256+...; 764>536 ok)
            Obstacle(1204, 168, 96, 224, "scifi_server"),   # far-right upper    (984+96+124=1204)
        ])
        # Isolated crate pockets — each separated by ≥20 px, clear of servers and antennas
        # Antenna 1 = (200,150,24,70): bottom=220. Crates must be >240
        # Antenna 2 = (600,700,24,70): keep crates away from x=560-660,y=680-790
        # Antenna 3 = (1350,450,24,70): keep crates away from x=1330-1400,y=440-530
        array_field.obstacles.extend([
            Obstacle(432, 140, 72, 72, "scifi_crate"),    # top-mid pocket A (clear of server_top at x=764)
            Obstacle(432, 232, 72, 72, "scifi_crate"),    # below A          (140+72+20=232)
            Obstacle(1108, 572, 72, 72, "scifi_crate"),   # bot-right pocket A (clear of antenna_2 and server_Rm)
            Obstacle(1108, 664, 72, 72, "scifi_crate"),   # below B          (572+72+20=664)
        ])
        # Antennas — placed in open areas clear of all obstacles
        # Antenna 1: x=200,y=150 — clear (left of server_L at x=264)
        # Antenna 2: x=660,y=700 — clear of server_bot (512+224=736>660? 512..736 x, 536..632 y → antenna at x=660 overlaps server_bot x range 512..736!)
        # Fix antenna 2 to x=760, y=700 — server_bot spans x=536..760 → right edge = 760. Antenna at x=760 is just clear.
        # Actually server_bot = Obstacle(536, 536, 224, 96) → x=536 to x=760. Antenna at x=760 starts exactly at right edge → add 20 px margin: x=780
        array_field.interactables = [
            Antenna(200, 150, 1),    # left open quadrant
            Antenna(780, 700, 2),    # bottom right of server_bot (server_bot right=760, 760+20=780 ✓)
            Antenna(1350, 450, 3),   # far right (right of server_Rhi right=1204+96=1300, 1300+50=1350 ✓)
        ]
        self.all_antennas = list(array_field.interactables)
        # Message fragment — clear of server_top (x=764..1020, y=184..280)
        array_field.message_fragments.append(MessageFragment(680, 700, "Fragment 3/3: FATAL. The rogue proxy is broadcasting its virus. Destroy the Boss Drone to stop the override!"))
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

        # Command core: outer corner crate ring + two server bridges in the centre.
        # Accent crates placed far from corner crates.
        command_core.obstacles.extend([
            Obstacle(200, 168, 128, 128, "scifi_crate"),    # TL corner
            Obstacle(200, 568, 128, 128, "scifi_crate"),    # BL corner  (168+128+272 gap=568)
            Obstacle(464, 312, 128, 128, "scifi_crate"),    # inner-left mid
            Obstacle(944, 312, 128, 128, "scifi_crate"),    # inner-right mid  (464+128+352=944)
            Obstacle(1208, 168, 128, 128, "scifi_crate"),   # TR corner
            Obstacle(1208, 568, 128, 128, "scifi_crate"),   # BR corner
            Obstacle(666, 240, 128, 80, "scifi_server"),    # upper bridge     (clear of inner-left: 464+128=592, 592+74=666 ✓)
            Obstacle(666, 520, 128, 80, "scifi_server"),    # lower bridge     (240+80+200 gap=520)
        ])
        # Accent crates — between corner and inner, ≥20 px from both
        command_core.obstacles.extend([
            Obstacle(360, 168, 80, 80, "scifi_crate"),    # TL accent  (200+128+32=360; inner-left at 464 → 360+80=440, 464-440=24 ✓)
            Obstacle(360, 264, 80, 80, "scifi_crate"),    # below TL   (168+80+16=264 → 264+80=344 < 360 ✓ but check vs TL: 200+128=328, 360>328+20 → 360-328=32 ✓)
            Obstacle(1096, 568, 80, 80, "scifi_crate"),   # BR accent  (1208-80-32=1096; inner-right right=944+128=1072, 1096-1072=24 ✓)
            Obstacle(1096, 664, 80, 80, "scifi_crate"),   # below BR   (568+80+16=664; BR corner at 568+128=696>664... overlap! fix: 568+128+20=716)
        ])
        # Fix last accent: BR corner bottom = 568+128=696, so below must be 696+20=716
        command_core.obstacles[-1] = Obstacle(1096, 716, 80, 80, "scifi_crate")
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

    def spawn_portal(self, cx: int, cy: int) -> None:
        """Spawn the level-exit portal at the given centre position."""
        frames = self.visual_assets.get_portal_frames()
        self.portal = Portal(cx, cy, frames)
        self.portal_active = True
        self._portal_spawned = True

    def check_portal_entered(self, player) -> bool:
        """Return True the frame the player walks into the active portal."""
        if self.portal_active and self.portal is not None:
            return self.portal.player_entered(player)
        return False

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

    def try_interact(self, player, dt: float, holding: bool) -> tuple[bool, str | None, bool]:
        room = self.current_room

        for log in room.message_fragments:
            if log.can_interact(player) and holding:
                triggered = log.interact(dt, True)
                if triggered:
                    return True, log.text, True

        for obj in room.interactables:
            if not obj.can_interact(player):
                if getattr(obj, "requires_hold", False):
                    obj.reset_progress()
                continue

            if isinstance(obj, Antenna):
                triggered = obj.interact(dt, holding)
                if triggered:
                    activated_count = sum(1 for antenna in self.all_antennas if antenna.completed)
                    self._start_antenna_wave(activated_count)
                    return True, f"Antenna {obj.index} aligned", False
                continue

            if isinstance(obj, SequenceSwitch):
                if not holding:
                    continue
                triggered = obj.interact(dt, holding)
                if triggered and self.all_switches_active():
                    self._status_message = "All switches active. Final gate unlocked."
                if triggered:
                    return True, f"Switch {obj.index} active", False
                continue

            if isinstance(obj, WeaponPickup):
                if holding:
                    continue
                triggered = obj.interact(dt, False)
                if triggered:
                    player.play_pickup()
                    player.weapon_module = obj.weapon_type
                    return True, f"Equipped {obj.weapon_type.capitalize()}", False
                continue

            if holding:
                triggered = obj.interact(dt, holding)
                if triggered:
                    return True, None, False

        return False, None, False

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
        """Return True when the level is done AND the portal has already been
        spawned (meaning check_portal_entered() should drive the actual exit).
        First time conditions are met we spawn the portal and return False so
        the game loop waits for the player to walk in.
        """
        conditions_met = False

        if self.level_id == 1:
            all_conduits_done = all(conduit.completed for conduit in self.all_conduits)
            all_enemies_down = all(not enemy.alive for room in self.rooms.values() for enemy in room.enemies)
            conditions_met = all_conduits_done and all_enemies_down

        elif self.level_id == 2:
            conditions_met = False  # Level 2 exit is handled via the physical door/gate

        elif self.level_id == 3:
            if not self.boss_spawned:
                conditions_met = False
            elif self.final_boss and self.final_boss.alive:
                conditions_met = False
            else:
                conditions_met = all(not enemy.alive for enemy in self.rooms["command_core"].enemies)

        if conditions_met and not self._portal_spawned:
            # Choose a safe centre for the portal (room centre, slightly away from walls)
            room = self.current_room
            cx = int(room.spawn_point.x)  # near original spawn is always clear
            cy = SCREEN_HEIGHT // 2
            # For level 3 command core, spawn slightly right of centre so
            # it doesn't overlap the boss spawn region
            if self.level_id == 3:
                cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
            self.spawn_portal(cx, cy)
            self._status_message = "Portal opened! Step through to advance."

        return False  # Let check_portal_entered() trigger the actual level exit

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

        if self.portal_active and self.portal is not None:
            self.portal.draw(surface)
