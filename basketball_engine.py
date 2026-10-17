"""
basketball_engine.py — Basketball Game Mode
Physics-based basketball game where you hit the ball with your hand to score.
"""

import cv2
import numpy as np
import time
import math

class BasketballEngine:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        self.ball_radius = 35
        self.ball_x = width // 2
        self.ball_y = height - 100
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        
        self.hoop_y = 180
        self.hoop_width = 140
        self.hoop_x = width // 2
        self.hoop_vx = 0.0
        self.moving_hoop = False
        
        self.score = 0
        self.score_timer = 0
        
        self.gravity = 1.2
        self.friction = 0.99
        self.bounce = -0.75
        
        self.reset()
        
    def reset(self):
        self.ball_x = self.width // 2
        self.ball_y = self.height - 100
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.score = 0
        self.score_timer = 0
        
    def set_moving_hoop(self, moving: bool):
        self.moving_hoop = moving
        if moving:
            self.hoop_vx = 6.0
        else:
            self.hoop_vx = 0.0
            
    def update(self, hand_pos=None, hand_velocity=(0.0, 0.0)):
        # Update hoop
        if self.moving_hoop:
            self.hoop_x += self.hoop_vx
            if self.hoop_x - self.hoop_width//2 < 100 or self.hoop_x + self.hoop_width//2 > self.width - 100:
                self.hoop_vx *= -1
                
        # Hand interaction
        if hand_pos:
            hx, hy = hand_pos
            dist = math.hypot(hx - self.ball_x, hy - self.ball_y)
            
            # Hit detection
            if dist < self.ball_radius + 50:
                hvx, hvy = hand_velocity
                push_mag = math.hypot(hvx, hvy)
                
                # If hand is moving fast enough, swat the ball
                if push_mag > 5.0:
                    self.ball_vx = hvx * 1.5
                    self.ball_vy = hvy * 1.5
                else:
                    # Gentle push away
                    dx = self.ball_x - hx
                    dy = self.ball_y - hy
                    mag = max(dist, 1.0)
                    self.ball_vx += (dx / mag) * 8.0
                    self.ball_vy += (dy / mag) * 8.0
                    
        # Physics
        self.ball_vy += self.gravity
        self.ball_vx *= self.friction
        self.ball_vy *= self.friction
        
        # Speed limits
        speed = math.hypot(self.ball_vx, self.ball_vy)
        if speed > 60:
            self.ball_vx = (self.ball_vx / speed) * 60
            self.ball_vy = (self.ball_vy / speed) * 60
            
        old_y = self.ball_y
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy
        
        # Floor / Ceiling Bounce
        if self.ball_y > self.height - self.ball_radius:
            self.ball_y = self.height - self.ball_radius
            self.ball_vy *= self.bounce
            # Stop rolling completely if slow
            if abs(self.ball_vy) < 2.0:
                self.ball_vy = 0.0
                self.ball_vx *= 0.9
        elif self.ball_y < self.ball_radius:
            self.ball_y = self.ball_radius
            self.ball_vy *= self.bounce
            
        # Wall Bounce
        if self.ball_x < self.ball_radius:
            self.ball_x = self.ball_radius
            self.ball_vx *= self.bounce
        elif self.ball_x > self.width - self.ball_radius:
            self.ball_x = self.width - self.ball_radius
            self.ball_vx *= self.bounce
            
        # Hoop collision & Scoring
        hx_min = self.hoop_x - self.hoop_width // 2
        hx_max = self.hoop_x + self.hoop_width // 2
        hy = self.hoop_y
        
        # Score if passed downwards through the hoop
        if old_y < hy and self.ball_y >= hy:
            if hx_min < self.ball_x < hx_max:
                if self.score_timer == 0:
                    self.score += 1
                    self.score_timer = 45 # frames
                    
        # Rim bouncing
        rim_points = [(hx_min, hy), (hx_max, hy)]
        for rx, ry in rim_points:
            dist_rim = math.hypot(self.ball_x - rx, self.ball_y - ry)
            if dist_rim < self.ball_radius + 5: # 5 is rim thickness
                # Resolve collision
                nx = (self.ball_x - rx) / dist_rim
                ny = (self.ball_y - ry) / dist_rim
                # Push out
                self.ball_x = rx + nx * (self.ball_radius + 5)
                self.ball_y = ry + ny * (self.ball_radius + 5)
                # Bounce velocity
                dot = self.ball_vx * nx + self.ball_vy * ny
                self.ball_vx -= 2 * dot * nx
                self.ball_vy -= 2 * dot * ny
                self.ball_vx *= 0.8
                self.ball_vy *= 0.8
                    
        if self.score_timer > 0:
            self.score_timer -= 1
            
    def draw(self, frame):
        # Draw Hoop
        hx_min = int(self.hoop_x - self.hoop_width // 2)
        hx_max = int(self.hoop_x + self.hoop_width // 2)
        hy = int(self.hoop_y)
        
        # Backboard
        cv2.rectangle(frame, (hx_min - 40, hy - 100), (hx_max + 40, hy + 20), (255, 255, 255), 4)
        cv2.rectangle(frame, (int(self.hoop_x - 30), hy - 60), (int(self.hoop_x + 30), hy), (255, 255, 255), 2)
        
        # Net
        for i in range(5):
            x = hx_min + i * (self.hoop_width // 4)
            cv2.line(frame, (x, hy), (int(self.hoop_x), hy + 80), (220, 220, 220), 2, cv2.LINE_AA)
            
        # Rim
        cv2.line(frame, (hx_min, hy), (hx_max, hy), (0, 100, 255), 10, cv2.LINE_AA)
            
        # Draw Ball
        bx, by = int(self.ball_x), int(self.ball_y)
        cv2.circle(frame, (bx, by), self.ball_radius, (0, 140, 255), cv2.FILLED, cv2.LINE_AA)
        
        # Ball patterns
        cv2.circle(frame, (bx, by), self.ball_radius, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.line(frame, (bx - self.ball_radius, by), (bx + self.ball_radius, by), (0, 0, 0), 2, cv2.LINE_AA)
        cv2.line(frame, (bx, by - self.ball_radius), (bx, by + self.ball_radius), (0, 0, 0), 2, cv2.LINE_AA)
        cv2.ellipse(frame, (bx, by), (self.ball_radius, self.ball_radius//2), 45, 0, 360, (0, 0, 0), 2, cv2.LINE_AA)
        
        # Score visual
        if self.score_timer > 15:
            scale = 1.0 + (45 - self.score_timer) / 30.0
            cv2.putText(frame, "SCORE!", (bx - 50, by - 60), cv2.FONT_HERSHEY_DUPLEX, scale, (0, 255, 0), 3, cv2.LINE_AA)
