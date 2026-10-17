"""
air_hockey.py — Two-Player Air Hockey Game Mode

A neon-styled air hockey game played with hand tracking.
Player 1 (blue, top half) and Player 2 (red, bottom half)
each control a mallet with their hand. The puck bounces
off walls and scores when entering a goal.

Features: physics-based puck, friction, goal detection,
particle trails, screen shake, and modern neon HUD.
"""

import math
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class Particle:
    """Visual particle for trail/goal effects."""
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    life: int = 20
    radius: int = 3


class AirHockey:
    """Two-player air hockey game engine.

    Attributes:
        score_p1: Player 1 score (top).
        score_p2: Player 2 score (bottom).
        game_over: Whether the game ended.
        winner: Winner string or None.
    """

    MAX_SCORE = 7
    PUCK_RADIUS = 18
    MALLET_RADIUS = 30
    GOAL_WIDTH_RATIO = 0.35
    FRICTION = 0.985
    MAX_PUCK_SPEED = 22
    BORDER = 30

    # Neon colors (BGR)
    COL_P1 = (255, 180, 50)    # Cyan-blue
    COL_P2 = (50, 50, 255)     # Red
    COL_PUCK = (0, 255, 255)   # Yellow
    COL_BORDER = (180, 130, 60)
    COL_CENTER = (100, 80, 40)
    COL_GOAL = (0, 200, 100)

    def __init__(self, width: int = 1280, height: int = 720) -> None:
        self.width = width
        self.height = height
        self.score_p1 = 0
        self.score_p2 = 0
        self.game_over = False
        self.winner: Optional[str] = None

        self._goal_w = int(width * self.GOAL_WIDTH_RATIO)
        self._goal_x1 = (width - self._goal_w) // 2
        self._goal_x2 = self._goal_x1 + self._goal_w

        # Puck state
        self._px = float(width // 2)
        self._py = float(height // 2)
        self._pvx = 0.0
        self._pvy = 0.0

        # Mallet positions (will be set by hand tracking)
        self._m1x = float(width // 2)
        self._m1y = float(height // 4)
        self._m2x = float(width // 2)
        self._m2y = float(3 * height // 4)

        # Previous mallet positions for velocity
        self._pm1x = self._m1x
        self._pm1y = self._m1y
        self._pm2x = self._m2x
        self._pm2y = self._m2y

        self._particles: List[Particle] = []
        self._shake = 0.0
        self._goal_flash = 0
        self._goal_flash_color = (0, 0, 0)
        self._frame = 0
        self._countdown = 90  # 3 sec countdown at start
        self._last_scorer = 0

    def reset(self) -> None:
        """Reset entire game."""
        self.score_p1 = 0
        self.score_p2 = 0
        self.game_over = False
        self.winner = None
        self._reset_puck(0)
        self._particles.clear()
        self._countdown = 90
        self._shake = 0.0

    def _reset_puck(self, direction: int = 0) -> None:
        """Reset puck to center with optional direction."""
        self._px = float(self.width // 2)
        self._py = float(self.height // 2)
        speed = 4.0
        angle = random.uniform(-0.5, 0.5)
        if direction > 0:
            self._pvx = math.sin(angle) * speed
            self._pvy = speed
        elif direction < 0:
            self._pvx = math.sin(angle) * speed
            self._pvy = -speed
        else:
            self._pvx = 0.0
            self._pvy = 0.0
        self._countdown = 60

    def update(self, hand_pos_0: Optional[Tuple[int, int]] = None,
               hand_pos_1: Optional[Tuple[int, int]] = None) -> None:
        """Advance game by one frame.

        Args:
            hand_pos_0: Player 2 hand (bottom half).
            hand_pos_1: Player 1 hand (top half).
        """
        if self.game_over:
            return

        self._frame += 1
        b = self.BORDER
        half = self.height // 2

        # Store previous mallet positions
        self._pm1x, self._pm1y = self._m1x, self._m1y
        self._pm2x, self._pm2y = self._m2x, self._m2y

        # Update mallet positions from hand tracking
        # Player 1 = top half, Player 2 = bottom half
        if hand_pos_1 is not None:
            mx = max(b + self.MALLET_RADIUS, min(self.width - b - self.MALLET_RADIUS, float(hand_pos_1[0])))
            my = max(b + self.MALLET_RADIUS, min(half - self.MALLET_RADIUS, float(hand_pos_1[1])))
            self._m1x, self._m1y = mx, my

        if hand_pos_0 is not None:
            mx = max(b + self.MALLET_RADIUS, min(self.width - b - self.MALLET_RADIUS, float(hand_pos_0[0])))
            my = max(half + self.MALLET_RADIUS, min(self.height - b - self.MALLET_RADIUS, float(hand_pos_0[1])))
            self._m2x, self._m2y = mx, my

        # Countdown
        if self._countdown > 0:
            self._countdown -= 1
            return

        # Puck physics
        self._pvx *= self.FRICTION
        self._pvy *= self.FRICTION
        self._px += self._pvx
        self._py += self._pvy

        # Clamp speed
        speed = math.hypot(self._pvx, self._pvy)
        if speed > self.MAX_PUCK_SPEED:
            scale = self.MAX_PUCK_SPEED / speed
            self._pvx *= scale
            self._pvy *= scale

        # Wall bounces (left/right)
        pr = self.PUCK_RADIUS
        if self._px - pr < b:
            self._px = float(b + pr)
            self._pvx = abs(self._pvx) * 0.9
        elif self._px + pr > self.width - b:
            self._px = float(self.width - b - pr)
            self._pvx = -abs(self._pvx) * 0.9

        # Top/bottom wall bounces (except goal area)
        in_goal_x = self._goal_x1 < self._px < self._goal_x2

        if self._py - pr < b:
            if not in_goal_x:
                self._py = float(b + pr)
                self._pvy = abs(self._pvy) * 0.9
            else:
                # Goal for Player 2!
                self.score_p2 += 1
                self._goal_effect(2)
                if self.score_p2 >= self.MAX_SCORE:
                    self.game_over = True
                    self.winner = "PLAYER 2"
                else:
                    self._reset_puck(-1)
                return

        if self._py + pr > self.height - b:
            if not in_goal_x:
                self._py = float(self.height - b - pr)
                self._pvy = -abs(self._pvy) * 0.9
            else:
                # Goal for Player 1!
                self.score_p1 += 1
                self._goal_effect(1)
                if self.score_p1 >= self.MAX_SCORE:
                    self.game_over = True
                    self.winner = "PLAYER 1"
                else:
                    self._reset_puck(1)
                return

        # Mallet-puck collisions
        self._check_mallet_collision(
            self._m1x, self._m1y,
            self._m1x - self._pm1x, self._m1y - self._pm1y
        )
        self._check_mallet_collision(
            self._m2x, self._m2y,
            self._m2x - self._pm2x, self._m2y - self._pm2y
        )

        # Puck trail particles
        if speed > 3:
            self._particles.append(Particle(
                x=self._px, y=self._py,
                vx=random.uniform(-0.5, 0.5),
                vy=random.uniform(-0.5, 0.5),
                color=self.COL_PUCK, life=12, radius=2
            ))

        # Update particles
        for p in self._particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self._particles = [p for p in self._particles if p.life > 0]

        # Decay shake
        self._shake *= 0.85
        if self._goal_flash > 0:
            self._goal_flash -= 1

    def _check_mallet_collision(self, mx: float, my: float,
                                 mvx: float, mvy: float) -> None:
        """Check and resolve puck-mallet collision."""
        dx = self._px - mx
        dy = self._py - my
        dist = math.hypot(dx, dy)
        min_dist = float(self.PUCK_RADIUS + self.MALLET_RADIUS)

        if dist < min_dist and dist > 0:
            # Normalize collision vector
            nx = dx / dist
            ny = dy / dist

            # Separate puck from mallet
            overlap = min_dist - dist
            self._px += nx * overlap
            self._py += ny * overlap

            # Reflect puck velocity + add mallet velocity
            dot = self._pvx * nx + self._pvy * ny
            self._pvx -= 2 * dot * nx
            self._pvy -= 2 * dot * ny

            # Add mallet momentum
            self._pvx += mvx * 1.2
            self._pvy += mvy * 1.2

            self._shake = 5.0

            # Hit particles
            for _ in range(6):
                angle = random.uniform(0, 2 * math.pi)
                sp = random.uniform(2, 5)
                self._particles.append(Particle(
                    x=self._px, y=self._py,
                    vx=math.cos(angle) * sp, vy=math.sin(angle) * sp,
                    color=(255, 255, 255), life=15, radius=3
                ))

    def _goal_effect(self, scorer: int) -> None:
        """Spawn goal celebration particles."""
        self._shake = 12.0
        self._goal_flash = 20
        self._goal_flash_color = self.COL_P1 if scorer == 1 else self.COL_P2
        self._last_scorer = scorer

        cx = self.width // 2
        cy = self.BORDER if scorer == 2 else self.height - self.BORDER
        for _ in range(30):
            angle = random.uniform(0, 2 * math.pi)
            sp = random.uniform(3, 10)
            col = self.COL_P1 if scorer == 1 else self.COL_P2
            self._particles.append(Particle(
                x=float(cx), y=float(cy),
                vx=math.cos(angle) * sp, vy=math.sin(angle) * sp,
                color=col, life=random.randint(20, 40),
                radius=random.randint(3, 7)
            ))

    def draw(self, frame: np.ndarray) -> None:
        """Render all game elements onto the frame."""
        h, w = frame.shape[:2]
        overlay = np.zeros((h, w, 3), dtype=np.uint8)

        # Apply screen shake
        sx = int(random.uniform(-self._shake, self._shake)) if self._shake > 0.5 else 0
        sy = int(random.uniform(-self._shake, self._shake)) if self._shake > 0.5 else 0

        # Goal flash
        if self._goal_flash > 0:
            alpha = self._goal_flash / 20.0
            flash = np.full_like(overlay, self._goal_flash_color, dtype=np.uint8)
            cv2.addWeighted(flash, alpha * 0.3, overlay, 1.0, 0, overlay)

        b = self.BORDER

        # Draw rink border
        cv2.rectangle(overlay, (b, b), (w - b, h - b), self.COL_BORDER, 3, cv2.LINE_AA)

        # Center line
        cv2.line(overlay, (b, h // 2), (w - b, h // 2), self.COL_CENTER, 2, cv2.LINE_AA)

        # Center circle
        cv2.circle(overlay, (w // 2, h // 2), 60, self.COL_CENTER, 2, cv2.LINE_AA)
        cv2.circle(overlay, (w // 2, h // 2), 5, self.COL_CENTER, cv2.FILLED)

        # Goals (top and bottom)
        goal_col = self.COL_GOAL
        # Top goal
        cv2.rectangle(overlay, (self._goal_x1, b - 8), (self._goal_x2, b + 4),
                       goal_col, cv2.FILLED)
        cv2.rectangle(overlay, (self._goal_x1, b - 8), (self._goal_x2, b + 4),
                       (255, 255, 255), 1, cv2.LINE_AA)
        # Bottom goal
        cv2.rectangle(overlay, (self._goal_x1, h - b - 4), (self._goal_x2, h - b + 8),
                       goal_col, cv2.FILLED)
        cv2.rectangle(overlay, (self._goal_x1, h - b - 4), (self._goal_x2, h - b + 8),
                       (255, 255, 255), 1, cv2.LINE_AA)

        # Particles
        for p in self._particles:
            alpha = p.life / 20.0
            r = max(1, int(p.radius * alpha))
            cv2.circle(overlay, (int(p.x) + sx, int(p.y) + sy), r,
                       p.color, cv2.FILLED, cv2.LINE_AA)

        # Puck
        px, py = int(self._px) + sx, int(self._py) + sy
        # Glow
        cv2.circle(overlay, (px, py), self.PUCK_RADIUS + 8,
                   (0, 80, 80), cv2.FILLED, cv2.LINE_AA)
        cv2.circle(overlay, (px, py), self.PUCK_RADIUS,
                   self.COL_PUCK, cv2.FILLED, cv2.LINE_AA)
        cv2.circle(overlay, (px, py), self.PUCK_RADIUS,
                   (255, 255, 255), 2, cv2.LINE_AA)
        cv2.circle(overlay, (px, py), self.PUCK_RADIUS // 3,
                   (200, 200, 200), 1, cv2.LINE_AA)

        # Mallets
        self._draw_mallet(overlay, int(self._m1x) + sx, int(self._m1y) + sy, self.COL_P1)
        self._draw_mallet(overlay, int(self._m2x) + sx, int(self._m2y) + sy, self.COL_P2)

        # Blend onto camera frame
        mask = overlay > 0
        blended = frame.copy()
        blended[mask] = cv2.addWeighted(frame, 0.3, overlay, 0.7, 0)[mask]

        # Draw semi-transparent rink background
        rink_bg = np.zeros_like(frame)
        cv2.rectangle(rink_bg, (b, b), (w - b, h - b), (40, 35, 25), cv2.FILLED)
        cv2.addWeighted(blended, 1.0, rink_bg, 0.4, 0, frame)

        # Re-draw bright elements on top
        frame[mask] = cv2.addWeighted(frame, 0.4, overlay, 0.6, 0)[mask]

        # Countdown
        if self._countdown > 0:
            sec = self._countdown // 30 + 1
            font = cv2.FONT_HERSHEY_SIMPLEX
            txt = str(sec)
            ts = cv2.getTextSize(txt, font, 3.0, 4)[0]
            tx = w // 2 - ts[0] // 2
            ty = h // 2 + ts[1] // 2
            cv2.putText(frame, txt, (tx, ty), font, 3.0,
                        (0, 255, 255), 4, cv2.LINE_AA)

        # HUD
        self._draw_hud(frame)

    def _draw_mallet(self, img: np.ndarray, x: int, y: int,
                      color: Tuple[int, int, int]) -> None:
        """Draw a mallet with glow effect."""
        r = self.MALLET_RADIUS
        # Outer glow
        glow_col = tuple(max(0, c // 3) for c in color)
        cv2.circle(img, (x, y), r + 10, glow_col, cv2.FILLED, cv2.LINE_AA)
        # Main body
        cv2.circle(img, (x, y), r, color, cv2.FILLED, cv2.LINE_AA)
        cv2.circle(img, (x, y), r, (255, 255, 255), 2, cv2.LINE_AA)
        # Inner ring
        cv2.circle(img, (x, y), r // 2, (255, 255, 255), 1, cv2.LINE_AA)
        # Center dot
        cv2.circle(img, (x, y), 4, (255, 255, 255), cv2.FILLED)

    def _draw_hud(self, frame: np.ndarray) -> None:
        """Draw scores, labels, and game-over screen."""
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Player 1 score (top-left)
        self._text_bg(frame, f"P1: {self.score_p1}", (15, 55),
                      0.8, self.COL_P1, 2)

        # Player 2 score (bottom-left)
        self._text_bg(frame, f"P2: {self.score_p2}", (15, h - 15),
                      0.8, self.COL_P2, 2)

        # Score dots (center-right)
        dot_x = w - 50
        for i in range(self.MAX_SCORE):
            cy1 = 60 + i * 18
            col1 = self.COL_P1 if i < self.score_p1 else (60, 60, 60)
            cv2.circle(frame, (dot_x, cy1), 5, col1, cv2.FILLED)

            cy2 = h - 60 - i * 18
            col2 = self.COL_P2 if i < self.score_p2 else (60, 60, 60)
            cv2.circle(frame, (dot_x, cy2), 5, col2, cv2.FILLED)

        # Game over
        if self.game_over and self.winner:
            dark = np.zeros_like(frame)
            cv2.addWeighted(frame, 0.35, dark, 0.65, 0, frame)

            txt = f"{self.winner} WINS!"
            ts = cv2.getTextSize(txt, font, 1.8, 3)[0]
            tx = w // 2 - ts[0] // 2
            color = self.COL_P1 if "1" in self.winner else self.COL_P2
            cv2.putText(frame, txt, (tx, h // 2 - 20), font, 1.8,
                        color, 3, cv2.LINE_AA)

            sub = f"Score: {self.score_p1} - {self.score_p2}  |  Press 'r' to restart"
            ts2 = cv2.getTextSize(sub, font, 0.7, 2)[0]
            cv2.putText(frame, sub, (w // 2 - ts2[0] // 2, h // 2 + 30),
                        font, 0.7, (200, 200, 200), 2, cv2.LINE_AA)

    @staticmethod
    def _text_bg(frame, text, pos, scale, color, thickness, pad=8):
        """Draw text with dark background."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), bl = cv2.getTextSize(text, font, scale, thickness)
        x, y = pos
        cv2.rectangle(frame, (x - pad, y - th - pad),
                       (x + tw + pad, y + bl + pad),
                       (20, 20, 20), cv2.FILLED)
        cv2.putText(frame, text, (x, y), font, scale, color,
                     thickness, cv2.LINE_AA)
