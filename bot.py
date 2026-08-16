from __future__ import annotations

import asyncio
import json
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


# ============================================================
# 설정
# ============================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")
KST = ZoneInfo("Asia/Seoul")
DB_PATH = Path(__file__).with_name("game.db")

COLORS = ("시안", "마젠타", "옐로")
COLOR_MARK = {"시안": "C", "마젠타": "M", "옐로": "Y"}

# 모양 자체가 공격 템포를 결정합니다.
SHAPES = {
    "정육면체": {
        "symbol": "■",
        "hp": (9, 13),
        "damage": (4, 6),
        "attack_perfect": 0.58,
        "attack_good": 1.12,
        "dodge_perfect": 0.62,
        "dodge_good": 1.20,
        "cue_delay": (1.4, 3.0),
        "coin_drop": (2, 4),
    },
    "원기둥": {
        "symbol": "▣",
        "hp": (7, 11),
        "damage": (3, 5),
        "attack_perfect": 0.46,
        "attack_good": 0.92,
        "dodge_perfect": 0.50,
        "dodge_good": 0.96,
        "cue_delay": (1.0, 2.6),
        "coin_drop": (2, 5),
    },
    "원뿔": {
        "symbol": "▲",
        "hp": (5, 9),
        "damage": (3, 5),
        "attack_perfect": 0.36,
        "attack_good": 0.76,
        "dodge_perfect": 0.38,
        "dodge_good": 0.80,
        "cue_delay": (0.8, 2.2),
        "coin_drop": (3, 5),
    },
}

DIRECTIONS = {
    "북": (0, -1),
    "동": (1, 0),
    "남": (0, 1),
    "서": (-1, 0),
}


# ============================================================
# 데이터
# ============================================================

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
            pips.append(f"{COLOR_MARK[color]}{'●' * n if n else '○'}")
        stat = "공격" if self.kind == "weapon" else "방어"
        return f"{self.name} | {stat} {self.power} | {' '.join(pips)}"

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
    "weapon", "기본 해머", 4, {"시안": 1, "마젠타": 0, "옐로": 0}
)
START_ARMOR = Gear(
    "armor", "기본 보호구", 1, {"시안": 0, "마젠타": 1, "옐로": 0}
)


@dataclass
class Enemy:
    shape: str
    color: str
    hp: int
    max_hp: int
    damage: int
    boss: bool = False

    @property
    def symbol(self) -> str:
        return SHAPES[self.shape]["symbol"]


@dataclass
class Room:
    pos: Tuple[int, int]
    kind: str = "normal"  # start, normal, boss, shop, slot
    visited: bool = False
    cleared: bool = False
    enemy: Optional[Enemy] = None
    shop_stock: list[Gear] = field(default_factory=list)
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


@dataclass
class GameSession:
    guild_id: int
    user_id: int
    day_key: str
    rooms: Dict[Tuple[int, int], Room]
    current: Tuple[int, int]
    boss_pos: Tuple[int, int]
    secret_pos: Tuple[int, int]
    secret_from: Tuple[int, int]
    secret_direction: str
    secret_revealed: bool = False
    boss_defeated: bool = False
    ended: bool = False
    phase: str = "explore"  # explore/player_turn/enemy_turn/timing_wait
    cue_started: Optional[float] = None
    cue_kind: Optional[str] = None

    def room(self) -> Room:
        return self.rooms[self.current]


# ============================================================
# DB
# ============================================================

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
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )

    def get_player(self, guild_id: int, user_id: int) -> PlayerState:
        with self.connect() as con:
            row = con.execute(
                """
                SELECT guild_id, user_id, coins, bombs, max_hp, hp,
                       weapon_json, armor_json, last_day, status
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
                     weapon_json, armor_json, last_day, status)
                    VALUES (?, ?, 3, 2, 20, 20, ?, ?, '', 'ready')
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
        )

    def save_player(self, p: PlayerState):
        with self.connect() as con:
            con.execute(
                """
                UPDATE players
                SET coins=?, bombs=?, max_hp=?, hp=?,
                    weapon_json=?, armor_json=?, last_day=?, status=?
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
                    p.guild_id,
                    p.user_id,
                ),
            )
            con.commit()

    def leaderboard(self, guild_id: int, limit: int = 10):
        with self.connect() as con:
            return con.execute(
                """
                SELECT user_id, coins
                FROM players
                WHERE guild_id=?
                ORDER BY coins DESC, user_id ASC
                LIMIT ?
                """,
                (guild_id, limit),
            ).fetchall()

    def test_reset(self, guild_id: int, user_id: int):
        p = self.get_player(guild_id, user_id)
        p.hp = p.max_hp
        p.last_day = ""
        p.status = "ready"
        self.save_player(p)


