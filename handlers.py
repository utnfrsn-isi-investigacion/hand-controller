import abc
import typing
from enum import Enum
import collections

from esp32 import Esp32
from hand import HandGestureDetector, HandType, IndexOrientation


import collections
import typing
from enum import Enum


class Handler(abc.ABC):
    _BUFFER_SIZE = 20

    def __init__(self, esp32: Esp32):
        self._esp32_connector = esp32
        # store last sent actions
        self._last_actions: typing.Dict[HandType, typing.Optional[Enum]] = {
            HandType.LEFT: None,
            HandType.RIGHT: None,
        }
        # buffers for each hand
        self._action_buffers: typing.Dict[HandType, collections.deque] = {
            HandType.LEFT: collections.deque(maxlen=self._BUFFER_SIZE),
            HandType.RIGHT: collections.deque(maxlen=self._BUFFER_SIZE),
        }

    def detect_action(self, hand_detector: HandGestureDetector):
        hand_type = hand_detector.hand_type()
        action = self._get_action(hand_detector)
        if hand_type == HandType.UNKNOWN:
            self._esp32_connector.send_action(action.value)
            self.__reset_buffers()
            self.__reset_last_actions()
            return

        action = self._get_action(hand_detector)
        # Add action to buffer
        self._action_buffers[hand_type].append(action)

        # Decide majority action in buffer
        majority_action = self._majority_action(hand_detector)

        # Send only if majority action changed
        if self._last_actions[hand_type] != majority_action:
            self._esp32_connector.send_action(majority_action.value)
            self._last_actions[hand_type] = majority_action

    def _majority_action(self, hand_detector: HandGestureDetector) -> Enum or None:
        if hand_detector.hand_type() == HandType.UNKNOWN:
            return None
        counter = collections.Counter(self._action_buffers[hand_detector.hand_type()])
        return counter.most_common(1)[0][0]

    def __reset_buffers(self):
        for key in self._action_buffers:
            self._action_buffers[key].clear()

    def __reset_last_actions(self) -> None:
        self._last_actions = {HandType.LEFT: None, HandType.RIGHT: None}

    def get_action(self, hand_detector: HandGestureDetector) -> Enum:
        hand_type = hand_detector.hand_type()
        if hand_type in self._action_buffers and self._action_buffers[hand_type]:
            return self._majority_action(hand_detector)
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
