"""
fruit_ninja.py — Fruit Ninja Game Mode

A Fruit-Ninja-style mini-game rendered on the webcam feed.
Fruits fly up from the bottom, the player slashes them with hand
movement. Features scoring, combos, lives, bombs, and particles.
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Tuple

import cv2
import numpy as np


# ── Fruit definitions ────────────────────────────────────────────────
FRUIT_TYPES = [
    {"name": "Apple",      "color": (50, 50, 220),   "radius": 30},
    {"name": "Orange",     "color": (0, 140, 255),    "radius": 28},
    {"name": "Lemon",      "color": (0, 230, 255),    "radius": 24},
    {"name": "Watermelon", "color": (60, 180, 75),    "radius": 36},
    {"name": "Grape",      "color": (180, 50, 160),   "radius": 22},
]

BOMB_COLOR = (40, 40, 40)
BOMB_ACCENT = (0, 0, 200)


@dataclass
class Fruit:
    """A fruit projectile in the game.

    Attributes:
        x, y: Current position.
        vx, vy: Velocity (pixels/frame).
        radius: Display radius.
        color: BGR colour.
        name: Fruit type name.
        alive: Whether the fruit is still on screen.
        sliced: Whether it was cut by the player.
        is_bomb: True for bomb objects.
        spawn_time: When the fruit was created.
    """
    x: float
    y: float
    vx: float
    vy: float
    radius: int
    color: Tuple[int, int, int]
    name: str
    alive: bool = True
    sliced: bool = False
    is_bomb: bool = False
    spawn_time: float = 0.0


@dataclass
class Particle:
    """A particle from a sliced fruit.

    Attributes:
        x, y: Position.
        vx, vy: Velocity.
        color: BGR colour.
        life: Remaining lifetime in frames.
        radius: Particle size.
    """
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    life: int = 20
    radius: int = 4


class FruitNinja:
    """Fruit Ninja game engine.

    Manages fruit spawning, physics, slash detection, scoring,
    combo tracking, lives, and particle effects.

    Attributes:
        score: Current player score.
        combo: Current combo multiplier.
        max_combo: Best combo this session.
        lives: Remaining lives (game over at 0).
        game_over: Whether the game has ended.
    """

    GRAVITY = 0.35          # pixels/frame^2
    SLASH_SPEED_THRESH = 18  # min hand speed to count as slash
    SLASH_RADIUS = 60       # how close hand must be to fruit
    SPAWN_INTERVAL = 1.2    # seconds between spawns
    BOMB_CHANCE = 0.15      # probability of bomb per spawn

    def __init__(self, width: int = 1280, height: int = 720) -> None:
        """Initialise the Fruit Ninja game.

        Args:
            width: Frame width.
            height: Frame height.
        """
        self.width = width
        self.height = height
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.lives = 3
        self.game_over = False

        self._fruits: List[Fruit] = []
        self._particles: List[Particle] = []
        self._slash_trail: List[Tuple[int, int]] = []
        self._last_spawn_time = time.time()
        self._combo_timer = 0.0
        self._frame_count = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the game to initial state."""
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.lives = 3
        self.game_over = False
        self._fruits.clear()
        self._particles.clear()
        self._slash_trail.clear()
        self._last_spawn_time = time.time()

    def update(self, hand_pos: Tuple[int, int] = None,
               hand_speed: float = 0.0) -> None:
        """Advance the game by one frame.

        Args:
            hand_pos: Current (x, y) of the player's index tip.
            hand_speed: Pixels/frame speed of hand movement.
        """
        if self.game_over:
            return

        self._frame_count += 1

        # Spawn fruits
        now = time.time()
        if now - self._last_spawn_time > self.SPAWN_INTERVAL:
            self._spawn_wave()
            self._last_spawn_time = now

        # Update slash trail
        if hand_pos is not None:
            self._slash_trail.append(hand_pos)
            if len(self._slash_trail) > 12:
                self._slash_trail.pop(0)
        else:
            if self._slash_trail:
                self._slash_trail.pop(0)

        # Update fruits physics
        for fruit in self._fruits:
            if not fruit.alive:
                continue
            fruit.x += fruit.vx
            fruit.y += fruit.vy
            fruit.vy += self.GRAVITY

            # Off-screen check (fell below)
            if fruit.y > self.height + 60:
                fruit.alive = False
                if not fruit.sliced and not fruit.is_bomb:
                    self.lives -= 1
                    self.combo = 0
                    if self.lives <= 0:
                        self.game_over = True

        # Check slash
        if hand_pos is not None and hand_speed > self.SLASH_SPEED_THRESH:
            self._check_slash(hand_pos)

        # Combo timeout
        if self.combo > 0:
            self._combo_timer += 1
            if self._combo_timer > 30:  # ~1 second
                self.combo = 0
                self._combo_timer = 0

        # Update particles
        for p in self._particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2
            p.life -= 1

        # Cleanup
        self._fruits = [f for f in self._fruits if f.alive]
        self._particles = [p for p in self._particles if p.life > 0]

    def draw(self, frame: np.ndarray) -> None:
        """Render all game elements onto the frame.

        Args:
            frame: BGR image to draw on (modified in place).
        """
        overlay = frame.copy()

        # Draw slash trail
        if len(self._slash_trail) > 1:
            for i in range(1, len(self._slash_trail)):
                alpha = i / len(self._slash_trail)
                thickness = int(3 + alpha * 6)
                color = (
                    int(100 + 155 * alpha),
                    int(200 * alpha),
                    int(255 * alpha),
                )
                cv2.line(overlay, self._slash_trail[i - 1],
                         self._slash_trail[i], color, thickness, cv2.LINE_AA)

        # Draw particles
        for p in self._particles:
            alpha = p.life / 20.0
            r = max(1, int(p.radius * alpha))
            cv2.circle(overlay, (int(p.x), int(p.y)), r,
                       p.color, cv2.FILLED, cv2.LINE_AA)

        # Draw fruits
        for fruit in self._fruits:
            if not fruit.alive or fruit.sliced:
                continue
            cx, cy = int(fruit.x), int(fruit.y)

            if fruit.is_bomb:
                # Bomb: dark circle with red accent
                cv2.circle(overlay, (cx, cy), fruit.radius,
                           BOMB_COLOR, cv2.FILLED, cv2.LINE_AA)
                cv2.circle(overlay, (cx, cy), fruit.radius,
                           BOMB_ACCENT, 2, cv2.LINE_AA)
                # Fuse
                cv2.line(overlay, (cx, cy - fruit.radius),
                         (cx + 8, cy - fruit.radius - 12),
                         (0, 100, 255), 2, cv2.LINE_AA)
                # Spark
                if self._frame_count % 4 < 2:
                    cv2.circle(overlay, (cx + 8, cy - fruit.radius - 12),
                               4, (0, 200, 255), cv2.FILLED)
                # Text
                cv2.putText(overlay, "X", (cx - 8, cy + 8),
                            cv2.FONT_HERSHEY_DUPLEX, 0.7, BOMB_ACCENT, 2)
            else:
                # Fruit: filled circle with highlight
                cv2.circle(overlay, (cx, cy), fruit.radius,
                           fruit.color, cv2.FILLED, cv2.LINE_AA)
                cv2.circle(overlay, (cx, cy), fruit.radius,
                           (255, 255, 255), 2, cv2.LINE_AA)
                # Highlight
                hx = cx - fruit.radius // 3
                hy = cy - fruit.radius // 3
                cv2.circle(overlay, (hx, hy), fruit.radius // 4,
                           (255, 255, 255), cv2.FILLED, cv2.LINE_AA)

        # Blend overlay
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # HUD
        self._draw_hud(frame)

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------

    def _draw_hud(self, frame: np.ndarray) -> None:
        """Draw score, lives, combo, and game-over screen.

        Args:
            frame: Image to draw on.
        """
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Score (top-left)
        self._text_bg(frame, f"Score: {self.score}", (15, 40), 0.9,
                      (0, 255, 255), 2)

        # Combo (top-center)
        if self.combo > 1:
            combo_text = f"COMBO x{self.combo}!"
            tw = cv2.getTextSize(combo_text, font, 1.0, 2)[0][0]
            self._text_bg(frame, combo_text, (w // 2 - tw // 2, 50),
                          1.0, (0, 200, 255), 2)

        # Lives (top-right)
        hearts = "♥ " * self.lives + "♡ " * (3 - self.lives)
        self._text_bg(frame, f"Lives: {hearts.strip()}", (w - 280, 40),
                      0.7, (100, 100, 255), 2)

        # Game over
        if self.game_over:
            # Dark overlay
            dark = np.zeros_like(frame)
            cv2.addWeighted(frame, 0.4, dark, 0.6, 0, frame)

            go_text = "GAME OVER"
            tw = cv2.getTextSize(go_text, font, 2.0, 3)[0][0]
            cv2.putText(frame, go_text, (w // 2 - tw // 2, h // 2 - 30),
                        font, 2.0, (0, 0, 255), 3, cv2.LINE_AA)

            score_text = f"Final Score: {self.score}  |  Best Combo: {self.max_combo}"
            tw2 = cv2.getTextSize(score_text, font, 0.8, 2)[0][0]
            cv2.putText(frame, score_text, (w // 2 - tw2 // 2, h // 2 + 30),
                        font, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

            restart_text = "Press 'r' to restart"
            tw3 = cv2.getTextSize(restart_text, font, 0.7, 2)[0][0]
            cv2.putText(frame, restart_text, (w // 2 - tw3 // 2, h // 2 + 70),
                        font, 0.7, (200, 200, 200), 2, cv2.LINE_AA)

    @staticmethod
    def _text_bg(frame, text, pos, scale, color, thickness, padding=8):
        """Draw text with dark background."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), bl = cv2.getTextSize(text, font, scale, thickness)
        x, y = pos
        cv2.rectangle(frame, (x - padding, y - th - padding),
                      (x + tw + padding, y + bl + padding),
                      (20, 20, 20), cv2.FILLED)
        cv2.putText(frame, text, (x, y), font, scale, color,
                    thickness, cv2.LINE_AA)

    # ------------------------------------------------------------------
    # Spawning
    # ------------------------------------------------------------------

    def _spawn_wave(self) -> None:
        """Spawn a wave of 1-3 fruits from the bottom."""
        count = random.randint(1, 3)
        for _ in range(count):
            if random.random() < self.BOMB_CHANCE:
                self._spawn_bomb()
            else:
                self._spawn_fruit()

    def _spawn_fruit(self) -> None:
        """Create a single fruit with upward trajectory."""
        ft = random.choice(FRUIT_TYPES)
        x = random.randint(100, self.width - 100)
        y = self.height + 30
        vx = random.uniform(-3, 3)
        vy = random.uniform(-14, -9)

        self._fruits.append(Fruit(
            x=x, y=y, vx=vx, vy=vy,
            radius=ft["radius"], color=ft["color"],
            name=ft["name"], spawn_time=time.time(),
        ))

    def _spawn_bomb(self) -> None:
        """Create a bomb object."""
        x = random.randint(100, self.width - 100)
        y = self.height + 30
        vx = random.uniform(-2, 2)
        vy = random.uniform(-13, -8)

        self._fruits.append(Fruit(
            x=x, y=y, vx=vx, vy=vy,
            radius=28, color=BOMB_COLOR,
            name="Bomb", is_bomb=True,
            spawn_time=time.time(),
        ))

    # ------------------------------------------------------------------
    # Slash detection
    # ------------------------------------------------------------------

    def _check_slash(self, hand_pos: Tuple[int, int]) -> None:
        """Check if the hand slash hits any fruit.

        Args:
            hand_pos: Current hand position.
        """
        hx, hy = hand_pos
        hit_any = False

        for fruit in self._fruits:
            if not fruit.alive or fruit.sliced:
                continue
            dist = math.hypot(hx - fruit.x, hy - fruit.y)
            if dist < fruit.radius + self.SLASH_RADIUS:
                fruit.sliced = True
                fruit.alive = False

                if fruit.is_bomb:
                    self.lives -= 1
                    self.combo = 0
                    self._spawn_bomb_particles(fruit)
                    if self.lives <= 0:
                        self.game_over = True
                else:
                    self.combo += 1
                    self._combo_timer = 0
                    points = 10 * max(1, self.combo)
                    self.score += points
                    self.max_combo = max(self.max_combo, self.combo)
                    self._spawn_slice_particles(fruit)
                    hit_any = True

    def _spawn_slice_particles(self, fruit: Fruit) -> None:
        """Create burst of coloured particles at fruit position.

        Args:
            fruit: The sliced fruit.
        """
        for _ in range(12):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 8)
            r, g, b = fruit.color
            # Colour variation
            cr = max(0, min(255, r + random.randint(-30, 30)))
            cg = max(0, min(255, g + random.randint(-30, 30)))
            cb = max(0, min(255, b + random.randint(-30, 30)))
            self._particles.append(Particle(
                x=fruit.x, y=fruit.y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 3,
                color=(cr, cg, cb),
                life=random.randint(15, 25),
                radius=random.randint(3, 6),
            ))

    def _spawn_bomb_particles(self, fruit: Fruit) -> None:
        """Create explosion particles for bomb.

        Args:
            fruit: The bomb that was hit.
        """
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(4, 10)
            self._particles.append(Particle(
                x=fruit.x, y=fruit.y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 2,
                color=(0, 0, random.randint(150, 255)),
                life=random.randint(15, 30),
                radius=random.randint(4, 8),
            ))
