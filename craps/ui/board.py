"""Static craps table artwork. Drawing only -- no game logic lives here.

The table is drawn once onto a cached surface and blitted every frame.
Every betting area's geometry lives in REGIONS (name -> Rect or polygon
points), so later features such as clicking a bet can reuse the same shapes
the artwork is drawn from. Only the Pass Line is playable today; everything
else is scenery.
"""
import math
from functools import cache

import pygame

from craps.ui.dice_view import PIP_LAYOUTS

WINDOW_SIZE = (1400, 770)

FELT = (0, 153, 51)
WHITE = (255, 255, 255)
YELLOW = (255, 214, 0)
RED = (230, 30, 30)
LINE_W = 3

# First font found wins. For a shipped game, bundle a .ttf file instead of
# relying on whatever the player's system has installed.
SERIF_FONTS = "georgia,timesnewroman,times,liberationserif,dejavuserif"

# --- Geometry -----------------------------------------------------------------

TOP, LEFT, BOTTOM = 45, 40, 725
MAIN_RIGHT = 1000          # right edge of the main (left-hand) layout
PASS_T, DP_T = 55, 45      # thickness of the Pass Line and Don't Pass bands
CORNER_R = 100             # outer radius of the curved bottom-left corner
CHAMFER = 28               # size of the angled corner on the Don't Pass Bar

# Center of the corner arc, and the edges of the two bands.
CX, CY = LEFT + CORNER_R, BOTTOM - CORNER_R
X_PASS_IN, Y_PASS_IN = LEFT + PASS_T, BOTTOM - PASS_T
X_DP_IN, Y_DP_IN = LEFT + PASS_T + DP_T, BOTTOM - PASS_T - DP_T


def _arc(cx, cy, radius, start_deg, end_deg, steps=14):
    """Points along an arc. 180 degrees is left of center, 90 is below it."""
    points = []
    for i in range(steps + 1):
        rad = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        points.append((round(cx + radius * math.cos(rad)), round(cy + radius * math.sin(rad))))
    return points


PASS_LINE_SHAPE = [
    (LEFT, TOP),
    *_arc(CX, CY, CORNER_R, 180, 90),
    (MAIN_RIGHT, BOTTOM),
    (MAIN_RIGHT, Y_PASS_IN),
    *_arc(CX, CY, CORNER_R - PASS_T, 90, 180),
    (X_PASS_IN, TOP),
]
DONT_PASS_SHAPE = [
    (X_PASS_IN, TOP),
    *_arc(CX, CY, CORNER_R - PASS_T, 180, 90),
    (MAIN_RIGHT, Y_PASS_IN),
    (MAIN_RIGHT, Y_DP_IN),
    (X_DP_IN + CHAMFER, Y_DP_IN),
    (X_DP_IN, Y_DP_IN - CHAMFER),
    (X_DP_IN, TOP),
]

PLACE_NUMBERS = (4, 5, 6, 8, 9, 10)
PLACE_BOX_W, PLACE_BOX_H = 115, 110
# point number -> its number box, so the puck knows where to sit
PLACE_RECTS = {
    number: pygame.Rect(300 + i * PLACE_BOX_W, 60, PLACE_BOX_W, PLACE_BOX_H)
    for i, number in enumerate(PLACE_NUMBERS)
}

_R = pygame.Rect
# Proposition bets (right-hand column): two half-width columns, then full width.
PROP_X, PROP_W, COL_W, COL2_X = 1020, 340, 168, 1192

