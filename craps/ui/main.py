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
ROLL_MS = 800   # how long the dice tumble before the result is revealed
TUMBLE_MS = 80  # how often the tumbling faces change

pygame.init()
screen = pygame.display.set_mode(WINDOW_SIZE)
pygame.display.set_caption("Craps")

outcome_font = pygame.font.Font(None, 40)
puck_font = pygame.font.Font(None, 18)
hud_fonts = make_hud_fonts()

engine = CrapsEngine()

player = Player()

error = ""
pending_bet = MIN_BET

dice_values = roll_dice()
last_result = None

roll_started = None  # None means the dice are not tumbling
final_dice = None    # the real roll, kept hidden until the reveal
last_tumble_step = None  # which TUMBLE_MS period the faces last changed on

# Dice sit side by side, centered on the open middle of the table.
center_x, center_y = DICE_AREA_CENTER
die1_rect = pygame.Rect(0, 0, DIE_SIZE, DIE_SIZE)
die2_rect = pygame.Rect(0, 0, DIE_SIZE, DIE_SIZE)
die1_rect.center = (center_x - (DIE_SIZE + DIE_GAP) // 2, center_y)
die2_rect.center = (center_x + (DIE_SIZE + DIE_GAP) // 2, center_y)

running = True

clock = pygame.time.Clock()

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
                if event.key == pygame.K_SPACE and roll_started is None:
                    roll_started = pygame.time.get_ticks()
                    last_tumble_step = None
                    final_dice = roll_dice()
                    last_result = None  # don't leave the old outcome up while tumbling

    # Runs once per frame, not once per event: time passing is not an event.
    if roll_started is not None:
        elapsed = pygame.time.get_ticks() - roll_started
        if elapsed >= ROLL_MS:
            # Reveal: only now do the real roll, the puck, and the bankroll change.
            dice_values = final_dice
            # Resolve first: settle() clears the bet when the round ends.
            last_result = engine.resolve_roll(sum(dice_values), player.current_bet)
            player.settle(last_result)
            # Keep the chosen amount within what the player can afford.
            pending_bet = max(MIN_BET, min(player.bankroll, pending_bet))
            roll_started = None
        else:
            # Tumbling: swap in a fake roll, but only when a new period starts.
            step = elapsed // TUMBLE_MS
            if step != last_tumble_step:
                last_tumble_step = step
                dice_values = roll_dice()

    draw_board(screen)
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
    clock.tick(60)

pygame.quit()