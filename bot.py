from __future__ import annotations

import asyncio
import json
import math
import os
import random
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from dotenv import load_dotenv



load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SHEET_WORKSHEET = os.getenv("GOOGLE_SHEET_WORKSHEET", "플레이어 현황")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
KST = ZoneInfo("Asia/Seoul")
DB_PATH = Path("/data/game.db")

COLORS = ("시안", "마젠타", "옐로")
COLOR_MARK = {"시안": "🩵", "마젠타": "🩷", "옐로": "💛"}
ANSI_COLOR = {"시안": 36, "마젠타": 35, "옐로": 33}
EMBED_COLORS = {
    "시안": 0x00DDE0,
    "마젠타": 0xF000B8,
    "옐로": 0xF4D800,
}
DIR_EMOJI = {"위": "⬆️", "오른쪽": "➡️", "아래": "⬇️", "왼쪽": "⬅️"}
RUN_SUCCESS_RATE = 0.65
MAX_DAILY_LIVES = 3
PERFECT_WINDOW_BONUS = 0.10
CRITICAL_HP_RATIO = 0.25
CRITICAL_PERFECT_WINDOW_BONUS = 0.20
PERFECT_COUNTER_DAMAGE = 2
BLEED_MAX_STACKS = 3
BLEED_DURATION_SECONDS = 4.0
BLEED_TICK_SECONDS = 1.0
BOMB_DAMAGE = (10, 14)
DEFEAT_SHAKE_FRAME_DELAY = 0.18
DEFEAT_SHAKE_END_HOLD = 0.28

NORMAL_ENEMIES = ("크랩", "옥토퍼스", "스퀴드")

SHAPES = {
    "크랩": {
        "hp": (9, 13),
        "damage": (4, 6),
        "attack_perfect": 0.85,
        "attack_good": 1.40,
        "defend_perfect": 0.90,
        "defend_good": 1.50,
        "cue_delay": (1.4, 3.0),
        "coin_drop": (2, 4),
    },
    "옥토퍼스": {
        "hp": (7, 11),
        "damage": (3, 5),
        "attack_perfect": 0.75,
        "attack_good": 1.25,
        "defend_perfect": 0.80,
        "defend_good": 1.30,
        "cue_delay": (1.0, 2.6),
        "coin_drop": (2, 5),
    },
    "스퀴드": {
        "hp": (5, 9),
        "damage": (3, 5),
        "attack_perfect": 0.65,
        "attack_good": 1.05,
        "defend_perfect": 0.70,
        "defend_good": 1.10,
        "cue_delay": (0.8, 2.2),
        "coin_drop": (3, 5),
    },
    "보스": {
        "hp": (22, 28),
        "damage": (5, 7),
        "attack_perfect": 0.70,
        "attack_good": 1.15,
        "defend_perfect": 0.75,
        "defend_good": 1.20,
        "cue_delay": (0.9, 2.4),
        "coin_drop": (7, 11),
    },
}

DIRECTIONS = {
    "왼쪽": (-1, 0),
    "위": (0, -1),
    "아래": (0, 1),
    "오른쪽": (1, 0),
}

FLOOR_TRIVIA = [
    "꼬지모의 영문명 Sudowoodo는 'pseudo wood', 즉 '가짜 나무'에서 왔다.",
    "프리져·썬더·파이어의 영문명 Articuno·Zapdos·Moltres에는 uno·dos·tres가 차례로 들어간다.",
    "피카츄 디자이너 니시다 아츠코는 피카츄를 디자인할 때 다람쥐를 떠올렸다.",
    "코뿌리는 가장 먼저 디자인된 포켓몬으로 알려져 있다.",
    "포켓몬스터 1세대 개발 초기에는 패배한 트레이너의 포켓몬을 상대가 가져가는 시스템도 검토됐다.",
    "기술 '물기'는 물리→특수→물리로 분류가 두 번 바뀌었다.",
    "3·4세대 더블배틀에서는 START 버튼을 누르면 포켓몬의 HP가 숫자로 표시된다.",
    "톱치는 플라이곤과 공격 종족값이 같다. 비브라바로 진화할 때 내려갔다가 플라이곤이 되면 다시 오른다.",
    "기술 '튀어오르기'의 일본판 이름은 '튀다'에 가까워서 잉어킹 말고도 여러 포켓몬이 배운다.",
    "중력이 강해진 상태에서는 '튀어오르기'를 사용할 수 없다.",
    "1세대에서 오박사가 소개하는 니드리노는 니드리나의 울음소리를 낸다.",
    "암컷 마자용은 입술 모양의 무늬로 성별을 구분할 수 있다.",
    "사철록의 영문명 Sawsbuck에는 Summer·Autumn·Winter·Spring의 머리글자 SAWS가 들어간다.",
    "피카츄의 전국도감 번호는 25번, 나옹은 52번이다.",
    "커비는 개발 초기에 '포포포'라는 이름으로 불렸다.",
    "초대 '별의 커비'에는 아직 카피 능력이 없었다.",
    "카피 능력이 처음 등장한 작품은 '별의 커비 꿈의 샘 이야기'다.",
    "커비의 둥근 디자인은 개발 중 임시로 쓰던 단순한 그래픽에서 출발했다.",
    "별의 커비에 등장하는 적 아폴로는 일본 과자 '아폴로'가 모티브라서 삼키면 체력이 회복된다.",
    "마르크는 초기 일본 일러스트에서 안경을 쓰고 있었다.",
    "북미판 커비 패키지에서 커비가 더 화난 표정을 짓던 것은 실제 현지 마케팅 방향이었다.",
    "별의 커비 시리즈는 일시정지 화면에 보스나 세계관 설정을 적어 둔 작품이 여럿 있다.",
    "마리오가 게임 안에서 처음 'Mario'라는 이름으로 불린 작품은 'Donkey Kong Jr.'다.",
    "루이지의 첫 등장은 아케이드판보다 먼저 나온 Game & Watch판 'Mario Bros.'다.",
    "서양판에서 피치 공주를 'Peach'라고 부른 것은 'Yoshi's Safari'가 'Super Mario 64'보다 먼저였다.",
    "초대 'Super Mario Bros.'의 구름과 수풀은 같은 모양의 그래픽에 색만 다르게 썼다.",
    "서양판 'Super Mario Bros. 2'는 원래 다른 게임인 '꿈공장 도키도키 패닉'을 마리오 게임으로 바꾼 작품이다.",
    "N64 'Mario Party' 시리즈에서 와리오는 독일어 대사를 말하는 음성이 있다.",
    "일본판 초대 '젤다의 전설'에서는 패미컴 2P 컨트롤러의 마이크에 소리를 내서 폴스 보이스를 쓰러뜨릴 수 있다.",
    "'젤다의 전설 꿈꾸는 섬'에서 상점 물건을 훔치면 이후 게임이 플레이어를 'THIEF'라고 부른다.",
    "'무쥬라의 가면'의 세계는 3일이 지나면 달이 떨어져 처음으로 되돌아간다.",
    "'동물의 숲' 시리즈 일부 작품에서는 새벽 3시 33분에 TV를 켜면 외계인 방송이 나온다.",
    "'튀어나와요 동물의 숲'에서는 일부 은 도구가 금 도구에 없는 고유 기능을 갖고 있다.",
    "'모여봐요 동물의 숲'의 일부 가짜 미술품은 밤이 되면 모습이 변한다.",
    "'Minecraft'의 철 골렘이 주민에게 꽃을 건네는 모습은 '천공의 성 라퓨타'의 로봇을 참고했다.",
    "'Minecraft'에서는 자연적으로 분홍색 양이 태어날 수 있다.",
    "'Minecraft'의 엔드 함선에 남아 있는 자홍색 유리는 개발 중 비콘 테스트의 흔적으로 알려져 있다.",
    "'Portal'의 연구실 모니터 뒤에는 케이크 레시피가 숨겨져 있다.",
    "'Metal Gear Solid 2'의 얼음 조각은 시간이 지나면 실제로 녹는다.",
]


ENEMY_ART_FRAMES = {
    "스퀴드": (
        "⢀⡴⣿⢦⡀\n⢈⢝⠭⡫⡁",
        "⢀⡴⣿⢦⡀\n⠨⡋⠛⢙⠅",
    ),
    "크랩": (
        "⢀⡵⣤⡴⣅\n⠏⢟⡛⣛⠏⠇",
        "⣆⡵⣤⡴⣅⡆\n⢘⠟⠛⠛⢟",
    ),
    "옥토퍼스": (
        "⣴⡶⢿⡿⢶⣦\n⠩⣟⠫⠝⣻⠍",
        "⣴⡶⢿⡿⢶⣦\n⣉⠽⠫⠝⠯⣉",
    ),
    "보스": (
        "⢀⡴⣾⢿⡿⣷⢦⡀\n⠉⠻⠋⠙⠋⠙⠟⠉",
    ),
}

ASCII_ART = {shape: frames[0] for shape, frames in ENEMY_ART_FRAMES.items()}


