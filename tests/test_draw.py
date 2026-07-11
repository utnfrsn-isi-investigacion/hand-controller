import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import DisplayConfig  # noqa: E402
from draw import Drawer  # noqa: E402
from hand import Hand, HandType  # noqa: E402
from handlers import CarAction  # noqa: E402


class TestDrawer(unittest.TestCase):

    def setUp(self):
        self.frame = Mock()
        self.frame.shape = (480, 640, 3)

    def make_hand(self, hand_type):
        mock_hand = Mock(spec=Hand)
        mock_hand.get_hand_type.return_value = hand_type
        mock_hand.landmarks = Mock()
        return mock_hand

    def draw(self, drawer, hands=(), actions=None, confidences=None, connected=True, fps=30.0):
        provider = (confidences or {}).get
        drawer.draw(self.frame, list(hands), actions or {}, provider, connected, fps)

    @patch('draw.mp_drawing')
    @patch('draw.cv2.putText')
    def test_master_toggle_disables_all_drawing(self, mock_put_text, mock_mp_drawing):
        drawer = Drawer(DisplayConfig(show_overlays=False, show_fps=True))
        hand = self.make_hand(HandType.LEFT)
        self.draw(drawer, [hand], {HandType.LEFT: CarAction.ACCELERATE})
        mock_put_text.assert_not_called()
        mock_mp_drawing.draw_landmarks.assert_not_called()

    @patch('draw.mp_drawing')
    @patch('draw.cv2.putText')
    def test_draws_action_text_with_confidence(self, mock_put_text, mock_mp_drawing):
        drawer = Drawer(DisplayConfig())
        hand = self.make_hand(HandType.LEFT)
        self.draw(drawer, [hand], {HandType.LEFT: CarAction.ACCELERATE}, {HandType.LEFT: 0.8})
        texts = [call.args[1] for call in mock_put_text.call_args_list]
        self.assertIn("ACCELERATE 80%", texts)

    @patch('draw.mp_drawing')
    @patch('draw.cv2.putText')
    def test_confidence_hidden_when_disabled_or_missing(self, mock_put_text, mock_mp_drawing):
        drawer = Drawer(DisplayConfig(show_confidence=False))
        hand = self.make_hand(HandType.LEFT)
        self.draw(drawer, [hand], {HandType.LEFT: CarAction.ACCELERATE}, {HandType.LEFT: 0.8})
        texts = [call.args[1] for call in mock_put_text.call_args_list]
        self.assertIn("ACCELERATE", texts)

        mock_put_text.reset_mock()
        drawer = Drawer(DisplayConfig())
        self.draw(drawer, [hand], {HandType.LEFT: CarAction.ACCELERATE}, {HandType.LEFT: None})
        texts = [call.args[1] for call in mock_put_text.call_args_list]
        self.assertIn("ACCELERATE", texts)

    @patch('draw.mp_drawing')
    @patch('draw.cv2.putText')
    def test_confidence_provider_not_called_when_disabled(self, mock_put_text, mock_mp_drawing):
        """The provider must not run when confidence display (or all overlays) is off."""
        hand = self.make_hand(HandType.LEFT)
        actions = {HandType.LEFT: CarAction.ACCELERATE}

        provider = Mock()
        drawer = Drawer(DisplayConfig(show_confidence=False))
        drawer.draw(self.frame, [hand], actions, provider, True, 30.0)
        provider.assert_not_called()

        provider = Mock()
        drawer = Drawer(DisplayConfig(show_overlays=False))
        drawer.draw(self.frame, [hand], actions, provider, True, 30.0)
        provider.assert_not_called()

    @patch('draw.mp_drawing')
    @patch('draw.cv2.putText')
    def test_landmarks_toggle(self, mock_put_text, mock_mp_drawing):
        hand = self.make_hand(HandType.LEFT)
        actions = {HandType.LEFT: CarAction.STOP}

        self.draw(Drawer(DisplayConfig(show_landmarks=True)), [hand], actions)
        mock_mp_drawing.draw_landmarks.assert_called_once()

        mock_mp_drawing.reset_mock()
        self.draw(Drawer(DisplayConfig(show_landmarks=False)), [hand], actions)
        mock_mp_drawing.draw_landmarks.assert_not_called()

    @patch('draw.mp_drawing')
    @patch('draw.cv2.putText')
    def test_unknown_hands_are_skipped(self, mock_put_text, mock_mp_drawing):
        drawer = Drawer(DisplayConfig())
        hand = self.make_hand(HandType.UNKNOWN)
        self.draw(drawer, [hand], {})
        mock_mp_drawing.draw_landmarks.assert_not_called()
        # Only the connection status is drawn
        self.assertEqual(mock_put_text.call_count, 1)

    @patch('draw.cv2.putText')
    def test_connection_status_text(self, mock_put_text):
        drawer = Drawer(DisplayConfig())

        self.draw(drawer, connected=True)
        self.assertEqual(mock_put_text.call_args_list[0].args[1], "ESP32: connected")

        mock_put_text.reset_mock()
        self.draw(drawer, connected=False)
        self.assertEqual(mock_put_text.call_args_list[0].args[1], "ESP32: disconnected (reconnecting...)")

    @patch('draw.cv2.putText')
    def test_fps_drawn_only_when_enabled(self, mock_put_text):
        self.draw(Drawer(DisplayConfig(show_fps=True)), fps=29.6)
        texts = [call.args[1] for call in mock_put_text.call_args_list]
        self.assertIn("FPS: 30", texts)

        mock_put_text.reset_mock()
        self.draw(Drawer(DisplayConfig(show_fps=False)), fps=29.6)
        texts = [call.args[1] for call in mock_put_text.call_args_list]
        self.assertNotIn("FPS: 30", texts)

    @patch('draw.mp_drawing')
    @patch('draw.cv2.putText')
    def test_hand_colors_come_from_config(self, mock_put_text, mock_mp_drawing):
        config = DisplayConfig(left_hand_color=[10, 20, 30], right_hand_color=[40, 50, 60])
        drawer = Drawer(config)
        left = self.make_hand(HandType.LEFT)
        right = self.make_hand(HandType.RIGHT)
        actions = {HandType.LEFT: CarAction.STOP, HandType.RIGHT: CarAction.DIRECTION_STRAIGHT}
        self.draw(drawer, [left, right], actions)
        colors = [call.args[5] for call in mock_put_text.call_args_list]
        self.assertIn((10, 20, 30), colors)
        self.assertIn((40, 50, 60), colors)


if __name__ == '__main__':
    unittest.main()
