import cv2
import mediapipe as mp
import math
from enum import Enum
from typing import Any, Optional, List

# MediaPipe solutions (Pylance may show warnings but these work at runtime)
mp_drawing = mp.solutions.drawing_utils  # type: ignore[attr-defined]
mp_hands = mp.solutions.hands  # type: ignore[attr-defined]

# Type aliases for MediaPipe types
# These are runtime types that Pylance can't fully resolve, so we use Any with documentation
HandLandmarkList = Any  # mediapipe.framework.formats.landmark_pb2.NormalizedLandmarkList
Handedness = Any  # mediapipe.framework.formats.classification_pb2.ClassificationList
NormalizedLandmark = Any  # mediapipe.framework.formats.landmark_pb2.NormalizedLandmark


class HandType(Enum):
    LEFT = "Left"
    RIGHT = "Right"
    UNKNOWN = "Unknown"


class IndexOrientation(Enum):
    LEFT = "Left"
    RIGHT = "Right"
    STRAIGHT = "Straight"


class HandGestureDetector:
    # Class-level MediaPipe hands object
    hands: Any = mp_hands.Hands()  # type: ignore[attr-defined]

    def __init__(self, handedness: Optional[Handedness] = None,
                 hand_landmarks: Optional[HandLandmarkList] = None) -> None:
        """Optional instance initialization with handedness and landmarks."""
        self.__handedness: Optional[Handedness] = handedness
        self.__hand_landmarks: Optional[HandLandmarkList] = hand_landmarks

    def reload(self, handedness: Handedness, hand_landmarks: HandLandmarkList) -> None:
        """Reload instance data."""
        self.__handedness = handedness
        self.__hand_landmarks = hand_landmarks

    @staticmethod
    def calculate_3d_distance(landmark1: NormalizedLandmark, landmark2: NormalizedLandmark) -> float:
        """Calculate 3D Euclidean distance between two landmarks."""
        return math.sqrt(
            (landmark2.x - landmark1.x) ** 2 +
            (landmark2.y - landmark1.y) ** 2 +
            (landmark2.z - landmark1.z) ** 2
        )

    def is_hand_fully_visible(self, margin: float = 0.01) -> bool:
        """Check if all landmarks of this hand instance are within normalized image bounds."""
        if not self.__hand_landmarks:
            return False
        return all(margin <= l.x <= 1 - margin and margin <= l.y <= 1 - margin for l in self.__hand_landmarks.landmark)

    def is_open(self, threshold_ratio: float = 0.6) -> bool:
        """Check if hand is open by measuring normalized finger extension.
        
        Measures distance from each fingertip to its base, normalizes by hand size
        (wrist to middle finger MCP), and checks if all fingers exceed the threshold.
        This approach is independent of hand size and camera distance.
        
        Args:
            threshold_ratio: Minimum ratio for extended finger (default 0.6 = 60%).
                           Lower values (0.4-0.5) are more sensitive.
        
        Returns:
            True if all five fingers are extended above threshold, False otherwise.
        """
        if not self.__hand_landmarks:
            raise ValueError("Hand landmarks not set for this instance.")

        # Calculate hand size reference (wrist to middle finger base)
        hand_size = self.calculate_3d_distance(
            self.__hand_landmarks.landmark[mp_hands.HandLandmark.WRIST],
            self.__hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
        )
        
        if hand_size == 0:  # Safety check
            return False

        distances: List[float] = [
            self.calculate_3d_distance(self.__hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP],
                                       self.__hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_CMC]),
            self.calculate_3d_distance(self.__hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP],
                                       self.__hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]),
            self.calculate_3d_distance(self.__hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP],
                                       self.__hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]),
            self.calculate_3d_distance(self.__hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP],
                                       self.__hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP]),
            self.calculate_3d_distance(self.__hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP],
                                       self.__hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP]),
        ]
        
        # Normalize distances by hand size
        normalized_distances = [d / hand_size for d in distances]
        
        return all(d > threshold_ratio for d in normalized_distances)

    def hand_type(self) -> HandType:
        """Get this hand instance's type."""
        if not self.__handedness or not self.__hand_landmarks:
            return HandType.UNKNOWN
        if not self.is_hand_fully_visible():
            return HandType.UNKNOWN
        if self.__handedness.classification[0].score < 0.7:
            return HandType.UNKNOWN
        label = self.__handedness.classification[0].label
        return HandType.LEFT if label == 'Left' else HandType.RIGHT

    def index_orientation(self, threshold: float = 0.05) -> IndexOrientation:
        """Get index finger orientation of this hand instance."""
        if not self.__hand_landmarks:
            raise ValueError("Hand landmarks not set for this instance.")

        index_tip: NormalizedLandmark = self.__hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
        index_base: NormalizedLandmark = self.__hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
        diff = index_tip.x - index_base.x
        if diff > threshold:
            return IndexOrientation.LEFT
        elif diff < -threshold:
            return IndexOrientation.RIGHT
        else:
            return IndexOrientation.STRAIGHT

    def draw_hand_info(self, cv_frame: Any, action: Enum) -> None:
        """Draw landmarks and action text on the frame.
        
        Args:
            cv_frame: OpenCV image (cv2.typing.MatLike)
            action: Action to display
        """
        if self.hand_type() == HandType.UNKNOWN:
            return
        elif self.hand_type() == HandType.LEFT:
            cv2.putText(cv_frame, action.name, (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        else:
            cv2.putText(cv_frame, action.name, (350, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        mp_drawing.draw_landmarks(cv_frame, self.__hand_landmarks, mp_hands.HAND_CONNECTIONS)
