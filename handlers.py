import abc
from enum import Enum
from typing import Dict, Optional, List
import collections

from esp32 import Esp32
from hand import Hand, HandType, IndexOrientation


class Handler(abc.ABC):
    def __init__(self, esp32: Esp32, buffer_size: int = 30):
        self._esp32_connector = esp32
        self._last_actions: Dict[HandType, Optional[Enum]] = {
            HandType.LEFT: None,
            HandType.RIGHT: None,
        }
        self._action_buffers: Dict[HandType, collections.deque] = {
            HandType.LEFT: collections.deque(maxlen=buffer_size),
            HandType.RIGHT: collections.deque(maxlen=buffer_size),
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

    def get_action(self, hand: Hand) -> Enum:
        hand_type = hand.get_hand_type()
        self._action_buffers[hand.get_hand_type()].append(self._get_action(hand))
        if hand_type in self._action_buffers and self._action_buffers[hand_type]:
            majority = self._majority_action(hand)
            return majority if majority is not None else self._get_action(hand)
        return self._get_action(hand)

    def _majority_action(self, hand: Hand) -> Optional[Enum]:
        if hand.get_hand_type() == HandType.UNKNOWN:
            return None
        counter = collections.Counter(self._action_buffers[hand.get_hand_type()])
        most_common = counter.most_common(1)
        if most_common:
            return most_common[0][0]
        return None

    @abc.abstractmethod
    def _get_action(self, hand: Hand) -> Enum:
        pass


class CarHandler(Handler):
    class Action(Enum):
        ACCELERATE = "001"
        STOP = "000"
        DIRECTION_LEFT = "101"
        DIRECTION_RIGHT = "110"
        DIRECTION_STRAIGHT = "111"

    def __init__(self, esp32: Esp32, buffer_size: int = 30):
        super().__init__(esp32, buffer_size)
        # Default actions when hands are not detected
        self._default_actions: Dict[HandType, 'CarHandler.Action'] = {
            HandType.LEFT: self.Action.STOP,
            HandType.RIGHT: self.Action.DIRECTION_STRAIGHT,
        }

    def process_hands(self, hands: List[Hand]) -> None:
        """Process a list of detected hands and send actions for car control."""
        # Create a dictionary of hand types present in the current frame
        detected_hands_map = {hand.get_hand_type(): hand for hand in hands if hand.get_hand_type() != HandType.UNKNOWN}

        # Process both hands types even if one is missing
        for hand_type in [HandType.LEFT, HandType.RIGHT]:
            hand = detected_hands_map.get(hand_type)  # None if hand not detected
            action = self._determine_action(hand_type, hand)
            if self._last_actions.get(hand_type) != action:
                self._send_action(hand_type, action)

    def _determine_action(self, hand_type: HandType, hand: Optional[Hand]) -> 'CarHandler.Action':
        """Determine the action for a specific hand type.
        
        Args:
            hand_type: The type of hand to process (LEFT or RIGHT)
            hand: The detected Hand object, or None if hand is not detected
            
        Returns:
            The action to perform for this hand
        """
        if hand is not None:
            # Hand is detected - use buffered action from get_action
            action = self.get_action(hand)
            return action  # type: ignore[return-value]
        else:
            # Hand not detected - return default action without polluting the buffer
            return self._default_actions[hand_type]

    def _get_action(self, hand: Hand) -> Action:
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
