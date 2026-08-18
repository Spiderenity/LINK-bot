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
MAGIC_WEAPON_CHAIN = "weapon_chain"
MAGIC_WEAPON_HURT = "weapon_hurt"
MAGIC_WEAPON_BLEED = "weapon_bleed"
MAGIC_SHIELD_COUNTER = "shield_counter"
MAGIC_SHIELD_GUARD = "shield_guard"
MAGIC_HEAD_POT_GUARD = "head_pot_guard"
MAGIC_HEAD_BOSS_HEAL = "head_boss_heal"
MAGIC_RING_BLEED = "ring_bleed"
MAGIC_RING_BOMB = "ring_bomb"
MAGIC_NAMES = {
    MAGIC_WEAPON_CHAIN: "제비의 세검",
    MAGIC_WEAPON_HURT: "멧돼지의 칼",
    MAGIC_WEAPON_BLEED: "사냥개의 단검",
    MAGIC_SHIELD_COUNTER: "가시 방패",
    MAGIC_SHIELD_GUARD: "검은 거울",
    MAGIC_HEAD_POT_GUARD: "도굴꾼의 두건",
    MAGIC_HEAD_BOSS_HEAL: "붉은 월계관",
    MAGIC_RING_BLEED: "혈석 반지",
    MAGIC_RING_BOMB: "화약 반지",
}
MAGIC_EFFECTS = {
    MAGIC_WEAPON_CHAIN: "공격을 계속 명중시키면 위력이 오른다.",
    MAGIC_WEAPON_HURT: "상처를 입으면 공격의 위력이 오른다.",
    MAGIC_WEAPON_BLEED: "출혈 중인 적에게 주는 피해를 늘린다.",
    MAGIC_SHIELD_COUNTER: "완벽한 방어의 위력을 높인다.",
    MAGIC_SHIELD_GUARD: "때때로 공격을 흘려낸다.",
    MAGIC_HEAD_POT_GUARD: "항아리의 위험으로부터 몸을 지킨다.",
    MAGIC_HEAD_BOSS_HEAL: "강적을 쓰러뜨리면 생기를 얻는다.",
    MAGIC_RING_BLEED: "출혈 피해량을 늘린다.",
    MAGIC_RING_BOMB: "폭탄의 위력을 높인다.",
}
MAGIC_KINDS = {
    MAGIC_WEAPON_CHAIN: "weapon",
    MAGIC_WEAPON_HURT: "weapon",
    MAGIC_WEAPON_BLEED: "weapon",
    MAGIC_SHIELD_COUNTER: "shield",
    MAGIC_SHIELD_GUARD: "shield",
    MAGIC_HEAD_POT_GUARD: "head",
    MAGIC_HEAD_BOSS_HEAL: "head",
    MAGIC_RING_BLEED: "ring",
    MAGIC_RING_BOMB: "ring",
}
MAGIC_POOL = tuple(MAGIC_KINDS)
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
        """░░░░░░░░░░░░░░░░
░░░░░░▄██▄░░░░░░
░░░░▄█▀██▀█▄░░░░
░░░░▀█▀██▀█▀░░░░
░░░░▀▄░░░░▄▀░░░░
░░░░░░░░░░░░░░░░""",
        """░░░░░░░░░░░░░░░░
░░░░░░▄██▄░░░░░░
░░░░▄█▀██▀█▄░░░░
░░░░▀▀█▀▀█▀▀░░░░
░░░░▄▀▄▀▀▄▀▄░░░░
░░░░░░░░░░░░░░░░""",
    ),
    "크랩": (
        """░░░░░░░░░░░░░░░░░
░░░░░▀▄░░░▄▀░░░░░
░░░░▄█▀███▀█▄░░░░
░░░█▀███████▀█░░░
░░░▀░▀▄▄░▄▄▀░▀░░░
░░░░░░░░░░░░░░░░░""",
        """░░░░░░░░░░░░░░░░░
░░░▄░▀▄░░░▄▀░▄░░░
░░░█▄█▀███▀█▄█░░░
░░░▀█████████▀░░░
░░░░▄▀░░░░░▀▄░░░░
░░░░░░░░░░░░░░░░░""",
    ),
    "옥토퍼스": (
        """░░░░░░░░░░░░░░░░░░
░░░░▄▄▄████▄▄▄░░░░
░░░███▀▀██▀▀███░░░
░░░▀▀███▀▀███▀▀░░░
░░░░▀█▄░▀▀░▄█▀░░░░
░░░░░░░░░░░░░░░░░░""",
        """░░░░░░░░░░░░░░░░░░
░░░░▄▄▄████▄▄▄░░░░
░░░███▀▀██▀▀███░░░
░░░▀▀▀██▀▀██▀▀▀░░░
░░░▄▄▀▀░▀▀░▀▀▄▄░░░
░░░░░░░░░░░░░░░░░░""",
    ),
    "보스": (
        """░░░░░░░░░░░░░░░░░░
░░░░▄▄██████▄▄░░░░
░░▄████████████▄░░
░▀▀███▀▀██▀▀███▀▀░
░░░░▀░░░░░░░░▀░░░░
░░░░░░░░░░░░░░░░░░""",
    ),
}

ASCII_ART = {shape: frames[0] for shape, frames in ENEMY_ART_FRAMES.items()}


