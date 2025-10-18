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
        self.mock_esp32.is_connected.return_value = True
        self.handler = CarHandler(self.mock_esp32)

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
        self.handler.process_hands([left_hand_open])
        # It should send ACCELERATE for left hand and STRAIGHT for the absent right hand
        self.mock_esp32.send_action.assert_any_call(CarAction.ACCELERATE.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_STRAIGHT.value)
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

    def test_left_hand_stop(self):
        """Test that a closed left hand triggers STOP."""
        left_hand_closed = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        self.handler.process_hands([left_hand_closed])
        self.mock_esp32.send_action.assert_any_call(CarAction.STOP.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_STRAIGHT.value)
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

    def test_right_hand_direction_right(self):
        """Test right hand direction controls: RIGHT orientation."""
        right_hand_right = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.RIGHT)
        self.handler.process_hands([right_hand_right])
        self.mock_esp32.send_action.assert_any_call(CarAction.STOP.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_RIGHT.value)

    def test_right_hand_direction_left(self):
        """Test right hand direction controls: LEFT orientation."""
        right_hand_left = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.LEFT)
        self.handler.process_hands([right_hand_left])
        self.mock_esp32.send_action.assert_any_call(CarAction.STOP.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_LEFT.value)

    def test_no_hands(self):
        """Test that no hands triggers STOP and DIRECTION_STRAIGHT."""
        self.handler.process_hands([])
        self.mock_esp32.send_action.assert_any_call(CarAction.STOP.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_STRAIGHT.value)
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

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

    def test_get_action_populates_buffer(self):
        """Test that get_action adds actions to the buffer and returns correct action."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        
        # Initially buffer should be empty
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 0)
        
        # Call get_action
        action = self.handler.get_action(left_hand_open)
        
        # Buffer should now have one element and action should be correct
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 1)
        self.assertEqual(action, CarAction.ACCELERATE)

    def test_majority_action_with_mixed_actions(self):
        """Test majority voting with different actions where one is majority."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        left_hand_closed = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        
        # Add 4 ACCELERATE actions
        for _ in range(4):
            self.handler.get_action(left_hand_open)
        
        # Add 2 STOP actions
        for _ in range(2):
            self.handler.get_action(left_hand_closed)
        
        # Next action with closed hand should still return ACCELERATE (majority)
        action = self.handler.get_action(left_hand_closed)
        self.assertEqual(action, CarAction.ACCELERATE)

    def test_majority_action_returns_none_for_unknown_hand(self):
        """Test that majority action returns None for UNKNOWN hand type."""
        unknown_hand = self.create_mock_hand(HandType.UNKNOWN, is_open=True, orientation=IndexOrientation.STRAIGHT)
        
        majority = self.handler._majority_action(unknown_hand)
        self.assertIsNone(majority)

    def test_buffer_respects_max_size(self):
        """Test that buffer doesn't exceed the specified max size."""
        # Create handler with small buffer size
        handler = CarHandler(self.mock_esp32, buffer_size=5)
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        
        # Add more actions than buffer size
        for _ in range(10):
            handler.get_action(left_hand_open)
        
        # Buffer should only contain buffer_size elements
        self.assertEqual(len(handler._action_buffers[HandType.LEFT]), 5)

    def test_buffer_fifo_behavior(self):
        """Test that buffer uses FIFO (first in, first out) behavior."""
        # Create handler with small buffer size
        handler = CarHandler(self.mock_esp32, buffer_size=3)
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        left_hand_closed = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        
        # Add 2 STOP actions
        handler.get_action(left_hand_closed)
        handler.get_action(left_hand_closed)
        
        # Add 3 ACCELERATE actions (should push out the STOP actions)
        handler.get_action(left_hand_open)
        handler.get_action(left_hand_open)
        action = handler.get_action(left_hand_open)
        
        # After buffer fills and old actions are pushed out, should return ACCELERATE
        self.assertEqual(action, CarAction.ACCELERATE)

    def test_separate_buffers_for_left_and_right_hands(self):
        """Test that left and right hands have separate buffers."""
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        right_hand_right = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.RIGHT)
        
        # Add actions for both hands
        self.handler.get_action(left_hand_open)
        self.handler.get_action(left_hand_open)
        self.handler.get_action(right_hand_right)
        
        # Check buffers are independent
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 2)
        self.assertEqual(len(self.handler._action_buffers[HandType.RIGHT]), 1)
        
        # Check buffer contents
        self.assertEqual(self.handler._action_buffers[HandType.LEFT][0], CarAction.ACCELERATE)
        self.assertEqual(self.handler._action_buffers[HandType.RIGHT][0], CarAction.DIRECTION_RIGHT)

    def test_get_action_uses_majority_when_available(self):
        """Test that get_action returns majority action from buffer."""
        handler = CarHandler(self.mock_esp32, buffer_size=10)
        left_hand_open = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        left_hand_closed = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        
        # Fill buffer with mostly ACCELERATE actions
        for _ in range(7):
            handler.get_action(left_hand_open)
        # Add fewer STOP actions
        for _ in range(2):
            handler.get_action(left_hand_closed)
        
        # Get action with a STOP gesture (current action would be STOP)
        # But majority should return ACCELERATE
        action = handler.get_action(left_hand_closed)
        
        # The returned action should be based on majority
        self.assertEqual(action, CarAction.ACCELERATE)

    def test_right_hand_buffer_with_direction_changes(self):
        """Test buffering and majority for right hand direction changes."""
        right_hand_left = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.LEFT)
        right_hand_right = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.RIGHT)
        right_hand_straight = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        
        # Add mixed directions with LEFT being majority
        self.handler.get_action(right_hand_left)
        self.handler.get_action(right_hand_left)
        self.handler.get_action(right_hand_left)
        self.handler.get_action(right_hand_right)
        self.handler.get_action(right_hand_straight)
        
        # Next action should be DIRECTION_LEFT (majority)
        action = self.handler.get_action(right_hand_straight)
        self.assertEqual(action, CarAction.DIRECTION_LEFT)


if __name__ == '__main__':
    unittest.main()
