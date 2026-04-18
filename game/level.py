"""
level.py
--------
Defines the game world:
  - Platform layout (static rects)
  - Coin collectibles
  - Finish flag
  - Nostalgic pixel background (sky, mountains, clouds, ground)

Designed to look like a classic 8-bit side-scroller.
"""

import pygame
import random
import math

# ── Colours (retro palette) ───────────────────────────────────────────────────
SKY_TOP     = ( 92, 148, 252)
SKY_BOT     = (138, 186, 255)
GROUND_TOP  = ( 92, 184,  92)
GROUND_BODY = (100,  72,  44)
MOUNTAIN    = (110, 130, 160)
CLOUD       = (240, 240, 255)
PLAT_TOP    = (100, 184, 100)
PLAT_SIDE   = ( 80, 140,  60)
PLAT_BOT    = ( 60, 100,  40)
COIN_GOLD   = (255, 200,   0)
COIN_SHINE  = (255, 240, 100)
FLAG_POLE   = (180, 180, 180)
FLAG_COL    = (255,  60,  60)
STAR_COL    = (255, 255, 200)


class Platform:
    def __init__(self, x, y, width, height=24, is_ground=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.is_ground = is_ground

    def draw(self, surface, camera_x):
        rx = self.rect.x - camera_x
        r  = pygame.Rect(rx, self.rect.y, self.rect.width, self.rect.height)

        if self.is_ground:
            # Ground strip
            pygame.draw.rect(surface, GROUND_TOP,  (rx, r.top,     r.width, 8))
            pygame.draw.rect(surface, GROUND_BODY, (rx, r.top + 8, r.width, r.height - 8))
        else:
            # Floating platform — 3-tone for depth
            pygame.draw.rect(surface, PLAT_TOP,  (rx, r.top,          r.width, 8))
            pygame.draw.rect(surface, PLAT_SIDE, (rx, r.top + 8,      r.width, r.height - 16))
            pygame.draw.rect(surface, PLAT_BOT,  (rx, r.bottom - 6,   r.width, 6))


class Coin:
    RADIUS = 8

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.collected = False
        self._tick = 0

    @property
    def rect(self):
        return pygame.Rect(self.x - self.RADIUS, self.y - self.RADIUS,
                           self.RADIUS * 2, self.RADIUS * 2)

    def update(self):
        if not self.collected:
            self._tick += 1

    def draw(self, surface, camera_x):
        if self.collected:
            return
        cx = self.x - camera_x
        # Wobble animation
        wobble = math.sin(self._tick * 0.15) * 2
        y = int(self.y + wobble)
        pygame.draw.circle(surface, COIN_GOLD,  (int(cx), y), self.RADIUS)
        pygame.draw.circle(surface, COIN_SHINE, (int(cx) - 2, y - 2), 3)


class Flag:
    def __init__(self, x, ground_y):
        self.x = x
        self.ground_y = ground_y
        self._tick = 0

    def draw(self, surface, camera_x):
        self._tick += 1
        cx = self.x - camera_x
        top = self.ground_y - 120

        # Pole
        pygame.draw.line(surface, FLAG_POLE, (cx, top), (cx, self.ground_y), 4)

        # Waving flag
        wave = math.sin(self._tick * 0.1) * 5
        pts = [
            (cx + 2, top),
            (cx + 40, top + 15 + wave),
            (cx + 2, top + 30),
        ]
        pygame.draw.polygon(surface, FLAG_COL, pts)

    @property
    def rect(self):
        return pygame.Rect(self.x - 5, self.ground_y - 130, 50, 130)


class Level:
    SCREEN_W = 1280
    SCREEN_H = 720
    LEVEL_W  = 6000    # total world width

    def __init__(self):
        self._setup_platforms()
        self._setup_coins()
        self.flag = Flag(self.LEVEL_W - 200, self.SCREEN_H - 40)
        self._clouds = _generate_clouds(self.LEVEL_W)
        self._stars  = _generate_stars(self.SCREEN_W, self.SCREEN_H)
        self.coins_collected = 0
        self.total_coins = len(self.coins)

    def _setup_platforms(self):
        """Hand-authored platform layout — classic Mario feel."""
        H = self.SCREEN_H
        ground_y = H - 40

        self.ground = Platform(0, ground_y, self.LEVEL_W, 80, is_ground=True)

        self.platforms = [
        self.ground,

        # Easy intro
        Platform(250,  H - 140, 180),
        Platform(500,  H - 180, 180),
        Platform(760,  H - 160, 200),

        # gentle rise
        Platform(1050, H - 200, 180),
        Platform(1300, H - 230, 180),
        Platform(1550, H - 210, 200),

        # relaxed staircase
        Platform(1850, H - 180, 180),
        Platform(2100, H - 220, 180),
        Platform(2350, H - 250, 180),

        # flat recovery
        Platform(2650, H - 220, 220),
        Platform(2950, H - 240, 220),

        # upper but safe
        Platform(3250, H - 280, 180),
        Platform(3500, H - 260, 180),
        Platform(3750, H - 240, 220),

        # final stretch easy
        Platform(4100, H - 220, 220),
        Platform(4400, H - 250, 200),
        Platform(4700, H - 220, 220),
        Platform(5050, H - 200, 250),
        Platform(5400, H - 180, 300),
    ]
    def _setup_coins(self):
        H = self.SCREEN_H
        self.coins = []
        # Place a coin cluster above each non-ground platform
        for plat in self.platforms[1:]:
            cx = plat.rect.centerx
            cy = plat.rect.top - 40
            # 1–3 coins per platform
            count = random.randint(1, 3)
            for i in range(count):
                self.coins.append(Coin(cx + i * 28 - (count - 1) * 14, cy))

    def get_all_rects(self):
        """Return all platform pygame.Rect objects for physics."""
        return [p.rect for p in self.platforms]

    def check_coins(self, player_rect: pygame.Rect) -> int:
        """Collect any coins the player touches. Returns number newly collected."""
        newly = 0
        for coin in self.coins:
            if not coin.collected and player_rect.colliderect(coin.rect):
                coin.collected = True
                self.coins_collected += 1
                newly += 1
        return newly

    def check_flag(self, player_rect: pygame.Rect) -> bool:
        return player_rect.colliderect(self.flag.rect)

    def update(self):
        for coin in self.coins:
            coin.update()

    def draw_background(self, surface, camera_x):
        """Draw layered parallax background."""
        # Sky gradient (two rects)
        surface.fill(SKY_TOP)
        pygame.draw.rect(surface, SKY_BOT,
                         (0, self.SCREEN_H // 2, self.SCREEN_W, self.SCREEN_H // 2))

        # Stars (very slow parallax — barely moves)
        for sx, sy in self._stars:
            sx_screen = (sx - camera_x * 0.02) % self.SCREEN_W
            pygame.draw.circle(surface, STAR_COL, (int(sx_screen), sy), 1)

        # Distant mountains (slow parallax)
        for mx, my, mw, mh in _mountain_rects(camera_x, self.SCREEN_H):
            pts = [(mx, my + mh), (mx + mw // 2, my), (mx + mw, my + mh)]
            pygame.draw.polygon(surface, MOUNTAIN, pts)

        # Clouds (medium parallax)
        for cx_, cy_, cw in self._clouds:
            scx = (cx_ - camera_x * 0.3) % (self.SCREEN_W + 200) - 100
            _draw_cloud(surface, int(scx), cy_, cw)

    def draw(self, surface, camera_x):
        self.draw_background(surface, camera_x)
        for plat in self.platforms:
            if -200 < plat.rect.x - camera_x < self.SCREEN_W + 200:
                plat.draw(surface, camera_x)
        for coin in self.coins:
            if not coin.collected and abs(coin.x - camera_x - self.SCREEN_W // 2) < self.SCREEN_W:
                coin.draw(surface, camera_x)
        self.flag.draw(surface, camera_x)


# ── Background helpers ────────────────────────────────────────────────────────
def _generate_clouds(level_w: int) -> list:
    clouds = []
    for _ in range(40):
        clouds.append((
            random.randint(0, level_w),
            random.randint(40, 250),
            random.randint(80, 200),
        ))
    return clouds


def _generate_stars(sw: int, sh: int) -> list:
    return [(random.randint(0, sw * 5), random.randint(0, sh // 2))
            for _ in range(120)]


def _mountain_rects(camera_x: int, screen_h: int) -> list:
    """Generate pseudo-random mountain positions seeded on screen chunk."""
    rects = []
    rng = random.Random(42)
    for i in range(30):
        x = i * 300 + rng.randint(-50, 50)
        w = rng.randint(180, 340)
        h = rng.randint(100, 220)
        screen_x = x - int(camera_x * 0.2)
        rects.append((screen_x, screen_h - 80 - h, w, h))
    return rects


def _draw_cloud(surface, x, y, w):
    h = w // 3
    for ox, oy, r in [
        (0, h // 2, h // 2),
        (w // 4, 0, h * 2 // 3),
        (w // 2, h // 4, h // 2),
        (w * 3 // 4, h // 3, h * 2 // 5),
    ]:
        pygame.draw.circle(surface, CLOUD, (x + ox, y + oy), r)
