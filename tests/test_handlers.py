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


if __name__ == '__main__':
    unittest.main()
