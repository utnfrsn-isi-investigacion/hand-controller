import logging
import mediapipe as mp
import math
from enum import Enum
from typing import Any, Optional, List

logger = logging.getLogger(__name__)

# MediaPipe solutions
mp_drawing = mp.solutions.drawing_utils  # type: ignore[attr-defined]
mp_hands = mp.solutions.hands  # type: ignore[attr-defined]

# Type aliases for MediaPipe types
HandLandmarkList = Any
Handedness = Any
NormalizedLandmark = Any


class HandType(Enum):
    LEFT = "Left"
    RIGHT = "Right"
    UNKNOWN = "Unknown"


class IndexOrientation(Enum):
    LEFT = "Left"
    RIGHT = "Right"
    STRAIGHT = "Straight"


class PalmOrientation(Enum):
    """Which way an open hand points, along the wrist-to-knuckles palm axis."""
    UP = "Up"
    DOWN = "Down"
    NEUTRAL = "Neutral"


class Hand:
    """Represents a single detected hand and its properties."""

    def __init__(self, handedness: Handedness, landmarks: HandLandmarkList,
                 open_threshold_ratio: float = 0.6, index_orientation_threshold: float = 0.05,
                 pitch_up_threshold_deg: float = 60.0, pitch_down_threshold_deg: float = 120.0):
        self.handedness = handedness
        self.landmarks = landmarks
        self._open_threshold_ratio = open_threshold_ratio
        self._index_orientation_threshold = index_orientation_threshold
        self._pitch_up_threshold_deg = pitch_up_threshold_deg
        self._pitch_down_threshold_deg = pitch_down_threshold_deg
        self._hand_size_cache: Optional[float] = None

    @staticmethod
    def _calculate_3d_distance(landmark1: NormalizedLandmark, landmark2: NormalizedLandmark) -> float:
        """Calculate 3D Euclidean distance between two landmarks."""
        return math.sqrt(
            (landmark2.x - landmark1.x) ** 2 +
            (landmark2.y - landmark1.y) ** 2 +
            (landmark2.z - landmark1.z) ** 2
        )

    def is_fully_visible(self, margin: float = 0.01) -> bool:
        """Check if all landmarks are within normalized image bounds."""
        if not self.landmarks:
            return False
        return all(margin <= lm.x <= 1 - margin and margin <= lm.y <= 1 - margin for lm in self.landmarks.landmark)

    def get_hand_type(self) -> HandType:
        """Get this hand's type (LEFT or RIGHT)."""
        if not self.handedness or not self.is_fully_visible():
            return HandType.UNKNOWN
        if self.handedness.classification[0].score < 0.7:
            return HandType.UNKNOWN
        label = self.handedness.classification[0].label
        return HandType[label.upper()]

    def is_open(self, threshold_ratio: Optional[float] = None) -> bool:
        """Check if the hand is open by measuring finger extension."""
        if threshold_ratio is None:
            threshold_ratio = self._open_threshold_ratio
        if not self.landmarks:
            return False

        if self._hand_size_cache is None:
            self._hand_size_cache = self._calculate_3d_distance(
                self.landmarks.landmark[mp_hands.HandLandmark.WRIST],
                self.landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
            )

        hand_size = self._hand_size_cache
        if hand_size < 1e-6:
            logger.warning("Hand size too small (%s), cannot determine if open.", hand_size)
            return False

        finger_tips = [
            mp_hands.HandLandmark.THUMB_TIP,
            mp_hands.HandLandmark.INDEX_FINGER_TIP,
            mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
            mp_hands.HandLandmark.RING_FINGER_TIP,
            mp_hands.HandLandmark.PINKY_TIP,
        ]
        finger_mcps = [
            mp_hands.HandLandmark.THUMB_CMC,
            mp_hands.HandLandmark.INDEX_FINGER_MCP,
            mp_hands.HandLandmark.MIDDLE_FINGER_MCP,
            mp_hands.HandLandmark.RING_FINGER_MCP,
            mp_hands.HandLandmark.PINKY_MCP,
        ]

        distances = [
            self._calculate_3d_distance(self.landmarks.landmark[tip], self.landmarks.landmark[mcp])
            for tip, mcp in zip(finger_tips, finger_mcps)
        ]

        normalized_distances = [d / hand_size for d in distances]
        return all(d > threshold_ratio for d in normalized_distances)

    def get_index_orientation(self, threshold: Optional[float] = None) -> IndexOrientation:
        """Get the orientation of the index finger.

        Assumes a mirrored (selfie-view) frame, where a larger x means
        further to the user's right.
        """
        if threshold is None:
            threshold = self._index_orientation_threshold
        if not self.landmarks:
            raise ValueError("Hand landmarks not available.")

        index_tip = self.landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
        index_base = self.landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
        diff = index_tip.x - index_base.x

        if diff > threshold:
            return IndexOrientation.RIGHT
        elif diff < -threshold:
            return IndexOrientation.LEFT
        else:
            return IndexOrientation.STRAIGHT

    def get_palm_pitch(self) -> float:
        """Angle of the palm axis away from straight up, in degrees (0..180).

        Measured on the wrist -> middle knuckle vector, the same one is_open()
        uses as its size baseline: 0 means the fingers point up, 90 means the
        hand is horizontal, 180 means the fingers point down.

        The horizontal component is taken as an absolute value, so the result
        is unaffected by the frame mirroring and by whether the hand is tilted
        inward or outward.
        """
        if not self.landmarks:
            raise ValueError("Hand landmarks not available.")

        wrist = self.landmarks.landmark[mp_hands.HandLandmark.WRIST]
        knuckle = self.landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
        # Image y grows downward, so negate it to make "up" positive.
        return math.degrees(math.atan2(abs(knuckle.x - wrist.x), -(knuckle.y - wrist.y)))

    def get_palm_orientation(self, up_threshold_deg: Optional[float] = None,
                             down_threshold_deg: Optional[float] = None) -> PalmOrientation:
        """Classify the palm axis as pointing UP, DOWN, or NEUTRAL.

        The NEUTRAL band between the two thresholds is deliberate: a hand
        rotating between up and down has to pass through it, which gives the
        handler a chance to stop the car before reversing it. How reliably it
        does so depends on the majority vote, not on this band alone -- see
        Handler._majority_action.
        """
        if up_threshold_deg is None:
            up_threshold_deg = self._pitch_up_threshold_deg
        if down_threshold_deg is None:
            down_threshold_deg = self._pitch_down_threshold_deg

        pitch = self.get_palm_pitch()
        if pitch <= up_threshold_deg:
            return PalmOrientation.UP
        if pitch >= down_threshold_deg:
            return PalmOrientation.DOWN
        return PalmOrientation.NEUTRAL


