"""
main.py
-------
Entry point for the retro Mario-style platformer.

Controls:
    Arrow Left / A   — move left
    Arrow Right / D  — move right
    Space / Up / W   — jump
    Escape           — quit

Run:
    python main.py

Install:
    pip install pygame pillow
"""

import pygame
import sys
import os
import math

from player import Player
from level  import Level
from physics import JUMP_STRENGTH
from arduino_bridge import get_state
# ── Settings ──────────────────────────────────────────────────────────────────
SCREEN_W   = 1280
SCREEN_H   = 720
FPS        = 60
TITLE      = "RetroAvatarQuest"
FONT_COLOR = (255, 255, 255)
SHADOW_COL = ( 30,  30,  50)

# Camera lookahead — player stays this far from left edge
CAM_LEFT_MARGIN  = SCREEN_W // 3
CAM_RIGHT_MARGIN = SCREEN_W * 2 // 3


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock  = pygame.time.Clock()

    # Load fonts (fall back gracefully)
    try:
        font_big  = pygame.font.SysFont("couriernew", 36, bold=True)
        font_med  = pygame.font.SysFont("couriernew", 24, bold=True)
        font_small = pygame.font.SysFont("couriernew", 18)
    except Exception:
        font_big  = pygame.font.Font(None, 36)
        font_med  = pygame.font.Font(None, 24)
        font_small = pygame.font.Font(None, 18)

    # Game objects
    level  = Level()
    player = Player(start_x=100, start_y=SCREEN_H - 200)
    camera_x = 0

    # Game state
    state       = "playing"   # "playing" | "win" | "dead"
    coin_flash  = 0           # ticks since last coin collected
    win_tick    = 0
    dead_tick   = 0

    while True:
        dt = clock.tick(FPS)

        # ── Events ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if state in ("win", "dead") and event.key == pygame.K_r:
                    # Restart
                    level  = Level()
                    player = Player(start_x=100, start_y=SCREEN_H - 200)
                    camera_x = 0
                    state = "playing"
                    win_tick = dead_tick = 0

        # ── Update ────────────────────────────────────────────────────────────
        if state == "playing":
            sensor = get_state()

            keys = pygame.key.get_pressed()

            left = keys[pygame.K_LEFT] or keys[pygame.K_a] or sensor == "LEFT"
            right = keys[pygame.K_RIGHT] or keys[pygame.K_d] or sensor == "RIGHT"
            jump = keys[pygame.K_SPACE] or sensor == "JUMP"

            player.handle_input_from_flags(left, right, jump)
            player.update(level.get_all_rects())
            level.update()

            # Camera follow
            player_screen_x = player.center_x - camera_x
            if player_screen_x > CAM_RIGHT_MARGIN:
                camera_x = int(player.center_x - CAM_RIGHT_MARGIN)
            elif player_screen_x < CAM_LEFT_MARGIN:
                camera_x = int(player.center_x - CAM_LEFT_MARGIN)
            camera_x = max(0, min(camera_x, level.LEVEL_W - SCREEN_W))

            # Collect coins
            newly = level.check_coins(player.rect)
            if newly:
                coin_flash = 20

            # Fell off the world
            if player.body.y > SCREEN_H + 100:
                state = "dead"
                dead_tick = 0

            # Reached flag
            if level.check_flag(player.rect):
                state = "win"
                win_tick = 0

        elif state == "win":
            win_tick += 1
        elif state == "dead":
            dead_tick += 1

        if coin_flash > 0:
            coin_flash -= 1

        # ── Draw ──────────────────────────────────────────────────────────────
        level.draw(screen, camera_x)
        player.draw(screen, camera_x)

        # HUD
        _draw_hud(screen, font_med, font_small,
                  level.coins_collected, level.total_coins, coin_flash)

        if state == "win":
            _draw_overlay(screen, font_big, font_small,
                          "YOU WIN!", "(press R to play again)", (80, 220, 80), win_tick)

        elif state == "dead":
            _draw_overlay(screen, font_big, font_small,
                          "GAME OVER", "(press R to try again)", (220, 80, 80), dead_tick)

        pygame.display.flip()


# ── HUD & overlays ────────────────────────────────────────────────────────────
def _draw_hud(screen, font_med, font_small, coins, total, flash):
    # Coin counter (top-left)
    coin_color = (255, 220, 0) if flash > 0 else (255, 255, 255)
    text = font_med.render(f"COINS: {coins} / {total}", True, SHADOW_COL)
    screen.blit(text, (12, 12))
    text = font_med.render(f"COINS: {coins} / {total}", True, coin_color)
    screen.blit(text, (10, 10))

    # Controls reminder (bottom-left)
    hint = font_small.render("ARROWS/WASD = move   SPACE = jump   ESC = quit", True, (180, 180, 220))
    screen.blit(hint, (10, SCREEN_H - 28))


def _draw_overlay(screen, font_big, font_small, line1, line2, colour, tick):
    # Fade in
    alpha = min(200, tick * 5)
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    screen.blit(overlay, (0, 0))

    # Pulsing main text
    scale = 1.0 + 0.05 * math.sin(tick * 0.12)
    t1 = font_big.render(line1, True, colour)
    t1 = pygame.transform.scale(t1, (int(t1.get_width() * scale),
                                      int(t1.get_height() * scale)))
    screen.blit(t1, t1.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 30)))

    t2 = font_small.render(line2, True, (200, 200, 200))
    screen.blit(t2, t2.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 30)))


if __name__ == "__main__":
    main()
