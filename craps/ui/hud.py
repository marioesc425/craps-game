"""Compact bankroll and selected-denomination display."""
from typing import NamedTuple
import pygame

PANEL_RECT = pygame.Rect(44, 592, 520, 96)
PANEL_COLOR = (0, 67, 47)
WHITE = (247, 238, 215)
GOLD = (230, 190, 93)


class HudFonts(NamedTuple):
    label: pygame.font.Font
    value: pygame.font.Font


def make_hud_fonts():
    return HudFonts(pygame.font.Font(None, 22), pygame.font.Font(None, 44))


def draw_hud(screen, fonts, bankroll, selected_chip):
    pygame.draw.rect(screen, PANEL_COLOR, PANEL_RECT)
    pygame.draw.rect(screen, WHITE, PANEL_RECT, 3)
    pygame.draw.line(screen, WHITE,
                     (PANEL_RECT.centerx, PANEL_RECT.top + 12),
                     (PANEL_RECT.centerx, PANEL_RECT.bottom - 12), 2)
    left_x = PANEL_RECT.left + PANEL_RECT.width // 4
    right_x = PANEL_RECT.left + 3 * PANEL_RECT.width // 4
    _center(screen, fonts.label, "BANKROLL", WHITE, (left_x, PANEL_RECT.top + 28))
    _center(screen, fonts.value, f"${bankroll:.2f}", WHITE, (left_x, PANEL_RECT.top + 62))
    _center(screen, fonts.label, "SELECTED CHIP", WHITE, (right_x, PANEL_RECT.top + 28))
    _center(screen, fonts.value, f"${selected_chip:g}", GOLD, (right_x, PANEL_RECT.top + 62))


def _center(screen, font, value, color, position):
    rendered = font.render(value, True, color)
    screen.blit(rendered, rendered.get_rect(center=position))
