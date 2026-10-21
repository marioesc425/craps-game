"""Static craps table artwork. Drawing only -- no game logic lives here.

All geometry is measured from a reference table image that is 800x400 pixels
("ref" units below) and multiplied by SCALE, so the whole table can be resized
by changing that one number. The table is drawn once onto a cached surface and
blitted every frame.

Every betting area's shape lives in REGIONS (name -> Rect or polygon points),
so table interaction hit testing uses the same geometry as the artwork.
"""
import math
from functools import cache

import pygame

from craps.ui.dice_view import PIP_LAYOUTS
from craps.engine.config import DEFAULT_TABLE_RULES
from craps.engine.bets import BetType
from craps.engine.settlement import HARDWAY_PAYOUTS, PLACE_PAYOUTS, PROPOSITION_PAYOUTS

SCALE = 1.75
WINDOW_SIZE = (1400, 700)  # the 800x400 reference times SCALE

FELT = (13, 88, 63)
WHITE = (238, 229, 205)
YELLOW = (230, 190, 93)
RED = (176, 54, 48)
BACKGROUND = (12, 21, 25)
RAIL = (91, 54, 31)
LINE_W = 3

# First font found wins. For a shipped game, bundle a .ttf file instead of
# relying on whatever the player's system has installed.
SERIF_FONTS = "timesnewroman,times,georgia,liberationserif,freeserif,dejavuserif"


# --- Scaling helpers (ref units in, window pixels out) -----------------------


def _p(x, y):
    return (round(x * SCALE), round(y * SCALE))


def _box(x0, y0, x1, y1):
    """A Rect from corner coordinates, so neighbouring boxes share exact edges."""
    left, top = round(x0 * SCALE), round(y0 * SCALE)
    return pygame.Rect(left, top, round(x1 * SCALE) - left, round(y1 * SCALE) - top)


def _poly(*points):
    return [_p(x, y) for x, y in points]


def _arc(cx, cy, radius, start_deg, end_deg, steps=20):
    """Points along an arc. 180 degrees is left of center, 90 is below it."""
    points = []
    for i in range(steps + 1):
        rad = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        points.append((cx + radius * math.cos(rad), cy + radius * math.sin(rad)))
    return points


# --- Geometry (ref units) ----------------------------------------------------

ARC_CENTER = (100, 250)    # center of the curved bottom-left corner
OUTER_R, INNER_R = 75, 37.5

# Left bands: Pass Line (outer) and Don't Pass Bar (inner). Both tops sit on
# one diagonal running from (25, 76) up to (101, 25).
PASS_LINE_SHAPE = _poly(
    (25, 76), (25, 250), *_arc(*ARC_CENTER, OUTER_R, 180, 90),
    (476, 325), (476, 287.5), *_arc(*ARC_CENTER, INNER_R, 90, 180),
    (62.5, 50.8),
)
DONT_PASS_SIDE_SHAPE = _poly((62.5, 50.8), (101, 25), (101, 188), (62.5, 188))
BIG_6_8_SHAPE = _poly(
    (62.5, 188), (101, 188), (163.5, 250), (163.5, 287.5), (100, 287.5),
    *_arc(*ARC_CENTER, INNER_R, 90, 180),
)

# The number row: six equal columns, with an empty cell above each number.
NUM_X = [163.5 + 62.4 * i for i in range(7)]
NUMBERS = (4, 5, 6, 8, 9, 10)
PLACE_RECTS = {n: _box(NUM_X[i], 55, NUM_X[i + 1], 117) for i, n in enumerate(NUMBERS)}
TOP_CELLS = {n: _box(NUM_X[i], 25, NUM_X[i + 1], 47) for i, n in enumerate(NUMBERS)}

TABLE_REGIONS = {
    "pass_line": PASS_LINE_SHAPE,
    "dont_pass_side": DONT_PASS_SIDE_SHAPE,
    "big_6_8": BIG_6_8_SHAPE,
    "dont_come_bar": _box(101, 25, 163.5, 125),
    "come": _box(101, 125, 476, 188),
    "field": _poly((101, 188), (476, 188), (476, 250), (163.5, 250)),
    "dont_pass_bottom": _box(163.5, 250, 476, 287.5),
    **{f"place_{n}": rect for n, rect in PLACE_RECTS.items()},
}

