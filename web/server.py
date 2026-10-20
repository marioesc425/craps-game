"""Small in-memory multiplayer server for the browser version of Golden Rail."""
from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from craps.engine.bets import Bet, BetType
from craps.engine.dice import roll_dice
from craps.engine.game import CrapsEngine
from craps.engine.outcomes import RollOutcome
from craps.engine.player import InvalidBetError, Player

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="The Golden Rail — Shared Craps")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
MAX_PLAYERS = 6
ROOMS: dict[str, "Room"] = {}

@dataclass(frozen=True)
class Zone:
    name: str
    bet_type: BetType
    number: int | None = None


ZONE_BY_NAME = {
    "pass_line": Zone("pass_line", BetType.PASS_LINE),
    "dont_pass_side": Zone("dont_pass_side", BetType.DONT_PASS),
    "dont_pass_bottom": Zone("dont_pass_bottom", BetType.DONT_PASS),
    "come": Zone("come", BetType.COME),
    "dont_come": Zone("dont_come", BetType.DONT_COME),
    "field": Zone("field", BetType.FIELD),
    **{f"place_{n}": Zone(f"place_{n}", BetType.PLACE, n) for n in (4,5,6,8,9,10)},
    **{f"hard_{n}": Zone(f"hard_{n}", BetType.HARDWAY, n) for n in (4,6,8,10)},
}


@dataclass
class Member:
    player_id: str
    name: str
    game: Player = field(default_factory=Player)
    undo: list[tuple[str, Bet, int]] = field(default_factory=list)


@dataclass
class Room:
    code: str
    engine: CrapsEngine = field(default_factory=CrapsEngine)
    members: dict[str, Member] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    connections: dict[str, WebSocket] = field(default_factory=dict)
    shooter_id: str | None = None
    dice: tuple[int, int] | None = None
    last_outcome: str = ""
    message: str = "Choose a chip and place bets on the table."
    rolling: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def _new_code() -> str:
    while True:
        code = "".join(secrets.choice(ROOM_ALPHABET) for _ in range(6))
        if code not in ROOMS:
            return code


def _member_index(room: Room, player_id: str) -> int:
    try:
        return room.order.index(player_id)
    except ValueError:
        return 0


def _all_bets(room: Room) -> list[Bet]:
    return [bet for player_id in room.order
            for bet in room.members[player_id].game.active_bets]


