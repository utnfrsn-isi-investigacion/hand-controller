import abc
from enum import Enum
from typing import Dict, Optional, List, Deque
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
        self._action_buffers: Dict[HandType, Deque[Enum]] = {
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

    def get_last_action(self, hand_type: HandType) -> Optional[Enum]:
        """Get the last action sent for a hand type without modifying the buffer.

        This method is safe to call for display purposes as it doesn't have side effects.
        It returns the last action that was actually sent to the ESP32 for the given
        hand type.

        Args:
            hand_type: The type of hand (LEFT or RIGHT) to get the last action for

        Returns:
            The last action sent for this hand type, or None if no action has been sent yet
        """
        return self._last_actions.get(hand_type)

    def get_action(self, hand: Hand) -> Enum:
        """Get the action for a hand using majority voting from the action buffer.

        This method adds the current action to the buffer and returns the majority action
        based on the buffered actions. This implements gesture smoothing to reduce noise
        and false detections.

        WARNING: This method has side effects - it modifies the action buffer. For display
        purposes without buffer modification, use get_last_action() instead.

        Args:
            hand: The Hand object to determine the action for

        Returns:
            The action to perform based on majority voting of buffered actions
        """
        hand_type = hand.get_hand_type()
        action = self._get_action(hand)
        self._action_buffers[hand.get_hand_type()].append(action)
        if hand_type in self._action_buffers and self._action_buffers[hand_type]:
            majority = self._majority_action(hand)
            return majority if majority is not None else action
        return action

    def _majority_action(self, hand: Hand) -> Optional[Enum]:
        """Calculate the most common action from the buffer using majority voting.

        Uses Counter to determine which action appears most frequently in the buffer
        for the given hand type. This helps smooth out noisy gesture detections.

        Args:
            hand: The Hand object to get the majority action for

        Returns:
            The most common action in the buffer, or None if hand type is UNKNOWN
            or if the buffer is empty
        """
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


class CarAction(Enum):
    ACCELERATE = "001"
    STOP = "000"
    DIRECTION_LEFT = "101"
    DIRECTION_RIGHT = "110"
    DIRECTION_STRAIGHT = "111"


class CarHandler(Handler):
    def __init__(self, esp32: Esp32, buffer_size: int = 30):
        super().__init__(esp32, buffer_size)
        # Default actions when hands are not detected
        self._default_actions: Dict[HandType, CarAction] = {
            HandType.LEFT: CarAction.STOP,
            HandType.RIGHT: CarAction.DIRECTION_STRAIGHT,
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

    def _determine_action(self, hand_type: HandType, hand: Optional[Hand]) -> CarAction:
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