db = Database(DB_PATH)
sessions: Dict[Tuple[int, int], GameSession] = {}


# ============================================================
# 랜덤 생성
# ============================================================

def today_key() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def add_pos(a, b):
    return a[0] + b[0], a[1] + b[1]


def random_affinity(min_points=1, max_points=3):
    result = {c: 0 for c in COLORS}
    for _ in range(random.randint(min_points, max_points)):
        choices = [c for c in COLORS if result[c] < 2]
        result[random.choice(choices)] += 1
    return result


def generate_gear(kind: str, boss_drop=False) -> Gear:
    if kind == "weapon":
        names = ["절단기", "충격봉", "압축 해머", "펄스 블레이드"]
        power = random.randint(5, 7 if not boss_drop else 9)
    else:
        names = ["충격 조끼", "반응 장갑", "복합 장갑", "공진 보호구"]
        power = random.randint(1, 3 if not boss_drop else 4)

    return Gear(
        kind=kind,
        name=random.choice(names),
        power=power,
        affinity=random_affinity(
            2 if boss_drop else 1,
            4 if boss_drop else 3,
        ),
    )


def make_enemy(boss=False) -> Enemy:
    shape = random.choice(tuple(SHAPES))
    color = random.choice(COLORS)
    spec = SHAPES[shape]

    hp = random.randint(*spec["hp"])
    damage = random.randint(*spec["damage"])

    if boss:
        hp = round(hp * random.uniform(2.2, 2.7))
        damage += random.randint(1, 2)

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


def generate_floor(guild_id: int, user_id: int, day: str) -> GameSession:
    # 시작방 포함 공개 방 8개.
    positions = {(0, 0)}
    while len(positions) < 8:
        anchor = random.choice(tuple(positions))
        delta = random.choice(tuple(DIRECTIONS.values()))
        positions.add(add_pos(anchor, delta))

    distances = bfs_distances(positions)
    boss_pos = max(distances, key=distances.get)

    rooms: Dict[Tuple[int, int], Room] = {}

    for pos in positions:
        if pos == (0, 0):
            rooms[pos] = Room(pos, "start", visited=True, cleared=True)
        elif pos == boss_pos:
            rooms[pos] = Room(pos, "boss", enemy=make_enemy(True))
        else:
            # 적은 방마다 독립적으로 랜덤 생성
            rooms[pos] = Room(pos, "normal", enemy=make_enemy(False))

    # 빈 인접칸 하나를 비밀방으로 선택
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
        # 상점 장비도 매 층 랜덤
        secret.shop_stock = [
            generate_gear("weapon"),
            generate_gear("armor"),
        ]

    rooms[secret_pos] = secret

    return GameSession(
        guild_id=guild_id,
        user_id=user_id,
        day_key=day,
        rooms=rooms,
        current=(0, 0),
        boss_pos=boss_pos,
        secret_pos=secret_pos,
        secret_from=secret_from,
        secret_direction=secret_direction,
    )


# ============================================================
# 계산
# ============================================================

def hp_bar(current: int, maximum: int, width=10):
    filled = round(width * max(0, current) / max(1, maximum))
    return "█" * filled + "░" * (width - filled)


def affinity(gear: Gear, color: str) -> int:
    return gear.affinity.get(color, 0)


def attack_damage(player: PlayerState, enemy: Enemy, grade: str) -> int:
    timing_mult = {"PERFECT": 1.40, "GOOD": 1.0, "MISS": 0.30}[grade]
    color_mult = 1.0 + 0.25 * affinity(player.weapon, enemy.color)
    return max(1, round(player.weapon.power * timing_mult * color_mult))


def incoming_damage(player: PlayerState, enemy: Enemy, grade: str) -> int:
    if grade == "PERFECT":
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
        return spec["attack_perfect"], spec["attack_good"]

    # 해당 색에 강한 방어구일수록 회피 허용 시간이 약간 늘어남
    extra = 0.05 * affinity(player.armor, enemy.color)
    return spec["dodge_perfect"] + extra, spec["dodge_good"] + extra


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
        east = add_pos(pos, DIRECTIONS["동"])
        south = add_pos(pos, DIRECTIONS["남"])

        if east in visible:
            ex, _ = cv(east)
            for xx in range(x + 1, ex):
                canvas[y][xx] = "─"

        if south in visible:
            _, sy = cv(south)
            canvas[y + 1][x] = "│"

    return "\n".join("".join(row).rstrip() for row in canvas)


