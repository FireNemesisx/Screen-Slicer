"""
sun_engine.py — Sun in Palm Interactive Mode
Calculates palm openness and draws dynamic sun/black holes for two hands.
"""

import math
import time
from typing import Tuple, List, Optional
import cv2
import numpy as np


class SunColor:
    """Palette of sun colors including black hole."""
    FIRE = (0, 120, 255)      # Orange/Red
    PLASMA = (255, 100, 100)  # Blue/Purple
    YELLOW = (0, 230, 255)    # Standard Yellow
    WHITE = (255, 255, 255)   # White Star
    BLACK = (10, 10, 10)      # Black Hole

    ALL = [FIRE, PLASMA, YELLOW, WHITE, BLACK]
    NAMES = ["Fire", "Plasma", "Yellow", "White", "Black Hole"]


class SunEngine:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Two hands support
        self.hands_data = [
            {"center": None, "openness": 0.0, "color_idx": 0, "color": SunColor.ALL[0]},
            {"center": None, "openness": 0.0, "color_idx": 4, "color": SunColor.ALL[4]} # Hand 2 defaults to Black Hole
        ]
        
        self.particles = []
        
    def reset(self):
        self.particles.clear()
        
    def cycle_color(self, hand_idx: int):
        if 0 <= hand_idx < 2:
            idx = (self.hands_data[hand_idx]["color_idx"] + 1) % len(SunColor.ALL)
            self.hands_data[hand_idx]["color_idx"] = idx
            self.hands_data[hand_idx]["color"] = SunColor.ALL[idx]
        
    def get_color_name(self, hand_idx: int) -> str:
        if 0 <= hand_idx < 2:
            return SunColor.NAMES[self.hands_data[hand_idx]["color_idx"]]
        return ""
        
    def _process_hand(self, hand_landmarks_px: Optional[List[Tuple[int, int]]]) -> Tuple[Optional[Tuple[int, int]], float]:
        if not hand_landmarks_px or len(hand_landmarks_px) < 21:
            return None, 0.0
            
        wrist = hand_landmarks_px[0]
        index_mcp = hand_landmarks_px[5]
        pinky_mcp = hand_landmarks_px[17]
        middle_mcp = hand_landmarks_px[9]
        
        cx = int((wrist[0] + index_mcp[0] + pinky_mcp[0]) / 3.0)
        cy = int((wrist[1] + index_mcp[1] + pinky_mcp[1]) / 3.0)
        
        tips = [hand_landmarks_px[4], hand_landmarks_px[8], hand_landmarks_px[12], 
                hand_landmarks_px[16], hand_landmarks_px[20]]
        
        max_dist = max(math.hypot(t[0] - wrist[0], t[1] - wrist[1]) for t in tips)
        base_dist = math.hypot(middle_mcp[0] - wrist[0], middle_mcp[1] - wrist[1])
        
        ratio = max_dist / max(base_dist, 1.0)
        normalized = (ratio - 1.2) / (2.2 - 1.2)
        openness = max(0.0, min(1.0, normalized))
        
        return (cx, cy), openness

    def update(self, hand0_px: Optional[List[Tuple[int, int]]], hand1_px: Optional[List[Tuple[int, int]]]):
        """Updates the suns' positions and brightness for both hands."""
        self.hands_data[0]["center"], self.hands_data[0]["openness"] = self._process_hand(hand0_px)
        self.hands_data[1]["center"], self.hands_data[1]["openness"] = self._process_hand(hand1_px)
        self._update_particles()

    def _update_particles(self):
        # Spawn new particles
        for i, hdata in enumerate(self.hands_data):
            if not hdata["center"]:
                continue
                
            cx, cy = hdata["center"]
            is_black = (hdata["color"] == SunColor.BLACK)
            other_idx = 1 - i
            other_hdata = self.hands_data[other_idx]
            
            # Calculate distance and intensity
            dist_to_other = 0.0
            if other_hdata["center"]:
                tx, ty = other_hdata["center"]
                dist_to_other = math.hypot(tx - cx, ty - cy)
            
            # If closer, intensity increases (max impact 1.5 when touching, 0.2 when far)
            closeness = max(0.2, 1.5 - (dist_to_other / 1000.0)) if other_hdata["center"] else 0.5
            intensity = hdata["openness"] * closeness
            
            # Spawn rate relies on intensity
            spawn_chance = intensity * 2.5 # High intensity = many particles
            num_spawns = 0
            while spawn_chance > 0:
                if np.random.rand() < min(1.0, spawn_chance):
                    num_spawns += 1
                spawn_chance -= 1.0
                
            for _ in range(num_spawns):
                angle = np.random.uniform(0, 2 * math.pi)
                speed = np.random.uniform(3, 8) + (intensity * 4.0) # Faster when intense
                
                vx = math.cos(angle) * speed * (1.0 if not is_black else -1.0)
                vy = math.sin(angle) * speed * (1.0 if not is_black else -1.0)
                
                # Shoot particles towards the OTHER hand (energy transfer)
                if other_hdata["center"] and np.random.rand() < 0.6: # 60% of particles flow to other hand
                    tx, ty = other_hdata["center"]
                    dx = tx - cx
                    dy = ty - cy
                    if dist_to_other > 0:
                        vx = (dx / dist_to_other) * speed * 2.5
                        vy = (dy / dist_to_other) * speed * 2.5
                
                # Start radius
                dist_offset = 60 if not is_black else 120
                px = cx + math.cos(angle) * dist_offset
                py = cy + math.sin(angle) * dist_offset
                
                self.particles.append({
                    "x": px, "y": py,
                    "vx": vx, "vy": vy,
                    "color": hdata["color"],
                    "life": 40
                })
                
        # Update existing particles
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            
        self.particles = [p for p in self.particles if p["life"] > 0]

    def draw(self, frame: np.ndarray):
        overlay = np.zeros_like(frame)
        
        # 1. Draw particles
        for p in self.particles:
            alpha = p["life"] / 40.0
            p_color = p["color"]
            if p_color == SunColor.BLACK:
                p_color = (200, 100, 255) # Purple for black hole particles
            pr = max(1, int(4 * alpha))
            cv2.circle(frame, (int(p["x"]), int(p["y"])), pr, p_color, cv2.FILLED, cv2.LINE_AA)
            
        # 2. Draw Suns
        for hdata in self.hands_data:
            if not hdata["center"]:
                continue
                
            cx, cy = hdata["center"]
            color = hdata["color"]
            is_black = (color == SunColor.BLACK)
            openness = hdata["openness"]
            
            # ALL suns are massive now
            base_radius = int(60 + openness * 120)
            
            # Time-based pulsing
            pulse = math.sin(time.time() * 5.0) * 8 * openness
            r = int(base_radius + pulse)
            if r < 1: r = 1

            if is_black:
                # Black Hole Effect
                aura_color = (200, 100, 255) 
                for i in range(5, 0, -1):
                    cr = r + i * 10
                    alpha = 0.1 + (0.05 * (5-i)) * openness
                    cv2.circle(overlay, (cx, cy), cr, aura_color, cv2.FILLED)
                    
                cv2.addWeighted(overlay, 1.0, frame, 1.0, 0, frame)
                cv2.circle(frame, (cx, cy), r, color, cv2.FILLED)
                cv2.circle(frame, (cx, cy), r + 2, (0, 0, 0), 2, cv2.LINE_AA)
                overlay.fill(0) # Reset overlay for next hand
                
            else:
                # Massive Sun Effect
                for i in range(4, 0, -1):
                    cr = r + int(i * 20 * openness)
                    alpha = 0.15 + (0.1 * (4-i)) * openness
                    temp = frame.copy()
                    cv2.circle(temp, (cx, cy), cr, color, cv2.FILLED)
                    cv2.addWeighted(temp, alpha, frame, 1 - alpha, 0, frame)
                    
                core_color = (255, 255, 255) if openness > 0.8 else color
                cv2.circle(frame, (cx, cy), r - 5, core_color, cv2.FILLED, cv2.LINE_AA)
