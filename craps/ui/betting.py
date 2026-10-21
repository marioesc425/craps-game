"""Direct wager hit-testing uses the same pixel geometry used to draw the table."""
from dataclasses import dataclass

import pygame

from craps.engine.bets import BetType
from craps.engine.player import InvalidBetError
from craps.engine.settlement import PLACE_PAYOUTS, HARDWAY_PAYOUTS
from craps.ui.board import TABLE_REGIONS, PROP_REGIONS, PLACE_RECTS, PROP_TYPES


@dataclass(frozen=True)
class BettingZone:
    name: str
    bet_type: BetType
    shape: object
    number: int | None = None

    @property
    def label(self):
        return self.name.replace("_", " ").title()

    def contains(self, position):
        if isinstance(self.shape, pygame.Rect):
            return self.shape.collidepoint(position)
        x, y = position
        inside = False
        points = self.shape
        for i, (x1, y1) in enumerate(points):
            x2, y2 = points[i - 1]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1) + x1:
                inside = not inside
        return inside

    def draw_highlight(self, surface):
        color = (255, 214, 112)
        if isinstance(self.shape, pygame.Rect):
            pygame.draw.rect(surface, color, self.shape, 4)
        else:
            pygame.draw.polygon(surface, color, self.shape, 4)


ZONES = [
    BettingZone("pass_line", BetType.PASS_LINE, TABLE_REGIONS["pass_line"]),
    BettingZone("dont_pass_side", BetType.DONT_PASS, TABLE_REGIONS["dont_pass_side"]),
    BettingZone("dont_pass_bottom", BetType.DONT_PASS, TABLE_REGIONS["dont_pass_bottom"]),
    BettingZone("come", BetType.COME, TABLE_REGIONS["come"]),
    BettingZone("dont_come", BetType.DONT_COME, TABLE_REGIONS["dont_come_bar"]),
    BettingZone("field", BetType.FIELD, TABLE_REGIONS["field"]),
]
ZONES.extend(BettingZone(f"place_{number}", BetType.PLACE, rect, number)
             for number, rect in PLACE_RECTS.items())
ZONES.extend(BettingZone(f"hard_{number}", BetType.HARDWAY, PROP_REGIONS[f"hard_{number}"], number)
             for number in (4, 6, 8, 10))
ZONES.extend(BettingZone(name, bet_type, PROP_REGIONS[name], number)
             for name, (bet_type, number) in PROP_TYPES.items()
             if bet_type not in (BetType.HARDWAY,))


def zone_at(position):
    """Return one drawn zone; Rects use left/top-inclusive, right/bottom-exclusive edges."""
    for zone in ZONES:
        if zone.contains(position):
            return zone
    return None


def _existing_zone_bet(player, zone):
    if zone.bet_type in (BetType.COME, BetType.DONT_COME):
        return None
    return next((b for b in reversed(player.active_bets)
                 if b.bet_type == zone.bet_type and b.number == zone.number), None)


def _payout_compatible(bet_type, number, amount):
    if bet_type == BetType.PLACE:
        n, d = PLACE_PAYOUTS[number]
        return amount * n % d == 0
    if bet_type == BetType.HARDWAY:
        n, d = HARDWAY_PAYOUTS[number]
        return amount * n % d == 0
    return True


def wager_available(player, engine, zone, chip, pending=0, reserved_elsewhere=0):
    if chip > player.bankroll or chip <= 0:
        return False
    if zone.bet_type in (BetType.PASS_LINE, BetType.DONT_PASS):
        if engine.point is not None:
            return False
    elif zone.bet_type in (BetType.COME, BetType.DONT_COME):
        if engine.point is None:
            return False
    existing = _existing_zone_bet(player, zone)
    total = (existing.amount if existing else 0) + pending + chip
    if total > player.rules.maximum_single_wager:
        return False
    return pending + chip + reserved_elsewhere <= player.bankroll


def place_chip(player, engine, zone, chip):
    """Place/increase a table wager; returns (Bet, transaction kind)."""
    if zone.bet_type in (BetType.PASS_LINE, BetType.DONT_PASS) and engine.point is not None:
        raise InvalidBetError("Pass Line and Don't Pass are come-out bets")
    if zone.bet_type in (BetType.COME, BetType.DONT_COME) and engine.point is None:
        raise InvalidBetError("Come and Don't Come need an established point")
    merge = zone.bet_type not in (BetType.COME, BetType.DONT_COME)
    existing = next((b for b in reversed(player.active_bets)
                     if merge and b.bet_type == zone.bet_type and b.number == zone.number), None)
    if existing:
        player.increase_wager(existing, chip)
        return existing, "increase"
    wager = player.place_wager(zone.bet_type, chip, zone.number, point=engine.point)
    return wager, "new"


