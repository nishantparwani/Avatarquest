"""
physics.py
----------
Arcade-tuned physics for sensor-controlled platformer.
Stronger movement, higher jump, reduced damping.
"""

# ── Constants (ARCADE MODE) ──────────────────────────────────────────────────
GRAVITY        = 0.65     # slightly stronger feel
MAX_FALL_SPEED = 18.0     # faster fall = more responsive
JUMP_STRENGTH  = -30.0    # BIG jump (fixes your issue)
MOVE_SPEED     = 20.0     # 5x faster movement (your request)
FRICTION       = 0.75     # less sticky movement


class PhysicsBody:

    def __init__(self, x: float, y: float, width: int, height: int):
        self.x = float(x)
        self.y = float(y)
        self.width  = width
        self.height = height

        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False

    # ── Rect helper ───────────────────────────────────────────────────────────
    @property
    def rect_tuple(self):
        return (int(self.x), int(self.y), self.width, self.height)

    def get_rect(self):
        return {
            "left": self.x,
            "right": self.x + self.width,
            "top": self.y,
            "bottom": self.y + self.height,
        }

    # ── Physics ───────────────────────────────────────────────────────────────
    def apply_gravity(self):
        if not self.on_ground:
            self.vy += GRAVITY
            if self.vy > MAX_FALL_SPEED:
                self.vy = MAX_FALL_SPEED

    def move_and_collide(self, platforms: list):
        self.on_ground = False

        # X movement
        self.x += self.vx
        r = self.get_rect()

        for plat in platforms:
            if _overlaps(r, plat):
                if self.vx > 0:
                    self.x = plat.left - self.width
                elif self.vx < 0:
                    self.x = plat.right
                self.vx = 0

        # Y movement
        self.y += self.vy
        r = self.get_rect()

        for plat in platforms:
            if _overlaps(r, plat):
                if self.vy > 0:
                    self.y = plat.top - self.height
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.y = plat.bottom
                    self.vy = 0

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_STRENGTH
            self.on_ground = False

    def walk(self, direction: int):
        if direction != 0:
            self.vx = direction * MOVE_SPEED
        else:
            self.vx *= FRICTION
            if abs(self.vx) < 0.2:
                self.vx = 0.0


# ── Collision helper ──────────────────────────────────────────────────────────
def _overlaps(a: dict, b) -> bool:
    return (
        a["left"]   < b.right  and
        a["right"]  > b.left   and
        a["top"]    < b.bottom and
        a["bottom"] > b.top
    )