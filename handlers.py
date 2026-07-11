import abc
import collections
import time
from enum import Enum
from typing import Dict, Optional, List

from esp32 import Esp32
from hand import Hand, HandType, IndexOrientation


class Handler(abc.ABC):
    def __init__(self, esp32: Esp32, buffer_size: int = 30, refresh_interval: float = 0.5):
        self._esp32_connector = esp32
        self._refresh_interval = refresh_interval
        self._last_actions: Dict[HandType, Optional[Enum]] = {
            HandType.LEFT: None,
            HandType.RIGHT: None,
        }
        self._last_send_times: Dict[HandType, float] = {
            HandType.LEFT: 0.0,
            HandType.RIGHT: 0.0,
        }
        self._action_buffers: Dict[HandType, collections.deque] = {
            HandType.LEFT: collections.deque(maxlen=buffer_size),
            HandType.RIGHT: collections.deque(maxlen=buffer_size),
        }

    @abc.abstractmethod
    def process_hands(self, hands: List[Hand]) -> Dict[HandType, Enum]:
        """Process a list of detected hands, send actions, and return them."""
        pass

    def _should_send(self, hand_type: HandType, action: Enum) -> bool:
        """Send when the action changed, or periodically as a keepalive refresh.

        The periodic resend keeps the firmware's dead-man timeout fed and
        re-syncs state if the ESP32 rebooted.
        """
        if self._last_actions.get(hand_type) != action:
            return True
        return time.monotonic() - self._last_send_times[hand_type] >= self._refresh_interval

    def _send_action(self, hand_type: HandType, action: Enum) -> None:
        """Sends the action; on success records it for change/refresh tracking."""
        if self._esp32_connector.send_action(action.value):
            self._last_actions[hand_type] = action
            self._last_send_times[hand_type] = time.monotonic()

    def get_action(self, hand: Hand) -> Enum:
        """Return the action for this hand, preferring the buffered majority.

        Read-only: does not modify the action buffers.
        """
        majority = self._majority_action(hand)
        return majority if majority is not None else self._get_action(hand)

    def _record_action(self, hand: Hand) -> Enum:
        """Record the hand's current action in its buffer and return the smoothed action."""
        action = self._get_action(hand)
        hand_type = hand.get_hand_type()
        if hand_type in self._action_buffers:
            self._action_buffers[hand_type].append(action)
            majority = self._majority_action(hand)
            if majority is not None:
                return majority
        return action

    def _majority_action(self, hand: Hand) -> Optional[Enum]:
        hand_type = hand.get_hand_type()
        if hand_type not in self._action_buffers:
            return None
        counter = collections.Counter(self._action_buffers[hand_type])
        most_common = counter.most_common(1)
        if most_common:
            return most_common[0][0]
        return None

    @abc.abstractmethod
    def _get_action(self, hand: Hand) -> Enum:
        pass


class CarAction(Enum):
    ACCELERATE = "001"
    STOP = "000"
    DIRECTION_LEFT = "101"
    DIRECTION_RIGHT = "110"
    DIRECTION_STRAIGHT = "111"


class CarHandler(Handler):
    def __init__(self, esp32: Esp32, buffer_size: int = 30, refresh_interval: float = 0.5):
        super().__init__(esp32, buffer_size, refresh_interval)
        # Default actions when hands are not detected
        self._default_actions: Dict[HandType, CarAction] = {
            HandType.LEFT: CarAction.STOP,
            HandType.RIGHT: CarAction.DIRECTION_STRAIGHT,
        }

    def __determine_actions(self, hands: List[Hand]) -> Dict[HandType, CarAction]:
        """
        Determine car actions based on hand detections.
        If  it does not detect the 2 hands, stops
        """
        detected = {h.get_hand_type(): h for h in hands if h.get_hand_type() != HandType.UNKNOWN}
        both = HandType.LEFT in detected and HandType.RIGHT in detected

        return {
            ht: self._determine_action(ht, detected[ht] if both else None)
            for ht in (HandType.LEFT, HandType.RIGHT)
        }

    def process_hands(self, hands: List[Hand]) -> Dict[HandType, Enum]:
        """Process a list of detected hands and send actions for car control."""
        actions: Dict[HandType, Enum] = dict(self.__determine_actions(hands))
        for hand_type, action in actions.items():
            if self._should_send(hand_type, action):
                self._send_action(hand_type, action)
        return actions

    def _determine_action(self, hand_type: HandType, hand: Optional[Hand]) -> CarAction:
        """Determine the action for a specific hand type.

        Args:
            hand_type: The type of hand to process (LEFT or RIGHT)
            hand: The detected Hand object, or None if hand is not detected

        Returns:
            The action to perform for this hand
        """
        if hand is not None:
            # Hand is detected - record it and use the buffered (smoothed) action
            return self._record_action(hand)  # type: ignore[return-value]
        else:
            # Hand not detected - return default action without polluting the buffer
            return self._default_actions[hand_type]

    def _get_action(self, hand: Hand) -> CarAction:
        """Return the Action for this hand based on type and gesture."""
        hand_type = hand.get_hand_type()

        if hand_type == HandType.LEFT:
            return CarAction.ACCELERATE if hand.is_open() else CarAction.STOP

        elif hand_type == HandType.RIGHT:
            orientation = hand.get_index_orientation()
            if orientation == IndexOrientation.LEFT:
                return CarAction.DIRECTION_LEFT
            elif orientation == IndexOrientation.RIGHT:
                return CarAction.DIRECTION_RIGHT
            else:
                return CarAction.DIRECTION_STRAIGHT

        return CarAction.STOP
