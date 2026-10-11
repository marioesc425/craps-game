from .outcomes import RollResult, RollOutcome

STARTING_BANKROLL = 100
MIN_BET = 5


class InvalidBetError(ValueError):
    """Raised when a bet can't be placed. The message says why."""


class Player:
    def __init__(self):
        self.current_bet = None
        self.bankroll = STARTING_BANKROLL

    def settle(self, result: RollResult) -> None:
        if result.outcome in (RollOutcome.WIN, RollOutcome.LOSE):
            self.bankroll += result.amount
            self.current_bet = None

    def place_bet(self, amount: int) -> None:
        if self.current_bet is not None:
            raise InvalidBetError("Bet already placed")
        if amount < MIN_BET:
            raise InvalidBetError(f"Please bet at least ${MIN_BET}")
        if amount > self.bankroll:
            raise InvalidBetError(f"Not enough funds: you have ${self.bankroll}")
        self.current_bet = amount

    def can_play(self) -> bool:
        return self.bankroll >= MIN_BET