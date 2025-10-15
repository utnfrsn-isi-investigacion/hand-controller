import unittest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hand import Hand, HandType, IndexOrientation
import mediapipe as mp

mp_hands = mp.solutions.hands # type: ignore[attr-defined]

# Mock for a single landmark
class MockLandmark:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

# Mock for the entire landmark list
class MockLandmarkList:
    def __init__(self, landmarks):
        self.landmark = landmarks

class TestHand(unittest.TestCase):

    def create_mock_hand(self, landmarks_data, hand_label="Right", score=0.9):
        """Helper to create a Hand instance with mock data."""
        mock_classification = Mock()
        mock_classification.label = hand_label
        mock_classification.score = score
        mock_handedness = Mock()
        mock_handedness.classification = [mock_classification]

        landmarks = [MockLandmark(x, y, z) for x, y, z in landmarks_data]
        mock_landmark_list = MockLandmarkList(landmarks)

        return Hand(handedness=mock_handedness, landmarks=mock_landmark_list)

    def test_get_hand_type(self):
        """Test that the correct hand type is identified."""
        landmarks_data = [(0.5, 0.5, 0)] * 21

        hand_right = self.create_mock_hand(landmarks_data, hand_label="Right")
        self.assertEqual(hand_right.get_hand_type(), HandType.RIGHT)

        hand_left = self.create_mock_hand(landmarks_data, hand_label="Left")
        self.assertEqual(hand_left.get_hand_type(), HandType.LEFT)

    def test_is_open(self):
        """Test the is_open logic with a clearly open hand."""
        landmarks_data = [(0.0, 0.0, 0.0)] * 21
        # Set wrist and MCPs
        landmarks_data[mp_hands.HandLandmark.WRIST] = (0.5, 0.9, 0.0)
        landmarks_data[mp_hands.HandLandmark.MIDDLE_FINGER_MCP] = (0.5, 0.7, 0.0)
        # Set finger tips far from MCPs
        landmarks_data[mp_hands.HandLandmark.THUMB_TIP] = (0.3, 0.5, 0.0)
        landmarks_data[mp_hands.HandLandmark.THUMB_CMC] = (0.35, 0.7, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_TIP] = (0.4, 0.2, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.4, 0.7, 0.0)
        landmarks_data[mp_hands.HandLandmark.MIDDLE_FINGER_TIP] = (0.5, 0.2, 0.0)
        landmarks_data[mp_hands.HandLandmark.RING_FINGER_TIP] = (0.6, 0.2, 0.0)
        landmarks_data[mp_hands.HandLandmark.RING_FINGER_MCP] = (0.6, 0.7, 0.0)
        landmarks_data[mp_hands.HandLandmark.PINKY_TIP] = (0.7, 0.2, 0.0)
        landmarks_data[mp_hands.HandLandmark.PINKY_MCP] = (0.7, 0.7, 0.0)

        hand = self.create_mock_hand(landmarks_data)
        self.assertTrue(hand.is_open())

    def test_is_closed(self):
        """Test the is_open logic with a clearly closed hand (fist)."""
        landmarks_data = [(0.0, 0.0, 0.0)] * 21
        # Set wrist and MCPs
        landmarks_data[mp_hands.HandLandmark.WRIST] = (0.5, 0.9, 0.0)
        landmarks_data[mp_hands.HandLandmark.MIDDLE_FINGER_MCP] = (0.5, 0.7, 0.0)
        # Set finger tips close to MCPs
        landmarks_data[mp_hands.HandLandmark.THUMB_TIP] = (0.48, 0.72, 0.0)
        landmarks_data[mp_hands.HandLandmark.THUMB_CMC] = (0.5, 0.8, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_TIP] = (0.4, 0.68, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.4, 0.7, 0.0)
        landmarks_data[mp_hands.HandLandmark.MIDDLE_FINGER_TIP] = (0.5, 0.68, 0.0)
        landmarks_data[mp_hands.HandLandmark.RING_FINGER_TIP] = (0.6, 0.68, 0.0)
        landmarks_data[mp_hands.HandLandmark.RING_FINGER_MCP] = (0.6, 0.7, 0.0)
        landmarks_data[mp_hands.HandLandmark.PINKY_TIP] = (0.7, 0.68, 0.0)
        landmarks_data[mp_hands.HandLandmark.PINKY_MCP] = (0.7, 0.7, 0.0)

        hand = self.create_mock_hand(landmarks_data)
        self.assertFalse(hand.is_open())

    def test_get_index_orientation(self):
        """Test the index finger orientation logic. MediaPipe's X-axis is inverted."""
        landmarks_data = [(0.0, 0.0, 0.0)] * 21

        # Pointing Right (for a Right hand) -> Tip X is LESS than Base X
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_TIP] = (0.3, 0.5, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.4, 0.5, 0.0)
        hand_pointing_right = self.create_mock_hand(landmarks_data)
        self.assertEqual(hand_pointing_right.get_index_orientation(), IndexOrientation.RIGHT)

        # Pointing Left (for a Right hand) -> Tip X is GREATER than Base X
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_TIP] = (0.5, 0.5, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.4, 0.5, 0.0)
        hand_pointing_left = self.create_mock_hand(landmarks_data)
        self.assertEqual(hand_pointing_left.get_index_orientation(), IndexOrientation.LEFT)

        # Pointing Straight
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_TIP] = (0.4, 0.5, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.4, 0.5, 0.0)
        hand_pointing_straight = self.create_mock_hand(landmarks_data)
        self.assertEqual(hand_pointing_straight.get_index_orientation(), IndexOrientation.STRAIGHT)

if __name__ == '__main__':
    unittest.main()