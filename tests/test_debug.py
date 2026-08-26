import unittest
from unittest.mock import Mock
import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import DebugConfig  # noqa: E402
from debug import DebugReporter  # noqa: E402
from hand import Hand, HandDiagnostics, HandType, IndexOrientation  # noqa: E402
from handlers import CarAction, HandDebug, HandlerDebug  # noqa: E402


def make_hand(diagnostics):
    """A Hand mock that reports the given diagnostics."""
    hand = Mock(spec=Hand)
    hand.diagnostics.return_value = diagnostics
    return hand


def right_hand_diag(offset=0.0, orientation=IndexOrientation.STRAIGHT):
    return HandDiagnostics(
        label="Right", score=0.95, hand_type=HandType.RIGHT, unknown_reason="",
        index_offset=offset, index_threshold=0.05, index_orientation=orientation,
    )


def left_hand_diag(is_open=True):
    return HandDiagnostics(
        label="Left", score=0.95, hand_type=HandType.LEFT, unknown_reason="",
        finger_ratios=[0.9, 1.1, 1.2, 1.0, 0.8], open_threshold=0.6, is_open=is_open,
    )


def unknown_hand_diag(reason="3 landmark(s) out of frame", out_of_frame=(0, 1, 2)):
    return HandDiagnostics(
        label="Left", score=0.99, hand_type=HandType.UNKNOWN, unknown_reason=reason,
        out_of_frame=list(out_of_frame),
    )


def handler_debug(gate_ok=True, missing=(), left=None, right=None, detections=2, unusable=0):
    debug = HandlerDebug(detections=detections, unusable=unusable,
                         gate_ok=gate_ok, missing=list(missing))
    debug.hands[HandType.LEFT] = left or HandDebug(
        detected=True, raw_action=CarAction.ACCELERATE, action=CarAction.ACCELERATE,
        confidence=1.0, sent=True)
    debug.hands[HandType.RIGHT] = right or HandDebug(
        detected=True, raw_action=CarAction.DIRECTION_STRAIGHT, action=CarAction.DIRECTION_STRAIGHT,
        confidence=1.0, sent=True)
    return debug


class TestDebugReporterDisabled(unittest.TestCase):

    def test_disabled_reporter_is_silent_and_draws_nothing(self):
        reporter = DebugReporter(DebugConfig(enabled=False))
        with self.assertNoLogs("debug", level="DEBUG"):
            lines = reporter.report([make_hand(left_hand_diag())], handler_debug(), True, 30.0)
        self.assertEqual(lines, [])

    def test_disabled_reporter_never_computes_diagnostics(self):
        """The expensive landmark passes must not run when debug is off."""
        reporter = DebugReporter(DebugConfig(enabled=False))
        hand = make_hand(left_hand_diag())
        reporter.report([hand], handler_debug(), True, 30.0)
        hand.diagnostics.assert_not_called()


