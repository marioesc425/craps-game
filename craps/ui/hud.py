"""Compact bankroll and selected-denomination display."""
from typing import NamedTuple
import pygame

PANEL_RECT = pygame.Rect(44, 660, 880, 30)
PANEL_COLOR = (0, 67, 47)
WHITE = (247, 238, 215)
GOLD = (230, 190, 93)


class HudFonts(NamedTuple):
    label: pygame.font.Font
    value: pygame.font.Font


def make_hud_fonts():
    return HudFonts(pygame.font.Font(None, 18), pygame.font.Font(None, 22))


def draw_hud(screen, fonts, bankroll, selected_chip, rules, chip_label=None):
    pygame.draw.rect(screen, PANEL_COLOR, PANEL_RECT)
    pygame.draw.rect(screen, GOLD, PANEL_RECT, 1)
    summary = (f"BANKROLL  ${bankroll}     CHIP  {chip_label or f'${selected_chip}'}"
               f"     TABLE  ${rules.minimum_bet}–${rules.maximum_single_wager}"
               f"     ODDS  {rules.maximum_odds_multiplier}×")
    _center(screen, fonts.value, summary, WHITE, PANEL_RECT.center)


def _center(screen, font, value, color, position):
    rendered = font.render(value, True, color)
    screen.blit(rendered, rendered.get_rect(center=position))
