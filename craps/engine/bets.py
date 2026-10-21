from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BetType(Enum):
    PASS_LINE = "pass_line"
    DONT_PASS = "dont_pass"
    COME = "come"
    DONT_COME = "dont_come"
    FIELD = "field"
    PLACE = "place"
    HARDWAY = "hardway"
    ANY_SEVEN = "any_seven"
    ACE_DEUCE = "ace_deuce"
    ACES = "aces"
    BOXCARS = "boxcars"
    YO_ELEVEN = "yo_eleven"
    ANY_CRAPS = "any_craps"


@dataclass
class Bet:
    bet_type: BetType
    amount: int
    number: Optional[int] = None
    odds: int = 0
    id: int = 0


class BetOutcome(Enum):
    WIN = "win"
    LOSE = "lose"
    PUSH = "push"
    NO_ACTION = "no_action"


@dataclass
class BetResult:
    bet: Bet
    outcome: BetOutcome
    amount: int = 0  # gross return credited to bankroll (stake was debited at placement)
