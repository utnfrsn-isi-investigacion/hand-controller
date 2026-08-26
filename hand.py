import logging
import mediapipe as mp
import math
from dataclasses import dataclass, field
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


@dataclass
class HandDiagnostics:
    """Every intermediate value behind one detection's gesture classification.

    Produced by Hand.diagnostics() for debug mode only (see debug.py): the
    predicates themselves return plain booleans, so when a gesture never
    fires this is what shows which threshold it missed and by how much.
    """
    label: str                                  # raw MediaPipe handedness label
    score: float                                # handedness confidence
    hand_type: HandType                         # what the pipeline actually uses
    unknown_reason: str                         # why hand_type is UNKNOWN, else ""
    out_of_frame: List[int] = field(default_factory=list)     # clipped landmark indices
    finger_ratios: List[float] = field(default_factory=list)  # per Hand.FINGER_NAMES
    open_threshold: float = 0.0
    is_open: bool = False
    index_offset: float = 0.0
    index_threshold: float = 0.0
    index_orientation: IndexOrientation = IndexOrientation.STRAIGHT


class Hand:
    """Represents a single detected hand and its properties."""

    # Below this MediaPipe handedness score the hand is treated as UNKNOWN
    _MIN_HANDEDNESS_SCORE = 0.7

    # Fingers checked by the open-hand test: name, tip and knuckle landmark,
    # all in the same order so debug output can label each ratio.
    FINGER_NAMES = ("thumb", "index", "middle", "ring", "pinky")
    _FINGER_TIPS = (
        mp_hands.HandLandmark.THUMB_TIP,
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP,
    )
    _FINGER_MCPS = (
        mp_hands.HandLandmark.THUMB_CMC,
        mp_hands.HandLandmark.INDEX_FINGER_MCP,
        mp_hands.HandLandmark.MIDDLE_FINGER_MCP,
        mp_hands.HandLandmark.RING_FINGER_MCP,
        mp_hands.HandLandmark.PINKY_MCP,
    )

    def __init__(self, handedness: Handedness, landmarks: HandLandmarkList,
                 open_threshold_ratio: float = 0.6, index_orientation_threshold: float = 0.05):
        self.handedness = handedness
        self.landmarks = landmarks
        self._open_threshold_ratio = open_threshold_ratio
        self._index_orientation_threshold = index_orientation_threshold
        self._hand_size_cache: Optional[float] = None

    @staticmethod
    def _calculate_3d_distance(landmark1: NormalizedLandmark, landmark2: NormalizedLandmark) -> float:
        """Calculate 3D Euclidean distance between two landmarks."""
        return math.sqrt(
            (landmark2.x - landmark1.x) ** 2 +
            (landmark2.y - landmark1.y) ** 2 +
            (landmark2.z - landmark1.z) ** 2
        )

    @staticmethod
    def _in_bounds(landmark: NormalizedLandmark, margin: float) -> bool:
        """Whether a landmark sits inside the frame, minus a border margin."""
        return margin <= landmark.x <= 1 - margin and margin <= landmark.y <= 1 - margin

    def is_fully_visible(self, margin: float = 0.01) -> bool:
        """Check if all landmarks are within normalized image bounds."""
        if not self.landmarks:
            return False
        return all(self._in_bounds(lm, margin) for lm in self.landmarks.landmark)

    def landmarks_out_of_frame(self, margin: float = 0.01) -> List[int]:
        """Indices of the landmarks that make is_fully_visible() fail.

        Diagnostics only: is_fully_visible() short-circuits on the first bad
        landmark, this returns all of them so debug output can name the parts
        of the hand that are clipped.
        """
        if not self.landmarks:
            return []
        return [i for i, lm in enumerate(self.landmarks.landmark) if not self._in_bounds(lm, margin)]

    def get_hand_type(self) -> HandType:
        """Get this hand's type (LEFT or RIGHT)."""
        if not self.handedness or not self.is_fully_visible():
            return HandType.UNKNOWN
        if self.handedness.classification[0].score < self._MIN_HANDEDNESS_SCORE:
            return HandType.UNKNOWN
        label = self.handedness.classification[0].label
        return HandType[label.upper()]

    def _hand_size(self) -> float:
        """Wrist-to-middle-knuckle distance, used to normalize finger extension."""
        if self._hand_size_cache is None:
            self._hand_size_cache = self._calculate_3d_distance(
                self.landmarks.landmark[mp_hands.HandLandmark.WRIST],
                self.landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
            )
        return self._hand_size_cache

    def finger_extension_ratios(self) -> List[float]:
        """Tip-to-knuckle distance of each finger, normalized by hand size.

        Ordered like FINGER_NAMES. Empty when landmarks are missing or the
        hand is too small to normalize against. is_open() thresholds these
        values and debug output prints them, which is how an open-hand
        gesture that never fires gets diagnosed.
        """
        if not self.landmarks:
            return []

        hand_size = self._hand_size()
        if hand_size < 1e-6:
            logger.warning("Hand size too small (%s), cannot determine if open.", hand_size)
            return []

        return [
            self._calculate_3d_distance(self.landmarks.landmark[tip], self.landmarks.landmark[mcp]) / hand_size
            for tip, mcp in zip(self._FINGER_TIPS, self._FINGER_MCPS)
        ]

    def is_open(self, threshold_ratio: Optional[float] = None) -> bool:
        """Check if the hand is open by measuring finger extension."""
        if threshold_ratio is None:
            threshold_ratio = self._open_threshold_ratio
        ratios = self.finger_extension_ratios()
        return bool(ratios) and all(d > threshold_ratio for d in ratios)

    def index_offset(self) -> float:
        """Signed horizontal tip-to-knuckle offset of the index finger.

        Positive means pointing to the user's right, since the frame is
        mirrored (selfie view). get_index_orientation() thresholds this.
        """
        if not self.landmarks:
            raise ValueError("Hand landmarks not available.")

        index_tip = self.landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
        index_base = self.landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
        return index_tip.x - index_base.x

    def get_index_orientation(self, threshold: Optional[float] = None) -> IndexOrientation:
        """Get the orientation of the index finger.

        Assumes a mirrored (selfie-view) frame, where a larger x means
        further to the user's right.
        """
        if threshold is None:
            threshold = self._index_orientation_threshold
        diff = self.index_offset()

        if diff > threshold:
            return IndexOrientation.RIGHT
        elif diff < -threshold:
            return IndexOrientation.LEFT
        else:
            return IndexOrientation.STRAIGHT

    def diagnostics(self, margin: float = 0.01) -> HandDiagnostics:
        """Recompute this hand's classification, keeping the raw numbers.

        Only called while debug mode is on; the extra landmark passes are not
        worth paying for in the normal frame loop.
        """
        classification = self.handedness.classification[0] if self.handedness else None
        label = classification.label if classification else "?"
        score = float(classification.score) if classification else 0.0
        out_of_frame = self.landmarks_out_of_frame(margin)
        hand_type = self.get_hand_type()

        reason = ""
        if hand_type == HandType.UNKNOWN:
            if classification is None:
                reason = "no handedness"
            elif not self.landmarks:
                reason = "no landmarks"
            elif out_of_frame:
                reason = f"{len(out_of_frame)} landmark(s) out of frame"
            elif score < self._MIN_HANDEDNESS_SCORE:
                reason = f"handedness {score:.2f} < {self._MIN_HANDEDNESS_SCORE:.2f}"
            else:
                reason = f"unrecognized label {label!r}"

        return HandDiagnostics(
            label=label,
            score=score,
            hand_type=hand_type,
            unknown_reason=reason,
            out_of_frame=out_of_frame,
            finger_ratios=self.finger_extension_ratios(),
            open_threshold=self._open_threshold_ratio,
            is_open=self.is_open(),
            index_offset=self.index_offset() if self.landmarks else 0.0,
            index_threshold=self._index_orientation_threshold,
            index_orientation=self.get_index_orientation() if self.landmarks else IndexOrientation.STRAIGHT,
        )

    @classmethod
    def landmark_name(cls, index: int) -> str:
        """Human-readable name of a landmark index, for debug output."""
        try:
            return mp_hands.HandLandmark(index).name
        except ValueError:
            return str(index)


class HandProcessor:
    """Processes video frames to detect and analyze hand gestures."""

    def __init__(self, min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5,
                 max_hands: int = 2, open_threshold_ratio: float = 0.6,
                 index_orientation_threshold: float = 0.05):
        self.hands_engine = mp_hands.Hands(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            max_num_hands=max_hands
        )
        self._open_threshold_ratio = open_threshold_ratio
        self._index_orientation_threshold = index_orientation_threshold

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
                    index_orientation_threshold=self._index_orientation_threshold
                ))

        return detected_hands

    def close(self) -> None:
        """Releases the MediaPipe hands engine."""
        self.hands_engine.close()
