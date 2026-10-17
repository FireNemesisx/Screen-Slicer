"""
archery_engine.py — Archery Game Mode
Angry Birds style bow and arrow physics, trajectory prediction, and bullseye scoring.
"""

import cv2
import numpy as np
import time
import math
import random

class ArcheryEngine:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        self.state = "IDLE" # IDLE, PULLING, FLYING
        
        self.bow_x = 0
        self.bow_y = 0
        self.target_x = 0
        self.target_y = height // 2
        self.bow_on_left = True
        
        self.arrow_x = 0.0
        self.arrow_y = 0.0
        self.arrow_vx = 0.0
        self.arrow_vy = 0.0
        
        self.pull_x = 0
        self.pull_y = 0
        
        self.gravity = 1.2
        self.score = 0
        self.score_msg = ""
        self.score_timer = 0
        
        self.target_moving = False
        self.target_vy = 4.0
        
        self._was_pinching = False
        self.randomize_positions()
        
    def reset(self):
        self.score = 0
        self.score_msg = ""
        self.score_timer = 0
        self.randomize_positions()
        
    def set_moving_target(self, moving: bool):
        self.target_moving = moving
        
    def randomize_positions(self):
        self.bow_on_left = random.choice([True, False])
        self.state = "IDLE"
        self.target_y = self.height // 2
        self.bow_y = self.height // 2 + random.randint(-100, 100)
        
        if self.bow_on_left:
            self.bow_x = 150
            self.target_x = self.width - 150
        else:
            self.bow_x = self.width - 150
            self.target_x = 150
            
        self.arrow_x = float(self.bow_x)
        self.arrow_y = float(self.bow_y)
        
    def update(self, hand_pos=None, is_pinching=False):
        # Update target movement
        if self.target_moving:
            self.target_y += self.target_vy
            if self.target_y < 150 or self.target_y > self.height - 150:
                self.target_vy *= -1
                
        if self.score_timer > 0:
            self.score_timer -= 1
            
        if self.state == "IDLE":
            if hand_pos:
                hx, hy = hand_pos
                # If pinching near the bow, grab it
                if is_pinching and not self._was_pinching:
                    dist = math.hypot(hx - self.bow_x, hy - self.bow_y)
                    if dist < 100:
                        self.state = "PULLING"
                        self.pull_x = hx
                        self.pull_y = hy
                        
        elif self.state == "PULLING":
            if hand_pos:
                self.pull_x, self.pull_y = hand_pos
                
            if not is_pinching:
                # Release!
                self.state = "FLYING"
                # Calculate velocity based on pull vector
                dx = self.bow_x - self.pull_x
                dy = self.bow_y - self.pull_y
                
                # Tension factor
                self.arrow_vx = dx * 0.3
                self.arrow_vy = dy * 0.3
                self.arrow_x = float(self.bow_x)
                self.arrow_y = float(self.bow_y)
                
        elif self.state == "FLYING":
            # Physics
            self.arrow_vy += self.gravity
            self.arrow_x += self.arrow_vx
            self.arrow_y += self.arrow_vy
            
            # Wind resistance
            self.arrow_vx *= 0.99
            self.arrow_vy *= 0.99
            
            # Collision with target
            target_hit_h = 100 # Total height of target
            target_w = 20
            bullseye_h = 20
            
            # Check crossing target X
            crossed = False
            hit_x = self.arrow_x
            if self.bow_on_left and self.arrow_x >= self.target_x:
                crossed = True
                hit_x = self.target_x
            elif not self.bow_on_left and self.arrow_x <= self.target_x:
                crossed = True
                hit_x = self.target_x
                
            if crossed:
                # Did it hit the vertical bounds?
                ty_min = self.target_y - target_hit_h // 2
                ty_max = self.target_y + target_hit_h // 2
                
                if ty_min <= self.arrow_y <= ty_max:
                    # HIT!
                    # Check Bullseye (center 20 pixels)
                    if abs(self.arrow_y - self.target_y) <= bullseye_h // 2:
                        self.score += 50
                        self.score_msg = "BULLSEYE! +50"
                    else:
                        self.score += 10
                        self.score_msg = "HIT! +10"
                        
                    self.score_timer = 60
                    self.randomize_positions()
                else:
                    # Missed, continue flying until off screen
                    pass
            
            # Reset if off screen
            if self.arrow_y > self.height + 100 or self.arrow_x < -100 or self.arrow_x > self.width + 100:
                self.score_msg = "MISSED!"
                self.score_timer = 40
                self.randomize_positions()
                
        self._was_pinching = is_pinching

    def draw(self, frame):
        # Draw Target
        t_w = 20
        t_h = 100
        tx = int(self.target_x)
        ty = int(self.target_y)
        
        # Target Board (White/Red strips)
        cv2.rectangle(frame, (tx - t_w//2, ty - t_h//2), (tx + t_w//2, ty + t_h//2), (255, 255, 255), cv2.FILLED)
        cv2.rectangle(frame, (tx - t_w//2, ty - t_h//4), (tx + t_w//2, ty + t_h//4), (0, 0, 255), cv2.FILLED)
        # Bullseye (12 noktası)
        cv2.circle(frame, (tx, ty), 10, (0, 255, 255), cv2.FILLED)
        cv2.circle(frame, (tx, ty), 10, (0, 0, 0), 2)
        
        # Draw Bow Structure
        bx = int(self.bow_x)
        by = int(self.bow_y)
        
        # Bow arc
        bow_h = 140
        bow_rect = (bx - 20, by - bow_h//2, 40, bow_h)
        start_angle = -90 if self.bow_on_left else 90
        end_angle = 90 if self.bow_on_left else 270
        cv2.ellipse(frame, (bx, by), (40, bow_h//2), 0, start_angle, end_angle, (139, 69, 19), 6, cv2.LINE_AA)
        
        # Draw State specific
        if self.state == "IDLE":
            # Idle string
            cv2.line(frame, (bx, by - bow_h//2), (bx, by + bow_h//2), (200, 200, 200), 2, cv2.LINE_AA)
            # Arrow resting
            direction = 1 if self.bow_on_left else -1
            self._draw_arrow(frame, bx, by, direction * 80, 0)
            
        elif self.state == "PULLING":
            px, py = int(self.pull_x), int(self.pull_y)
            # String stretched
            cv2.line(frame, (bx, by - bow_h//2), (px, py), (200, 200, 200), 2, cv2.LINE_AA)
            cv2.line(frame, (bx, by + bow_h//2), (px, py), (200, 200, 200), 2, cv2.LINE_AA)
            
            # Arrow being pulled
            dx = bx - px
            dy = by - py
            self._draw_arrow(frame, px, py, dx, dy)
            
            # TRAJECTORY GUIDE (Dotted line)
            sim_x = px
            sim_y = py
            sim_vx = dx * 0.3
            sim_vy = dy * 0.3
            for i in range(20):
                sim_vy += self.gravity
                sim_x += sim_vx
                sim_y += sim_vy
                sim_vx *= 0.99
                sim_vy *= 0.99
                
                # Draw dot
                if i % 2 == 0:
                    cv2.circle(frame, (int(sim_x), int(sim_y)), 3, (0, 255, 255), cv2.FILLED)
                    
        elif self.state == "FLYING":
            # String returned
            cv2.line(frame, (bx, by - bow_h//2), (bx, by + bow_h//2), (200, 200, 200), 2, cv2.LINE_AA)
            # Flying Arrow
            self._draw_arrow(frame, int(self.arrow_x), int(self.arrow_y), self.arrow_vx, self.arrow_vy)
            
        # Draw score message
        if self.score_timer > 0:
            color = (0, 255, 0) if "HIT" in self.score_msg else (0, 0, 255)
            if "BULLSEYE" in self.score_msg:
                color = (0, 255, 255)
            cv2.putText(frame, self.score_msg, (self.width // 2 - 100, 100), cv2.FONT_HERSHEY_DUPLEX, 1.2, color, 3, cv2.LINE_AA)
            
    def _draw_arrow(self, frame, x, y, dx, dy):
        mag = math.hypot(dx, dy)
        if mag == 0:
            return
        
        # Arrow length
        length = 80
        nx = dx / mag
        ny = dy / mag
        
        tip_x = int(x + nx * length)
        tip_y = int(y + ny * length)
        
        # Shaft
        cv2.line(frame, (x, y), (tip_x, tip_y), (150, 150, 150), 3, cv2.LINE_AA)
        # Tip
        cv2.circle(frame, (tip_x, tip_y), 4, (100, 100, 100), cv2.FILLED)
        # Feathers
        fx = int(x + nx * 10)
        fy = int(y + ny * 10)
        p1 = (int(fx - ny * 10), int(fy + nx * 10))
        p2 = (int(fx + ny * 10), int(fy - nx * 10))
        cv2.line(frame, (x, y), p1, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.line(frame, (x, y), p2, (0, 0, 255), 2, cv2.LINE_AA)