@dataclass
class Gear:
    kind: str
    name: str
    power: int
    affinity: Dict[str, int]

    def label(self) -> str:
        pips = []
        for color in COLORS:
            n = self.affinity.get(color, 0)
            pips.append(f"{COLOR_MARK[color]} {'●' * n if n else '○'}")
        stat = "공격" if self.kind == "weapon" else "방어"
        return f"{self.name} | {stat} {self.power} | {'  '.join(pips)}"

    def to_json(self) -> str:
        return json.dumps(
            {
                "kind": self.kind,
                "name": self.name,
                "power": self.power,
                "affinity": self.affinity,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def from_json(raw: str) -> "Gear":
        d = json.loads(raw)
        return Gear(d["kind"], d["name"], d["power"], d["affinity"])


START_WEAPON = Gear(
    "weapon", "유리 파편", 4, {"시안": 1, "마젠타": 0, "옐로": 0}
)
START_ARMOR = Gear(
    "armor", "화물 상자 뚜껑", 1, {"시안": 0, "마젠타": 1, "옐로": 0}
)


@dataclass
class Enemy:
    shape: str
    color: str
    hp: int
    max_hp: int
    damage: int
    boss: bool = False
    bleed_stacks: int = 0
    bleed_expires_at: float = 0.0

    @property
    def art(self) -> str:
        return ASCII_ART[self.shape]


@dataclass
class Room:
    pos: Tuple[int, int]
    kind: str = "normal"
    visited: bool = False
    cleared: bool = False
    enemy: Optional[Enemy] = None
    shop_stock: list[Gear] = field(default_factory=list)
    bomb_stock: int = 0
    slot_uses: int = 0
    slot_broken: bool = False


@dataclass
class PlayerState:
    guild_id: int
    user_id: int
    coins: int
    bombs: int
    max_hp: int
    hp: int
    weapon: Gear
    armor: Gear
    last_day: str
    status: str
    floor_number: int
    highest_floor: int
    lives_used: int
    tutorial_completed: bool


@dataclass
class GameSession:
    guild_id: int
    user_id: int
    day_key: str
    floor_number: int
    rooms: Dict[Tuple[int, int], Room]
    current: Tuple[int, int]
    boss_pos: Tuple[int, int]
    secret_pos: Tuple[int, int]
    secret_from: Tuple[int, int]
    secret_direction: str
    is_tutorial: bool = False
    tutorial_replay: bool = False
    temp_player: Optional[PlayerState] = None
    secret_revealed: bool = False
    boss_defeated: bool = False
    ended: bool = False
    phase: str = "explore"
    previous: Optional[Tuple[int, int]] = None
    cue_started: Optional[float] = None
    cue_kind: Optional[str] = None
    cue_state: str = "idle"
    cue_token: int = 0
    cue_task: Optional[asyncio.Task] = field(default=None, repr=False)
    bleed_token: int = 0
    bleed_task: Optional[asyncio.Task] = field(default=None, repr=False)
    hit_animating: bool = False
    enemy_anim_frame: int = 0

    def room(self) -> Room:
        return self.rooms[self.current]



class Database:
    def __init__(self, path: Path):
        self.path = path
        self.init()

    def connect(self):
        return sqlite3.connect(self.path)

    def init(self):
        with self.connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS players (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    coins INTEGER NOT NULL DEFAULT 3,
                    bombs INTEGER NOT NULL DEFAULT 2,
                    max_hp INTEGER NOT NULL DEFAULT 20,
                    hp INTEGER NOT NULL DEFAULT 20,
                    weapon_json TEXT NOT NULL,
                    armor_json TEXT NOT NULL,
                    last_day TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'ready',
                    floor_number INTEGER NOT NULL DEFAULT 1,
                    highest_floor INTEGER NOT NULL DEFAULT 1,
                    lives_used INTEGER NOT NULL DEFAULT 0,
                    tutorial_completed INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            columns = {
                row[1] for row in con.execute("PRAGMA table_info(players)").fetchall()
            }
            if "floor_number" not in columns:
                con.execute(
                    "ALTER TABLE players ADD COLUMN floor_number INTEGER NOT NULL DEFAULT 1"
                )
            if "highest_floor" not in columns:
                con.execute(
                    "ALTER TABLE players ADD COLUMN highest_floor INTEGER NOT NULL DEFAULT 1"
                )
            if "lives_used" not in columns:
                con.execute(
                    "ALTER TABLE players ADD COLUMN lives_used INTEGER NOT NULL DEFAULT 0"
                )
            if "tutorial_completed" not in columns:

                con.execute(
                    "ALTER TABLE players ADD COLUMN tutorial_completed INTEGER NOT NULL DEFAULT 1"
                )

    def get_player(self, guild_id: int, user_id: int) -> PlayerState:
        with self.connect() as con:
            row = con.execute(
                """
                SELECT guild_id, user_id, coins, bombs, max_hp, hp,
                       weapon_json, armor_json, last_day, status, floor_number,
                       highest_floor, lives_used, tutorial_completed
                FROM players
                WHERE guild_id=? AND user_id=?
                """,
                (guild_id, user_id),
            ).fetchone()

            if row is None:
                con.execute(
                    """
                    INSERT INTO players
                    (guild_id, user_id, coins, bombs, max_hp, hp,
                     weapon_json, armor_json, last_day, status, floor_number,
                     highest_floor, lives_used, tutorial_completed)
                    VALUES (?, ?, 3, 2, 20, 20, ?, ?, '', 'ready', 1, 1, 0, 0)
                    """,
                    (
                        guild_id,
                        user_id,
                        START_WEAPON.to_json(),
                        START_ARMOR.to_json(),
                    ),
                )
                con.commit()
                return self.get_player(guild_id, user_id)

        return PlayerState(
            guild_id=row[0],
            user_id=row[1],
            coins=row[2],
            bombs=row[3],
            max_hp=row[4],
            hp=row[5],
            weapon=Gear.from_json(row[6]),
            armor=Gear.from_json(row[7]),
            last_day=row[8],
            status=row[9],
            floor_number=row[10],
            highest_floor=row[11],
            lives_used=row[12],
            tutorial_completed=bool(row[13]),
        )

    def save_player(self, p: PlayerState):
        with self.connect() as con:
            con.execute(
                """
                UPDATE players
                SET coins=?, bombs=?, max_hp=?, hp=?,
                    weapon_json=?, armor_json=?, last_day=?, status=?,
                    floor_number=?, highest_floor=?, lives_used=?,
                    tutorial_completed=?
                WHERE guild_id=? AND user_id=?
                """,
                (
                    p.coins,
                    p.bombs,
                    p.max_hp,
                    p.hp,
                    p.weapon.to_json(),
                    p.armor.to_json(),
                    p.last_day,
                    p.status,
                    p.floor_number,
                    p.highest_floor,
                    p.lives_used,
                    int(p.tutorial_completed),
                    p.guild_id,
                    p.user_id,
                ),
            )
            con.commit()

    def leaderboard(self, guild_id: int, limit: int = 10):
        with self.connect() as con:
            return con.execute(
                """
                SELECT user_id, floor_number, coins
                FROM players
                WHERE guild_id=?
                ORDER BY floor_number DESC, coins DESC, user_id ASC
                LIMIT ?
                """,
                (guild_id, limit),
            ).fetchall()

    def all_players(self, guild_id: int):
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT guild_id, user_id, coins, bombs, max_hp, hp,
                       weapon_json, armor_json, last_day, status, floor_number,
                       highest_floor, lives_used, tutorial_completed
                FROM players
                WHERE guild_id=?
                ORDER BY floor_number DESC, coins DESC, user_id ASC
                """,
                (guild_id,),
            ).fetchall()

        return [
            PlayerState(
                guild_id=row[0],
                user_id=row[1],
                coins=row[2],
                bombs=row[3],
                max_hp=row[4],
                hp=row[5],
                weapon=Gear.from_json(row[6]),
                armor=Gear.from_json(row[7]),
                last_day=row[8],
                status=row[9],
                floor_number=row[10],
                highest_floor=row[11],
                lives_used=row[12],
                tutorial_completed=bool(row[13]),
            )
            for row in rows
        ]

    def test_reset(self, guild_id: int, user_id: int):
        p = self.get_player(guild_id, user_id)
        p.hp = p.max_hp
        p.last_day = ""
        p.status = "ready"
        p.floor_number = 1
        p.lives_used = 0
        self.save_player(p)


db = Database(DB_PATH)
sessions: Dict[Tuple[int, int], GameSession] = {}
tutorial_sessions: Dict[Tuple[int, int], GameSession] = {}


def session_player(session: GameSession) -> PlayerState:
    if session.is_tutorial:
        assert session.temp_player is not None
        return session.temp_player
    return db.get_player(session.guild_id, session.user_id)


def save_session_player(session: GameSession, player: PlayerState):
    if session.is_tutorial:
        session.temp_player = player
        return
    db.save_player(player)


def remaining_lives(player: PlayerState) -> int:
    return max(0, MAX_DAILY_LIVES - player.lives_used)


def today_key() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def add_pos(a, b):
    return a[0] + b[0], a[1] + b[1]


def random_affinity(min_points=1, max_points=3):
    min_points = max(0, min(6, min_points))
    max_points = max(min_points, min(6, max_points))
    result = {c: 0 for c in COLORS}
    for _ in range(random.randint(min_points, max_points)):
        choices = [c for c in COLORS if result[c] < 2]
        result[random.choice(choices)] += 1
    return result


def gear_price(gear: Gear, floor_number: int) -> int:
    floor_bonus = max(0, floor_number - 1)
    if gear.kind == "weapon":
        return 18 + floor_bonus * 4
    return 15 + floor_bonus * 3


def bomb_price(floor_number: int) -> int:
    return 8 + max(0, floor_number - 1) * 2


def generate_gear(kind: str, boss_drop=False, floor_number: int = 1) -> Gear:
    floor_bonus = max(0, floor_number - 1)

    if kind == "weapon":
        names = [
            "유리 파편",
            "금속 파이프",
            "깨진 칼날",
            "고장 난 절단기",
            "비상 신호총",
        ]
        low = 6 if boss_drop else 5
        high = 9 if boss_drop else 7
        power = random.randint(low, high) + floor_bonus
    else:
        names = [
            "화물 상자 뚜껑",
            "기계 덮개",
            "깨진 방탄유리",
            "비상문 조각",
            "금 간 방패",
        ]
        low = 2 if boss_drop else 1
        high = 4 if boss_drop else 3
        power = random.randint(low, high) + floor_bonus // 2

    affinity_bonus = min(2, floor_bonus // 2)
    return Gear(
        kind=kind,
        name=random.choice(names),
        power=power,
        affinity=random_affinity(
            (2 if boss_drop else 1) + affinity_bonus,
            (4 if boss_drop else 3) + affinity_bonus,
        ),
    )


def make_enemy(boss=False, floor_number: int = 1) -> Enemy:
    shape = "보스" if boss else random.choice(NORMAL_ENEMIES)
    color = random.choice(COLORS)
    spec = SHAPES[shape]
    floor_bonus = max(0, floor_number - 1)

    hp = random.randint(*spec["hp"]) + floor_bonus * (4 if boss else 2)
    damage = random.randint(*spec["damage"]) + floor_bonus // 2

    return Enemy(shape, color, hp, hp, damage, boss)


def bfs_distances(positions, start=(0, 0)):
    positions = set(positions)
    distance = {start: 0}
    queue = [start]

    while queue:
        cur = queue.pop(0)
        for delta in DIRECTIONS.values():
            nxt = add_pos(cur, delta)
            if nxt in positions and nxt not in distance:
                distance[nxt] = distance[cur] + 1
                queue.append(nxt)

    return distance


def generate_floor(guild_id: int, user_id: int, day: str, floor_number: int = 1) -> GameSession:
    positions = {(0, 0)}
    while len(positions) < 8:
        anchor = random.choice(tuple(positions))
        delta = random.choice(tuple(DIRECTIONS.values()))
        positions.add(add_pos(anchor, delta))

    distances = bfs_distances(positions)
    boss_pos = max(distances, key=distances.get)

    rooms: Dict[Tuple[int, int], Room] = {}

    regular_positions = [
        pos for pos in positions
        if pos != (0, 0) and pos != boss_pos
    ]

    room_kinds = random.choices(
        ("normal", "coin", "empty", "pot"),
        weights=(55, 15, 15, 15),
        k=len(regular_positions),
    )

    while room_kinds.count("normal") < min(2, len(room_kinds)):
        index = random.randrange(len(room_kinds))
        room_kinds[index] = "normal"

    kind_by_pos = dict(zip(regular_positions, room_kinds))

    for pos in positions:
        if pos == (0, 0):
            rooms[pos] = Room(pos, "start", visited=True, cleared=True)
        elif pos == boss_pos:
            rooms[pos] = Room(pos, "boss", enemy=make_enemy(True, floor_number))
        else:
            kind = kind_by_pos[pos]
            if kind == "normal":
                rooms[pos] = Room(pos, "normal", enemy=make_enemy(False, floor_number))
            else:
                rooms[pos] = Room(pos, kind)

    candidates = []
    for source in positions:
        if source == boss_pos:
            continue
        for direction, delta in DIRECTIONS.items():
            target = add_pos(source, delta)
            if target not in positions:
                candidates.append((source, direction, target))

    secret_from, secret_direction, secret_pos = random.choice(candidates)
    secret_kind = random.choice(("shop", "slot"))

    secret = Room(secret_pos, secret_kind)
    if secret_kind == "shop":
        secret.shop_stock = [
            generate_gear("weapon", floor_number=floor_number),
            generate_gear("armor", floor_number=floor_number),
        ]
        secret.bomb_stock = random.randint(1, 3)

    rooms[secret_pos] = secret

    return GameSession(
        guild_id=guild_id,
        user_id=user_id,
        day_key=day,
        floor_number=floor_number,
        rooms=rooms,
        current=(0, 0),
        boss_pos=boss_pos,
        secret_pos=secret_pos,
        secret_from=secret_from,
        secret_direction=secret_direction,
    )



def make_tutorial_player(guild_id: int, user_id: int) -> PlayerState:
    return PlayerState(
        guild_id=guild_id,
        user_id=user_id,
        coins=20,
        bombs=2,
        max_hp=20,
        hp=20,
        weapon=Gear.from_json(START_WEAPON.to_json()),
        armor=Gear.from_json(START_ARMOR.to_json()),
        last_day="",
        status="tutorial",
        floor_number=0,
        highest_floor=0,
        lives_used=0,
        tutorial_completed=False,
    )


def generate_tutorial(guild_id: int, user_id: int, *, replay: bool) -> GameSession:
    practice_enemy = make_enemy(False, 1)
    practice_enemy.hp = 7
    practice_enemy.max_hp = 7
    practice_enemy.damage = 0

    boss = make_enemy(True, 1)
    boss.hp = 14
    boss.max_hp = 14
    boss.damage = 3

    rooms: Dict[Tuple[int, int], Room] = {
        (0, 0): Room((0, 0), "start", visited=True, cleared=True),
        (1, 0): Room((1, 0), "normal", enemy=practice_enemy),
        (2, 0): Room((2, 0), "coin"),
        (2, 1): Room((2, 1), "pot"),
        (3, 0): Room((3, 0), "boss", enemy=boss),
    }

    secret_pos = (3, 1)
    secret = Room(secret_pos, "shop")
    secret.shop_stock = [
        generate_gear("weapon", floor_number=1),
        generate_gear("armor", floor_number=1),
    ]
    secret.bomb_stock = 2
    rooms[secret_pos] = secret

    return GameSession(
        guild_id=guild_id,
        user_id=user_id,
        day_key=today_key(),
        floor_number=0,
        rooms=rooms,
        current=(0, 0),
        boss_pos=(3, 0),
        secret_pos=secret_pos,
        secret_from=(2, 1),
        secret_direction="오른쪽",
        is_tutorial=True,
        tutorial_replay=replay,
        temp_player=make_tutorial_player(guild_id, user_id),
    )


def tutorial_start_note(replay: bool) -> str:
    return ""


def hp_bar(current: int, maximum: int, width=8, enemy=False):
    ratio = max(0, current) / max(1, maximum)
    filled = round(width * ratio)
    if enemy:
        full = "🟥"
    elif ratio > 0.5:
        full = "🟩"
    elif ratio > 0.25:
        full = "🟨"
    else:
        full = "🟥"
    return full * filled + "⬛" * (width - filled)


def bleed_seconds_left(enemy: Enemy) -> float:
    if enemy.bleed_stacks <= 0 or enemy.bleed_expires_at <= 0 or enemy.hp <= 0:
        return 0.0
    return max(0.0, enemy.bleed_expires_at - time.monotonic())


def bleed_pending_damage(enemy: Enemy) -> int:
    seconds = bleed_seconds_left(enemy)
    if seconds <= 0:
        return 0
    ticks = max(0, math.ceil((seconds - 0.001) / BLEED_TICK_SECONDS))
    return min(max(0, enemy.hp), enemy.bleed_stacks * ticks)


def enemy_hp_bar(enemy: Enemy, width=8) -> str:
    current = max(0, enemy.hp)
    maximum = max(1, enemy.max_hp)
    filled = max(0, min(width, round(width * current / maximum)))
    pending = bleed_pending_damage(enemy)

    yellow = 0
    if pending > 0 and filled > 0:
        yellow = max(1, round(width * min(current, pending) / maximum))
        yellow = min(filled, yellow)

    red = filled - yellow
    return "🟥" * red + "🟨" * yellow + "⬛" * (width - filled)


def enemy_is_critical(enemy: Enemy) -> bool:
    return 0 < enemy.hp <= enemy.max_hp * CRITICAL_HP_RATIO


def shift_ascii_art(art: str, offset: int) -> str:
    if offset == 0:
        return art

    shifted = []
    for line in art.splitlines():
        if not line:
            shifted.append(line)
        elif offset < 0:
            shifted.append(line[1:] + "░")
        else:
            shifted.append("░" + line[:-1])
    return "\n".join(shifted)


def current_enemy_art(session: GameSession, enemy: Enemy) -> str:
    frames = ENEMY_ART_FRAMES.get(enemy.shape, (enemy.art,))
    if not frames:
        return enemy.art
    index = session.enemy_anim_frame % len(frames)
    return frames[index]


def advance_enemy_art(session: GameSession, enemy: Enemy) -> str:
    frames = ENEMY_ART_FRAMES.get(enemy.shape, (enemy.art,))
    if not frames:
        return enemy.art
    if len(frames) == 1:
        session.enemy_anim_frame = 0
        return frames[0]
    session.enemy_anim_frame = (session.enemy_anim_frame + 1) % len(frames)
    return frames[session.enemy_anim_frame]


def colored_enemy_art(enemy: Enemy, art: Optional[str] = None) -> str:
    code = ANSI_COLOR[enemy.color]
    art = enemy.art if art is None else art
    return f"```ansi\n\u001b[{code}m{art}\u001b[0m\n```"


def apply_bleed(enemy: Enemy) -> int:
    enemy.bleed_stacks = min(BLEED_MAX_STACKS, enemy.bleed_stacks + 1)
    enemy.bleed_expires_at = time.monotonic() + BLEED_DURATION_SECONDS
    return enemy.bleed_stacks


def clear_bleed(enemy: Enemy):
    enemy.bleed_stacks = 0
    enemy.bleed_expires_at = 0.0


def affinity(gear: Gear, color: str) -> int:
    return gear.affinity.get(color, 0)


def attack_damage(player: PlayerState, enemy: Enemy, grade: str) -> int:
    if grade == "MISS":
        return 0
    timing_mult = {"PERFECT": 1.40, "GOOD": 1.0}[grade]
    color_mult = 1.0 + 0.25 * affinity(player.weapon, enemy.color)
    return max(1, round(player.weapon.power * timing_mult * color_mult))


def incoming_damage(player: PlayerState, enemy: Enemy, grade: str) -> int:
    if grade == "PERFECT" or enemy.damage <= 0:
        return 0

    damage = enemy.damage
    if grade == "GOOD":
        damage = max(1, round(damage * 0.45))

    damage = max(0, damage - player.armor.power)
    resistance = max(0.35, 1.0 - 0.15 * affinity(player.armor, enemy.color))
    return max(0, round(damage * resistance))


def timing_windows(player: PlayerState, enemy: Enemy, kind: str):
    spec = SHAPES[enemy.shape]

    if kind == "attack":
        good = spec["attack_good"]
        critical_bonus = CRITICAL_PERFECT_WINDOW_BONUS if enemy_is_critical(enemy) else 0.0
        perfect = min(
            good,
            spec["attack_perfect"] + PERFECT_WINDOW_BONUS + critical_bonus,
        )
        return perfect, good

    extra = 0.05 * affinity(player.armor, enemy.color)
    good = spec["defend_good"] + extra
    perfect = min(good, spec["defend_perfect"] + PERFECT_WINDOW_BONUS + extra)
    return perfect, good


def timing_grade(seconds: float, perfect: float, good: float):
    if seconds <= perfect:
        return "PERFECT"
    if seconds <= good:
        return "GOOD"
    return "MISS"


def room_name(room: Room):
    return {
        "start": "시작 방",
        "normal": "전투 방",
        "boss": "보스 방",
        "coin": "버려진 코인",
        "empty": "빈 방",
        "pot": "항아리",
        "shop": "비밀 상점",
        "slot": "슬롯머신 방",
    }[room.kind]


def accessible_directions(session: GameSession):
    result = []
    for name, delta in DIRECTIONS.items():
        target = add_pos(session.current, delta)
        if target not in session.rooms:
            continue
        if target == session.secret_pos and not session.secret_revealed:
            continue
        result.append((name, target))
    return result


def crack_here(session: GameSession):
    return (
        not session.secret_revealed
        and session.current == session.secret_from
    )


def map_ascii(session: GameSession):
    visible = {
        p: room
        for p, room in session.rooms.items()
        if p != session.secret_pos or session.secret_revealed
    }

    xs = [p[0] for p in visible]
    ys = [p[1] for p in visible]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width = (max_x - min_x) * 4 + 3
    height = (max_y - min_y) * 2 + 1
    canvas = [[" " for _ in range(width)] for _ in range(height)]

    def cv(pos):
        return (pos[0] - min_x) * 4 + 1, (pos[1] - min_y) * 2

    for pos, room in visible.items():
        x, y = cv(pos)

        if pos == session.current:
            mark = "@"
        elif pos == session.secret_pos:
            mark = "S"
        elif pos == session.boss_pos:
            mark = "B" if room.visited or room.cleared else "?"
        elif not room.visited:
            mark = "?"
        elif room.cleared:
            mark = "·"
        else:
            mark = "!"

        canvas[y][x] = mark

    for pos in visible:
        x, y = cv(pos)
        east = add_pos(pos, DIRECTIONS["오른쪽"])
        south = add_pos(pos, DIRECTIONS["아래"])

        if east in visible:
            ex, _ = cv(east)
            for xx in range(x + 1, ex):
                canvas[y][xx] = "─"

        if south in visible:
            _, sy = cv(south)
            canvas[y + 1][x] = "│"

    return "\n".join("".join(row).rstrip() for row in canvas)



def player_embed(player: PlayerState, session: GameSession, title: str, colour=None):
    if session.is_tutorial and not title.startswith("0층"):
        title = f"0층 · 튜토리얼 · {title}"

    if session.is_tutorial:
        resource_line = f"코인 `{player.coins}` · 폭탄 `{player.bombs}`"
    else:
        resource_line = (
            f"코인 `{player.coins}` · 폭탄 `{player.bombs}`\n"
            f"남은 목숨 `{remaining_lives(player)}/{MAX_DAILY_LIVES}`"
        )

    embed = discord.Embed(title=title, colour=colour)
    embed.add_field(
        name="상태",
        value=(
            f"HP {hp_bar(player.hp, player.max_hp)} `{player.hp}/{player.max_hp}`\n"
            f"{resource_line}"
        ),
        inline=False,
    )
    embed.add_field(name="무기", value=player.weapon.label(), inline=False)
    embed.add_field(name="방패", value=player.armor.label(), inline=False)
    return embed


def exploration_embed(player, session, note=""):
    room = session.room()
    title = (
        f"0층 · 튜토리얼 · {room_name(room)}"
        if session.is_tutorial
        else f"{session.floor_number}층 · {room_name(room)}"
    )
    embed = player_embed(player, session, title)
    if note:
        embed.description = note

    embed.add_field(
        name="맵",
        value=(
            f"```text\n{map_ascii(session)}\n```\n"
            "`@` 현재 · `·` 클리어 · `?` 미탐색 · `B` 보스 · `S` 비밀방"
        ),
        inline=False,
    )

    around = []
    for direction in ("왼쪽", "위", "아래", "오른쪽"):
        target = add_pos(session.current, DIRECTIONS[direction])
        can_move = (
            target in session.rooms
            and not (
                target == session.secret_pos
                and not session.secret_revealed
            )
        )
        if can_move:
            around.append(f"{DIR_EMOJI[direction]} 문")

    if crack_here(session):
        around.append(f"{DIR_EMOJI[session.secret_direction]} **금이 간 벽**")

    if (
        session.boss_defeated
        and session.current == session.boss_pos
        and not session.is_tutorial
    ):
        around.append(f"🪜 **{session.floor_number + 1}층**")

    embed.add_field(
        name="주변",
        value="\n".join(around) if around else "막다른 방이다.",
        inline=False,
    )

    if session.boss_defeated:
        if session.is_tutorial:
            if not session.tutorial_replay and session.current == session.boss_pos:
                embed.set_footer(text="⚠️ 튜토리얼의 아이템은 사라져요!")
        elif session.current == session.boss_pos:
            embed.set_footer(
                text=f"{session.floor_number + 1}층으로 가거나 더 둘러볼 수 있다."
            )
        else:
            embed.set_footer(
                text=f"보스 방에서 {session.floor_number + 1}층으로 갈 수 있다."
            )
    return embed


def combat_embed(player, session, note="", enemy_art: Optional[str] = None):
    enemy = session.room().enemy
    assert enemy is not None

    color_icon = COLOR_MARK[enemy.color]
    enemy_title = (
        f"{color_icon} {enemy.color} 보스"
        if enemy.boss
        else f"{color_icon} {enemy.color} {enemy.shape}"
    )
    title = (
        f"0층 · 튜토리얼 · {enemy_title}"
        if session.is_tutorial
        else f"{session.floor_number}층 · {enemy_title}"
    )

    embed = discord.Embed(
        title=title,
        colour=EMBED_COLORS[enemy.color],
    )

    embed.add_field(
        name="적",
        value=colored_enemy_art(enemy, enemy_art),
        inline=False,
    )
    bleed_left = bleed_seconds_left(enemy)
    bleed_line = (
        f"\n🩸 출혈 `{enemy.bleed_stacks}` · `{bleed_left:.1f}초`"
        if bleed_left > 0
        else ""
    )
    critical_line = "\n⚠️ **CRITICAL!**" if enemy_is_critical(enemy) else ""

    embed.add_field(
        name="적 HP",
        value=(
            f"{enemy_hp_bar(enemy)} "
            f"`{max(0, enemy.hp)}/{enemy.max_hp}`\n"
            f"공격력 `{enemy.damage}`"
            f"{bleed_line}{critical_line}"
        ),
        inline=False,
    )

    embed.add_field(
        name="내 HP",
        value=(
            f"{hp_bar(player.hp, player.max_hp)} "
            f"`{player.hp}/{player.max_hp}`\n"
            f"코인 `{player.coins}` · 폭탄 `{player.bombs}`"
            + (
                ""
                if session.is_tutorial
                else f"\n남은 목숨 `{remaining_lives(player)}/{MAX_DAILY_LIVES}`"
            )
        ),
        inline=False,
    )
    embed.add_field(name="무기", value=player.weapon.label(), inline=False)
    embed.add_field(name="방패", value=player.armor.label(), inline=False)

    if note:
        embed.add_field(
            name="\u200b",
            value=note,
            inline=False,
        )

    return embed


async def edit_interaction_message(interaction, *, embed, view):
    if interaction.response.is_done():
        await interaction.edit_original_response(embed=embed, view=view)
    else:
        await interaction.response.edit_message(embed=embed, view=view)


async def animate_enemy_defeat(interaction, player, session, note):
    enemy = session.room().enemy
    if enemy is None:
        return


    session.hit_animating = True
    try:
        frames = (0, -1, 1, -1, 0)
        for index, offset in enumerate(frames):
            await edit_interaction_message(
                interaction,
                embed=combat_embed(
                    player,
                    session,
                    note,
                    enemy_art=shift_ascii_art(current_enemy_art(session, enemy), offset),
                ),
                view=None,
            )
            if index < len(frames) - 1:
                await asyncio.sleep(DEFEAT_SHAKE_FRAME_DELAY)
            else:

                await asyncio.sleep(DEFEAT_SHAKE_END_HOLD)
    finally:
        session.hit_animating = False


def shop_embed(player, session, note=""):
    room = session.room()
    embed = player_embed(player, session, "비밀 상점")
    if note:
        embed.description = note

    lines = []
    for i, gear in enumerate(room.shop_stock[:2], 1):
        price = gear_price(gear, session.floor_number)
        lines.append(f"{i}. `{price}코인` — {gear.label()}")
    price = bomb_price(session.floor_number)
    if room.bomb_stock > 0:
        lines.append(f"3. `{price}코인` — 폭탄 +1 · 재고 `{room.bomb_stock}`")
    else:
        lines.append("3. **SOLD OUT** — 폭탄")

    embed.add_field(
        name="판매 목록",
        value="\n".join(lines),
        inline=False,
    )
    return embed


def slot_cost(room, floor_number: int):
    return 10 * (room.slot_uses + 1) + max(0, floor_number - 1) * 2


def slot_embed(player, session, note=""):
    room = session.room()
    embed = player_embed(player, session, "🎰 슬롯머신")
    if note:
        embed.description = note
    embed.add_field(
        name="기계",
        value=(
            f"상태: **{'고장' if room.slot_broken else '작동 중'}**\n"
            f"사용 횟수: `{room.slot_uses}`\n"
            f"1회 비용: `{slot_cost(room, session.floor_number)}코인`"
        ),
        inline=False,
    )
    return embed


ATTACK_FLAVOR = [
    "아직인가...",
    "좀만 더 보자...",
    "가만히 있네...",
    "타이밍 잡기 어렵네...",
    "계속 지켜보자...",
]
ATTACK_FAKEOUT = [
    "**💥 앗!!! 멀쩡히 서 있다!!!**",
    "**💥 앗!!! 이쪽을 쳐다본다!!!**",
    "**💥 앗!!! 괜히 한 바퀴 돌았다!!!**",
    "**💥 앗!!! 아무 일도 없었다!!!**",
]
ATTACK_REAL = [
    "**💥 앗!!! 지금이야!!!**",
    "**💥 앗!!! 기회다!!!**",
]

DEFEND_FLAVOR = [
    "아직인가...",
    "언제 치려나...",
    "좀만 더 보자...",
    "가만히 있네...",
    "뭘 하려는 거지...",
    "계속 지켜보자...",
]
DEFEND_FAKEOUT = [
    "**💥 앗!!! 아무 일도 없다!!!**",
    "**💥 앗!!! 그냥 쳐다본다!!!**",
    "**💥 앗!!! 가만히 서 있다!!!**",
    "**💥 앗!!! 괜히 움직였다!!!**",
    "**💥 앗!!! 다시 멈춰 섰다!!!**",
    "**💥 앗!!! 그냥 지나간다!!!**",
]
DEFEND_REAL = [
    "**💥 앗!!! 공격한다!!!**",
    "**💥 앗!!! 지금 막아!!!**",
]


class OwnerView(discord.ui.View):
    def __init__(self, session: GameSession, timeout=300):
        super().__init__(timeout=timeout)
        self.session = session

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.user_id:
            await interaction.response.defer()
            return False
        return True


class ExploreView(OwnerView):
    def __init__(self, session):
        super().__init__(session)

        for direction in ("왼쪽", "위", "아래", "오른쪽"):
            target = add_pos(session.current, DIRECTIONS[direction])
            can_move = (
                target in session.rooms
                and not (
                    target == session.secret_pos
                    and not session.secret_revealed
                )
            )

            btn = discord.ui.Button(
                emoji=DIR_EMOJI[direction],
                style=discord.ButtonStyle.primary,
                disabled=not can_move,
                row=0,
            )

            async def callback(interaction, d=direction, t=target):
                await move_player(interaction, self.session, d, t)

            btn.callback = callback
            self.add_item(btn)

        if crack_here(session):
            btn = discord.ui.Button(
                label=f"{DIR_EMOJI[session.secret_direction]} 벽 파괴",
                emoji="💣",
                style=discord.ButtonStyle.danger,
            )

            async def crack_callback(interaction):
                await open_secret(interaction, self.session)

            btn.callback = crack_callback
            self.add_item(btn)

        room = session.room()
        if room.kind == "pot" and not room.cleared:
            btn = discord.ui.Button(
                label="항아리 깨기",
                emoji="🏺",
                style=discord.ButtonStyle.secondary,
            )

            async def pot_callback(interaction):
                await break_pot(interaction, self.session)

            btn.callback = pot_callback
            self.add_item(btn)

        if session.boss_defeated and session.current == session.boss_pos:
            if session.is_tutorial and session.tutorial_replay:
                btn = discord.ui.Button(
                    label="튜토리얼 나가기",
                    emoji="🪜",
                    style=discord.ButtonStyle.success,
                )

                async def leave_tutorial_callback(interaction):
                    await leave_tutorial(interaction, self.session)

                btn.callback = leave_tutorial_callback
                self.add_item(btn)
            else:
                btn = discord.ui.Button(
                    label=f"{session.floor_number + 1}층",
                    emoji="🪜",
                    style=discord.ButtonStyle.success,
                )

                async def climb_callback(interaction):
                    await climb_next_floor(interaction, self.session)

                btn.callback = climb_callback
                self.add_item(btn)


class BattleStartView(OwnerView):
    def __init__(self, session):
        super().__init__(session)
        btn = discord.ui.Button(
            label="전투 시작",
            emoji="⚔️",
            style=discord.ButtonStyle.danger,
        )

        async def callback(interaction):
            await start_battle(interaction, self.session)

        btn.callback = callback
        self.add_item(btn)


class CombatView(OwnerView):
    def __init__(self, session, kind):
        super().__init__(session)
        p = session_player(session)
        enemy = session.room().enemy

        if kind == "attack":
            attack = discord.ui.Button(
                emoji="⚔️",
                style=discord.ButtonStyle.danger,
            )

            async def attack_callback(interaction):
                await press_timing(interaction, self.session, "attack")

            attack.callback = attack_callback
            self.add_item(attack)

            bomb = discord.ui.Button(
                emoji="💣",
                style=discord.ButtonStyle.secondary,
                disabled=p.bombs <= 0,
            )

            async def bomb_callback(interaction):
                await combat_bomb(interaction, self.session)

            bomb.callback = bomb_callback
            self.add_item(bomb)

        else:
            shield = discord.ui.Button(
                emoji="🛡️",
                style=discord.ButtonStyle.success,
            )

            async def shield_callback(interaction):
                await press_timing(interaction, self.session, "defend")

            shield.callback = shield_callback
            self.add_item(shield)

        if enemy and not enemy.boss:
            run = discord.ui.Button(
                label="도주",
                style=discord.ButtonStyle.secondary,
            )

            async def run_callback(interaction):
                await try_run(interaction, self.session)

            run.callback = run_callback
            self.add_item(run)


class LootView(OwnerView):
    def __init__(self, session, gear):
        super().__init__(session)
        self.gear = gear

        equip = discord.ui.Button(
            label="장착",
            emoji="✅",
            style=discord.ButtonStyle.success,
        )
        skip = discord.ui.Button(
            label="버리기",
            emoji="🗑️",
            style=discord.ButtonStyle.secondary,
        )

        async def equip_callback(interaction):
            p = session_player(session)
            if gear.kind == "weapon":
                p.weapon = gear
            else:
                p.armor = gear
            save_session_player(session, p)
            await show_after_clear(
                interaction,
                session,
                f"**{gear.name}** 장착 완료.",
            )

        async def skip_callback(interaction):
            await show_after_clear(
                interaction,
                session,
                "새 장비를 버렸다.",
            )

        equip.callback = equip_callback
        skip.callback = skip_callback
        self.add_item(equip)
        self.add_item(skip)


class ShopView(OwnerView):
    def __init__(self, session):
        super().__init__(session)
        room = session.room()
        p = session_player(session)

        for index, gear in enumerate(room.shop_stock[:2]):
            price = gear_price(gear, session.floor_number)
            btn = discord.ui.Button(
                label=f"{index + 1}번 ({price})",
                style=discord.ButtonStyle.success,
                disabled=p.coins < price,
            )

            async def callback(interaction, idx=index, cost=price):
                await buy_gear(interaction, self.session, idx, cost)

            btn.callback = callback
            self.add_item(btn)

        price = bomb_price(session.floor_number)
        bomb = discord.ui.Button(
            label=f"{price}코인" if room.bomb_stock > 0 else "SOLD OUT",
            emoji="💣",
            style=discord.ButtonStyle.secondary,
            disabled=room.bomb_stock <= 0 or p.coins < price,
        )

        async def bomb_callback(interaction):
            await buy_bomb(interaction, self.session)

        bomb.callback = bomb_callback
        self.add_item(bomb)

        leave = discord.ui.Button(
            emoji="↩️",
            style=discord.ButtonStyle.primary,
        )

        async def leave_callback(interaction):
            p2 = session_player(session)
            await interaction.response.edit_message(
                embed=exploration_embed(p2, session, "상점을 나왔다."),
                view=ExploreView(session),
            )

        leave.callback = leave_callback
        self.add_item(leave)


class SlotView(OwnerView):
    def __init__(self, session):
        super().__init__(session)
        room = session.room()
        p = session_player(session)

        cost = slot_cost(room, session.floor_number)
        play = discord.ui.Button(
            label=f"{cost}코인",
            emoji="🎰",
            style=discord.ButtonStyle.success,
            disabled=room.slot_broken or p.coins < cost,
        )

        async def play_callback(interaction):
            await play_slot(interaction, self.session)

        play.callback = play_callback
        self.add_item(play)

        bomb = discord.ui.Button(
            emoji="💣",
            style=discord.ButtonStyle.danger,
            disabled=room.slot_broken or p.bombs < 1,
        )

        async def bomb_callback(interaction):
            await bomb_slot(interaction, self.session)

        bomb.callback = bomb_callback
        self.add_item(bomb)

        leave = discord.ui.Button(
            emoji="↩️",
            style=discord.ButtonStyle.primary,
        )

        async def leave_callback(interaction):
            p2 = session_player(session)
            await interaction.response.edit_message(
                embed=exploration_embed(p2, session, "슬롯머신 방을 나왔다."),
                view=ExploreView(session),
            )

        leave.callback = leave_callback
        self.add_item(leave)



def cancel_cue(session: GameSession):
    session.cue_token += 1
    session.cue_state = "idle"
    session.cue_kind = None
    session.cue_started = None
    task = session.cue_task
    session.cue_task = None
    if task and not task.done() and task is not asyncio.current_task():
        task.cancel()


def cancel_bleed(session: GameSession, *, clear=True):
    session.bleed_token += 1
    task = session.bleed_task
    session.bleed_task = None
    if task and not task.done() and task is not asyncio.current_task():
        task.cancel()

    if clear:
        enemy = session.room().enemy
        if enemy is not None:
            clear_bleed(enemy)


def schedule_bleed(interaction: discord.Interaction, session: GameSession):
    enemy = session.room().enemy
    if enemy is None or enemy.hp <= 0 or enemy.bleed_stacks <= 0:
        return

    if session.bleed_task and not session.bleed_task.done():
        return

    token = session.bleed_token
    room_pos = session.current
    session.bleed_task = asyncio.create_task(
        bleed_sequence(interaction, session, enemy, room_pos, token)
    )


async def bleed_sequence(interaction, session, enemy, room_pos, token):
    next_tick = time.monotonic() + BLEED_TICK_SECONDS

    try:
        while True:
            await asyncio.sleep(max(0.0, next_tick - time.monotonic()))

            if (
                session.bleed_token != token
                or session.ended
                or session.current != room_pos
                or session.room().enemy is not enemy
                or session.room().cleared
            ):
                return

            now = time.monotonic()
            if enemy.bleed_stacks <= 0 or enemy.hp <= 0:
                return
            if now > enemy.bleed_expires_at + 0.05:
                clear_bleed(enemy)
                return

            damage = enemy.bleed_stacks
            enemy.hp -= damage
            next_tick += BLEED_TICK_SECONDS

            if enemy.hp <= 0:
                enemy.hp = 0
                while session.hit_animating and not session.ended:
                    await asyncio.sleep(0.05)
                if session.ended or session.current != room_pos or session.room().cleared:
                    return
                await enemy_defeated(
                    interaction,
                    session,
                    f"🩸 **BLEED!** 적에게 **{damage} 피해!**",
                )
                return

            if time.monotonic() >= enemy.bleed_expires_at - 0.05:
                clear_bleed(enemy)
                return

    except asyncio.CancelledError:
        return
    finally:
        if session.bleed_task is asyncio.current_task():
            session.bleed_task = None


def schedule_cue(interaction: discord.Interaction, session: GameSession, kind: str):
    cancel_cue(session)
    session.phase = kind
    session.cue_kind = kind
    session.cue_state = "waiting"
    token = session.cue_token
    session.cue_task = asyncio.create_task(cue_sequence(interaction, session, kind, token))


async def cue_sequence(interaction, session, kind, token):
    enemy = session.room().enemy
    if enemy is None:
        return

    flavor = ATTACK_FLAVOR if kind == "attack" else DEFEND_FLAVOR
    fakeouts = ATTACK_FAKEOUT if kind == "attack" else DEFEND_FAKEOUT
    real_cues = ATTACK_REAL if kind == "attack" else DEFEND_REAL

    try:
        for _ in range(random.randint(1, 3)):
            await asyncio.sleep(random.uniform(0.65, 1.35))
            if session.cue_token != token or session.ended or session.phase != kind:
                return

            is_fake = random.random() < 0.48
            session.cue_state = "fake" if is_fake else "waiting"
            line = random.choice(fakeouts if is_fake else flavor)
            p = session_player(session)
            await interaction.edit_original_response(
                embed=combat_embed(
                    p,
                    session,
                    line,
                    enemy_art=advance_enemy_art(session, enemy),
                ),
                view=CombatView(session, kind),
            )

        spec = SHAPES[enemy.shape]
        low, high = spec["cue_delay"]
        await asyncio.sleep(random.uniform(max(0.45, low * 0.35), max(0.85, high * 0.45)))
        if session.cue_token != token or session.ended or session.phase != kind:
            return

        p = session_player(session)
        await interaction.edit_original_response(
            embed=combat_embed(
                p,
                session,
                random.choice(real_cues),
                enemy_art=advance_enemy_art(session, enemy),
            ),
            view=CombatView(session, kind),
        )
        session.cue_state = "real"
        session.cue_started = time.monotonic()

        perfect, good = timing_windows(p, enemy, kind)
        await asyncio.sleep(good + 0.45)
        if (
            session.cue_token == token
            and session.phase == kind
            and session.cue_state == "real"
        ):
            await timeout_timing(interaction, session, kind, token)
    except asyncio.CancelledError:
        return
    except discord.HTTPException:
        if session.cue_token == token:
            session.phase = "battle_ready"
            session.cue_state = "idle"


async def timeout_timing(interaction, session, kind, token):
    if session.cue_token != token:
        return

    session.cue_state = "idle"
    session.cue_kind = None
    session.cue_started = None
    p = session_player(session)
    enemy = session.room().enemy
    if enemy is None:
        return

    if kind == "attack":
        note = "**MISS!** 늦었다."
        session.phase = "defend"
        await interaction.edit_original_response(
            embed=combat_embed(p, session, note + "\n\n적이 이쪽을 노린다."),
            view=CombatView(session, "defend"),
        )
        schedule_cue(interaction, session, "defend")
        return

    damage = incoming_damage(p, enemy, "MISS")
    p.hp = max(0, p.hp - damage)
    save_session_player(session, p)
    note = f"**MISS!** 늦었다. **{damage} 피해**."

    if p.hp <= 0:
        await player_died_background(interaction, session, note)
        return

    session.phase = "attack"
    await interaction.edit_original_response(
        embed=combat_embed(p, session, note),
        view=CombatView(session, "attack"),
    )
    schedule_cue(interaction, session, "attack")


async def move_player(interaction, session, direction, target):
    if session.ended:
        await interaction.response.defer()
        return

    cancel_cue(session)
    session.previous = session.current
    session.current = target
    room = session.room()
    room.visited = True
    p = session_player(session)

    if room.kind in ("normal", "boss") and not room.cleared:
        session.phase = "battle_ready"
        encounter_note = f"**{room.enemy.color} {room.enemy.shape}**이(가) 나타났다!"
        await interaction.response.edit_message(
            embed=combat_embed(
                p,
                session,
                encounter_note,
            ),
            view=BattleStartView(session),
        )
        return

    if room.kind == "shop":
        await interaction.response.edit_message(
            embed=shop_embed(p, session),
            view=ShopView(session),
        )
        return

    if room.kind == "slot":
        await interaction.response.edit_message(
            embed=slot_embed(p, session),
            view=SlotView(session),
        )
        return

    if room.kind == "coin" and not room.cleared:
        reward_bonus = max(0, (session.floor_number - 1) // 2)
        amount = random.randint(2, 4) + reward_bonus
        p.coins += amount
        room.cleared = True
        save_session_player(session, p)
        session.phase = "explore"
        await interaction.response.edit_message(
            embed=exploration_embed(
                p,
                session,
                f"🪙 코인 **{amount}개**를 주웠다.",
            ),
            view=ExploreView(session),
        )
        return

    if room.kind == "empty" and not room.cleared:
        room.cleared = True
        session.phase = "explore"
        await interaction.response.edit_message(
            embed=exploration_embed(
                p,
                session,
                "아무것도 없다.",
            ),
            view=ExploreView(session),
        )
        return

    if room.kind == "pot" and not room.cleared:
        session.phase = "explore"
        await interaction.response.edit_message(
            embed=exploration_embed(
                p,
                session,
                "항아리가 있다.",
            ),
            view=ExploreView(session),
        )
        return

    session.phase = "explore"
    await interaction.response.edit_message(
        embed=exploration_embed(p, session),
        view=ExploreView(session),
    )


async def break_pot(interaction, session):
    room = session.room()
    if room.kind != "pot" or room.cleared:
        await interaction.response.defer()
        return

    p = session_player(session)
    room.cleared = True
    roll = random.random()

    if roll < 0.50:
        reward_bonus = max(0, (session.floor_number - 1) // 2)
        amount = random.randint(2, 5) + reward_bonus
        p.coins += amount
        save_session_player(session, p)
        note = f"🏺 항아리를 깼다! 코인 **{amount}개**가 나왔다."
    elif roll < 0.80:
        note = "🏺 항아리를 깼다. 아무것도 없었다."
    else:
        damage = random.randint(1, 3)
        p.hp = max(0, p.hp - damage)
        save_session_player(session, p)
        note = f"🏺 항아리를 깼다. **{damage} 피해**"

        if p.hp <= 0:
            await player_died(interaction, session, note)
            return

    await interaction.response.edit_message(
        embed=exploration_embed(p, session, note),
        view=ExploreView(session),
    )


async def open_secret(interaction, session):
    p = session_player(session)
    if p.bombs <= 0:
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, "폭탄이 없다."),
            view=ExploreView(session),
        )
        return

    p.bombs -= 1
    save_session_player(session, p)
    session.secret_revealed = True

    await interaction.response.edit_message(
        embed=exploration_embed(
            p,
            session,
            f"💣 {DIR_EMOJI[session.secret_direction]} **금이 간 벽을 부쉈다.**",
        ),
        view=ExploreView(session),
    )


async def start_battle(interaction, session):
    enemy = session.room().enemy
    if enemy is None or enemy.hp <= 0:
        p = session_player(session)
        session.phase = "explore"
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, "싸울 적이 없다."),
            view=ExploreView(session),
        )
        return
    if session.phase != "battle_ready":
        await interaction.response.defer()
        return

    p = session_player(session)
    session.phase = "attack"
    session.enemy_anim_frame = 0
    await interaction.response.edit_message(
        embed=combat_embed(
            p,
            session,
            "**전투 시작!**\n신호를 잘 보고 누르세요.",
        ),
        view=CombatView(session, "attack"),
    )
    schedule_cue(interaction, session, "attack")


async def press_timing(interaction, session, kind):
    if session.phase != kind or session.cue_kind != kind:
        await interaction.response.defer()
        return

    room = session.room()
    enemy = room.enemy
    if enemy is None or enemy.hp <= 0:
        await interaction.response.defer()
        return

    p = session_player(session)
    state = session.cue_state

    if state != "real" or session.cue_started is None:
        cancel_cue(session)
        bait = state == "fake"

        if kind == "attack":
            note = (
                "**MISS!** 페이크였다."
                if bait
                else "**MISS!** 너무 빨랐다."
            )
            session.phase = "defend"
            await interaction.response.edit_message(
                embed=combat_embed(p, session, note + "\n\n적이 반격한다."),
                view=CombatView(session, "defend"),
            )
            schedule_cue(interaction, session, "defend")
            return

        damage = incoming_damage(p, enemy, "MISS")
        p.hp = max(0, p.hp - damage)
        save_session_player(session, p)
        note = (
            f"**MISS!** 페이크였다. **{damage} 피해**."
            if bait
            else f"**MISS!** 너무 빨랐다. **{damage} 피해**."
        )
        if p.hp <= 0:
            await player_died(interaction, session, note)
            return

        session.phase = "attack"
        await interaction.response.edit_message(
            embed=combat_embed(p, session, note),
            view=CombatView(session, "attack"),
        )
        schedule_cue(interaction, session, "attack")
        return

    elapsed = time.monotonic() - session.cue_started
    perfect, good = timing_windows(p, enemy, kind)
    grade = timing_grade(elapsed, perfect, good)
    cancel_cue(session)

    if kind == "attack":
        damage = attack_damage(p, enemy, grade)
        enemy.hp -= damage

        if grade == "PERFECT":
            note = (
                f"💥 **SMAAAASH!!**\n"
                f"`{elapsed:.2f}초` — 적에게 **{damage} 피해!**"
            )
            if enemy.hp > 0:
                stacks = apply_bleed(enemy)
                schedule_bleed(interaction, session)
                note += f"\n🩸 출혈 **{stacks}** · {BLEED_DURATION_SECONDS:.0f}초"
        elif grade == "GOOD":
            note = f"⚔️ **HIT!** · `{elapsed:.2f}초` — 적에게 **{damage} 피해!**"
        else:
            note = f"**MISS!** · `{elapsed:.2f}초` — 공격이 빗나갔다."

        if enemy.hp <= 0:
            await enemy_defeated(interaction, session, note)
            return

        session.phase = "defend"
        final_note = note + "\n\n적이 반격한다."
        await edit_interaction_message(
            interaction,
            embed=combat_embed(p, session, final_note),
            view=CombatView(session, "defend"),
        )
        schedule_cue(interaction, session, "defend")
        return

    damage = incoming_damage(p, enemy, grade)
    p.hp = max(0, p.hp - damage)
    save_session_player(session, p)

    if grade == "PERFECT":
        counter = PERFECT_COUNTER_DAMAGE
        enemy.hp -= counter
        note = (
            f"🛡️ **PERFECT GUARD!!**\n"
            f"`{elapsed:.2f}초` — 피해 **0** · 반격 **{counter} 피해!**"
        )
    else:
        counter = 0
        if grade == "GOOD":
            note = f"🛡️ **BLOCK!** · `{elapsed:.2f}초` — 받은 피해 **{damage}**."
        else:
            note = f"**MISS!** · `{elapsed:.2f}초` — 받은 피해 **{damage}**."

    if p.hp <= 0:
        await player_died(interaction, session, note)
        return

    if enemy.hp <= 0:
        await enemy_defeated(interaction, session, note)
        return

    session.phase = "attack"
    await edit_interaction_message(
        interaction,
        embed=combat_embed(p, session, note),
        view=CombatView(session, "attack"),
    )
    schedule_cue(interaction, session, "attack")


async def combat_bomb(interaction, session):
    if session.phase != "attack":
        await interaction.response.defer()
        return

    p = session_player(session)
    enemy = session.room().enemy

    if enemy is None:
        await interaction.response.defer()
        return
    if p.bombs <= 0:
        cancel_cue(session)
        await interaction.response.edit_message(
            embed=combat_embed(p, session, "폭탄이 없다."),
            view=CombatView(session, "attack"),
        )
        schedule_cue(interaction, session, "attack")
        return

    cancel_cue(session)
    p.bombs -= 1
    save_session_player(session, p)

    damage = random.randint(*BOMB_DAMAGE)
    enemy.hp -= damage
    note = f"💣 **KABOOM!!** 적에게 **{damage} 피해!**"

    if enemy.hp <= 0:
        await enemy_defeated(interaction, session, note)
        return

    session.phase = "defend"
    final_note = note + "\n\n적이 반격한다."
    await edit_interaction_message(
        interaction,
        embed=combat_embed(p, session, final_note),
        view=CombatView(session, "defend"),
    )
    schedule_cue(interaction, session, "defend")


async def try_run(interaction, session):
    enemy = session.room().enemy
    if enemy is None or enemy.boss:
        await interaction.response.defer()
        return
    if session.phase not in ("attack", "defend"):
        await interaction.response.defer()
        return

    cancel_cue(session)
    p = session_player(session)

    if random.random() < RUN_SUCCESS_RATE:
        cancel_bleed(session, clear=True)
        enemy.hp = enemy.max_hp
        if session.previous is not None:
            session.current = session.previous
        session.phase = "explore"
        await interaction.response.edit_message(
            embed=exploration_embed(
                p,
                session,
                "**도주 성공!**",
            ),
            view=ExploreView(session),
        )
        return

    damage = incoming_damage(p, enemy, "MISS")
    p.hp = max(0, p.hp - damage)
    save_session_player(session, p)
    note = f"**도주 실패!** **{damage} 피해**"

    if p.hp <= 0:
        await player_died(interaction, session, note)
        return

    session.phase = "attack"
    await interaction.response.edit_message(
        embed=combat_embed(p, session, note),
        view=CombatView(session, "attack"),
    )
    schedule_cue(interaction, session, "attack")


async def enemy_defeated(interaction, session, combat_note):
    room = session.room()
    enemy = room.enemy
    assert enemy is not None
    if room.cleared:
        return


    room.cleared = True
    cancel_cue(session)
    cancel_bleed(session, clear=True)
    session.phase = "explore"

    p = session_player(session)
    await animate_enemy_defeat(interaction, p, session, combat_note)

    low, high = SHAPES[enemy.shape]["coin_drop"]
    reward_bonus = max(0, (session.floor_number - 1) // 2)
    coins = random.randint(low, high) + reward_bonus
    if enemy.boss:
        coins += random.randint(5, 9) + reward_bonus

    p.coins += coins

    bomb_gain = 1 if random.random() < (0.40 if enemy.boss else 0.25) else 0
    p.bombs += bomb_gain
    save_session_player(session, p)

    note = f"{combat_note}\n\n코인 **+{coins}**"
    if bomb_gain:
        note += " · 폭탄 **+1**"

    if enemy.boss:
        session.boss_defeated = True

    if enemy.boss or random.random() < 0.30:
        gear = generate_gear(
            random.choice(("weapon", "armor")),
            boss_drop=enemy.boss,
            floor_number=session.floor_number,
        )
        embed = player_embed(p, session, "전리품 발견", colour=EMBED_COLORS[enemy.color])
        embed.description = note
        embed.add_field(name="새 장비", value=gear.label(), inline=False)

        current = p.weapon if gear.kind == "weapon" else p.armor
        embed.add_field(name="현재 장비", value=current.label(), inline=False)

        await edit_interaction_message(
            interaction,
            embed=embed,
            view=LootView(session, gear),
        )
        return

    await show_after_clear(interaction, session, note)


async def show_after_clear(interaction, session, note):
    p = session_player(session)

    if session.boss_defeated and session.current == session.boss_pos:
        if not session.is_tutorial:
            note += (
                "\n\n**보스를 처치했다!** "
                f"🪜 **{session.floor_number + 1}층**으로 갈 수 있다."
            )

    await edit_interaction_message(
        interaction,
        embed=exploration_embed(p, session, note),
        view=ExploreView(session),
    )


def death_description(player: PlayerState, note: str) -> str:
    left = remaining_lives(player)
    if left <= 0:
        return (
            note
            + "\n\n**눈앞이 캄캄해졌다!**"
            + "\n오늘은 더 이상 플레이할 수 없다. 내일 다시 도전하자!"
            + "\n무기·방패·코인·폭탄은 그대로 유지된다."
            + "\n플레이테스트 중이라면 `/테스트리셋`을 사용할 수 있습니다."
        )
    return (
        note
        + "\n\n**눈앞이 캄캄해졌다!**"
        + f"\n남은 목숨 **{left}/{MAX_DAILY_LIVES}**"
        + "\n`/게임`으로 1층부터 다시 도전하자!"
    )


async def player_died(interaction, session, note):
    cancel_cue(session)
    cancel_bleed(session, clear=True)
    p = session_player(session)
    p.hp = 0
    session.ended = True

    if session.is_tutorial:
        embed = player_embed(p, session, "게임 오버")
        embed.description = note + "\n\n**눈앞이 캄캄해졌다!**"
        await interaction.response.edit_message(embed=embed, view=None)
        return

    p.last_day = today_key()
    p.status = "dead"
    p.floor_number = session.floor_number
    p.highest_floor = max(p.highest_floor, session.floor_number)
    p.lives_used += 1
    save_session_player(session, p)

    embed = player_embed(p, session, "게임 오버")
    embed.description = death_description(p, note)
    await interaction.response.edit_message(embed=embed, view=None)


async def player_died_background(interaction, session, note):
    cancel_cue(session)
    cancel_bleed(session, clear=True)
    p = session_player(session)
    p.hp = 0
    session.ended = True

    if session.is_tutorial:
        embed = player_embed(p, session, "게임 오버")
        embed.description = note + "\n\n**눈앞이 캄캄해졌다!**"
        await interaction.edit_original_response(embed=embed, view=None)
        return

    p.last_day = today_key()
    p.status = "dead"
    p.floor_number = session.floor_number
    p.highest_floor = max(p.highest_floor, session.floor_number)
    p.lives_used += 1
    save_session_player(session, p)

    embed = player_embed(p, session, "게임 오버")
    embed.description = death_description(p, note)
    await interaction.edit_original_response(embed=embed, view=None)


async def leave_tutorial(interaction, session):
    if not (
        session.is_tutorial
        and session.tutorial_replay
        and session.boss_defeated
        and session.current == session.boss_pos
    ):
        await interaction.response.defer()
        return

    cancel_cue(session)
    session.ended = True
    key = (session.guild_id, session.user_id)
    if tutorial_sessions.get(key) is session:
        tutorial_sessions.pop(key, None)

    p = session_player(session)
    embed = player_embed(p, session, "튜토리얼 완료")
    embed.description = (
        "**튜토리얼을 종료했다.**\n"
        "언제든 `/튜토리얼`로 다시 플레이할 수 있다.\n"
        "튜토리얼에서 얻은 아이템은 실제 게임에 반영되지 않는다."
    )
    await interaction.response.edit_message(embed=embed, view=None)


async def climb_next_floor(interaction, session):
    if not session.boss_defeated or session.current != session.boss_pos:
        p = session_player(session)
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, "아직 올라갈 수 없다."),
            view=ExploreView(session),
        )
        return

    if session.is_tutorial:
        if session.tutorial_replay:
            await leave_tutorial(interaction, session)
            return

        cancel_cue(session)
        session.ended = True
        key = (session.guild_id, session.user_id)
        tutorial_sessions.pop(key, None)

        p = db.get_player(session.guild_id, session.user_id)
        today = today_key()
        if p.last_day != today:
            p.lives_used = 0
        p.hp = p.max_hp
        p.last_day = today
        p.status = "playing"
        p.floor_number = 1
        p.highest_floor = max(p.highest_floor, 1)
        p.tutorial_completed = True
        db.save_player(p)

        old = sessions.pop(key, None)
        if old:
            cancel_cue(old)
        new_session = generate_floor(
            session.guild_id,
            session.user_id,
            today,
            1,
        )
        sessions[key] = new_session

        await interaction.response.edit_message(
            embed=exploration_embed(
                p,
                new_session,
                "**1층 시작!**",
            ),
            view=ExploreView(new_session),
        )
        return

    cancel_cue(session)
    p = session_player(session)
    p.floor_number = session.floor_number + 1
    p.highest_floor = max(p.highest_floor, p.floor_number)
    p.last_day = today_key()
    p.status = "playing"
    save_session_player(session, p)

    session.ended = True

    trivia = random.choice(FLOOR_TRIVIA)
    loading_steps = [
        (0, 0.75),
        (18, 0.90),
        (41, 1.00),
        (67, 0.85),
        (88, 0.70),
        (100, 0.50),
    ]

    def loading_embed(progress):
        filled = round(progress / 10)
        bar = "█" * filled + "░" * (10 - filled)
        return discord.Embed(
            description=(
                "**올라가는 중...**\n"
                f"`{bar}` {progress}%\n\n"
                f"🎮 {trivia}"
            )
        )

    first_progress, first_delay = loading_steps[0]
    await interaction.response.edit_message(
        embed=loading_embed(first_progress),
        view=None,
    )
    await asyncio.sleep(first_delay)

    for progress, delay in loading_steps[1:]:
        await interaction.edit_original_response(
            embed=loading_embed(progress),
            view=None,
        )
        await asyncio.sleep(delay)

    new_session = generate_floor(
        session.guild_id,
        session.user_id,
        session.day_key,
        p.floor_number,
    )
    sessions[(session.guild_id, session.user_id)] = new_session

    await interaction.edit_original_response(
        embed=exploration_embed(
            p,
            new_session,
            f"**{p.floor_number}층 시작!**",
        ),
        view=ExploreView(new_session),
    )


async def buy_gear(interaction, session, index, price):
    room = session.room()
    p = session_player(session)

    if index >= len(room.shop_stock):
        await interaction.response.edit_message(
            embed=shop_embed(p, session, "이미 팔렸다."),
            view=ShopView(session),
        )
        return

    if p.coins < price:
        await interaction.response.edit_message(
            embed=shop_embed(p, session, "코인이 부족하다."),
            view=ShopView(session),
        )
        return

    gear = room.shop_stock.pop(index)
    p.coins -= price

    if gear.kind == "weapon":
        p.weapon = gear
    else:
        p.armor = gear

    save_session_player(session, p)

    await interaction.response.edit_message(
        embed=shop_embed(
            p,
            session,
            f"**{gear.name}** 구입 및 장착 완료.",
        ),
        view=ShopView(session),
    )


async def buy_bomb(interaction, session):
    room = session.room()
    p = session_player(session)

    if room.bomb_stock <= 0:
        await interaction.response.edit_message(
            embed=shop_embed(p, session, "SOLD OUT"),
            view=ShopView(session),
        )
        return

    price = bomb_price(session.floor_number)
    if p.coins < price:
        await interaction.response.edit_message(
            embed=shop_embed(p, session, "코인이 부족하다."),
            view=ShopView(session),
        )
        return

    p.coins -= price
    p.bombs += 1
    room.bomb_stock -= 1
    save_session_player(session, p)

    note = (
        "폭탄 **1개**를 구입했다."
        if room.bomb_stock > 0
        else "폭탄 **1개**를 구입했다. **SOLD OUT**"
    )

    await interaction.response.edit_message(
        embed=shop_embed(p, session, note),
        view=ShopView(session),
    )


async def play_slot(interaction, session):
    room = session.room()
    p = session_player(session)

    if room.slot_broken:
        await interaction.response.edit_message(
            embed=slot_embed(p, session, "이미 고장 난 기계다."),
            view=SlotView(session),
        )
        return

    cost = slot_cost(room, session.floor_number)
    if p.coins < cost:
        await interaction.response.edit_message(
            embed=slot_embed(p, session, "코인이 부족하다."),
            view=SlotView(session),
        )
        return

    p.coins -= cost
    room.slot_uses += 1

    roll = random.random()
    reward_bonus = max(0, (session.floor_number - 1) // 2)

    if roll < 0.45:
        note = "아무것도 안 나왔다."
    elif roll < 0.68:
        gain = random.randint(2, 4) + reward_bonus
        p.coins += gain
        note = f"코인 **+{gain}**"
    elif roll < 0.80:
        p.bombs += 1
        note = "폭탄 **+1**"
    elif roll < 0.91:
        heal = random.randint(3, 6)
        before = p.hp
        p.hp = min(p.max_hp, p.hp + heal)
        note = f"HP **+{p.hp - before}**"
    else:
        gain = random.randint(6, 10) + reward_bonus * 2
        p.coins += gain
        note = f"잭팟! 코인 **+{gain}**"

    break_rates = [0.05, 0.10, 0.20, 0.35, 0.55, 0.75]
    break_rate = break_rates[min(room.slot_uses - 1, len(break_rates) - 1)]

    if random.random() < break_rate:
        room.slot_broken = True
        note += "\n\n**철컥.** 슬롯머신이 멈췄다."

    save_session_player(session, p)

    await interaction.response.edit_message(
        embed=slot_embed(p, session, note),
        view=SlotView(session),
    )


async def bomb_slot(interaction, session):
    room = session.room()
    p = session_player(session)

    if room.slot_broken:
        await interaction.response.edit_message(
            embed=slot_embed(p, session, "이미 고장 난 기계다."),
            view=SlotView(session),
        )
        return

    if p.bombs < 1:
        await interaction.response.edit_message(
            embed=slot_embed(p, session, "폭탄이 없다."),
            view=SlotView(session),
        )
        return

    p.bombs -= 1
    room.slot_broken = True

    reward_bonus = max(0, (session.floor_number - 1) // 2)
    gain = random.randint(27, 33) + reward_bonus * 2
    p.coins += gain
    save_session_player(session, p)

    await interaction.response.edit_message(
        embed=slot_embed(
            p,
            session,
            f"💣 슬롯머신 폭파!\n코인 **+{gain}**",
        ),
        view=SlotView(session),
    )


SHEET_HEADERS = [
    "이름",
    "사용자 ID",
    "현재 층",
    "최고 층",
    "남은 목숨",
    "코인",
    "무기",
    "공격력",
    "방패",
    "방어력",
    "폭탄",
    "HP",
    "상태",
    "마지막 플레이",
]


def worksheet_title_for_guild(guild: discord.Guild) -> str:
    forbidden = set("[]:*?/\\")
    safe_name = "".join("_" if ch in forbidden else ch for ch in guild.name).strip()
    base = f"{GOOGLE_SHEET_WORKSHEET} - {safe_name} ({guild.id})"
    return base[:100]


def sync_players_to_google_sheet(rows: list[list[object]], worksheet_title: str):
    if not GOOGLE_SHEET_ID:
        raise RuntimeError("GOOGLE_SHEET_ID가 설정되어 있지 않습니다.")

    try:
        import gspread
    except ImportError as exc:
        raise RuntimeError("gspread가 설치되어 있지 않습니다. `pip install gspread`가 필요합니다.") from exc

    if GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            credentials = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON 형식이 올바르지 않습니다.") from exc
        client = gspread.service_account_from_dict(credentials)
    elif GOOGLE_SERVICE_ACCOUNT_FILE:
        client = gspread.service_account(filename=GOOGLE_SERVICE_ACCOUNT_FILE)
    else:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON 또는 GOOGLE_SERVICE_ACCOUNT_FILE이 필요합니다."
        )

    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(worksheet_title)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_title,
            rows=max(100, len(rows) + 20),
            cols=len(SHEET_HEADERS),
        )

    existing = worksheet.get_all_values()
    existing_by_user_id: dict[str, int] = {}
    for row_number, row in enumerate(existing[1:], start=2):
        if len(row) >= 2 and row[1].strip():
            existing_by_user_id[row[1].strip()] = row_number

    updates = [
        {
            "range": "A1:N1",
            "values": [SHEET_HEADERS],
        }
    ]

    next_row = max(2, len(existing) + 1)
    for row in rows:
        user_id = str(row[1])
        row_number = existing_by_user_id.get(user_id)
        if row_number is None:
            row_number = next_row
            next_row += 1
        updates.append(
            {
                "range": f"A{row_number}:N{row_number}",
                "values": [row],
            }
        )

    worksheet.batch_update(updates, value_input_option="RAW")
    worksheet.freeze(rows=1)
    return spreadsheet.url, len(rows)


intents = discord.Intents.default()


class ShapeGameBot(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync()


bot = ShapeGameBot(command_prefix="!", intents=intents)


@bot.tree.command(name="게임", description="오늘의 탐색을 시작하거나 이어서 플레이합니다.")
async def game(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    guild_id = interaction.guild_id
    user_id = interaction.user.id
    key = (guild_id, user_id)
    today = today_key()
    p = db.get_player(guild_id, user_id)


    if not p.tutorial_completed:
        old_tutorial = tutorial_sessions.get(key)
        if (
            old_tutorial
            and not old_tutorial.ended
            and not old_tutorial.tutorial_replay
        ):
            tp = session_player(old_tutorial)
            room = old_tutorial.room()
            if room.kind in ("normal", "boss") and not room.cleared:
                cancel_cue(old_tutorial)
                old_tutorial.phase = "battle_ready"
                await interaction.response.send_message(
                    embed=combat_embed(
                        tp,
                        old_tutorial,
                        "",
                    ),
                    view=BattleStartView(old_tutorial),
                    ephemeral=True,
                )
            elif room.kind == "shop":
                await interaction.response.send_message(
                    embed=shop_embed(
                        tp,
                        old_tutorial,
                        "",
                    ),
                    view=ShopView(old_tutorial),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=exploration_embed(
                        tp,
                        old_tutorial,
                        "",
                    ),
                    view=ExploreView(old_tutorial),
                    ephemeral=True,
                )
            return

        if old_tutorial:
            cancel_cue(old_tutorial)
            old_tutorial.ended = True

        tutorial = generate_tutorial(guild_id, user_id, replay=False)
        tutorial_sessions[key] = tutorial
        await interaction.response.send_message(
            embed=exploration_embed(
                session_player(tutorial),
                tutorial,
                tutorial_start_note(False),
            ),
            view=ExploreView(tutorial),
            ephemeral=True,
        )
        return


    if p.last_day != today:
        old = sessions.pop(key, None)
        if old:
            cancel_cue(old)
            old.ended = True

        p.hp = p.max_hp
        p.last_day = today
        p.status = "playing"
        p.floor_number = 1
        p.lives_used = 0
        p.highest_floor = max(p.highest_floor, 1)
        db.save_player(p)

        session = generate_floor(guild_id, user_id, today, 1)
        sessions[key] = session

        await interaction.response.send_message(
            embed=exploration_embed(
                p,
                session,
                f"**1층 시작!**\n남은 목숨 `{MAX_DAILY_LIVES}/{MAX_DAILY_LIVES}`",
            ),
            view=ExploreView(session),
            ephemeral=True,
        )
        return

    if p.status == "dead":
        if p.lives_used >= MAX_DAILY_LIVES:
            await interaction.response.send_message(
                "오늘은 더 이상 플레이할 수 없다. 내일 다시 도전하자!\n"
                "무기·방패·코인·폭탄은 그대로 유지된다.\n"
                "플레이테스트 중이라면 `/테스트리셋`을 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        old = sessions.pop(key, None)
        if old:
            cancel_cue(old)
            old.ended = True

        p.hp = p.max_hp
        p.status = "playing"
        p.floor_number = 1
        db.save_player(p)

        session = generate_floor(guild_id, user_id, today, 1)
        sessions[key] = session
        await interaction.response.send_message(
            embed=exploration_embed(
                p,
                session,
                (
                    "**다시 도전!**\n"
                    f"남은 목숨 `{remaining_lives(p)}/{MAX_DAILY_LIVES}` · 1층부터 시작한다."
                ),
            ),
            view=ExploreView(session),
            ephemeral=True,
        )
        return

    if p.status != "playing":
        p.status = "playing"
        db.save_player(p)

    old = sessions.get(key)
    if old and not old.ended and old.day_key == today:
        room = old.room()

        if room.kind in ("normal", "boss") and not room.cleared:
            cancel_cue(old)
            old.phase = "battle_ready"
            await interaction.response.send_message(
                embed=combat_embed(p, old, "전투 화면으로 돌아왔다. 다시 전투를 시작하자!"),
                view=BattleStartView(old),
                ephemeral=True,
            )
        elif room.kind == "shop":
            await interaction.response.send_message(
                embed=shop_embed(p, old),
                view=ShopView(old),
                ephemeral=True,
            )
        elif room.kind == "slot":
            await interaction.response.send_message(
                embed=slot_embed(p, old),
                view=SlotView(old),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=exploration_embed(p, old, "진행 중인 층으로 돌아왔다."),
                view=ExploreView(old),
                ephemeral=True,
            )
        return


    p.floor_number = max(1, p.floor_number)
    session = generate_floor(guild_id, user_id, today, p.floor_number)
    sessions[key] = session

    await interaction.response.send_message(
        embed=exploration_embed(
            p,
            session,
            f"**{p.floor_number}층 탐색을 재개했다!**",
        ),
        view=ExploreView(session),
        ephemeral=True,
    )


@bot.tree.command(name="튜토리얼", description="튜토리얼")
async def tutorial(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    key = (interaction.guild_id, interaction.user.id)
    old = tutorial_sessions.pop(key, None)
    if old:
        cancel_cue(old)
        old.ended = True

    session = generate_tutorial(
        interaction.guild_id,
        interaction.user.id,
        replay=True,
    )
    tutorial_sessions[key] = session

    await interaction.response.send_message(
        embed=exploration_embed(
            session_player(session),
            session,
            tutorial_start_note(True),
        ),
        view=ExploreView(session),
        ephemeral=True,
    )


@bot.tree.command(name="상태", description="현재 장비와 자원을 확인합니다.")
async def status(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    p = db.get_player(interaction.guild_id, interaction.user.id)
    lives = (
        MAX_DAILY_LIVES
        if p.last_day != today_key()
        else remaining_lives(p)
    )

    embed = discord.Embed(title=f"{interaction.user.display_name} — 상태")
    embed.add_field(
        name="자원",
        value=(
            f"HP `{p.hp}/{p.max_hp}`\n"
            f"코인 `{p.coins}` · 폭탄 `{p.bombs}`\n"
            f"남은 목숨 `{lives}/{MAX_DAILY_LIVES}`"
        ),
        inline=False,
    )
    embed.add_field(name="무기", value=p.weapon.label(), inline=False)
    embed.add_field(name="방패", value=p.armor.label(), inline=False)
    embed.add_field(
        name="진행",
        value=(
            f"현재 `{p.floor_number}층` · 최고 `{p.highest_floor}층`\n"
            f"`{p.last_day or '미시작'}` · `{p.status}`"
        ),
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="점수판", description="순위를 확인합니다.")
async def leaderboard(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    rows = db.leaderboard(interaction.guild_id)
    lines = []

    for rank, (user_id, floor_number, coins) in enumerate(rows, 1):
        member = interaction.guild.get_member(user_id)
        name = member.display_name if member else f"<@{user_id}>"
        lines.append(
            f"`{rank:>2}.` {name} — **{floor_number}층** · `{coins} 코인`"
        )

    embed = discord.Embed(
        title="진행 순위",
        description="\n".join(lines) if lines else "아직 기록이 없다.",
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="주기", description="플레이어에게 아이템을 지급합니다.")
@discord.app_commands.describe(
    대상="아이템을 받을 플레이어",
    아이템="지급할 아이템",
    수량="코인 또는 폭탄의 수량",
    위력="무기 또는 방패의 위력",
)
@discord.app_commands.choices(
    아이템=[
        discord.app_commands.Choice(name="코인", value="coin"),
        discord.app_commands.Choice(name="폭탄", value="bomb"),
        discord.app_commands.Choice(name="무기", value="weapon"),
        discord.app_commands.Choice(name="방패", value="armor"),
    ]
)
async def give_item(
    interaction: discord.Interaction,
    대상: discord.Member,
    아이템: str,
    수량: int = 1,
    위력: Optional[int] = None,
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    is_owner = interaction.guild.owner_id == interaction.user.id
    is_admin = interaction.user.guild_permissions.administrator
    if not (is_owner or is_admin):
        await interaction.response.send_message(
            "서버 주인 또는 관리자만 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    if 수량 < 1:
        await interaction.response.send_message(
            "수량은 1 이상이어야 합니다.",
            ephemeral=True,
        )
        return

    p = db.get_player(interaction.guild_id, 대상.id)

    if 아이템 == "coin":
        p.coins += 수량
        result = f"코인 **{수량}개**"
    elif 아이템 == "bomb":
        p.bombs += 수량
        result = f"폭탄 **{수량}개**"
    elif 아이템 in ("weapon", "armor"):
        if 수량 != 1:
            await interaction.response.send_message(
                "무기와 방패는 한 번에 1개만 지급할 수 있습니다.",
                ephemeral=True,
            )
            return
        if 위력 is not None and 위력 < 0:
            await interaction.response.send_message(
                "위력은 0 이상이어야 합니다.",
                ephemeral=True,
            )
            return

        gear = generate_gear(
            아이템,
            floor_number=max(1, p.floor_number),
        )
        if 위력 is not None:
            gear.power = 위력

        if 아이템 == "weapon":
            p.weapon = gear
            result = f"무기 **{gear.name}** (공격 {gear.power})"
        else:
            p.armor = gear
            result = f"방패 **{gear.name}** (방어 {gear.power})"
    else:
        await interaction.response.send_message(
            "알 수 없는 아이템입니다.",
            ephemeral=True,
        )
        return

    db.save_player(p)
    await interaction.response.send_message(
        f"{대상.mention}에게 {result}을(를) 지급했습니다.",
        ephemeral=True,
    )


@bot.tree.command(
    name="시트업데이트",
    description="모든 플레이어의 진행 상황을 구글 시트에 업데이트합니다.",
)
async def sheet_update(interaction: discord.Interaction):
    if interaction.guild_id is None or interaction.guild is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    players = db.all_players(interaction.guild_id)
    sheet_rows = []

    for p in players:
        member = interaction.guild.get_member(p.user_id)
        if member is not None:
            name = member.display_name
        else:
            try:
                user = await bot.fetch_user(p.user_id)
                name = user.global_name or user.name
            except discord.HTTPException:
                name = str(p.user_id)

        lives = (
            MAX_DAILY_LIVES
            if p.last_day != today_key()
            else remaining_lives(p)
        )
        sheet_rows.append(
            [
                name,
                str(p.user_id),
                p.floor_number,
                p.highest_floor,
                lives,
                p.coins,
                p.weapon.name,
                p.weapon.power,
                p.armor.name,
                p.armor.power,
                p.bombs,
                f"{p.hp}/{p.max_hp}",
                p.status,
                p.last_day or "미시작",
            ]
        )

    worksheet_title = worksheet_title_for_guild(interaction.guild)
    try:
        sheet_url, count = await asyncio.to_thread(
            sync_players_to_google_sheet,
            sheet_rows,
            worksheet_title,
        )
    except Exception as exc:
        await interaction.edit_original_response(
            content=f"시트 업데이트에 실패했습니다.\n`{type(exc).__name__}: {exc}`"
        )
        return

    await interaction.edit_original_response(
        content=(
            f"구글 시트를 업데이트했습니다. **{count}명**의 진행 상황을 반영했습니다.\n"
            f"탭: `{worksheet_title}`\n"
            f"{sheet_url}"
        )
    )


@bot.tree.command(
    name="테스트리셋",
    description="플레이테스트용: 오늘의 플레이 제한과 현재 진행을 초기화합니다.",
)
async def test_reset(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    key = (interaction.guild_id, interaction.user.id)

    old = sessions.pop(key, None)
    if old:
        cancel_cue(old)
        old.ended = True

    old_tutorial = tutorial_sessions.pop(key, None)
    if old_tutorial:
        cancel_cue(old_tutorial)
        old_tutorial.ended = True

    db.test_reset(interaction.guild_id, interaction.user.id)

    await interaction.response.send_message(
        "테스트 상태를 초기화했습니다. `/게임`으로 다시 시작할 수 있습니다.\n"
        "**무기·방패·코인·폭탄은 유지됩니다.**",
        ephemeral=True,
    )


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN이 없습니다. `.env.example`을 복사해 `.env`를 만든 뒤 토큰을 넣어 주세요."
        )

    bot.run(TOKEN)
