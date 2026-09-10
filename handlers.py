import abc
import collections
import time
from enum import Enum
from typing import Dict, Optional, List

from esp32 import Esp32
from hand import Hand, HandType, IndexOrientation, VerticalOrientation


class Handler(abc.ABC):
    def __init__(self, esp32: Esp32, buffer_size: int = 10, refresh_interval: float = 0.5):
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
        action = self._get_action(hand)
        majority = self._majority_action(hand)
        return majority if majority is not None else action

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

    def get_action_confidence(self, hand_type: HandType) -> Optional[float]:
        """Share (0..1) of the most common action in this hand's buffer.

        Serves as a gesture-stability indicator for display. Returns None
        when there is no buffered history for the hand type.
        """
        buffer = self._action_buffers.get(hand_type)
        if not buffer:
            return None
        _, count = collections.Counter(buffer).most_common(1)[0]
        return count / len(buffer)

    def _majority_action(self, hand: Hand) -> Optional[Enum]:
        """Most common action in this hand's buffer, or None when it is empty.

        This vote is also the client's half of the forward/reverse interlock,
        and it only carries it so far. Starting from a buffer saturated with
        one action, an intermediate action has to occupy enough of the buffer
        to outvote both neighbours -- roughly a quarter of it, so ~4 frames at
        the default buffer_size of 10 (~0.13s at 30 FPS), and it then holds the
        majority for only ~2 more. A hand flicked from pointing up to pointing
        down faster than that yields ACCELERATE followed directly by REVERSE,
        with no STOP in between. Enlarging the NEUTRAL thumb band buys crossing
        frames.

        What actually protects the motor is downstream, in the firmware:
        REVERSAL_DWELL_MS holds off a drive command that opposes the current
        direction until the motor has sat stopped for seconds (see
        DriveControl::engage in _esp32/lib/DriveControl). The vote only makes
        the gesture feel right; it is not, and cannot be, the safety guarantee
        -- the ESP32 serves whatever client connects.
        """
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
    REVERSE = "010"
    STOP = "000"
    DIRECTION_LEFT = "101"
    DIRECTION_RIGHT = "110"
    DIRECTION_STRAIGHT = "111"


class CarHandler(Handler):
    def __init__(self, esp32: Esp32, buffer_size: int = 10, refresh_interval: float = 0.5):
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
            # Hand not detected. Drop the history as well as returning the
            # default: a buffer left saturated with the pre-loss action would
            # outvote the first frames of whatever gesture comes back, so the
            # car would replay ACCELERATE for a few frames at a user already
            # signalling REVERSE -- and that burst re-arms the firmware's last
            # driven direction, making the real reversal pay the full dwell.
            # The cost is that the frame after reacquisition is unsmoothed,
            # since a one-entry buffer is its own majority, so a misread there
            # reaches the wire. What it cannot do is invert a spinning motor:
            # a reversal still brakes and waits out the firmware dwell. A
            # misread in the direction already being driven is a twitch of a
            # frame or two, which is the accepted trade against replaying the
            # pre-loss action for six.
            self._action_buffers[hand_type].clear()
            return self._default_actions[hand_type]

    def _get_action(self, hand: Hand) -> CarAction:
        """Return the Action for this hand based on type and gesture."""
        hand_type = hand.get_hand_type()

        if hand_type == HandType.LEFT:
            # Landmarks too collapsed to measure are not a gesture at all, and
            # the only safe reading of "no gesture" is STOP. Without this the
            # hand falls through to the thumb angle, which on degenerate points
            # cannot return NEUTRAL -- so garbage would read as ACCELERATE or
            # REVERSE. This is the branch that keeps "every error path ends in
            # a stop" true after the gesture set was inverted.
            if not hand.has_usable_geometry():
                return CarAction.STOP
            # An open palm is the fast, unambiguous stop. Driving takes a
            # closed hand, and then the thumb picks the direction.
            if hand.is_open():
                return CarAction.STOP
            orientation = hand.get_thumb_orientation()
            if orientation == VerticalOrientation.UP:
                return CarAction.ACCELERATE
            elif orientation == VerticalOrientation.DOWN:
                return CarAction.REVERSE
            else:
                # Thumb sideways, i.e. a plain fist: the neutral pose a thumb
                # crosses on its way between ACCELERATE and REVERSE. Makes the
                # stop deliberate rather than guaranteed -- the firmware's
                # reversal dwell is what enforces it (see
                # Handler._majority_action).
                return CarAction.STOP

        elif hand_type == HandType.RIGHT:
            orientation = hand.get_index_orientation()
            if orientation == IndexOrientation.LEFT:
                return CarAction.DIRECTION_LEFT
            elif orientation == IndexOrientation.RIGHT:
                return CarAction.DIRECTION_RIGHT
            else:
                return CarAction.DIRECTION_STRAIGHT

        return CarAction.STOP
