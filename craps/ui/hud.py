"""Heads-up display: bankroll, bet, control hints, and error messages.

Drawing only -- no game logic lives here. It takes plain values so it never
needs to import the engine or the player.
"""
from typing import NamedTuple

import pygame

PANEL_RECT = pygame.Rect(44, 592, 520, 96)
PANEL_COLOR = (0, 90, 30)
WHITE = (255, 255, 255)
GOLD = (255, 214, 0)
ERROR_COLOR = (255, 190, 170)

HINT_CENTER = (1158, 238)
ERROR_CENTER = (1158, 205)


class HudFonts(NamedTuple):
    label: pygame.font.Font
    value: pygame.font.Font
    hint: pygame.font.Font


def make_hud_fonts():
    """Create the HUD fonts. Call this after pygame.init()."""
    return HudFonts(
        label=pygame.font.Font(None, 22),
        value=pygame.font.Font(None, 44),
        hint=pygame.font.Font(None, 28),
    )


def draw_hud(screen, fonts, bankroll, bet, bet_locked, error):
    """Draw the money panel, the control hint, and any error message.

    bet_locked is True while a bet is on the Pass Line (rolling phase) and
    False while the player is still choosing an amount (betting phase).
    """
    pygame.draw.rect(screen, PANEL_COLOR, PANEL_RECT)
    pygame.draw.rect(screen, WHITE, PANEL_RECT, 3)
    pygame.draw.line(
        screen, WHITE,
        (PANEL_RECT.centerx, PANEL_RECT.top + 12), (PANEL_RECT.centerx, PANEL_RECT.bottom - 12), 2,
    )

    left_x = PANEL_RECT.left + PANEL_RECT.width // 4
    right_x = PANEL_RECT.left + 3 * PANEL_RECT.width // 4
    top = PANEL_RECT.top
    bet_label = "ON PASS LINE" if bet_locked else "NEXT BET"
    bet_color = GOLD if bet_locked else WHITE

    _blit_centered(screen, fonts.label, "BANKROLL", WHITE, (left_x, top + 28))
    _blit_centered(screen, fonts.value, f"${bankroll:.2f}", WHITE, (left_x, top + 62))
    _blit_centered(screen, fonts.label, bet_label, WHITE, (right_x, top + 28))
    _blit_centered(screen, fonts.value, f"${bet:.2f}", bet_color, (right_x, top + 62))

    hint = "SPACE: roll the dice" if bet_locked else "UP / DOWN: change bet     ENTER: place bet"
    _blit_centered(screen, fonts.hint, hint, WHITE, HINT_CENTER)

    if error:
        _blit_centered(screen, fonts.hint, error, ERROR_COLOR, ERROR_CENTER)


def _blit_centered(screen, font, text, color, center):
    surface = font.render(text, True, color)
    screen.blit(surface, surface.get_rect(center=center))