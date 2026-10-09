"""Static craps table artwork. Drawing only -- no game logic lives here."""
import pygame

WINDOW_SIZE = (1200, 700)

RAIL_COLOR = (92, 58, 30)
FELT_COLOR = (14, 105, 62)
LINE_COLOR = (240, 230, 200)
PASS_COLOR = (230, 190, 70)

RAIL_WIDTH = 30
LINE_THICKNESS = 3

# Each region is (label, Rect). One loop draws them all, so adding or moving
# a region is a one-line change.
PLACE_NUMBERS = [4, 5, 6, 8, 9, 10]
PLACE_LABELS = {4: "4", 5: "5", 6: "SIX", 8: "8", 9: "NINE", 10: "10"}
PLACE_BOX_W, PLACE_BOX_H = 130, 90
PLACE_START_X = (WINDOW_SIZE[0] - PLACE_BOX_W * len(PLACE_NUMBERS)) // 2

# point number -> its place box, so the puck knows where to sit
PLACE_RECTS = {
    number: pygame.Rect(PLACE_START_X + i * PLACE_BOX_W, 50, PLACE_BOX_W, PLACE_BOX_H)
    for i, number in enumerate(PLACE_NUMBERS)
}

REGIONS = [(PLACE_LABELS[number], rect) for number, rect in PLACE_RECTS.items()]
REGIONS += [
    ("COME", pygame.Rect(210, 150, 780, 65)),
    ("FIELD   2   3   4   9   10   11   12", pygame.Rect(210, 225, 780, 65)),
    ("DON'T PASS BAR", pygame.Rect(60, 530, 1080, 50)),
]

# The pass line gets its own highlight color, so it is kept separate.
PASS_LINE = ("PASS LINE", pygame.Rect(60, 590, 1080, 60))

# The ON/OFF puck. OFF rests beside the COME box; ON sits in the point's place box.
PUCK_RADIUS = 16
PUCK_REST_CENTER = (150, 182)

# Empty middle of the table where the dice land.
DICE_AREA_CENTER = (WINDOW_SIZE[0] // 2, 400)


def draw_board(screen, label_font):
    """Draw the rail, felt, and every betting region onto `screen`."""
    screen.fill(RAIL_COLOR)
    felt = pygame.Rect(
        RAIL_WIDTH, RAIL_WIDTH,
        WINDOW_SIZE[0] - 2 * RAIL_WIDTH, WINDOW_SIZE[1] - 2 * RAIL_WIDTH,
    )
    pygame.draw.rect(screen, FELT_COLOR, felt)

    for label, rect in REGIONS:
        _draw_region(screen, label_font, label, rect, LINE_COLOR)
    _draw_region(screen, label_font, *PASS_LINE, PASS_COLOR)


def _draw_region(screen, font, label, rect, color):
    pygame.draw.rect(screen, color, rect, LINE_THICKNESS)
    text = font.render(label, True, color)
    screen.blit(text, text.get_rect(center=rect.center))


def draw_puck(screen, font, point):
    """Draw the puck. `point` is the point number, or None when the point is off."""
    if point is None:
        center, fill, text_color, label = PUCK_REST_CENTER, (20, 20, 20), (255, 255, 255), "OFF"
    else:
        box = PLACE_RECTS[point]
        center = (box.centerx, box.bottom - PUCK_RADIUS - 4)
        fill, text_color, label = (255, 255, 255), (20, 20, 20), "ON"

    pygame.draw.circle(screen, fill, center, PUCK_RADIUS)
    pygame.draw.circle(screen, LINE_COLOR, center, PUCK_RADIUS, 2)
    text = font.render(label, True, text_color)
    screen.blit(text, text.get_rect(center=center))    