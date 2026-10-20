from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .bets import BetResult


class RollOutcome(Enum):
    WIN = "win"
    LOSE = "lose"
    POINT_ESTABLISHED = "point_established"
    CONTINUE = "continue"


@dataclass
class RollResult:
    outcome: RollOutcome
    point: Optional[int] = None
    bet_results: list[BetResult] = field(default_factory=list)