"""
main.py — Hand-Gesture AR Drawing + Fruit Ninja + Air Hockey (v4)

Modes:
    AR_DRAW     — Draw, place 3D shapes, erase, particle brush
    FRUIT_NINJA — Slash flying fruits
    AIR_HOCKEY  — Two-player air hockey
    SUN_IN_PALM — Hold a dynamic sun in your palm

Controls:
    f       — Toggle Fruit Ninja mode
    h       — Toggle Air Hockey mode
    g       — Toggle Sun in Palm mode
    c       — Clear canvas
    r       — Restart game (Fruit Ninja)
    1-5     — Select drawing colour
    +/-     — Line thickness
    e       — Toggle eraser mode
    p       — Toggle particle brush
    t       — Cycle 3D shape (Cube/Pyramid/Diamond)
    s       — Screenshot
    z       — Undo last stroke
    x       — Remove last placed shape
    q/ESC   — Quit
"""

import os
import time
import math
import ctypes
from enum import Enum, auto

# Enable Per-Monitor High-DPI awareness on Windows to prevent blurry/pixelated scaling
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import cv2
import numpy as np
from PIL import Image, ImageDraw

from hand_tracker import HandTracker
from gesture_engine import GestureEngine, GestureState, COLOR_PALETTE, COLOR_NAMES
from geometry_engine import GeometryEngine, ShapeType
from fruit_ninja import FruitNinja
from air_hockey import AirHockey
from ui_engine import UIEngine
from sun_engine import SunEngine
from basketball_engine import BasketballEngine
from archery_engine import ArcheryEngine
from boxing_engine import BoxingEngine


class AppMode(Enum):
    """Application modes."""
    MAIN_MENU = auto()
    AR_DRAW = auto()
    FRUIT_NINJA = auto()
    AIR_HOCKEY = auto()
    SUN_IN_PALM = auto()
    BASKETBALL = auto()
    ARCHERY = auto()
    BOXING = auto()


# ── Colour palette (BGR) ─────────────────────────────────────────────
COL_CURSOR      = (255, 200, 0)
COL_TEXT_BG     = (30, 30, 30)
COL_FPS         = (0, 255, 255)
COL_STATE       = (255, 180, 0)
COL_HELP        = (180, 180, 180)
COL_ZOOM        = (255, 100, 255)
COL_ERASER      = (100, 100, 255)
COL_PARTICLE    = (255, 200, 100)


def draw_text_bg(frame, text, pos, scale=0.6, color=(255, 255, 255),
                 bg=COL_TEXT_BG, thick=1, pad=6):
    """Wrapper around modern UI text rendering."""
    UIEngine.draw_text_modern(frame, text, pos, scale=scale, color=color, bg_color=bg, thick=thick, pad=pad)


def draw_strokes(canvas, all_drawings, current_pts, cur_color, cur_thick,
                 zoom=1.0, pan=(0.0, 0.0)):
    """Render all strokes with per-stroke colour/thickness.

    Args:
        canvas: Drawing layer.
        all_drawings: List of stroke dicts.
        current_pts: In-progress stroke points.
        cur_color: Current drawing colour.
        cur_thick: Current line thickness.
        zoom: Zoom factor.
        pan: Pan offset.
    """
    def xform(pts):
        return [(int(px * zoom + pan[0]), int(py * zoom + pan[1]))
                for px, py in pts]

    for s in all_drawings:
        pts = s["points"]
        if len(pts) > 1:
            arr = np.array(xform(pts), np.int32).reshape((-1, 1, 2))
            t = max(1, int(s["thickness"] * zoom))
            cv2.polylines(canvas, [arr], False, s["color"], t, cv2.LINE_AA)

    if len(current_pts) > 1:
        arr = np.array(xform(current_pts), np.int32).reshape((-1, 1, 2))
        t = max(1, int(cur_thick * zoom))
        cv2.polylines(canvas, [arr], False, cur_color, t, cv2.LINE_AA)


