"""
hand_tracker.py — HandTracker Class (v2 — Multi-Hand)

Wraps MediaPipe Tasks Vision HandLandmarker API to provide real-time
tracking of up to 2 hands with coordinate smoothing, finger state
detection, and palm orientation extraction.

Requires 'hand_landmarker.task' model file in the working directory.
"""

import math
import os
from collections import deque
from typing import Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision


class HandTracker:
    """Tracks up to 2 hands using MediaPipe HandLandmarker (Tasks API).

    Provides smoothed landmark coordinates, finger-up detection,
    and palm orientation for each detected hand.

    Attributes:
        landmarker: MediaPipe HandLandmarker instance.
        num_hands_detected: Number of hands found in the latest frame.
        hands_landmarks_px: List of landmark lists, one per detected hand.
    """

    # Landmark IDs
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20

    # Finger tip/pip pairs for "finger up" detection
    FINGER_TIPS = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
    FINGER_PIPS = [INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]

    # Hand skeleton connections
    HAND_CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (0, 9), (9, 10), (10, 11), (11, 12),
        (0, 13), (13, 14), (14, 15), (15, 16),
        (0, 17), (17, 18), (18, 19), (19, 20),
        (5, 9), (9, 13), (13, 17),
    ]

    def __init__(self, smooth_window: int = 7, num_hands: int = 2) -> None:
        """Initialise the HandTracker.

        Args:
            smooth_window: Window size for Moving Average Filter.
            num_hands: Maximum number of hands to detect (1 or 2).
        """
        model_path = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = mp_vision.HandLandmarker.create_from_options(options)

        self._smooth_window = smooth_window
        self._smooth_buffers: Dict[int, deque] = {
            0: deque(maxlen=smooth_window),
            1: deque(maxlen=smooth_window),
        }
        self.hands_landmarks_px: List[List[Tuple[int, int]]] = []
        self.num_hands_detected: int = 0
        self.frame_w: int = 0
        self.frame_h: int = 0
        self._frame_timestamp_ms: int = 0

    # ------------------------------------------------------------------
    # Core detection
    # ------------------------------------------------------------------

    def process_frame(self, frame: np.ndarray) -> int:
        """Run hand detection on a BGR frame.

        Args:
            frame: BGR image from OpenCV.

        Returns:
            Number of hands detected (0, 1, or 2).
        """
        self.frame_h, self.frame_w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._frame_timestamp_ms += 33

        result = self.landmarker.detect_for_video(mp_image, self._frame_timestamp_ms)

        self.hands_landmarks_px = []
        if result.hand_landmarks:
            for hand in result.hand_landmarks:
                pixels = [
                    (int(lm.x * self.frame_w), int(lm.y * self.frame_h))
                    for lm in hand
                ]
                self.hands_landmarks_px.append(pixels)

        self.num_hands_detected = len(self.hands_landmarks_px)

        # Clear smooth buffers for hands that disappeared
        for hid in range(2):
            if hid >= self.num_hands_detected:
                self._smooth_buffers[hid].clear()

        return self.num_hands_detected

    # ------------------------------------------------------------------
    # Landmark access
    # ------------------------------------------------------------------

    def get_landmark(self, landmark_id: int, hand_id: int = 0) -> Optional[Tuple[int, int]]:
        """Return raw pixel coords for a landmark on a specific hand.

        Args:
            landmark_id: MediaPipe landmark index (0-20).
            hand_id: Which hand (0 or 1).

        Returns:
            (x, y) tuple or None.
        """
        if hand_id >= self.num_hands_detected:
            return None
        if landmark_id >= len(self.hands_landmarks_px[hand_id]):
            return None
        return self.hands_landmarks_px[hand_id][landmark_id]

    def get_smoothed_index_tip(self, hand_id: int = 0) -> Optional[Tuple[int, int]]:
        """Return Moving-Average-filtered index tip position.

        Args:
            hand_id: Which hand (0 or 1).

        Returns:
            Smoothed (x, y) or None.
        """
        raw = self.get_landmark(self.INDEX_TIP, hand_id)
        if raw is None:
            self._smooth_buffers[hand_id].clear()
            return None

        buf = self._smooth_buffers[hand_id]
        buf.append(raw)
        avg_x = int(sum(p[0] for p in buf) / len(buf))
        avg_y = int(sum(p[1] for p in buf) / len(buf))
        return avg_x, avg_y

    # ------------------------------------------------------------------
    # Finger state detection
    # ------------------------------------------------------------------

    def is_finger_up(self, finger_idx: int, hand_id: int = 0) -> bool:
        """Check if a finger is extended (tip above pip in y).

        Args:
            finger_idx: 0=index, 1=middle, 2=ring, 3=pinky.
            hand_id: Which hand.

        Returns:
            True if the finger tip is above (lower y) its PIP joint.
        """
        if hand_id >= self.num_hands_detected:
            return False
        tip = self.get_landmark(self.FINGER_TIPS[finger_idx], hand_id)
        pip = self.get_landmark(self.FINGER_PIPS[finger_idx], hand_id)
        if tip is None or pip is None:
            return False
        return tip[1] < pip[1]  # y increases downward

    def is_thumb_up(self, hand_id: int = 0) -> bool:
        """Check if thumb is extended outward.

        Args:
            hand_id: Which hand.

        Returns:
            True if thumb tip is far from palm center.
        """
        if hand_id >= self.num_hands_detected:
            return False
        thumb_tip = self.get_landmark(self.THUMB_TIP, hand_id)
        thumb_ip = self.get_landmark(self.THUMB_IP, hand_id)
        wrist = self.get_landmark(self.WRIST, hand_id)
        if thumb_tip is None or thumb_ip is None or wrist is None:
            return False
        # Thumb is "up" if tip is farther from wrist than IP joint
        d_tip = math.hypot(thumb_tip[0] - wrist[0], thumb_tip[1] - wrist[1])
        d_ip = math.hypot(thumb_ip[0] - wrist[0], thumb_ip[1] - wrist[1])
        return d_tip > d_ip

    def is_index_only_up(self, hand_id: int = 0) -> bool:
        """Check if only the index finger is raised.

        Args:
            hand_id: Which hand.

        Returns:
            True if index up AND middle, ring, pinky down.
        """
        if hand_id >= self.num_hands_detected:
            return False
        return (
            self.is_finger_up(0, hand_id)       # index up
            and not self.is_finger_up(1, hand_id)  # middle down
            and not self.is_finger_up(2, hand_id)  # ring down
            and not self.is_finger_up(3, hand_id)  # pinky down
        )

    def get_hand_velocity(self, hand_id: int = 0) -> float:
        """Estimate hand movement speed from smooth buffer.

        Args:
            hand_id: Which hand.

        Returns:
            Pixels per frame movement speed, or 0.
        """
        buf = self._smooth_buffers.get(hand_id)
        if buf is None or len(buf) < 2:
            return 0.0
        p1 = buf[-2]
        p2 = buf[-1]
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    # ------------------------------------------------------------------
    # Palm orientation
    # ------------------------------------------------------------------

    def get_palm_orientation(self, hand_id: int = 0) -> Optional[Tuple[float, float, float]]:
        """Compute roll, pitch, yaw from the palm plane.

        Args:
            hand_id: Which hand.

        Returns:
            (roll, pitch, yaw) in radians, or None.
        """
        p0 = self.get_landmark(self.WRIST, hand_id)
        p5 = self.get_landmark(self.INDEX_MCP, hand_id)
        p17 = self.get_landmark(self.PINKY_MCP, hand_id)
        if p0 is None or p5 is None or p17 is None:
            return None

        v1 = np.array([p5[0] - p0[0], p5[1] - p0[1], 0.0])
        v2 = np.array([p17[0] - p0[0], p17[1] - p0[1], 0.0])

        normal = np.cross(v1, v2)
        norm_len = np.linalg.norm(normal)
        if norm_len < 1e-6:
            return 0.0, 0.0, 0.0
        normal /= norm_len

        roll = math.atan2(v1[1], v1[0])
        pitch = math.atan2(normal[1], normal[2]) if abs(normal[2]) > 1e-6 else 0.0
        yaw = math.atan2(p5[1] - p0[1], p5[0] - p0[0])
        return roll, pitch, yaw

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def draw_landmarks(self, frame: np.ndarray) -> None:
        """Draw all detected hand landmarks on the frame.

        Args:
            frame: BGR image (modified in place).
        """
        colors = [(0, 255, 128), (255, 128, 0)]  # green, orange
        for hid, landmarks in enumerate(self.hands_landmarks_px):
            col = colors[hid % 2]
            for i, j in self.HAND_CONNECTIONS:
                if i < len(landmarks) and j < len(landmarks):
                    cv2.line(frame, landmarks[i], landmarks[j], col, 1, cv2.LINE_AA)
            for pt in landmarks:
                cv2.circle(frame, pt, 3, col, cv2.FILLED, cv2.LINE_AA)

    def release(self) -> None:
        """Release MediaPipe resources."""
        self.landmarker.close()