class TestDebugReporterOutput(unittest.TestCase):

    def setUp(self):
        self.reporter = DebugReporter(DebugConfig(enabled=True, log_interval=3600))

    def report(self, hands, debug, connected=True, fps=30.0):
        with self.assertLogs("debug", level="DEBUG") as captured:
            lines = self.reporter.report(hands, debug, connected, fps)
        return "\n".join(captured.output), lines

    def test_blocked_gate_names_the_missing_hand(self):
        debug = handler_debug(
            gate_ok=False, missing=[HandType.RIGHT], detections=1,
            left=HandDebug(detected=False, action=CarAction.STOP, sent=True),
            right=HandDebug(detected=False, action=CarAction.DIRECTION_STRAIGHT, sent=True),
        )
        logged, overlay = self.report([make_hand(left_hand_diag())], debug)

        self.assertIn("missing RIGHT", logged)
        self.assertIn("gestures ignored", logged)
        self.assertIn("default", logged)
        self.assertTrue(any("missing RIGHT" in line for line in overlay))

    def test_unknown_hand_reports_reason_and_landmark_names(self):
        debug = handler_debug(gate_ok=False, missing=[HandType.LEFT], detections=1, unusable=1)
        logged, _ = self.report([make_hand(unknown_hand_diag())], debug)

        self.assertIn("UNKNOWN", logged)
        self.assertIn("out of frame", logged)
        self.assertIn("WRIST", logged)  # landmark 0, named rather than numbered

    def test_open_hand_ratios_are_reported_against_the_threshold(self):
        logged, _ = self.report([make_hand(left_hand_diag(is_open=False))], handler_debug())

        self.assertIn("open=no", logged)
        self.assertIn("thumb 0.90", logged)
        self.assertIn(">0.60", logged)

    def test_index_offset_is_reported_against_the_threshold(self):
        diag = right_hand_diag(offset=-0.12, orientation=IndexOrientation.LEFT)
        logged, _ = self.report([make_hand(diag)], handler_debug())

        self.assertIn("index dx -0.120", logged)
        self.assertIn("LEFT", logged)

    def test_failed_send_is_called_out(self):
        debug = handler_debug(left=HandDebug(detected=True, raw_action=CarAction.ACCELERATE,
                                             action=CarAction.ACCELERATE, confidence=1.0, sent=False))
        logged, overlay = self.report([make_hand(left_hand_diag())], debug)

        self.assertIn("SEND FAILED", logged)
        self.assertTrue(any("SEND FAILED" in line for line in overlay))

    def test_smoothing_shows_raw_and_final_action(self):
        """A gesture outvoted by the buffer is the difference between the two."""
        debug = handler_debug(left=HandDebug(detected=True, raw_action=CarAction.STOP,
                                             action=CarAction.ACCELERATE, confidence=0.8, sent=None))
        logged, _ = self.report([make_hand(left_hand_diag())], debug)

        self.assertIn("raw STOP -> ACCELERATE", logged)
        self.assertIn("vote 80%", logged)
        self.assertIn("not resent (unchanged)", logged)

    def test_disconnected_esp32_is_flagged(self):
        logged, _ = self.report([make_hand(left_hand_diag())], handler_debug(), connected=False)
        self.assertIn("DISCONNECTED", logged)

    def test_panel_can_be_turned_off_without_disabling_logging(self):
        reporter = DebugReporter(DebugConfig(enabled=True, show_panel=False))
        with self.assertLogs("debug", level="DEBUG"):
            lines = reporter.report([make_hand(left_hand_diag())], handler_debug(), True, 30.0)
        self.assertEqual(lines, [])


class TestDebugReporterThrottling(unittest.TestCase):

    def setUp(self):
        # Long interval: only state changes can trigger a second log
        self.reporter = DebugReporter(DebugConfig(enabled=True, log_interval=3600))
        self.hands = [make_hand(left_hand_diag())]

    def test_unchanged_state_is_logged_once(self):
        with self.assertLogs("debug", level="DEBUG") as captured:
            for _ in range(5):
                self.reporter.report(self.hands, handler_debug(), True, 30.0)
        self.assertEqual(len([line for line in captured.output if "frame" in line]), 1)

    def test_changed_action_logs_immediately(self):
        changed = handler_debug(left=HandDebug(detected=True, raw_action=CarAction.STOP,
                                               action=CarAction.STOP, confidence=1.0, sent=True))
        with self.assertLogs("debug", level="DEBUG") as captured:
            self.reporter.report(self.hands, handler_debug(), True, 30.0)
            self.reporter.report(self.hands, changed, True, 30.0)
        self.assertEqual(len([line for line in captured.output if "frame" in line]), 2)

    def test_connection_change_logs_immediately(self):
        with self.assertLogs("debug", level="DEBUG") as captured:
            self.reporter.report(self.hands, handler_debug(), True, 30.0)
            self.reporter.report(self.hands, handler_debug(), False, 30.0)
        self.assertEqual(len([line for line in captured.output if "frame" in line]), 2)

    def test_interval_elapsed_relogs_unchanged_state(self):
        reporter = DebugReporter(DebugConfig(enabled=True, log_interval=0))
        with self.assertLogs("debug", level="DEBUG") as captured:
            reporter.report(self.hands, handler_debug(), True, 30.0)
            reporter.report(self.hands, handler_debug(), True, 30.0)
        self.assertEqual(len([line for line in captured.output if "frame" in line]), 2)


if __name__ == "__main__":
    unittest.main()