@dataclass
class PendingWager:
    zone: BettingZone
    amount: int


class WagerAccumulator:
    """Stage selected chip values until they form one valid base wager."""

    def __init__(self):
        self.pending: dict[str, PendingWager] = {}

    def amount_for(self, zone):
        item = self.pending.get(zone.name)
        return item.amount if item else 0

    def amount_to_complete(self, player, zone):
        existing = _existing_zone_bet(player, zone)
        base = existing.amount if existing else 0
        current = base + self.amount_for(zone)
        step = (6 if zone.bet_type == BetType.PLACE and zone.number in (6, 8)
                else 5 if zone.bet_type == BetType.PLACE else 1)
        target = max(player.rules.minimum_bet, current + 1)
        target = ((target + step - 1) // step) * step
        return target - current

    def add_chip(self, player, engine, zone, chip):
        if zone.bet_type in (BetType.PASS_LINE, BetType.DONT_PASS) and engine.point is not None:
            raise InvalidBetError("Pass Line and Don't Pass are come-out bets")
        if zone.bet_type in (BetType.COME, BetType.DONT_COME) and engine.point is None:
            raise InvalidBetError("Come and Don't Come need an established point")
        if type(chip) is not int or chip <= 0:
            raise InvalidBetError("Choose a positive whole-dollar chip")
        existing = _existing_zone_bet(player, zone)
        staged = self.amount_for(zone)
        contribution = staged + chip
        total = (existing.amount if existing else 0) + contribution
        if total > player.rules.maximum_single_wager:
            raise InvalidBetError(f"Maximum base wager is ${player.rules.maximum_single_wager}")
        reserved_elsewhere = sum(item.amount for key, item in self.pending.items() if key != zone.name)
        if contribution + reserved_elsewhere > player.bankroll:
            raise InvalidBetError(f"Not enough funds: you have ${player.bankroll} available")
        complete = total >= player.rules.minimum_bet and _payout_compatible(zone.bet_type, zone.number, total)
        if not complete:
            self.pending[zone.name] = PendingWager(zone, contribution)
            return None, "pending", contribution
        self.pending.pop(zone.name, None)
        bet, action = place_chip(player, engine, zone, contribution)
        return bet, action, contribution

    def undo_chip(self, zone, chip):
        item = self.pending.get(zone.name)
        if item is None or item.amount < chip:
            raise InvalidBetError("That staged chip is no longer available")
        item.amount -= chip
        if not item.amount:
            del self.pending[zone.name]
        return item.amount if zone.name in self.pending else 0

    def clear(self):
        self.pending.clear()


def draw_pending_stacks(surface, builder, bets, small_font):
    for pending in builder.pending.values():
        zone = pending.zone
        existing = next((bet for bet in reversed(bets)
                         if zone.bet_type not in (BetType.COME, BetType.DONT_COME)
                         and bet.bet_type == zone.bet_type and bet.number == zone.number), None)
        count = sum(bet.bet_type == zone.bet_type for bet in bets)
        x, y = stack_center(existing) if existing else stack_center_for_zone(zone, count)
        if existing:
            y -= 38
        center = (x, y)
        pygame.draw.circle(surface, (5, 20, 15), (x + 2, y + 3), 19)
        pygame.draw.circle(surface, (79, 58, 19), center, 17)
        pygame.draw.circle(surface, (245, 199, 99), center, 14, 2)
        amount = small_font.render(f"${pending.amount}", True, (255, 246, 221))
        surface.blit(amount, amount.get_rect(center=center))


def stack_center_for_zone(zone, index=0):
    if zone.name == "pass_line":
        return (790, 538)
    if zone.name in ("dont_pass_side", "dont_pass_bottom"):
        return (788, 477)
    if zone.name == "come":
        slots = ((685, 265), (733, 265), (781, 265), (685, 312), (733, 312), (781, 312))
        return slots[index % len(slots)]
    if zone.name == "dont_come":
        slots = ((198, 73), (232, 73), (266, 73), (198, 118), (232, 118), (266, 118),
                 (198, 163), (232, 163), (266, 163))
        return slots[index % len(slots)]
    if zone.bet_type == BetType.FIELD:
        return (790, 350)
    if zone.bet_type == BetType.PLACE:
        rect = PLACE_RECTS[zone.number]
        return (rect.centerx, rect.bottom - 18)
    if zone.name in PROP_REGIONS:
        cell = PROP_REGIONS[zone.name]
        return (cell.right - 25, cell.bottom - 25)
    return zone.shape.center


def odds_eligible(bet, point):
    from craps.engine.bets import BetType
    if bet.bet_type in (BetType.PASS_LINE, BetType.DONT_PASS):
        return point is not None
    if bet.bet_type in (BetType.COME, BetType.DONT_COME):
        return bet.number is not None
    return False


def stack_center(bet, index=0):
    """Pixel centers for markers, kept within the bet's drawn area."""
    from craps.engine.bets import BetType
    if bet.bet_type == BetType.PASS_LINE:
        return (790, 538)
    if bet.bet_type == BetType.DONT_PASS:
        return (788, 477)
    if bet.bet_type == BetType.COME:
        if bet.number is not None:
            rect = PLACE_RECTS[bet.number]
            # A traveling Come bet leaves the Come box and sits on its number.
            # Keep it near the left side so the printed number and a Place bet
            # marker on the lower edge remain visible.
            row = (-36, 0, 36)[index % 3]
            return (rect.left + 22, rect.centery + row)
        slots = ((685, 265), (733, 265), (781, 265), (685, 312), (733, 312), (781, 312))
        return slots[index % len(slots)]
    if bet.bet_type == BetType.DONT_COME:
        if bet.number is not None:
            rect = PLACE_RECTS[bet.number]
            # Keep the Don't Come marker on the opposite side of the number.
            row = (-36, 0, 36)[index % 3]
            return (rect.right - 22, rect.centery + row)
        slots = ((198, 73), (232, 73), (266, 73), (198, 118), (232, 118), (266, 118),
                 (198, 163), (232, 163), (266, 163))
        return slots[index % len(slots)]
    if bet.bet_type == BetType.FIELD:
        return (790, 350)
    if bet.bet_type == BetType.PLACE:
        rect = PLACE_RECTS[bet.number]
        return (rect.centerx, rect.bottom - 18)
    # Every proposition stack is anchored to the lower-right of its drawn cell.
    name = (f"hard_{bet.number}" if bet.bet_type == BetType.HARDWAY else
            next((cell_name for cell_name, (kind, number) in PROP_TYPES.items()
                  if kind == bet.bet_type and number == bet.number), None))
    if name:
        cell = PROP_REGIONS[name]
        return (cell.right - 25, cell.bottom - 25)
    raise ValueError(f"No table zone for {bet.bet_type}")


def stack_positions(bets):
    counts = {}
    output = []
    for bet in bets:
        # Traveling line bets need independent chip slots for each number;
        # before travel they are arranged in their Come / Don't Come boxes.
        key = ((bet.bet_type, bet.number)
               if bet.bet_type in (BetType.COME, BetType.DONT_COME)
               else bet.bet_type)
        index = counts.get(key, 0)
        counts[key] = index + 1
        output.append((bet, stack_center(bet, index)))
    return output


def stack_at(position, bets):
    """Find the topmost wager marker within its visible chip token."""
    positioned = stack_positions(bets)
    for index in range(len(positioned) - 1, -1, -1):
        bet, center = positioned[index]
        if (position[0] - center[0]) ** 2 + (position[1] - center[1]) ** 2 <= 22 ** 2:
            return bet
    return None


def draw_chip_stacks(surface, bets, small_font):
    for bet, center in stack_positions(bets):
        x, y = center
        pygame.draw.circle(surface, (5, 20, 15), (x + 2, y + 3), 21)
        pygame.draw.circle(surface, (176, 127, 48), center, 20)
        pygame.draw.circle(surface, (28, 52, 42), center, 16)
        pygame.draw.circle(surface, (236, 203, 123), center, 13, 1)
        amount = small_font.render(f"${bet.amount}", True, (255, 246, 221))
        surface.blit(amount, amount.get_rect(center=center))
        if bet.odds:
            odds = small_font.render(f"+{bet.odds}", True, (255, 227, 150))
            surface.blit(odds, odds.get_rect(center=(x + 22, y + 20)))
