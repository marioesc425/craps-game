import pygame
from craps.engine.dice import roll_dice
from craps.engine.game import CrapsEngine
from craps.engine.player import Player, InvalidBetError, MIN_BET
from craps.ui.board import WINDOW_SIZE, DICE_AREA_CENTER, draw_board, draw_puck
from craps.ui.dice_view import draw_die
from craps.ui.hud import draw_hud, make_hud_fonts


DIE_SIZE = 60
DIE_GAP = 16
BET_STEP = 5

pygame.init()
screen = pygame.display.set_mode(WINDOW_SIZE)
pygame.display.set_caption("Craps")

label_font = pygame.font.Font(None, 30)
outcome_font = pygame.font.Font(None, 40)
puck_font = pygame.font.Font(None, 18)
hud_fonts = make_hud_fonts()

engine = CrapsEngine()

player = Player()

error = ""
pending_bet = MIN_BET

dice_values = roll_dice()
last_result = None

# Dice sit side by side, centered on the open middle of the table.
center_x, center_y = DICE_AREA_CENTER
die1_rect = pygame.Rect(0, 0, DIE_SIZE, DIE_SIZE)
die2_rect = pygame.Rect(0, 0, DIE_SIZE, DIE_SIZE)
die1_rect.center = (center_x - (DIE_SIZE + DIE_GAP) // 2, center_y)
die2_rect.center = (center_x + (DIE_SIZE + DIE_GAP) // 2, center_y)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if player.current_bet is None:          # betting phase
                if event.key == pygame.K_UP:
                    pending_bet = max(MIN_BET, min(player.bankroll, pending_bet + BET_STEP))
                elif event.key == pygame.K_DOWN:
                    pending_bet = max(MIN_BET, min(player.bankroll, pending_bet - BET_STEP))
                elif event.key == pygame.K_RETURN:
                    try:
                        player.place_bet(pending_bet)
                        error = ""
                    except InvalidBetError as e:
                        error = str(e)
            else:                                   # rolling phase
                if event.key == pygame.K_SPACE:
                    dice_values = roll_dice()
                    # Resolve first: settle() clears the bet when the round ends.
                    last_result = engine.resolve_roll(sum(dice_values), player.current_bet)
                    player.settle(last_result)
                    # Keep the chosen amount within what the player can afford.
                    pending_bet = max(MIN_BET, min(player.bankroll, pending_bet))

    draw_board(screen, label_font)
    draw_puck(screen, puck_font, engine.point)

    bet_locked = player.current_bet is not None
    shown_bet = player.current_bet if bet_locked else pending_bet
    draw_hud(screen, hud_fonts, player.bankroll, shown_bet, bet_locked, error)

    draw_die(screen, die1_rect, dice_values[0])
    draw_die(screen, die2_rect, dice_values[1])

    if last_result is not None:
        result_text = outcome_font.render(last_result.outcome.value, True, (255, 255, 255))
        screen.blit(result_text, result_text.get_rect(center=(center_x, center_y + 70)))

    pygame.display.flip()

pygame.quit()