# ============================================================
# Embed
# ============================================================

def player_embed(player: PlayerState, session: GameSession, title: str):
    embed = discord.Embed(title=title)
    embed.add_field(
        name="상태",
        value=(
            f"HP `{player.hp}/{player.max_hp}` {hp_bar(player.hp, player.max_hp)}\n"
            f"코인 `{player.coins}` · 폭탄 `{player.bombs}`"
        ),
        inline=False,
    )
    embed.add_field(name="무기", value=player.weapon.label(), inline=False)
    embed.add_field(name="방어구", value=player.armor.label(), inline=False)
    return embed


def exploration_embed(player, session, note=""):
    room = session.room()
    embed = player_embed(player, session, room_name(room))
    if note:
        embed.description = note

    embed.add_field(
        name="맵",
        value=(
            f"```text\n{map_ascii(session)}\n```\n"
            "`@` 현재 · `·` 클리어 · `?` 미탐색 · `B` 보스 · `S` 비밀"
        ),
        inline=False,
    )

    around = [f"{direction}: 문" for direction, _ in accessible_directions(session)]
    if crack_here(session):
        around.append(f"{session.secret_direction}: **금이 간 벽**")

    embed.add_field(
        name="주변",
        value="\n".join(around) if around else "막다른 방입니다.",
        inline=False,
    )

    if session.boss_defeated:
        embed.set_footer(
            text="보스를 처치했습니다. 오늘을 끝내거나 남은 방을 더 탐색할 수 있습니다."
        )
    return embed


def combat_embed(player, session, note=""):
    enemy = session.room().enemy
    assert enemy is not None

    prefix = "보스 " if enemy.boss else ""
    embed = player_embed(
        player,
        session,
        f"{prefix}{enemy.color} {enemy.shape} {enemy.symbol}",
    )
    if note:
        embed.description = note
    embed.add_field(
        name="적",
        value=(
            f"HP `{max(0, enemy.hp)}/{enemy.max_hp}` "
            f"{hp_bar(max(0, enemy.hp), enemy.max_hp)}\n"
            f"공격력 `{enemy.damage}`"
        ),
        inline=False,
    )
    return embed


def timing_embed(player, session, kind):
    enemy = session.room().enemy
    assert enemy is not None
    action = "공격" if kind == "attack" else "회피"

    embed = combat_embed(
        player,
        session,
        f"## 지금! — {action} 버튼을 누르세요.",
    )
    perfect, good = timing_windows(player, enemy, kind)
    embed.add_field(
        name="현재 판정창",
        value=f"PERFECT ≤ `{perfect:.2f}s` · GOOD ≤ `{good:.2f}s`",
        inline=False,
    )
    return embed


def shop_embed(player, session, note=""):
    room = session.room()
    embed = player_embed(player, session, "비밀 상점")
    if note:
        embed.description = note

    lines = []
    for i, gear in enumerate(room.shop_stock[:2], 1):
        price = 6 if gear.kind == "weapon" else 5
        lines.append(f"{i}. `{price}코인` — {gear.label()}")
    lines.append("3. `3코인` — 폭탄 +1")

    embed.add_field(
        name="판매 목록",
        value="\n".join(lines),
        inline=False,
    )
    embed.set_footer(text="코인이 곧 순위이므로 구매하면 점수판의 코인 수도 줄어듭니다.")
    return embed


def slot_embed(player, session, note=""):
    room = session.room()
    embed = player_embed(player, session, "슬롯머신")
    if note:
        embed.description = note
    embed.add_field(
        name="기계",
        value=(
            f"상태: **{'고장남' if room.slot_broken else '작동 중'}**\n"
            f"사용 횟수: `{room.slot_uses}`\n"
            "1회 비용: `1코인`"
        ),
        inline=False,
    )
    return embed


# ============================================================
# Views
# ============================================================

class OwnerView(discord.ui.View):
    def __init__(self, session: GameSession, timeout=300):
        super().__init__(timeout=timeout)
        self.session = session

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message(
                "다른 플레이어의 게임에는 조작할 수 없습니다.",
                ephemeral=True,
            )
            return False
        return True