def draw_color_palette(frame, selected_idx, y_pos=70):
    """Draw colour selection indicator on HUD.

    Args:
        frame: Frame to draw on.
        selected_idx: Currently selected colour index.
        y_pos: Y position for the palette row.
    """
    x = 10
    for i, (col, name) in enumerate(zip(COLOR_PALETTE, COLOR_NAMES)):
        bx, by = x + i * 40, y_pos
        cv2.rectangle(frame, (bx, by), (bx + 30, by + 20), col, cv2.FILLED)
        if i == selected_idx:
            cv2.rectangle(frame, (bx - 2, by - 2), (bx + 32, by + 22),
                          (255, 255, 255), 2)
        cv2.putText(frame, str(i + 1), (bx + 8, by + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    # Label
    draw_text_bg(frame, f"Thick: {0}", (x + 210, y_pos + 15), 0.45,
                 (255, 255, 255))


def main() -> None:
    """Run the application main loop."""
    tracker = HandTracker(smooth_window=7, num_hands=2)
    gestures = GestureEngine(pinch_threshold=40)
    geometry = GeometryEngine(size=50, focal_length=500, z_offset=300)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    WINDOW_NAME = "Screen Slicer"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    is_fullscreen = False

    mode = AppMode.MAIN_MENU
    ninja = None
    hockey = None
    sun = None
    basketball = None
    archery = None
    boxing = None
    canvas = None
    prev_time = time.time()
    screenshot_count = 0

    print("[INFO] Started. Welcome to Screen Slicer.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        if canvas is None or canvas.shape[:2] != (h, w):
            canvas = np.zeros((h, w, 3), dtype=np.uint8)
        if ninja is None:
            ninja = FruitNinja(width=w, height=h)
        if hockey is None:
            hockey = AirHockey(width=w, height=h)
        if sun is None:
            sun = SunEngine(width=w, height=h)
        if basketball is None:
            basketball = BasketballEngine(width=w, height=h)
        if archery is None:
            archery = ArcheryEngine(width=w, height=h)
        if boxing is None:
            boxing = BoxingEngine(width=w, height=h)

        # ── Hand tracking ─────────────────────────────────────────
        num_hands = tracker.process_frame(frame)
        tracker.draw_landmarks(frame)

        smoothed_0 = tracker.get_smoothed_index_tip(0)
        smoothed_1 = tracker.get_smoothed_index_tip(1)
        index_tip_0 = tracker.get_landmark(HandTracker.INDEX_TIP, 0)
        thumb_tip_0 = tracker.get_landmark(HandTracker.THUMB_TIP, 0)
        index_only_up_0 = tracker.is_index_only_up(0)
        thumb_up_0 = tracker.is_thumb_up(0)
        index_up_0 = tracker.is_finger_up(0, 0)
        hand_speed_0 = tracker.get_hand_velocity(0)
        index_tip_1 = tracker.get_landmark(HandTracker.INDEX_TIP, 1)

        # Calculate hand velocity vectors for physics engines and boxing
        hand_velocity_0 = (0.0, 0.0)
        if smoothed_0 is not None:
            if 'prev_smoothed_0' not in locals() or prev_smoothed_0 is None:
                hand_velocity_0 = (0.0, 0.0)
            else:
                hand_velocity_0 = (float(smoothed_0[0] - prev_smoothed_0[0]), float(smoothed_0[1] - prev_smoothed_0[1]))
            prev_smoothed_0 = smoothed_0
        else:
            prev_smoothed_0 = None
        hand_velocity = hand_velocity_0

        hand_velocity_1 = (0.0, 0.0)
        if smoothed_1 is not None:
            if 'prev_smoothed_1' not in locals() or prev_smoothed_1 is None:
                hand_velocity_1 = (0.0, 0.0)
            else:
                hand_velocity_1 = (float(smoothed_1[0] - prev_smoothed_1[0]), float(smoothed_1[1] - prev_smoothed_1[1]))
            prev_smoothed_1 = smoothed_1
        else:
            prev_smoothed_1 = None

        # ── MAIN MENU MODE ───────────────────────────────────────
        if mode == AppMode.MAIN_MENU:
            combined = frame.copy()
            
            # 1. High-Definition Header Banner
            UIEngine.draw_modern_header(combined, w, h, title="SCREEN SLICER", subtitle="AUGMENTED REALITY GESTURE HUB")

            # 2. Responsive 2-Column Button Grid
            c1_x1, c1_x2 = w // 2 - 310, w // 2 - 15
            c2_x1, c2_x2 = w // 2 + 15, w // 2 + 310
            row_h = 68
            row_gap = 14
            y_start = 125

            fs_title = "Pencere Modu" if is_fullscreen else "Tam Ekran"
            fs_sub = "Pencereye don" if is_fullscreen else "Ekrani kapla"
            
            buttons = [
                {
                    "title": "AR Draw",
                    "subtext": "3D Sekil & Cizim",
                    "key": "D",
                    "icon": "ART",
                    "accent": (255, 240, 0),     # Cyan BGR
                    "mode": AppMode.AR_DRAW,
                    "rect": (c1_x1, y_start, c1_x2, y_start + row_h)
                },
                {
                    "title": "Fruit Ninja",
                    "subtext": "Meyve Kesmece",
                    "key": "F",
                    "icon": "SLASH",
                    "accent": (0, 145, 255),     # Orange BGR
                    "mode": AppMode.FRUIT_NINJA,
                    "rect": (c2_x1, y_start, c2_x2, y_start + row_h)
                },
                {
                    "title": "Air Hockey",
                    "subtext": "2 Kisilik Mac",
                    "key": "H",
                    "icon": "PUCK",
                    "accent": (230, 80, 200),    # Magenta BGR
                    "mode": AppMode.AIR_HOCKEY,
                    "rect": (c1_x1, y_start + (row_h + row_gap), c1_x2, y_start + (row_h + row_gap) + row_h)
                },
                {
                    "title": "Sun in Palm",
                    "subtext": "Avucta Gunes",
                    "key": "G",
                    "icon": "SUN",
                    "accent": (30, 215, 255),    # Solar Gold BGR
                    "mode": AppMode.SUN_IN_PALM,
                    "rect": (c2_x1, y_start + (row_h + row_gap), c2_x2, y_start + (row_h + row_gap) + row_h)
                },
                {
                    "title": "Basketball",
                    "subtext": "Fizik & Pota",
                    "key": "B",
                    "icon": "HOOP",
                    "accent": (40, 120, 255),    # Amber BGR
                    "mode": AppMode.BASKETBALL,
                    "rect": (c1_x1, y_start + 2 * (row_h + row_gap), c1_x2, y_start + 2 * (row_h + row_gap) + row_h)
                },
                {
                    "title": "Archery",
                    "subtext": "Yay & Hedef Vur",
                    "key": "A",
                    "icon": "BOW",
                    "accent": (100, 240, 60),    # Emerald BGR
                    "mode": AppMode.ARCHERY,
                    "rect": (c2_x1, y_start + 2 * (row_h + row_gap), c2_x2, y_start + 2 * (row_h + row_gap) + row_h)
                },
                {
                    "title": "Boks / Boxing",
                    "subtext": "Titan ile Dovus",
                    "key": "K",
                    "icon": "FIGHT",
                    "accent": (80, 50, 255),     # Crimson BGR
                    "mode": AppMode.BOXING,
                    "rect": (c1_x1, y_start + 3 * (row_h + row_gap), c1_x2, y_start + 3 * (row_h + row_gap) + row_h)
                },
                {
                    "title": fs_title,
                    "subtext": fs_sub,
                    "key": "U",
                    "icon": "FULL",
                    "accent": (255, 200, 90),    # Sky Blue BGR
                    "mode": "FULLSCREEN",
                    "rect": (c2_x1, y_start + 3 * (row_h + row_gap), c2_x2, y_start + 3 * (row_h + row_gap) + row_h)
                },
            ]

            # Pinch detection
            is_pinching = False
            if smoothed_0 is not None and index_tip_0 is not None and thumb_tip_0 is not None:
                thumb_idx_dist = math.hypot(thumb_tip_0[0] - index_tip_0[0], thumb_tip_0[1] - index_tip_0[1])
                is_pinching = thumb_idx_dist < 40

            # Render Buttons
            for btn in buttons:
                x1, y1, x2, y2 = btn["rect"]
                hovered = False
                if smoothed_0 is not None:
                    hx, hy = smoothed_0
                    if x1 <= hx <= x2 and y1 <= hy <= y2:
                        hovered = True

                UIEngine.draw_modern_card_button(
                    combined,
                    rect=btn["rect"],
                    title=btn["title"],
                    key_hint=btn["key"],
                    icon_text=btn["icon"],
                    accent_color=btn["accent"],
                    hovered=hovered,
                    is_pinching=is_pinching,
                    subtext=btn["subtext"]
                )

                if hovered and is_pinching:
                    if btn["mode"] == "FULLSCREEN":
                        is_fullscreen = not is_fullscreen
                        if is_fullscreen:
                            cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                        else:
                            cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                    else:
                        mode = btn["mode"]
                        if mode == AppMode.BASKETBALL: basketball.reset()
                        if mode == AppMode.SUN_IN_PALM: sun.reset()
                        if mode == AppMode.FRUIT_NINJA: ninja.reset()
                        if mode == AppMode.AIR_HOCKEY: hockey.reset()
                        if mode == AppMode.ARCHERY: archery.reset()
                        if mode == AppMode.BOXING: boxing.reset()
                    cv2.waitKey(300) # Prevents instant double click

            # Modern Cursor Reticle
            if smoothed_0 is not None:
                UIEngine.draw_modern_reticle(combined, smoothed_0, is_pinching)

            # Sleek Bottom Status Bar
            UIEngine.draw_modern_status_bar(
                combined, w, h,
                "Butona dokunup cimdik atin veya klavye tusuna basin  •  [ U ] Tam Ekran  •  [ Q ] Cikis"
            )
                    
        # ── AR DRAW MODE ──────────────────────────────────────────
        elif mode == AppMode.AR_DRAW:
            state = gestures.update(
                num_hands=num_hands,
                index_only_up_0=index_only_up_0,
                thumb_up_0=thumb_up_0,
                index_up_0=index_up_0,
                thumb_tip_0=thumb_tip_0,
                index_tip_0=index_tip_0,
                smoothed_tip_0=smoothed_0,
                index_tip_1=index_tip_1,
                current_shape_type=geometry.current_shape.value,
            )

            overlay = np.zeros((h, w, 3), dtype=np.uint8)

            # Redraw canvas
            canvas[:] = 0
            draw_strokes(canvas, gestures.get_all_drawings(),
                         gestures.get_drawing_points(),
                         gestures.current_color,
                         gestures.line_thickness,
                         gestures.zoom_scale,
                         tuple(gestures.pan_offset))

            # Draw placed shapes (auto-rotating)
            for shape in gestures.placed_shapes:
                st = ShapeType(shape.shape_type)
                rotated = geometry.get_auto_rotated_shape(
                    shape.rotation_offset, st)
                pts_2d = geometry.project_to_2d(rotated, shape.x, shape.y)
                edges = geometry.get_edges(st)
                geometry.draw_wireframe(canvas, pts_2d, edges,
                                        shape.color, 2)

            # Draw particles
            for p in gestures.particles:
                alpha = p.life / 40.0
                r = max(1, int(p.radius * alpha))
                cv2.circle(canvas, (int(p.x), int(p.y)), r,
                           p.color, cv2.FILLED, cv2.LINE_AA)

            # Cursor / state-specific overlays
            if smoothed_0 is not None:
                sx, sy = smoothed_0

                if state == GestureState.IDLE:
                    cv2.circle(overlay, (sx, sy), 16, COL_CURSOR, 2, cv2.LINE_AA)
                    cv2.circle(overlay, (sx, sy), 5, COL_CURSOR, cv2.FILLED)

                elif state == GestureState.DRAWING:
                    cv2.circle(overlay, (sx, sy), 10, gestures.current_color,
                               cv2.FILLED, cv2.LINE_AA)
                    cv2.circle(overlay, (sx, sy), 14, gestures.current_color,
                               2, cv2.LINE_AA)

                elif state == GestureState.CUBE_PREVIEW:
                    # Preview shape following finger (semi-transparent)
                    orient = tracker.get_palm_orientation(0) or (0, 0, 0)
                    rotated = geometry.get_rotated_shape(*orient)
                    pts_2d = geometry.project_to_2d(rotated, sx, sy)
                    edges = geometry.get_edges()
                    geometry.draw_wireframe(overlay, pts_2d, edges,
                                            gestures.current_color, 2)
                    # "Release to place" hint
                    cv2.putText(overlay, "Release to place",
                                (sx - 60, sy - 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                (200, 200, 200), 1, cv2.LINE_AA)

                elif state == GestureState.ERASER:
                    cv2.circle(overlay, (sx, sy), gestures.ERASER_RADIUS,
                               COL_ERASER, 2, cv2.LINE_AA)
                    cv2.line(overlay, (sx - 8, sy - 8), (sx + 8, sy + 8),
                             COL_ERASER, 2, cv2.LINE_AA)
                    cv2.line(overlay, (sx + 8, sy - 8), (sx - 8, sy + 8),
                             COL_ERASER, 2, cv2.LINE_AA)

                elif state == GestureState.PARTICLE:
                    cv2.circle(overlay, (sx, sy), 12, COL_PARTICLE,
                               2, cv2.LINE_AA)

                elif state == GestureState.ZOOM:
                    if index_tip_1 is not None:
                        cv2.line(overlay, (sx, sy), index_tip_1,
                                 COL_ZOOM, 2, cv2.LINE_AA)
                        mx = (sx + index_tip_1[0]) // 2
                        my = (sy + index_tip_1[1]) // 2
                        pct = int(gestures.zoom_scale * 100)
                        cv2.putText(overlay, f"{pct}%", (mx - 20, my - 15),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                    COL_ZOOM, 2, cv2.LINE_AA)

            # Composite
            combined = cv2.addWeighted(frame, 1.0, canvas, 0.7, 0)
            combined = cv2.addWeighted(combined, 1.0, overlay, 1.0, 0)

            # HUD
            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            draw_text_bg(combined, f"FPS: {fps:.0f}", (10, 30), 0.7, COL_FPS)

            # State + shape info
            state_str = state.name
            if state == GestureState.ZOOM:
                state_str += f" {int(gestures.zoom_scale * 100)}%"
            draw_text_bg(combined, f"State: {state_str}",
                         (w - 300, 30), 0.6, COL_STATE)

            # Mode label
            mode_label = "AR DRAW"
            if gestures.eraser_mode:
                mode_label += " [ERASER]"
            elif gestures.particle_mode:
                mode_label += " [PARTICLE]"
            draw_text_bg(combined, mode_label,
                         (w // 2 - 80, 30), 0.6, (0, 200, 255))

            # Shape type
            draw_text_bg(combined, f"Shape: {geometry.get_shape_name()}",
                         (w - 300, 60), 0.5, (200, 200, 255))

            # Colour palette
            px = 10
            for i, col in enumerate(COLOR_PALETTE):
                bx, by = px + i * 38, 58
                UIEngine.draw_rounded_rect(combined, (bx, by), (bx + 28, by + 18), col, -1, 6)
                if i == gestures.current_color_idx:
                    UIEngine.draw_rounded_rect(combined, (bx - 2, by - 2),
                                  (bx + 30, by + 20), (255, 255, 255), 2, 8, filled=False)
                cv2.putText(combined, str(i + 1), (bx + 8, by + 14),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)

            # Thickness
            draw_text_bg(combined, f"Thick: {gestures.line_thickness}",
                         (210, 71), 0.45, (255, 255, 255))

            # Shapes count
            n = len(gestures.placed_shapes)
            if n > 0:
                draw_text_bg(combined, f"Shapes: {n}", (310, 71),
                             0.45, (200, 255, 200))

            # Help
            lines = [
                f"Index up:DRAW | l:Toggle 3D ({'ON' if gestures.enable_3d_placement else 'OFF'}) | Pinch:PLACE 3D",
                "1-5:Color +/-:Thick e:Eraser p:Particle t:Shape",
                "s:Screenshot z:Undo x:Del c:Clear f:Ninja",
            ]
            for i, line in enumerate(lines):
                draw_text_bg(combined, line,
                             (10, h - 10 - (len(lines) - 1 - i) * 25),
                             0.4, COL_HELP)

        # ── FRUIT NINJA MODE ─────────────────────────────────────
        elif mode == AppMode.FRUIT_NINJA:
            hand_pos = smoothed_0
            ninja.update(hand_pos=hand_pos, hand_speed=hand_speed_0)

            combined = frame.copy()
            ninja.draw(combined)

            if hand_pos is not None:
                cx, cy = hand_pos
                cv2.circle(combined, (cx, cy), 8, (255, 255, 255), 2,
                           cv2.LINE_AA)
                if hand_speed_0 > ninja.SLASH_SPEED_THRESH:
                    cv2.circle(combined, (cx, cy), 20, (0, 200, 255), 2,
                               cv2.LINE_AA)

            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now
            draw_text_bg(combined, f"FPS: {fps:.0f}", (15, h - 15),
                         0.5, COL_FPS)
            draw_text_bg(combined, "FRUIT NINJA",
                         (w // 2 - 60, 30), 0.6, (0, 0, 255))
            draw_text_bg(combined, "'f':AR Draw | 'h':Hockey | 'r':Restart",
                         (w - 350, h - 15), 0.4, COL_HELP)

        # ── AIR HOCKEY MODE ────────────────────────────────────
        elif mode == AppMode.AIR_HOCKEY:
            smoothed_1 = tracker.get_smoothed_index_tip(1)
            hockey.update(hand_pos_0=smoothed_0, hand_pos_1=smoothed_1)

            combined = frame.copy()
            hockey.draw(combined)

            # Draw hand cursors
            if smoothed_0 is not None:
                cv2.circle(combined, smoothed_0, 5, (255, 255, 255), 2, cv2.LINE_AA)
            if smoothed_1 is not None:
                cv2.circle(combined, smoothed_1, 5, (255, 255, 255), 2, cv2.LINE_AA)

            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now
            draw_text_bg(combined, f"FPS: {fps:.0f}", (15, h - 15),
                         0.5, COL_FPS)
            draw_text_bg(combined, "AIR HOCKEY",
                         (w // 2 - 70, 30), 0.7, (0, 200, 255))
            draw_text_bg(combined, "'h':AR Draw | 'f':Ninja | 'r':Restart",
                         (w - 400, h - 15), 0.4, COL_HELP)

        # ── SUN IN PALM MODE ───────────────────────────────────
        elif mode == AppMode.SUN_IN_PALM:
            hand0 = tracker.hands_landmarks_px[0] if tracker.num_hands_detected > 0 else None
            hand1 = tracker.hands_landmarks_px[1] if tracker.num_hands_detected > 1 else None
            sun.update(hand0, hand1)
            
            combined = frame.copy()
            sun.draw(combined)
            
            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now
            draw_text_bg(combined, f"FPS: {fps:.0f}", (15, h - 15), 0.5, COL_FPS)
            draw_text_bg(combined, "SUN IN PALM", (w // 2 - 70, 30), 0.7, (0, 200, 255))
            draw_text_bg(combined, f"H1: {sun.get_color_name(0)} (SPACE) | H2: {sun.get_color_name(1)} (C)", (w // 2 - 180, 65), 0.5, (255, 200, 100))
            draw_text_bg(combined, "'g':AR Draw | 'f':Ninja | 'h':Hockey | 'm':Menu", (w - 400, h - 15), 0.4, COL_HELP)

        # ── BASKETBALL MODE ────────────────────────────────────
        elif mode == AppMode.BASKETBALL:
            basketball.update(hand_pos=smoothed_0, hand_velocity=hand_velocity)
            
            combined = frame.copy()
            basketball.draw(combined)
            
            if smoothed_0:
                cv2.circle(combined, smoothed_0, 15, (255, 255, 255), 2, cv2.LINE_AA)
                
            draw_text_bg(combined, f"SCORE: {basketball.score}", (15, 50), 1.0, (0, 255, 0), thick=2)
            draw_text_bg(combined, "BASKETBALL (1: Static | 2: Moving)", (w // 2 - 200, 30), 0.7, (0, 200, 255))
            draw_text_bg(combined, "'m':Menu | 'q':Quit", (w - 250, h - 15), 0.5, COL_HELP)

        # ── ARCHERY MODE ───────────────────────────────────────
        elif mode == AppMode.ARCHERY:
            is_pinching = False
            if smoothed_0 is not None and index_tip_0 is not None and thumb_tip_0 is not None:
                thumb_idx_dist = math.hypot(thumb_tip_0[0] - index_tip_0[0], thumb_tip_0[1] - index_tip_0[1])
                is_pinching = thumb_idx_dist < 40
                
            archery.update(hand_pos=smoothed_0, is_pinching=is_pinching)
            
            combined = frame.copy()
            archery.draw(combined)
            
            if smoothed_0:
                color = (0, 255, 0) if is_pinching else (255, 255, 255)
                cv2.circle(combined, smoothed_0, 10, color, cv2.FILLED if is_pinching else 2, cv2.LINE_AA)
                
            draw_text_bg(combined, f"SCORE: {archery.score}", (15, 50), 1.0, (0, 255, 0), thick=2)
            draw_text_bg(combined, "ARCHERY (1: Static | 2: Moving Target)", (w // 2 - 200, 30), 0.7, (0, 200, 255))
            draw_text_bg(combined, "'m':Menu | 'q':Quit", (w - 250, h - 15), 0.5, COL_HELP)

        # ── BOXING MODE ────────────────────────────────────────
        elif mode == AppMode.BOXING:
            boxing.update(
                hands=[smoothed_0, smoothed_1],
                velocities=[hand_velocity_0, hand_velocity_1]
            )
            combined = frame.copy()
            boxing.draw(combined, hands=[smoothed_0, smoothed_1])
            draw_text_bg(combined, "'m':Menu | 'r':Yeniden Baslat | 'u':Tam Ekran | 'q':Cikis", (w - 490, h - 15), 0.5, COL_HELP)

        else:
            combined = frame.copy()

        cv2.imshow("Screen Slicer", combined)

        # ── Key handling & Window close detection ─────────────────
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):
            break

        # Check if the user clicked the 'X' (close) button
        if cv2.getWindowProperty("Screen Slicer", cv2.WND_PROP_VISIBLE) < 1:
            break

        elif key == ord('c'):
            if mode == AppMode.AR_DRAW:
                canvas = np.zeros((h, w, 3), dtype=np.uint8)
                gestures.clear_drawing()
            elif mode == AppMode.SUN_IN_PALM:
                sun.cycle_color(1)

        elif key == ord('l') and mode == AppMode.AR_DRAW:
            gestures.enable_3d_placement = not gestures.enable_3d_placement

        elif key == ord('f'):
            if mode != AppMode.FRUIT_NINJA:
                mode = AppMode.FRUIT_NINJA
                ninja.reset()
            else:
                mode = AppMode.AR_DRAW

        elif key == ord('h'):
            if mode != AppMode.AIR_HOCKEY:
                mode = AppMode.AIR_HOCKEY
                hockey.reset()
            else:
                mode = AppMode.AR_DRAW

        elif key == ord('g'):
            if mode != AppMode.SUN_IN_PALM:
                mode = AppMode.SUN_IN_PALM
                sun.reset()
            else:
                mode = AppMode.AR_DRAW
                
        elif key == ord(' '):
            if mode == AppMode.SUN_IN_PALM:
                sun.cycle_color(0)

        elif key == ord('m'):
            mode = AppMode.MAIN_MENU
        elif key == ord('d'):
            if mode != AppMode.AR_DRAW:
                mode = AppMode.AR_DRAW
        elif key == ord('b'):
            if mode != AppMode.BASKETBALL:
                mode = AppMode.BASKETBALL
                basketball.reset()
        elif key == ord('a'):
            if mode != AppMode.ARCHERY:
                mode = AppMode.ARCHERY
                archery.reset()
                
        elif key == ord('1'):
            if mode == AppMode.BASKETBALL:
                basketball.set_moving_hoop(False)
            elif mode == AppMode.ARCHERY:
                archery.set_moving_target(False)
        elif key == ord('2'):
            if mode == AppMode.BASKETBALL:
                basketball.set_moving_hoop(True)
            elif mode == AppMode.ARCHERY:
                archery.set_moving_target(True)

        elif key == ord('r') and mode == AppMode.FRUIT_NINJA:
            ninja.reset()

        elif key == ord('r') and mode == AppMode.AIR_HOCKEY:
            hockey.reset()

        elif key == ord('r') and mode == AppMode.BOXING:
            boxing.reset()

        elif key in (ord('k'), ord('K')):
            if mode != AppMode.BOXING:
                mode = AppMode.BOXING
                boxing.reset()
            else:
                mode = AppMode.MAIN_MENU

        elif key in (ord('u'), ord('U')):
            is_fullscreen = not is_fullscreen
            if is_fullscreen:
                cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            else:
                cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

        # Colour selection
        elif key in (ord('1'), ord('2'), ord('3'), ord('4'), ord('5')):
            gestures.set_color(key - ord('1'))

        # Thickness
        elif key in (ord('+'), ord('=')):
            gestures.increase_thickness()
        elif key in (ord('-'), ord('_')):
            gestures.decrease_thickness()

        # Eraser
        elif key == ord('e') and mode == AppMode.AR_DRAW:
            gestures.toggle_eraser()

        # Particle brush
        elif key == ord('p') and mode == AppMode.AR_DRAW:
            gestures.toggle_particle()

        # Shape cycle
        elif key == ord('t') and mode == AppMode.AR_DRAW:
            geometry.cycle_shape()

        # Screenshot
        elif key == ord('s'):
            screenshot_count += 1
            fname = os.path.join(os.path.dirname(__file__),
                                 f"screenshot_{screenshot_count:03d}.png")
            cv2.imwrite(fname, combined)
            print(f"[INFO] Screenshot saved: {fname}")

        # Undo stroke
        elif key == ord('z') and mode == AppMode.AR_DRAW:
            gestures.undo()

        # Delete last shape
        elif key == ord('x') and mode == AppMode.AR_DRAW:
            gestures.undo_shape()

    tracker.release()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
