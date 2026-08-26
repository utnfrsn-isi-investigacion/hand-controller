import unittest
from unittest.mock import Mock
import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hand import Hand, HandType, IndexOrientation  # noqa: E402
import mediapipe as mp  # noqa: E402

mp_hands = mp.solutions.hands  # type: ignore[attr-defined]


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

    def test_is_open_respects_configured_threshold(self):
        """Test that the constructor threshold changes the is_open outcome."""
        landmarks_data = [(0.0, 0.0, 0.0)] * 21
        landmarks_data[mp_hands.HandLandmark.WRIST] = (0.5, 0.9, 0.0)
        landmarks_data[mp_hands.HandLandmark.MIDDLE_FINGER_MCP] = (0.5, 0.7, 0.0)
        landmarks_data[mp_hands.HandLandmark.THUMB_TIP] = (0.3, 0.5, 0.0)
        landmarks_data[mp_hands.HandLandmark.THUMB_CMC] = (0.35, 0.7, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_TIP] = (0.4, 0.2, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.4, 0.7, 0.0)
        landmarks_data[mp_hands.HandLandmark.MIDDLE_FINGER_TIP] = (0.5, 0.2, 0.0)
        landmarks_data[mp_hands.HandLandmark.RING_FINGER_TIP] = (0.6, 0.2, 0.0)
        landmarks_data[mp_hands.HandLandmark.RING_FINGER_MCP] = (0.6, 0.7, 0.0)
        landmarks_data[mp_hands.HandLandmark.PINKY_TIP] = (0.7, 0.2, 0.0)
        landmarks_data[mp_hands.HandLandmark.PINKY_MCP] = (0.7, 0.7, 0.0)

        open_hand = self.create_mock_hand(landmarks_data)
        self.assertTrue(open_hand.is_open())

        # The same landmarks fail with an absurdly strict configured threshold
        strict_hand = Hand(
            handedness=open_hand.handedness,
            landmarks=open_hand.landmarks,
            open_threshold_ratio=100.0
        )
        self.assertFalse(strict_hand.is_open())

        # A per-call threshold overrides the configured one
        self.assertTrue(strict_hand.is_open(threshold_ratio=0.6))

    def test_get_index_orientation(self):
        """Test the index finger orientation logic on a mirrored (selfie-view) frame."""
        landmarks_data = [(0.0, 0.0, 0.0)] * 21

        # Pointing Left -> Tip X is LESS than Base X (mirrored view)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_TIP] = (0.3, 0.5, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.4, 0.5, 0.0)
        hand_pointing_left = self.create_mock_hand(landmarks_data)
        self.assertEqual(hand_pointing_left.get_index_orientation(), IndexOrientation.LEFT)

        # Pointing Right -> Tip X is GREATER than Base X (mirrored view)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_TIP] = (0.5, 0.5, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.4, 0.5, 0.0)
        hand_pointing_right = self.create_mock_hand(landmarks_data)
        self.assertEqual(hand_pointing_right.get_index_orientation(), IndexOrientation.RIGHT)

        # Pointing Straight
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_TIP] = (0.4, 0.5, 0.0)
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.4, 0.5, 0.0)
        hand_pointing_straight = self.create_mock_hand(landmarks_data)
        self.assertEqual(hand_pointing_straight.get_index_orientation(), IndexOrientation.STRAIGHT)


class TestHandDiagnostics(unittest.TestCase):
    """diagnostics() must explain the classification, not just repeat it."""

    def create_mock_hand(self, landmarks_data, hand_label="Right", score=0.9):
        mock_classification = Mock()
        mock_classification.label = hand_label
        mock_classification.score = score
        mock_handedness = Mock()
        mock_handedness.classification = [mock_classification]
        landmarks = [MockLandmark(x, y, z) for x, y, z in landmarks_data]
        return Hand(handedness=mock_handedness, landmarks=MockLandmarkList(landmarks))

    def open_hand_data(self):
        """Landmarks for a clearly open hand, centered in frame."""
        data = [(0.5, 0.5, 0.0)] * 21
        data[mp_hands.HandLandmark.WRIST] = (0.5, 0.9, 0.0)
        data[mp_hands.HandLandmark.MIDDLE_FINGER_MCP] = (0.5, 0.7, 0.0)
        data[mp_hands.HandLandmark.THUMB_TIP] = (0.3, 0.5, 0.0)
        data[mp_hands.HandLandmark.THUMB_CMC] = (0.35, 0.7, 0.0)
        data[mp_hands.HandLandmark.INDEX_FINGER_TIP] = (0.4, 0.2, 0.0)
        data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.4, 0.7, 0.0)
        data[mp_hands.HandLandmark.MIDDLE_FINGER_TIP] = (0.5, 0.2, 0.0)
        data[mp_hands.HandLandmark.RING_FINGER_TIP] = (0.6, 0.2, 0.0)
        data[mp_hands.HandLandmark.RING_FINGER_MCP] = (0.6, 0.7, 0.0)
        data[mp_hands.HandLandmark.PINKY_TIP] = (0.7, 0.2, 0.0)
        data[mp_hands.HandLandmark.PINKY_MCP] = (0.7, 0.7, 0.0)
        return data

    def test_reports_ratios_agreeing_with_is_open(self):
        hand = self.create_mock_hand(self.open_hand_data())
        diag = hand.diagnostics()

        self.assertEqual(len(diag.finger_ratios), len(Hand.FINGER_NAMES))
        self.assertTrue(diag.is_open)
        self.assertEqual(diag.is_open, hand.is_open())
        self.assertTrue(all(ratio > diag.open_threshold for ratio in diag.finger_ratios))

    def test_reports_index_offset_agreeing_with_orientation(self):
        data = self.open_hand_data()
        data[mp_hands.HandLandmark.INDEX_FINGER_TIP] = (0.2, 0.2, 0.0)  # tip well left of knuckle
        hand = self.create_mock_hand(data)
        diag = hand.diagnostics()

        self.assertAlmostEqual(diag.index_offset, -0.2)
        self.assertEqual(diag.index_orientation, IndexOrientation.LEFT)
        self.assertEqual(diag.index_orientation, hand.get_index_orientation())

    def test_clipped_hand_reports_which_landmarks_left_the_frame(self):
        data = self.open_hand_data()
        data[mp_hands.HandLandmark.WRIST] = (0.5, 1.05, 0.0)  # below the bottom edge
        hand = self.create_mock_hand(data)
        diag = hand.diagnostics()

        self.assertEqual(diag.hand_type, HandType.UNKNOWN)
        self.assertEqual(diag.out_of_frame, [int(mp_hands.HandLandmark.WRIST)])
        self.assertIn("out of frame", diag.unknown_reason)
        self.assertEqual(Hand.landmark_name(0), "WRIST")

    def test_low_handedness_score_is_reported_with_the_number(self):
        hand = self.create_mock_hand(self.open_hand_data(), score=0.55)
        diag = hand.diagnostics()

        self.assertEqual(diag.hand_type, HandType.UNKNOWN)
        self.assertIn("0.55", diag.unknown_reason)
        self.assertEqual(diag.out_of_frame, [])

    def test_usable_hand_has_no_unknown_reason(self):
        diag = self.create_mock_hand(self.open_hand_data(), hand_label="Left").diagnostics()

        self.assertEqual(diag.hand_type, HandType.LEFT)
        self.assertEqual(diag.unknown_reason, "")


if __name__ == '__main__':
    unittest.main()