class ExploreView(OwnerView):
    def __init__(self, session):
        super().__init__(session)

        for direction, target in accessible_directions(session):
            btn = discord.ui.Button(
                label=direction,
                style=discord.ButtonStyle.primary,
            )

            async def callback(interaction, d=direction, t=target):
                await move_player(interaction, self.session, d, t)

            btn.callback = callback
            self.add_item(btn)

        if crack_here(session):
            btn = discord.ui.Button(
                label=f"폭탄으로 {session.secret_direction} 벽 파괴",
                style=discord.ButtonStyle.danger,
            )

            async def crack_callback(interaction):
                await open_secret(interaction, self.session)

            btn.callback = crack_callback
            self.add_item(btn)

        if session.boss_defeated:
            btn = discord.ui.Button(
                label="오늘 종료",
                style=discord.ButtonStyle.success,
            )

            async def end_callback(interaction):
                await end_day(interaction, self.session)

            btn.callback = end_callback
            self.add_item(btn)


class AttackView(OwnerView):
    def __init__(self, session):
        super().__init__(session)
        p = db.get_player(session.guild_id, session.user_id)

        attack = discord.ui.Button(
            label="공격 준비",
            style=discord.ButtonStyle.danger,
        )

        async def attack_callback(interaction):
            await prepare_timing(interaction, self.session, "attack")

        attack.callback = attack_callback
        self.add_item(attack)

        bomb = discord.ui.Button(
            label=f"폭탄 사용 ({p.bombs})",
            style=discord.ButtonStyle.secondary,
            disabled=p.bombs <= 0,
        )

        async def bomb_callback(interaction):
            await combat_bomb(interaction, self.session)

        bomb.callback = bomb_callback
        self.add_item(bomb)


class DodgeView(OwnerView):
    def __init__(self, session):
        super().__init__(session)

        btn = discord.ui.Button(
            label="회피 준비",
            style=discord.ButtonStyle.primary,
        )

        async def callback(interaction):
            await prepare_timing(interaction, self.session, "dodge")

        btn.callback = callback
        self.add_item(btn)


class CueView(OwnerView):
    def __init__(self, session, kind):
        super().__init__(session, timeout=60)

        btn = discord.ui.Button(
            label="공격!" if kind == "attack" else "회피!",
            style=(
                discord.ButtonStyle.danger
                if kind == "attack"
                else discord.ButtonStyle.success
            ),
        )

        async def callback(interaction):
            await resolve_timing(interaction, self.session, kind)

        btn.callback = callback
        self.add_item(btn)


class LootView(OwnerView):
    def __init__(self, session, gear):
        super().__init__(session)
        self.gear = gear

        equip = discord.ui.Button(
            label="장착",
            style=discord.ButtonStyle.success,
        )
        skip = discord.ui.Button(
            label="버리기",
            style=discord.ButtonStyle.secondary,
        )

        async def equip_callback(interaction):
            p = db.get_player(session.guild_id, session.user_id)
            if gear.kind == "weapon":
                p.weapon = gear
            else:
                p.armor = gear
            db.save_player(p)
            await show_after_clear(
                interaction,
                session,
                f"**{gear.name}**을(를) 장착했습니다.",
            )

        async def skip_callback(interaction):
            await show_after_clear(
                interaction,
                session,
                "새 장비를 버렸습니다.",
            )

        equip.callback = equip_callback
        skip.callback = skip_callback
        self.add_item(equip)
        self.add_item(skip)


class ShopView(OwnerView):
    def __init__(self, session):
        super().__init__(session)
        room = session.room()
        p = db.get_player(session.guild_id, session.user_id)

        for index, gear in enumerate(room.shop_stock[:2]):
            price = 6 if gear.kind == "weapon" else 5
            btn = discord.ui.Button(
                label=f"{index + 1}번 구매 ({price})",
                style=discord.ButtonStyle.success,
                disabled=p.coins < price,
            )

            async def callback(interaction, idx=index, cost=price):
                await buy_gear(interaction, self.session, idx, cost)

            btn.callback = callback
            self.add_item(btn)

        bomb = discord.ui.Button(
            label="폭탄 구매 (3)",
            style=discord.ButtonStyle.secondary,
            disabled=p.coins < 3,
        )

        async def bomb_callback(interaction):
            await buy_bomb(interaction, self.session)

        bomb.callback = bomb_callback
        self.add_item(bomb)

        leave = discord.ui.Button(
            label="나가기",
            style=discord.ButtonStyle.primary,
        )

        async def leave_callback(interaction):
            p2 = db.get_player(session.guild_id, session.user_id)
            await interaction.response.edit_message(
                embed=exploration_embed(p2, session, "상점을 나왔습니다."),
                view=ExploreView(session),
            )

        leave.callback = leave_callback
        self.add_item(leave)