# Proposition bets (right-hand box), in ref units: name -> (x0, y0, x1, y1).
PROP_LEFT, PROP_MID, PROP_RIGHT = 550, 662.5, 775
PROP_ROW_Y = (149.5, 194.5, 239.5, 284.5, 329.5, 374.5)
PROP_CELLS = {
    "hard_6": (550, 149.5, PROP_MID, 194.5),
    "hard_10": (PROP_MID, 149.5, 775, 194.5),
    "hard_8": (550, 194.5, PROP_MID, 239.5),
    "hard_4": (PROP_MID, 194.5, 775, 239.5),
    "ace_deuce": (550, 239.5, PROP_MID, 284.5),
    "aces": (PROP_MID, 239.5, 775, 284.5),
    "boxcars": (550, 284.5, PROP_MID, 329.5),
    "yo_eleven": (PROP_MID, 284.5, 775, 329.5),
    "any_seven": (550, 329.5, PROP_MID, 374.5),
    "any_craps": (PROP_MID, 329.5, 775, 374.5),
}
PROP_REGIONS = {name: _box(*coords) for name, coords in PROP_CELLS.items()}

REGIONS = {**TABLE_REGIONS, **PROP_REGIONS}

PROP_LABELS = {
    "hard_6": "HARD 6", "hard_10": "HARD 10", "hard_8": "HARD 8", "hard_4": "HARD 4",
    "any_seven": "ANY SEVEN", "ace_deuce": "ACE-DEUCE", "aces": "ACES",
    "boxcars": "BOXCARS", "yo_eleven": "YO (11)", "any_craps": "ANY CRAPS (2/3/12)",
}
PROP_TYPES = {
    "hard_6": (BetType.HARDWAY, 6), "hard_10": (BetType.HARDWAY, 10),
    "hard_8": (BetType.HARDWAY, 8), "hard_4": (BetType.HARDWAY, 4),
    "any_seven": (BetType.ANY_SEVEN, None), "ace_deuce": (BetType.ACE_DEUCE, None),
    "aces": (BetType.ACES, None), "boxcars": (BetType.BOXCARS, None),
    "yo_eleven": (BetType.YO_ELEVEN, None), "any_craps": (BetType.ANY_CRAPS, None),
}


def _payout_label(name):
    bet_type, number = PROP_TYPES[name]
    if bet_type == BetType.HARDWAY:
        net, _ = HARDWAY_PAYOUTS[number]
    else:
        _, net = PROPOSITION_PAYOUTS[bet_type]
    return f"{net}:1"

# --- Game overlay positions (window pixels) ----------------------------------

# The ON/OFF puck: ON sits in the empty cell above the point; OFF rests on the
# open felt beside the number row.
PUCK_RADIUS = 14
PUCK_REST_CENTER = _p(507, 152)

# Open felt above the proposition box, where the dice, outcome and messages go.
DICE_AREA_CENTER = (1158, 100)


# --- Public drawing functions --------------------------------------------------


def draw_board(screen, rules=DEFAULT_TABLE_RULES):
    """Draw the whole table onto `screen`."""
    screen.blit(_render_board(rules.field_two_payout, rules.field_twelve_payout), (0, 0))


def draw_puck(screen, font, point):
    """Draw the puck. `point` is the point number, or None when the point is off."""
    if point is None:
        center, fill, text_color, label = PUCK_REST_CENTER, (20, 20, 20), WHITE, "OFF"
    else:
        center, fill, text_color, label = TOP_CELLS[point].center, WHITE, (20, 20, 20), "ON"

    pygame.draw.circle(screen, fill, center, PUCK_RADIUS)
    pygame.draw.circle(screen, WHITE, center, PUCK_RADIUS, 2)
    text = font.render(label, True, text_color)
    screen.blit(text, text.get_rect(center=center))


# --- Rendering ------------------------------------------------------------------


@cache
def _font(size, bold, italic):
    return pygame.font.SysFont(SERIF_FONTS, round(size * SCALE), bold=bold, italic=italic)


