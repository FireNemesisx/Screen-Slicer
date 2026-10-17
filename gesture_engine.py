"""
gesture_engine.py — GestureEngine Class (v3)

State machine with:
    IDLE         — cursor shown
    DRAWING      — index finger up, records stroke
    CUBE_PREVIEW — thumb+index pinch, cube follows finger
    ERASER       — eraser mode, removes nearby strokes
    ZOOM         — two hands, pinch-zoom canvas
    PARTICLE     — particle brush mode
"""

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

import numpy as np


class GestureState(Enum):
    """Possible states of the gesture state machine."""
    IDLE = auto()
    DRAWING = auto()
    CUBE_PREVIEW = auto()
    ERASER = auto()
    ZOOM = auto()
    PARTICLE = auto()


# Colour palette for drawing
COLOR_PALETTE = [
    (0, 255, 128),    # 1: Green
    (60, 60, 255),    # 2: Red
    (255, 180, 0),    # 3: Blue
    (0, 230, 255),    # 4: Yellow
    (200, 50, 200),   # 5: Purple
]

COLOR_NAMES = ["Green", "Red", "Blue", "Yellow", "Purple"]


@dataclass
class PlacedShape:
    """A 3D shape placed permanently on the canvas.

    Attributes:
        x, y: Screen position.
        shape_type: Which shape (from ShapeType enum value).
        color: BGR wireframe colour.
        rotation_offset: Unique rotation phase offset.
        place_time: When it was placed (for animation).
    """
    x: int
    y: int
    shape_type: int  # ShapeType enum value
    color: Tuple[int, int, int]
    rotation_offset: float
    place_time: float = 0.0


@dataclass
class BrushParticle:
    """A particle emitted by the particle brush.

    Attributes:
        x, y: Position.
        vx, vy: Velocity.
        color: BGR colour.
        life: Remaining frames.
        radius: Size.
    """
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    life: int = 30
    radius: int = 4


