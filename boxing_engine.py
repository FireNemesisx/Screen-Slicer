"""
boxing_engine.py — Action Boxing Game Mode ("Screen Slicer - Boxer")
Interactive AR Boxing: Dodge incoming punches, guard, and throw real punches with your hands!
"""

import math
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class HitSpark:
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    life: int
    max_life: int
    radius: float


@dataclass
class FloatingText:
    text: str
    x: float
    y: float
    color: Tuple[int, int, int]
    scale: float
    life: int
    max_life: int


class BoxingEngine:
    """Boxing Game Engine with animated opponent, punch detection, dodging, and guarding."""

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height

        # Player stats
        self.player_hp = 100.0
        self.player_max_hp = 100.0
        self.player_score = 0
        self.punch_count = 0
        self.dodge_count = 0
        self.combo = 0
        self.combo_timer = 0.0

        # Opponent stats
        self.opp_hp = 100.0
        self.opp_max_hp = 100.0
        self.opp_lag_hp = 100.0  # Catch-up health bar
        self.opp_name = "TITAN (CHAMPION)"

        # Opponent position and animation
        self.opp_x = width // 2
        self.opp_y = height // 2 + 30
        self.sway_time = 0.0
        self.hit_reaction = 0.0
        self.hit_dir = 0.0

        # AI State Machine: IDLE, WINDUP, STRIKE, VULNERABLE, RECOVER, KO
        self.ai_state = "IDLE"
        self.state_timer = 1.5
        self.attack_type = "NONE"  # "HOOK_LEFT", "HOOK_RIGHT", "JAB_CENTER"
        self.attack_target_side = "NONE"  # "LEFT", "RIGHT", "CENTER"
        self.fist_strike_progress = 0.0

        # Visual feedback & particles
        self.sparks: List[HitSpark] = []
        self.floating_texts: List[FloatingText] = []
        self.screen_shake = 0
        self.damage_flash = 0.0

        # Player inputs cooldowns
        self.last_hit_time_hand0 = 0.0
        self.last_hit_time_hand1 = 0.0
        self.is_guarding = False
        self.dodge_result = None  # None, "DODGED", "BLOCKED", "HIT"
        self.dodge_banner_timer = 0.0

        self.game_over = False
        self.victory = False

        self.reset()

    def reset(self):
        """Reset the match."""
        self.player_hp = self.player_max_hp
        self.opp_hp = self.opp_max_hp
        self.opp_lag_hp = self.opp_max_hp
        self.player_score = 0
        self.punch_count = 0
        self.dodge_count = 0
        self.combo = 0
        self.combo_timer = 0.0

        self.ai_state = "IDLE"
        self.state_timer = 1.5
        self.attack_type = "NONE"
        self.attack_target_side = "NONE"
        self.fist_strike_progress = 0.0

        self.sparks.clear()
        self.floating_texts.clear()
        self.screen_shake = 0
        self.damage_flash = 0.0
        self.dodge_result = None
        self.dodge_banner_timer = 0.0

        self.game_over = False
        self.victory = False

    def add_sparks(self, x: float, y: float, count: int = 15, color=(0, 255, 255)):
        """Generate impact spark particles."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(4.0, 14.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.randint(10, 25)
            self.sparks.append(HitSpark(
                x=x, y=y, vx=vx, vy=vy,
                color=color, life=life, max_life=life,
                radius=random.uniform(2.0, 5.0)
            ))

    def add_floating_text(self, text: str, x: float, y: float, color=(0, 255, 255), scale=1.0):
        """Add floating comic action text."""
        self.floating_texts.append(FloatingText(
            text=text, x=x + random.uniform(-20, 20), y=y,
            color=color, scale=scale, life=30, max_life=30
        ))

    def update(self, hands: List[Optional[Tuple[int, int]]], velocities: List[Tuple[float, float]]):
        """Update game logic, AI state machine, and collisions."""
        dt = 0.033  # ~30 FPS step
        self.sway_time += dt

        # Update catch-up health bar
        if self.opp_lag_hp > self.opp_hp:
            self.opp_lag_hp = max(self.opp_hp, self.opp_lag_hp - 0.5)

        # Update combo timer
        if self.combo > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 0

        # Update screen effects
        if self.screen_shake > 0:
            self.screen_shake -= 1
        if self.damage_flash > 0:
            self.damage_flash = max(0.0, self.damage_flash - 0.08)
        if self.hit_reaction > 0:
            self.hit_reaction = max(0.0, self.hit_reaction - dt * 3.0)
        if self.dodge_banner_timer > 0:
            self.dodge_banner_timer -= dt

        # Update particles
        for s in self.sparks:
            s.x += s.vx
            s.y += s.vy
            s.vy += 0.4  # gravity
            s.life -= 1
        self.sparks = [s for s in self.sparks if s.life > 0]

        # Update floating texts
        for ft in self.floating_texts:
            ft.y -= 2.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

        # Check win / lose
        if self.opp_hp <= 0:
            self.victory = True
            self.game_over = True
            self.ai_state = "KO"
            return
        if self.player_hp <= 0:
            self.game_over = True
            self.victory = False
            return

        # ── 1. PLAYER GUARD (BLOCK) & DODGE POSITION ───────────
        h0 = hands[0] if len(hands) > 0 else None
        h1 = hands[1] if len(hands) > 1 else None

        # Guard detection: two hands close to each other in front of upper torso/face
        self.is_guarding = False
        player_x = self.width // 2
        player_y = self.height // 2

        if h0 is not None and h1 is not None:
            dist = math.hypot(h0[0] - h1[0], h0[1] - h1[1])
            mid_y = (h0[1] + h1[1]) // 2
            if dist < 180 and mid_y < self.height * 0.75:
                self.is_guarding = True
            player_x = (h0[0] + h1[0]) // 2
            player_y = mid_y
        elif h0 is not None:
            player_x = h0[0]
            player_y = h0[1]
        elif h1 is not None:
            player_x = h1[0]
            player_y = h1[1]

        # ── 2. PLAYER ATTACK HIT DETECTION ─────────────────────
        now = time.time()
        head_cx = self.opp_x + math.sin(self.sway_time * 2.5) * 35 + (self.hit_dir * self.hit_reaction * 40)
        head_cy = self.opp_y - 70 + math.cos(self.sway_time * 5.0) * 10
        body_cx = self.opp_x + math.sin(self.sway_time * 2.0) * 20
        body_cy = self.opp_y + 40

        for idx, (hand, vel) in enumerate(zip([h0, h1], velocities)):
            if hand is None:
                continue
            last_hit = self.last_hit_time_hand0 if idx == 0 else self.last_hit_time_hand1
            if now - last_hit < 0.22:
                continue

            hx, hy = hand
            speed = math.hypot(vel[0], vel[1])

            # Check hit against opponent head (Radius: 65) or body (Radius: 85)
            d_head = math.hypot(hx - head_cx, hy - head_cy)
            d_body = math.hypot(hx - body_cx, hy - body_cy)

            # Hit requires either fast movement or striking opponent during vulnerability
            is_strike = speed > 10.0 or (self.ai_state == "VULNERABLE" and speed > 5.0)

            if is_strike and (d_head < 70 or d_body < 90):
                if idx == 0:
                    self.last_hit_time_hand0 = now
                else:
                    self.last_hit_time_hand1 = now

                # Calculate damage
                base_dmg = 12.0 if d_head < 70 else 8.0
                multiplier = 1.0

                if self.ai_state == "VULNERABLE":
                    multiplier = 2.0
                    self.add_floating_text("COUNTER HIT! x2", hx, hy - 40, (0, 255, 0), 1.2)
                elif d_head < 70:
                    self.add_floating_text(random.choice(["POW!", "SMACK!", "BOOM!"]), hx, hy - 30, (0, 255, 255), 1.0)
                else:
                    self.add_floating_text(random.choice(["BODY SHOT!", "WHAM!"]), hx, hy - 30, (255, 180, 50), 0.9)

                # Combo bonus
                self.combo += 1
                self.combo_timer = 1.6
                if self.combo > 1:
                    multiplier += (self.combo * 0.15)
                    self.add_floating_text(f"{self.combo}x COMBO!", hx + 30, hy - 60, (0, 255, 255), 0.8)

                damage = base_dmg * multiplier
                self.opp_hp = max(0.0, self.opp_hp - damage)
                self.player_score += int(damage * 10)
                self.punch_count += 1

                # Visual reactions
                self.hit_reaction = 1.0
                self.hit_dir = 1.0 if hx < head_cx else -1.0
                self.add_sparks(hx, hy, count=16, color=(0, 200, 255) if multiplier > 1.5 else (0, 255, 255))
                self.screen_shake = 5

                # Stun opponent if in windup or vulnerable
                if self.ai_state in ("WINDUP", "VULNERABLE"):
                    self.ai_state = "RECOVER"
                    self.state_timer = 0.5
                    self.add_floating_text("INTERRUPTED!", self.opp_x, self.opp_y - 120, (50, 255, 50), 1.1)

        # ── 3. OPPONENT AI STATE MACHINE ───────────────────────
        self.state_timer -= dt

        if self.ai_state == "IDLE":
            if self.state_timer <= 0:
                # Decide next attack
                self.ai_state = "WINDUP"
                attack_choice = random.choice(["HOOK_LEFT", "HOOK_RIGHT", "JAB_CENTER"])
                self.attack_type = attack_choice
                if attack_choice == "HOOK_LEFT":
                    self.attack_target_side = "RIGHT"  # Opponent's left hook strikes player's right
                    self.state_timer = 0.85
                elif attack_choice == "HOOK_RIGHT":
                    self.attack_target_side = "LEFT"   # Opponent's right hook strikes player's left
                    self.state_timer = 0.85
                else:
                    self.attack_target_side = "CENTER"
                    self.state_timer = 0.75
                self.fist_strike_progress = 0.0

        elif self.ai_state == "WINDUP":
            if self.state_timer <= 0:
                self.ai_state = "STRIKE"
                self.state_timer = 0.35
                self.fist_strike_progress = 0.0

        elif self.ai_state == "STRIKE":
            self.fist_strike_progress = min(1.0, self.fist_strike_progress + dt * 3.5)

            if self.state_timer <= 0:
                # Attack reaches culmination! Evaluate player response:
                dodged = False
                blocked = self.is_guarding

                if self.attack_target_side == "RIGHT":
                    # Player must dodge to the LEFT (player_x < width * 0.44)
                    if player_x < self.width * 0.44:
                        dodged = True
                elif self.attack_target_side == "LEFT":
                    # Player must dodge to the RIGHT (player_x > width * 0.56)
                    if player_x > self.width * 0.56:
                        dodged = True
                elif self.attack_target_side == "CENTER":
                    # Player must duck (player_y > height * 0.65) or guard
                    if player_y > self.height * 0.65:
                        dodged = True

                if dodged:
                    self.dodge_result = "DODGED"
                    self.dodge_banner_timer = 1.2
                    self.dodge_count += 1
                    self.player_score += 150
                    self.add_floating_text("CLEAN DODGE!", player_x, player_y - 50, (0, 255, 0), 1.3)
                    # Opponent missed and is wide open!
                    self.ai_state = "VULNERABLE"
                    self.state_timer = 1.3
                elif blocked:
                    self.dodge_result = "BLOCKED"
                    self.dodge_banner_timer = 1.0
                    self.player_hp = max(0.0, self.player_hp - 3.0)  # minimal chip damage
                    self.add_floating_text("SHIELD BLOCK! -3", player_x, player_y - 50, (255, 200, 50), 1.1)
                    self.add_sparks(player_x, player_y, count=10, color=(255, 200, 0))
                    self.screen_shake = 4
                    self.ai_state = "RECOVER"
                    self.state_timer = 0.6
                else:
                    self.dodge_result = "HIT"
                    self.dodge_banner_timer = 1.0
                    dmg = random.randint(15, 22)
                    self.player_hp = max(0.0, self.player_hp - dmg)
                    self.combo = 0
                    self.damage_flash = 0.65
                    self.screen_shake = 12
                    self.add_floating_text(f"OUCH! -{dmg}", player_x, player_y - 60, (0, 0, 255), 1.4)
                    self.add_sparks(player_x, player_y, count=22, color=(0, 0, 255))
                    self.ai_state = "RECOVER"
                    self.state_timer = 0.7

        elif self.ai_state in ("VULNERABLE", "RECOVER"):
            if self.state_timer <= 0:
                self.ai_state = "IDLE"
                self.state_timer = random.uniform(1.2, 2.0)
                self.attack_type = "NONE"
                self.attack_target_side = "NONE"

    def draw(self, frame: np.ndarray, hands: List[Optional[Tuple[int, int]]]):
        """Render opponent character, attack animations, HUD, and effects."""
        h, w = frame.shape[:2]

        # Apply screen shake if active
        if self.screen_shake > 0:
            ox = random.randint(-self.screen_shake, self.screen_shake)
            oy = random.randint(-self.screen_shake, self.screen_shake)
            M = np.float32([[1, 0, ox], [0, 1, oy]])
            frame[:] = cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT)

        # Red flash on player hit
        if self.damage_flash > 0:
            red_overlay = np.zeros_like(frame)
            red_overlay[:, :] = (0, 0, 200)
            cv2.addWeighted(red_overlay, self.damage_flash * 0.45, frame, 1.0, 0, frame)

        # ── 1. DRAW OPPONENT CHARACTER ─────────────────────────
        self._draw_opponent(frame)

        # ── 2. DRAW ATTACK CUES & WARNINGS ─────────────────────
        self._draw_attack_warning(frame)

        # ── 3. DRAW SPARKS & FLOATING TEXTS ────────────────────
        for s in self.sparks:
            alpha = s.life / s.max_life
            r = max(1, int(s.radius * alpha))
            cv2.circle(frame, (int(s.x), int(s.y)), r, s.color, cv2.FILLED, cv2.LINE_AA)

        for ft in self.floating_texts:
            alpha = ft.life / ft.max_life
            font = cv2.FONT_HERSHEY_DUPLEX
            pos = (int(ft.x), int(ft.y))
            # Outline
            cv2.putText(frame, ft.text, pos, font, ft.scale, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(frame, ft.text, pos, font, ft.scale, ft.color, 2, cv2.LINE_AA)

        # ── 4. DRAW PLAYER GLOVES / GUARD SHIELD ───────────────
        self._draw_player_hands(frame, hands)

        # ── 5. DRAW MODERN BOXING HUD ──────────────────────────
        self._draw_hud(frame)

    def _draw_opponent(self, frame: np.ndarray):
        """Draw animated stylized opponent boxer."""
        # Calculate dynamic bobbing and weave
        bob_x = math.sin(self.sway_time * 2.5) * 35 + (self.hit_dir * self.hit_reaction * 45)
        bob_y = math.cos(self.sway_time * 5.0) * 12
        cx = int(self.opp_x + bob_x)
        cy = int(self.opp_y + bob_y)

        # Knockout fall down
        if self.victory:
            cy += min(300, int((time.time() % 10) * 80))

        # Color schemes (Normal vs Stunned vs Vulnerable)
        body_color = (45, 55, 75)
        highlight_color = (70, 90, 130)
        trim_color = (0, 200, 255)
        if self.ai_state == "VULNERABLE":
            trim_color = (50, 255, 50)  # Green glow when vulnerable
        elif self.ai_state == "WINDUP":
            trim_color = (0, 100, 255)  # Orange/Red glow when attacking

        # 1. Torso / Shoulders
        pts_torso = np.array([
            [cx - 130, cy + 130],
            [cx - 95, cy - 10],
            [cx + 95, cy - 10],
            [cx + 130, cy + 130],
            [cx + 80, cy + 220],
            [cx - 80, cy + 220]
        ], np.int32)
        cv2.fillPoly(frame, [pts_torso], body_color)
        cv2.polylines(frame, [pts_torso], True, highlight_color, 3, cv2.LINE_AA)

        # Chest definition lines
        cv2.line(frame, (cx - 70, cy + 40), (cx, cy + 70), highlight_color, 2, cv2.LINE_AA)
        cv2.line(frame, (cx + 70, cy + 40), (cx, cy + 70), highlight_color, 2, cv2.LINE_AA)
        cv2.line(frame, (cx, cy + 70), (cx, cy + 170), highlight_color, 2, cv2.LINE_AA)

        # Champion Belt
        belt_y = cy + 170
        cv2.rectangle(frame, (cx - 85, belt_y), (cx + 85, belt_y + 40), (20, 20, 20), cv2.FILLED)
        cv2.rectangle(frame, (cx - 85, belt_y), (cx + 85, belt_y + 40), (0, 215, 255), 2, cv2.LINE_AA)
        cv2.circle(frame, (cx, belt_y + 20), 16, (0, 215, 255), cv2.FILLED)
        cv2.putText(frame, "C", (cx - 7, belt_y + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)

        # 2. Neck & Head
        cv2.rectangle(frame, (cx - 25, cy - 35), (cx + 25, cy - 5), (60, 75, 100), cv2.FILLED)

        # Head base
        head_r = 50
        cv2.circle(frame, (cx, cy - 70), head_r, (70, 90, 120), cv2.FILLED)
        cv2.circle(frame, (cx, cy - 70), head_r, trim_color, 2, cv2.LINE_AA)

        # Boxing Headgear / Helmet
        cv2.ellipse(frame, (cx, cy - 80), (head_r + 4, 38), 0, 180, 360, (20, 20, 160), cv2.FILLED)
        cv2.circle(frame, (cx - 48, cy - 70), 14, (20, 20, 160), cv2.FILLED)  # Left ear guard
        cv2.circle(frame, (cx + 48, cy - 70), 14, (20, 20, 160), cv2.FILLED)  # Right ear guard

        # Fierce Eyes
        eye_y = cy - 75
        cv2.ellipse(frame, (cx - 20, eye_y), (12, 6), 15, 0, 360, (255, 255, 255), cv2.FILLED)
        cv2.circle(frame, (cx - 18, eye_y), 4, (0, 0, 200) if self.ai_state == "WINDUP" else (0, 0, 0), cv2.FILLED)

        cv2.ellipse(frame, (cx + 20, eye_y), (12, 6), -15, 0, 360, (255, 255, 255), cv2.FILLED)
        cv2.circle(frame, (cx + 18, eye_y), 4, (0, 0, 200) if self.ai_state == "WINDUP" else (0, 0, 0), cv2.FILLED)

        # Eyebrows (Angry)
        cv2.line(frame, (cx - 32, eye_y - 12), (cx - 10, eye_y - 4), (10, 10, 80), 3, cv2.LINE_AA)
        cv2.line(frame, (cx + 32, eye_y - 12), (cx + 10, eye_y - 4), (10, 10, 80), 3, cv2.LINE_AA)

        # Mouthguard
        cv2.ellipse(frame, (cx, cy - 48), (18, 7), 0, 0, 180, (255, 255, 255), cv2.FILLED)
        cv2.ellipse(frame, (cx, cy - 48), (18, 7), 0, 0, 180, (0, 0, 0), 1, cv2.LINE_AA)

        # 3. Opponent Boxing Gloves / Fists
        glove_l_pos = [cx - 85, cy - 30]
        glove_r_pos = [cx + 85, cy - 30]

        # Animate glove movements based on attack
        strike_radius = 42
        if self.ai_state == "WINDUP":
            if self.attack_type == "HOOK_LEFT":
                glove_l_pos[0] -= 45
                glove_l_pos[1] -= 30
            elif self.attack_type == "HOOK_RIGHT":
                glove_r_pos[0] += 45
                glove_r_pos[1] -= 30
            elif self.attack_type == "JAB_CENTER":
                glove_r_pos[1] -= 35

        elif self.ai_state == "STRIKE":
            prog = self.fist_strike_progress
            strike_radius = int(42 + prog * 95)  # Fist grows huge as it flies towards screen!
            if self.attack_type == "HOOK_LEFT":
                glove_l_pos[0] = int(glove_l_pos[0] + prog * 320)
                glove_l_pos[1] = int(glove_l_pos[1] + prog * 200)
            elif self.attack_type == "HOOK_RIGHT":
                glove_r_pos[0] = int(glove_r_pos[0] - prog * 320)
                glove_r_pos[1] = int(glove_r_pos[1] + prog * 200)
            elif self.attack_type == "JAB_CENTER":
                glove_r_pos[1] = int(glove_r_pos[1] + prog * 250)

        # Draw Left Glove (Red Boxing Glove)
        r_l = strike_radius if (self.ai_state == "STRIKE" and self.attack_type == "HOOK_LEFT") else 42
        cv2.circle(frame, tuple(glove_l_pos), r_l, (20, 20, 210), cv2.FILLED)
        cv2.circle(frame, tuple(glove_l_pos), r_l, (0, 200, 255), 2, cv2.LINE_AA)
        cv2.ellipse(frame, tuple(glove_l_pos), (int(r_l * 0.7), int(r_l * 0.4)), -30, 0, 360, (40, 40, 255), cv2.FILLED)

        # Draw Right Glove (Red Boxing Glove)
        r_r = strike_radius if (self.ai_state == "STRIKE" and self.attack_type in ("HOOK_RIGHT", "JAB_CENTER")) else 42
        cv2.circle(frame, tuple(glove_r_pos), r_r, (20, 20, 210), cv2.FILLED)
        cv2.circle(frame, tuple(glove_r_pos), r_r, (0, 200, 255), 2, cv2.LINE_AA)
        cv2.ellipse(frame, tuple(glove_r_pos), (int(r_r * 0.7), int(r_r * 0.4)), 30, 0, 360, (40, 40, 255), cv2.FILLED)

        # Stars spinning if KO or Stunned
        if self.victory:
            t = time.time() * 6
            for i in range(4):
                angle = t + i * (math.pi / 2)
                sx = int(cx + math.cos(angle) * 75)
                sy = int(cy - 120 + math.sin(angle) * 20)
                cv2.circle(frame, (sx, sy), 8, (0, 255, 255), cv2.FILLED)

    def _draw_attack_warning(self, frame: np.ndarray):
        """Draw interactive warnings instructing the player to dodge or block."""
        h, w = frame.shape[:2]

        if self.ai_state == "WINDUP":
            flash = int((time.time() * 15) % 2)
            warn_color = (0, 0, 255) if flash == 0 else (0, 220, 255)

            if self.attack_target_side == "RIGHT":
                # Danger on right -> DODGE LEFT!
                cv2.arrowedLine(frame, (w // 2 + 100, h // 2), (w // 2 - 220, h // 2), warn_color, 8, tipLength=0.25)
                self._draw_badge(frame, "<<< SOLA KAC! (DODGE LEFT!)", (w // 2 - 250, h // 2 - 60), warn_color)

                # Danger zone circle on right
                cv2.circle(frame, (int(w * 0.72), h // 2), 100, (0, 0, 255), 3, cv2.LINE_AA)
                cv2.putText(frame, "DANGER ZONE", (int(w * 0.72) - 80, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            elif self.attack_target_side == "LEFT":
                # Danger on left -> DODGE RIGHT!
                cv2.arrowedLine(frame, (w // 2 - 100, h // 2), (w // 2 + 220, h // 2), warn_color, 8, tipLength=0.25)
                self._draw_badge(frame, "SAGA KAC! (DODGE RIGHT!) >>>", (w // 2 - 180, h // 2 - 60), warn_color)

                # Danger zone circle on left
                cv2.circle(frame, (int(w * 0.28), h // 2), 100, (0, 0, 255), 3, cv2.LINE_AA)
                cv2.putText(frame, "DANGER ZONE", (int(w * 0.28) - 80, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            elif self.attack_target_side == "CENTER":
                # Center strike -> DUCK OR GUARD!
                self._draw_badge(frame, "EGIL VEYA BLOKLA! (DUCK / GUARD)", (w // 2 - 240, h // 2 - 60), warn_color)
                cv2.circle(frame, (w // 2, h // 2), 120, (0, 0, 255), 3, cv2.LINE_AA)

        elif self.ai_state == "VULNERABLE":
            # Opponent is open for counter-attacks!
            pulse = int((time.time() * 10) % 2)
            col = (0, 255, 0) if pulse == 0 else (100, 255, 100)
            self._draw_badge(frame, "VUR! ACIK VERDI! (COUNTER ATTACK!)", (w // 2 - 260, h // 2 - 140), col)

        # Dodge Result Banner
        if self.dodge_banner_timer > 0 and self.dodge_result:
            if self.dodge_result == "DODGED":
                self._draw_badge(frame, "MUKEMMEL KACIS! (EVADED!)", (w // 2 - 200, 220), (0, 255, 0))
            elif self.dodge_result == "BLOCKED":
                self._draw_badge(frame, "BLOKLANDI! (BLOCKED)", (w // 2 - 160, 220), (255, 200, 0))

    def _draw_player_hands(self, frame: np.ndarray, hands: List[Optional[Tuple[int, int]]]):
        """Render player's glowing gloves and guard shield."""
        # 1. Guard Shield between hands if blocking
        if self.is_guarding and len(hands) >= 2 and hands[0] and hands[1]:
            hx = (hands[0][0] + hands[1][0]) // 2
            hy = (hands[0][1] + hands[1][1]) // 2
            # Draw glowing blue shield
            cv2.circle(frame, (hx, hy), 95, (255, 200, 0), 3, cv2.LINE_AA)
            cv2.ellipse(frame, (hx, hy), (80, 50), 0, 0, 360, (255, 180, 50), 2, cv2.LINE_AA)
            cv2.putText(frame, "GUARD ACTIVE", (hx - 70, hy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        # 2. Player Gloves (Cyan / Neon Blue for Player)
        for h_pt in hands:
            if h_pt is not None:
                x, y = h_pt
                # Outer ring
                cv2.circle(frame, (x, y), 34, (255, 255, 255), 2, cv2.LINE_AA)
                # Glove fill
                cv2.circle(frame, (x, y), 28, (255, 180, 0), cv2.FILLED, cv2.LINE_AA)
                # Crosshair target in center of glove
                cv2.line(frame, (x - 12, y), (x + 12, y), (0, 0, 0), 2, cv2.LINE_AA)
                cv2.line(frame, (x, y - 12), (x, y + 12), (0, 0, 0), 2, cv2.LINE_AA)

    def _draw_hud(self, frame: np.ndarray):
        """Draw health bars, combo counter, score, and state banners."""
        h, w = frame.shape[:2]

        # ── 1. OPPONENT HEALTH BAR (Top Center) ─────────────────
        bar_w = 460
        bar_h = 26
        bx = (w - bar_w) // 2
        by = 35

        # Lagging / Catch-up red bar
        opp_hp_ratio = self.opp_hp / self.opp_max_hp
        opp_lag_ratio = self.opp_lag_hp / self.opp_max_hp

        # Background
        cv2.rectangle(frame, (bx - 4, by - 4), (bx + bar_w + 4, by + bar_h + 4), (20, 20, 20), cv2.FILLED)
        cv2.rectangle(frame, (bx - 4, by - 4), (bx + bar_w + 4, by + bar_h + 4), (100, 100, 100), 2, cv2.LINE_AA)

        # Yellow catch-up bar
        cv2.rectangle(frame, (bx, by), (bx + int(bar_w * opp_lag_ratio), by + bar_h), (0, 200, 255), cv2.FILLED)
        # Red actual health bar
        cv2.rectangle(frame, (bx, by), (bx + int(bar_w * opp_hp_ratio), by + bar_h), (0, 0, 220), cv2.FILLED)

        # Opponent Name & HP Text
        cv2.putText(frame, f"{self.opp_name}: {int(self.opp_hp)}/100", (bx + 10, by - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)

        # ── 2. PLAYER HEALTH BAR (Bottom Left) ──────────────────
        p_bar_w = 280
        p_bar_h = 20
        pbx = 40
        pby = h - 65

        p_hp_ratio = self.player_hp / self.player_max_hp
        cv2.rectangle(frame, (pbx - 3, pby - 3), (pbx + p_bar_w + 3, pby + p_bar_h + 3), (20, 20, 20), cv2.FILLED)
        cv2.rectangle(frame, (pbx - 3, pby - 3), (pbx + p_bar_w + 3, pby + p_bar_h + 3), (100, 100, 100), 2, cv2.LINE_AA)

        # Green Player Health Bar
        cv2.rectangle(frame, (pbx, pby), (pbx + int(p_bar_w * p_hp_ratio), pby + p_bar_h), (50, 220, 50), cv2.FILLED)
        cv2.putText(frame, f"SEN (PLAYER HP): {int(self.player_hp)}/100", (pbx, pby - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)

        # ── 3. SCORE & STATS (Top Left) ────────────────────────
        cv2.putText(frame, f"SKOR: {self.player_score}", (40, 45),
                    cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Yumruk: {self.punch_count} | Kavis: {self.dodge_count}", (40, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)

        # ── 4. COMBO DISPLAY (Right Side) ──────────────────────
        if self.combo > 1:
            scale = 1.0 + min(0.6, self.combo * 0.1)
            cv2.putText(frame, f"{self.combo}x COMBO!", (w - 280, 80),
                        cv2.FONT_HERSHEY_DUPLEX, scale, (0, 255, 255), 3, cv2.LINE_AA)

        # ── 5. GAME OVER / VICTORY OVERLAYS ────────────────────
        if self.game_over:
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), cv2.FILLED)
            cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

            if self.victory:
                self._draw_badge(frame, "K.O. — KAZANDIN! (VICTORY!)", (w // 2 - 280, h // 2 - 50), (0, 255, 255), scale=1.5, pad=25)
                cv2.putText(frame, f"Toplam Skor: {self.player_score}", (w // 2 - 140, h // 2 + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
            else:
                self._draw_badge(frame, "NAKAVT! YENILDIN! (DEFEAT)", (w // 2 - 260, h // 2 - 50), (0, 0, 255), scale=1.5, pad=25)

            cv2.putText(frame, "Tekrar baslamak icin 'R' tuşuna basın | Menü icin 'M'",
                        (w // 2 - 260, h // 2 + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2, cv2.LINE_AA)

    def _draw_badge(self, frame: np.ndarray, text: str, pos: Tuple[int, int], color: Tuple[int, int, int], scale=0.85, pad=12):
        """Draw an arcade banner with background."""
        font = cv2.FONT_HERSHEY_DUPLEX
        (tw, th), bl = cv2.getTextSize(text, font, scale, 2)
        x, y = pos
        cv2.rectangle(frame, (x - pad, y - th - pad), (x + tw + pad, y + bl + pad), (15, 15, 15), cv2.FILLED)
        cv2.rectangle(frame, (x - pad, y - th - pad), (x + tw + pad, y + bl + pad), color, 2, cv2.LINE_AA)
        cv2.putText(frame, text, (x, y), font, scale, color, 2, cv2.LINE_AA)