def _text(surface, text, size, color, center, angle=0, bold=True, italic=False, spacing=0):
    """Draw text centered on `center`. Size, center and spacing are in ref units."""
    font = _font(size, bold, italic)
    glyphs = [font.render(ch, True, color) for ch in text]
    gap = round(spacing * SCALE)
    width = sum(g.get_width() for g in glyphs) + gap * (len(glyphs) - 1)
    line = pygame.Surface((width, font.get_height()), pygame.SRCALPHA)
    x = 0
    for glyph in glyphs:
        line.blit(glyph, (x, 0))
        x += glyph.get_width() + gap
    if angle:
        line = pygame.transform.rotozoom(line, angle, 1)
    surface.blit(line, line.get_rect(center=_p(*center)))


def _die(surface, center, value, size):
    """A small yellow die with felt-colored pips. Center and size in ref units."""
    side = round(size * SCALE)
    rect = pygame.Rect(0, 0, side, side)
    rect.center = _p(*center)
    pygame.draw.rect(surface, YELLOW, rect, border_radius=max(2, round(side * 0.18)))
    for fx, fy in PIP_LAYOUTS[value]:
        pip = (rect.left + round(side * fx), rect.top + round(side * fy))
        pygame.draw.circle(surface, FELT, pip, max(1, round(side * 0.09)))


def _dice_pair(surface, center, values, size, spacing):
    cx, cy = center
    _die(surface, (cx - spacing / 2, cy), values[0], size)
    _die(surface, (cx + spacing / 2, cy), values[1], size)


def _line(surface, start, end, width=LINE_W):
    pygame.draw.line(surface, WHITE, _p(*start), _p(*end), width)


@cache
def _render_board(field_two_payout=2, field_twelve_payout=2):
    surface = pygame.Surface(WINDOW_SIZE)
    surface.fill(BACKGROUND)
    pygame.draw.rect(surface, RAIL, pygame.Rect(13, 13, WINDOW_SIZE[0]-26, WINDOW_SIZE[1]-26), border_radius=34)
    pygame.draw.rect(surface, YELLOW, pygame.Rect(20, 20, WINDOW_SIZE[0]-40, WINDOW_SIZE[1]-40), 2, border_radius=30)
    pygame.draw.rect(surface, FELT, pygame.Rect(31, 31, WINDOW_SIZE[0]-62, WINDOW_SIZE[1]-62), border_radius=25)
    for shape in TABLE_REGIONS.values():
        if isinstance(shape, pygame.Rect):
            pygame.draw.rect(surface, WHITE, shape, LINE_W)
        else:
            pygame.draw.polygon(surface, WHITE, shape, LINE_W)
    _draw_number_row_lines(surface)
    _draw_proposition_box(surface)
    _draw_left_side(surface)
    _draw_number_row(surface)
    _draw_middle(surface, field_two_payout, field_twelve_payout)
    _draw_propositions(surface)
    return surface


def _draw_number_row_lines(surface):
    # Strips above and below the numbers, and the column dividers through them.
    for y in (47, 55, 117):
        _line(surface, (NUM_X[0], y), (NUM_X[6], y))
    pygame.draw.rect(surface, WHITE, _box(NUM_X[0], 25, NUM_X[6], 125), LINE_W)
    for x in NUM_X[1:6]:
        _line(surface, (x, 25), (x, 125))


def _draw_proposition_box(surface):
    outline = _box(PROP_LEFT, PROP_ROW_Y[0], PROP_RIGHT, PROP_ROW_Y[-1])
    for index, (y0, y1) in enumerate(zip(PROP_ROW_Y, PROP_ROW_Y[1:])):
        fill = (8, 67, 50) if index % 2 == 0 else (10, 75, 56)
        pygame.draw.rect(surface, fill, _box(PROP_LEFT, y0, PROP_RIGHT, y1))
    pygame.draw.rect(surface, YELLOW, outline, LINE_W, border_radius=round(8 * SCALE))
    for y in PROP_ROW_Y[1:-1]:
        _line(surface, (PROP_LEFT, y), (PROP_RIGHT, y), 2)
    _line(surface, (PROP_MID, PROP_ROW_Y[0]), (PROP_MID, PROP_ROW_Y[-1]), 2)