def _stack_position(room: Room, member: Member, bet: Bet, bet_index: int) -> tuple[int, int]:
    """Spread each player's stack within the same visible table betting area."""
    seat = _member_index(room, member.player_id)
    zone_key = (bet.bet_type, bet.number)
    same = [(m, b) for pid in room.order for m in [room.members[pid]]
            for b in m.game.active_bets if (b.bet_type, b.number) == zone_key]
    ordinal = next((i for i, pair in enumerate(same) if pair == (member, bet)), 0)
    if bet.bet_type == BetType.PLACE:
        numbers = (4,5,6,8,9,10)
        index = numbers.index(bet.number)
        rect_center = (round((163.5 + 62.4 * index + 31.2) * 1.75), round((55 + 117) / 2 * 1.75))
        slots = ((-30,-24), (0,-24), (30,-24), (-30,24), (0,24), (30,24))
        dx, dy = slots[ordinal % len(slots)]
        return rect_center[0] + dx, rect_center[1] + dy
    if bet.bet_type == BetType.HARDWAY:
        hard_rects = {6:(962,302,1159,380), 10:(1159,302,1356,380),
                      8:(962,380,1159,457), 4:(1159,380,1356,457)}
        x0,y0,x1,y1 = hard_rects[bet.number]
        rect_center = ((x0+x1)//2, (y0+y1)//2)
        slots = ((-60,-16), (-20,-16), (20,-16), (60,-16), (-40,16), (40,16))
        dx, dy = slots[ordinal % len(slots)]
        return rect_center[0] + dx, rect_center[1] + dy
    if bet.bet_type == BetType.PASS_LINE:
        return (785 + (seat % 3) * 45, 535 - (seat // 3) * 28)
    if bet.bet_type == BetType.DONT_PASS:
        slots = ((720,455),(770,455),(820,455),(720,484),(770,484),(820,484))
        return slots[seat % len(slots)]
    if bet.bet_type == BetType.COME:
        slots = ((680,258),(730,258),(780,258),(680,300),(730,300),(780,300))
        return slots[(seat + bet_index) % len(slots)]
    if bet.bet_type == BetType.DONT_COME:
        slots = ((197,75),(240,75),(197,117),(240,117),(197,160),(240,160))
        return slots[seat % len(slots)]
    if bet.bet_type == BetType.FIELD:
        slots = ((690,350),(740,350),(790,350),(690,390),(740,390),(790,390))
        return slots[seat % len(slots)]
    return (790, 350)


def _snapshot(room: Room, you: str) -> dict:
    players = []
    for pid in room.order:
        member = room.members[pid]
        wagers = []
        for index, bet in enumerate(member.game.active_bets):
            x, y = _stack_position(room, member, bet, index)
            wagers.append({"id": bet.id, "type": bet.bet_type.value,
                           "number": bet.number, "amount": bet.amount,
                           "odds": bet.odds, "x": x, "y": y})
        players.append({"id": pid, "name": member.name,
                        "bankroll": member.game.bankroll,
                        "online": pid in room.connections,
                        "shooter": pid == room.shooter_id,
                        "wagers": wagers})
    return {"type": "state", "room": room.code, "you": you,
            "point": room.engine.point, "dice": room.dice,
            "outcome": room.last_outcome, "history": [sum(r) for r in room.engine.roll_history[-8:]],
            "players": players, "shooter": room.shooter_id,
            "shooter_online": room.shooter_id in room.connections if room.shooter_id else False,
            "rolling": room.rolling, "undo_available": bool(room.members.get(you) and room.members[you].undo),
            "message": room.message}


async def _send_state(room: Room) -> None:
    stale = []
    for player_id, socket in list(room.connections.items()):
        try:
            await socket.send_json(_snapshot(room, player_id))
        except Exception:
            stale.append(player_id)
    for player_id in stale:
        room.connections.pop(player_id, None)


async def _error(socket: WebSocket, message: str) -> None:
    await socket.send_json({"type": "error", "message": message})


def _find_bet(member: Member, bet_id: object) -> Bet | None:
    if type(bet_id) is not int:
        return None
    return next((bet for bet in member.game.active_bets if bet.id == bet_id), None)


def _place(member: Member, room: Room, message: dict) -> None:
    chip = message.get("chip")
    zone_name = message.get("zone")
    if type(chip) is not int or chip not in (1, 5, 6, 25, 100, 500):
        raise InvalidBetError("Choose a chip from the tray.")
    zone = ZONE_BY_NAME.get(zone_name) if isinstance(zone_name, str) else None
    if zone is None:
        raise InvalidBetError("That isn't a betting area.")
    if zone.bet_type in (BetType.PASS_LINE, BetType.DONT_PASS) and room.engine.point is not None:
        raise InvalidBetError("Pass Line and Don't Pass are come-out bets.")
    if zone.bet_type in (BetType.COME, BetType.DONT_COME) and room.engine.point is None:
        raise InvalidBetError("Come and Don't Come need an established point.")
    merge = zone.bet_type not in (BetType.COME, BetType.DONT_COME)
    existing = next((b for b in reversed(member.game.active_bets)
                     if merge and b.bet_type == zone.bet_type and b.number == zone.number), None)
    if existing:
        member.game.increase_wager(existing, chip)
        bet, kind = existing, "increase"
    else:
        bet = member.game.place_wager(zone.bet_type, chip, zone.number, point=room.engine.point)
        kind = "new"
    member.undo.append((kind, bet, chip))
    room.message = f"{member.name} put ${chip} on {zone.name.replace('_', ' ')}."


def _stack(member: Member, room: Room, message: dict) -> None:
    chip, bet = message.get("chip"), _find_bet(member, message.get("bet_id"))
    if type(chip) is not int or chip not in (1, 5, 6, 25, 100, 500):
        raise InvalidBetError("Choose a chip from the tray.")
    if bet is None:
        raise InvalidBetError("That wager is no longer yours or has already resolved.")
    eligible = (bet.bet_type in (BetType.PASS_LINE, BetType.DONT_PASS) and room.engine.point is not None
                or bet.bet_type in (BetType.COME, BetType.DONT_COME) and bet.number is not None)
    if eligible:
        member.game.add_odds(bet, chip, room.engine.point)
        member.undo.append(("odds", bet, chip))
        room.message = f"{member.name} added ${chip} odds to their {bet.bet_type.value.replace('_', ' ')}."
    else:
        member.game.increase_wager(bet, chip)
        member.undo.append(("increase", bet, chip))
        room.message = f"{member.name} added ${chip} to their {bet.bet_type.value.replace('_', ' ')}."


def _undo(member: Member, room: Room) -> None:
    if not member.undo:
        raise InvalidBetError("There is no recent chip to undo.")
    kind, bet, amount = member.undo.pop()
    if kind == "new":
        member.game.undo_wager(bet)
    elif kind == "increase":
        member.game.reduce_wager(bet, amount)
    else:
        member.game.reduce_odds(bet, amount)
    room.message = f"{member.name} removed their last chip and got ${amount} back."


async def _finish_roll(room: Room) -> None:
    await asyncio.sleep(0.85)
    async with room.lock:
        dice = roll_dice()
        result = room.engine.resolve_roll(dice, _all_bets(room))
        for player_id in room.order:
            room.members[player_id].game.settle(result)
            room.members[player_id].undo.clear()
        room.dice = dice
        room.last_outcome = result.outcome.value.replace("_", " ")
        room.rolling = False
        room.message = f"{room.members[room.shooter_id].name} rolled {sum(dice)} — {room.last_outcome}."
        if result.outcome in (RollOutcome.WIN, RollOutcome.LOSE):
            current = _member_index(room, room.shooter_id or "")
            room.shooter_id = room.order[(current + 1) % len(room.order)] if room.order else None
        await _send_state(room)


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/")
async def home():
    return FileResponse(ROOT / "static" / "index.html")


@app.websocket("/ws")
async def websocket_game(socket: WebSocket):
    await socket.accept()
    player_id = None
    room = None
    try:
        hello = await socket.receive_json()
        if not isinstance(hello, dict) or hello.get("type") != "join":
            await _error(socket, "Join a room to start playing.")
            await socket.close()
            return
        player_id = hello.get("player_id")
        name = " ".join(str(hello.get("name", "Guest")).split())[:18] or "Guest"
        code = str(hello.get("room", "")).upper().strip()
        if not isinstance(player_id, str) or len(player_id) < 12 or len(player_id) > 80:
            await _error(socket, "Refresh the page and try again.")
            await socket.close()
            return
        if not code:
            code = _new_code()
            ROOMS[code] = Room(code)
        room = ROOMS.get(code)
        if room is None:
            await _error(socket, "That room doesn't exist on this server. Create a new table.")
            await socket.close()
            return
        async with room.lock:
            member = room.members.get(player_id)
            if member is None:
                if len(room.members) >= MAX_PLAYERS:
                    await _error(socket, "This table is full (6 players maximum).")
                    await socket.close()
                    return
                member = Member(player_id, name)
                room.members[player_id] = member
                room.order.append(player_id)
                if room.shooter_id is None:
                    room.shooter_id = player_id
            else:
                member.name = name
            old = room.connections.get(player_id)
            room.connections[player_id] = socket
            if old and old is not socket:
                try:
                    await old.close()
                except Exception:
                    pass
            room.message = f"{name} joined the table."
            await _send_state(room)

        while True:
            message = await socket.receive_json()
            if not isinstance(message, dict):
                continue
            if message.get("type") == "ping":
                await socket.send_json({"type": "pong"})
                continue
            async with room.lock:
                member = room.members[player_id]
                try:
                    action = message.get("type")
                    if room.rolling:
                        raise InvalidBetError("The dice are rolling. Wait for the result.")
                    if action == "bet":
                        _place(member, room, message)
                    elif action == "stack":
                        _stack(member, room, message)
                    elif action == "undo":
                        _undo(member, room)
                    elif action == "roll":
                        if room.shooter_id not in room.connections:
                            room.shooter_id = player_id
                        if player_id != room.shooter_id:
                            raise InvalidBetError("Wait for the shooter to roll.")
                        if not _all_bets(room):
                            raise InvalidBetError("Place at least one wager before rolling.")
                        room.rolling = True
                        room.message = f"{member.name} is rolling…"
                        asyncio.create_task(_finish_roll(room))
                    else:
                        raise InvalidBetError("Unknown table action.")
                    await _send_state(room)
                except InvalidBetError as exc:
                    await _error(socket, str(exc))
    except WebSocketDisconnect:
        pass
    finally:
        if room is not None and player_id is not None:
            async with room.lock:
                if room.connections.get(player_id) is socket:
                    room.connections.pop(player_id, None)
                    await _send_state(room)
