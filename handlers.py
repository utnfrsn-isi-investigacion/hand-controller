import abc
import typing
from enum import Enum

from esp32 import Esp32
from hand import HandGestureDetector, HandType, IndexOrientation


class Handler(abc.ABC):
    def __init__(self, esp32: Esp32):
        self._esp32_connector = esp32
        self._last_actions: typing.Dict[HandType, typing.Optional[Enum]] = {
            HandType.LEFT: None,
            HandType.RIGHT: None,
        }

    def detect_action(self, hand_detector: HandGestureDetector):
        action = self._get_action(hand_detector)
        hand_type = hand_detector.hand_type()
        if hand_type == HandType.UNKNOWN:
            self._esp32_connector.send_action(action.value)
            self.__reset_last_actions()
            return
        # Only send if action changed for this hand type
        if self._last_actions[hand_type] is None or self._last_actions[hand_type] != action:
            self._esp32_connector.send_action(action.value)
            self._last_actions[hand_type] = action

    def __reset_last_actions(self) -> None:
        self._last_actions: typing.Dict[HandType, typing.Optional[Enum]] = {
            HandType.LEFT: None,
            HandType.RIGHT: None,
        }

    def get_action(self, hand_detector: HandGestureDetector) -> Enum:
        return self._get_action(hand_detector)

    @abc.abstractmethod
    def _get_action(self, hand_detector: HandGestureDetector) -> Enum:
        pass


class CarHandler(Handler):
    class Action(Enum):
        ACCELERATE = "001"
        STOP = "000"
        DIRECTION_LEFT = "101"
        DIRECTION_RIGHT = "110"
        DIRECTION_STRAIGHT = "111"

    def _get_action(self, hand_detector: HandGestureDetector) -> Action:
        """Return the Action for this hand based on type and gesture."""
        hand_type = hand_detector.hand_type()
        if hand_type == HandType.UNKNOWN:
            return self.Action.STOP
        if hand_type == HandType.LEFT:
            return self.Action.ACCELERATE if hand_detector.is_open() else self.Action.STOP
        elif hand_type == HandType.RIGHT:
            orientation = hand_detector.index_orientation()
            if orientation == IndexOrientation.LEFT:
                return self.Action.DIRECTION_LEFT
            elif orientation == IndexOrientation.RIGHT:
                return self.Action.DIRECTION_RIGHT
            else:
                return self.Action.DIRECTION_STRAIGHT
        else:
            raise ValueError("Cannot determine action for unknown hand type")