class GestureEngine:
    """Evaluates hand landmarks and manages gesture state, drawing,
    placed shapes, colours, thickness, undo, eraser, and particles.

    Attributes:
        state: Current GestureState.
        drawing_points: Active stroke.
        all_drawings: Completed strokes with colour and thickness.
        placed_shapes: List of permanently placed 3D shapes.
        current_color_idx: Index into COLOR_PALETTE.
        line_thickness: Current stroke thickness (1-8).
        eraser_mode: Whether eraser is active.
        particle_mode: Whether particle brush is active.
        particles: Active brush particles.
        zoom_scale: Canvas zoom factor.
        pan_offset: Canvas pan (dx, dy).
    """

    MIN_DRAW_DIST = 5
    ERASER_RADIUS = 30

    def __init__(self, pinch_threshold: float = 40.0) -> None:
        """Initialise the GestureEngine.

        Args:
            pinch_threshold: Thumb+index pinch distance threshold.
        """
        self.state = GestureState.IDLE
        self.pinch_threshold = pinch_threshold

        # Drawing
        self.drawing_points: List[Tuple[int, int]] = []
        # Each entry: {"points": [...], "color": (b,g,r), "thickness": int}
        self.all_drawings: List[Dict] = []
        self._undo_stack: List[Dict] = []

        # Colours & thickness
        self.current_color_idx: int = 0
        self.line_thickness: int = 2

        # Modes
        self.eraser_mode: bool = False
        self.particle_mode: bool = False

        # Placed shapes
        self.placed_shapes: List[PlacedShape] = []
        self._was_pinching: bool = False
        self.enable_3d_placement: bool = False

        # Particles
        self.particles: List[BrushParticle] = []

        # Zoom
        self.zoom_scale: float = 1.0
        self.pan_offset: List[float] = [0.0, 0.0]
        self._prev_two_hand_dist: Optional[float] = None
        self._prev_two_hand_center: Optional[Tuple[float, float]] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_color(self) -> Tuple[int, int, int]:
        """Get current drawing colour."""
        return COLOR_PALETTE[self.current_color_idx]

    @property
    def current_color_name(self) -> str:
        """Get current colour name."""
        return COLOR_NAMES[self.current_color_idx]

    # ------------------------------------------------------------------
    # Colour / Thickness / Mode controls
    # ------------------------------------------------------------------

    def set_color(self, idx: int) -> None:
        """Set drawing colour by index (0-4)."""
        self.current_color_idx = max(0, min(idx, len(COLOR_PALETTE) - 1))

    def increase_thickness(self) -> int:
        """Increase line thickness (max 8)."""
        self.line_thickness = min(8, self.line_thickness + 1)
        return self.line_thickness

    def decrease_thickness(self) -> int:
        """Decrease line thickness (min 1)."""
        self.line_thickness = max(1, self.line_thickness - 1)
        return self.line_thickness

    def toggle_eraser(self) -> bool:
        """Toggle eraser mode on/off."""
        self.eraser_mode = not self.eraser_mode
        if self.eraser_mode:
            self.particle_mode = False
        return self.eraser_mode

    def toggle_particle(self) -> bool:
        """Toggle particle brush mode on/off."""
        self.particle_mode = not self.particle_mode
        if self.particle_mode:
            self.eraser_mode = False
        return self.particle_mode

    # ------------------------------------------------------------------
    # Undo
    # ------------------------------------------------------------------

    def undo(self) -> bool:
        """Undo the last drawing stroke.

        Returns:
            True if something was undone.
        """
        if self.all_drawings:
            removed = self.all_drawings.pop()
            self._undo_stack.append(removed)
            return True
        return False

    def undo_shape(self) -> bool:
        """Remove the last placed shape.

        Returns:
            True if a shape was removed.
        """
        if self.placed_shapes:
            self.placed_shapes.pop()
            return True
        return False

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    def update(
        self,
        num_hands: int,
        index_only_up_0: bool,
        thumb_up_0: bool,
        index_up_0: bool,
        thumb_tip_0: Optional[Tuple[int, int]],
        index_tip_0: Optional[Tuple[int, int]],
        smoothed_tip_0: Optional[Tuple[int, int]],
        index_tip_1: Optional[Tuple[int, int]],
        current_shape_type=None,
    ) -> GestureState:
        """Evaluate gesture and transition state.

        Args:
            num_hands: Number of hands detected.
            index_only_up_0: Only index finger up on hand 0.
            thumb_up_0: Thumb extended on hand 0.
            index_up_0: Index finger up on hand 0.
            thumb_tip_0: Thumb tip of hand 0.
            index_tip_0: Index tip of hand 0.
            smoothed_tip_0: Smoothed index tip of hand 0.
            index_tip_1: Index tip of hand 1.
            current_shape_type: ShapeType enum value for placing.

        Returns:
            Updated GestureState.
        """
        # Update particles
        self._update_particles()

        # --- Two hands → ZOOM ---
        if num_hands >= 2 and index_tip_0 is not None and index_tip_1 is not None:
            self._handle_zoom(index_tip_0, index_tip_1)
            if self.state == GestureState.DRAWING and self.drawing_points:
                self._commit_stroke()
            self._was_pinching = False
            self.state = GestureState.ZOOM
            return self.state

        self._prev_two_hand_dist = None
        self._prev_two_hand_center = None

        # --- No hands ---
        if num_hands == 0 or index_tip_0 is None:
            if self.state == GestureState.DRAWING and self.drawing_points:
                self._commit_stroke()
            self._was_pinching = False
            self.state = GestureState.IDLE
            return self.state

        # --- Pinch detection ---
        thumb_idx_dist = float('inf')
        is_pinching = False
        if self.enable_3d_placement and thumb_tip_0 is not None and index_tip_0 is not None:
            thumb_idx_dist = self._euclidean(thumb_tip_0, index_tip_0)
            is_pinching = thumb_idx_dist < self.pinch_threshold and not index_only_up_0

        # Cube placement: pinch released → place shape
        if self._was_pinching and not is_pinching and smoothed_tip_0 is not None:
            if current_shape_type is not None:
                self.placed_shapes.append(PlacedShape(
                    x=smoothed_tip_0[0],
                    y=smoothed_tip_0[1],
                    shape_type=current_shape_type,
                    color=self.current_color,
                    rotation_offset=random.uniform(0, 6.28),
                    place_time=time.time(),
                ))
        self._was_pinching = is_pinching

        # Pinching → CUBE_PREVIEW
        if is_pinching:
            if self.state == GestureState.DRAWING and self.drawing_points:
                self._commit_stroke()
            self.state = GestureState.CUBE_PREVIEW
            return self.state

        # --- Eraser mode ---
        if self.eraser_mode and index_only_up_0 and smoothed_tip_0 is not None:
            self._erase_near(smoothed_tip_0)
            self.state = GestureState.ERASER
            return self.state

        # --- Particle brush mode ---
        if self.particle_mode and index_only_up_0 and smoothed_tip_0 is not None:
            self._emit_particles(smoothed_tip_0)
            self.state = GestureState.PARTICLE
            return self.state

        # --- Drawing ---
        if index_only_up_0:
            self.state = GestureState.DRAWING
            if smoothed_tip_0 is not None:
                self._add_draw_point(smoothed_tip_0)
            return self.state

        # Default → IDLE
        if self.state == GestureState.DRAWING and self.drawing_points:
            self._commit_stroke()
        self.state = GestureState.IDLE
        return self.state

    # ------------------------------------------------------------------
    # Getters
    # ------------------------------------------------------------------

    def get_drawing_points(self) -> List[Tuple[int, int]]:
        """Return active stroke points."""
        return self.drawing_points

    def get_all_drawings(self) -> List[Dict]:
        """Return all completed strokes with metadata."""
        return self.all_drawings

    def clear_drawing(self) -> None:
        """Erase all drawings, shapes, particles and reset zoom."""
        self.drawing_points.clear()
        self.all_drawings.clear()
        self.placed_shapes.clear()
        self.particles.clear()
        self._undo_stack.clear()
        self.zoom_scale = 1.0
        self.pan_offset = [0.0, 0.0]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _add_draw_point(self, pt: Tuple[int, int]) -> None:
        """Add point with min distance filter."""
        if self.drawing_points:
            if self._euclidean(self.drawing_points[-1], pt) < self.MIN_DRAW_DIST:
                return
        self.drawing_points.append(pt)

    def _commit_stroke(self) -> None:
        """Save stroke with colour and thickness metadata."""
        if len(self.drawing_points) > 1:
            self.all_drawings.append({
                "points": list(self.drawing_points),
                "color": self.current_color,
                "thickness": self.line_thickness,
            })
        self.drawing_points.clear()

    def _erase_near(self, pos: Tuple[int, int]) -> None:
        """Remove strokes near the given position.

        Args:
            pos: Eraser center position.
        """
        remaining = []
        for stroke in self.all_drawings:
            keep = True
            for pt in stroke["points"]:
                if self._euclidean(pt, pos) < self.ERASER_RADIUS:
                    keep = False
                    break
            if keep:
                remaining.append(stroke)
        self.all_drawings = remaining

    def _emit_particles(self, pos: Tuple[int, int]) -> None:
        """Emit particles at the brush position.

        Args:
            pos: Emission center.
        """
        for _ in range(3):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 4)
            col = self.current_color
            cr = max(0, min(255, col[0] + random.randint(-30, 30)))
            cg = max(0, min(255, col[1] + random.randint(-30, 30)))
            cb = max(0, min(255, col[2] + random.randint(-30, 30)))
            self.particles.append(BrushParticle(
                x=pos[0], y=pos[1],
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=(cr, cg, cb),
                life=random.randint(20, 40),
                radius=random.randint(2, 5),
            ))

    def _update_particles(self) -> None:
        """Advance particle physics and remove dead ones."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # slight gravity
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _handle_zoom(self, tip0: Tuple[int, int], tip1: Tuple[int, int]) -> None:
        """Update zoom/pan from two-hand distance change."""
        dist = self._euclidean(tip0, tip1)
        center = ((tip0[0] + tip1[0]) / 2.0, (tip0[1] + tip1[1]) / 2.0)

        if self._prev_two_hand_dist is not None:
            ratio = dist / max(self._prev_two_hand_dist, 1.0)
            self.zoom_scale *= ratio
            self.zoom_scale = max(0.3, min(self.zoom_scale, 5.0))

        if self._prev_two_hand_center is not None:
            dx = center[0] - self._prev_two_hand_center[0]
            dy = center[1] - self._prev_two_hand_center[1]
            self.pan_offset[0] += dx
            self.pan_offset[1] += dy

        self._prev_two_hand_dist = dist
        self._prev_two_hand_center = center

    @staticmethod
    def _euclidean(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """Euclidean distance between two 2D points."""
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])
