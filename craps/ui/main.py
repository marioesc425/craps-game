"""Direct table betting Pygame app. Click a printed zone to bet on it."""
import math
import pygame

from craps.engine.dice import roll_dice
from craps.engine.bets import BetType
from craps.engine.game import CrapsEngine
from craps.engine.player import Player, InvalidBetError
from craps.ui.board import WINDOW_SIZE, DICE_AREA_CENTER, draw_board, draw_puck
from craps.ui.betting import (ZONES, zone_at, wager_available, place_chip,
                               odds_eligible, stack_at, stack_center, draw_chip_stacks)
from craps.ui.dice_view import draw_die
from craps.ui.hud import draw_hud, make_hud_fonts

DIE_SIZE, ROLL_MS, TUMBLE_MS = 60, 800, 80
CHIP_VALUES = (1, 5, 6, 25, 100, 500)
CHIP_COLORS = ((245, 242, 226), (190, 50, 55), (24, 135, 126), (28, 130, 83), (35, 40, 47), (115, 67, 153))
CHIP_X = (975, 1040, 1105, 1170, 1235, 1300)
CHIP_Y = 208
BG, GOLD, CREAM = (11, 22, 27), (226, 184, 92), (247, 238, 215)

pygame.init()
display = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
screen = pygame.Surface(WINDOW_SIZE)
pygame.display.set_caption("Craps — The Golden Rail")
engine, player = CrapsEngine(), Player()
hud_fonts = make_hud_fonts()
small = pygame.font.SysFont("georgia", 15)
chip_font = pygame.font.SysFont("georgia", 13, bold=True)
status_font = pygame.font.SysFont("georgia", 17)
chip_index = 1  # start with the conventional $5 chip
hover_position = None
status_message = "Select a chip, click a table area, then roll."
status_error = False
undo_stack = []  # only actions since the last roll can be undone
last_result = None
dice_values = roll_dice()
roll_started = final_dice = last_tumble_step = None
clock = pygame.time.Clock()
center_x, center_y = DICE_AREA_CENTER
rects = [pygame.Rect(0, 0, DIE_SIZE, DIE_SIZE) for _ in range(2)]
rects[0].center, rects[1].center = (center_x - 38, center_y), (center_x + 38, center_y)
UNDO_RECT = pygame.Rect(1000, 230, 132, 27)
ROLL_RECT = pygame.Rect(1150, 230, 190, 27)


def set_status(message, error=False):
    global status_message, status_error
    status_message, status_error = message, error


