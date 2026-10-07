from typing import Optional
from .outcomes import RollResult
from .outcomes import RollOutcome

    
class CrapsEngine:
    def __init__(self):
        self.point_on: bool = False
        self.point: Optional[int] = None
        
    def resolve_roll(self, roll_sum: int) -> RollResult:
        #If point established
        loss = (2, 3, 12)
        win = (7, 11)
        if self.point_on:
            if roll_sum == 7:
                self.point_on = False
                self.point = None
                return RollResult(outcome=RollOutcome.LOSE, amount=None, point=None)
            elif roll_sum == self.point:
                self.point_on = False
                self.point = None
                return RollResult(outcome=RollOutcome.WIN, amount=None, point=None)
            else:
                return RollResult(outcome=RollOutcome.CONTINUE, amount=None, point=self.point)
        else:
            if roll_sum in loss:
                self.point_on = False
                return RollResult(outcome=RollOutcome.LOSE, amount=None, point=None)
            elif roll_sum in win:
                self.point_on = False
                return RollResult(outcome=RollOutcome.WIN, amount=None, point=None)
            else:
                self.point_on = True
                self.point = roll_sum
                return RollResult(outcome=RollOutcome.POINT_ESTABLISHED, amount=None, point=roll_sum)