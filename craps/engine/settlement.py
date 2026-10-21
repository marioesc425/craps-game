"""Craps wager rules. BetResult.amount is the gross return, including stake."""
from .bets import Bet, BetOutcome, BetResult, BetType
from .config import DEFAULT_TABLE_RULES, TableRules

VALID_NUMBERS = (4, 5, 6, 8, 9, 10)
PLACE_PAYOUTS = {4: (9, 5), 5: (7, 5), 6: (7, 6), 8: (7, 6), 9: (7, 5), 10: (9, 5)}
HARDWAY_PAYOUTS = {4: (7, 1), 6: (9, 1), 8: (9, 1), 10: (7, 1)}
PROPOSITION_PAYOUTS = {
    BetType.ANY_SEVEN: ({7}, 4),
    BetType.ACE_DEUCE: ({3}, 15),
    BetType.ACES: ({2}, 30),
    BetType.BOXCARS: ({12}, 30),
    BetType.YO_ELEVEN: ({11}, 15),
    BetType.ANY_CRAPS: ({2, 3, 12}, 7),
}


def settle_bet(bet: Bet, dice: tuple[int, int], point: int | None,
               field_two: int | None = None, dont_pass_12_push: bool | None = None,
               field_twelve: int | None = None,
               rules: TableRules = DEFAULT_TABLE_RULES) -> BetResult:
    field_two = rules.field_two_payout if field_two is None else field_two
    field_twelve = rules.field_twelve_payout if field_twelve is None else field_twelve
    dont_pass_12_push = rules.dont_pass_12_push if dont_pass_12_push is None else dont_pass_12_push
    if not isinstance(bet, Bet) or type(bet.amount) is not int or not rules.minimum_bet <= bet.amount <= rules.maximum_single_wager:
        raise ValueError(f"A base wager must be between ${rules.minimum_bet} and ${rules.maximum_single_wager}")
    if type(bet.odds) is not int or bet.odds < 0:
        raise ValueError("Odds must be a nonnegative whole-dollar amount")
    if bet.odds > bet.amount * rules.maximum_odds_multiplier:
        raise ValueError(f"Odds cannot exceed {rules.maximum_odds_multiplier}x the associated base wager")
    if bet.odds and bet.bet_type not in (BetType.PASS_LINE, BetType.DONT_PASS, BetType.COME, BetType.DONT_COME):
        raise ValueError("Odds can only be attached to Pass/Don't Pass/Come/Don't Come wagers")
    if bet.odds and bet.bet_type in (BetType.COME, BetType.DONT_COME) and bet.number is None:
        raise ValueError("Come odds require an established number")
    if bet.odds:
        reference = bet.number if bet.bet_type in (BetType.COME, BetType.DONT_COME) else point
        if reference is None:
            raise ValueError("Odds require an established number")
        if reference not in VALID_NUMBERS:
            raise ValueError("Odds require a valid point number")
        n, d = {4:(2,1), 5:(3,2), 6:(6,5), 8:(6,5), 9:(3,2), 10:(2,1)}[reference]
        if bet.bet_type in (BetType.DONT_PASS, BetType.DONT_COME):
            n, d = d, n
        if bet.odds * n % d:
            raise ValueError("Odds payout is not representable in whole-dollar chips")
    if bet.bet_type == BetType.PLACE and bet.number not in PLACE_PAYOUTS:
        raise ValueError("Place bets require a number from 4, 5, 6, 8, 9, or 10")
    if bet.bet_type == BetType.PLACE:
        numerator, denominator = PLACE_PAYOUTS[bet.number]
        if bet.amount * numerator % denominator:
            raise ValueError(f"Place {bet.number} stake must produce an exact whole-dollar payout")
    if bet.bet_type == BetType.HARDWAY and bet.number not in HARDWAY_PAYOUTS:
        raise ValueError("Hardways require a number of 4, 6, 8, or 10")
    if len(dice) != 2 or any(type(die) is not int or die < 1 or die > 6 for die in dice):
        raise ValueError("A roll must contain two integers from 1 to 6")
    if field_two not in (2, 3) or field_twelve not in (2, 3):
        raise ValueError("Field 2 and 12 payouts must be 2:1 or 3:1")
    total, is_hard = sum(dice), dice[0] == dice[1]
    typ = bet.bet_type
    win = lose = push = False
    mult = (1, 1)
    if typ in (BetType.PASS_LINE, BetType.DONT_PASS, BetType.COME, BetType.DONT_COME):
        dont = typ in (BetType.DONT_PASS, BetType.DONT_COME)
        come = typ in (BetType.COME, BetType.DONT_COME)
        reference = bet.number if come else point
        if reference is None:
            if total in (4, 5, 6, 8, 9, 10):
                if come:
                    bet.number = total
                return _result(bet, BetOutcome.NO_ACTION)
            if dont:
                win = total in (2, 3)
                lose = total in (7, 11)
                push = total == 12 and dont_pass_12_push
                lose = lose or (total == 12 and not dont_pass_12_push)
            else:
                win = total in (7, 11)
                lose = total in (2, 3, 12)
        else:
            win = total == (7 if dont else reference)
            lose = total == (reference if dont else 7)
        if bet.odds and reference is not None and (win or lose):
            n, d = ({4:(2,1),5:(3,2),6:(6,5),8:(6,5),9:(3,2),10:(2,1)}[reference])
            if dont:
                n, d = d, n
            if bet.odds * n % d:
                raise ValueError("Odds payout is not representable in whole-dollar chips")
            odds_return = bet.odds + (bet.odds * n // d) if win else 0
        else:
            odds_return = 0
        if win:
            return _result(bet, BetOutcome.WIN, bet.amount * 2 + odds_return)
        if push:
            return _result(bet, BetOutcome.PUSH, bet.amount + bet.odds)
        if lose:
            return _result(bet, BetOutcome.LOSE)
        return _result(bet, BetOutcome.NO_ACTION)
    if typ == BetType.FIELD:
        if total == 2:
            return _result(bet, BetOutcome.WIN, bet.amount * (1 + field_two))
        if total == 12:
            return _result(bet, BetOutcome.WIN, bet.amount * (1 + field_twelve))
        if total in (3,4,9,10,11):
            return _result(bet, BetOutcome.WIN, bet.amount * 2)
        return _result(bet, BetOutcome.LOSE)
    if typ == BetType.PLACE:
        if point is None:
            return _result(bet, BetOutcome.NO_ACTION)
        if total == 7:
            return _result(bet, BetOutcome.LOSE)
        if total == bet.number:
            n,d = PLACE_PAYOUTS[bet.number]
            if bet.amount * n % d:
                raise ValueError("Place payout is not representable in whole-dollar chips")
            return _result(bet, BetOutcome.WIN, bet.amount + bet.amount*n//d)
        return _result(bet, BetOutcome.NO_ACTION)
    if typ == BetType.HARDWAY:
        if total == 7 or (total == bet.number and not is_hard):
            return _result(bet, BetOutcome.LOSE)
        if total == bet.number and is_hard:
            n,d = HARDWAY_PAYOUTS[bet.number]
            return _result(bet, BetOutcome.WIN, bet.amount + bet.amount*n//d)
        return _result(bet, BetOutcome.NO_ACTION)
    if typ in PROPOSITION_PAYOUTS:
        winning_totals, net_payout = PROPOSITION_PAYOUTS[typ]
        if total in winning_totals:
            return _result(bet, BetOutcome.WIN, bet.amount * (1 + net_payout))
        return _result(bet, BetOutcome.LOSE)
    raise ValueError(f"Unknown bet type: {typ}")


def _result(bet, outcome, returned=0):
    return BetResult(bet, outcome, returned)
