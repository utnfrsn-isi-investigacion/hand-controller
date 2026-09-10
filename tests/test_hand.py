import math
import unittest
from unittest.mock import Mock
import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hand import Hand, HandType, IndexOrientation, VerticalOrientation  # noqa: E402
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

    def test_has_usable_geometry(self):
        """Landmarks collapsed onto each other cannot be measured at all."""
        landmarks_data = [(0.0, 0.0, 0.0)] * 21
        landmarks_data[mp_hands.HandLandmark.WRIST] = (0.5, 0.9, 0.0)
        landmarks_data[mp_hands.HandLandmark.MIDDLE_FINGER_MCP] = (0.5, 0.7, 0.0)
        self.assertTrue(self.create_mock_hand(landmarks_data).has_usable_geometry())

        # Wrist and middle knuckle on the same point: hand size is zero, so
        # every ratio and angle taken from these points is noise.
        self.assertFalse(self.create_mock_hand([(0.5, 0.5, 0.0)] * 21).has_usable_geometry())

    def test_degenerate_hand_is_not_open(self):
        """is_open() warns and refuses rather than dividing by zero."""
        degenerate = self.create_mock_hand([(0.5, 0.5, 0.0)] * 21)
        with self.assertLogs('hand', level='WARNING'):
            self.assertFalse(degenerate.is_open())

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

    def _thumb_hand(self, pitch_deg, **kwargs):
        """A hand whose index-knuckle -> thumb-tip vector sits at the given pitch."""
        radians = math.radians(pitch_deg)
        landmarks_data = [(0.0, 0.0, 0.0)] * 21
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.5, 0.5, 0.0)
        landmarks_data[mp_hands.HandLandmark.THUMB_TIP] = (
            0.5 + 0.2 * math.sin(radians), 0.5 - 0.2 * math.cos(radians), 0.0)
        hand = self.create_mock_hand(landmarks_data)
        if kwargs:
            return Hand(handedness=hand.handedness, landmarks=hand.landmarks, **kwargs)
        return hand

    def test_get_thumb_pitch(self):
        """Pitch is 0 with the thumb up, 90 sideways, 180 pointing down."""
        for pitch in (0.0, 45.0, 90.0, 135.0, 180.0):
            with self.subTest(pitch=pitch):
                self.assertAlmostEqual(self._thumb_hand(pitch).get_thumb_pitch(), pitch, places=4)

    def test_get_thumb_pitch_ignores_horizontal_direction(self):
        """A thumb leaning left or right by the same amount reads the same.

        The x component is taken as an absolute value, so the measure survives
        the frame mirroring and works for either hand.
        """
        landmarks_data = [(0.0, 0.0, 0.0)] * 21
        landmarks_data[mp_hands.HandLandmark.INDEX_FINGER_MCP] = (0.5, 0.5, 0.0)
        landmarks_data[mp_hands.HandLandmark.THUMB_TIP] = (0.6, 0.4, 0.0)
        leaning_right = self.create_mock_hand(landmarks_data)
        landmarks_data[mp_hands.HandLandmark.THUMB_TIP] = (0.4, 0.4, 0.0)
        leaning_left = self.create_mock_hand(landmarks_data)
        self.assertAlmostEqual(leaning_right.get_thumb_pitch(),
                               leaning_left.get_thumb_pitch(), places=4)

    def test_get_thumb_orientation(self):
        """The three bands map to UP, NEUTRAL and DOWN."""
        self.assertEqual(self._thumb_hand(0).get_thumb_orientation(), VerticalOrientation.UP)
        self.assertEqual(self._thumb_hand(100).get_thumb_orientation(), VerticalOrientation.NEUTRAL)
        self.assertEqual(self._thumb_hand(180).get_thumb_orientation(), VerticalOrientation.DOWN)

    def test_thumb_band_edges_are_inclusive(self):
        """A thumb exactly on a threshold belongs to the outer band, not NEUTRAL.

        Compared against the hand's own measured pitch rather than the angle it
        was built from, since reconstructing landmarks from an angle and
        re-deriving it does not round-trip exactly.
        """
        hand = self._thumb_hand(120)
        edge = hand.get_thumb_pitch()
        self.assertEqual(hand.get_thumb_orientation(up_threshold_deg=edge,
                                                    down_threshold_deg=180.0),
                         VerticalOrientation.UP)
        self.assertEqual(hand.get_thumb_orientation(up_threshold_deg=0.0,
                                                    down_threshold_deg=edge),
                         VerticalOrientation.DOWN)
        # Just inside the band on both sides
        self.assertEqual(hand.get_thumb_orientation(up_threshold_deg=edge - 1,
                                                    down_threshold_deg=edge + 1),
                         VerticalOrientation.NEUTRAL)

    def test_get_thumb_orientation_respects_configured_thresholds(self):
        """Constructor thresholds move the band edges; per-call values override them."""
        self.assertEqual(self._thumb_hand(60).get_thumb_orientation(), VerticalOrientation.UP)

        strict = self._thumb_hand(60, thumb_up_threshold_deg=40.0,
                                  thumb_down_threshold_deg=135.0)
        self.assertEqual(strict.get_thumb_orientation(), VerticalOrientation.NEUTRAL)

        # A per-call threshold overrides the configured one
        self.assertEqual(strict.get_thumb_orientation(up_threshold_deg=70.0),
                         VerticalOrientation.UP)

    def test_measured_poses_land_in_the_right_bands(self):
        """The angles recorded from real hands classify as intended.

        Held poses measured ~33 degrees (thumbs up), ~112 (plain fist) and
        ~158 (thumbs down), against band edges at 70 and 135.
        """
        for pitch, expected in ((33.3, VerticalOrientation.UP),
                                (111.9, VerticalOrientation.NEUTRAL),
                                (158.3, VerticalOrientation.DOWN)):
            with self.subTest(pitch=pitch):
                hand = self._thumb_hand(pitch)
                self.assertAlmostEqual(hand.get_thumb_pitch(), pitch, places=3)
                self.assertEqual(hand.get_thumb_orientation(), expected)


if __name__ == '__main__':
    unittest.main()