class HandProcessor:
    """Processes video frames to detect and analyze hand gestures."""

    def __init__(self, min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5,
                 max_hands: int = 2, open_threshold_ratio: float = 0.6,
                 index_orientation_threshold: float = 0.05,
                 pitch_up_threshold_deg: float = 60.0, pitch_down_threshold_deg: float = 120.0):
        self.hands_engine = mp_hands.Hands(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            max_num_hands=max_hands
        )
        self._open_threshold_ratio = open_threshold_ratio
        self._index_orientation_threshold = index_orientation_threshold
        self._pitch_up_threshold_deg = pitch_up_threshold_deg
        self._pitch_down_threshold_deg = pitch_down_threshold_deg

    def process_frame(self, rgb_frame: Any) -> List[Hand]:
        """Processes a single RGB frame to find hands."""
        results = self.hands_engine.process(rgb_frame)
        detected_hands: List[Hand] = []

        if results.multi_hand_landmarks:
            for handedness, landmarks in zip(results.multi_handedness, results.multi_hand_landmarks):
                detected_hands.append(Hand(
                    handedness=handedness,
                    landmarks=landmarks,
                    open_threshold_ratio=self._open_threshold_ratio,
                    index_orientation_threshold=self._index_orientation_threshold,
                    pitch_up_threshold_deg=self._pitch_up_threshold_deg,
                    pitch_down_threshold_deg=self._pitch_down_threshold_deg
                ))

        return detected_hands

    def close(self) -> None:
        """Releases the MediaPipe hands engine."""
        self.hands_engine.close()