class SlotView(OwnerView):
    def __init__(self, session):
        super().__init__(session)
        room = session.room()
        p = db.get_player(session.guild_id, session.user_id)

        play = discord.ui.Button(
            label="1코인 넣기",
            style=discord.ButtonStyle.success,
            disabled=room.slot_broken or p.coins < 1,
        )

        async def play_callback(interaction):
            await play_slot(interaction, self.session)

        play.callback = play_callback
        self.add_item(play)

        bomb = discord.ui.Button(
            label=f"폭탄으로 부수기 ({p.bombs})",
            style=discord.ButtonStyle.danger,
            disabled=room.slot_broken or p.bombs < 1,
        )

        async def bomb_callback(interaction):
            await bomb_slot(interaction, self.session)

        bomb.callback = bomb_callback
        self.add_item(bomb)

        leave = discord.ui.Button(
            label="나가기",
            style=discord.ButtonStyle.primary,
        )

        async def leave_callback(interaction):
            p2 = db.get_player(session.guild_id, session.user_id)
            await interaction.response.edit_message(
                embed=exploration_embed(p2, session, "슬롯머신 방을 나왔습니다."),
                view=ExploreView(session),
            )

        leave.callback = leave_callback
        self.add_item(leave)


# ============================================================
# 게임 액션
# ============================================================

