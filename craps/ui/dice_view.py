"""Draws a single die face with pips. Drawing only -- no game logic lives here."""
import pygame

DIE_COLOR = (247, 245, 236)
PIP_COLOR = (30, 34, 32)
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
    shadow = rect.move(3, 5)
    pygame.draw.rect(screen, (5, 18, 13), shadow, border_radius=CORNER_RADIUS + 2)
    pygame.draw.rect(screen, (194, 191, 177), rect, border_radius=CORNER_RADIUS + 2)
    face = rect.inflate(-4, -4)
    pygame.draw.rect(screen, DIE_COLOR, face, border_radius=CORNER_RADIUS)
    pygame.draw.line(screen, (255, 255, 250), (face.left+7, face.top+3), (face.right-8, face.top+3), 2)
    pygame.draw.line(screen, (223, 220, 207), (face.left+5, face.bottom-4), (face.right-6, face.bottom-4), 2)
    pip_radius = rect.width // 10
    for fx, fy in PIP_LAYOUTS[value]:
        center = (face.left + round(face.width * fx), face.top + round(face.height * fy))
        pygame.draw.circle(screen, (0, 0, 0), (center[0]+1, center[1]+1), pip_radius+1)
        pygame.draw.circle(screen, PIP_COLOR, center, pip_radius)
        pygame.draw.circle(screen, (69, 73, 70), (center[0]-1, center[1]-1), max(1, pip_radius//3))