REGIONS = {
    "pass_line": PASS_LINE_SHAPE,
    "dont_pass_bar": DONT_PASS_SHAPE,
    "dont_come_bar": _R(150, 60, 140, 110),
    "come": _R(150, 180, 850, 320),
    "field": _R(150, 510, 850, 105),
    **{f"place_{number}": rect for number, rect in PLACE_RECTS.items()},
    "any_seven": _R(PROP_X, 45, PROP_W, 70),
    "hard_6": _R(PROP_X, 120, COL_W, 85),
    "hard_10": _R(COL2_X, 120, COL_W, 85),
    "hard_8": _R(PROP_X, 209, COL_W, 85),
    "hard_4": _R(COL2_X, 209, COL_W, 85),
    "aces": _R(PROP_X, 300, COL_W, 85),
    "ace_deuce": _R(COL2_X, 300, COL_W, 85),
    "yo": _R(PROP_X, 389, COL_W, 85),
    "boxcars": _R(COL2_X, 389, COL_W, 85),
    "any_craps": _R(PROP_X, 480, PROP_W, 55),
    "c": _R(1020, 541, 110, 55),
    "e": _R(1134, 541, 110, 55),
    "horn": _R(1248, 541, 112, 55),
}

# (region, label, dice shown, payout) for the compact proposition grid.
PROP_CELLS = [
    ("hard_6", "HARD 6", (3, 3), "9 to 1"),
    ("hard_10", "HARD 10", (5, 5), "7 to 1"),
    ("hard_8", "HARD 8", (4, 4), "9 to 1"),
    ("hard_4", "HARD 4", (2, 2), "7 to 1"),
    ("aces", "ACES", (1, 1), "30 to 1"),
    ("ace_deuce", "ACE-DEUCE", (1, 2), "15 to 1"),
    ("yo", "YO", (5, 6), "15 to 1"),
    ("boxcars", "BOXCARS", (6, 6), "30 to 1"),
]

# The ON/OFF puck. OFF rests in the Don't Come Bar; ON sits on the point's box.
PUCK_RADIUS = 14
PUCK_REST_CENTER = (258, 142)

# Middle of the COME area, where the dice land.
DICE_AREA_CENTER = (575, 355)

MINI_DIE = 22

# --- Public drawing functions ---------------------------------------------------


def draw_board(screen):
    """Draw the whole table onto `screen`."""
    screen.blit(_render_board(), (0, 0))


def draw_puck(screen, font, point):
    """Draw the puck. `point` is the point number, or None when the point is off."""
    if point is None:
        center, fill, text_color, label = PUCK_REST_CENTER, (20, 20, 20), WHITE, "OFF"
    else:
        box = PLACE_RECTS[point]
        center = (box.right - 22, box.bottom - 22)
        fill, text_color, label = WHITE, (20, 20, 20), "ON"

    pygame.draw.circle(screen, fill, center, PUCK_RADIUS)
    pygame.draw.circle(screen, WHITE, center, PUCK_RADIUS, 2)
    text = font.render(label, True, text_color)
    screen.blit(text, text.get_rect(center=center))


# --- Rendering helpers ------------------------------------------------------------


@cache
def _serif(size):
    return pygame.font.SysFont(SERIF_FONTS, size, bold=True)


@cache
def _render_board():
    surface = pygame.Surface(WINDOW_SIZE)
    surface.fill(FELT)
    for shape in REGIONS.values():
        if isinstance(shape, pygame.Rect):
            pygame.draw.rect(surface, WHITE, shape, LINE_W)
        else:
            pygame.draw.polygon(surface, WHITE, shape, LINE_W)
    _draw_main_layout(surface)
    _draw_propositions(surface)
    return surface


def _text(surface, text, size, color, center, angle=0):
    image = _serif(size).render(text, True, color)
    if angle:
        image = pygame.transform.rotozoom(image, angle, 1)
    surface.blit(image, image.get_rect(center=center))


