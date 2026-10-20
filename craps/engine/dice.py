import random

def roll_dice():
    """Return two independent six-sided die results."""
    return (random.randint(1,6), random.randint(1,6))
