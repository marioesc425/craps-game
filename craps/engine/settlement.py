"""Settles one bet against one roll. Rules only -- no drawing, no bankroll."""
from typing import Optional

from .bets import Bet, BetOutcome, BetResult, BetType

# Payout ratios as (numerator, denominator): winnings = amount * num // den.
# Whole-dollar bets mean odd amounts round down, in the house's favor.
FIELD_PAYOUTS = {
    2: (2, 1), 3: (1, 1), 4: (1, 1), 9: (1, 1), 10: (1, 1), 11: (1, 1), 12: (3, 1),
}
PLACE_PAYOUTS = {
    4: (9, 5), 5: (7, 5), 6: (7, 6), 8: (7, 6), 9: (7, 5), 10: (9, 5),
}


def settle_bet(bet: Bet, dice: tuple[int, int], point: Optional[int]) -> BetResult:
    """Settle one bet against a roll.

    `point` is the point as it stood BEFORE this roll (None means come-out).
    """
    settler = _SETTLERS.get(bet.bet_type)
    if settler is None:
        raise NotImplementedError(f"No settlement rule for {bet.bet_type}")
    return settler(bet, dice, point)


def _win(bet: Bet, winnings: int) -> BetResult:
    return BetResult(bet, BetOutcome.WIN, winnings)


def _lose(bet: Bet) -> BetResult:
    return BetResult(bet, BetOutcome.LOSE, -bet.amount)


def _no_action(bet: Bet) -> BetResult:
    return BetResult(bet, BetOutcome.NO_ACTION)


def _settle_pass_line(bet, dice, point):
    total = sum(dice)
    if point is None:                       # come-out roll
        if total in (7, 11):
            return _win(bet, bet.amount)
        if total in (2, 3, 12):
            return _lose(bet)
    else:                                   # point phase
        if total == point:
            return _win(bet, bet.amount)
        if total == 7:
            return _lose(bet)
    return _no_action(bet)


def _settle_field(bet, dice, point):
    total = sum(dice)
    if total in FIELD_PAYOUTS:
        numerator, denominator = FIELD_PAYOUTS[total]
        return _win(bet, bet.amount * numerator // denominator)
    return _lose(bet)                       # 5, 6, 7, 8


def _settle_place(bet, dice, point):
    total = sum(dice)
    if point is None:                       # place bets are off on the come-out
        return _no_action(bet)
    if total == bet.number:
        numerator, denominator = PLACE_PAYOUTS[bet.number]
        return _win(bet, bet.amount * numerator // denominator)
    if total == 7:
        return _lose(bet)
    return _no_action(bet)


# Adding a bet type = write one settler above and add one line here.
_SETTLERS = {
    BetType.PASS_LINE: _settle_pass_line,
    BetType.FIELD: _settle_field,
    BetType.PLACE: _settle_place,
}