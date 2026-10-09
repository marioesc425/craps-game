"""Draws a single die face with pips. Drawing only -- no game logic lives here."""
import pygame

DIE_COLOR = (255, 255, 255)
PIP_COLOR = (20, 20, 20)
CORNER_RADIUS = 10

# Pip positions as fractions of the die's width/height, so one table works
# at any die size. (0, 0) is the top-left corner, (1, 1) the bottom-right.
L, C, R = 0.27, 0.5, 0.73
T, M, B = 0.27, 0.5, 0.73

PIP_LAYOUTS = {
    1: [(C, M)],
    2: [(L, T), (R, B)],
    3: [(L, T), (C, M), (R, B)],
    4: [(L, T), (R, T), (L, B), (R, B)],
    5: [(L, T), (R, T), (C, M), (L, B), (R, B)],
    6: [(L, T), (R, T), (L, M), (R, M), (L, B), (R, B)],
}


def draw_die(screen, rect, value):
    """Draw a die face showing `value` (1-6) inside `rect`."""
    pygame.draw.rect(screen, DIE_COLOR, rect, border_radius=CORNER_RADIUS)
    pip_radius = rect.width // 10
    for fx, fy in PIP_LAYOUTS[value]:
        center = (rect.left + round(rect.width * fx), rect.top + round(rect.height * fy))
        pygame.draw.circle(screen, PIP_COLOR, center, pip_radius)