from dataclasses import dataclass
from typing import Optional
from enum import Enum

class RollOutcome(Enum):
    WIN = "win"
    LOSE = "lose"
    POINT_ESTABLISHED = "point_established"
    CONTINUE = "continue"
    
@dataclass
class RollResult:
    outcome: RollOutcome
    # Not every outcome needs updated amount and point isn't always established 
    amount: Optional[int] = None
    point: Optional[int] = None