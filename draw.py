"""Overlay rendering for the hand controller preview window.

All OpenCV drawing goes through the Drawer class so gesture logic stays
free of rendering details and every visual element can be configured or
toggled from DisplayConfig.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import cv2

from config import DisplayConfig
from hand import Hand, HandType, mp_drawing, mp_hands

# Fixed overlay colors (BGR)
_STATUS_OK_COLOR = (0, 255, 0)
_STATUS_ERROR_COLOR = (0, 0, 255)
_FPS_COLOR = (255, 255, 0)


class Drawer:
    """Renders visual feedback overlays on the preview frame."""

    # Text anchor per hand type (x, y)
    _ACTION_POSITIONS = {
        HandType.LEFT: (50, 50),
        HandType.RIGHT: (350, 50),
    }

    def __init__(self, config: DisplayConfig):
        self._config = config

    def draw(self, frame: Any, hands: List[Hand], actions: Dict[HandType, Enum],
             confidences: Dict[HandType, Optional[float]], connected: bool, fps: float) -> None:
        """Draw all enabled overlays for one frame.

        :param frame: BGR frame to draw on (modified in place)
        :param hands: detected hands
        :param actions: action per hand type, as returned by the handler
        :param confidences: gesture confidence (0..1) per hand type, or None
        :param connected: whether the ESP32 connection is up
        :param fps: current frames per second
        """
        if not self._config.show_overlays:
            return

        for hand in hands:
            hand_type = hand.get_hand_type()
            if hand_type == HandType.UNKNOWN:
                continue
            self._draw_hand(frame, hand, hand_type, actions[hand_type], confidences.get(hand_type))

        self._draw_connection_status(frame, connected)

        if self._config.show_fps:
            self._draw_fps(frame, fps)

    def _hand_color(self, hand_type: HandType) -> Tuple[int, ...]:
        if hand_type == HandType.LEFT:
            return tuple(self._config.left_hand_color)
        return tuple(self._config.right_hand_color)

    def _draw_hand(self, frame: Any, hand: Hand, hand_type: HandType,
                   action: Enum, confidence: Optional[float]) -> None:
        """Draw landmarks and the current action (with confidence) for one hand."""
        text = action.name
        if self._config.show_confidence and confidence is not None:
            text = f"{text} {confidence:.0%}"

        cv2.putText(frame, text, self._ACTION_POSITIONS[hand_type], cv2.FONT_HERSHEY_SIMPLEX,
                    self._config.text_scale, self._hand_color(hand_type), self._config.text_thickness)

        if self._config.show_landmarks:
            mp_drawing.draw_landmarks(frame, hand.landmarks, mp_hands.HAND_CONNECTIONS)

    def _draw_connection_status(self, frame: Any, connected: bool) -> None:
        """Draw the ESP32 connection state in the top-left corner."""
        if connected:
            text, color = "ESP32: connected", _STATUS_OK_COLOR
        else:
            text, color = "ESP32: disconnected (reconnecting...)", _STATUS_ERROR_COLOR
        cv2.putText(frame, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6 * self._config.text_scale, color, self._config.text_thickness)

    def _draw_fps(self, frame: Any, fps: float) -> None:
        """Draw the FPS counter in the bottom-left corner."""
        cv2.putText(frame, f"FPS: {fps:.0f}", (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7 * self._config.text_scale, _FPS_COLOR, self._config.text_thickness)