def viewport():
    scale = min(display.get_width() / WINDOW_SIZE[0], display.get_height() / WINDOW_SIZE[1])
    size = (round(WINDOW_SIZE[0] * scale), round(WINDOW_SIZE[1] * scale))
    offset = ((display.get_width() - size[0]) // 2, (display.get_height() - size[1]) // 2)
    return scale, size, offset


def design_position(position):
    scale, _, offset = viewport()
    return (round((position[0] - offset[0]) / scale),
            round((position[1] - offset[1]) / scale))


def do_undo():
    if not undo_stack:
        set_status("No new wager to undo.", True)
        return
    kind, bet, amount = undo_stack.pop()
    try:
        if kind == "new":
            player.undo_wager(bet)
        elif kind == "increase":
            player.reduce_wager(bet, amount)
        else:
            player.reduce_odds(bet, amount)
        set_status("Last chip removed and refunded.")
    except InvalidBetError as exc:
        undo_stack.append((kind, bet, amount))
        set_status(str(exc), True)


def click_stack(position):
    bet = stack_at(position, player.active_bets)
    if bet is None:
        return False
    chip = CHIP_VALUES[chip_index]
    try:
        if odds_eligible(bet, engine.point):
            player.add_odds(bet, chip, engine.point)
            undo_stack.append(("odds", bet, chip))
            set_status(f"${chip} odds added to {bet.bet_type.value.replace('_', ' ')}.")
        else:
            player.increase_wager(bet, chip)
            undo_stack.append(("increase", bet, chip))
            set_status(f"${chip} added to {bet.bet_type.value.replace('_', ' ')}.")
    except InvalidBetError as exc:
        set_status(str(exc), True)
    return True


def roll_dice_once():
    global roll_started, last_tumble_step, final_dice, last_result
    if roll_started is not None:
        return
    if not player.active_bets:
        set_status("Place at least one wager before rolling.", True)
        return
    roll_started = pygame.time.get_ticks()
    last_tumble_step = None
    final_dice, last_result = roll_dice(), None
    set_status("Dice rolling…")


def draw_chip_tray(surface):
    for i, (value, x, color) in enumerate(zip(CHIP_VALUES, CHIP_X, CHIP_COLORS)):
        affordable = value <= player.bankroll
        enabled_color = color if affordable else (73, 76, 77)
        pygame.draw.circle(surface, (5, 18, 14), (x + 2, CHIP_Y + 3), 19)
        pygame.draw.circle(surface, enabled_color, (x, CHIP_Y), 18)
        edge = GOLD if i == chip_index else (230, 223, 205) if affordable else (105, 104, 99)
        pygame.draw.circle(surface, edge, (x, CHIP_Y), 18 if i == chip_index else 16, 3 if i == chip_index else 1)
        pygame.draw.circle(surface, edge, (x, CHIP_Y), 12, 1)
        ink = (28, 30, 29) if affordable and i == 0 else (255, 247, 225) if affordable else (158, 158, 151)
        chip_text = chip_font.render(f"${value}", True, ink)
        surface.blit(chip_text, chip_text.get_rect(center=(x, CHIP_Y)))
        if hover_position and math.dist(hover_position, (x, CHIP_Y)) <= 20 and affordable:
            pygame.draw.circle(surface, (255, 250, 224), (x, CHIP_Y), 21, 2)


def draw_control(surface, rect, label, enabled, hovered=False):
    fill = (31, 103, 75) if enabled else (50, 60, 58)
    outline = (255, 222, 145) if hovered and enabled else GOLD if enabled else (99, 103, 95)
    pygame.draw.rect(surface, fill, rect, border_radius=8)
    pygame.draw.rect(surface, outline, rect, 2, border_radius=8)
    ink = CREAM if enabled else (150, 153, 145)
    rendered = status_font.render(label, True, ink)
    surface.blit(rendered, rendered.get_rect(center=rect.center))


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            display = pygame.display.set_mode(event.size, pygame.RESIZABLE)
        elif event.type == pygame.MOUSEMOTION:
            hover_position = design_position(event.pos)
        elif event.type == pygame.KEYDOWN and roll_started is None:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                roll_dice_once()
            elif event.key == pygame.K_z:
                do_undo()
            elif event.key == pygame.K_r:
                player.reset()
                engine.reset()
                undo_stack.clear()
                last_result = None
                set_status("New game started.")
            elif pygame.K_1 <= event.key <= pygame.K_6:
                candidate = event.key - pygame.K_1
                if CHIP_VALUES[candidate] <= player.bankroll:
                    chip_index = candidate
                    set_status(f"${CHIP_VALUES[chip_index]} chip selected.")
                else:
                    set_status("That chip exceeds the available bankroll.", True)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and roll_started is None:
            position = design_position(event.pos)
            selected_chip = next((i for i, x in enumerate(CHIP_X)
                                  if math.dist(position, (x, CHIP_Y)) <= 20), None)
            if selected_chip is not None:
                denomination = CHIP_VALUES[selected_chip]
                if denomination <= player.bankroll:
                    chip_index = selected_chip
                    set_status(f"${denomination} chip selected.")
                else:
                    set_status("That chip exceeds the available bankroll.", True)
            elif UNDO_RECT.collidepoint(position):
                do_undo()
            elif ROLL_RECT.collidepoint(position):
                roll_dice_once()
            elif click_stack(position):
                pass
            else:
                zone = zone_at(position)
                if zone is not None:
                    chip = CHIP_VALUES[chip_index]
                    try:
                        bet, kind = place_chip(player, engine, zone, chip)
                        undo_stack.append((kind, bet, chip))
                        label = zone.name.replace("_", " ")
                        set_status(f"${chip} on {label}.")
                    except InvalidBetError as exc:
                        set_status(str(exc), True)
    if roll_started is not None:
        elapsed = pygame.time.get_ticks() - roll_started
        if elapsed >= ROLL_MS:
            dice_values = final_dice
            last_result = engine.resolve_roll(dice_values, list(player.active_bets))
            player.settle(last_result)
            undo_stack.clear()
            settled = [r for r in last_result.bet_results if r.outcome.value != "no_action"]
            summary = ", ".join(f"{r.bet.bet_type.value.replace('_', ' ')} {r.outcome.value}"
                                 for r in settled)
            set_status(f"Roll {sum(dice_values)} — {summary or last_result.outcome.value.replace('_', ' ')}")
            roll_started = None
        else:
            step = elapsed // TUMBLE_MS
            if step != last_tumble_step:
                last_tumble_step = step
                dice_values = roll_dice()

    screen.fill(BG)
    draw_board(screen)
    draw_puck(screen, pygame.font.Font(None, 18), engine.point)
    current_zone = zone_at(hover_position) if hover_position else None
    if (current_zone and roll_started is None
            and wager_available(player, engine, current_zone, CHIP_VALUES[chip_index])):
        current_zone.draw_highlight(screen)
    draw_chip_stacks(screen, player.active_bets, small)
    draw_hud(screen, hud_fonts, player.bankroll, CHIP_VALUES[chip_index])
    for index, (rect, value) in enumerate(zip(rects, dice_values)):
        if roll_started is None:
            draw_die(screen, rect, value)
        else:
            tumble = pygame.Surface((DIE_SIZE, DIE_SIZE), pygame.SRCALPHA)
            draw_die(tumble, pygame.Rect(0, 0, DIE_SIZE, DIE_SIZE), value)
            elapsed = pygame.time.get_ticks() - roll_started
            tilted = pygame.transform.rotozoom(tumble, (elapsed * 0.65 + index * 37) % 360, 1.0)
            bob = abs(math.sin(math.radians(elapsed * 1.1 + index * 80))) * 11
            screen.blit(tilted, tilted.get_rect(center=(rect.centerx, round(rect.centery - bob))))

    phase = f"POINT {engine.point}" if engine.point is not None else "COME OUT"
    phase_surface = status_font.render(phase, True, GOLD)
    screen.blit(phase_surface, phase_surface.get_rect(center=(1158, 143)))
    recent = "  ".join(str(sum(pair)) for pair in engine.roll_history[-6:]) or "—"
    recent_color = (255, 166, 148) if status_error else CREAM
    result_surface = small.render(status_message[:60], True, recent_color)
    screen.blit(result_surface, result_surface.get_rect(center=(1158, 161)))
    history_surface = small.render(f"RECENT  {recent}", True, CREAM)
    screen.blit(history_surface, history_surface.get_rect(center=(1158, 179)))
    draw_chip_tray(screen)
    hovered_undo = hover_position is not None and UNDO_RECT.collidepoint(hover_position)
    hovered_roll = hover_position is not None and ROLL_RECT.collidepoint(hover_position)
    draw_control(screen, UNDO_RECT, "UNDO CHIP  [Z]", bool(undo_stack), hovered_undo)
    draw_control(screen, ROLL_RECT, "ROLL DICE  [SPACE]", bool(player.active_bets) and roll_started is None, hovered_roll)
    scale, viewport_size, offset = viewport()
    display.fill(BG)
    if viewport_size == WINDOW_SIZE:
        display.blit(screen, offset)
    else:
        display.blit(pygame.transform.smoothscale(screen, viewport_size), offset)
    pygame.display.flip()
    clock.tick(60)
pygame.quit()
