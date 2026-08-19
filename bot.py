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
DEBUG_USER_ID_RAW = os.getenv("DEBUG_USER_ID", "").strip()
DEBUG_USER_ID = int(DEBUG_USER_ID_RAW) if DEBUG_USER_ID_RAW.isdigit() else None
FULL_VERSION_PASSWORD = os.getenv("FULL_VERSION_PASSWORD", "").strip()
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
DAILY_TARGET_FLOOR = 10
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
SUPERSCRIPT_TRANS = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")


def small_number(value) -> str:
    return str(value).translate(SUPERSCRIPT_TRANS)


def korean_josa(text: str, consonant: str, vowel: str) -> str:
    for ch in reversed(text):
        if "가" <= ch <= "힣":
            return consonant if (ord(ch) - 0xAC00) % 28 else vowel
    return vowel

NORMAL_ENEMIES = ("크랩", "옥토퍼스", "스퀴드")
NORMAL_GEAR_NAMES = {
    "weapon": ("유리 파편", "금속 파이프", "깨진 칼날", "고장 난 절단기", "비상 신호총"),
    "ring": ("철사 반지", "녹슨 반지", "구리 반지", "볼트 반지", "얇은 합금 반지"),
    "shield": ("화물 상자 뚜껑", "기계 덮개", "깨진 방탄유리", "비상문 조각", "금 간 방패"),
    "head": ("낡은 안전모", "깨진 바이저", "작업용 헬멧", "안전모", "두꺼운 후드"),
}
UTILITY_ITEMS = ("폭탄", "항아리")
CHARACTER_BASIC = "basic"
CHARACTER_VAMPIRE = "vampire"
CHARACTER_BOMBER = "bomber"
CHARACTER_SCRAPPER = "scrapper"
CHARACTER_POT_THROWER = "pot_thrower"
CHARACTER_TOMB_RAIDER = "tomb_raider"
CHARACTER_PERFECTIONIST = "perfectionist"
CHARACTER_GLASS = "glass"
CHARACTER_CHAOS = "chaos"
CHARACTERS = {
    CHARACTER_BASIC: {
        "name": "기본",
        "description": "특별한 능력이 없다.",
        "ability": "가장 평범한 탐사자다.",
    },
    CHARACTER_VAMPIRE: {
        "name": "흡혈",
        "description": "피를 흘리게 하고 상처를 회복하는 탐사자다.",
        "ability": "직접 공격으로 출혈을 내는 데 성공하면 50% 확률로 HP를 1 회복한다.",
    },
    CHARACTER_BOMBER: {
        "name": "폭발광",
        "description": "폭발물을 유난히 잘 다루는 탐사자다.",
        "ability": "폭탄 10개로 시작한다. 폭탄 피해가 2 증가하고 폭탄 수급량이 늘어난다.",
    },
    CHARACTER_SCRAPPER: {
        "name": "고물상",
        "description": "버려지는 장비에서도 쓸모를 찾아낸다.",
        "ability": "전리품 장비를 버리면 가치에 따라 코인을 얻는다.",
    },
    CHARACTER_POT_THROWER: {
        "name": "항아리 투척꾼",
        "description": "항아리를 깨는 대신 들고 다닐 수 있다.",
        "ability": "항아리 하나를 보관해 전투에서 던질 수 있다. 던진 항아리는 폭탄과 같은 피해를 주며 항아리의 피해를 받지 않는다.",
    },
    CHARACTER_TOMB_RAIDER: {
        "name": "도굴꾼",
        "description": "숨겨진 공간의 기척을 알아챈다.",
        "ability": "층에 들어설 때부터 보스의 위치를 알고 비밀방이 열려 있다.",
    },
    CHARACTER_PERFECTIONIST: {
        "name": "완벽주의자",
        "description": "완벽한 타이밍만을 노린다.",
        "ability": "PERFECT 공격과 반격이 더 강하다. 대신 GOOD 공격의 피해가 감소한다.",
    },
    CHARACTER_GLASS: {
        "name": "유리몸",
        "description": "조금만 맞아도 위험하지만 공격은 강하다.",
        "ability": "기본 최대 HP가 10이 되는 대신 직접 공격 피해가 3 증가한다.",
    },
    CHARACTER_CHAOS: {
        "name": "혼돈",
        "description": "다른 무기를 사용할 수 없는 변칙적인 탐사자다.",
        "ability": "혼돈의 검으로 시작한다. 직접 공격이 적중할 때마다 검의 효과가 무작위로 발동한다.",
    },
}
CHARACTER_ORDER = (
    CHARACTER_BASIC,
    CHARACTER_VAMPIRE,
    CHARACTER_BOMBER,
    CHARACTER_SCRAPPER,
    CHARACTER_POT_THROWER,
    CHARACTER_TOMB_RAIDER,
    CHARACTER_PERFECTIONIST,
    CHARACTER_GLASS,
    CHARACTER_CHAOS,
)
DAILY_RULES = (
    "큰 맵",
    "목숨 1개",
)
ENEMY_MODIFIERS = (
    "졸린",
    "멍한",
    "신경질적인",
    "겁이 많은",
    "산만한",
    "먼지투성이",
    "축축한",
    "잔뜩 웅크린",
)
ENEMY_MODIFIER_CHANCE = 0.20

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
        pips = " ".join(
            f"{COLOR_MARK[color]}{small_number(self.affinity.get(color, 0))}"
            for color in COLORS
        )
        if self.kind == "weapon":
            stats = f"⚔️ {small_number(self.power)} · {pips}"
        elif self.kind == "ring":
            stats = f"⚔️ {small_number(f'+{self.power}')} · {pips}"
        elif self.kind == "shield":
            stats = f"🛡️ {small_number(self.power)} · ❤️ {small_number(f'+{self.hp_bonus}')} · {pips}"
        else:
            stats = f"🛡️ {small_number(self.power)} · ❤️ {small_number(f'+{self.hp_bonus}')} · {pips}"
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
CHAOS_SWORD = Gear(
    "weapon", "혼돈의 검", 4, {"시안": 0, "마젠타": 0, "옐로": 0}
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
    modifier: Optional[str] = None

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
    flavor: str = ""


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
    carried_pot: int = 0
    mode: str = "main"
    character_key_override: Optional[str] = None
    daily_rule: str = ""
    fake_enabled: bool = False

    @property
    def is_daily(self) -> bool:
        return self.mode == "daily"

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
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_ui_messages (
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    PRIMARY KEY (guild_id, channel_id, kind)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS full_access (
                    user_id INTEGER PRIMARY KEY,
                    authorized_at TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS user_meta (
                    user_id INTEGER PRIMARY KEY,
                    ending15_count INTEGER NOT NULL DEFAULT 0,
                    true_ending_count INTEGER NOT NULL DEFAULT 0,
                    bomb_uses INTEGER NOT NULL DEFAULT 0,
                    gear_discards INTEGER NOT NULL DEFAULT 0,
                    pots_broken INTEGER NOT NULL DEFAULT 0,
                    secrets_found INTEGER NOT NULL DEFAULT 0,
                    perfect_count INTEGER NOT NULL DEFAULT 0,
                    flawless_true_endings INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS discoveries (
                    user_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    item_key TEXT NOT NULL,
                    PRIMARY KEY (user_id, category, item_key)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS run_meta (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    character_key TEXT NOT NULL DEFAULT 'basic',
                    reincarnated INTEGER NOT NULL DEFAULT 0,
                    fake_enabled INTEGER NOT NULL DEFAULT 0,
                    died_once INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_runs (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    day_key TEXT NOT NULL,
                    floor_number INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_records (
                    guild_id INTEGER NOT NULL,
                    day_key TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    floor_number INTEGER NOT NULL DEFAULT 1,
                    coins INTEGER NOT NULL DEFAULT 0,
                    completed INTEGER NOT NULL DEFAULT 0,
                    finished INTEGER NOT NULL DEFAULT 0,
                    character_key TEXT NOT NULL DEFAULT 'basic',
                    rule TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (guild_id, day_key, user_id)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS expedition_activity (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    last_mode TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            run_meta_columns = {
                row[1] for row in con.execute("PRAGMA table_info(run_meta)").fetchall()
            }
            if "fake_enabled" not in run_meta_columns:
                con.execute("ALTER TABLE run_meta ADD COLUMN fake_enabled INTEGER NOT NULL DEFAULT 0")
            if "died_once" not in run_meta_columns:
                con.execute("ALTER TABLE run_meta ADD COLUMN died_once INTEGER NOT NULL DEFAULT 0")

            user_meta_columns = {
                row[1] for row in con.execute("PRAGMA table_info(user_meta)").fetchall()
            }
            user_meta_additions = {
                "gear_discards": "INTEGER NOT NULL DEFAULT 0",
                "pots_broken": "INTEGER NOT NULL DEFAULT 0",
                "secrets_found": "INTEGER NOT NULL DEFAULT 0",
                "perfect_count": "INTEGER NOT NULL DEFAULT 0",
                "flawless_true_endings": "INTEGER NOT NULL DEFAULT 0",
            }
            for name, definition in user_meta_additions.items():
                if name not in user_meta_columns:
                    con.execute(f"ALTER TABLE user_meta ADD COLUMN {name} {definition}")

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
                    floor_number=MAX(daily_records.floor_number, excluded.floor_number),
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

    def save_daily_run(self, guild_id: int, user_id: int, day_key: str, floor_number: int, state_json: str):
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO daily_runs (guild_id, user_id, day_key, floor_number, state_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    day_key=excluded.day_key,
                    floor_number=excluded.floor_number,
                    state_json=excluded.state_json
                """,
                (guild_id, user_id, day_key, floor_number, state_json),
            )
            con.commit()

    def load_daily_run(self, guild_id: int, user_id: int):
        with self.connect() as con:
            return con.execute(
                """
                SELECT day_key, floor_number, state_json
                FROM daily_runs
                WHERE guild_id=? AND user_id=?
                """,
                (guild_id, user_id),
            ).fetchone()

    def delete_daily_run(self, guild_id: int, user_id: int):
        with self.connect() as con:
            con.execute(
                "DELETE FROM daily_runs WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            )
            con.commit()

    def record_daily_progress(self, guild_id: int, day_key: str, user_id: int, floor_number: int, coins: int, character_key: str, rule: str, completed: bool = False, finished: bool = False):
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO daily_records
                    (guild_id, day_key, user_id, floor_number, coins, completed, finished, character_key, rule, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, day_key, user_id) DO UPDATE SET
                    floor_number=excluded.floor_number,
                    coins=excluded.coins,
                    completed=MAX(daily_records.completed, excluded.completed),
                    finished=MAX(daily_records.finished, excluded.finished),
                    character_key=excluded.character_key,
                    rule=excluded.rule,
                    updated_at=excluded.updated_at
                """,
                (
                    guild_id, day_key, user_id, max(1, floor_number), max(0, coins),
                    int(completed), int(finished), character_key, rule,
                    datetime.now(KST).isoformat(timespec="seconds"),
                ),
            )
            con.commit()

    def get_daily_record(self, guild_id: int, day_key: str, user_id: int):
        with self.connect() as con:
            row = con.execute(
                """
                SELECT floor_number, coins, completed, finished, character_key, rule
                FROM daily_records
                WHERE guild_id=? AND day_key=? AND user_id=?
                """,
                (guild_id, day_key, user_id),
            ).fetchone()
        if row is None:
            return None
        return {
            "floor_number": int(row[0]),
            "coins": int(row[1]),
            "completed": bool(row[2]),
            "finished": bool(row[3]),
            "character_key": str(row[4]),
            "rule": str(row[5]),
        }

    def daily_ranking(self, guild_id: int, day_key: str, limit: int = 10):
        with self.connect() as con:
            return con.execute(
                """
                SELECT user_id, floor_number, coins, completed, finished
                FROM daily_records
                WHERE guild_id=? AND day_key=?
                ORDER BY completed DESC, floor_number DESC, coins DESC, user_id ASC
                LIMIT ?
                """,
                (guild_id, day_key, limit),
            ).fetchall()

    def get_channel_ui_message(self, guild_id: int, channel_id: int, kind: str):
        with self.connect() as con:
            row = con.execute(
                """
                SELECT message_id
                FROM channel_ui_messages
                WHERE guild_id=? AND channel_id=? AND kind=?
                """,
                (guild_id, channel_id, kind),
            ).fetchone()
        return int(row[0]) if row else None

    def set_channel_ui_message(self, guild_id: int, channel_id: int, kind: str, message_id: int):
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO channel_ui_messages (guild_id, channel_id, kind, message_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id, channel_id, kind) DO UPDATE SET
                    message_id=excluded.message_id
                """,
                (guild_id, channel_id, kind, message_id),
            )
            con.commit()

    def has_full_access(self, user_id: int) -> bool:
        with self.connect() as con:
            row = con.execute(
                "SELECT 1 FROM full_access WHERE user_id=?",
                (user_id,),
            ).fetchone()
        return row is not None

    def grant_full_access(self, user_id: int):
        with self.connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO full_access (user_id, authorized_at) VALUES (?, ?)",
                (user_id, datetime.now(KST).isoformat(timespec="seconds")),
            )
            con.commit()

    def get_user_meta(self, user_id: int):
        with self.connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO user_meta (user_id) VALUES (?)",
                (user_id,),
            )
            row = con.execute(
                "SELECT ending15_count, true_ending_count, bomb_uses, gear_discards, pots_broken, secrets_found, perfect_count, flawless_true_endings FROM user_meta WHERE user_id=?",
                (user_id,),
            ).fetchone()
            con.commit()
        return {
            "ending15_count": int(row[0]),
            "true_ending_count": int(row[1]),
            "bomb_uses": int(row[2]),
            "gear_discards": int(row[3]),
            "pots_broken": int(row[4]),
            "secrets_found": int(row[5]),
            "perfect_count": int(row[6]),
            "flawless_true_endings": int(row[7]),
        }

    def increment_user_meta(self, user_id: int, field: str, amount: int = 1):
        allowed = {"bomb_uses", "gear_discards", "pots_broken", "secrets_found", "perfect_count", "flawless_true_endings"}
        if field not in allowed:
            raise ValueError("알 수 없는 메타 기록이다.")
        with self.connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO user_meta (user_id) VALUES (?)",
                (user_id,),
            )
            con.execute(
                f"UPDATE user_meta SET {field}={field}+? WHERE user_id=?",
                (max(0, amount), user_id),
            )
            con.commit()

    def record_bomb_use(self, user_id: int, amount: int = 1):
        self.increment_user_meta(user_id, "bomb_uses", amount)

    def record_gear_discard(self, user_id: int, amount: int = 1):
        self.increment_user_meta(user_id, "gear_discards", amount)

    def record_pot_break(self, user_id: int, amount: int = 1):
        self.increment_user_meta(user_id, "pots_broken", amount)

    def record_secret_found(self, user_id: int, amount: int = 1):
        self.increment_user_meta(user_id, "secrets_found", amount)

    def record_perfect(self, user_id: int, amount: int = 1):
        self.increment_user_meta(user_id, "perfect_count", amount)

    def record_flawless_true_ending(self, user_id: int):
        self.increment_user_meta(user_id, "flawless_true_endings", 1)

    def record_ending(self, user_id: int, true_ending: bool = False):
        field = "true_ending_count" if true_ending else "ending15_count"
        with self.connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO user_meta (user_id) VALUES (?)",
                (user_id,),
            )
            con.execute(
                f"UPDATE user_meta SET {field}={field}+1 WHERE user_id=?",
                (user_id,),
            )
            con.commit()

    def discover(self, user_id: int, category: str, item_key: str):
        with self.connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO discoveries (user_id, category, item_key) VALUES (?, ?, ?)",
                (user_id, category, item_key),
            )
            con.commit()

    def get_discoveries(self, user_id: int, category: str):
        with self.connect() as con:
            rows = con.execute(
                "SELECT item_key FROM discoveries WHERE user_id=? AND category=?",
                (user_id, category),
            ).fetchall()
        return {str(row[0]) for row in rows}

    def get_run_meta(self, guild_id: int, user_id: int):
        with self.connect() as con:
            row = con.execute(
                "SELECT character_key, reincarnated, fake_enabled, died_once FROM run_meta WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            ).fetchone()
        if row is None:
            return {"character_key": CHARACTER_BASIC, "reincarnated": False, "fake_enabled": False, "died_once": False}
        character_key = str(row[0]) if str(row[0]) in CHARACTERS else CHARACTER_BASIC
        return {"character_key": character_key, "reincarnated": bool(row[1]), "fake_enabled": bool(row[2]), "died_once": bool(row[3])}

    def set_run_meta(self, guild_id: int, user_id: int, character_key: str, reincarnated: bool, fake_enabled: bool = False, died_once: bool = False):
        if character_key not in CHARACTERS:
            character_key = CHARACTER_BASIC
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO run_meta (guild_id, user_id, character_key, reincarnated, fake_enabled, died_once)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    character_key=excluded.character_key,
                    reincarnated=excluded.reincarnated,
                    fake_enabled=excluded.fake_enabled,
                    died_once=excluded.died_once
                """,
                (guild_id, user_id, character_key, int(reincarnated), int(fake_enabled), int(died_once)),
            )
            con.commit()

    def clear_run_meta(self, guild_id: int, user_id: int):
        with self.connect() as con:
            con.execute(
                "DELETE FROM run_meta WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            )
            con.commit()

    def mark_expedition_activity(self, guild_id: int, user_id: int, mode: str):
        if mode not in ("main", "daily"):
            return
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO expedition_activity (guild_id, user_id, last_mode, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    last_mode=excluded.last_mode,
                    updated_at=excluded.updated_at
                """,
                (guild_id, user_id, mode, datetime.now(KST).isoformat(timespec="microseconds")),
            )
            con.commit()

    def get_last_expedition_mode(self, guild_id: int, user_id: int):
        with self.connect() as con:
            row = con.execute(
                "SELECT last_mode FROM expedition_activity WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            ).fetchone()
        if row is None or row[0] not in ("main", "daily"):
            return None
        return str(row[0])

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

    def total_clear_ranking(self, guild_id: int, limit: int = 25):
        with self.connect() as con:
            return con.execute(
                """
                SELECT p.user_id,
                       COALESCE(m.ending15_count, 0) + COALESCE(m.true_ending_count, 0) AS total_clears,
                       COALESCE(m.true_ending_count, 0) AS true_endings
                FROM players p
                LEFT JOIN user_meta m ON m.user_id=p.user_id
                WHERE p.guild_id=?
                  AND COALESCE(m.ending15_count, 0) + COALESCE(m.true_ending_count, 0) > 0
                ORDER BY total_clears DESC, true_endings DESC, p.user_id ASC
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
daily_sessions: Dict[Tuple[int, int], GameSession] = {}
debug_messages = {}


def full_version_allowed(user_id: int) -> bool:
    return (DEBUG_USER_ID is not None and user_id == DEBUG_USER_ID) or db.has_full_access(user_id)


def current_character_key(guild_id: int, user_id: int) -> str:
    return db.get_run_meta(guild_id, user_id)["character_key"]


def current_character_name(guild_id: int, user_id: int) -> str:
    return CHARACTERS[current_character_key(guild_id, user_id)]["name"]


def session_character_key(session: GameSession) -> str:
    if session.character_key_override in CHARACTERS:
        return session.character_key_override
    if session.is_tutorial or not full_version_allowed(session.user_id):
        return CHARACTER_BASIC
    return current_character_key(session.guild_id, session.user_id)


def player_character_key(player: PlayerState) -> str:
    if not full_version_allowed(player.user_id):
        return CHARACTER_BASIC
    return current_character_key(player.guild_id, player.user_id)


def character_bomb_damage_bonus(session: GameSession) -> int:
    return 2 if session_character_key(session) == CHARACTER_BOMBER else 0


def character_direct_damage_bonus(session: GameSession, grade: str) -> int:
    key = session_character_key(session)
    if grade == "MISS":
        return 0
    if key == CHARACTER_GLASS:
        return 3
    if key == CHARACTER_PERFECTIONIST:
        return 3 if grade == "PERFECT" else -2
    return 0


def character_perfect_counter_bonus(session: GameSession) -> int:
    return 2 if session_character_key(session) == CHARACTER_PERFECTIONIST else 0


def bomber_bomb_gain(session: GameSession, amount: int = 1) -> int:
    if amount <= 0:
        return 0
    return amount * 2 if session_character_key(session) == CHARACTER_BOMBER else amount


def vampire_attack_heal(player: PlayerState, session: GameSession, bleed_applied: bool) -> int:
    if session_character_key(session) != CHARACTER_VAMPIRE:
        return 0
    if not bleed_applied or player.hp >= player_max_hp(player):
        return 0
    if random.random() >= 0.50:
        return 0
    before = player.hp
    player.hp = min(player_max_hp(player), player.hp + 1)
    return player.hp - before


def chaos_attack_effect(player: PlayerState, session: GameSession, enemy: Enemy, grade: str):
    if session_character_key(session) != CHARACTER_CHAOS or grade == "MISS":
        return 0, "", False, 0
    effect = random.choice(("power", "bleed", "heal"))
    if effect == "power":
        return 3, "🌀 혼돈의 검이 난폭하게 진동한다. **추가로 3 피해를 줬다!**", False, 0
    if effect == "bleed":
        return 0, "🌀 혼돈의 검이 상처를 찢어 놓는다.", True, 0
    before = player.hp
    player.hp = min(player_max_hp(player), player.hp + 1)
    healed = player.hp - before
    return 0, (f"🌀 혼돈의 검이 생기를 끌어온다. ❤️ HP가 {healed} 회복됐다!" if healed else "🌀 혼돈의 검이 생기를 끌어오려 했지만 이미 멀쩡하다."), False, healed


def character_unlocked(user_id: int, character_key: str) -> bool:
    if character_key in (CHARACTER_BASIC, CHARACTER_VAMPIRE):
        return True
    meta = db.get_user_meta(user_id)
    if character_key == CHARACTER_BOMBER:
        return meta["ending15_count"] >= 1
    if character_key == CHARACTER_SCRAPPER:
        return meta["gear_discards"] >= 30
    if character_key == CHARACTER_POT_THROWER:
        return meta["pots_broken"] >= 50
    if character_key == CHARACTER_TOMB_RAIDER:
        return meta["secrets_found"] >= 30
    if character_key == CHARACTER_PERFECTIONIST:
        return meta["perfect_count"] >= 30
    if character_key == CHARACTER_GLASS:
        return meta["flawless_true_endings"] >= 1
    if character_key == CHARACTER_CHAOS:
        completed = {
            key
            for key in db.get_discoveries(user_id, "ending15_character")
            if key in CHARACTER_ORDER and key != CHARACTER_CHAOS
        }
        return len(completed) >= 5
    return False


def character_unlock_text(user_id: int, character_key: str) -> str:
    meta = db.get_user_meta(user_id)
    if character_key in (CHARACTER_BASIC, CHARACTER_VAMPIRE):
        return "처음부터 사용 가능"
    if character_key == CHARACTER_BOMBER:
        return f"15층 엔딩 1회 · {min(meta['ending15_count'], 1)}/1"
    if character_key == CHARACTER_SCRAPPER:
        return f"장비 누적 30회 버리기 · {min(meta['gear_discards'], 30)}/30"
    if character_key == CHARACTER_POT_THROWER:
        return f"항아리 누적 50개 깨기 · {min(meta['pots_broken'], 50)}/50"
    if character_key == CHARACTER_TOMB_RAIDER:
        return f"비밀방 누적 30회 발견 · {min(meta['secrets_found'], 30)}/30"
    if character_key == CHARACTER_PERFECTIONIST:
        return f"PERFECT 누적 30회 · {min(meta['perfect_count'], 30)}/30"
    if character_key == CHARACTER_GLASS:
        return f"목숨 3개를 모두 유지한 채 30층 진엔딩 · {min(meta['flawless_true_endings'], 1)}/1"
    if character_key == CHARACTER_CHAOS:
        completed = {
            key
            for key in db.get_discoveries(user_id, "ending15_character")
            if key in CHARACTER_ORDER and key != CHARACTER_CHAOS
        }
        return f"서로 다른 캐릭터로 15층 엔딩 5회 · {min(len(completed), 5)}/5"
    return "해금 조건 미정"


def unlocked_character_keys(user_id: int):
    return [key for key in CHARACTER_ORDER if character_unlocked(user_id, key)]


def monster_catalog():
    return tuple(SHAPES.keys())


def tool_catalog():
    result = []
    for kind in ("weapon", "ring", "shield", "head"):
        result.extend(NORMAL_GEAR_NAMES[kind])
    result.extend(MAGIC_NAMES.values())
    result.append(CHAOS_SWORD.display_name())
    result.extend(UTILITY_ITEMS)
    return tuple(dict.fromkeys(result))


def discover_tool(user_id: int, name: str):
    db.discover(user_id, "tool", name)


def discover_equipped_tools(player: PlayerState):
    discover_tool(player.user_id, player.weapon.display_name())
    discover_tool(player.user_id, player.shield.display_name())
    if player.ring is not None:
        discover_tool(player.user_id, player.ring.display_name())
    if player.head is not None:
        discover_tool(player.user_id, player.head.display_name())
    if player.bombs > 0:
        discover_tool(player.user_id, "폭탄")


def reset_player_for_full_run(player: PlayerState, character_key: str, carried: Optional[Gear] = None, fake_enabled: bool = False):
    player.coins = 3
    player.bombs = 10 if character_key == CHARACTER_BOMBER else 2
    player.max_hp = 10 if character_key == CHARACTER_GLASS else 20
    player.weapon = Gear.from_json(CHAOS_SWORD.to_json()) if character_key == CHARACTER_CHAOS else Gear.from_json(START_WEAPON.to_json())
    player.ring = None
    player.shield = Gear.from_json(START_SHIELD.to_json())
    player.head = None
    if carried is not None and not (character_key == CHARACTER_CHAOS and carried.kind == "weapon"):
        equip_gear(player, Gear.from_json(carried.to_json()))
    player.hp = player_max_hp(player)
    player.last_day = today_key()
    player.status = "playing"
    player.floor_number = 1
    player.checkpoint_floor = 0
    player.lives_used = 0
    player.highest_floor = max(player.highest_floor, 1)
    db.save_player(player)
    db.set_run_meta(player.guild_id, player.user_id, character_key, carried is not None, fake_enabled)


def mark_full_run_ready(player: PlayerState):
    player.status = "ready"
    player.floor_number = 1
    player.checkpoint_floor = 0
    player.lives_used = 0
    player.last_day = today_key()
    db.save_player(player)
    db.clear_run_meta(player.guild_id, player.user_id)
    db.delete_run(player.guild_id, player.user_id)


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
        "modifier": enemy.modifier,
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
        data.get("modifier"),
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
        "flavor": room.flavor,
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
        flavor=str(data.get("flavor", "")),
    )
    return room


def player_state_data(player: Optional[PlayerState]):
    if player is None:
        return None
    return {
        "guild_id": player.guild_id,
        "user_id": player.user_id,
        "coins": player.coins,
        "bombs": player.bombs,
        "max_hp": player.max_hp,
        "hp": player.hp,
        "weapon": gear_state(player.weapon),
        "ring": gear_state(player.ring),
        "shield": gear_state(player.shield),
        "head": gear_state(player.head),
        "last_day": player.last_day,
        "status": player.status,
        "floor_number": player.floor_number,
        "highest_floor": player.highest_floor,
        "checkpoint_floor": player.checkpoint_floor,
        "lives_used": player.lives_used,
        "tutorial_completed": player.tutorial_completed,
    }


def player_from_state_data(data):
    if not data:
        return None
    weapon = gear_from_state(data.get("weapon"))
    shield = gear_from_state(data.get("shield"))
    if weapon is None or shield is None:
        raise ValueError("저장된 플레이어 장비가 올바르지 않다.")
    return PlayerState(
        guild_id=int(data["guild_id"]),
        user_id=int(data["user_id"]),
        coins=int(data.get("coins", 0)),
        bombs=int(data.get("bombs", 0)),
        max_hp=int(data.get("max_hp", 20)),
        hp=int(data.get("hp", 20)),
        weapon=weapon,
        ring=gear_from_state(data.get("ring")),
        shield=shield,
        head=gear_from_state(data.get("head")),
        last_day=str(data.get("last_day", "")),
        status=str(data.get("status", "daily")),
        floor_number=int(data.get("floor_number", 1)),
        highest_floor=int(data.get("highest_floor", 1)),
        checkpoint_floor=int(data.get("checkpoint_floor", 0)),
        lives_used=int(data.get("lives_used", 0)),
        tutorial_completed=bool(data.get("tutorial_completed", True)),
    )


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
        "carried_pot": session.carried_pot,
        "mode": session.mode,
        "character_key_override": session.character_key_override,
        "daily_rule": session.daily_rule,
        "fake_enabled": session.fake_enabled,
        "temp_player": player_state_data(session.temp_player) if session.temp_player is not None else None,
    }


def session_from_state(guild_id: int, user_id: int, raw: str):
    data = json.loads(raw)
    rooms = {}
    for room_data in data.get("rooms", []):
        room = room_from_state(room_data)
        rooms[room.pos] = room
    if not rooms:
        raise ValueError("저장된 맵에 방이 없다.")
    current = tuple(int(v) for v in data.get("current", (0, 0)))
    boss_pos = tuple(int(v) for v in data["boss_pos"])
    secret_pos = tuple(int(v) for v in data["secret_pos"])
    secret_from = tuple(int(v) for v in data["secret_from"])
    if current not in rooms or boss_pos not in rooms or secret_pos not in rooms:
        raise ValueError("저장된 맵 좌표가 올바르지 않다.")
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
        carried_pot=max(0, min(1, int(data.get("carried_pot", 0)))),
        mode=str(data.get("mode", "main")),
        character_key_override=data.get("character_key_override"),
        daily_rule=str(data.get("daily_rule", "")),
        fake_enabled=bool(data.get("fake_enabled", False)),
        temp_player=player_from_state_data(data.get("temp_player")),
    )
    room = session.room()
    if room.kind in ("normal", "boss") and not room.cleared and room.enemy is not None:
        session.phase = "battle_ready"
    return session


def persist_session(session: GameSession):
    if session.is_tutorial:
        return
    try:
        if session.is_daily:
            db.mark_expedition_activity(session.guild_id, session.user_id, "daily")
            p = session_player(session)
            db.record_daily_progress(
                session.guild_id,
                session.day_key,
                session.user_id,
                session.floor_number,
                p.coins,
                session_character_key(session),
                session.daily_rule,
            )
            raw = json.dumps(session_state(session), ensure_ascii=False, separators=(",", ":"))
            db.save_daily_run(session.guild_id, session.user_id, session.day_key, session.floor_number, raw)
            return
        if session.ended:
            db.delete_run(session.guild_id, session.user_id)
            return
        db.mark_expedition_activity(session.guild_id, session.user_id, "main")
        raw = json.dumps(session_state(session), ensure_ascii=False, separators=(",", ":"))
        db.save_run(session.guild_id, session.user_id, session.day_key, session.floor_number, raw)
    except Exception as exc:
        print(f"맵 저장에 실패했다: {type(exc).__name__}: {exc}")


def load_persisted_daily_session(guild_id: int, user_id: int, day_key: str):
    row = db.load_daily_run(guild_id, user_id)
    if row is None:
        return None
    saved_day, saved_floor, raw = row
    if saved_day != day_key:
        db.delete_daily_run(guild_id, user_id)
        return None
    try:
        session = session_from_state(guild_id, user_id, raw)
        if not session.is_daily or int(saved_floor) != int(session.floor_number):
            raise ValueError("저장된 데일리 상태가 올바르지 않다.")
        return session
    except Exception as exc:
        print(f"저장된 데일리를 불러오지 못했다: {type(exc).__name__}: {exc}")
        db.delete_daily_run(guild_id, user_id)
        return None


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
        print(f"저장된 맵을 불러오지 못했다: {type(exc).__name__}: {exc}")
        db.delete_run(guild_id, user_id)
        return None


def session_player(session: GameSession) -> PlayerState:
    if session.is_tutorial or session.is_daily:
        assert session.temp_player is not None
        return session.temp_player
    return db.get_player(session.guild_id, session.user_id)


def save_session_player(session: GameSession, player: PlayerState):
    if session.is_tutorial or session.is_daily:
        session.temp_player = player
        return
    db.save_player(player)


def remaining_lives(player: PlayerState) -> int:
    return max(0, MAX_DAILY_LIVES - player.lives_used)


def life_hearts(player: PlayerState) -> str:
    lives = max(0, min(MAX_DAILY_LIVES, remaining_lives(player)))
    return "❤️" * lives + "🖤" * (MAX_DAILY_LIVES - lives)


def session_life_hearts(player: PlayerState, session: GameSession) -> str:
    if session.is_daily and session.daily_rule == "목숨 1개":
        return "❤️" if remaining_lives(player) > 0 else "🖤"
    return life_hearts(player)


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


def stat_with_delta(current: int, projected: int) -> str:
    delta = projected - current
    return small_number(current) + (small_number(f"{delta:+d}") if delta else "")


def gear_change_summary(player: PlayerState, gear: Gear) -> str:
    current = equipped_gear(player, gear.kind)
    current_power = current.power if current else 0
    if gear.kind in ("weapon", "ring"):
        before_power = attack_power(player)
        after_power = max(0, before_power - current_power + gear.power)
        before_affinity = {color: attack_affinity(player, color) for color in COLORS}
        after_affinity = {
            color: before_affinity[color] - affinity(current, color) + affinity(gear, color)
            for color in COLORS
        }
        affinity_text = " ".join(
            f"{COLOR_MARK[color]}{stat_with_delta(before_affinity[color], after_affinity[color])}"
            for color in COLORS
        )
        return f"⚔️ {stat_with_delta(before_power, after_power)} · {affinity_text}"

    before_power = defense_power(player)
    after_power = max(0, before_power - current_power + gear.power)
    before_affinity = {color: defense_affinity(player, color) for color in COLORS}
    after_affinity = {
        color: before_affinity[color] - affinity(current, color) + affinity(gear, color)
        for color in COLORS
    }
    affinity_text = " ".join(
        f"{COLOR_MARK[color]}{stat_with_delta(before_affinity[color], after_affinity[color])}"
        for color in COLORS
    )
    before_hp = player_max_hp(player)
    current_hp_bonus = current.hp_bonus if current else 0
    after_hp = max(1, before_hp - current_hp_bonus + gear.hp_bonus)
    return (
        f"🛡️ {stat_with_delta(before_power, after_power)} · "
        f"❤️ {stat_with_delta(before_hp, after_hp)} · {affinity_text}"
    )


def room_title(session: GameSession, label: str) -> str:
    if session.is_tutorial:
        return f"0층 · 튜토리얼 · {label}"
    return f"{session.floor_number}층 · {label}"


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
        names = NORMAL_GEAR_NAMES["weapon"]
        low, high = ((5, 8) if boss_drop else (4, 6))
        power = random.randint(low, high) + floor_bonus
        hp_bonus = 0
    elif kind == "ring":
        names = NORMAL_GEAR_NAMES["ring"]
        low, high = ((2, 3) if boss_drop else (1, 3))
        power = random.randint(low, high)
        hp_bonus = 0
    elif kind == "shield":
        names = NORMAL_GEAR_NAMES["shield"]
        low, high = ((2, 4) if boss_drop else (1, 3))
        power = random.randint(low, high) + floor_bonus // 2
        hp_bonus = random.randint(*gear_hp_range("shield", floor_number))
    elif kind == "head":
        names = NORMAL_GEAR_NAMES["head"]
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
    pool = list(magic_pool_for_floor(session.floor_number))
    if session_character_key(session) == CHARACTER_CHAOS:
        pool = [effect for effect in pool if MAGIC_KINDS[effect] != "weapon"]
    effects = random.sample(pool, min(3, len(pool)))
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
    modifier = None
    if not boss and random.random() < ENEMY_MODIFIER_CHANCE:
        modifier = random.choice(ENEMY_MODIFIERS)

    return Enemy(shape, color, hp, hp, damage, boss, modifier=modifier)


def enemy_display_name(enemy: Enemy) -> str:
    parts = []
    if enemy.modifier:
        parts.append(enemy.modifier)
    parts.extend((enemy.color, enemy.shape))
    return " ".join(parts)


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


def generate_floor(guild_id: int, user_id: int, day: str, floor_number: int = 1, character_key: Optional[str] = None, fake_enabled: Optional[bool] = None, room_count: Optional[int] = None) -> GameSession:
    effective_character = character_key if character_key in CHARACTERS else (
        current_character_key(guild_id, user_id)
        if full_version_allowed(user_id)
        else CHARACTER_BASIC
    )
    effective_fake = (
        bool(fake_enabled)
        if fake_enabled is not None
        else (db.get_run_meta(guild_id, user_id)["fake_enabled"] if full_version_allowed(user_id) and character_key is None else False)
    )
    positions = {(0, 0)}
    selected_room_count = room_count if room_count is not None else (12 if random.random() < 0.25 else 8)
    target_room_count = max(2, int(selected_room_count))
    while len(positions) < target_room_count:
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
        shop_pool = list(normal_gear_kinds(floor_number))
        if effective_character == CHARACTER_CHAOS:
            shop_pool = [kind for kind in shop_pool if kind != "weapon"]
        shop_kinds = random.sample(shop_pool, min(2, len(shop_pool)))
        while shop_pool and len(shop_kinds) < 2:
            shop_kinds.append(random.choice(shop_pool))
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
        secret_revealed=effective_character == CHARACTER_TOMB_RAIDER,
        character_key_override=character_key if character_key in CHARACTERS else None,
        fake_enabled=effective_fake,
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
    return f"👾 **{enemy_display_name(enemy)}가 도망갔다!**"


def timing_windows(player: PlayerState, enemy: Enemy, kind: str):
    spec = SHAPES[enemy.shape]

    if kind == "attack":
        good = spec["attack_good"]
        critical_bonus = CRITICAL_PERFECT_WINDOW_BONUS if enemy_is_critical(enemy) else 0.0
        perfect = min(
            good,
            max(0.05, spec["attack_perfect"] + PERFECT_WINDOW_BONUS + critical_bonus),
        )
        return perfect, good

    extra = 0.05 * defense_affinity(player, enemy.color)
    good = spec["defend_good"] + extra
    perfect = min(
        good,
        max(0.05, spec["defend_perfect"] + PERFECT_WINDOW_BONUS + extra),
    )
    return perfect, good


def timing_grade(seconds: float, perfect: float, good: float):
    if seconds <= perfect:
        return "PERFECT"
    if seconds <= good:
        return "GOOD"
    return "MISS"


EMPTY_ROOM_ORDINARY = [
    "바닥에 먼지가 쌓여 있다.",
    "벽에 긁힌 자국이 있다.",
    "천장에서 물이 한 방울 떨어졌다.",
    "낡은 전선이 벽을 따라 이어져 있다.",
    "깨진 조명 하나가 천장에 매달려 있다.",
    "녹슨 나사가 하나 떨어져 있다.",
    "벽면 패널 하나가 반쯤 떨어져 있다.",
    "바닥의 금속 격자가 녹슬어 있다.",
    "찌그러진 철제 보관함이 벽에 기대어 있다.",
]

EMPTY_ROOM_LIVED_IN = [
    "누군가 여기서 잠깐 쉬었던 것 같다.",
    "벽에 오래된 낙서가 남아 있다.",
    "찌그러진 음료 캔이 구석에 굴러다닌다.",
    "철제 의자 하나가 벽을 바라보고 있다.",
    "누군가 바닥에 선을 여러 번 그었다.",
    "작은 발자국이 먼지 위에 남아 있다.",
    "벽면 패널에 오래된 테이프 자국이 남아 있다.",
    "꺼진 휴대 단말기 하나가 바닥에 놓여 있다.",
    "금속 보관함 문 안쪽에 이름 몇 개가 적혀 있다.",
]

EMPTY_ROOM_FALSE_CLUES = [
    "벽에 붉은 선이 하나 그어져 있다.",
    "바닥에 작은 금속 조각들이 원을 이루고 있다.",
    "문틀에 일정한 간격으로 홈이 세 개 나 있다.",
    "낡은 안내 패널의 글자가 모두 지워져 있다.",
    "벽면 패널에 날짜처럼 보이는 숫자가 적혀 있다.",
]

POT_ROOM_FLAVORS = [
    "검은 점토로 만들어진 항아리가 있다.",
    "금속 띠를 두른 항아리가 있다.",
    "크랩 가족이 그려진 항아리가 있다.",
]

COIN_ROOM_FLAVORS = [
    "바닥 틈에서 무언가 반짝인다.",
    "철제 패널 아래에서 코인을 발견했다.",
    "녹슨 기계 틈에 코인이 끼어 있다.",
    "금속 격자 아래로 코인이 보인다.",
    "열린 철제 보관함 안쪽에서 코인이 반짝인다.",
    "배선 덮개 틈에 코인이 끼어 있다.",
]

def empty_room_flavor() -> str:
    roll = random.random()
    if roll < 0.55:
        return "아무것도 없다."
    if roll < 0.92:
        return random.choice(EMPTY_ROOM_ORDINARY)
    if roll < 0.99:
        return random.choice(EMPTY_ROOM_LIVED_IN)
    return random.choice(EMPTY_ROOM_FALSE_CLUES)


def pot_room_flavor(room: Room) -> str:
    if room.flavor:
        return room.flavor
    room.flavor = "항아리가 있다." if random.random() < 0.80 else random.choice(POT_ROOM_FLAVORS)
    return room.flavor


def coin_room_flavor() -> str:
    if random.random() < 0.80:
        return "✨ 반짝이는 것을 주웠다."
    return random.choice(COIN_ROOM_FLAVORS)


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
    tomb_raider = session_character_key(session) == CHARACTER_TOMB_RAIDER
    visible = {
        p: room
        for p, room in session.rooms.items()
        if p != session.secret_pos or session.secret_revealed or tomb_raider
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
            mark = "B" if tomb_raider or room.visited or room.cleared else "?"
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
    return " ".join(
        f"{COLOR_MARK[color]}{small_number(gear.affinity.get(color, 0))}"
        for color in COLORS
    )


def combined_affinity_line(player: PlayerState, offensive: bool) -> str:
    return " ".join(
        f"{COLOR_MARK[color]}{small_number((attack_affinity if offensive else defense_affinity)(player, color))}"
        for color in COLORS
    )


def combat_stat_lines(player: PlayerState) -> str:
    return (
        f"⚔️ {small_number(attack_power(player))} · {combined_affinity_line(player, True)}\n"
        f"🛡️ {small_number(defense_power(player))} · {combined_affinity_line(player, False)}"
    )



def player_embed(player: PlayerState, session: GameSession, title: str, colour=None, show_resources=True):
    if session.is_tutorial and not title.startswith("0층"):
        title = f"0층 · 튜토리얼 · {title}"

    resource_line = (
        f"🪙 {small_number(player.coins)} · 💣 {small_number(player.bombs)}"
        if session.is_tutorial
        else (
            f"{session_life_hearts(player, session)} · 🪙 {small_number(player.coins)} · 💣 {small_number(player.bombs)}"
            if session.is_daily
            else f"{life_hearts(player)} · 🪙 {small_number(player.coins)} · 💣 {small_number(player.bombs)}"
        )
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
            if target == session.secret_pos and not session.rooms[target].visited:
                around.append(f"{DIR_EMOJI[direction]} **???**")
            else:
                around.append(f"{DIR_EMOJI[direction]} 문")

    if crack_here(session):
        around.append(f"{DIR_EMOJI[session.secret_direction]} **금이 간 벽**")

    if (
        session.boss_defeated
        and session.current == session.boss_pos
        and not session.is_tutorial
    ):
        if full_version_allowed(session.user_id) and session.floor_number == 30:
            around.append("📖 **진엔딩**")
        else:
            around.append(f"🪜 **{session.floor_number + 1}층**")
        if full_version_allowed(session.user_id) and session.floor_number == 15:
            around.append("📖 **엔딩** · ⛲ **환생**")

    resources = (
        f"🪙 {small_number(player.coins)} · 💣 {small_number(player.bombs)}"
        if session.is_tutorial
        else (
            f"{session_life_hearts(player, session)} · 🪙 {small_number(player.coins)} · 💣 {small_number(player.bombs)}"
            if session.is_daily
            else f"{life_hearts(player)} · 🪙 {small_number(player.coins)} · 💣 {small_number(player.bombs)}"
        )
    )
    if session.carried_pot > 0:
        resources += f" · 🏺 {small_number(session.carried_pot)}"

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
                footer_lines.append("⚠️ 튜토리얼의 아이템은 사라진다!")
        elif session.current == session.boss_pos:
            footer_lines.append("보스를 처치했다!")
            if full_version_allowed(session.user_id) and session.floor_number == 15:
                run_meta = db.get_run_meta(session.guild_id, session.user_id)
                options = "엔딩을 보거나, 16층으로 가거나 더 둘러볼 수 있다."
                if not run_meta["reincarnated"]:
                    options = "엔딩을 보거나, 환생하거나, 16층으로 갈 수 있다."
                footer_lines.append(options)
            elif full_version_allowed(session.user_id) and session.floor_number == 30:
                footer_lines.append("진엔딩을 볼 수 있다.")
            else:
                footer_lines.append(
                    f"{session.floor_number + 1}층으로 가거나 더 둘러볼 수 있다."
                )
        else:
            if full_version_allowed(session.user_id) and session.floor_number == 30:
                footer_lines.append("보스 방에서 진엔딩을 볼 수 있다.")
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
        else f"{color_icon} {enemy_display_name(enemy)}"
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
            f"⚔️ {small_number(enemy.damage)}"
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
            f"💣 {small_number(player.bombs)}"
            + (f" · 🏺 {small_number(session.carried_pot)}" if session.carried_pot > 0 else "")
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


def shop_embed(player, session, note="", footer_status=""):
    room = session.room()
    if session_character_key(session) == CHARACTER_CHAOS:
        room.shop_stock = [gear for gear in room.shop_stock if gear.kind != "weapon"]
    persist_session(session)
    embed = discord.Embed(title=room_title(session, "비밀 상점"), description=note or None)

    lines = []
    for i, gear in enumerate(room.shop_stock[:2], 1):
        if not session.is_tutorial:
            discover_tool(session.user_id, gear.display_name())
        price = gear_price(gear, session.floor_number)
        lines.append(f"{i}. 🪙 {small_number(price)} — {gear.label()}")
    price = bomb_price(session.floor_number)
    if room.bomb_stock > 0:
        lines.append(f"3. 🪙 {small_number(price)} — 💣 +¹ · 재고 {small_number(room.bomb_stock)}")
    else:
        lines.append("3. **SOLD OUT** — 폭탄")

    embed.add_field(
        name="판매 목록",
        value="\n".join(lines),
        inline=False,
    )
    if footer_status:
        embed.set_footer(text=footer_status)
    return embed


def gear_purchase_embed(player: PlayerState, session: GameSession, gear: Gear, price: int, magic_shop: bool) -> discord.Embed:
    if not session.is_tutorial:
        discover_tool(session.user_id, gear.display_name())
    title = room_title(session, "마법 상점" if magic_shop else "비밀 상점")
    embed = discord.Embed(title=title)
    current = equipped_gear(player, gear.kind)
    embed.add_field(
        name="현재 장비",
        value=current.label() if current else "없음",
        inline=False,
    )
    embed.add_field(
        name=f"새 장비 · 🪙 {small_number(price)}",
        value=gear.label(),
        inline=False,
    )
    embed.add_field(
        name="착용 시",
        value=gear_change_summary(player, gear),
        inline=False,
    )
    if magic_shop:
        embed.set_footer(text="한 가지만 살 수 있다.")
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
            f"사용 횟수: {small_number(room.slot_uses)}\n"
            f"1회 비용: 🪙 {small_number(slot_cost(room, session.floor_number))}"
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


class StatusCloseView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=900)
        self.owner_id = owner_id
        close = discord.ui.Button(
            label="닫기",
            style=discord.ButtonStyle.secondary,
        )

        async def close_callback(interaction: discord.Interaction):
            if interaction.user.id != self.owner_id:
                await interaction.response.defer()
                return
            await interaction.response.defer()
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass
            self.stop()

        close.callback = close_callback
        self.add_item(close)


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
        p = session_player(session)

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
                disabled=p.bombs <= 0,
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

            if session_character_key(session) == CHARACTER_POT_THROWER and session.carried_pot <= 0:
                take = discord.ui.Button(
                    label="항아리 줍기",
                    emoji="👐",
                    style=discord.ButtonStyle.secondary,
                )

                async def take_callback(interaction):
                    await take_pot(interaction, self.session)

                take.callback = take_callback
                self.add_item(take)

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
            elif full_version_allowed(session.user_id) and session.floor_number == 30:
                ending = discord.ui.Button(
                    label="진엔딩",
                    emoji="📖",
                    style=discord.ButtonStyle.success,
                )

                async def true_ending_callback(interaction):
                    await finish_full_ending(interaction, self.session, True)

                ending.callback = true_ending_callback
                self.add_item(ending)
            else:
                if full_version_allowed(session.user_id) and session.floor_number == 15:
                    ending = discord.ui.Button(
                        label="엔딩",
                        emoji="📖",
                        style=discord.ButtonStyle.secondary,
                    )

                    async def ending_callback(interaction):
                        await finish_full_ending(interaction, self.session, False)

                    ending.callback = ending_callback
                    self.add_item(ending)

                    reincarnated = db.get_run_meta(session.guild_id, session.user_id)["reincarnated"]
                    rebirth = discord.ui.Button(
                        label="환생 완료" if reincarnated else "환생",
                        emoji="⛲",
                        style=discord.ButtonStyle.secondary,
                        disabled=reincarnated,
                    )

                    async def rebirth_callback(interaction):
                        await open_reincarnation(interaction, self.session)

                    rebirth.callback = rebirth_callback
                    self.add_item(rebirth)

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

            if session_character_key(session) == CHARACTER_POT_THROWER:
                pot = discord.ui.Button(
                    emoji="🏺",
                    style=discord.ButtonStyle.secondary,
                    disabled=session.carried_pot <= 0,
                )

                async def pot_callback(interaction):
                    await combat_pot(interaction, self.session)

                pot.callback = pot_callback
                self.add_item(pot)

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
    if not session.is_tutorial:
        discover_tool(session.user_id, gear.display_name())
    enemy = session.room().enemy
    colour = EMBED_COLORS[enemy.color] if enemy is not None else None
    embed = discord.Embed(
        title=room_title(session, "전리품 발견"),
        colour=colour,
        description=session.pending_loot_note or None,
    )
    if session.pending_loot_footer:
        embed.set_footer(text=session.pending_loot_footer)
    current = equipped_gear(player, gear.kind)
    embed.add_field(name="현재 장비", value=current.label() if current else "없음", inline=False)
    embed.add_field(name="새 장비", value=gear.label(), inline=False)
    embed.add_field(name="착용 시", value=gear_change_summary(player, gear), inline=False)
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
                f"{gear.display_name()}{korean_josa(gear.display_name(), '을', '를')} 장착했다.",
            )

        async def skip_callback(interaction):
            p = session_player(session)
            if not session.is_tutorial:
                db.record_gear_discard(session.user_id)
            footer_status = ""
            if session_character_key(session) == CHARACTER_SCRAPPER:
                salvage = max(2, gear.power + gear.hp_bonus + sum(gear.affinity.values()))
                p.coins += salvage
                save_session_player(session, p)
                footer_status = f"🪙 코인을 {salvage}개 얻었다!"
            session.pending_loot = None
            session.pending_loot_note = ""
            session.pending_loot_footer = ""
            await show_after_clear(
                interaction,
                session,
                "새 장비를 버렸다.",
                footer_status=footer_status,
            )

        equip.callback = equip_callback
        skip.callback = skip_callback
        self.add_item(equip)
        self.add_item(skip)


class GearPurchaseConfirmView(OwnerView):
    def __init__(self, session, index: int, price: int, magic_shop: bool):
        super().__init__(session)
        self.index = index
        self.price = price
        self.magic_shop = magic_shop

        confirm = discord.ui.Button(
            label="구입 및 착용",
            emoji="✅",
            style=discord.ButtonStyle.success,
        )
        cancel = discord.ui.Button(
            label="취소",
            style=discord.ButtonStyle.secondary,
        )

        async def confirm_callback(interaction):
            if self.magic_shop:
                await confirm_magic_gear(interaction, self.session, self.index, self.price)
            else:
                await confirm_shop_gear(interaction, self.session, self.index, self.price)

        async def cancel_callback(interaction):
            p = session_player(self.session)
            if self.magic_shop:
                await interaction.response.edit_message(
                    embed=magic_shop_embed(p, self.session),
                    view=MagicShopView(self.session),
                )
            else:
                await interaction.response.edit_message(
                    embed=shop_embed(p, self.session),
                    view=ShopView(self.session),
                )

        confirm.callback = confirm_callback
        cancel.callback = cancel_callback
        self.add_item(confirm)
        self.add_item(cancel)


class MagicShopView(OwnerView):
    def __init__(self, session):
        super().__init__(session)
        p = session_player(session)

        for index, gear in enumerate(session.magic_shop_stock[:3]):
            price = magic_price(gear, session.floor_number)
            btn = discord.ui.Button(
                label=f"{index + 1}번 ({small_number(price)})",
                style=discord.ButtonStyle.success,
                disabled=session.magic_shop_used or p.coins < price,
            )

            async def callback(interaction, idx=index, cost=price):
                await buy_magic_gear(interaction, self.session, idx, cost)

            btn.callback = callback
            self.add_item(btn)

        leave = discord.ui.Button(
            label="나가기",
            emoji="↩️",
            style=discord.ButtonStyle.secondary,
        )

        async def leave_callback(interaction):
            if getattr(session, "debug_mode", False):
                await debug_return_to_panel(interaction, session)
                return
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
                label=f"{index + 1}번 ({small_number(price)})",
                style=discord.ButtonStyle.success,
                disabled=p.coins < price,
            )

            async def callback(interaction, idx=index, cost=price):
                await buy_gear(interaction, self.session, idx, cost)

            btn.callback = callback
            self.add_item(btn)

        price = bomb_price(session.floor_number)
        bomb = discord.ui.Button(
            label=f"{small_number(price)}코인" if room.bomb_stock > 0 else "SOLD OUT",
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
            if getattr(session, "debug_mode", False):
                await debug_return_to_panel(interaction, session)
                return
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
            label=f"{small_number(cost)}코인",
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
            if getattr(session, "debug_mode", False):
                await debug_return_to_panel(interaction, session)
                return
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

            is_fake = session.fake_enabled and random.random() < 0.48
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
    if not session.is_tutorial and room.kind == "pot":
        discover_tool(session.user_id, "항아리")
    if not session.is_tutorial and room.kind in ("normal", "boss") and room.enemy is not None:
        db.discover(session.user_id, "monster", room.enemy.shape)

    flee_note = flee_overpowered_enemy(session, p)
    if flee_note:
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, flee_note),
            view=ExploreView(session),
        )
        return

    if room.kind in ("normal", "boss") and not room.cleared:
        session.phase = "battle_ready"
        encounter_note = f"**{enemy_display_name(room.enemy)}**{korean_josa(enemy_display_name(room.enemy), '이', '가')} 나타났다!"
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
        amount = daily_coin_gain(session, random.randint(2, 4) + reward_bonus)
        p.coins += amount
        room.cleared = True
        save_session_player(session, p)
        session.phase = "explore"
        await interaction.response.edit_message(
            embed=exploration_embed(
                p,
                session,
                coin_room_flavor(),
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
                empty_room_flavor(),
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
                pot_room_flavor(room),
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
    if not session.is_tutorial:
        db.record_pot_break(session.user_id)
    roll = random.random()

    if roll < 0.50:
        reward_bonus = max(0, (session.floor_number - 1) // 2)
        amount = daily_coin_gain(session, random.randint(2, 5) + reward_bonus)
        p.coins += amount
        save_session_player(session, p)
        note = "🏺 항아리를 깼다! 반짝이는 것이 보인다."
        footer_status = f"🪙 코인을 {amount}개 얻었다!"
    elif roll < 0.80:
        note = "🏺 항아리를 깼다! 아무것도 없다."
        footer_status = ""
    else:
        if session_character_key(session) == CHARACTER_POT_THROWER:
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


async def take_pot(interaction, session):
    room = session.room()
    if (
        room.kind != "pot"
        or room.cleared
        or session_character_key(session) != CHARACTER_POT_THROWER
        or session.carried_pot > 0
    ):
        await interaction.response.defer()
        return
    room.cleared = True
    session.carried_pot = 1
    persist_session(session)
    await interaction.response.edit_message(
        embed=exploration_embed(
            session_player(session),
            session,
            "🏺 항아리를 하나 챙겼다.",
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
    if not session.is_tutorial:
        db.record_bomb_use(session.user_id)
        discover_tool(session.user_id, "폭탄")
    save_session_player(session, p)
    session.secret_revealed = True
    if not session.is_tutorial:
        db.record_secret_found(session.user_id)

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
    if enemy is not None and not session.is_tutorial:
        db.discover(session.user_id, "monster", enemy.shape)
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
            "**전투를 시작한다!**\n신호에 맞춰 버튼을 누르자.",
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
    if grade == "PERFECT" and not session.is_tutorial:
        db.record_perfect(session.user_id)

    if kind == "attack":
        damage = attack_damage(p, enemy, grade)
        damage += weapon_magic_damage_bonus(p, enemy, session, grade)
        damage += character_direct_damage_bonus(session, grade)
        chaos_bonus, chaos_note, chaos_bleed, chaos_healed = chaos_attack_effect(p, session, enemy, grade)
        damage = max(0, damage + chaos_bonus)
        if grade == "MISS":
            session.attack_chain = 0
        else:
            session.attack_chain += 1
        enemy.hp -= damage

        bleed_applied = False
        if grade == "PERFECT":
            note = (
                f"💥 **SMAAAASH!!**\n"
                f"`{elapsed:.2f}초` — 적에게 **{damage} 피해!**"
            )
            if enemy.hp > 0:
                apply_bleed(enemy, p)
                bleed_applied = True
                schedule_bleed(interaction, session)
        elif grade == "GOOD":
            note = f"⚔️ **HIT!** · `{elapsed:.2f}초` — 적에게 **{damage} 피해!**"
            if enemy.hp > 0 and session_character_key(session) == CHARACTER_VAMPIRE:
                apply_bleed(enemy, p)
                bleed_applied = True
                schedule_bleed(interaction, session)
        else:
            note = f"**MISS!** · `{elapsed:.2f}초` — 공격이 빗나갔다."

        if chaos_bleed and enemy.hp > 0:
            apply_bleed(enemy, p)
            schedule_bleed(interaction, session)
        if chaos_note:
            note += f"\n{chaos_note}"
        if chaos_healed > 0:
            save_session_player(session, p)

        healed = vampire_attack_heal(p, session, bleed_applied)
        if healed > 0:
            save_session_player(session, p)
            note += f"\n❤️ 흡혈로 HP가 {healed} 회복됐다!"

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
        counter = (
            PERFECT_COUNTER_DAMAGE
            + (1 if has_magic(p, "shield", MAGIC_SHIELD_COUNTER) else 0)
            + character_perfect_counter_bonus(session)
        )
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


async def combat_pot(interaction, session):
    if session.phase != "attack" or session.carried_pot <= 0:
        await interaction.response.defer()
        return

    p = session_player(session)
    enemy = session.room().enemy
    if enemy is None:
        await interaction.response.defer()
        return

    cancel_cue(session)
    session.carried_pot = 0
    if not session.is_tutorial:
        db.record_pot_break(session.user_id)
    damage = (
        random.randint(*BOMB_DAMAGE)
        + (2 if has_magic(p, "ring", MAGIC_RING_BOMB) else 0)
        + character_bomb_damage_bonus(session)
    )
    enemy.hp -= damage
    note = f"🏺 **KABOOM!!** 적에게 **{damage} 피해!**"
    persist_session(session)

    if enemy.hp <= 0:
        await enemy_defeated(interaction, session, note)
        return

    session.phase = "defend"
    await edit_interaction_message(
        interaction,
        embed=combat_embed(p, session, note + "\n\n적이 반격한다."),
        view=CombatView(session, "defend"),
    )
    schedule_cue(interaction, session, "defend")


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
    if not session.is_tutorial:
        db.record_bomb_use(session.user_id)
        discover_tool(session.user_id, "폭탄")
    save_session_player(session, p)

    damage = (
        random.randint(*BOMB_DAMAGE)
        + (2 if has_magic(p, "ring", MAGIC_RING_BOMB) else 0)
        + character_bomb_damage_bonus(session)
    )
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
    coins = daily_coin_gain(session, coins)

    p.coins += coins

    bomb_chance = (0.65 if enemy.boss else 0.45) if session_character_key(session) == CHARACTER_BOMBER else (0.40 if enemy.boss else 0.25)
    bomb_gain = bomber_bomb_gain(session, 1) if random.random() < bomb_chance else 0
    p.bombs += bomb_gain
    save_session_player(session, p)

    reward_lines = [f"🪙 코인을 {coins}개 획득했다!"]
    if bomb_gain:
        reward_lines.append(f"💣 폭탄을 {bomb_gain}개 획득했다!")
    if not session.is_tutorial and not session.hurt_this_battle and p.hp < player_max_hp(p) and random.random() < 0.33:
        before = p.hp
        p.hp = min(player_max_hp(p), p.hp + random.randint(1, 3))
        healed = p.hp - before
        reward_lines.append("자신감을 회복했다!")
        reward_lines.append(f"❤️ HP가 {healed} 회복됐다!")
        save_session_player(session, p)
    if enemy.boss and has_magic(p, "head", MAGIC_HEAD_BOSS_HEAL):
        before = p.hp
        p.hp = min(player_max_hp(p), p.hp + 2)
        healed = p.hp - before
        if healed > 0:
            reward_lines.append(f"❤️ HP가 {healed} 회복됐다!")
        save_session_player(session, p)
    if enemy.boss:
        session.boss_defeated = True
        if session.floor_number % 5 == 0 and not session.is_tutorial:
            previous_checkpoint = p.checkpoint_floor
            p.checkpoint_floor = max(p.checkpoint_floor, session.floor_number)
            save_session_player(session, p)
            if p.checkpoint_floor > previous_checkpoint:
                reward_lines.append("📝 체크포인트가 기록되었다.")
            if not (session.is_daily and session.floor_number >= DAILY_TARGET_FLOOR):
                prepare_magic_shop(session)

    reward_status = "\n".join(reward_lines)

    if session.is_daily and enemy.boss and session.floor_number >= DAILY_TARGET_FLOOR:
        await finish_daily_challenge(
            interaction,
            session,
            True,
            combat_note + "\n\n**10층의 마지막 적을 쓰러뜨렸다!**",
            footer_status=reward_status,
        )
        return

    if enemy.boss or random.random() < 0.30:
        loot_kinds = list(normal_gear_kinds(session.floor_number))
        if session_character_key(session) == CHARACTER_CHAOS:
            loot_kinds = [kind for kind in loot_kinds if kind != "weapon"]
        gear = generate_gear(
            random.choice(loot_kinds),
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
        if full_version_allowed(player.user_id):
            return note + "\n\n**눈앞이 캄캄해졌다!**\n`/게임`으로 새 탐사를 시작할 수 있다."
        return note + "\n\n**눈앞이 캄캄해졌다!**\n오늘은 더 이상 플레이할 수 없다."
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


def reset_player_after_game_over(player: PlayerState, full_access: bool):
    player.coins = 3
    player.bombs = 2
    player.max_hp = 20
    player.weapon = Gear.from_json(START_WEAPON.to_json())
    player.ring = None
    player.shield = Gear.from_json(START_SHIELD.to_json())
    player.head = None
    player.hp = player_max_hp(player)
    player.floor_number = 1
    player.checkpoint_floor = 0
    player.last_day = today_key()
    player.status = "ready" if full_access else "dead"
    player.lives_used = 0 if full_access else MAX_DAILY_LIVES
    db.save_player(player)
    db.clear_run_meta(player.guild_id, player.user_id)
    db.delete_run(player.guild_id, player.user_id)


async def player_died(interaction, session, note, footer_status=""):
    cancel_cue(session)
    cancel_bleed(session, clear=True)
    p = session_player(session)
    p.hp = 0
    if session.is_daily:
        p.lives_used += 1
        if remaining_lives(p) <= 0:
            save_session_player(session, p)
            await finish_daily_challenge(
                interaction,
                session,
                False,
                note + "\n\n**눈앞이 캄캄해졌다!**",
                footer_status=footer_status,
            )
            return
        p.hp = player_max_hp(p)
        p.status = "daily"
        restart_floor = checkpoint_start_floor(p)
        p.floor_number = restart_floor
        save_session_player(session, p)
        new_session = generate_daily_floor(
            session.guild_id,
            session.user_id,
            session.day_key,
            restart_floor,
            p,
        )
        new_session.carried_pot = session.carried_pot
        daily_sessions[(session.guild_id, session.user_id)] = new_session
        restart_note = (
            note
            + "\n\n**눈앞이 캄캄해졌다!**"
            + (
                "\n**체크포인트로 돌아왔다.**"
                if p.checkpoint_floor > 0
                else "\n1층부터 다시 시작한다."
            )
            + f"\n남은 목숨 **{remaining_lives(p)}/{MAX_DAILY_LIVES}**"
        )
        await interaction.response.edit_message(
            embed=exploration_embed(p, new_session, restart_note, footer_status=footer_status),
            view=ExploreView(new_session),
        )
        return
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
    if full_version_allowed(session.user_id):
        run_meta = db.get_run_meta(session.guild_id, session.user_id)
        db.set_run_meta(
            session.guild_id,
            session.user_id,
            run_meta["character_key"],
            run_meta["reincarnated"],
            run_meta["fake_enabled"],
            True,
        )
    save_session_player(session, p)

    final_game_over = remaining_lives(p) <= 0
    if final_game_over:
        embed = discord.Embed(title="게임 오버", description=death_description(p, note))
    else:
        embed = player_embed(p, session, "게임 오버")
        embed.description = death_description(p, note)
    if footer_status:
        embed.set_footer(text=footer_status)
    if final_game_over:
        reset_player_after_game_over(p, full_version_allowed(session.user_id))
    await interaction.response.edit_message(embed=embed, view=None)


async def player_died_background(interaction, session, note):
    cancel_cue(session)
    cancel_bleed(session, clear=True)
    p = session_player(session)
    p.hp = 0
    if session.is_daily:
        p.lives_used += 1
        if remaining_lives(p) <= 0:
            save_session_player(session, p)
            await finish_daily_challenge(
                interaction,
                session,
                False,
                note + "\n\n**눈앞이 캄캄해졌다!**",
            )
            return
        p.hp = player_max_hp(p)
        p.status = "daily"
        restart_floor = checkpoint_start_floor(p)
        p.floor_number = restart_floor
        save_session_player(session, p)
        new_session = generate_daily_floor(
            session.guild_id,
            session.user_id,
            session.day_key,
            restart_floor,
            p,
        )
        new_session.carried_pot = session.carried_pot
        daily_sessions[(session.guild_id, session.user_id)] = new_session
        restart_note = (
            note
            + "\n\n**눈앞이 캄캄해졌다!**"
            + (
                "\n**체크포인트로 돌아왔다.**"
                if p.checkpoint_floor > 0
                else "\n1층부터 다시 시작한다."
            )
            + f"\n남은 목숨 **{remaining_lives(p)}/{MAX_DAILY_LIVES}**"
        )
        await interaction.edit_original_response(
            embed=exploration_embed(p, new_session, restart_note),
            view=ExploreView(new_session),
        )
        return
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
    if full_version_allowed(session.user_id):
        run_meta = db.get_run_meta(session.guild_id, session.user_id)
        db.set_run_meta(
            session.guild_id,
            session.user_id,
            run_meta["character_key"],
            run_meta["reincarnated"],
            run_meta["fake_enabled"],
            True,
        )
    save_session_player(session, p)

    final_game_over = remaining_lives(p) <= 0
    if final_game_over:
        embed = discord.Embed(title="게임 오버", description=death_description(p, note))
    else:
        embed = player_embed(p, session, "게임 오버")
        embed.description = death_description(p, note)
    if final_game_over:
        reset_player_after_game_over(p, full_version_allowed(session.user_id))
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

    if full_version_allowed(session.user_id) and not session.is_tutorial and session.floor_number >= 30:
        p = session_player(session)
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, "더 내려갈 길은 없다. 진엔딩을 볼 수 있다."),
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

        if full_version_allowed(session.user_id):
            p.status = "ready"
            p.floor_number = 1
            p.checkpoint_floor = 0
            p.lives_used = 0
            db.save_player(p)
            db.clear_run_meta(session.guild_id, session.user_id)
            db.delete_run(session.guild_id, session.user_id)
            old = sessions.pop(key, None)
            if old:
                cancel_cue(old)
                cancel_bleed(old, clear=True)
                old.ended = True
            await interaction.response.edit_message(
                embed=character_select_embed(session.user_id),
                view=CharacterSelectView(session.guild_id, session.user_id),
            )
            return

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
                "**1층 탐사를 시작한다!**",
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

    if session.is_daily:
        new_session = generate_daily_floor(
            session.guild_id,
            session.user_id,
            session.day_key,
            p.floor_number,
            p,
        )
        daily_sessions[(session.guild_id, session.user_id)] = new_session
    else:
        new_session = generate_floor(
            session.guild_id,
            session.user_id,
            session.day_key,
            p.floor_number,
        )
        sessions[(session.guild_id, session.user_id)] = new_session
    new_session.carried_pot = session.carried_pot

    await interaction.edit_original_response(
        embed=exploration_embed(
            p,
            new_session,
            f"**{p.floor_number}층 탐사를 시작한다!**",
        ),
        view=ExploreView(new_session),
    )


def magic_shop_embed(player: PlayerState, session: GameSession, note="") -> discord.Embed:
    if session_character_key(session) == CHARACTER_CHAOS:
        session.magic_shop_stock = [gear for gear in session.magic_shop_stock if gear.kind != "weapon"]
    persist_session(session)
    embed = discord.Embed(title=room_title(session, "마법 상점"), description=note or None)
    lines = []
    for index, gear in enumerate(session.magic_shop_stock[:3], 1):
        discover_tool(session.user_id, gear.display_name())
        price = magic_price(gear, session.floor_number)
        lines.append(f"{index}. 🪙 {small_number(price)} — {gear.label()}")
    embed.add_field(
        name="판매 목록",
        value="\n".join(lines) if lines else "판매할 물건이 없다.",
        inline=False,
    )
    embed.set_footer(text="한 가지만 살 수 있다.")
    return embed


async def open_magic_shop(interaction, session):
    prepare_magic_shop(session)
    p = session_player(session)
    if not magic_shop_available(session):
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, "마법 상점은 이미 닫혔다."),
            view=ExploreView(session),
        )
        return
    await interaction.response.edit_message(
        embed=magic_shop_embed(p, session),
        view=MagicShopView(session),
    )


async def buy_magic_gear(interaction, session, index, price):
    p = session_player(session)
    if session.magic_shop_used or index >= len(session.magic_shop_stock):
        if getattr(session, "debug_mode", False):
            await debug_return_to_panel(interaction, session, "상점은 이미 닫혔다.")
            return
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, "상점은 이미 닫혔다."),
            view=ExploreView(session),
        )
        return
    gear = session.magic_shop_stock[index]
    actual_price = magic_price(gear, session.floor_number)
    if actual_price != price or p.coins < actual_price:
        await interaction.response.edit_message(
            embed=magic_shop_embed(p, session, "코인이 부족하다." if p.coins < actual_price else "가격이 바뀌었다."),
            view=MagicShopView(session),
        )
        return
    await interaction.response.edit_message(
        embed=gear_purchase_embed(p, session, gear, actual_price, True),
        view=GearPurchaseConfirmView(session, index, actual_price, True),
    )


async def confirm_magic_gear(interaction, session, index, price):
    p = session_player(session)
    if session.magic_shop_used or index >= len(session.magic_shop_stock):
        if getattr(session, "debug_mode", False):
            await debug_return_to_panel(interaction, session, "상점은 이미 닫혔다.")
            return
        await interaction.response.edit_message(
            embed=exploration_embed(p, session, "상점은 이미 닫혔다."),
            view=ExploreView(session),
        )
        return
    gear = session.magic_shop_stock[index]
    actual_price = magic_price(gear, session.floor_number)
    if actual_price != price or p.coins < actual_price:
        await interaction.response.edit_message(
            embed=magic_shop_embed(p, session, "코인이 부족하다." if p.coins < actual_price else "가격이 바뀌었다."),
            view=MagicShopView(session),
        )
        return
    p.coins -= actual_price
    equip_gear(p, gear)
    save_session_player(session, p)
    session.magic_shop_used = True
    session.magic_shop_stock.clear()
    if getattr(session, "debug_mode", False):
        await debug_return_to_panel(
            interaction,
            session,
            f"**{gear.display_name()}**{korean_josa(gear.display_name(), '을', '를')} 구입하고 장착했다.",
        )
        return
    await interaction.response.edit_message(
        embed=exploration_embed(
            p,
            session,
            f"**{gear.display_name()}**{korean_josa(gear.display_name(), '을', '를')} 구입하고 장착했다.",
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
    gear = room.shop_stock[index]
    actual_price = gear_price(gear, session.floor_number)
    if actual_price != price or p.coins < actual_price:
        await interaction.response.edit_message(
            embed=shop_embed(p, session, "코인이 부족하다." if p.coins < actual_price else "가격이 바뀌었다."),
            view=ShopView(session),
        )
        return
    await interaction.response.edit_message(
        embed=gear_purchase_embed(p, session, gear, actual_price, False),
        view=GearPurchaseConfirmView(session, index, actual_price, False),
    )


async def confirm_shop_gear(interaction, session, index, price):
    room = session.room()
    p = session_player(session)
    if index >= len(room.shop_stock):
        await interaction.response.edit_message(
            embed=shop_embed(p, session, "이미 팔렸다."),
            view=ShopView(session),
        )
        return
    gear = room.shop_stock[index]
    actual_price = gear_price(gear, session.floor_number)
    if actual_price != price or p.coins < actual_price:
        await interaction.response.edit_message(
            embed=shop_embed(p, session, "코인이 부족하다." if p.coins < actual_price else "가격이 바뀌었다."),
            view=ShopView(session),
        )
        return
    room.shop_stock.pop(index)
    p.coins -= actual_price
    equip_gear(p, gear)
    save_session_player(session, p)
    await interaction.response.edit_message(
        embed=shop_embed(
            p,
            session,
            f"**{gear.display_name()}**{korean_josa(gear.display_name(), '을', '를')} 구입하고 장착했다.",
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
    bomb_gain = bomber_bomb_gain(session, 1)
    p.bombs += bomb_gain
    room.bomb_stock -= 1
    save_session_player(session, p)

    note = (
        "💣 폭탄을 구입했다."
        if room.bomb_stock > 0
        else "💣 폭탄을 구입했다. **SOLD OUT**"
    )
    footer_status = f"💣 폭탄을 {bomb_gain}개 획득했다!"

    await interaction.response.edit_message(
        embed=shop_embed(p, session, note, footer_status=footer_status),
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
    coin_gain = 0
    footer_lines = []
    if roll < 0.36:
        note = "아무것도 안 나왔다."
    elif roll < 0.59:
        coin_gain = daily_coin_gain(session, random.randint(2, 4) + reward_bonus)
        p.coins += coin_gain
    elif roll < 0.71:
        bomb_gain = bomber_bomb_gain(session, 1)
        p.bombs += bomb_gain
        footer_lines.append(f"💣 폭탄을 {bomb_gain}개 획득했다!")
    elif roll < 0.91:
        heal = random.randint(3, 6)
        before = p.hp
        p.hp = min(player_max_hp(p), p.hp + heal)
        restored = p.hp - before
        footer_lines.append(f"❤️ HP가 {restored} 회복됐다!")
    else:
        coin_gain = daily_coin_gain(session, random.randint(6, 10) + reward_bonus * 2)
        p.coins += coin_gain
        note = "🎰 JACKPOT!!"

    if coin_gain:
        footer_lines.insert(0, f"🪙 코인을 {coin_gain}개 획득했다!")

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
    if not session.is_tutorial:
        db.record_bomb_use(session.user_id)
        discover_tool(session.user_id, "폭탄")
    room.slot_broken = True

    reward_bonus = max(0, (session.floor_number - 1) // 2)
    gain = daily_coin_gain(session, random.randint(27, 33) + reward_bonus * 2)
    p.coins += gain
    save_session_player(session, p)

    await interaction.response.edit_message(
        embed=slot_embed(
            p,
            session,
            "💣 **KABOOM!!** 동전이 쏟아진다.",
            footer_status=f"🪙 코인을 {gain}개 획득했다!",
        ),
        view=SlotView(session),
    )


SHEET_HEADERS = [
    "이름",
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
        raise RuntimeError("GOOGLE_SHEET_ID가 설정되어 있지 않다.")

    try:
        import gspread
    except ImportError as exc:
        raise RuntimeError("gspread가 설치되어 있지 않다. `pip install gspread`가 필요하다.") from exc

    if GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            credentials = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON 형식이 올바르지 않다.") from exc
        client = gspread.service_account_from_dict(credentials)
    elif GOOGLE_SERVICE_ACCOUNT_FILE:
        client = gspread.service_account(filename=GOOGLE_SERVICE_ACCOUNT_FILE)
    else:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON 또는 GOOGLE_SERVICE_ACCOUNT_FILE이 필요하다."
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
    worksheet.clear()
    worksheet.resize(rows=max(100, len(rows) + 20), cols=len(SHEET_HEADERS))
    values = [SHEET_HEADERS, *rows]
    end_row = len(values)
    worksheet.batch_update(
        [
            {
                "range": f"A1:{last_col}{end_row}",
                "values": values,
            }
        ],
        value_input_option="RAW",
    )
    worksheet.freeze(rows=1)
    return spreadsheet.url, len(rows)


def debug_allowed(interaction: discord.Interaction) -> bool:
    return DEBUG_USER_ID is not None and interaction.user.id == DEBUG_USER_ID


def status_gear_block(slot_name: str, gear: Gear) -> str:
    _, stats = gear.label().split(" | ", 1)
    return f"`{slot_name}` | `{gear.display_name()}`\n{stats}"


def add_status_fields(embed: discord.Embed, p: PlayerState):
    lives = MAX_DAILY_LIVES if p.last_day != today_key() else remaining_lives(p)
    status_hearts = "❤️" * max(0, min(MAX_DAILY_LIVES, lives)) + "🖤" * (MAX_DAILY_LIVES - max(0, min(MAX_DAILY_LIVES, lives)))
    equipment_lines = [
        status_gear_block("무기", p.weapon),
        status_gear_block("방패", p.shield),
    ]
    if p.ring is not None:
        equipment_lines.insert(1, status_gear_block("반지", p.ring))
    if p.head is not None:
        equipment_lines.append(status_gear_block("투구", p.head))
    embed.add_field(
        name="내 HP",
        value=(
            f"{hp_bar(p.hp, player_max_hp(p))} `{p.hp}/{player_max_hp(p)}`\n"
            f"{combat_stat_lines(p)}\n"
            f"{status_hearts} · 🪙 {small_number(p.coins)} · 💣 {small_number(p.bombs)}"
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
        value=f"🪜 **{p.floor_number}층** · 👑 {small_number(p.highest_floor)}",
        inline=False,
    )


def debug_panel_embed(guild_id: int, user_id: int, note: str = "") -> discord.Embed:
    p = db.get_player(guild_id, user_id)
    embed = discord.Embed(title="디버그")
    if note:
        embed.description = note
    add_status_fields(embed, p)
    embed.set_footer(text="DEBUG_USER_ID와 일치하는 계정만 사용할 수 있다.")
    return embed


async def debug_return_to_panel(interaction: discord.Interaction, session: GameSession, note: str = ""):
    await interaction.response.edit_message(
        embed=debug_panel_embed(session.guild_id, session.user_id, note),
        view=DebugView(session.user_id),
    )


def debug_stop_sessions(guild_id: int, user_id: int):
    key = (guild_id, user_id)
    old = sessions.pop(key, None)
    if old:
        cancel_cue(old)
        cancel_bleed(old, clear=True)
        old.ended = True
    old_tutorial = tutorial_sessions.pop(key, None)
    if old_tutorial:
        cancel_cue(old_tutorial)
        cancel_bleed(old_tutorial, clear=True)
        old_tutorial.ended = True
    db.delete_run(guild_id, user_id)


def debug_new_floor(guild_id: int, user_id: int, floor_number: int) -> GameSession:
    debug_stop_sessions(guild_id, user_id)
    p = db.get_player(guild_id, user_id)
    p.floor_number = floor_number
    p.last_day = today_key()
    p.status = "playing"
    p.hp = min(max(1, p.hp), player_max_hp(p))
    db.save_player(p)
    session = generate_floor(guild_id, user_id, p.last_day, floor_number)
    session.debug_mode = True
    sessions[(guild_id, user_id)] = session
    persist_session(session)
    return session


async def debug_show_floor(interaction: discord.Interaction, floor_number: int):
    session = debug_new_floor(interaction.guild_id, interaction.user.id, floor_number)
    p = session_player(session)
    await interaction.response.edit_message(
        embed=exploration_embed(p, session, f"디버그: **{floor_number}층**으로 이동했다."),
        view=ExploreView(session),
    )


async def debug_show_magic_shop(interaction: discord.Interaction, floor_number: int):
    session = debug_new_floor(interaction.guild_id, interaction.user.id, floor_number)
    p = session_player(session)
    session.boss_defeated = True
    session.current = session.boss_pos
    boss_room = session.room()
    boss_room.cleared = True
    boss_room.visited = True
    prepare_magic_shop(session)
    persist_session(session)
    await interaction.response.edit_message(
        embed=magic_shop_embed(p, session),
        view=MagicShopView(session),
    )


async def debug_show_secret_room(interaction: discord.Interaction, kind: str):
    p = db.get_player(interaction.guild_id, interaction.user.id)
    floor_number = max(1, p.floor_number)
    session = debug_new_floor(interaction.guild_id, interaction.user.id, floor_number)
    room = session.rooms[session.secret_pos]
    room.kind = kind
    room.visited = True
    room.cleared = False
    room.enemy = None
    room.slot_uses = 0
    room.slot_broken = False
    room.shop_stock = []
    room.bomb_stock = 0
    if kind == "shop":
        pool = list(normal_gear_kinds(floor_number))
        if session_character_key(session) == CHARACTER_CHAOS:
            pool = [item_kind for item_kind in pool if item_kind != "weapon"]
        kinds = random.sample(pool, min(2, len(pool)))
        while pool and len(kinds) < 2:
            kinds.append(random.choice(pool))
        room.shop_stock = [generate_gear(item_kind, floor_number=floor_number) for item_kind in kinds]
        room.bomb_stock = random.randint(1, 3)
    session.secret_revealed = True
    session.current = session.secret_pos
    persist_session(session)
    p = session_player(session)
    if kind == "shop":
        await interaction.response.edit_message(embed=shop_embed(p, session), view=ShopView(session))
    else:
        await interaction.response.edit_message(embed=slot_embed(p, session), view=SlotView(session))


class DebugFloorModal(discord.ui.Modal, title="층 이동"):
    floor_input = discord.ui.TextInput(label="층", placeholder="예: 12", max_length=4)

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        if not debug_allowed(interaction) or interaction.user.id != self.user_id or interaction.guild_id is None:
            await interaction.response.send_message("사용할 수 없는 디버그 명령이다.", ephemeral=True)
            return
        try:
            floor_number = int(str(self.floor_input.value).strip())
        except ValueError:
            await interaction.response.send_message("층에는 숫자를 입력해야 한다.", ephemeral=True)
            return
        if floor_number < 1 or floor_number > 999:
            await interaction.response.send_message("층은 1~999 사이여야 한다.", ephemeral=True)
            return
        await debug_show_floor(interaction, floor_number)


class DebugGearSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="장비 버리기 / 초기화",
            min_values=1,
            max_values=1,
            row=3,
            options=[
                discord.SelectOption(label="무기 버리기", value="weapon"),
                discord.SelectOption(label="반지 버리기", value="ring"),
                discord.SelectOption(label="방패 버리기", value="shield"),
                discord.SelectOption(label="투구 버리기", value="head"),
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        if not debug_allowed(interaction) or interaction.guild_id is None:
            await interaction.response.send_message("사용할 수 없는 디버그 명령이다.", ephemeral=True)
            return
        p = db.get_player(interaction.guild_id, interaction.user.id)
        kind = self.values[0]
        if kind == "weapon":
            p.weapon = Gear.from_json(START_WEAPON.to_json())
            note = "무기를 버리고 기본 무기로 되돌렸다."
        elif kind == "shield":
            p.shield = Gear.from_json(START_SHIELD.to_json())
            note = "방패를 버리고 기본 방패로 되돌렸다."
        elif kind == "ring":
            p.ring = None
            note = "반지를 버렸다."
        else:
            p.head = None
            note = "투구를 버렸다."
        p.hp = min(p.hp, player_max_hp(p))
        db.save_player(p)
        await interaction.response.edit_message(
            embed=debug_panel_embed(interaction.guild_id, interaction.user.id, note),
            view=DebugView(interaction.user.id),
        )


class DebugView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=900)
        self.user_id = user_id
        actions = [
            ("층 이동", None, discord.ButtonStyle.primary, 0, "floor"),
            ("5층 마법상점", "🔮", discord.ButtonStyle.secondary, 0, "magic5"),
            ("10층 마법상점", "🔮", discord.ButtonStyle.secondary, 0, "magic10"),
            ("비밀 상점", "💰", discord.ButtonStyle.secondary, 0, "shop"),
            ("슬롯머신", "🎰", discord.ButtonStyle.secondary, 0, "slot"),
            ("코인 0", "🪙", discord.ButtonStyle.secondary, 1, "coin0"),
            ("코인 +10", "🪙", discord.ButtonStyle.secondary, 1, "coin10"),
            ("폭탄 0", "💣", discord.ButtonStyle.secondary, 1, "bomb0"),
            ("폭탄 +10", "💣", discord.ButtonStyle.secondary, 1, "bomb10"),
            ("HP -1", None, discord.ButtonStyle.secondary, 2, "hpminus"),
            ("HP +1", None, discord.ButtonStyle.secondary, 2, "hpplus"),
            ("HP 회복", "❤️", discord.ButtonStyle.secondary, 2, "hpfull"),
            ("오늘 리셋", "🔄", discord.ButtonStyle.danger, 2, "dailyreset"),
        ]
        for label, emoji, style, row, action in actions:
            button = discord.ui.Button(label=label, emoji=emoji, style=style, row=row)

            async def callback(interaction, selected_action=action):
                await self.run_action(interaction, selected_action)

            button.callback = callback
            self.add_item(button)
        self.add_item(DebugGearSelect())
        close = discord.ui.Button(
            label="닫기",
            style=discord.ButtonStyle.secondary,
            row=4,
        )

        async def close_callback(interaction):
            message = debug_messages.pop(self.user_id, None)
            await interaction.response.defer()
            if message is not None:
                try:
                    await message.delete()
                    return
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass
            try:
                await interaction.delete_original_response()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                if interaction.message is not None:
                    try:
                        await interaction.message.delete()
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        pass

        close.callback = close_callback
        self.add_item(close)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id or not debug_allowed(interaction):
            if not interaction.response.is_done():
                await interaction.response.send_message("사용할 수 없는 디버그 명령이다.", ephemeral=True)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        message = f"디버그 동작 오류: `{type(error).__name__}: {error}`"
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def run_action(self, interaction: discord.Interaction, action: str):
        if interaction.guild_id is None:
            await interaction.response.send_message("서버 안에서만 사용할 수 있다.", ephemeral=True)
            return
        if action == "floor":
            await interaction.response.send_modal(DebugFloorModal(self.user_id))
            return
        if action == "magic5":
            await debug_show_magic_shop(interaction, 5)
            return
        if action == "magic10":
            await debug_show_magic_shop(interaction, 10)
            return
        if action == "shop":
            await debug_show_secret_room(interaction, "shop")
            return
        if action == "slot":
            await debug_show_secret_room(interaction, "slot")
            return

        p = db.get_player(interaction.guild_id, interaction.user.id)
        note = ""
        if action == "coin0":
            p.coins = 0
            note = "코인을 0으로 만들었다."
        elif action == "coin10":
            p.coins += 10
            note = "코인을 10개 추가했다."
        elif action == "bomb0":
            p.bombs = 0
            note = "폭탄을 0으로 만들었다."
        elif action == "bomb10":
            p.bombs += 10
            note = "폭탄을 10개 추가했다."
        elif action == "hpminus":
            p.hp = max(1, p.hp - 1)
            note = "HP를 1 줄였다."
        elif action == "hpplus":
            p.hp = min(player_max_hp(p), p.hp + 1)
            note = "HP를 1 늘렸다."
        elif action == "hpfull":
            p.hp = player_max_hp(p)
            note = "HP를 전부 회복했다."
        elif action == "dailyreset":
            debug_stop_sessions(interaction.guild_id, interaction.user.id)
            db.test_reset(interaction.guild_id, interaction.user.id)
            await interaction.response.edit_message(
                embed=debug_panel_embed(interaction.guild_id, interaction.user.id, "오늘의 플레이 제한과 현재 진행을 초기화했다."),
                view=DebugView(self.user_id),
            )
            return
        db.save_player(p)
        await interaction.response.edit_message(
            embed=debug_panel_embed(interaction.guild_id, interaction.user.id, note),
            view=DebugView(self.user_id),
        )


async def require_full_version(interaction: discord.Interaction) -> bool:
    if full_version_allowed(interaction.user.id):
        return True
    message = "🔒 풀 버전 기능이다. `/풀버전`으로 풀 버전을 해금할 수 있다."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
    return False


class FullAccessModal(discord.ui.Modal, title="풀 버전 인증"):
    password = discord.ui.TextInput(
        label="비밀번호",
        placeholder="비밀번호 입력",
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if full_version_allowed(interaction.user.id):
            await interaction.response.send_message("이미 풀 버전이 해금되어 있다.", ephemeral=True)
            return
        if not FULL_VERSION_PASSWORD:
            await interaction.response.send_message("풀 버전 비밀번호가 아직 설정되어 있지 않다.", ephemeral=True)
            return
        if str(self.password.value) != FULL_VERSION_PASSWORD:
            await interaction.response.send_message("비밀번호가 맞지 않다.", ephemeral=True)
            return
        db.grant_full_access(interaction.user.id)
        await interaction.response.send_message("✅ 풀 버전이 해금되었다!", ephemeral=True)


def character_select_embed(user_id: int, selected_key: str = CHARACTER_BASIC, fake_enabled: bool = False) -> discord.Embed:
    if selected_key not in CHARACTERS or not character_unlocked(user_id, selected_key):
        selected_key = CHARACTER_BASIC
    info = CHARACTERS[selected_key]
    embed = discord.Embed(
        title="탐사 준비",
        description=(
            f"캐릭터 · `{info['name']}`\n"
            f"페이크 · `{'사용' if fake_enabled else '사용 안 함'}`\n"
            f"{info['description']}\n\n"
            f"{info['ability']}"
        ),
    )
    embed.set_footer(text="해금 조건과 기록은 /도감에서 확인할 수 있다.")
    return embed


async def start_full_run(interaction: discord.Interaction, character_key: str, fake_enabled: bool):
    if not await require_full_version(interaction):
        return
    if interaction.guild_id is None:
        await interaction.response.send_message("서버 안에서만 사용할 수 있다.", ephemeral=True)
        return
    if not character_unlocked(interaction.user.id, character_key):
        await interaction.response.send_message("아직 해금되지 않은 캐릭터다.", ephemeral=True)
        return
    key = (interaction.guild_id, interaction.user.id)
    old = sessions.pop(key, None)
    if old:
        cancel_cue(old)
        cancel_bleed(old, clear=True)
        old.ended = True
    db.delete_run(interaction.guild_id, interaction.user.id)
    p = db.get_player(interaction.guild_id, interaction.user.id)
    reset_player_for_full_run(p, character_key, fake_enabled=fake_enabled)
    discover_equipped_tools(p)
    session = generate_floor(interaction.guild_id, interaction.user.id, today_key(), 1)
    sessions[key] = session
    db.mark_expedition_activity(interaction.guild_id, interaction.user.id, "main")
    await interaction.response.edit_message(
        embed=exploration_embed(
            p,
            session,
            f"`{CHARACTERS[character_key]['name']}`으로 **1층 탐사를 시작한다!**",
        ),
        view=ExploreView(session),
    )


class CharacterSelectView(discord.ui.View):
    def __init__(self, guild_id: int, user_id: int, selected_key: str = CHARACTER_BASIC, fake_enabled: bool = False):
        super().__init__(timeout=900)
        self.guild_id = guild_id
        self.user_id = user_id
        self.selected_key = selected_key if character_unlocked(user_id, selected_key) else CHARACTER_BASIC
        self.fake_enabled = fake_enabled
        options = [
            discord.SelectOption(
                label=CHARACTERS[key]["name"],
                value=key,
                description=CHARACTERS[key]["description"][:100],
                default=key == self.selected_key,
            )
            for key in unlocked_character_keys(user_id)
        ]
        select = discord.ui.Select(
            placeholder="캐릭터 선택",
            options=options,
            min_values=1,
            max_values=1,
        )
        fake_toggle = discord.ui.Button(
            label=f"페이크: {'ON' if self.fake_enabled else 'OFF'}",
            style=discord.ButtonStyle.secondary,
        )
        start = discord.ui.Button(
            label="탐사 시작",
            emoji="🪜",
            style=discord.ButtonStyle.success,
        )
        close = discord.ui.Button(
            label="닫기",
            style=discord.ButtonStyle.secondary,
        )

        async def select_callback(interaction: discord.Interaction):
            self.selected_key = select.values[0]
            for option in select.options:
                option.default = option.value == self.selected_key
            await interaction.response.edit_message(
                embed=character_select_embed(self.user_id, self.selected_key, self.fake_enabled),
                view=self,
            )

        async def fake_callback(interaction: discord.Interaction):
            self.fake_enabled = not self.fake_enabled
            fake_toggle.label = f"페이크: {'ON' if self.fake_enabled else 'OFF'}"
            await interaction.response.edit_message(
                embed=character_select_embed(self.user_id, self.selected_key, self.fake_enabled),
                view=self,
            )

        async def start_callback(interaction: discord.Interaction):
            await start_full_run(interaction, self.selected_key, self.fake_enabled)

        async def close_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass
            self.stop()

        select.callback = select_callback
        fake_toggle.callback = fake_callback
        start.callback = start_callback
        close.callback = close_callback
        self.add_item(select)
        self.add_item(fake_toggle)
        self.add_item(start)
        self.add_item(close)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id or interaction.guild_id != self.guild_id:
            await interaction.response.defer()
            return False
        return True


def ending_result_embed(user_id: int, character_key: str, floor_number: int, true_ending: bool, newly_unlocked):
    title = "30층 · 진엔딩" if true_ending else "15층 · 엔딩"
    embed = discord.Embed(
        title=title,
        description="**탐사를 끝냈다.**\n\n엔딩 스토리는 아직 준비 중이다.",
    )
    embed.add_field(
        name="결과",
        value=(
            f"캐릭터 · `{CHARACTERS.get(character_key, CHARACTERS[CHARACTER_BASIC])['name']}`\n"
            f"🪜 **{floor_number}층**"
        ),
        inline=False,
    )
    if newly_unlocked:
        names = " · ".join(f"`{CHARACTERS[key]['name']}`" for key in newly_unlocked)
        embed.add_field(name="🔓 캐릭터 해금", value=names, inline=False)
    embed.set_footer(text="엔딩 기록이 도감에 추가되었다.")
    return embed


async def finish_full_ending(interaction: discord.Interaction, session: GameSession, true_ending: bool):
    if not await require_full_version(interaction):
        return
    target_floor = 30 if true_ending else 15
    if session.is_tutorial or session.floor_number != target_floor or not session.boss_defeated or session.current != session.boss_pos:
        await interaction.response.defer()
        return
    before = {key for key in CHARACTER_ORDER if character_unlocked(session.user_id, key)}
    character_key = current_character_key(session.guild_id, session.user_id)
    p = session_player(session)
    db.record_ending(session.user_id, true_ending=true_ending)
    if not true_ending:
        db.discover(session.user_id, "ending15_character", character_key)
    run_meta = db.get_run_meta(session.guild_id, session.user_id)
    if true_ending and p.lives_used == 0 and not run_meta["died_once"]:
        db.record_flawless_true_ending(session.user_id)
    after = {key for key in CHARACTER_ORDER if character_unlocked(session.user_id, key)}
    newly_unlocked = [key for key in CHARACTER_ORDER if key in after and key not in before]
    p.highest_floor = max(p.highest_floor, target_floor)
    session.ended = True
    persist_session(session)
    key = (session.guild_id, session.user_id)
    if sessions.get(key) is session:
        sessions.pop(key, None)
    mark_full_run_ready(p)
    await interaction.response.edit_message(
        embed=ending_result_embed(session.user_id, character_key, target_floor, true_ending, newly_unlocked),
        view=StatusCloseView(session.user_id),
    )


def reincarnation_embed(player: PlayerState, session: GameSession, selected_kind: Optional[str] = None) -> discord.Embed:
    embed = discord.Embed(
        title="15층 · 환생하는 분수",
        description="현재 장비 하나를 가지고 1층으로 돌아간다.",
    )
    equipped = [
        ("weapon", "무기", player.weapon),
        ("ring", "반지", player.ring),
        ("shield", "방패", player.shield),
        ("head", "투구", player.head),
    ]
    lines = []
    for kind, slot, gear in equipped:
        if gear is None:
            continue
        marker = "→ " if kind == selected_kind else ""
        lines.append(f"{marker}`{slot}` · {gear.label()}")
    embed.add_field(name="계승할 장비", value="\n".join(lines), inline=False)
    embed.set_footer(text="한 탐사에 한 번만 환생할 수 있다.")
    return embed


async def perform_reincarnation(interaction: discord.Interaction, session: GameSession, selected_kind: str):
    if not await require_full_version(interaction):
        return
    if session.floor_number != 15 or not session.boss_defeated or session.current != session.boss_pos:
        await interaction.response.defer()
        return
    run_meta = db.get_run_meta(session.guild_id, session.user_id)
    if run_meta["reincarnated"]:
        await interaction.response.edit_message(
            embed=exploration_embed(session_player(session), session, "이 탐사에서는 이미 환생했다."),
            view=ExploreView(session),
        )
        return
    p = session_player(session)
    gear = equipped_gear(p, selected_kind)
    if gear is None:
        await interaction.response.send_message("계승할 장비가 없다.", ephemeral=True)
        return
    carried = Gear.from_json(gear.to_json())
    character_key = run_meta["character_key"]
    session.ended = True
    persist_session(session)
    reset_player_for_full_run(p, character_key, carried=carried, fake_enabled=run_meta["fake_enabled"])
    db.set_run_meta(
        session.guild_id,
        session.user_id,
        character_key,
        True,
        run_meta["fake_enabled"],
        run_meta["died_once"],
    )
    discover_tool(p.user_id, carried.display_name())
    new_session = generate_floor(session.guild_id, session.user_id, today_key(), 1)
    sessions[(session.guild_id, session.user_id)] = new_session
    await interaction.response.edit_message(
        embed=exploration_embed(
            p,
            new_session,
            f"⛲ `{carried.display_name()}`{korean_josa(carried.display_name(), '을', '를')} 가지고 **1층으로 환생했다.**",
        ),
        view=ExploreView(new_session),
    )


async def open_reincarnation(interaction: discord.Interaction, session: GameSession):
    if not await require_full_version(interaction):
        return
    run_meta = db.get_run_meta(session.guild_id, session.user_id)
    if run_meta["reincarnated"]:
        await interaction.response.edit_message(
            embed=exploration_embed(session_player(session), session, "이 탐사에서는 이미 환생했다."),
            view=ExploreView(session),
        )
        return
    p = session_player(session)
    await interaction.response.edit_message(
        embed=reincarnation_embed(p, session),
        view=ReincarnationView(session),
    )


class ReincarnationView(OwnerView):
    def __init__(self, session: GameSession):
        super().__init__(session, timeout=900)
        self.selected_kind = None
        p = session_player(session)
        equipped = [
            ("weapon", "무기", p.weapon),
            ("ring", "반지", p.ring),
            ("shield", "방패", p.shield),
            ("head", "투구", p.head),
        ]
        select = discord.ui.Select(
            placeholder="계승할 장비 선택",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=f"{slot} · {gear.display_name()}",
                    value=kind,
                )
                for kind, slot, gear in equipped
                if gear is not None and not (session_character_key(session) == CHARACTER_CHAOS and kind == "weapon")
            ],
        )
        confirm = discord.ui.Button(
            label="환생",
            emoji="⛲",
            style=discord.ButtonStyle.success,
            disabled=True,
        )
        cancel = discord.ui.Button(
            label="취소",
            style=discord.ButtonStyle.secondary,
        )

        async def select_callback(interaction: discord.Interaction):
            self.selected_kind = select.values[0]
            confirm.disabled = False
            await interaction.response.edit_message(
                embed=reincarnation_embed(session_player(self.session), self.session, self.selected_kind),
                view=self,
            )

        async def confirm_callback(interaction: discord.Interaction):
            if self.selected_kind is None:
                await interaction.response.defer()
                return
            await perform_reincarnation(interaction, self.session, self.selected_kind)

        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(
                embed=exploration_embed(session_player(self.session), self.session),
                view=ExploreView(self.session),
            )

        select.callback = select_callback
        confirm.callback = confirm_callback
        cancel.callback = cancel_callback
        self.add_item(select)
        self.add_item(confirm)
        self.add_item(cancel)


def collection_embed(guild_id: int, user_id: int, category: str = "overview") -> discord.Embed:
    if category in ("characters", "endings") and not full_version_allowed(user_id):
        title = "도감 · 캐릭터" if category == "characters" else "도감 · 엔딩"
        return discord.Embed(title=title, description="데모 버전에서는 확인할 수 없습니다.")
    p = db.get_player(guild_id, user_id)
    discover_equipped_tools(p)
    meta = db.get_user_meta(user_id)
    monsters = monster_catalog()
    tools = tool_catalog()
    seen_monsters = db.get_discoveries(user_id, "monster")
    seen_tools = db.get_discoveries(user_id, "tool")
    unlocked = [key for key in CHARACTER_ORDER if character_unlocked(user_id, key)]
    if category == "characters":
        embed = discord.Embed(title="도감 · 캐릭터")
        lines = []
        for key in CHARACTER_ORDER:
            info = CHARACTERS[key]
            if key in unlocked:
                lines.append(
                    f"✅ `{info['name']}`\n"
                    f"{info['description']}\n"
                    f"{info['ability']}"
                )
            else:
                lines.append(
                    f"🔒 `???`\n"
                    f"해금: {character_unlock_text(user_id, key)}"
                )
        embed.description = "\n\n".join(lines)
        return embed
    if category == "monsters":
        embed = discord.Embed(title="도감 · 몬스터")
        lines = [f"✅ {name}" if name in seen_monsters else "???" for name in monsters]
        embed.description = "\n".join(lines) if lines else "등록된 몬스터가 없다."
        embed.set_footer(text=f"{len(seen_monsters.intersection(monsters))}/{len(monsters)} 발견")
        return embed
    if category == "tools":
        embed = discord.Embed(title="도감 · 도구")
        lines = [f"✅ {name}" if name in seen_tools else "???" for name in tools]
        embed.description = "\n".join(lines) if lines else "등록된 도구가 없다."
        embed.set_footer(text=f"{len(seen_tools.intersection(tools))}/{len(tools)} 발견")
        return embed
    if category == "endings":
        embed = discord.Embed(title="도감 · 엔딩")
        ending15 = "✅" if meta["ending15_count"] > 0 else "🔒"
        true_mark = "✅" if meta["true_ending_count"] > 0 else "🔒"
        embed.description = (
            f"{ending15} **15층 엔딩** · {meta['ending15_count']}회\n"
            f"{true_mark} **진엔딩** · {meta['true_ending_count']}회"
        )
        return embed
    embed = discord.Embed(title="도감")
    embed.description = (
        f"🧑 캐릭터 · {len(unlocked)}/{len(CHARACTER_ORDER)}\n"
        f"👾 몬스터 · {len(seen_monsters.intersection(monsters))}/{len(monsters)}\n"
        f"🧰 도구 · {len(seen_tools.intersection(tools))}/{len(tools)}\n"
        f"📖 15층 엔딩 · {meta['ending15_count']}회\n"
        f"📕 진엔딩 · {meta['true_ending_count']}회"
    )
    return embed


class CollectionView(discord.ui.View):
    def __init__(self, guild_id: int, user_id: int, category: str = "overview"):
        super().__init__(timeout=900)
        self.guild_id = guild_id
        self.user_id = user_id
        select = discord.ui.Select(
            placeholder="도감 분류",
            options=[
                discord.SelectOption(label="전체", value="overview", emoji="📚", default=category == "overview"),
                discord.SelectOption(label="캐릭터", value="characters", emoji="🧑", default=category == "characters"),
                discord.SelectOption(label="몬스터", value="monsters", emoji="👾", default=category == "monsters"),
                discord.SelectOption(label="도구", value="tools", emoji="🧰", default=category == "tools"),
                discord.SelectOption(label="엔딩", value="endings", emoji="📖", default=category == "endings"),
            ],
        )
        close = discord.ui.Button(label="닫기", style=discord.ButtonStyle.secondary)

        async def select_callback(interaction: discord.Interaction):
            selected = select.values[0]
            await interaction.response.edit_message(
                embed=collection_embed(self.guild_id, self.user_id, selected),
                view=CollectionView(self.guild_id, self.user_id, selected),
            )

        async def close_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass
            self.stop()

        select.callback = select_callback
        close.callback = close_callback
        self.add_item(select)
        self.add_item(close)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id or interaction.guild_id != self.guild_id:
            await interaction.response.defer()
            return False
        return True


def daily_profile(day_key: str):
    parsed = datetime.strptime(day_key, "%Y-%m-%d").date()
    ordinal = parsed.toordinal()
    block_size = len(CHARACTER_ORDER)
    block = ordinal // block_size
    index = ordinal % block_size

    def raw_block_order(block_number: int):
        order = list(CHARACTER_ORDER)
        random.Random(0xD4117 + block_number * 7919).shuffle(order)
        return order

    def block_order(block_number: int):
        order = raw_block_order(block_number)
        previous = raw_block_order(block_number - 1)
        if order[0] == previous[-1] and len(order) > 1:
            order[0], order[1] = order[1], order[0]
        return order

    order = block_order(block)

    seed = int(day_key.replace("-", ""))
    rule = random.Random(seed ^ 0x5F3759DF).choice(DAILY_RULES)
    return {
        "seed": seed,
        "character_key": order[index],
        "rule": rule,
        "target_floor": DAILY_TARGET_FLOOR,
    }


def daily_rule_description(rule: str) -> str:
    return {
        "큰 맵": "모든 층의 맵이 12개의 방으로 생성된다.",
        "목숨 1개": "목숨이 1개뿐이다. 죽으면 오늘의 도전이 끝난다.",
    }.get(rule, "특별한 규칙이 적용된다.")


def make_daily_player(guild_id: int, user_id: int, character_key: str, day_key: str, rule: str) -> PlayerState:
    max_hp = 10 if character_key == CHARACTER_GLASS else 20
    return PlayerState(
        guild_id=guild_id,
        user_id=user_id,
        coins=3,
        bombs=10 if character_key == CHARACTER_BOMBER else 2,
        max_hp=max_hp,
        hp=max_hp,
        weapon=Gear.from_json(CHAOS_SWORD.to_json()) if character_key == CHARACTER_CHAOS else Gear.from_json(START_WEAPON.to_json()),
        ring=None,
        shield=Gear.from_json(START_SHIELD.to_json()),
        head=None,
        last_day=day_key,
        status="daily",
        floor_number=1,
        highest_floor=1,
        checkpoint_floor=0,
        lives_used=2 if rule == "목숨 1개" else 0,
        tutorial_completed=True,
    )


def generate_daily_floor(guild_id: int, user_id: int, day_key: str, floor_number: int, player: PlayerState) -> GameSession:
    profile = daily_profile(day_key)
    rng_state = random.getstate()
    try:
        random.seed(profile["seed"] * 1009 + floor_number * 9176)
        session = generate_floor(
            guild_id,
            user_id,
            day_key,
            floor_number,
            character_key=profile["character_key"],
            fake_enabled=False,
            room_count=12 if profile["rule"] == "큰 맵" else 8,
        )
        session.mode = "daily"
        session.character_key_override = profile["character_key"]
        session.daily_rule = profile["rule"]
        session.temp_player = player
        return session
    finally:
        random.setstate(rng_state)


def daily_coin_gain(session: GameSession, amount: int) -> int:
    return amount


def daily_ranking_lines(guild: Optional[discord.Guild], day_key: str, limit: int = 10):
    if guild is None:
        return ["랭킹을 불러올 수 없다."]
    rows = db.daily_ranking(guild.id, day_key, limit)
    if not rows:
        return ["아직 기록이 없다."]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = []
    for rank, (user_id, floor_number, coins, completed, finished) in enumerate(rows, 1):
        member = guild.get_member(int(user_id))
        name = member.display_name if member else f"<@{user_id}>"
        rank_mark = medals.get(rank, f"{rank}.")
        result = "✅ **10층 클리어**" if completed else f"🪜 **{floor_number}층**"
        if not finished and not completed:
            result += " · 진행 중"
        lines.append(f"{rank_mark} {name} — {result} · 🪙 {small_number(coins)}")
    return lines


def daily_embed(day_key: str, user_id: int, guild: Optional[discord.Guild] = None) -> discord.Embed:
    profile = daily_profile(day_key)
    character_key = profile["character_key"]
    character = CHARACTERS[character_key]["name"] if character_unlocked(user_id, character_key) else "???"
    record = db.get_daily_record(guild.id, day_key, user_id) if guild is not None else None
    if record is None:
        state = "아직 도전하지 않았다."
    elif record["completed"]:
        state = f"✅ **10층 클리어** · 🪙 {small_number(record['coins'])}"
    elif record["finished"]:
        state = f"도전 종료 · 🪜 **{record['floor_number']}층** · 🪙 {small_number(record['coins'])}"
    else:
        state = f"진행 중 · 🪜 **{record['floor_number']}층** · 🪙 {small_number(record['coins'])}"

    embed = discord.Embed(
        title=f"오늘의 탐사 · {day_key[5:].replace('-', '/')}",
        description=state,
    )
    embed.add_field(name="오늘의 캐릭터", value=f"`{character}`", inline=False)
    embed.add_field(
        name="오늘의 규칙",
        value=f"`{profile['rule']}`\n{daily_rule_description(profile['rule'])}",
        inline=False,
    )
    embed.add_field(name="목표", value="🪜 **10층**", inline=False)
    embed.set_footer(text="하루 한 번 도전할 수 있다. 날짜가 바뀌면 캐릭터와 규칙도 바뀐다.")
    return embed


async def finish_daily_challenge(interaction: discord.Interaction, session: GameSession, completed: bool, note: str = "", footer_status: str = ""):
    p = session_player(session)
    session.ended = True
    cancel_cue(session)
    cancel_bleed(session, clear=True)
    db.record_daily_progress(
        session.guild_id,
        session.day_key,
        session.user_id,
        session.floor_number,
        p.coins,
        session_character_key(session),
        session.daily_rule,
        completed=completed,
        finished=True,
    )
    db.delete_daily_run(session.guild_id, session.user_id)
    daily_sessions.pop((session.guild_id, session.user_id), None)
    title = "오늘의 탐사 · 클리어" if completed else "오늘의 탐사 · 종료"
    description = note or ("10층의 마지막 적을 쓰러뜨렸다." if completed else "이번 도전은 여기까지다.")
    embed = discord.Embed(title=title, description=description)
    embed.add_field(
        name="기록",
        value=(
            f"{'✅ **10층 클리어**' if completed else f'🪜 **{session.floor_number}층**'}\n"
            f"🪙 {small_number(p.coins)}"
        ),
        inline=False,
    )
    if footer_status:
        embed.set_footer(text=footer_status)
    await edit_interaction_message(
        interaction,
        embed=embed,
        view=DailyResultView(session.guild_id, session.user_id, session.day_key),
    )


class DailyResultView(discord.ui.View):
    def __init__(self, guild_id: int, user_id: int, day_key: str):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.user_id = user_id
        self.day_key = day_key
        close = discord.ui.Button(label="닫기", style=discord.ButtonStyle.secondary)

        async def close_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass
            self.stop()

        close.callback = close_callback
        self.add_item(close)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id or interaction.guild_id != self.guild_id:
            await interaction.response.defer()
            return False
        return True


class DailyLobbyView(discord.ui.View):
    def __init__(self, guild_id: int, user_id: int, day_key: str):
        super().__init__(timeout=900)
        self.guild_id = guild_id
        self.user_id = user_id
        self.day_key = day_key
        record = db.get_daily_record(guild_id, day_key, user_id)
        key = (guild_id, user_id)
        active = daily_sessions.get(key)
        if active is not None and active.day_key != day_key:
            cancel_cue(active)
            cancel_bleed(active, clear=True)
            active.ended = True
            daily_sessions.pop(key, None)
            active = None
        if active is None:
            active = load_persisted_daily_session(guild_id, user_id, day_key)
        if active is not None:
            daily_sessions[key] = active
        if record is None or (record is not None and not record["finished"]):
            start = discord.ui.Button(
                label="계속" if active is not None else "시작",
                emoji="▶️",
                style=discord.ButtonStyle.success,
            )

            async def start_callback(interaction: discord.Interaction):
                await start_or_continue_daily(interaction, self.day_key)

            start.callback = start_callback
            self.add_item(start)
        close = discord.ui.Button(label="닫기", style=discord.ButtonStyle.secondary)

        async def close_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass
            self.stop()

        close.callback = close_callback
        self.add_item(close)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id or interaction.guild_id != self.guild_id:
            await interaction.response.defer()
            return False
        return True


async def start_or_continue_daily(interaction: discord.Interaction, day_key: str):
    if interaction.guild_id is None or day_key != today_key():
        await interaction.response.edit_message(
            embed=daily_embed(today_key(), interaction.user.id, interaction.guild),
            view=DailyLobbyView(interaction.guild_id, interaction.user.id, today_key()) if interaction.guild_id else None,
        )
        return
    guild_id = interaction.guild_id
    user_id = interaction.user.id
    record = db.get_daily_record(guild_id, day_key, user_id)
    if record is not None and record["finished"]:
        await interaction.response.edit_message(
            embed=daily_embed(day_key, user_id, interaction.guild),
            view=DailyLobbyView(guild_id, user_id, day_key),
        )
        return
    key = (guild_id, user_id)
    session = daily_sessions.get(key)
    if session is None or session.ended or session.day_key != day_key:
        session = load_persisted_daily_session(guild_id, user_id, day_key)
    if session is None:
        profile = daily_profile(day_key)
        player = make_daily_player(guild_id, user_id, profile["character_key"], day_key, profile["rule"])
        session = generate_daily_floor(guild_id, user_id, day_key, 1, player)
        db.record_daily_progress(
            guild_id,
            day_key,
            user_id,
            1,
            player.coins,
            profile["character_key"],
            profile["rule"],
        )
    daily_sessions[key] = session
    db.mark_expedition_activity(guild_id, user_id, "daily")
    p = session_player(session)
    room = session.room()
    if room.kind in ("normal", "boss") and not room.cleared:
        session.phase = "battle_ready"
        embed = combat_embed(p, session, "")
        view = BattleStartView(session)
    elif room.kind == "shop":
        embed = shop_embed(p, session)
        view = ShopView(session)
    elif room.kind == "slot":
        embed = slot_embed(p, session)
        view = SlotView(session)
    else:
        embed = exploration_embed(p, session, "**오늘의 탐사를 시작한다.**" if session.floor_number == 1 and session.current == (0, 0) else "")
        view = ExploreView(session)
    await interaction.response.edit_message(embed=embed, view=view)


def forfeit_embed(player: PlayerState, character_key: str, mode: str) -> discord.Embed:
    is_daily = mode == "daily"
    embed = discord.Embed(
        title="탐사 포기",
        description="**데일리 탐사를 포기합니다.**" if is_daily else "**메인 탐사를 포기합니다.**",
    )
    if is_daily:
        embed.add_field(
            name="현재 탐사",
            value=f"🪜 **{player.floor_number}층** · 🪙 {small_number(player.coins)}",
            inline=False,
        )
        embed.set_footer(text="포기하면 오늘은 다시 데일리에 도전할 수 없다.")
    else:
        if full_version_allowed(player.user_id):
            embed.add_field(
                name="현재 탐사",
                value=(
                    f"캐릭터 · `{CHARACTERS.get(character_key, CHARACTERS[CHARACTER_BASIC])['name']}`\n"
                    f"🪜 **{player.floor_number}층** · 👑 {small_number(player.highest_floor)}"
                ),
                inline=False,
            )
            embed.set_footer(text="도감과 해금 기록은 유지된다.")
        else:
            embed.add_field(
                name="현재 탐사",
                value=f"🪜 **{player.floor_number}층** · 🪙 {small_number(player.coins)}",
                inline=False,
            )
            embed.set_footer(text="포기하면 오늘은 더 이상 탐사할 수 없다.")
    return embed


def daily_forfeit_state(guild_id: int, user_id: int):
    day_key = today_key()
    record = db.get_daily_record(guild_id, day_key, user_id)
    if record is None or record["finished"]:
        return None, None
    key = (guild_id, user_id)
    session = daily_sessions.get(key)
    if session is not None and (session.ended or session.day_key != day_key):
        cancel_cue(session)
        cancel_bleed(session, clear=True)
        daily_sessions.pop(key, None)
        session = None
    if session is None:
        session = load_persisted_daily_session(guild_id, user_id, day_key)
        if session is not None:
            daily_sessions[key] = session
    return record, session


async def perform_main_forfeit(interaction: discord.Interaction, guild_id: int, user_id: int):
    p = db.get_player(guild_id, user_id)
    full_access = full_version_allowed(user_id)
    character_key = current_character_key(guild_id, user_id)
    key = (guild_id, user_id)
    old = sessions.pop(key, None)
    if old:
        cancel_cue(old)
        cancel_bleed(old, clear=True)
        old.ended = True
    if full_access:
        mark_full_run_ready(p)
        description = (
            f"`{CHARACTERS.get(character_key, CHARACTERS[CHARACTER_BASIC])['name']}`의 탐사를 포기했다.\n"
            "`/게임`으로 새 탐사를 시작할 수 있다."
        )
    else:
        reset_player_after_game_over(p, False)
        description = "탐사를 포기했다.\n오늘은 더 이상 탐사할 수 없다."
    await interaction.response.edit_message(
        embed=discord.Embed(title="탐사 포기", description=description),
        view=StatusCloseView(user_id),
    )


async def perform_daily_forfeit(interaction: discord.Interaction, guild_id: int, user_id: int):
    day_key = today_key()
    record, session = daily_forfeit_state(guild_id, user_id)
    if record is None:
        await interaction.response.edit_message(
            embed=discord.Embed(title="탐사 포기", description="진행 중인 데일리 탐사가 없다."),
            view=StatusCloseView(user_id),
        )
        return
    if session is not None:
        p = session_player(session)
        floor_number = session.floor_number
        coins = p.coins
        character_key = session_character_key(session)
        rule = session.daily_rule
        session.ended = True
        cancel_cue(session)
        cancel_bleed(session, clear=True)
    else:
        floor_number = record["floor_number"]
        coins = record["coins"]
        character_key = record["character_key"]
        rule = record["rule"]
    db.record_daily_progress(
        guild_id,
        day_key,
        user_id,
        floor_number,
        coins,
        character_key,
        rule,
        completed=False,
        finished=True,
    )
    db.delete_daily_run(guild_id, user_id)
    daily_sessions.pop((guild_id, user_id), None)
    await interaction.response.edit_message(
        embed=discord.Embed(
            title="탐사 포기",
            description="데일리 탐사를 포기했다.\n오늘은 다시 데일리에 도전할 수 없다.",
        ),
        view=StatusCloseView(user_id),
    )


class ForfeitConfirmView(discord.ui.View):
    def __init__(self, guild_id: int, user_id: int, mode: str):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.user_id = user_id
        self.mode = mode
        confirm = discord.ui.Button(label="포기", style=discord.ButtonStyle.danger)
        cancel = discord.ui.Button(label="취소", style=discord.ButtonStyle.secondary)

        async def confirm_callback(interaction: discord.Interaction):
            if self.mode == "daily":
                await perform_daily_forfeit(interaction, self.guild_id, self.user_id)
            else:
                await perform_main_forfeit(interaction, self.guild_id, self.user_id)

        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass
            self.stop()

        confirm.callback = confirm_callback
        cancel.callback = cancel_callback
        self.add_item(confirm)
        self.add_item(cancel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id or interaction.guild_id != self.guild_id:
            await interaction.response.defer()
            return False
        return True


def daily_forfeit_player(guild_id: int, user_id: int, record, session):
    if session is not None:
        return session_player(session), session_character_key(session)
    player = PlayerState(
        guild_id=guild_id,
        user_id=user_id,
        coins=record["coins"],
        bombs=0,
        max_hp=20,
        hp=20,
        weapon=Gear.from_json(START_WEAPON.to_json()),
        ring=None,
        shield=Gear.from_json(START_SHIELD.to_json()),
        head=None,
        last_day=today_key(),
        status="daily",
        floor_number=record["floor_number"],
        highest_floor=record["floor_number"],
        checkpoint_floor=0,
        lives_used=0,
        tutorial_completed=True,
    )
    return player, record["character_key"]


intents = discord.Intents.default()


class ShapeGameBot(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync()


bot = ShapeGameBot(command_prefix="!", intents=intents)


@bot.tree.command(name="풀버전", description="풀 버전 비밀번호를 입력한다.")
async def full_version_auth(interaction: discord.Interaction):
    if full_version_allowed(interaction.user.id):
        await interaction.response.send_message("이미 풀 버전이 해금되어 있다.", ephemeral=True)
        return
    if not FULL_VERSION_PASSWORD:
        await interaction.response.send_message("풀 버전 비밀번호가 아직 설정되어 있지 않다.", ephemeral=True)
        return
    await interaction.response.send_modal(FullAccessModal())


@bot.tree.command(name="디버그", description="개발자용 테스트 패널을 연다.")
async def debug_command(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message("서버 안에서만 사용할 수 있다.", ephemeral=True)
        return
    if not debug_allowed(interaction):
        await interaction.response.send_message("사용할 수 없는 디버그 명령이다.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        old_message = debug_messages.pop(interaction.user.id, None)
        if old_message is not None:
            try:
                await old_message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        embed = debug_panel_embed(interaction.guild_id, interaction.user.id)
        view = DebugView(interaction.user.id)
        message = await interaction.edit_original_response(embed=embed, view=view)
        debug_messages[interaction.user.id] = message
    except Exception as exc:
        await interaction.edit_original_response(
            content=f"디버그 패널 오류: `{type(exc).__name__}: {exc}`",
            embed=None,
            view=None,
        )


@bot.tree.command(name="게임", description="탐사를 시작하거나 이어서 진행한다.")
async def game(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있다.",
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


    if full_version_allowed(user_id) and p.status == "ready":
        await interaction.response.send_message(
            embed=character_select_embed(user_id),
            view=CharacterSelectView(guild_id, user_id),
            ephemeral=True,
        )
        return

    if full_version_allowed(user_id) and p.last_day != today:
        p.last_day = today
        db.save_player(p)

    if p.last_day != today:
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
        db.mark_expedition_activity(guild_id, user_id, "main")

        start_note = (
            f"**체크포인트로 돌아왔다.**\n남은 목숨 `{MAX_DAILY_LIVES}/{MAX_DAILY_LIVES}`"
            if p.checkpoint_floor > 0
            else f"**1층 탐사를 시작한다!**\n남은 목숨 `{MAX_DAILY_LIVES}/{MAX_DAILY_LIVES}`"
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
            if not full_version_allowed(user_id):
                await interaction.response.send_message(
                    "오늘은 더 이상 플레이할 수 없다.",
                    ephemeral=True,
                )
                return
            reset_player_after_game_over(p, True)
            await interaction.response.send_message(
                embed=character_select_embed(user_id),
                view=CharacterSelectView(guild_id, user_id),
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
        db.mark_expedition_activity(guild_id, user_id, "main")
        restart_note = (
            f"**체크포인트로 돌아왔다.**\n남은 목숨 `{remaining_lives(p)}/{MAX_DAILY_LIVES}`"
            if p.checkpoint_floor > 0
            else (
                "**다시 도전하자!**\n"
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
        db.mark_expedition_activity(guild_id, user_id, "main")
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
    db.mark_expedition_activity(guild_id, user_id, "main")

    await interaction.response.send_message(
        embed=exploration_embed(
            p,
            session,
            f"**{p.floor_number}층 탐색을 재개했다!**",
        ),
        view=ExploreView(session),
        ephemeral=True,
    )


@bot.tree.command(name="도감", description="도감을 확인한다.")
async def collection_command(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message("서버 안에서만 사용할 수 있다.", ephemeral=True)
        return
    await interaction.response.send_message(
        embed=collection_embed(interaction.guild_id, interaction.user.id),
        view=CollectionView(interaction.guild_id, interaction.user.id),
        ephemeral=True,
    )


@bot.tree.command(name="데일리", description="오늘의 데일리 챌린지를 확인한다.")
async def daily_command(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message("서버 안에서만 사용할 수 있다.", ephemeral=True)
        return
    if not await require_full_version(interaction):
        return
    day_key = today_key()
    await interaction.response.send_message(
        embed=daily_embed(day_key, interaction.user.id, interaction.guild),
        view=DailyLobbyView(interaction.guild_id, interaction.user.id, day_key),
        ephemeral=True,
    )



@bot.tree.command(name="포기", description="현재 탐사를 포기한다.")
async def forfeit_command(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message("서버 안에서만 사용할 수 있다.", ephemeral=True)
        return
    guild_id = interaction.guild_id
    user_id = interaction.user.id
    p = db.get_player(guild_id, user_id)
    main_active = p.status in ("playing", "dead") and not (p.status == "dead" and p.lives_used >= MAX_DAILY_LIVES)
    daily_record, daily_session = daily_forfeit_state(guild_id, user_id)
    daily_active = daily_record is not None
    if not main_active and not daily_active:
        await interaction.response.send_message("진행 중인 탐사가 없다.", ephemeral=True)
        return

    if main_active and daily_active:
        target_mode = db.get_last_expedition_mode(guild_id, user_id)
        if target_mode not in ("main", "daily"):
            target_mode = "daily"
    elif daily_active:
        target_mode = "daily"
    else:
        target_mode = "main"

    if target_mode == "daily":
        player, character_key = daily_forfeit_player(guild_id, user_id, daily_record, daily_session)
        await interaction.response.send_message(
            embed=forfeit_embed(player, character_key, "daily"),
            view=ForfeitConfirmView(guild_id, user_id, "daily"),
            ephemeral=True,
        )
        return

    character_key = current_character_key(guild_id, user_id)
    await interaction.response.send_message(
        embed=forfeit_embed(p, character_key, "main"),
        view=ForfeitConfirmView(guild_id, user_id, "main"),
        ephemeral=True,
    )


@bot.tree.command(name="튜토리얼", description="튜토리얼")
async def tutorial(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있다.",
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


@bot.tree.command(name="상태", description="현재 장비와 자원을 확인한다.")
async def status(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있다.",
            ephemeral=True,
        )
        return

    p = db.get_player(interaction.guild_id, interaction.user.id)
    embed = discord.Embed(title=f"{interaction.user.display_name} — 상태")
    expedition_ended = p.status == "ready" or (p.status == "dead" and p.lives_used >= MAX_DAILY_LIVES)
    if expedition_ended:
        embed.description = "지금은 진행 중인 탐사가 없다!"
    else:
        add_status_fields(embed, p)
        embed.set_footer(text=f"{p.last_day or '미시작'} · {p.status}")
    await interaction.response.send_message(
        embed=embed,
        view=StatusCloseView(interaction.user.id),
        ephemeral=True,
    )


def ranking_name(guild: discord.Guild, user_id: int) -> str:
    member = guild.get_member(int(user_id))
    return member.display_name if member else f"<@{user_id}>"


def ranked_lines(rows, guild: discord.Guild, kind: str):
    if not rows:
        return ["아직 기록이 없다."]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = []
    for rank, row in enumerate(rows, 1):
        rank_mark = medals.get(rank, f"{rank}.")
        name = ranking_name(guild, int(row[0]))
        if kind == "daily":
            _, floor_number, coins, completed, finished = row
            result = "✅ **10층 클리어**" if completed else f"🪜 **{floor_number}층**"
            if not finished and not completed:
                result += " · 진행 중"
            lines.append(f"{rank_mark} {name} — {result} · 🪙 {small_number(coins)}")
        elif kind == "clears":
            _, total_clears, _ = row
            lines.append(f"{rank_mark} {name} — 🏁 **{total_clears}회**")
        else:
            _, floor_number, coins = row
            lines.append(f"{rank_mark} {name} — 🪜 **{floor_number}층** · 🪙 {small_number(coins)}")
    return lines


def full_leaderboard_embed(guild: discord.Guild, mode: str = "overview") -> discord.Embed:
    day_key = today_key()
    if mode == "daily":
        rows = db.daily_ranking(guild.id, day_key, 25)
        return discord.Embed(
            title="순위표 · 데일리",
            description="\n".join(ranked_lines(rows, guild, "daily")),
        )
    if mode == "clears":
        rows = db.total_clear_ranking(guild.id, 25)
        return discord.Embed(
            title="순위표 · 총 클리어",
            description="\n".join(ranked_lines(rows, guild, "clears")),
        )
    daily_rows = db.daily_ranking(guild.id, day_key, 5)
    clear_rows = db.total_clear_ranking(guild.id, 5)
    embed = discord.Embed(title="순위표")
    embed.add_field(
        name="오늘의 데일리",
        value="\n".join(ranked_lines(daily_rows, guild, "daily")),
        inline=False,
    )
    embed.add_field(
        name="총 클리어",
        value="\n".join(ranked_lines(clear_rows, guild, "clears")),
        inline=False,
    )
    return embed


class LeaderboardView(discord.ui.View):
    def __init__(self, guild_id: int, mode: str = "overview"):
        super().__init__(timeout=900)
        self.guild_id = guild_id
        self.mode = mode
        overview = discord.ui.Button(
            label="요약",
            style=discord.ButtonStyle.primary if mode == "overview" else discord.ButtonStyle.secondary,
            disabled=mode == "overview",
        )
        daily = discord.ui.Button(
            label="데일리",
            style=discord.ButtonStyle.primary if mode == "daily" else discord.ButtonStyle.secondary,
            disabled=mode == "daily",
        )
        clears = discord.ui.Button(
            label="총 클리어",
            style=discord.ButtonStyle.primary if mode == "clears" else discord.ButtonStyle.secondary,
            disabled=mode == "clears",
        )

        async def switch(interaction: discord.Interaction, next_mode: str):
            if interaction.guild is None or interaction.guild_id != self.guild_id:
                await interaction.response.defer()
                return
            await interaction.response.edit_message(
                embed=full_leaderboard_embed(interaction.guild, next_mode),
                view=LeaderboardView(self.guild_id, next_mode),
            )

        async def overview_callback(interaction: discord.Interaction):
            await switch(interaction, "overview")

        async def daily_callback(interaction: discord.Interaction):
            await switch(interaction, "daily")

        async def clears_callback(interaction: discord.Interaction):
            await switch(interaction, "clears")

        overview.callback = overview_callback
        daily.callback = daily_callback
        clears.callback = clears_callback
        self.add_item(overview)
        self.add_item(daily)
        self.add_item(clears)


@bot.tree.command(name="랭킹", description="순위를 확인한다.")
async def leaderboard(interaction: discord.Interaction):
    if interaction.guild_id is None or interaction.guild is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있다.",
            ephemeral=True,
        )
        return

    if full_version_allowed(interaction.user.id):
        embed = full_leaderboard_embed(interaction.guild)
        view = LeaderboardView(interaction.guild_id)
    else:
        rows = db.leaderboard(interaction.guild_id)
        embed = discord.Embed(
            title="진행 순위",
            description="\n".join(ranked_lines(rows, interaction.guild, "progress")) if rows else "아직 기록이 없다.",
        )
        view = None

    old_message_id = db.get_channel_ui_message(
        interaction.guild_id,
        interaction.channel_id,
        "leaderboard",
    )
    channel = interaction.channel
    if old_message_id is not None and channel is not None and hasattr(channel, "get_partial_message"):
        try:
            await channel.get_partial_message(old_message_id).delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()
    db.set_channel_ui_message(
        interaction.guild_id,
        interaction.channel_id,
        "leaderboard",
        message.id,
    )


@bot.tree.command(name="주기", description="플레이어에게 아이템을 지급한다.")
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
            "서버 안에서만 사용할 수 있다.",
            ephemeral=True,
        )
        return

    is_owner = interaction.guild.owner_id == interaction.user.id
    is_admin = interaction.user.guild_permissions.administrator
    if not (is_owner or is_admin):
        await interaction.response.send_message(
            "서버 주인 또는 관리자만 사용할 수 있다.",
            ephemeral=True,
        )
        return

    if 수량 < 1:
        await interaction.response.send_message(
            "수량은 1 이상이어야 한다.",
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
                "장비는 한 번에 1개만 지급할 수 있다.",
                ephemeral=True,
            )
            return
        if 위력 is not None and 위력 < 0:
            await interaction.response.send_message(
                "위력은 0 이상이어야 한다.",
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
            "알 수 없는 아이템이다.",
            ephemeral=True,
        )
        return

    db.save_player(p)
    await interaction.response.send_message(
        f"{대상.mention}에게 {result}{korean_josa(result, '을', '를')} 지급했다.",
        ephemeral=True,
    )


@bot.tree.command(
    name="시트업데이트",
    description="모든 플레이어의 진행 상황을 구글 시트에 업데이트한다.",
)
async def sheet_update(interaction: discord.Interaction):
    if interaction.guild_id is None or interaction.guild is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있다.",
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
                name = "알 수 없는 플레이어"

        lives = (
            MAX_DAILY_LIVES
            if p.last_day != today_key()
            else remaining_lives(p)
        )
        sheet_rows.append(
            [
                name,
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
            content=f"시트 업데이트에 실패했다.\n`{type(exc).__name__}: {exc}`"
        )
        return

    await interaction.edit_original_response(
        content=(
            f"구글 시트를 업데이트했다. **{count}명**의 진행 상황을 반영했다.\n"
            f"탭: `{worksheet_title}`\n"
            f"{sheet_url}"
        )
    )



if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN이 없다. `.env.example`을 복사해 `.env`를 만든 뒤 토큰을 넣어야 한다."
        )

    bot.run(TOKEN)