def _mini_dice(surface, center, values):
    """Small yellow outlined dice, side by side, centered on `center`."""
    gap = 4
    total = len(values) * MINI_DIE + (len(values) - 1) * gap
    left = center[0] - total // 2
    for i, value in enumerate(values):
        rect = pygame.Rect(left + i * (MINI_DIE + gap), center[1] - MINI_DIE // 2, MINI_DIE, MINI_DIE)
        pygame.draw.rect(surface, YELLOW, rect, 2, border_radius=4)
        for fx, fy in PIP_LAYOUTS[value]:
            pip = (rect.left + round(rect.width * fx), rect.top + round(rect.height * fy))
            pygame.draw.circle(surface, YELLOW, pip, 2)


def _up_arrow(surface, x, y):
    pygame.draw.polygon(surface, RED, [(x, y - 14), (x - 10, y + 6), (x + 10, y + 6)])


def _draw_main_layout(surface):
    # Left-hand bands: lettering follows the table edge.
    mid_y = (TOP + Y_DP_IN) // 2
    _text(surface, "PASS LINE", 38, WHITE, ((LEFT + X_PASS_IN) // 2, mid_y), 90)
    _text(surface, "DON'T PASS BAR", 26, WHITE, ((X_PASS_IN + X_DP_IN) // 2, mid_y), 90)
    _up_arrow(surface, (LEFT + X_PASS_IN) // 2, TOP + 32)
    _up_arrow(surface, (X_PASS_IN + X_DP_IN) // 2, TOP + 32)

    # Bottom bands.
    _text(surface, "PASS LINE", 56, WHITE, ((CX + MAIN_RIGHT) // 2, (Y_PASS_IN + BOTTOM) // 2))
    dp_center = ((X_DP_IN + CHAMFER + MAIN_RIGHT) // 2, (Y_DP_IN + Y_PASS_IN) // 2)
    _text(surface, "DON'T PASS BAR", 30, WHITE, dp_center)
    _mini_dice(surface, (dp_center[0] - 150, dp_center[1]), (6, 6))
    _mini_dice(surface, (dp_center[0] + 150, dp_center[1]), (6, 6))

    # Don't Come Bar.
    for i, word in enumerate(("DON'T", "COME", "BAR")):
        _text(surface, word, 20, RED, (220, 76 + i * 20))
    _mini_dice(surface, (190, 142), (6, 6))

    # Thin divisions above the number boxes, then the numbers themselves.
    for y in (49, 55):
        pygame.draw.line(surface, WHITE, (300, y), (990, y), 2)
    for number, rect in PLACE_RECTS.items():
        # Numbers sit a little high so the puck has room in the lower corner.
        x, y = rect.centerx, rect.centery - 8
        if number == 6:
            _text(surface, "SIX", 46, YELLOW, (x, y), 35)
        elif number == 9:
            _text(surface, "NINE", 40, YELLOW, (x - 8, y - 4), -35)
        else:
            _text(surface, str(number), 84, YELLOW, (x, y))

    # COME.
    _text(surface, "COME", 150, RED, (575, 250))

    # FIELD: 2 and 12 are circled.
    for i, number in enumerate((2, 3, 4, 9, 10, 11, 12)):
        x = 575 + (i - 3) * 95
        _text(surface, str(number), 48, YELLOW, (x, 543))
        if number in (2, 12):
            pygame.draw.circle(surface, YELLOW, (x, 543), 27, 3)
    _text(surface, "FIELD", 34, YELLOW, (575, 594))


def _draw_propositions(surface):
    seven = REGIONS["any_seven"]
    _text(surface, "SEVEN", 42, RED, (seven.centerx, seven.y + 24))
    _text(surface, "4 to 1", 22, WHITE, (seven.centerx, seven.y + 55))
    _mini_dice(surface, (seven.x + 55, seven.centery), (3, 4))
    _mini_dice(surface, (seven.right - 55, seven.centery), (3, 4))

    for key, label, dice, payout in PROP_CELLS:
        rect = REGIONS[key]
        _mini_dice(surface, (rect.centerx, rect.y + 24), dice)
        _text(surface, label, 24, YELLOW, (rect.centerx, rect.y + 52))
        _text(surface, payout, 20, WHITE, (rect.centerx, rect.y + 72))

    craps = REGIONS["any_craps"]
    _text(surface, "ANY CRAPS", 30, RED, (craps.centerx, craps.y + 18))
    _text(surface, "7 to 1", 18, WHITE, (craps.centerx, craps.y + 42))

    _text(surface, "C", 40, YELLOW, REGIONS["c"].center)
    _text(surface, "E", 40, YELLOW, REGIONS["e"].center)
    _text(surface, "HORN", 32, YELLOW, REGIONS["horn"].center)