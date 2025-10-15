import abc
from enum import Enum
from typing import Dict, Optional, List

from esp32 import Esp32
from hand import Hand, HandType, IndexOrientation


class Handler(abc.ABC):
    def __init__(self, esp32: Esp32):
        self._esp32_connector = esp32
        self._last_actions: Dict[HandType, Optional[Enum]] = {
            HandType.LEFT: None,
            HandType.RIGHT: None,
        }

    @abc.abstractmethod
    def process_hands(self, hands: List[Hand]) -> None:
        """Process a list of detected hands and send actions."""
        pass

    def _send_action(self, hand_type: HandType, action: Enum):
        """Sends the action and updates the last action for the given hand type."""
        if self._esp32_connector.is_connected():
            self._esp32_connector.send_action(action.value)
            self._last_actions[hand_type] = action

    @abc.abstractmethod
    def get_action(self, hand: Hand) -> Enum:
        pass


class CarHandler(Handler):
    class Action(Enum):
        ACCELERATE = "001"
        STOP = "000"
        DIRECTION_LEFT = "101"
        DIRECTION_RIGHT = "110"
        DIRECTION_STRAIGHT = "111"

    def process_hands(self, hands: List[Hand]) -> None:
        """Process a list of detected hands and send actions for car control."""

        # Create a dictionary of hand types present in the current frame
        detected_hands_map = {hand.get_hand_type(): hand for hand in hands if hand.get_hand_type() != HandType.UNKNOWN}

        # Determine and send action for the left hand (throttle)
        if HandType.LEFT in detected_hands_map:
            left_action = self.get_action(detected_hands_map[HandType.LEFT])
        else:
            left_action = self.Action.STOP

        if self._last_actions.get(HandType.LEFT) != left_action:
            self._send_action(HandType.LEFT, left_action)

        # Determine and send action for the right hand (direction)
        if HandType.RIGHT in detected_hands_map:
            right_action = self.get_action(detected_hands_map[HandType.RIGHT])
        else:
            right_action = self.Action.DIRECTION_STRAIGHT

        if self._last_actions.get(HandType.RIGHT) != right_action:
            self._send_action(HandType.RIGHT, right_action)

    def get_action(self, hand: Hand) -> Action:
        """Return the Action for this hand based on type and gesture."""
        hand_type = hand.get_hand_type()

        if hand_type == HandType.LEFT:
            return self.Action.ACCELERATE if hand.is_open() else self.Action.STOP

        elif hand_type == HandType.RIGHT:
            orientation = hand.get_index_orientation()
            if orientation == IndexOrientation.LEFT:
                return self.Action.DIRECTION_LEFT
            elif orientation == IndexOrientation.RIGHT:
                return self.Action.DIRECTION_RIGHT
            else:
                return self.Action.DIRECTION_STRAIGHT

        return self.Action.STOP
