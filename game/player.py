"""
player.py
---------
Loads avatar sprite, handles movement, animation, and supports BOTH:
- keyboard input (WASD / arrows)
- sensor input (LEFT / RIGHT / JUMP strings from Arduino bridge)

Fallback stick figure if avatar missing.
"""

import os
import json
import pygame
from physics import PhysicsBody

# ── Paths ────────────────────────────────────────────────────────────────────
OUTPUTS_DIR = "../outputs"
AVATAR_PNG   = os.path.join(OUTPUTS_DIR, "avatar.png")
JOINTS_JSON  = os.path.join(OUTPUTS_DIR, "joints.json")

PLAYER_W = 90
PLAYER_H = 160
WALK_FRAME_SPEED = 6


class Player:
    def __init__(self, start_x: int, start_y: int):
        self.body = PhysicsBody(start_x, start_y, PLAYER_W, PLAYER_H)
        self.facing = 1
        self.state = "idle"
        self.anim_tick = 0
        self.frame_idx = 0

        self.sprites = _load_or_generate_sprites()
        self.joints = _load_joints()

    # ─────────────────────────────────────────────────────────────
    # NEW UNIFIED INPUT SYSTEM
    # ─────────────────────────────────────────────────────────────
    def handle_input_from_flags(self, left=False, right=False, jump=False):
        """
        Works with BOTH:
        - keyboard input (mapped in main.py)
        - Arduino sensor input
        """

        direction = 0

        if left:
            direction = -1
            self.facing = -1
            if self.body.on_ground:
                self.state = "walk"

        elif right:
            direction = 1
            self.facing = 1
            if self.body.on_ground:
                self.state = "walk"

        else:
            if self.body.on_ground:
                self.state = "idle"

        # IMPORTANT: prevent jump spam
        if jump and self.body.on_ground:
            self.body.jump()
            self.state = "jump"

        self.body.walk(direction)

    # ─────────────────────────────────────────────────────────────
    # OLD METHOD (kept for compatibility)
    # ─────────────────────────────────────────────────────────────
    def handle_input(self, keys):
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        jump = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]

        self.handle_input_from_flags(left, right, jump)

    # ── Physics ──────────────────────────────────────────────────
    def update(self, platforms: list):
        self.body.apply_gravity()
        self.body.move_and_collide(platforms)

        self.anim_tick += 1
        if self.anim_tick >= WALK_FRAME_SPEED:
            self.anim_tick = 0
            frames = self.sprites.get(self.state, self.sprites["idle"])
            self.frame_idx = (self.frame_idx + 1) % len(frames)

        if self.body.on_ground and self.state == "jump":
            self.state = "idle"

    # ── Draw ─────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, camera_x: int):
        frames = self.sprites.get(self.state, self.sprites["idle"])
        frame = frames[self.frame_idx % len(frames)]

        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)

        surface.blit(frame, (int(self.body.x) - camera_x, int(self.body.y)))

    @property
    def rect(self):
        x, y, w, h = self.body.rect_tuple
        return pygame.Rect(x, y, w, h)

    @property
    def center_x(self):
        return self.body.x + PLAYER_W // 2


# ─────────────────────────────────────────────────────────────
# SPRITES
# ─────────────────────────────────────────────────────────────
def _load_or_generate_sprites():
    base = None

    if os.path.exists(AVATAR_PNG):
        try:
            raw = pygame.image.load(AVATAR_PNG).convert_alpha()
            base = pygame.transform.smoothscale(raw, (PLAYER_W, PLAYER_H))
            print("[player] avatar loaded")
        except:
            pass

    if base is None:
        base = _fallback()

    return {
        "idle": [base],
        "walk": _walk(base),
        "jump": [_tint(base, (255, 255, 150))]
    }


def _fallback():
    surf = pygame.Surface((PLAYER_W, PLAYER_H), pygame.SRCALPHA)

    pygame.draw.circle(surf, (240, 200, 160), (PLAYER_W//2, 10), 9)
    pygame.draw.rect(surf, (70, 130, 200), (12, 20, 16, 18))

    pygame.draw.line(surf, (240, 200, 160), (12, 22), (3, 34), 4)
    pygame.draw.line(surf, (240, 200, 160), (28, 22), (37, 34), 4)

    pygame.draw.rect(surf, (50, 80, 160), (12, 38, 6, 14))
    pygame.draw.rect(surf, (50, 80, 160), (22, 38, 6, 14))

    return surf


def _walk(base):
    frames = []
    for i in range(4):
        offset = [0, -2, 0, 2][i]
        surf = pygame.Surface((PLAYER_W, PLAYER_H), pygame.SRCALPHA)
        surf.blit(base, (0, offset))
        frames.append(surf)
    return frames


def _tint(surface, color):
    s = surface.copy()
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((*color, 60))
    s.blit(overlay, (0, 0))
    return s


def _load_joints():
    if os.path.exists(JOINTS_JSON):
        with open(JOINTS_JSON) as f:
            return json.load(f).get("joints_2d_normalised", {})
    return {}