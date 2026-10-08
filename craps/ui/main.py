import pygame
from craps.engine.dice import roll_dice
from craps.engine.game import CrapsEngine

pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Craps")

#Initialize tracking for the last win,lose,continue, point established
last_result = None

engine = CrapsEngine()

font = pygame.font.Font(None, 72)
dice_values = roll_dice()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            dice_values = roll_dice()
            last_result = engine.resolve_roll(sum(dice_values))
            

    screen.fill((0, 100, 0))

    # Die 1 (left)
    die1_rect = pygame.Rect(290, 250, 100, 100)
    pygame.draw.rect(screen, (255, 255, 255), die1_rect)
    die1_text = font.render(str(dice_values[0]), True, (0, 0, 0))
    die1_text_rect = die1_text.get_rect(center=die1_rect.center)
    screen.blit(die1_text, die1_text_rect)

    # Die 2 (right) — your turn
    die2_rect = pygame.Rect(410, 250, 100, 100)
    pygame.draw.rect(screen, (255, 255, 255), die2_rect)
    die2_text = font.render(str(dice_values[1]), True, (0, 0, 0))
    die2_text_rect = die2_text.get_rect(center=die2_rect.center)
    screen.blit(die2_text, die2_text_rect)
    
    if last_result is not None:
        result_rect = pygame.Rect(0, 400, 800, 100)
        result_text = font.render(last_result.outcome.value, True, (255, 255, 255))
        result_text_rect = result_text.get_rect(center=result_rect.center)
        screen.blit(result_text, result_text_rect)
    
    
    pygame.display.flip()

pygame.quit()