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


class Action(Enum):
    ACCELERATE = "Accelerate"
    STOP = "Stop"
    DIRECTION_LEFT = "Direction-Left"
    DIRECTION_RIGHT = "Direction-Right"
    DIRECTION_STRAIGHT = "Direction-Straight"


class HandGestureDetector:
    # Class-level MediaPipe hands object
    hands: Any = mp_hands.Hands()  # type: ignore[attr-defined]

    def __init__(self, handedness: Optional[Handedness] = None, hand_landmarks: Optional[HandLandmarkList] = None) -> None:
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

    def is_open(self, threshold: float = 0.06) -> bool:
        """Check if this hand instance is open."""
        if not self.__hand_landmarks:
            raise ValueError("Hand landmarks not set for this instance.")
        
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
        return all(d > threshold for d in distances)

    def hand_type(self) -> HandType:
        """Get this hand instance's type."""
        if not self.__handedness or not self.__hand_landmarks:
            return HandType.UNKNOWN
        if not self.is_hand_fully_visible():
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

    def get_action(self) -> Action:
        """Return the Action for this hand based on type and gesture."""
        hand_type = self.hand_type()
        if hand_type == HandType.LEFT:
            return Action.ACCELERATE if self.is_open() else Action.STOP
        elif hand_type == HandType.RIGHT:
            orientation = self.index_orientation()
            if orientation == IndexOrientation.LEFT:
                return Action.DIRECTION_LEFT
            elif orientation == IndexOrientation.RIGHT:
                return Action.DIRECTION_RIGHT
            else:
                return Action.DIRECTION_STRAIGHT
        else:
            raise ValueError("Cannot determine action for unknown hand type")

    @classmethod
    def draw_hand_info(cls, frame: Any, hand_landmarks: HandLandmarkList, label_position: int, action: Action) -> None:
        """Draw landmarks and action text on the frame.
        
        Args:
            frame: OpenCV image (cv2.typing.MatLike)
            hand_landmarks: MediaPipe hand landmarks
            label_position: X-coordinate for text label
            action: Action to display
        """
        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        cv2.putText(frame, action.value, (label_position, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, action.value, (label_position, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
