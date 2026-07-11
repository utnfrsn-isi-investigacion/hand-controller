import unittest
from unittest.mock import Mock
import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from handlers import CarHandler, CarAction  # noqa: E402
from hand import Hand, HandType, IndexOrientation  # noqa: E402


class TestCarHandler(unittest.TestCase):

    def setUp(self):
        """Set up a mock ESP32 connector and the CarHandler."""
        self.mock_esp32 = Mock()
        self.mock_esp32.send_action.return_value = True
        # Large refresh interval so tests only observe change-driven sends
        self.handler = CarHandler(self.mock_esp32, refresh_interval=3600)

    def create_mock_hand(self, hand_type, is_open, orientation):
        """Helper to create a mock Hand object with specific properties."""
        mock_hand = Mock(spec=Hand)
        mock_hand.get_hand_type.return_value = hand_type
        mock_hand.is_open.return_value = is_open
        mock_hand.get_index_orientation.return_value = orientation
        return mock_hand

    def test_left_hand_accelerate(self):
        """Test that an open left hand triggers ACCELERATE."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        right_hand = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        self.handler.process_hands([left_hand_open, right_hand])
        # It should send ACCELERATE for the left hand and STRAIGHT for the right hand
        self.mock_esp32.send_action.assert_any_call(CarAction.ACCELERATE.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_STRAIGHT.value)
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

    def test_left_hand_stop(self):
        """Test that a closed left hand triggers STOP."""
        left_hand_closed = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        right_hand = self.create_mock_hand(HandType.RIGHT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        self.handler.process_hands([left_hand_closed, right_hand])
        self.mock_esp32.send_action.assert_any_call(CarAction.STOP.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_STRAIGHT.value)
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

    def test_right_hand_direction_right(self):
        """Test right hand direction controls: RIGHT orientation."""
        right_hand_right = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.RIGHT)
        left_hand = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.LEFT)
        self.handler.process_hands([right_hand_right, left_hand])
        self.mock_esp32.send_action.assert_any_call(CarAction.STOP.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_RIGHT.value)

    def test_right_hand_direction_left(self):
        """Test right hand direction controls: LEFT orientation."""
        right_hand_left = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.LEFT)
        left_hand = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.LEFT)
        self.handler.process_hands([right_hand_left, left_hand])
        self.mock_esp32.send_action.assert_any_call(CarAction.STOP.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_LEFT.value)

    def test_no_hands(self):
        """Test that no hands triggers STOP and DIRECTION_STRAIGHT."""
        self.handler.process_hands([])
        self.mock_esp32.send_action.assert_any_call(CarAction.STOP.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_STRAIGHT.value)
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

    def test_process_hands_returns_actions(self):
        """Test that process_hands returns the actions it determined."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        right_hand_right = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.RIGHT)
        actions = self.handler.process_hands([left_hand_open, right_hand_right])
        self.assertEqual(actions[HandType.LEFT], CarAction.ACCELERATE)
        self.assertEqual(actions[HandType.RIGHT], CarAction.DIRECTION_RIGHT)

    def test_single_hand_uses_defaults_and_keeps_buffers_clean(self):
        """Test that with only one hand detected, defaults are used and buffers stay empty."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        actions = self.handler.process_hands([left_hand_open])
        self.assertEqual(actions[HandType.LEFT], CarAction.STOP)
        self.assertEqual(actions[HandType.RIGHT], CarAction.DIRECTION_STRAIGHT)
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 0)
        self.assertEqual(len(self.handler._action_buffers[HandType.RIGHT]), 0)

    def test_action_sent_only_once_when_unchanged(self):
        """Test that the same actions are not sent repeatedly."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        # First call should send actions
        self.handler.process_hands([left_hand_open])
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

        # Subsequent calls with the same state should not send more actions
        self.handler.process_hands([left_hand_open])
        self.handler.process_hands([left_hand_open])
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

    def test_unchanged_action_resent_after_refresh_interval(self):
        """Test the keepalive: unchanged actions are resent once the refresh interval elapses."""
        handler = CarHandler(self.mock_esp32, refresh_interval=0)
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        handler.process_hands([left_hand_open])
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

        # Same state, but refresh_interval=0 means every call resends
        handler.process_hands([left_hand_open])
        self.assertEqual(self.mock_esp32.send_action.call_count, 4)

    def test_failed_send_is_retried_until_success(self):
        """Test that actions keep being attempted while sending fails."""
        self.mock_esp32.send_action.return_value = False
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        self.handler.process_hands([left_hand_open])
        self.handler.process_hands([left_hand_open])
        # Failed sends are not recorded as "last action", so both frames retry
        self.assertEqual(self.mock_esp32.send_action.call_count, 4)

        # Once sending succeeds, the action is recorded and no longer resent
        self.mock_esp32.send_action.return_value = True
        self.handler.process_hands([left_hand_open])
        self.assertEqual(self.mock_esp32.send_action.call_count, 6)
        self.handler.process_hands([left_hand_open])
        self.assertEqual(self.mock_esp32.send_action.call_count, 6)

    def test_get_action_is_read_only(self):
        """Test that get_action does not modify the action buffers."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        action = self.handler.get_action(left_hand_open)

        self.assertEqual(action, CarAction.ACCELERATE)
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 0)

    def test_record_action_populates_buffer(self):
        """Test that _record_action adds actions to the buffer and returns the correct action."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        # Initially buffer should be empty
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 0)

        action = self.handler._record_action(left_hand_open)

        # Buffer should now have one element and action should be correct
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 1)
        self.assertEqual(action, CarAction.ACCELERATE)

    def test_unknown_hand_does_not_crash(self):
        """Test that UNKNOWN hands are handled without touching (missing) buffers."""
        unknown_hand = self.create_mock_hand(HandType.UNKNOWN, is_open=True, orientation=IndexOrientation.STRAIGHT)

        self.assertEqual(self.handler._record_action(unknown_hand), CarAction.STOP)
        self.assertEqual(self.handler.get_action(unknown_hand), CarAction.STOP)
        self.assertIsNone(self.handler._majority_action(unknown_hand))

    def test_stop_bypasses_majority_vote(self):
        """A STOP gesture takes effect immediately, even against an ACCELERATE majority."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        left_hand_closed = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)

        # Fill the buffer with ACCELERATE
        for _ in range(10):
            self.handler._record_action(left_hand_open)

        # A single closed-hand frame must return STOP, not the majority
        self.assertEqual(self.handler._record_action(left_hand_closed), CarAction.STOP)
        # The read-only path agrees
        self.assertEqual(self.handler.get_action(left_hand_closed), CarAction.STOP)

    def test_accelerate_still_smoothed_by_majority(self):
        """Non-priority actions keep majority smoothing: one open frame can't override STOP."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        left_hand_closed = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)

        # Fill the buffer with STOP
        for _ in range(10):
            self.handler._record_action(left_hand_closed)

        # A single open-hand frame is outvoted by the STOP majority
        action = self.handler._record_action(left_hand_open)
        self.assertEqual(action, CarAction.STOP)

    def test_buffer_respects_max_size(self):
        """Test that buffer doesn't exceed the specified max size."""
        handler = CarHandler(self.mock_esp32, buffer_size=5)
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        # Add more actions than buffer size
        for _ in range(10):
            handler._record_action(left_hand_open)

        # Buffer should only contain buffer_size elements
        self.assertEqual(len(handler._action_buffers[HandType.LEFT]), 5)

    def test_buffer_fifo_behavior(self):
        """Test that buffer uses FIFO (first in, first out) behavior."""
        handler = CarHandler(self.mock_esp32, buffer_size=3)
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        left_hand_closed = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)

        # Add 2 STOP actions
        handler._record_action(left_hand_closed)
        handler._record_action(left_hand_closed)

        # Add 3 ACCELERATE actions (should push out the STOP actions)
        handler._record_action(left_hand_open)
        handler._record_action(left_hand_open)
        action = handler._record_action(left_hand_open)

        # After buffer fills and old actions are pushed out, should return ACCELERATE
        self.assertEqual(action, CarAction.ACCELERATE)

    def test_separate_buffers_for_left_and_right_hands(self):
        """Test that left and right hands have separate buffers."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        right_hand_right = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.RIGHT)

        # Add actions for both hands
        self.handler._record_action(left_hand_open)
        self.handler._record_action(left_hand_open)
        self.handler._record_action(right_hand_right)

        # Check buffers are independent
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 2)
        self.assertEqual(len(self.handler._action_buffers[HandType.RIGHT]), 1)

        # Check buffer contents
        self.assertEqual(self.handler._action_buffers[HandType.LEFT][0], CarAction.ACCELERATE)
        self.assertEqual(self.handler._action_buffers[HandType.RIGHT][0], CarAction.DIRECTION_RIGHT)

    def test_get_action_uses_majority_when_available(self):
        """Test that get_action returns the majority action from the buffer."""
        handler = CarHandler(self.mock_esp32, buffer_size=10)
        right_hand_left = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.LEFT)
        right_hand_straight = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        # Fill buffer with mostly DIRECTION_LEFT actions
        for _ in range(7):
            handler._record_action(right_hand_left)
        # Add fewer STRAIGHT actions
        for _ in range(2):
            handler._record_action(right_hand_straight)

        # Reading with a STRAIGHT gesture still returns the majority (DIRECTION_LEFT)
        action = handler.get_action(right_hand_straight)
        self.assertEqual(action, CarAction.DIRECTION_LEFT)

    def test_right_hand_buffer_with_direction_changes(self):
        """Test buffering and majority for right hand direction changes."""
        right_hand_left = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.LEFT)
        right_hand_right = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.RIGHT)
        right_hand_straight = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        # Add mixed directions with LEFT being majority
        self.handler._record_action(right_hand_left)
        self.handler._record_action(right_hand_left)
        self.handler._record_action(right_hand_left)
        self.handler._record_action(right_hand_right)
        self.handler._record_action(right_hand_straight)

        # Next action should be DIRECTION_LEFT (majority)
        action = self.handler._record_action(right_hand_straight)
        self.assertEqual(action, CarAction.DIRECTION_LEFT)


if __name__ == '__main__':
    unittest.main()
