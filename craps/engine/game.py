from typing import Optional
from .bets import Bet
from .outcomes import RollResult
from .outcomes import RollOutcome
from .settlement import settle_bet
from .config import DEFAULT_TABLE_RULES, TableRules


class CrapsEngine:
    def __init__(self, field_two_payout: int | None = None, dont_pass_12_push: bool | None = None,
                 field_twelve_payout: int | None = None, rules: TableRules = DEFAULT_TABLE_RULES):
        if not isinstance(rules, TableRules):
            raise TypeError("rules must be a TableRules configuration")
        self.point_on: bool = False
        self.point: Optional[int] = None
        self.rules = rules
        self.field_two_payout = rules.field_two_payout if field_two_payout is None else field_two_payout
        self.field_twelve_payout = rules.field_twelve_payout if field_twelve_payout is None else field_twelve_payout
        self.dont_pass_12_push = rules.dont_pass_12_push if dont_pass_12_push is None else dont_pass_12_push
        if self.field_two_payout not in (2, 3) or self.field_twelve_payout not in (2, 3):
            raise ValueError("Field 2 and 12 payouts must be 2:1 or 3:1")
        self.roll_history: list[tuple[int, int]] = []

    def resolve_roll(self, dice: tuple[int, int], bets: list[Bet]) -> RollResult:
        if (not isinstance(dice, (tuple, list)) or len(dice) != 2
                or any(type(value) is not int or not 1 <= value <= 6 for value in dice)):
            raise ValueError("A roll must contain two integers from 1 to 6")
        if not isinstance(bets, (tuple, list)) or any(not isinstance(bet, Bet) for bet in bets):
            raise ValueError("bets must be a list of Bet objects")
        dice = tuple(dice)
        # Settle every bet first, against the point as it stood BEFORE this roll.
        bet_results = [settle_bet(bet, dice, self.point, self.field_two_payout,
                                  self.dont_pass_12_push, self.field_twelve_payout, self.rules) for bet in bets]
        self.roll_history.append(dice)

        roll_sum = sum(dice)
        loss = (2, 3, 12)
        win = (7, 11)
        if self.point_on:
            if roll_sum == 7:
                self.point_on = False
                self.point = None
                return RollResult(outcome=RollOutcome.LOSE, point=None, bet_results=bet_results)
            elif roll_sum == self.point:
                self.point_on = False
                self.point = None
                return RollResult(outcome=RollOutcome.WIN, point=None, bet_results=bet_results)
            else:
                return RollResult(outcome=RollOutcome.CONTINUE, point=self.point, bet_results=bet_results)
        else:
            if roll_sum in loss:
                self.point_on = False
                return RollResult(outcome=RollOutcome.LOSE, point=None, bet_results=bet_results)
            elif roll_sum in win:
                self.point_on = False
                return RollResult(outcome=RollOutcome.WIN, point=None, bet_results=bet_results)
            else:
                self.point_on = True
                self.point = roll_sum
                return RollResult(outcome=RollOutcome.POINT_ESTABLISHED, point=roll_sum, bet_results=bet_results)

    def reset(self) -> None:
        """Return to the come-out phase."""
        self.point_on = False
        self.point = None
        self.roll_history.clear()
