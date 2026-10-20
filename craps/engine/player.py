from .bets import Bet, BetOutcome
from .settlement import PLACE_PAYOUTS

STARTING_BANKROLL = 100
MIN_BET = 5
CHIP_UNIT = 1
MAX_ODDS_MULTIPLIER = 3


class InvalidBetError(ValueError):
    pass


class Player:
    def __init__(self, max_odds_multiplier=MAX_ODDS_MULTIPLIER):
        if max_odds_multiplier not in (0, 1, 2, 3, 4, 5, 10):
            raise ValueError("Unsupported odds limit")
        self.max_odds_multiplier = max_odds_multiplier
        self.bankroll = STARTING_BANKROLL
        self.active_bets: list[Bet] = []
        self._next_id = 1
        self._settled_bets = []

    @property
    def current_bet(self):
        return next((b.amount for b in self.active_bets if b.bet_type.value == "pass_line"), None)

    def place_wager(self, bet_type, amount, number=None, odds=0, point=None):
        from .bets import BetType
        if not isinstance(bet_type, BetType) or type(amount) is not int or amount < MIN_BET or amount % CHIP_UNIT:
            raise InvalidBetError("Choose a valid bet of at least $5 in $1 chips")
        if type(odds) is not int or odds < 0:
            raise InvalidBetError("Odds must be a nonnegative whole-dollar amount")
        needs_number = bet_type in (BetType.PLACE, BetType.HARDWAY)
        if needs_number and number not in ((4,5,6,8,9,10) if bet_type == BetType.PLACE else (4,6,8,10)):
            raise InvalidBetError("Choose a valid number for this bet")
        if bet_type == BetType.PLACE:
            n, d = PLACE_PAYOUTS[number]
            if amount * n % d:
                raise InvalidBetError(f"${amount} cannot pay exactly on Place {number}; choose a compatible wager")
        if bet_type in (BetType.PASS_LINE, BetType.DONT_PASS) and point is not None:
            raise InvalidBetError("Pass and Don't Pass bets are available on the come-out")
        if bet_type in (BetType.COME, BetType.DONT_COME) and point is None:
            raise InvalidBetError("Come and Don't Come bets require an established point")
        if odds:
            if bet_type not in (BetType.PASS_LINE, BetType.DONT_PASS, BetType.COME, BetType.DONT_COME):
                raise InvalidBetError("Odds are only available on line bets")
            if bet_type in (BetType.COME, BetType.DONT_COME):
                raise InvalidBetError("Place Come odds after that wager establishes a number")
            if odds < 0 or odds > amount * self.max_odds_multiplier or odds % CHIP_UNIT:
                raise InvalidBetError(f"Odds limit is {self.max_odds_multiplier}x the base wager")
            if bet_type in (BetType.PASS_LINE, BetType.DONT_PASS) and point is None:
                raise InvalidBetError("Odds require an established number")
        cost = amount + odds
        if cost > self.bankroll:
            raise InvalidBetError(f"Not enough funds: you have ${self.bankroll}")
        if bet_type in (BetType.PASS_LINE, BetType.DONT_PASS) and any(b.bet_type == bet_type for b in self.active_bets):
            raise InvalidBetError("That line wager is already active")
        wager = Bet(bet_type, amount, number, odds, self._next_id)
        self._next_id += 1
        self.bankroll -= cost
        self.active_bets.append(wager)
        return wager

    def place_bet(self, amount):
        from .bets import BetType
        return self.place_wager(BetType.PASS_LINE, amount)

    def add_odds(self, bet, amount, point):
        from .bets import BetType
        if not any(current is bet for current in self.active_bets) or bet.bet_type not in (BetType.PASS_LINE, BetType.DONT_PASS, BetType.COME, BetType.DONT_COME):
            raise InvalidBetError("Select an active line wager for odds")
        number = bet.number if bet.bet_type in (BetType.COME, BetType.DONT_COME) else point
        if number is None:
            raise InvalidBetError("Odds require an established number")
        if type(amount) is not int or amount <= 0 or amount + bet.odds > bet.amount * self.max_odds_multiplier:
            raise InvalidBetError(f"Odds limit is {self.max_odds_multiplier}x the base wager")
        odds_numbers = {4:(2,1),5:(3,2),6:(6,5),8:(6,5),9:(3,2),10:(2,1)}
        n, d = odds_numbers[number]
        if bet.bet_type in (BetType.DONT_PASS, BetType.DONT_COME): n, d = d, n
        if amount * n % d:
            raise InvalidBetError("That odds amount cannot be paid exactly in whole-dollar chips")
        if amount > self.bankroll:
            raise InvalidBetError(f"Not enough funds: you have ${self.bankroll}")
        self.bankroll -= amount
        bet.odds += amount

    def increase_wager(self, bet, amount):
        if not any(current is bet for current in self.active_bets):
            raise InvalidBetError("That wager is no longer active")
        if type(amount) is not int or amount <= 0:
            raise InvalidBetError("Choose a positive whole-dollar chip")
        if amount > self.bankroll:
            raise InvalidBetError(f"Not enough funds: you have ${self.bankroll}")
        if bet.bet_type.value == "place":
            n, d = PLACE_PAYOUTS[bet.number]
            if (bet.amount + amount) * n % d:
                raise InvalidBetError(f"That chip would make the Place {bet.number} payout fractional")
        if bet.odds > (bet.amount + amount) * self.max_odds_multiplier:
            raise InvalidBetError("This increase would violate the maximum odds limit")
        self.bankroll -= amount
        bet.amount += amount

    def reduce_wager(self, bet, amount):
        if not any(current is bet for current in self.active_bets):
            raise InvalidBetError("That wager is no longer active")
        if type(amount) is not int or amount <= 0 or bet.amount - amount < MIN_BET:
            raise InvalidBetError("Cannot undo that chip without invalidating the wager")
        bet.amount -= amount
        self.bankroll += amount

    def reduce_odds(self, bet, amount):
        if not any(current is bet for current in self.active_bets):
            raise InvalidBetError("That wager is no longer active")
        if type(amount) is not int or amount <= 0 or bet.odds < amount:
            raise InvalidBetError("Cannot undo that odds chip")
        bet.odds -= amount
        self.bankroll += amount

    def undo_wager(self, bet):
        index = next((i for i, current in enumerate(self.active_bets) if current is bet), None)
        if index is None:
            raise InvalidBetError("That wager is no longer active")
        self.bankroll += bet.amount + bet.odds
        self.active_bets.pop(index)

    def settle(self, result):
        for br in result.bet_results:
            active_index = next((i for i, b in enumerate(self.active_bets) if b is br.bet), None)
            if br.outcome != BetOutcome.NO_ACTION and active_index is not None and not any(b is br.bet for b in self._settled_bets):
                self.bankroll += br.amount
                self._settled_bets.append(br.bet)
                self.active_bets.pop(active_index)

    def can_play(self):
        return self.bankroll >= MIN_BET

    def reset(self):
        self.active_bets.clear()
        self._settled_bets.clear()
        self.bankroll = STARTING_BANKROLL
