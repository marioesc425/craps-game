from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BetType(Enum):
    PASS_LINE = "pass_line"
    FIELD = "field"
    PLACE = "place"


@dataclass
class Bet:
    bet_type: BetType
    amount: int
    number: Optional[int] = None  # only number bets use it; None means "not applicable"
  
    
class BetOutcome(Enum):
    WIN = "win"
    LOSE = "lose"
    PUSH = "push"
    NO_ACTION = "no_action"


@dataclass
class BetResult:
    bet: Bet               # which bet this result is about
    outcome: BetOutcome
    amount: int = 0           # net change in dollars: + for a win, - for a loss