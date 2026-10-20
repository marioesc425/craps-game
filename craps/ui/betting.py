"""Direct wager hit-testing uses the same pixel geometry used to draw the table."""
from dataclasses import dataclass

import pygame

from craps.engine.bets import BetType
from craps.engine.player import InvalidBetError
from craps.engine.settlement import PLACE_PAYOUTS
from craps.ui.board import TABLE_REGIONS, PROP_REGIONS, PLACE_RECTS


@dataclass(frozen=True)
class BettingZone:
    name: str
    bet_type: BetType
    shape: object
    number: int | None = None

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


def zone_at(position):
    """Return the one drawn zone under a pixel position, or None."""
    for zone in ZONES:
        if zone.contains(position):
            return zone
    return None


def wager_available(player, engine, zone, chip):
    if chip > player.bankroll or chip <= 0:
        return False
    if zone.bet_type in (BetType.PASS_LINE, BetType.DONT_PASS):
        if engine.point is not None:
            return False
    elif zone.bet_type in (BetType.COME, BetType.DONT_COME):
        if engine.point is None:
            return False
    if zone.bet_type == BetType.PLACE:
        n, d = PLACE_PAYOUTS[zone.number]
        existing = next((b for b in player.active_bets
                         if b.bet_type == BetType.PLACE and b.number == zone.number), None)
        base = existing.amount if existing else 0
        if (base + chip) * n % d:
            return False
    if chip < 5:
        if zone.bet_type in (BetType.COME, BetType.DONT_COME):
            return False
        return any(b.bet_type == zone.bet_type and b.number == zone.number
                   for b in player.active_bets)
    return True


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
        slots = ((685, 265), (733, 265), (781, 265), (685, 312), (733, 312), (781, 312))
        return slots[index % len(slots)]
    if bet.bet_type == BetType.DONT_COME:
        slots = ((198, 73), (232, 73), (266, 73), (198, 118), (232, 118), (266, 118),
                 (198, 163), (232, 163), (266, 163))
        return slots[index % len(slots)]
    if bet.bet_type == BetType.FIELD:
        return (790, 350)
    if bet.bet_type == BetType.PLACE:
        rect = PLACE_RECTS[bet.number]
        return (rect.centerx, rect.bottom - 18)
    # Hardway markers sit at the right edge of each printed proposition box.
    cell = PROP_REGIONS[f"hard_{bet.number}"]
    return (cell.right - 25, cell.centery)


def stack_positions(bets):
    counts = {}
    output = []
    for bet in bets:
        index = counts.get(bet.bet_type, 0)
        counts[bet.bet_type] = index + 1
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
