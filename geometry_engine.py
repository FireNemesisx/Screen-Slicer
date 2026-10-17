"""
geometry_engine.py — GeometryEngine Class (v3)

Supports multiple 3D shapes: Cube, Pyramid, Diamond.
Provides rotation matrices, perspective projection, and
auto-rotation for placed objects.
"""

import time
from enum import Enum, auto
from typing import List, Tuple

import cv2
import numpy as np


class ShapeType(Enum):
    """Available 3D shape types."""
    CUBE = auto()
    PYRAMID = auto()
    DIAMOND = auto()


# Shape definitions: (vertices, edges)
def _make_cube(s: float = 50.0):
    """Create cube vertices and edges."""
    verts = np.array([
        [-s, -s, -s], [+s, -s, -s], [-s, +s, -s], [+s, +s, -s],
        [-s, -s, +s], [+s, -s, +s], [-s, +s, +s], [+s, +s, +s],
    ], dtype=np.float64)
    edges = [
        (0, 1), (1, 3), (3, 2), (2, 0),
        (4, 5), (5, 7), (7, 6), (6, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    return verts, edges


def _make_pyramid(s: float = 50.0):
    """Create pyramid vertices and edges (square base + apex)."""
    verts = np.array([
        [-s, +s, -s], [+s, +s, -s], [+s, +s, +s], [-s, +s, +s],  # base
        [0, -s, 0],  # apex
    ], dtype=np.float64)
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # base
        (0, 4), (1, 4), (2, 4), (3, 4),  # sides
    ]
    return verts, edges


def _make_diamond(s: float = 50.0):
    """Create diamond/octahedron vertices and edges."""
    verts = np.array([
        [0, -s, 0],   # top
        [-s, 0, 0],   # left
        [0, 0, -s],   # front
        [+s, 0, 0],   # right
        [0, 0, +s],   # back
        [0, +s, 0],   # bottom
    ], dtype=np.float64)
    edges = [
        (0, 1), (0, 2), (0, 3), (0, 4),  # top to middle
        (5, 1), (5, 2), (5, 3), (5, 4),  # bottom to middle
        (1, 2), (2, 3), (3, 4), (4, 1),  # middle ring
    ]
    return verts, edges


SHAPE_BUILDERS = {
    ShapeType.CUBE: _make_cube,
    ShapeType.PYRAMID: _make_pyramid,
    ShapeType.DIAMOND: _make_diamond,
}

SHAPE_NAMES = {
    ShapeType.CUBE: "Cube",
    ShapeType.PYRAMID: "Pyramid",
    ShapeType.DIAMOND: "Diamond",
}


class GeometryEngine:
    """Manages 3D shape geometry, rotation, and perspective projection.

    Supports cube, pyramid, and diamond shapes with auto-rotation
    for placed objects.

    Attributes:
        current_shape: Active ShapeType.
        focal_length: Focal length for projection.
        z_offset: Z translation before projection.
    """

    def __init__(self, size: float = 50.0, focal_length: float = 500.0,
                 z_offset: float = 300.0) -> None:
        """Initialise the GeometryEngine.

        Args:
            size: Half-extent of shapes.
            focal_length: Focal length for pinhole projection.
            z_offset: Z offset to prevent div-by-zero.
        """
        self.size = size
        self.focal_length = focal_length
        self.z_offset = z_offset
        self.current_shape = ShapeType.CUBE
        self._shapes = {st: builder(size) for st, builder in SHAPE_BUILDERS.items()}
        self._start_time = time.time()

    # ------------------------------------------------------------------
    # Shape selection
    # ------------------------------------------------------------------

    def cycle_shape(self) -> ShapeType:
        """Cycle to the next shape type.

        Returns:
            The new active ShapeType.
        """
        shapes = list(ShapeType)
        idx = shapes.index(self.current_shape)
        self.current_shape = shapes[(idx + 1) % len(shapes)]
        return self.current_shape

    def get_shape_name(self) -> str:
        """Return human-readable name of current shape."""
        return SHAPE_NAMES[self.current_shape]

    # ------------------------------------------------------------------
    # Rotation matrices
    # ------------------------------------------------------------------

    @staticmethod
    def _rotation_x(angle: float) -> np.ndarray:
        """3x3 rotation matrix about X axis."""
        c, s = np.cos(angle), np.sin(angle)
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

    @staticmethod
    def _rotation_y(angle: float) -> np.ndarray:
        """3x3 rotation matrix about Y axis."""
        c, s = np.cos(angle), np.sin(angle)
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

    @staticmethod
    def _rotation_z(angle: float) -> np.ndarray:
        """3x3 rotation matrix about Z axis."""
        c, s = np.cos(angle), np.sin(angle)
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

    # ------------------------------------------------------------------
    # Geometry operations
    # ------------------------------------------------------------------

    def get_rotated_shape(self, roll: float, pitch: float, yaw: float,
                          shape_type: ShapeType = None) -> np.ndarray:
        """Apply rotation to shape vertices.

        Args:
            roll: Rotation about Z in radians.
            pitch: Rotation about X in radians.
            yaw: Rotation about Y in radians.
            shape_type: Which shape (defaults to current_shape).

        Returns:
            Rotated vertices array.
        """
        st = shape_type or self.current_shape
        verts = self._shapes[st][0]
        rot = self._rotation_y(yaw) @ self._rotation_x(pitch) @ self._rotation_z(roll)
        return (rot @ verts.T).T

    def get_auto_rotated_shape(self, offset: float = 0.0,
                               shape_type: ShapeType = None) -> np.ndarray:
        """Get shape with automatic time-based rotation.

        Args:
            offset: Additional rotation offset in radians.
            shape_type: Which shape.

        Returns:
            Rotated vertices array.
        """
        t = time.time() - self._start_time + offset
        roll = t * 0.5
        pitch = t * 0.3
        yaw = t * 0.7
        return self.get_rotated_shape(roll, pitch, yaw, shape_type)

    def project_to_2d(self, vertices_3d: np.ndarray,
                      center_x: int, center_y: int) -> List[Tuple[int, int]]:
        """Perspective-project 3D vertices onto 2D screen.

        Args:
            vertices_3d: (N, 3) array of 3D points.
            center_x: Screen X center.
            center_y: Screen Y center.

        Returns:
            List of (x, y) pixel coordinates.
        """
        projected = []
        for v in vertices_3d:
            z = max(v[2] + self.z_offset, 1.0)
            px = int(self.focal_length * v[0] / z) + center_x
            py = int(self.focal_length * v[1] / z) + center_y
            projected.append((px, py))
        return projected

    def get_edges(self, shape_type: ShapeType = None) -> List[Tuple[int, int]]:
        """Return edge index pairs for a shape.

        Args:
            shape_type: Which shape (defaults to current).

        Returns:
            List of (i, j) edge pairs.
        """
        st = shape_type or self.current_shape
        return self._shapes[st][1]

    def draw_wireframe(self, frame: np.ndarray,
                       projected_pts: List[Tuple[int, int]],
                       edges: List[Tuple[int, int]],
                       color: Tuple[int, int, int] = (255, 255, 0),
                       thickness: int = 2) -> None:
        """Render wireframe onto an image.

        Args:
            frame: BGR image (modified in place).
            projected_pts: 2D vertex positions.
            edges: Edge index pairs.
            color: BGR line colour.
            thickness: Line thickness.
        """
        for i, j in edges:
            if i < len(projected_pts) and j < len(projected_pts):
                cv2.line(frame, projected_pts[i], projected_pts[j],
                         color, thickness, cv2.LINE_AA)