@dataclass
class Gear:
    kind: str
    name: str
    power: int
    affinity: Dict[str, int]
    hp_bonus: int = 0
    magic: Optional[str] = None

    def display_name(self) -> str:
        return MAGIC_NAMES.get(self.magic, self.name) if self.magic else self.name

    def label(self) -> str:
        superscript = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
        pips = " ".join(
            f"{COLOR_MARK[color]}{str(self.affinity.get(color, 0)).translate(superscript)}"
            for color in COLORS
        )
        if self.kind == "weapon":
            stats = f"⚔️ {self.power} · {pips}"
        elif self.kind == "ring":
            stats = f"⚔️ +{self.power} · {pips}"
        elif self.kind == "shield":
            stats = f"🛡️ {self.power} · ❤️ +{self.hp_bonus} · {pips}"
        else:
            stats = f"🛡️ {self.power} · ❤️ +{self.hp_bonus} · {pips}"
        if self.magic:
            effect = MAGIC_EFFECTS.get(self.magic, self.magic)
            return f"{self.display_name()} | {stats}\n✨ {effect}"
        return f"{self.name} | {stats}"

    def to_json(self) -> str:
        return json.dumps(
            {
                "kind": self.kind,
                "name": self.name,
                "power": self.power,
                "affinity": self.affinity,
                "hp_bonus": self.hp_bonus,
                "magic": self.magic,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def from_json(raw: str) -> "Gear":
        d = json.loads(raw)
        return Gear(
            d["kind"],
            d["name"],
            d["power"],
            d["affinity"],
            d.get("hp_bonus", 0),
            d.get("magic"),
        )


def empty_affinity() -> Dict[str, int]:
    return {color: 0 for color in COLORS}


def split_affinity(source: Dict[str, int], points: int) -> tuple[Dict[str, int], Dict[str, int]]:
    main = {color: max(0, int(source.get(color, 0))) for color in COLORS}
    split = empty_affinity()
    remaining = max(0, points)
    while remaining > 0:
        choices = [color for color in COLORS if main[color] > 0]
        if not choices:
            break
        color = max(choices, key=lambda c: (main[c], -COLORS.index(c)))
        main[color] -= 1
        split[color] += 1
        remaining -= 1
    return main, split


def split_legacy_weapon(old: Gear) -> tuple[Gear, Gear]:
    ring_power = min(3, max(1, old.power // 4)) if old.power >= 2 else 0
    total_affinity = sum(max(0, old.affinity.get(color, 0)) for color in COLORS)
    weapon_affinity, ring_affinity = split_affinity(old.affinity, 1 if total_affinity >= 2 else 0)
    weapon = Gear("weapon", old.name, max(1, old.power - ring_power), weapon_affinity)
    ring = Gear("ring", f"{old.name} 조각 반지", ring_power, ring_affinity)
    return weapon, ring


def split_legacy_armor(old: Gear) -> tuple[Gear, Gear]:
    head_power = min(2, max(0, old.power // 4))
    total_affinity = sum(max(0, old.affinity.get(color, 0)) for color in COLORS)
    shield_affinity, head_affinity = split_affinity(old.affinity, 1 if total_affinity >= 2 else 0)
    shield = Gear("shield", old.name, max(0, old.power - head_power), shield_affinity, 0)
    head = Gear("head", "개조 안전모", head_power, head_affinity, 0)
    return shield, head


START_WEAPON = Gear(
    "weapon", "유리 파편", 4, {"시안": 1, "마젠타": 0, "옐로": 0}
)
START_RING = Gear(
    "ring", "철사 반지", 1, {"시안": 0, "마젠타": 0, "옐로": 0}
)
START_SHIELD = Gear(
    "shield", "화물 상자 뚜껑", 1, {"시안": 0, "마젠타": 1, "옐로": 0}, 0
)
START_HEAD = Gear(
    "head", "낡은 안전모", 0, {"시안": 0, "마젠타": 0, "옐로": 0}, 0
)
START_ARMOR = START_SHIELD


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
    ring: Optional[Gear]
    shield: Gear
    head: Optional[Gear]
    last_day: str
    status: str
    floor_number: int
    highest_floor: int
    checkpoint_floor: int
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
    run_failed: bool = False
    attack_chain: int = 0
    hurt_this_battle: bool = False
    magic_shop_stock: list[Gear] = field(default_factory=list)
    magic_shop_used: bool = False
    pending_loot: Optional[Gear] = None
    pending_loot_note: str = ""
    pending_loot_footer: str = ""

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
                    shield_json TEXT,
                    head_json TEXT,
                    ring_json TEXT,
                    legacy_weapon_json TEXT,
                    equipment_version INTEGER NOT NULL DEFAULT 0,
                    last_day TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'ready',
                    floor_number INTEGER NOT NULL DEFAULT 1,
                    highest_floor INTEGER NOT NULL DEFAULT 1,
                    checkpoint_floor INTEGER NOT NULL DEFAULT 0,
                    lives_used INTEGER NOT NULL DEFAULT 0,
                    tutorial_completed INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_runs (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    day_key TEXT NOT NULL,
                    floor_number INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            columns = {
                row[1] for row in con.execute("PRAGMA table_info(players)").fetchall()
            }
            additions = {
                "floor_number": "INTEGER NOT NULL DEFAULT 1",
                "highest_floor": "INTEGER NOT NULL DEFAULT 1",
                "checkpoint_floor": "INTEGER NOT NULL DEFAULT 0",
                "lives_used": "INTEGER NOT NULL DEFAULT 0",
                "tutorial_completed": "INTEGER NOT NULL DEFAULT 1",
                "shield_json": "TEXT",
                "head_json": "TEXT",
                "ring_json": "TEXT",
                "legacy_weapon_json": "TEXT",
                "equipment_version": "INTEGER NOT NULL DEFAULT 0",
            }
            for name, definition in additions.items():
                if name not in columns:
                    con.execute(f"ALTER TABLE players ADD COLUMN {name} {definition}")
            if "checkpoint_floor" not in columns:
                con.execute(
                    "UPDATE players SET checkpoint_floor = CAST((MAX(highest_floor, 1) - 1) / 5 AS INTEGER) * 5"
                )
            rows = con.execute(
                """
                SELECT guild_id, user_id, weapon_json, armor_json,
                       shield_json, head_json, ring_json, equipment_version, legacy_weapon_json
                FROM players
                WHERE equipment_version < 3
                   OR shield_json IS NULL
                """
            ).fetchall()
            for row in rows:
                legacy_weapon = row[8] or row[2]
                old_weapon = Gear.from_json(legacy_weapon)
                old_armor = Gear.from_json(row[3])
                weapon = Gear(
                    "weapon",
                    old_weapon.name,
                    old_weapon.power,
                    dict(old_weapon.affinity),
                    old_weapon.hp_bonus,
                    old_weapon.magic,
                )
                shield = Gear(
                    "shield",
                    old_armor.name,
                    old_armor.power,
                    dict(old_armor.affinity),
                    old_armor.hp_bonus,
                    old_armor.magic,
                )
                con.execute(
                    """
                    UPDATE players
                    SET weapon_json=?, shield_json=?, head_json=NULL, ring_json=NULL,
                        legacy_weapon_json=?, equipment_version=3
                    WHERE guild_id=? AND user_id=?
                    """,
                    (
                        weapon.to_json(),
                        shield.to_json(),
                        legacy_weapon,
                        row[0],
                        row[1],
                    ),
                )

    def get_player(self, guild_id: int, user_id: int) -> PlayerState:
        with self.connect() as con:
            row = con.execute(
                """
                SELECT guild_id, user_id, coins, bombs, max_hp, hp,
                       weapon_json, ring_json, shield_json, head_json,
                       last_day, status, floor_number, highest_floor,
                       checkpoint_floor, lives_used, tutorial_completed
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
                     weapon_json, armor_json, shield_json, head_json, ring_json,
                     legacy_weapon_json, equipment_version, last_day, status,
                     floor_number, highest_floor, checkpoint_floor, lives_used, tutorial_completed)
                    VALUES (?, ?, 3, 2, 20, 20, ?, ?, ?, NULL, NULL, ?, 3, '', 'ready', 1, 1, 0, 0, 0)
                    """,
                    (
                        guild_id,
                        user_id,
                        START_WEAPON.to_json(),
                        START_SHIELD.to_json(),
                        START_SHIELD.to_json(),
                        START_WEAPON.to_json(),
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
            ring=Gear.from_json(row[7]) if row[7] else None,
            shield=Gear.from_json(row[8]),
            head=Gear.from_json(row[9]) if row[9] else None,
            last_day=row[10],
            status=row[11],
            floor_number=row[12],
            highest_floor=row[13],
            checkpoint_floor=row[14],
            lives_used=row[15],
            tutorial_completed=bool(row[16]),
        )

    def save_player(self, p: PlayerState):
        with self.connect() as con:
            con.execute(
                """
                UPDATE players
                SET coins=?, bombs=?, max_hp=?, hp=?,
                    weapon_json=?, ring_json=?, shield_json=?, head_json=?,
                    last_day=?, status=?, floor_number=?, highest_floor=?,
                    checkpoint_floor=?, lives_used=?, tutorial_completed=?,
                    equipment_version=3
                WHERE guild_id=? AND user_id=?
                """,
                (
                    p.coins,
                    p.bombs,
                    p.max_hp,
                    p.hp,
                    p.weapon.to_json(),
                    p.ring.to_json() if p.ring else None,
                    p.shield.to_json(),
                    p.head.to_json() if p.head else None,
                    p.last_day,
                    p.status,
                    p.floor_number,
                    p.highest_floor,
                    p.checkpoint_floor,
                    p.lives_used,
                    int(p.tutorial_completed),
                    p.guild_id,
                    p.user_id,
                ),
            )
            con.commit()

    def save_run(self, guild_id: int, user_id: int, day_key: str, floor_number: int, state_json: str):
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO saved_runs (guild_id, user_id, day_key, floor_number, state_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    day_key=excluded.day_key,
                    floor_number=excluded.floor_number,
                    state_json=excluded.state_json
                """,
                (guild_id, user_id, day_key, floor_number, state_json),
            )
            con.commit()

    def load_run(self, guild_id: int, user_id: int):
        with self.connect() as con:
            return con.execute(
                """
                SELECT day_key, floor_number, state_json
                FROM saved_runs
                WHERE guild_id=? AND user_id=?
                """,
                (guild_id, user_id),
            ).fetchone()

    def delete_run(self, guild_id: int, user_id: int):
        with self.connect() as con:
            con.execute(
                "DELETE FROM saved_runs WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
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
                       weapon_json, ring_json, shield_json, head_json,
                       last_day, status, floor_number, highest_floor,
                       checkpoint_floor, lives_used, tutorial_completed
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
                ring=Gear.from_json(row[7]) if row[7] else None,
                shield=Gear.from_json(row[8]),
                head=Gear.from_json(row[9]) if row[9] else None,
                last_day=row[10],
                status=row[11],
                floor_number=row[12],
                highest_floor=row[13],
                checkpoint_floor=row[14],
                lives_used=row[15],
                tutorial_completed=bool(row[16]),
            )
            for row in rows
        ]

    def test_reset(self, guild_id: int, user_id: int):
        p = self.get_player(guild_id, user_id)
        p.hp = player_max_hp(p)
        p.last_day = ""
        p.status = "ready"
        p.floor_number = max(1, p.checkpoint_floor + 1)
        p.lives_used = 0
        self.save_player(p)
        self.delete_run(guild_id, user_id)


db = Database(DB_PATH)
sessions: Dict[Tuple[int, int], GameSession] = {}
tutorial_sessions: Dict[Tuple[int, int], GameSession] = {}


def gear_state(gear: Optional[Gear]):
    if gear is None:
        return None
    return {
        "kind": gear.kind,
        "name": gear.name,
        "power": gear.power,
        "affinity": dict(gear.affinity),
        "hp_bonus": gear.hp_bonus,
        "magic": gear.magic,
    }


def gear_from_state(data):
    if not data:
        return None
    return Gear(
        str(data.get("kind", "weapon")),
        str(data.get("name", "이름 없는 장비")),
        int(data.get("power", 0)),
        {color: int(data.get("affinity", {}).get(color, 0)) for color in COLORS},
        int(data.get("hp_bonus", 0)),
        data.get("magic"),
    )


def enemy_state(enemy: Optional[Enemy]):
    if enemy is None:
        return None
    return {
        "shape": enemy.shape,
        "color": enemy.color,
        "hp": enemy.hp,
        "max_hp": enemy.max_hp,
        "damage": enemy.damage,
        "boss": enemy.boss,
    }


def enemy_from_state(data):
    if not data:
        return None
    return Enemy(
        str(data["shape"]),
        str(data["color"]),
        int(data["hp"]),
        int(data["max_hp"]),
        int(data["damage"]),
        bool(data.get("boss", False)),
        0,
        0.0,
    )


def room_state(room: Room):
    return {
        "pos": list(room.pos),
        "kind": room.kind,
        "visited": room.visited,
        "cleared": room.cleared,
        "enemy": enemy_state(room.enemy),
        "shop_stock": [gear_state(gear) for gear in room.shop_stock],
        "bomb_stock": room.bomb_stock,
        "slot_uses": room.slot_uses,
        "slot_broken": room.slot_broken,
    }


def room_from_state(data):
    pos = tuple(int(v) for v in data["pos"])
    room = Room(
        pos=pos,
        kind=str(data.get("kind", "normal")),
        visited=bool(data.get("visited", False)),
        cleared=bool(data.get("cleared", False)),
        enemy=enemy_from_state(data.get("enemy")),
        shop_stock=[gear for item in data.get("shop_stock", []) if (gear := gear_from_state(item)) is not None],
        bomb_stock=int(data.get("bomb_stock", 0)),
        slot_uses=int(data.get("slot_uses", 0)),
        slot_broken=bool(data.get("slot_broken", False)),
    )
    return room


def session_state(session: GameSession):
    return {
        "version": 1,
        "day_key": session.day_key,
        "floor_number": session.floor_number,
        "rooms": [room_state(room) for room in session.rooms.values()],
        "current": list(session.current),
        "boss_pos": list(session.boss_pos),
        "secret_pos": list(session.secret_pos),
        "secret_from": list(session.secret_from),
        "secret_direction": session.secret_direction,
        "secret_revealed": session.secret_revealed,
        "boss_defeated": session.boss_defeated,
        "previous": list(session.previous) if session.previous is not None else None,
        "run_failed": session.run_failed,
        "magic_shop_stock": [gear_state(gear) for gear in session.magic_shop_stock],
        "magic_shop_used": session.magic_shop_used,
        "pending_loot": gear_state(session.pending_loot),
        "pending_loot_note": session.pending_loot_note,
        "pending_loot_footer": session.pending_loot_footer,
    }


def session_from_state(guild_id: int, user_id: int, raw: str):
    data = json.loads(raw)
    rooms = {}
    for room_data in data.get("rooms", []):
        room = room_from_state(room_data)
        rooms[room.pos] = room
    if not rooms:
        raise ValueError("저장된 맵에 방이 없습니다.")
    current = tuple(int(v) for v in data.get("current", (0, 0)))
    boss_pos = tuple(int(v) for v in data["boss_pos"])
    secret_pos = tuple(int(v) for v in data["secret_pos"])
    secret_from = tuple(int(v) for v in data["secret_from"])
    if current not in rooms or boss_pos not in rooms or secret_pos not in rooms:
        raise ValueError("저장된 맵 좌표가 올바르지 않습니다.")
    previous_data = data.get("previous")
    previous = tuple(int(v) for v in previous_data) if previous_data is not None else None
    session = GameSession(
        guild_id=guild_id,
        user_id=user_id,
        day_key=str(data["day_key"]),
        floor_number=int(data["floor_number"]),
        rooms=rooms,
        current=current,
        boss_pos=boss_pos,
        secret_pos=secret_pos,
        secret_from=secret_from,
        secret_direction=str(data["secret_direction"]),
        secret_revealed=bool(data.get("secret_revealed", False)),
        boss_defeated=bool(data.get("boss_defeated", False)),
        phase="explore",
        previous=previous,
        run_failed=bool(data.get("run_failed", False)),
        magic_shop_stock=[gear for item in data.get("magic_shop_stock", []) if (gear := gear_from_state(item)) is not None],
        magic_shop_used=bool(data.get("magic_shop_used", False)),
        pending_loot=gear_from_state(data.get("pending_loot")),
        pending_loot_note=str(data.get("pending_loot_note", "")),
        pending_loot_footer=str(data.get("pending_loot_footer", "")),
    )
    room = session.room()
    if room.kind in ("normal", "boss") and not room.cleared and room.enemy is not None:
        session.phase = "battle_ready"
    return session


def persist_session(session: GameSession):
    if session.is_tutorial:
        return
    try:
        if session.ended:
            db.delete_run(session.guild_id, session.user_id)
            return
        raw = json.dumps(session_state(session), ensure_ascii=False, separators=(",", ":"))
        db.save_run(session.guild_id, session.user_id, session.day_key, session.floor_number, raw)
    except Exception as exc:
        print(f"맵 저장에 실패했습니다: {type(exc).__name__}: {exc}")


def load_persisted_session(guild_id: int, user_id: int, day_key: str, floor_number: int):
    row = db.load_run(guild_id, user_id)
    if row is None:
        return None
    saved_day, saved_floor, raw = row
    if saved_day != day_key or int(saved_floor) != int(floor_number):
        db.delete_run(guild_id, user_id)
        return None
    try:
        return session_from_state(guild_id, user_id, raw)
    except Exception as exc:
        print(f"저장된 맵을 불러오지 못했습니다: {type(exc).__name__}: {exc}")
        db.delete_run(guild_id, user_id)
        return None


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


def life_hearts(player: PlayerState) -> str:
    lives = max(0, min(MAX_DAILY_LIVES, remaining_lives(player)))
    return "❤️" * lives + "🖤" * (MAX_DAILY_LIVES - lives)


def checkpoint_start_floor(player: PlayerState) -> int:
    return max(1, player.checkpoint_floor + 1)


def player_max_hp(player: PlayerState) -> int:
    shield_hp = player.shield.hp_bonus if player.shield else 0
    head_hp = player.head.hp_bonus if player.head else 0
    return max(1, player.max_hp + shield_hp + head_hp)


def attack_power(player: PlayerState) -> int:
    ring_power = player.ring.power if player.ring else 0
    return max(0, player.weapon.power + ring_power)


def defense_power(player: PlayerState) -> int:
    head_power = player.head.power if player.head else 0
    return max(0, player.shield.power + head_power)


def attack_affinity(player: PlayerState, color: str) -> int:
    return affinity(player.weapon, color) + affinity(player.ring, color)


def defense_affinity(player: PlayerState, color: str) -> int:
    return affinity(player.shield, color) + affinity(player.head, color)


def has_magic(player: PlayerState, kind: str, effect: str) -> bool:
    gear = {
        "weapon": player.weapon,
        "ring": player.ring,
        "shield": player.shield,
        "head": player.head,
    }[kind]
    return gear is not None and gear.magic == effect


def equipped_gear(player: PlayerState, kind: str) -> Optional[Gear]:
    return {
        "weapon": player.weapon,
        "ring": player.ring,
        "shield": player.shield,
        "head": player.head,
    }[kind]


def equipped_gear_label(player: PlayerState, kind: str) -> str:
    gear = equipped_gear(player, kind)
    return gear.label() if gear else "`없음`"


def equip_gear(player: PlayerState, gear: Gear):
    if gear.kind == "weapon":
        player.weapon = gear
    elif gear.kind == "ring":
        player.ring = gear
    elif gear.kind == "shield":
        player.shield = gear
    elif gear.kind == "head":
        player.head = gear
    else:
        raise ValueError(f"알 수 없는 장비 종류: {gear.kind}")
    player.hp = min(player.hp, player_max_hp(player))


def gear_slot_name(kind: str) -> str:
    return {
        "weapon": "무기",
        "ring": "반지",
        "shield": "방패",
        "head": "투구",
    }[kind]


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
    base = {"weapon": 18, "ring": 14, "shield": 15, "head": 13}[gear.kind]
    scale = {"weapon": 4, "ring": 3, "shield": 3, "head": 3}[gear.kind]
    return base + floor_bonus * scale


def bomb_price(floor_number: int) -> int:
    return 8 + max(0, floor_number - 1) * 2


def normal_gear_kinds(floor_number: int) -> tuple[str, ...]:
    if floor_number < 6:
        return ("weapon", "shield")
    return ("weapon", "ring", "shield", "head")


def magic_pool_for_floor(floor_number: int) -> tuple[str, ...]:
    if floor_number < 10:
        return tuple(
            effect
            for effect in MAGIC_POOL
            if MAGIC_KINDS[effect] in ("weapon", "shield")
        )
    return MAGIC_POOL


def gear_affinity_range(kind: str, boss_drop: bool, floor_number: int) -> tuple[int, int]:
    growth = min(3, max(0, floor_number - 1) // 5)
    base = {
        "weapon": ((1, 2), (2, 3)),
        "ring": ((0, 1), (1, 2)),
        "shield": ((1, 2), (2, 3)),
        "head": ((0, 1), (1, 2)),
    }[kind][1 if boss_drop else 0]
    low = min(6, base[0] + growth)
    high = min(6, base[1] + growth)
    return low, max(low, high)


def gear_hp_range(kind: str, floor_number: int) -> tuple[int, int]:
    if floor_number >= 10:
        return (1, 4) if kind == "shield" else (2, 4)
    if floor_number >= 5:
        return (0, 3) if kind == "shield" else (1, 3)
    return (0, 2)


def generate_gear(kind: str, boss_drop=False, floor_number: int = 1) -> Gear:
    if kind == "armor":
        kind = "shield"
    floor_bonus = max(0, floor_number - 1)

    if kind == "weapon":
        names = ["유리 파편", "금속 파이프", "깨진 칼날", "고장 난 절단기", "비상 신호총"]
        low, high = ((5, 8) if boss_drop else (4, 6))
        power = random.randint(low, high) + floor_bonus
        hp_bonus = 0
    elif kind == "ring":
        names = ["철사 반지", "녹슨 반지", "구리 반지", "볼트 반지", "얇은 합금 반지"]
        low, high = ((2, 3) if boss_drop else (1, 3))
        power = random.randint(low, high)
        hp_bonus = 0
    elif kind == "shield":
        names = ["화물 상자 뚜껑", "기계 덮개", "깨진 방탄유리", "비상문 조각", "금 간 방패"]
        low, high = ((2, 4) if boss_drop else (1, 3))
        power = random.randint(low, high) + floor_bonus // 2
        hp_bonus = random.randint(*gear_hp_range("shield", floor_number))
    elif kind == "head":
        names = ["낡은 안전모", "깨진 바이저", "작업용 헬멧", "안전모", "두꺼운 후드"]
        low, high = ((1, 2) if boss_drop else (0, 2))
        power = random.randint(low, high) + floor_bonus // 4
        hp_bonus = random.randint(*gear_hp_range("head", floor_number))
    else:
        raise ValueError(f"알 수 없는 장비 종류: {kind}")

    affinity_points = gear_affinity_range(kind, boss_drop, floor_number)
    return Gear(
        kind=kind,
        name=random.choice(names),
        power=power,
        affinity=random_affinity(*affinity_points),
        hp_bonus=hp_bonus,
        magic=None,
    )


def generate_magic_gear(effect: str, floor_number: int) -> Gear:
    kind = MAGIC_KINDS[effect]
    gear = generate_gear(kind, boss_drop=True, floor_number=floor_number)
    gear.name = MAGIC_NAMES[effect]
    gear.magic = effect
    return gear


def magic_price(gear: Gear, floor_number: int) -> int:
    return gear_price(gear, floor_number) + 15 + floor_number * 2


def prepare_magic_shop(session: GameSession):
    if (
        session.is_tutorial
        or session.floor_number % 5 != 0
        or not session.boss_defeated
        or session.magic_shop_used
        or session.magic_shop_stock
    ):
        return
    effects = random.sample(magic_pool_for_floor(session.floor_number), 3)
    session.magic_shop_stock = [
        generate_magic_gear(effect, session.floor_number) for effect in effects
    ]


def magic_shop_available(session: GameSession) -> bool:
    return (
        not session.is_tutorial
        and session.floor_number % 5 == 0
        and session.boss_defeated
        and session.current == session.boss_pos
        and not session.magic_shop_used
        and bool(session.magic_shop_stock)
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
        shop_kinds = random.sample(normal_gear_kinds(floor_number), 2)
        secret.shop_stock = [
            generate_gear(kind, floor_number=floor_number)
            for kind in shop_kinds
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
        ring=None,
        shield=Gear.from_json(START_SHIELD.to_json()),
        head=None,
        last_day="",
        status="tutorial",
        floor_number=0,
        highest_floor=0,
        checkpoint_floor=0,
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
        generate_gear("shield", floor_number=1),
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


def apply_bleed(enemy: Enemy, player: Optional[PlayerState] = None) -> int:
    magic_bleed = player is not None and has_magic(player, "ring", MAGIC_RING_BLEED)
    cap = BLEED_MAX_STACKS + (1 if magic_bleed else 0)
    gain = 2 if magic_bleed and enemy.bleed_stacks == 0 else 1
    enemy.bleed_stacks = min(cap, enemy.bleed_stacks + gain)
    enemy.bleed_expires_at = time.monotonic() + BLEED_DURATION_SECONDS
    return enemy.bleed_stacks


def clear_bleed(enemy: Enemy):
    enemy.bleed_stacks = 0
    enemy.bleed_expires_at = 0.0


def affinity(gear: Optional[Gear], color: str) -> int:
    return gear.affinity.get(color, 0) if gear else 0


def attack_damage(player: PlayerState, enemy: Enemy, grade: str) -> int:
    if grade == "MISS":
        return 0
    timing_mult = {"PERFECT": 1.40, "GOOD": 1.0}[grade]
    color_mult = 1.0 + 0.25 * attack_affinity(player, enemy.color)
    return max(1, round(attack_power(player) * timing_mult * color_mult))


def weapon_magic_damage_bonus(player: PlayerState, enemy: Enemy, session: GameSession, grade: str) -> int:
    if grade == "MISS":
        return 0
    effect = player.weapon.magic
    if effect == MAGIC_WEAPON_CHAIN:
        return 1 if session.attack_chain + 1 >= 3 else 0
    if effect == MAGIC_WEAPON_HURT:
        return 1 if session.hurt_this_battle else 0
    if effect == MAGIC_WEAPON_BLEED:
        return 1 if enemy.bleed_stacks > 0 and bleed_seconds_left(enemy) > 0 else 0
    return 0


def incoming_damage(player: PlayerState, enemy: Enemy, grade: str, magic_roll=True) -> int:
    if grade == "PERFECT" or enemy.damage <= 0:
        return 0

    damage = enemy.damage
    if grade == "GOOD":
        damage = max(1, round(damage * 0.45))

    damage = max(0, damage - defense_power(player))
    resistance = max(0.35, 1.0 - 0.15 * defense_affinity(player, enemy.color))
    result = max(0, round(damage * resistance))
    if grade == "MISS":
        result = max(1, result)
    if (
        result > 0
        and magic_roll
        and has_magic(player, "shield", MAGIC_SHIELD_GUARD)
        and random.random() < 0.10
    ):
        result = max(1, result - 2)
    return result


def enemy_should_flee(player: PlayerState, enemy: Enemy) -> bool:
    if enemy.boss:
        return False
    return (
        attack_damage(player, enemy, "GOOD") >= enemy.max_hp
        and incoming_damage(player, enemy, "MISS", magic_roll=False) <= 1
    )


def flee_overpowered_enemy(session: GameSession, player: PlayerState) -> str:
    room = session.room()
    enemy = room.enemy
    if (
        session.is_tutorial
        or room.kind != "normal"
        or room.cleared
        or enemy is None
        or not enemy_should_flee(player, enemy)
    ):
        return ""
    room.cleared = True
    session.phase = "explore"
    cancel_bleed(session, clear=True)
    return f"👾 **{enemy.color} {enemy.shape}가 도망갔다!**"


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

    extra = 0.05 * defense_affinity(player, enemy.color)
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


def secret_edge(session: GameSession, source, target) -> bool:
    return (
        (source == session.secret_from and target == session.secret_pos)
        or (source == session.secret_pos and target == session.secret_from)
    )


def can_move_between(session: GameSession, source, target) -> bool:
    if target not in session.rooms:
        return False
    if source == session.secret_pos or target == session.secret_pos:
        return session.secret_revealed and secret_edge(session, source, target)
    return True


def accessible_directions(session: GameSession):
    result = []
    for name, delta in DIRECTIONS.items():
        target = add_pos(session.current, delta)
        if can_move_between(session, session.current, target):
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

        if east in visible and can_move_between(session, pos, east):
            ex, _ = cv(east)
            for xx in range(x + 1, ex):
                canvas[y][xx] = "─"

        if south in visible and can_move_between(session, pos, south):
            _, sy = cv(south)
            canvas[y + 1][x] = "│"

    return "\n".join("".join(row).rstrip() for row in canvas)


def gear_affinity_line(gear: Gear) -> str:
    superscript = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    return " ".join(
        f"{COLOR_MARK[color]}{str(gear.affinity.get(color, 0)).translate(superscript)}"
        for color in COLORS
    )


def combined_affinity_line(player: PlayerState, offensive: bool) -> str:
    superscript = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    return " ".join(
        f"{COLOR_MARK[color]}{str((attack_affinity if offensive else defense_affinity)(player, color)).translate(superscript)}"
        for color in COLORS
    )


def combat_stat_lines(player: PlayerState) -> str:
    return (
        f"⚔️ `{attack_power(player)}` · {combined_affinity_line(player, True)}\n"
        f"🛡️ `{defense_power(player)}` · {combined_affinity_line(player, False)}"
    )



def player_embed(player: PlayerState, session: GameSession, title: str, colour=None, show_resources=True):
    if session.is_tutorial and not title.startswith("0층"):
        title = f"0층 · 튜토리얼 · {title}"

    resource_line = (
        f"🪙 `{player.coins}` · 💣 `{player.bombs}`"
        if session.is_tutorial
        else f"{life_hearts(player)} · 🪙 `{player.coins}` · 💣 `{player.bombs}`"
    )

    value = (
        f"{hp_bar(player.hp, player_max_hp(player))} `{player.hp}/{player_max_hp(player)}`\n"
        f"{combat_stat_lines(player)}"
    )
    if show_resources:
        value += f"\n{resource_line}"

    embed = discord.Embed(title=title, colour=colour)
    embed.add_field(
        name="내 HP",
        value=value,
        inline=False,
    )
    return embed


def exploration_embed(player, session, note="", footer_status=""):
    persist_session(session)
    room = session.room()
    title = (
        f"0층 · 튜토리얼 · {room_name(room)}"
        if session.is_tutorial
        else f"{session.floor_number}층 · {room_name(room)}"
    )

    around = []
    for direction in ("왼쪽", "위", "아래", "오른쪽"):
        target = add_pos(session.current, DIRECTIONS[direction])
        can_move = can_move_between(session, session.current, target)
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

    resources = (
        f"🪙 `{player.coins}` · 💣 `{player.bombs}`"
        if session.is_tutorial
        else f"{life_hearts(player)} · 🪙 `{player.coins}` · 💣 `{player.bombs}`"
    )

    parts = []
    if note:
        parts.append(note)
    parts.append(
        f"**내 HP**\n"
        f"{hp_bar(player.hp, player_max_hp(player))} `{player.hp}/{player_max_hp(player)}`\n"
        f"{resources}"
    )
    parts.append(
        f"```text\n{map_ascii(session)}\n```\n"
        "`@` 현재 · `?` 미탐색 · `B` 보스 · `S` 비밀방"
    )
    parts.append("\n".join(around) if around else "막다른 방이다.")

    embed = discord.Embed(
        title=title,
        description="\n\n".join(parts),
    )

    footer_lines = []
    if footer_status:
        footer_lines.append(footer_status)

    if session.boss_defeated:
        if session.is_tutorial:
            if not session.tutorial_replay and session.current == session.boss_pos:
                footer_lines.append("⚠️ 튜토리얼의 아이템은 사라져요!")
        elif session.current == session.boss_pos:
            footer_lines.append("보스를 처치했다!")
            footer_lines.append(
                f"{session.floor_number + 1}층으로 가거나 더 둘러볼 수 있다."
            )
        else:
            footer_lines.append(
                f"보스 방에서 {session.floor_number + 1}층으로 갈 수 있다."
            )

    if footer_lines:
        embed.set_footer(text="\n".join(footer_lines))
    return embed


def combat_embed(player, session, note="", enemy_art: Optional[str] = None):
    enemy = session.room().enemy
    assert enemy is not None
    if not session.hit_animating:
        persist_session(session)

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

    embed.description = colored_enemy_art(enemy, enemy_art)
    bleed_left = bleed_seconds_left(enemy)
    bleed_line = (
        f" · {'🩸' * enemy.bleed_stacks} `{bleed_left:.1f}초`"
        if bleed_left > 0
        else ""
    )
    critical_line = "\n⚠️ **CRITICAL!**" if enemy_is_critical(enemy) else ""

    embed.add_field(
        name="적 HP",
        value=(
            f"{enemy_hp_bar(enemy)} "
            f"`{max(0, enemy.hp)}/{enemy.max_hp}`\n"
            f"⚔️ `{enemy.damage}`"
            f"{bleed_line}{critical_line}"
        ),
        inline=False,
    )

    embed.add_field(
        name="내 HP",
        value=(
            f"{hp_bar(player.hp, player_max_hp(player))} "
            f"`{player.hp}/{player_max_hp(player)}`\n"
            f"{combat_stat_lines(player)}\n"
            f"💣 `{player.bombs}`"
        ),
        inline=False,
    )

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
    persist_session(session)
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


def slot_embed(player, session, note="", footer_status=""):
    persist_session(session)
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
    if footer_status:
        embed.set_footer(text=footer_status)
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
            can_move = can_move_between(session, session.current, target)

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

        if magic_shop_available(session):
            magic_shop = discord.ui.Button(
                label="마법 상점",
                emoji="🔮",
                style=discord.ButtonStyle.secondary,
            )

            async def magic_shop_callback(interaction):
                await open_magic_shop(interaction, self.session)

            magic_shop.callback = magic_shop_callback
            self.add_item(magic_shop)

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
            label="전투개시",
            emoji="⚔️",
            style=discord.ButtonStyle.danger,
        )

        async def callback(interaction):
            await start_battle(interaction, self.session)

        btn.callback = callback
        self.add_item(btn)

        enemy = session.room().enemy
        if enemy and not enemy.boss:
            run = discord.ui.Button(
                label="도주",
                style=discord.ButtonStyle.secondary,
                disabled=session.run_failed,
            )

            async def run_callback(interaction):
                await try_run(interaction, self.session)

            run.callback = run_callback
            self.add_item(run)


class CombatView(OwnerView):
    def __init__(self, session, kind):
        super().__init__(session)
        p = session_player(session)
        enemy = session.room().enemy

        if kind == "attack":
            attack = discord.ui.Button(
                label="공격하기",
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
                label="방어하기",
                emoji="🛡️",
                style=discord.ButtonStyle.success,
            )

            async def shield_callback(interaction):
                await press_timing(interaction, self.session, "defend")

            shield.callback = shield_callback
            self.add_item(shield)



def loot_embed(player: PlayerState, session: GameSession, gear: Gear) -> discord.Embed:
    enemy = session.room().enemy
    colour = EMBED_COLORS[enemy.color] if enemy is not None else None
    embed = player_embed(
        player,
        session,
        "전리품 발견",
        colour=colour,
        show_resources=False,
    )
    if session.pending_loot_note:
        embed.description = session.pending_loot_note
    if session.pending_loot_footer:
        embed.set_footer(text=session.pending_loot_footer)
    current = equipped_gear(player, gear.kind)
    item_name = gear_slot_name(gear.kind)
    embed.add_field(name=f"새 {item_name}", value=gear.label(), inline=False)
    embed.add_field(name=f"현재 {item_name}", value=current.label() if current else "`없음`", inline=False)
    return embed


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
            equip_gear(p, gear)
            save_session_player(session, p)
            session.pending_loot = None
            session.pending_loot_note = ""
            session.pending_loot_footer = ""
            await show_after_clear(
                interaction,
                session,
                f"{gear.display_name()} 장착 완료.",
            )

        async def skip_callback(interaction):
            session.pending_loot = None
            session.pending_loot_note = ""
            session.pending_loot_footer = ""
            await show_after_clear(
                interaction,
                session,
                "새 장비를 버렸다.",
            )

        equip.callback = equip_callback
        skip.callback = skip_callback
        self.add_item(equip)
        self.add_item(skip)


class MagicShopView(OwnerView):
    def __init__(self, session):
        super().__init__(session)
        p = session_player(session)

        for index, gear in enumerate(session.magic_shop_stock[:3]):
            price = magic_price(gear, session.floor_number)
            btn = discord.ui.Button(
                label=f"{index + 1}번 ({price})",
                style=discord.ButtonStyle.success,
                disabled=session.magic_shop_used or p.coins < price,
            )

            async def callback(interaction, idx=index):
                await buy_magic_gear(interaction, self.session, idx)

            btn.callback = callback
            self.add_item(btn)

        leave = discord.ui.Button(
            label="나가기",
            emoji="↩️",
            style=discord.ButtonStyle.secondary,
        )

        async def leave_callback(interaction):
            p2 = session_player(session)
            await interaction.response.edit_message(
                embed=exploration_embed(p2, session),
                view=ExploreView(session),
            )

        leave.callback = leave_callback
        self.add_item(leave)


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
            persist_session(session)
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
        session.attack_chain = 0
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
    if damage > 0:
        session.hurt_this_battle = True
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
    if not can_move_between(session, session.current, target):
        await interaction.response.defer()
        return
    if session.ended:
        await interaction.response.defer()
        return

    cancel_cue(session)
    session.previous = session.current
    session.current = target
    session.run_failed = False
    room = session.room()
    room.visited = True
    p = session_player(session)

    flee_note = flee_overpowered_enemy(session, p)
    if flee_note:
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, flee_note),
            view=ExploreView(session),
        )
        return

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
                "✨ 반짝이는 것을 주웠다.",
                footer_status=f"🪙 코인을 {amount}개 획득했다!",
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
        note = "🏺 항아리를 깼다! 반짝이는 것이 보인다."
        footer_status = f"🪙 코인을 {amount}개 얻었다!"
    elif roll < 0.80:
        note = "🏺 항아리를 깼다! 아무것도 없다."
        footer_status = ""
    else:
        damage = random.randint(1, 3)
        if has_magic(p, "head", MAGIC_HEAD_POT_GUARD):
            damage = max(0, damage - 2)
        p.hp = max(0, p.hp - damage)
        save_session_player(session, p)
        note = "🏺 항아리를 깼다!"
        footer_status = f"❤️ HP가 {damage} 감소했다!"

        if p.hp <= 0:
            await player_died(
                interaction,
                session,
                note,
                footer_status=footer_status,
            )
            return

    await interaction.response.edit_message(
        embed=exploration_embed(
            p,
            session,
            note,
            footer_status=footer_status,
        ),
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
    flee_note = flee_overpowered_enemy(session, p)
    if flee_note:
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, flee_note),
            view=ExploreView(session),
        )
        return

    session.phase = "attack"
    session.enemy_anim_frame = 0
    session.attack_chain = 0
    session.hurt_this_battle = False
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
            session.attack_chain = 0
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
        if damage > 0:
            session.hurt_this_battle = True
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
        damage += weapon_magic_damage_bonus(p, enemy, session, grade)
        if grade == "MISS":
            session.attack_chain = 0
        else:
            session.attack_chain += 1
        enemy.hp -= damage

        if grade == "PERFECT":
            note = (
                f"💥 **SMAAAASH!!**\n"
                f"`{elapsed:.2f}초` — 적에게 **{damage} 피해!**"
            )
            if enemy.hp > 0:
                stacks = apply_bleed(enemy, p)
                schedule_bleed(interaction, session)
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
    if damage > 0:
        session.hurt_this_battle = True
    save_session_player(session, p)

    if grade == "PERFECT":
        counter = PERFECT_COUNTER_DAMAGE + (1 if has_magic(p, "shield", MAGIC_SHIELD_COUNTER) else 0)
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

    damage = random.randint(*BOMB_DAMAGE) + (2 if has_magic(p, "ring", MAGIC_RING_BOMB) else 0)
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
    if session.phase != "battle_ready" or session.run_failed:
        await interaction.response.defer()
        return

    p = session_player(session)

    if random.random() < RUN_SUCCESS_RATE:
        cancel_bleed(session, clear=True)
        enemy.hp = enemy.max_hp
        session.run_failed = False
        if session.previous is not None:
            session.current = session.previous
        session.phase = "explore"
        await interaction.response.edit_message(
            embed=exploration_embed(
                p,
                session,
                "**무사히 도망쳤다!**",
            ),
            view=ExploreView(session),
        )
        return

    session.run_failed = True
    await interaction.response.edit_message(
        embed=combat_embed(p, session, "**도망칠 수 없었다!**"),
        view=BattleStartView(session),
    )


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

    reward_lines = [f"🪙 코인을 {coins}개 획득했다!"]
    if bomb_gain:
        reward_lines.append("💣 폭탄을 1개 획득했다!")
    if enemy.boss and has_magic(p, "head", MAGIC_HEAD_BOSS_HEAL):
        before = p.hp
        p.hp = min(player_max_hp(p), p.hp + 2)
        healed = p.hp - before
        if healed > 0:
            reward_lines.append(f"❤️ HP가 {healed} 회복됐다!")
        save_session_player(session, p)
    reward_status = "\n".join(reward_lines)

    if enemy.boss:
        session.boss_defeated = True
        if session.floor_number % 5 == 0 and not session.is_tutorial:
            p.checkpoint_floor = max(p.checkpoint_floor, session.floor_number)
            save_session_player(session, p)
            prepare_magic_shop(session)

    if enemy.boss or random.random() < 0.30:
        gear = generate_gear(
            random.choice(normal_gear_kinds(session.floor_number)),
            boss_drop=enemy.boss,
            floor_number=session.floor_number,
        )
        session.pending_loot = gear
        session.pending_loot_note = combat_note
        session.pending_loot_footer = reward_status
        persist_session(session)

        await edit_interaction_message(
            interaction,
            embed=loot_embed(p, session, gear),
            view=LootView(session, gear),
        )
        return

    await show_after_clear(
        interaction,
        session,
        combat_note,
        footer_status=reward_status,
    )


async def show_after_clear(interaction, session, note, footer_status=""):
    p = session_player(session)
    await edit_interaction_message(
        interaction,
        embed=exploration_embed(
            p,
            session,
            note,
            footer_status=footer_status,
        ),
        view=ExploreView(session),
    )


def death_description(player: PlayerState, note: str) -> str:
    left = remaining_lives(player)
    if left <= 0:
        return (
            note
            + "\n\n**눈앞이 캄캄해졌다!**"
            + "\n오늘은 더 이상 플레이할 수 없다. 내일 다시 도전하자!"
            + "\n무기·반지·방패·투구·코인·폭탄은 그대로 유지된다."
            + "\n플레이테스트 중이라면 `/테스트리셋`을 사용할 수 있습니다."
        )
    return (
        note
        + "\n\n**눈앞이 캄캄해졌다!**"
        + f"\n남은 목숨 **{left}/{MAX_DAILY_LIVES}**"
        + (
            "\n`/게임`으로 체크포인트에서 다시 도전하자!"
            if player.checkpoint_floor > 0
            else "\n`/게임`으로 1층부터 다시 도전하자!"
        )
    )


async def player_died(interaction, session, note, footer_status=""):
    cancel_cue(session)
    cancel_bleed(session, clear=True)
    p = session_player(session)
    p.hp = 0
    session.ended = True
    persist_session(session)

    if session.is_tutorial:
        embed = player_embed(p, session, "게임 오버")
        embed.description = note + "\n\n**눈앞이 캄캄해졌다!**"
        if footer_status:
            embed.set_footer(text=footer_status)
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
    if footer_status:
        embed.set_footer(text=footer_status)
    await interaction.response.edit_message(embed=embed, view=None)


async def player_died_background(interaction, session, note):
    cancel_cue(session)
    cancel_bleed(session, clear=True)
    p = session_player(session)
    p.hp = 0
    session.ended = True
    persist_session(session)

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
        p.hp = player_max_hp(p)
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
    persist_session(session)

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


def magic_shop_embed(player: PlayerState, session: GameSession, note="") -> discord.Embed:
    persist_session(session)
    embed = discord.Embed(
        title=f"{session.floor_number}층 · 마법 상점",
        description=note or "🔮 보스 방 한쪽에서 이상한 상인이 기다리고 있다.\n**한 가지만 살 수 있다.**",
    )
    for index, gear in enumerate(session.magic_shop_stock[:3], 1):
        price = magic_price(gear, session.floor_number)
        current = equipped_gear(player, gear.kind)
        embed.add_field(
            name=f"{index}번 · 🪙 {price}",
            value=(
                f"{gear.label()}\n"
                f"현재 {gear_slot_name(gear.kind)}: {current.label() if current else '없음'}"
            ),
            inline=False,
        )
    embed.set_footer(text=f"🪙 현재 코인 {player.coins}")
    return embed


async def open_magic_shop(interaction, session):
    prepare_magic_shop(session)
    p = session_player(session)
    if not magic_shop_available(session):
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, "상인은 이미 자리를 떠났다."),
            view=ExploreView(session),
        )
        return
    await interaction.response.edit_message(
        embed=magic_shop_embed(p, session),
        view=MagicShopView(session),
    )


async def buy_magic_gear(interaction, session, index):
    p = session_player(session)
    if session.magic_shop_used or index >= len(session.magic_shop_stock):
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, "상인은 더 이상 거래하지 않는다."),
            view=ExploreView(session),
        )
        return

    gear = session.magic_shop_stock[index]
    price = magic_price(gear, session.floor_number)
    if p.coins < price:
        await interaction.response.edit_message(
            embed=magic_shop_embed(p, session, "코인이 부족하다."),
            view=MagicShopView(session),
        )
        return

    p.coins -= price
    equip_gear(p, gear)
    save_session_player(session, p)
    session.magic_shop_used = True
    session.magic_shop_stock.clear()

    await interaction.response.edit_message(
        embed=exploration_embed(
            p,
            session,
            f"**{gear.display_name()}** 구입 및 장착 완료.",
            footer_status=f"🪙 코인을 {price}개 사용했다!",
        ),
        view=ExploreView(session),
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

    equip_gear(p, gear)
    save_session_player(session, p)

    await interaction.response.edit_message(
        embed=shop_embed(
            p,
            session,
            f"**{gear.display_name()}** 구입 및 장착 완료.",
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

    note = ""
    footer_lines = []
    if roll < 0.45:
        note = "아무것도 안 나왔다."
    elif roll < 0.68:
        gain = random.randint(2, 4) + reward_bonus
        p.coins += gain
        footer_lines.append(f"🪙 코인을 {gain}개 획득했다!")
    elif roll < 0.80:
        p.bombs += 1
        footer_lines.append("💣 폭탄을 1개 획득했다!")
    elif roll < 0.91:
        heal = random.randint(3, 6)
        before = p.hp
        p.hp = min(player_max_hp(p), p.hp + heal)
        restored = p.hp - before
        footer_lines.append(f"❤️ HP가 {restored} 회복됐다!")
    else:
        gain = random.randint(6, 10) + reward_bonus * 2
        p.coins += gain
        note = "🎰 잭팟!"
        footer_lines.append(f"🪙 코인을 {gain}개 획득했다!")

    break_rates = [0.05, 0.10, 0.20, 0.35, 0.55, 0.75]
    break_rate = break_rates[min(room.slot_uses - 1, len(break_rates) - 1)]

    if random.random() < break_rate:
        room.slot_broken = True
        note = f"{note}\n\n**철컥.** 슬롯머신이 멈췄다." if note else "**철컥.** 슬롯머신이 멈췄다."

    save_session_player(session, p)

    await interaction.response.edit_message(
        embed=slot_embed(
            p,
            session,
            note,
            footer_status="\n".join(footer_lines),
        ),
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
            "💣 슬롯머신 폭파!",
            footer_status=f"🪙 코인을 {gain}개 획득했다!",
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
    "무기 공격",
    "반지",
    "반지 공격",
    "방패",
    "방패 방어",
    "방패 HP",
    "투구",
    "투구 방어",
    "투구 HP",
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

    if worksheet.col_count < len(SHEET_HEADERS):
        worksheet.resize(cols=len(SHEET_HEADERS))

    last_col = gspread.utils.rowcol_to_a1(1, len(SHEET_HEADERS)).replace("1", "")
    existing = worksheet.get_all_values()
    existing_by_user_id: dict[str, int] = {}
    for row_number, row in enumerate(existing[1:], start=2):
        if len(row) >= 2 and row[1].strip():
            existing_by_user_id[row[1].strip()] = row_number

    updates = [
        {
            "range": f"A1:{last_col}1",
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
                "range": f"A{row_number}:{last_col}{row_number}",
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
        db.delete_run(guild_id, user_id)
        db.delete_run(guild_id, user_id)
        old = sessions.pop(key, None)
        if old:
            cancel_cue(old)
            old.ended = True

        p.hp = player_max_hp(p)
        p.last_day = today
        p.status = "playing"
        p.floor_number = checkpoint_start_floor(p)
        p.lives_used = 0
        p.highest_floor = max(p.highest_floor, p.floor_number)
        db.save_player(p)

        session = generate_floor(guild_id, user_id, today, p.floor_number)
        sessions[key] = session

        start_note = (
            f"**체크포인트로 돌아왔다.**\n남은 목숨 `{MAX_DAILY_LIVES}/{MAX_DAILY_LIVES}`"
            if p.checkpoint_floor > 0
            else f"**1층 시작!**\n남은 목숨 `{MAX_DAILY_LIVES}/{MAX_DAILY_LIVES}`"
        )
        await interaction.response.send_message(
            embed=exploration_embed(
                p,
                session,
                start_note,
            ),
            view=ExploreView(session),
            ephemeral=True,
        )
        return

    if p.status == "dead":
        if p.lives_used >= MAX_DAILY_LIVES:
            await interaction.response.send_message(
                "오늘은 더 이상 플레이할 수 없다. 내일 다시 도전하자!\n"
                "무기·반지·방패·투구·코인·폭탄은 그대로 유지된다.\n"
                "플레이테스트 중이라면 `/테스트리셋`을 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        old = sessions.pop(key, None)
        if old:
            cancel_cue(old)
            old.ended = True

        p.hp = player_max_hp(p)
        p.status = "playing"
        p.floor_number = checkpoint_start_floor(p)
        db.save_player(p)

        session = generate_floor(guild_id, user_id, today, p.floor_number)
        sessions[key] = session
        restart_note = (
            f"**체크포인트로 돌아왔다.**\n남은 목숨 `{remaining_lives(p)}/{MAX_DAILY_LIVES}`"
            if p.checkpoint_floor > 0
            else (
                "**다시 도전!**\n"
                f"남은 목숨 `{remaining_lives(p)}/{MAX_DAILY_LIVES}` · 1층부터 시작한다."
            )
        )
        await interaction.response.send_message(
            embed=exploration_embed(
                p,
                session,
                restart_note,
            ),
            view=ExploreView(session),
            ephemeral=True,
        )
        return

    if p.status != "playing":
        p.status = "playing"
        db.save_player(p)

    old = sessions.get(key)
    restored_from_disk = False
    if old is None:
        old = load_persisted_session(guild_id, user_id, today, p.floor_number)
        if old is not None:
            sessions[key] = old
            restored_from_disk = True

    if old and not old.ended and old.day_key == today:
        room = old.room()

        if old.pending_loot is not None:
            await interaction.response.send_message(
                embed=loot_embed(p, old, old.pending_loot),
                view=LootView(old, old.pending_loot),
                ephemeral=True,
            )
        elif room.kind in ("normal", "boss") and not room.cleared:
            flee_note = None if restored_from_disk else flee_overpowered_enemy(old, p)
            if flee_note:
                await interaction.response.send_message(
                    embed=exploration_embed(p, old, flee_note),
                    view=ExploreView(old),
                    ephemeral=True,
                )
                return
            cancel_cue(old)
            old.phase = "battle_ready"
            note = "저장된 전투로 돌아왔다. 다시 전투를 시작하자!" if restored_from_disk else "전투 화면으로 돌아왔다. 다시 전투를 시작하자!"
            await interaction.response.send_message(
                embed=combat_embed(p, old, note),
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
            note = "저장된 층으로 돌아왔다." if restored_from_disk else "진행 중인 층으로 돌아왔다."
            await interaction.response.send_message(
                embed=exploration_embed(p, old, note),
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

    status_hearts = "❤️" * max(0, min(MAX_DAILY_LIVES, lives)) + "🖤" * (MAX_DAILY_LIVES - max(0, min(MAX_DAILY_LIVES, lives)))
    equipment_lines = [
        f"⚔️ **무기** · {p.weapon.label().replace(' | ', chr(10), 1)}",
        f"🛡️ **방패** · {p.shield.label().replace(' | ', chr(10), 1)}",
    ]
    if p.ring is not None:
        equipment_lines.insert(1, f"💍 **반지** · {p.ring.label().replace(' | ', chr(10), 1)}")
    if p.head is not None:
        equipment_lines.append(f"⛑️ **투구** · {p.head.label().replace(' | ', chr(10), 1)}")

    embed = discord.Embed(title=f"{interaction.user.display_name} — 상태")
    embed.add_field(
        name=f"내 HP {status_hearts}",
        value=(
            f"{hp_bar(p.hp, player_max_hp(p))} `{p.hp}/{player_max_hp(p)}`\n"
            f"{combat_stat_lines(p)}\n"
            f"코인 `{p.coins}` · 폭탄 `{p.bombs}`"
        ),
        inline=False,
    )
    embed.add_field(
        name="장비",
        value="\n".join(equipment_lines),
        inline=False,
    )
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
    위력="장비의 공격력 또는 방어력",
)
@discord.app_commands.choices(
    아이템=[
        discord.app_commands.Choice(name="코인", value="coin"),
        discord.app_commands.Choice(name="폭탄", value="bomb"),
        discord.app_commands.Choice(name="무기", value="weapon"),
        discord.app_commands.Choice(name="반지", value="ring"),
        discord.app_commands.Choice(name="방패", value="shield"),
        discord.app_commands.Choice(name="투구", value="head"),
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
    elif 아이템 in ("weapon", "ring", "shield", "head"):
        if 수량 != 1:
            await interaction.response.send_message(
                "장비는 한 번에 1개만 지급할 수 있습니다.",
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

        equip_gear(p, gear)
        slot_name = gear_slot_name(아이템)
        stat_name = "공격" if 아이템 in ("weapon", "ring") else "방어"
        result = f"{slot_name} **{gear.display_name()}** ({stat_name} {gear.power})"
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
                p.ring.name if p.ring else "",
                p.ring.power if p.ring else "",
                p.shield.name,
                p.shield.power,
                p.shield.hp_bonus,
                p.head.name if p.head else "",
                p.head.power if p.head else "",
                p.head.hp_bonus if p.head else "",
                p.bombs,
                f"{p.hp}/{player_max_hp(p)}",
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
        "**무기·반지·방패·투구·코인·폭탄은 유지됩니다.**",
        ephemeral=True,
    )


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN이 없습니다. `.env.example`을 복사해 `.env`를 만든 뒤 토큰을 넣어 주세요."
        )

    bot.run(TOKEN)
