import unittest
from unittest.mock import Mock
import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from handlers import CarHandler, CarAction  # noqa: E402
from hand import Hand, HandType, IndexOrientation, VerticalOrientation  # noqa: E402


class TestCarHandler(unittest.TestCase):

    def setUp(self):
        """Set up a mock ESP32 connector and the CarHandler."""
        self.mock_esp32 = Mock()
        self.mock_esp32.send_action.return_value = True
        # Large refresh interval so tests only observe change-driven sends
        self.handler = CarHandler(self.mock_esp32, refresh_interval=3600)

    def create_mock_hand(self, hand_type, is_open, orientation, thumb=VerticalOrientation.UP):
        """Helper to create a mock Hand object with specific properties.

        The thumb orientation defaults to UP, so a closed left hand accelerates.
        """
        mock_hand = Mock(spec=Hand)
        mock_hand.get_hand_type.return_value = hand_type
        mock_hand.is_open.return_value = is_open
        mock_hand.get_index_orientation.return_value = orientation
        mock_hand.get_thumb_orientation.return_value = thumb
        return mock_hand

    def _left(self, thumb):
        """A closed left hand with the given thumb orientation."""
        return self.create_mock_hand(HandType.LEFT, is_open=False,
                                     orientation=IndexOrientation.STRAIGHT, thumb=thumb)

    def _right(self):
        """A right hand pointing straight ahead."""
        return self.create_mock_hand(HandType.RIGHT, is_open=True,
                                     orientation=IndexOrientation.STRAIGHT)

    def test_left_hand_accelerate(self):
        """Test that a left thumbs-up triggers ACCELERATE."""
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        right_hand = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        self.handler.process_hands([left_accelerate, right_hand])
        # It should send ACCELERATE for the left hand and STRAIGHT for the right hand
        self.mock_esp32.send_action.assert_any_call(CarAction.ACCELERATE.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_STRAIGHT.value)
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

    def test_left_hand_stop(self):
        """Test that an open left palm triggers STOP."""
        left_stop = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)
        right_hand = self.create_mock_hand(HandType.RIGHT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        self.handler.process_hands([left_stop, right_hand])
        self.mock_esp32.send_action.assert_any_call(CarAction.STOP.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_STRAIGHT.value)
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

    def test_left_hand_reverse(self):
        """A left thumbs-down triggers REVERSE."""
        self.handler.process_hands([self._left(VerticalOrientation.DOWN), self._right()])
        self.mock_esp32.send_action.assert_any_call(CarAction.REVERSE.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_STRAIGHT.value)
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

    def test_left_hand_neutral_thumb_stops(self):
        """A sideways thumb lands in the dead band and stops."""
        self.handler.process_hands([self._left(VerticalOrientation.NEUTRAL), self._right()])
        self.mock_esp32.send_action.assert_any_call(CarAction.STOP.value)
        self.assertNotIn(
            ((CarAction.ACCELERATE.value,),),
            [(c.args,) for c in self.mock_esp32.send_action.call_args_list])

    def test_open_palm_stops_regardless_of_thumb(self):
        """The open-palm fast path wins over thumb orientation, thumb down included."""
        for thumb in (VerticalOrientation.UP, VerticalOrientation.DOWN, VerticalOrientation.NEUTRAL):
            with self.subTest(thumb=thumb):
                handler = CarHandler(self.mock_esp32, refresh_interval=3600)
                palm = self.create_mock_hand(HandType.LEFT, is_open=True,
                                             orientation=IndexOrientation.STRAIGHT, thumb=thumb)
                actions = handler.process_hands([palm, self._right()])
                self.assertEqual(actions[HandType.LEFT], CarAction.STOP)

    def test_plain_fist_stops(self):
        """A closed hand with the thumb sideways is the neutral pose and stops."""
        actions = self.handler.process_hands(
            [self._left(VerticalOrientation.NEUTRAL), self._right()])
        self.assertEqual(actions[HandType.LEFT], CarAction.STOP)

    def _rotate_down(self, neutral_frames, buffer_size=10):
        """Saturate the buffer with ACCELERATE, then rotate down through NEUTRAL.

        Returns the actions emitted while crossing and settling.
        """
        handler = CarHandler(self.mock_esp32, buffer_size=buffer_size, refresh_interval=3600)
        right = self._right()
        for _ in range(buffer_size):
            handler.process_hands([self._left(VerticalOrientation.UP), right])
        self.assertEqual(handler.get_action(self._left(VerticalOrientation.UP)), CarAction.ACCELERATE)

        palms = [VerticalOrientation.NEUTRAL] * neutral_frames + [VerticalOrientation.DOWN] * 12
        return [handler.process_hands([self._left(p), right])[HandType.LEFT] for p in palms]

    def test_unhurried_rotation_stops_before_reversing(self):
        """A hand that dwells in the neutral band stops before REVERSE takes over."""
        seen = self._rotate_down(neutral_frames=6)
        self.assertIn(CarAction.STOP, seen)
        self.assertEqual(seen[-1], CarAction.REVERSE)
        self.assertLess(seen.index(CarAction.STOP), seen.index(CarAction.REVERSE))

    def test_neutral_band_interlock_needs_a_quarter_of_the_buffer(self):
        """Pins how soft the forward/reverse interlock actually is.

        STOP only reaches the wire if the neutral crossing outvotes both
        neighbours in the buffer, which takes a quarter of it -- 4 frames at
        the default size of 10. This is a documented limitation, not a
        guarantee: a faster flick emits ACCELERATE then REVERSE back to back.
        The motor survives that because the firmware refuses the reversal
        until it has been stopped for REVERSAL_DWELL_MS (see
        tests/test_firmware_safety.py), not because of anything here.
        """
        for neutral_frames in (0, 1, 2, 3):
            with self.subTest(neutral_frames=neutral_frames, expected="no stop"):
                self.assertNotIn(CarAction.STOP, self._rotate_down(neutral_frames))

        for neutral_frames in (4, 5, 6):
            with self.subTest(neutral_frames=neutral_frames, expected="stops"):
                self.assertIn(CarAction.STOP, self._rotate_down(neutral_frames))

    def test_interlock_threshold_scales_with_buffer_size(self):
        """The frames needed to force a STOP track buffer_size, not a constant."""
        # 4 neutral frames are enough at the default size but not at 20
        self.assertIn(CarAction.STOP, self._rotate_down(4, buffer_size=10))
        self.assertNotIn(CarAction.STOP, self._rotate_down(4, buffer_size=20))
        self.assertIn(CarAction.STOP, self._rotate_down(8, buffer_size=20))

    def test_right_hand_direction_right(self):
        """Test right hand direction controls: RIGHT orientation."""
        right_hand_right = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.RIGHT)
        left_hand = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.LEFT)
        self.handler.process_hands([right_hand_right, left_hand])
        self.mock_esp32.send_action.assert_any_call(CarAction.STOP.value)
        self.mock_esp32.send_action.assert_any_call(CarAction.DIRECTION_RIGHT.value)

    def test_right_hand_direction_left(self):
        """Test right hand direction controls: LEFT orientation."""
        right_hand_left = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.LEFT)
        left_hand = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.LEFT)
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
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        right_hand_right = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.RIGHT)
        actions = self.handler.process_hands([left_accelerate, right_hand_right])
        self.assertEqual(actions[HandType.LEFT], CarAction.ACCELERATE)
        self.assertEqual(actions[HandType.RIGHT], CarAction.DIRECTION_RIGHT)

    def test_single_hand_uses_defaults_and_keeps_buffers_clean(self):
        """Test that with only one hand detected, defaults are used and buffers stay empty."""
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        actions = self.handler.process_hands([left_accelerate])
        self.assertEqual(actions[HandType.LEFT], CarAction.STOP)
        self.assertEqual(actions[HandType.RIGHT], CarAction.DIRECTION_STRAIGHT)
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 0)
        self.assertEqual(len(self.handler._action_buffers[HandType.RIGHT]), 0)

    def test_action_sent_only_once_when_unchanged(self):
        """Test that the same actions are not sent repeatedly."""
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)

        # First call should send actions
        self.handler.process_hands([left_accelerate])
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

        # Subsequent calls with the same state should not send more actions
        self.handler.process_hands([left_accelerate])
        self.handler.process_hands([left_accelerate])
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

    def test_unchanged_action_resent_after_refresh_interval(self):
        """Test the keepalive: unchanged actions are resent once the refresh interval elapses."""
        handler = CarHandler(self.mock_esp32, refresh_interval=0)
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)

        handler.process_hands([left_accelerate])
        self.assertEqual(self.mock_esp32.send_action.call_count, 2)

        # Same state, but refresh_interval=0 means every call resends
        handler.process_hands([left_accelerate])
        self.assertEqual(self.mock_esp32.send_action.call_count, 4)

    def test_failed_send_is_retried_until_success(self):
        """Test that actions keep being attempted while sending fails."""
        self.mock_esp32.send_action.return_value = False
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)

        self.handler.process_hands([left_accelerate])
        self.handler.process_hands([left_accelerate])
        # Failed sends are not recorded as "last action", so both frames retry
        self.assertEqual(self.mock_esp32.send_action.call_count, 4)

        # Once sending succeeds, the action is recorded and no longer resent
        self.mock_esp32.send_action.return_value = True
        self.handler.process_hands([left_accelerate])
        self.assertEqual(self.mock_esp32.send_action.call_count, 6)
        self.handler.process_hands([left_accelerate])
        self.assertEqual(self.mock_esp32.send_action.call_count, 6)

    def test_get_action_is_read_only(self):
        """Test that get_action does not modify the action buffers."""
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)

        action = self.handler.get_action(left_accelerate)

        self.assertEqual(action, CarAction.ACCELERATE)
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 0)

    def test_record_action_populates_buffer(self):
        """Test that _record_action adds actions to the buffer and returns the correct action."""
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)

        # Initially buffer should be empty
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 0)

        action = self.handler._record_action(left_accelerate)

        # Buffer should now have one element and action should be correct
        self.assertEqual(len(self.handler._action_buffers[HandType.LEFT]), 1)
        self.assertEqual(action, CarAction.ACCELERATE)

    def test_unknown_hand_does_not_crash(self):
        """Test that UNKNOWN hands are handled without touching (missing) buffers."""
        unknown_hand = self.create_mock_hand(HandType.UNKNOWN, is_open=True, orientation=IndexOrientation.STRAIGHT)

        self.assertEqual(self.handler._record_action(unknown_hand), CarAction.STOP)
        self.assertEqual(self.handler.get_action(unknown_hand), CarAction.STOP)
        self.assertIsNone(self.handler._majority_action(unknown_hand))

    def test_stop_is_smoothed_like_any_other_action(self):
        """STOP gets no special treatment: it must win the majority vote to take effect."""
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        left_stop = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        # Fill the buffer with ACCELERATE
        for _ in range(10):
            self.handler._record_action(left_accelerate)

        # A single closed-hand frame is outvoted by the ACCELERATE majority
        self.assertEqual(self.handler._record_action(left_stop), CarAction.ACCELERATE)
        # The read-only path agrees
        self.assertEqual(self.handler.get_action(left_stop), CarAction.ACCELERATE)

        # Once closed frames outnumber the open ones, STOP wins
        for _ in range(10):
            self.handler._record_action(left_stop)
        self.assertEqual(self.handler._record_action(left_stop), CarAction.STOP)

    def test_accelerate_still_smoothed_by_majority(self):
        """One open frame can't override a STOP majority."""
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        left_stop = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        # Fill the buffer with STOP
        for _ in range(10):
            self.handler._record_action(left_stop)

        # A single open-hand frame is outvoted by the STOP majority
        action = self.handler._record_action(left_accelerate)
        self.assertEqual(action, CarAction.STOP)

    def test_buffer_respects_max_size(self):
        """Test that buffer doesn't exceed the specified max size."""
        handler = CarHandler(self.mock_esp32, buffer_size=5)
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)

        # Add more actions than buffer size
        for _ in range(10):
            handler._record_action(left_accelerate)

        # Buffer should only contain buffer_size elements
        self.assertEqual(len(handler._action_buffers[HandType.LEFT]), 5)

    def test_buffer_fifo_behavior(self):
        """Test that buffer uses FIFO (first in, first out) behavior."""
        handler = CarHandler(self.mock_esp32, buffer_size=3)
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        left_stop = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        # Add 2 STOP actions
        handler._record_action(left_stop)
        handler._record_action(left_stop)

        # Add 3 ACCELERATE actions (should push out the STOP actions)
        handler._record_action(left_accelerate)
        handler._record_action(left_accelerate)
        action = handler._record_action(left_accelerate)

        # After buffer fills and old actions are pushed out, should return ACCELERATE
        self.assertEqual(action, CarAction.ACCELERATE)

    def test_separate_buffers_for_left_and_right_hands(self):
        """Test that left and right hands have separate buffers."""
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        right_hand_right = self.create_mock_hand(HandType.RIGHT, is_open=True, orientation=IndexOrientation.RIGHT)

        # Add actions for both hands
        self.handler._record_action(left_accelerate)
        self.handler._record_action(left_accelerate)
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

    def test_action_confidence_reflects_buffer_share(self):
        """Test that get_action_confidence returns the winning action's buffer share."""
        left_accelerate = self.create_mock_hand(HandType.LEFT, is_open=False, orientation=IndexOrientation.STRAIGHT)
        left_stop = self.create_mock_hand(HandType.LEFT, is_open=True, orientation=IndexOrientation.STRAIGHT)

        # Empty buffer -> no confidence
        self.assertIsNone(self.handler.get_action_confidence(HandType.LEFT))
        # Unknown hand type has no buffer -> no confidence
        self.assertIsNone(self.handler.get_action_confidence(HandType.UNKNOWN))

        # 4 ACCELERATE + 1 STOP -> 80% confidence
        for _ in range(4):
            self.handler._record_action(left_accelerate)
        self.handler._record_action(left_stop)
        self.assertEqual(self.handler.get_action_confidence(HandType.LEFT), 0.8)

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