async def move_player(interaction, session, direction, target):
    if session.ended:
        await interaction.response.send_message(
            "오늘의 게임은 이미 끝났습니다.",
            ephemeral=True,
        )
        return

    session.current = target
    room = session.room()
    room.visited = True
    p = db.get_player(session.guild_id, session.user_id)

    if room.kind in ("normal", "boss") and not room.cleared:
        session.phase = "player_turn"
        await interaction.response.edit_message(
            embed=combat_embed(
                p,
                session,
                f"**{room.enemy.color} {room.enemy.shape}**이(가) 나타났습니다.",
            ),
            view=AttackView(session),
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

    await interaction.response.edit_message(
        embed=exploration_embed(p, session),
        view=ExploreView(session),
    )


async def open_secret(interaction, session):
    p = db.get_player(session.guild_id, session.user_id)
    if p.bombs <= 0:
        await interaction.response.send_message("폭탄이 없습니다.", ephemeral=True)
        return

    p.bombs -= 1
    db.save_player(p)
    session.secret_revealed = True

    await interaction.response.edit_message(
        embed=exploration_embed(
            p,
            session,
            f"폭탄으로 **{session.secret_direction}쪽 금이 간 벽**을 열었습니다.",
        ),
        view=ExploreView(session),
    )


async def prepare_timing(interaction, session, kind):
    enemy = session.room().enemy
    if enemy is None or enemy.hp <= 0:
        await interaction.response.send_message(
            "현재 전투 중이 아닙니다.",
            ephemeral=True,
        )
        return

    expected = "player_turn" if kind == "attack" else "enemy_turn"
    if session.phase != expected:
        await interaction.response.send_message(
            "지금 사용할 수 없는 행동입니다.",
            ephemeral=True,
        )
        return

    p = db.get_player(session.guild_id, session.user_id)
    action = "공격" if kind == "attack" else "회피"

    session.phase = "timing_wait"
    session.cue_kind = kind
    session.cue_started = None

    # 먼저 즉시 응답한 뒤 랜덤 대기.
    await interaction.response.edit_message(
        embed=combat_embed(
            p,
            session,
            f"**{action} 준비...**\n버튼이 나타날 때까지 기다리세요.",
        ),
        view=None,
    )

    spec = SHAPES[enemy.shape]
    await asyncio.sleep(random.uniform(*spec["cue_delay"]))

    try:
        # Discord가 메시지 편집을 받아들인 직후를 타이밍 시작점으로 사용.
        await interaction.edit_original_response(
            embed=timing_embed(p, session, kind),
            view=CueView(session, kind),
        )
        session.cue_started = time.monotonic()
    except discord.HTTPException:
        session.phase = expected
        session.cue_kind = None


async def resolve_timing(interaction, session, kind):
    if (
        session.phase != "timing_wait"
        or session.cue_kind != kind
        or session.cue_started is None
    ):
        await interaction.response.send_message(
            "이미 끝난 판정입니다.",
            ephemeral=True,
        )
        return

    elapsed = time.monotonic() - session.cue_started
    session.cue_started = None
    session.cue_kind = None

    room = session.room()
    enemy = room.enemy
    assert enemy is not None
    p = db.get_player(session.guild_id, session.user_id)

    perfect, good = timing_windows(p, enemy, kind)
    grade = timing_grade(elapsed, perfect, good)

    if kind == "attack":
        damage = attack_damage(p, enemy, grade)
        enemy.hp -= damage
        note = f"**{grade}** · `{elapsed:.2f}s`\n적에게 **{damage} 피해**."

        if enemy.hp <= 0:
            await enemy_defeated(interaction, session, note)
            return

        session.phase = "enemy_turn"
        await interaction.response.edit_message(
            embed=combat_embed(p, session, note + "\n\n적이 반격합니다."),
            view=DodgeView(session),
        )
        return

    damage = incoming_damage(p, enemy, grade)
    p.hp = max(0, p.hp - damage)
    db.save_player(p)

    note = f"**{grade}** · `{elapsed:.2f}s`\n받은 피해: **{damage}**"

    if p.hp <= 0:
        await player_died(interaction, session, note)
        return

    session.phase = "player_turn"
    await interaction.response.edit_message(
        embed=combat_embed(p, session, note + "\n\n공격할 차례입니다."),
        view=AttackView(session),
    )


async def combat_bomb(interaction, session):
    if session.phase != "player_turn":
        await interaction.response.send_message(
            "지금은 폭탄을 사용할 수 없습니다.",
            ephemeral=True,
        )
        return

    p = db.get_player(session.guild_id, session.user_id)
    enemy = session.room().enemy

    if enemy is None:
        await interaction.response.send_message("적이 없습니다.", ephemeral=True)
        return
    if p.bombs <= 0:
        await interaction.response.send_message("폭탄이 없습니다.", ephemeral=True)
        return

    p.bombs -= 1
    db.save_player(p)

    damage = random.randint(7, 10)
    enemy.hp -= damage

    if enemy.hp <= 0:
        await enemy_defeated(
            interaction,
            session,
            f"폭탄이 폭발해 **{damage} 피해**를 주었습니다.",
        )
        return

    session.phase = "enemy_turn"
    await interaction.response.edit_message(
        embed=combat_embed(
            p,
            session,
            f"폭탄이 폭발해 **{damage} 피해**를 주었습니다.\n\n적이 반격합니다.",
        ),
        view=DodgeView(session),
    )


async def enemy_defeated(interaction, session, combat_note):
    room = session.room()
    enemy = room.enemy
    assert enemy is not None

    room.cleared = True
    session.phase = "explore"

    p = db.get_player(session.guild_id, session.user_id)

    # 코인이 유일한 점수이자 화폐.
    low, high = SHAPES[enemy.shape]["coin_drop"]
    coins = random.randint(low, high)
    if enemy.boss:
        coins += random.randint(5, 9)

    p.coins += coins

    # 기타 전리품도 랜덤.
    bomb_gain = 1 if random.random() < (0.35 if enemy.boss else 0.20) else 0
    p.bombs += bomb_gain
    db.save_player(p)

    note = f"{combat_note}\n\n코인 **+{coins}**"
    if bomb_gain:
        note += " · 폭탄 **+1**"

    if enemy.boss:
        session.boss_defeated = True

    # 일반 적은 30%, 보스는 100% 장비 드롭.
    if enemy.boss or random.random() < 0.30:
        gear = generate_gear(
            random.choice(("weapon", "armor")),
            boss_drop=enemy.boss,
        )
        embed = player_embed(p, session, "전리품 발견")
        embed.description = note
        embed.add_field(name="새 장비", value=gear.label(), inline=False)

        current = p.weapon if gear.kind == "weapon" else p.armor
        embed.add_field(name="현재 장비", value=current.label(), inline=False)

        await interaction.response.edit_message(
            embed=embed,
            view=LootView(session, gear),
        )
        return

    await show_after_clear(interaction, session, note)


async def show_after_clear(interaction, session, note):
    p = db.get_player(session.guild_id, session.user_id)

    if session.boss_defeated and session.current == session.boss_pos:
        note += (
            "\n\n**보스를 처치했습니다.** "
            "지금 오늘을 끝내거나 남은 방을 더 탐색할 수 있습니다."
        )

    await interaction.response.edit_message(
        embed=exploration_embed(p, session, note),
        view=ExploreView(session),
    )


async def player_died(interaction, session, note):
    p = db.get_player(session.guild_id, session.user_id)
    p.hp = 0
    p.last_day = today_key()
    p.status = "dead"
    db.save_player(p)

    session.ended = True

    embed = player_embed(p, session, "게임 오버")
    embed.description = (
        note
        + "\n\n오늘은 더 이상 행동할 수 없습니다."
        + "\n**무기·방어구·코인·폭탄은 전부 유지됩니다.**"
        + "\n다음 날에는 HP만 전부 회복되어 새 층을 시작합니다."
    )
    await interaction.response.edit_message(embed=embed, view=None)


async def end_day(interaction, session):
    if not session.boss_defeated:
        await interaction.response.send_message(
            "보스를 먼저 처치해야 합니다.",
            ephemeral=True,
        )
        return

    p = db.get_player(session.guild_id, session.user_id)
    p.last_day = today_key()
    p.status = "finished"
    db.save_player(p)

    session.ended = True

    embed = player_embed(p, session, "오늘의 층 종료")
    embed.description = (
        f"최종 보유 코인: **{p.coins}**\n"
        "장비와 자원은 다음 날에도 그대로 유지됩니다."
    )
    await interaction.response.edit_message(embed=embed, view=None)


# ============================================================
# 상점 / 슬롯
# ============================================================

async def buy_gear(interaction, session, index, price):
    room = session.room()
    p = db.get_player(session.guild_id, session.user_id)

    if index >= len(room.shop_stock):
        await interaction.response.send_message(
            "이미 팔린 물건입니다.",
            ephemeral=True,
        )
        return

    if p.coins < price:
        await interaction.response.send_message(
            "코인이 부족합니다.",
            ephemeral=True,
        )
        return

    gear = room.shop_stock.pop(index)
    p.coins -= price

    if gear.kind == "weapon":
        p.weapon = gear
    else:
        p.armor = gear

    db.save_player(p)

    await interaction.response.edit_message(
        embed=shop_embed(
            p,
            session,
            f"**{gear.name}**을(를) 구입해 바로 장착했습니다.",
        ),
        view=ShopView(session),
    )


async def buy_bomb(interaction, session):
    p = db.get_player(session.guild_id, session.user_id)

    if p.coins < 3:
        await interaction.response.send_message(
            "코인이 부족합니다.",
            ephemeral=True,
        )
        return

    p.coins -= 3
    p.bombs += 1
    db.save_player(p)

    await interaction.response.edit_message(
        embed=shop_embed(p, session, "폭탄 **1개**를 구입했습니다."),
        view=ShopView(session),
    )


async def play_slot(interaction, session):
    room = session.room()
    p = db.get_player(session.guild_id, session.user_id)

    if room.slot_broken:
        await interaction.response.send_message(
            "이미 고장난 기계입니다.",
            ephemeral=True,
        )
        return

    if p.coins < 1:
        await interaction.response.send_message(
            "코인이 없습니다.",
            ephemeral=True,
        )
        return

    p.coins -= 1
    room.slot_uses += 1

    roll = random.random()
    if roll < 0.45:
        note = "아무것도 나오지 않았습니다."
    elif roll < 0.68:
        gain = random.randint(1, 2)
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
        gain = random.randint(4, 7)
        p.coins += gain
        note = f"잭팟. 코인 **+{gain}**"

    break_rates = [0.05, 0.10, 0.20, 0.35, 0.55, 0.75]
    break_rate = break_rates[min(room.slot_uses - 1, len(break_rates) - 1)]

    if random.random() < break_rate:
        room.slot_broken = True
        note += "\n\n`철컥.` 슬롯머신이 고장났습니다."

    db.save_player(p)

    await interaction.response.edit_message(
        embed=slot_embed(p, session, note),
        view=SlotView(session),
    )


async def bomb_slot(interaction, session):
    room = session.room()
    p = db.get_player(session.guild_id, session.user_id)

    if room.slot_broken:
        await interaction.response.send_message(
            "이미 고장난 기계입니다.",
            ephemeral=True,
        )
        return

    if p.bombs < 1:
        await interaction.response.send_message(
            "폭탄이 없습니다.",
            ephemeral=True,
        )
        return

    p.bombs -= 1
    room.slot_broken = True

    gain = random.randint(1, 7)
    p.coins += gain
    db.save_player(p)

    await interaction.response.edit_message(
        embed=slot_embed(
            p,
            session,
            f"슬롯머신을 폭파했습니다.\n잔해에서 코인 **{gain}개**를 얻었습니다.",
        ),
        view=SlotView(session),
    )


# ============================================================
# Bot / Slash commands
# ============================================================

intents = discord.Intents.default()


class ShapeGameBot(commands.Bot):
    async def setup_hook(self):
        if TEST_GUILD_ID:
            guild = discord.Object(id=int(TEST_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"테스트 서버 {TEST_GUILD_ID}에 명령어 동기화 완료")
        else:
            await self.tree.sync()
            print("전역 명령어 동기화 완료")


bot = ShapeGameBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"로그인 완료: {bot.user} ({bot.user.id})")


@bot.tree.command(name="게임", description="오늘의 층을 시작하거나 이어서 플레이합니다.")
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

    if p.last_day == today and p.status == "dead":
        await interaction.response.send_message(
            "오늘은 이미 사망했습니다. 내일 다시 플레이할 수 있습니다.\n"
            "무기·방어구·코인·폭탄은 그대로 유지됩니다.\n"
            "플레이테스트 중이라면 `/테스트리셋`을 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    if p.last_day == today and p.status == "finished":
        await interaction.response.send_message(
            "오늘의 층을 이미 종료했습니다.\n"
            "플레이테스트 중이라면 `/테스트리셋`을 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    old = sessions.get(key)
    if old and not old.ended:
        room = old.room()

        if room.kind in ("normal", "boss") and not room.cleared:
            old.phase = "player_turn"
            await interaction.response.send_message(
                embed=combat_embed(p, old, "진행 중인 전투로 돌아왔습니다."),
                view=AttackView(old),
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
                embed=exploration_embed(p, old, "진행 중인 층으로 돌아왔습니다."),
                view=ExploreView(old),
                ephemeral=True,
            )
        return

    # 새 날: 아이템/코인/폭탄 유지, HP만 회복
    p.hp = p.max_hp
    p.last_day = today
    p.status = "playing"
    db.save_player(p)

    session = generate_floor(guild_id, user_id, today)
    sessions[key] = session

    await interaction.response.send_message(
        embed=exploration_embed(
            p,
            session,
            "**플레이테스트용 1층**이 랜덤 생성되었습니다.",
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
    embed = discord.Embed(title=f"{interaction.user.display_name} — 상태")
    embed.add_field(
        name="자원",
        value=(
            f"HP `{p.hp}/{p.max_hp}`\n"
            f"코인 `{p.coins}` · 폭탄 `{p.bombs}`"
        ),
        inline=False,
    )
    embed.add_field(name="무기", value=p.weapon.label(), inline=False)
    embed.add_field(name="방어구", value=p.armor.label(), inline=False)
    embed.add_field(
        name="오늘",
        value=f"`{p.last_day or '미시작'}` · `{p.status}`",
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="점수판", description="보유 코인이 많은 순서대로 순위를 봅니다.")
async def leaderboard(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    rows = db.leaderboard(interaction.guild_id)
    lines = []

    for rank, (user_id, coins) in enumerate(rows, 1):
        member = interaction.guild.get_member(user_id)
        name = member.display_name if member else f"<@{user_id}>"
        lines.append(f"`{rank:>2}.` {name} — **{coins} 코인**")

    embed = discord.Embed(
        title="코인 순위",
        description="\n".join(lines) if lines else "아직 기록이 없습니다.",
    )
    embed.set_footer(text="별도 점수는 없습니다. 현재 보유 코인이 순위입니다.")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="테스트리셋",
    description="플레이테스트용: 오늘 제한과 현재 층만 초기화합니다.",
)
async def test_reset(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있습니다.",
            ephemeral=True,
        )
        return

    key = (interaction.guild_id, interaction.user.id)
    sessions.pop(key, None)
    db.test_reset(interaction.guild_id, interaction.user.id)

    await interaction.response.send_message(
        "테스트 상태를 초기화했습니다. `/게임`으로 새 랜덤 층을 시작할 수 있습니다.\n"
        "**무기·방어구·코인·폭탄은 유지됩니다.**",
        ephemeral=True,
    )


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN이 없습니다. `.env.example`을 복사해 `.env`를 만든 뒤 토큰을 넣어 주세요."
        )

    bot.run(TOKEN)
