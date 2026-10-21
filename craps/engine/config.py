"""Central, explicit house rules for the default virtual craps table."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TableRules:
    minimum_bet: int = 1
    maximum_bet: int = 500
    maximum_single_wager: int = 500
    maximum_odds_multiplier: int = 3
    starting_bankroll: int = 100
    chip_denominations: tuple[int, ...] = (1, 5, 25, 100, 500)
    field_two_payout: int = 2
    field_twelve_payout: int = 2
    dont_pass_12_push: bool = True

    def __post_init__(self):
        if type(self.minimum_bet) is not int or self.minimum_bet < 1:
            raise ValueError("Minimum bet must be a positive whole-dollar amount")
        if type(self.maximum_bet) is not int or self.maximum_bet < self.minimum_bet:
            raise ValueError("Maximum bet must be at least the minimum bet")
        if type(self.maximum_single_wager) is not int or self.maximum_single_wager < self.minimum_bet:
            raise ValueError("Maximum single wager must be at least the minimum bet")
        if self.maximum_single_wager > self.maximum_bet:
            raise ValueError("A single wager cannot exceed the base-bet maximum")
        if self.maximum_odds_multiplier not in range(0, 11):
            raise ValueError("Odds multiplier must be between 0x and 10x")
        if type(self.starting_bankroll) is not int or self.starting_bankroll < 0:
            raise ValueError("Starting bankroll must be a nonnegative whole-dollar amount")
        if not self.chip_denominations or any(type(v) is not int or v <= 0 for v in self.chip_denominations):
            raise ValueError("Chip denominations must be positive whole-dollar amounts")
        if self.field_two_payout not in (2, 3) or self.field_twelve_payout not in (2, 3):
            raise ValueError("Field 2 and 12 payouts must each be 2:1 or 3:1")


DEFAULT_TABLE_RULES = TableRules()