def _draw_left_side(surface):
    # Bands: lettering follows the table edge, reading top to bottom.
    _text(surface, "PASS LINE", 22, WHITE, (43, 146), angle=-90, spacing=3)
    _text(surface, "Don't Pass Bar", 15.5, WHITE, (83, 98), angle=-90, italic=True)
    _die(surface, (82, 159), 6, 11)
    _die(surface, (82, 176), 6, 11)

    # Don't Come Bar.
    for i, word in enumerate(("Don't", "Come", "Bar")):
        _text(surface, word, 17, WHITE, (132, 45 + i * 17.5))
    _dice_pair(surface, (132, 103), (6, 6), 14, 20)

    # BIG 6 / BIG 8 corner: a divider with B-I-G stacked in its gap.
    _text(surface, "6", 38, RED, (85, 224), italic=True)
    _text(surface, "8", 43, RED, (128.5, 263.5), italic=True)
    _line(surface, (131.9, 220), (123.7, 228.1), 2)
    _line(surface, (85, 268.1), (76.3, 276.9), 2)
    for letter, pos in (("B", (115.6, 235)), ("I", (105.6, 246.9)), ("G", (93.75, 260))):
        _text(surface, letter, 13, WHITE, pos, angle=-45, bold=False)


def _draw_number_row(surface):
    for number, rect in PLACE_RECTS.items():
        center = (rect.centerx / SCALE, 86.7)
        n, d = PLACE_PAYOUTS[number]
        _text(surface, f"{n}:{d}", 12, WHITE, (center[0], 35.5))
        if number == 6:
            _text(surface, "SIX", 22, YELLOW, center, angle=18, italic=True)
        elif number == 9:
            _text(surface, "NINE", 22, YELLOW, center, angle=18, italic=True)
        else:
            _text(surface, str(number), 40, YELLOW, center)


def _draw_middle(surface, field_two_payout=2, field_twelve_payout=2):
    _text(surface, "COME", 50, RED, (270, 157))

    # FIELD: 2 and 12 are circled.
    for x in (199, 421):
        pygame.draw.circle(surface, YELLOW, _p(x, 215), round(15 * SCALE), 2)
    _text(surface, "2", 17, YELLOW, (199, 215))
    _text(surface, "12", 17, YELLOW, (421, 215))
    _text(surface, "\u2022 3 \u2022 4 \u2022 9 \u2022 10 \u2022 11 \u2022", 19.5, YELLOW, (310, 214))
    _text(surface, "FIELD", 23, YELLOW, (310, 231))
    _text(surface, f"2 PAYS {field_two_payout}:1  ·  12 PAYS {field_twelve_payout}:1",
          10, WHITE, (310, 244), bold=False)

    # Bottom bands.
    _text(surface, "Don't Pass Bar", 21, WHITE, (247, 269), italic=True)
    _dice_pair(surface, (345, 269), (6, 6), 14, 19)
    _text(surface, "PASS LINE", 24, WHITE, (259, 306), spacing=4)


def _draw_propositions(surface):
    dice_faces = {
        "hard_6": (3, 3), "hard_10": (5, 5), "hard_8": (4, 4),
        "hard_4": (2, 2), "ace_deuce": (1, 2), "aces": (1, 1),
        "boxcars": (6, 6), "yo_eleven": (5, 6), "any_seven": (3, 4),
        "any_craps": (1, 2),
    }
    for name, label in PROP_LABELS.items():
        x0, y0, x1, y1 = PROP_CELLS[name]
        # Keep labels and dice in the same bounded cell, leaving the lower
        # right corner clear for the wager stack drawn by the betting UI.
        text_x = x0 + 66
        _text(surface, label.replace(" (2/3/12)", ""), 9, WHITE, (text_x, y0 + 13))
        _text(surface, f"PAYS  {_payout_label(name)}", 8, YELLOW, (text_x, y0 + 29))
        _dice_pair(surface, (x0 + 25, y0 + 23), dice_faces[name], 10, 12)
