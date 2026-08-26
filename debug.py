"""Pipeline diagnostics for the hand controller.

Turned on with `python main.py --debug` (or `debug.enabled` in config.json).
Nothing moving usually means one specific stage said no: MediaPipe never saw a
usable hand, the all-hands gate fell back to defaults, a gesture missed its
threshold, majority smoothing has not caught up, or the send never left the
socket. DebugReporter prints all of those side by side, per frame, so the
failing stage is visible instead of inferred.

Disabled, every entry point returns immediately: the frame loop pays one
attribute check.
"""
import logging
import time
from enum import Enum
from typing import Any, List, Optional, Sequence, Tuple

from config import DebugConfig
from hand import Hand, HandDiagnostics, HandType
from handlers import HandlerDebug

logger = logging.getLogger(__name__)


def _action_name(action: Optional[Enum]) -> str:
    return action.name if action is not None else "-"


def _hand_summary(index: int, diag: HandDiagnostics) -> str:
    """One line per MediaPipe detection: what it was classified as, and why."""
    head = f"  [{index}] {diag.label} {diag.score:.2f} -> {diag.hand_type.name}"
    if diag.hand_type == HandType.UNKNOWN:
        detail = diag.unknown_reason
        if diag.out_of_frame:
            names = ", ".join(Hand.landmark_name(i) for i in diag.out_of_frame[:4])
            extra = "..." if len(diag.out_of_frame) > 4 else ""
            detail = f"{detail} [{names}{extra}]"
        return f"{head} ({detail})"

    if diag.hand_type == HandType.LEFT:
        ratios = " ".join(
            f"{name} {ratio:.2f}" for name, ratio in zip(Hand.FINGER_NAMES, diag.finger_ratios)
        ) or "no ratios"
        return f"{head} | open={'yes' if diag.is_open else 'no'} ({ratios} vs >{diag.open_threshold:.2f})"

    return (f"{head} | index dx {diag.index_offset:+.3f} vs +-{diag.index_threshold:.3f}"
            f" -> {diag.index_orientation.name}")


def _gate_line(handler_debug: HandlerDebug) -> str:
    """Whether gestures were obeyed at all this frame."""
    if handler_debug.gate_ok:
        return "  gate: both hands present -> gestures in control"
    missing = ", ".join(ht.name for ht in handler_debug.missing) or "none"
    return (f"  gate: missing {missing} -> defaults sent, gestures ignored"
            f" ({handler_debug.detections} detection(s), {handler_debug.unusable} unusable)")


def _sent_label(sent: Optional[bool]) -> str:
    if sent is None:
        return "not resent (unchanged)"
    return "sent" if sent else "SEND FAILED"


def _action_lines(handler_debug: HandlerDebug) -> List[str]:
    """One line per controlled hand type: gesture, smoothing, and send result."""
    lines = []
    for hand_type in (HandType.LEFT, HandType.RIGHT):
        info = handler_debug.hands.get(hand_type)
        if info is None:
            continue
        confidence = f"{info.confidence:.0%}" if info.confidence is not None else "--"
        source = f"raw {_action_name(info.raw_action)} ->" if info.raw_action is not None else "default"
        lines.append(f"  {hand_type.name:<5} {source} {_action_name(info.action)}"
                     f" (vote {confidence}) {_sent_label(info.sent)}")
    return lines


class DebugReporter:
    """Throttled reporter for one frame's worth of pipeline state."""

    def __init__(self, config: DebugConfig):
        self._config = config
        self._frames = 0
        self._last_log = 0.0
        self._last_signature: Optional[Tuple[Any, ...]] = None

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def report(self, hands: Sequence[Hand], handler_debug: HandlerDebug,
               connected: bool, fps: float) -> List[str]:
        """Log the pipeline state and return short lines for the preview overlay.

        Logging is throttled to config.log_interval, but any change in the
        pipeline (gate, actions, send outcome, connection) is logged as soon
        as it happens so transitions are never hidden by the throttle.
        """
        if not self._config.enabled:
            return []

        self._frames += 1
        diagnostics = [hand.diagnostics() for hand in hands]
        signature = self._signature(diagnostics, handler_debug, connected)
        now = time.monotonic()

        if signature != self._last_signature or now - self._last_log >= self._config.log_interval:
            self._last_signature = signature
            self._last_log = now
            for line in self._log_block(diagnostics, handler_debug, connected, fps):
                logger.debug("%s", line)

        return self._overlay_lines(handler_debug) if self._config.show_panel else []

    @staticmethod
    def _signature(diagnostics: Sequence[HandDiagnostics], handler_debug: HandlerDebug,
                   connected: bool) -> Tuple[Any, ...]:
        """State worth logging again. Excludes frame counter, fps and raw
        landmark values, which change every frame and would defeat throttling."""
        hands = tuple(
            (ht, info.detected, _action_name(info.raw_action), _action_name(info.action), info.sent)
            for ht, info in sorted(handler_debug.hands.items(), key=lambda item: item[0].name)
        )
        return (connected, handler_debug.gate_ok, tuple(handler_debug.missing),
                tuple(d.hand_type for d in diagnostics), hands)

    def _log_block(self, diagnostics: Sequence[HandDiagnostics], handler_debug: HandlerDebug,
                   connected: bool, fps: float) -> List[str]:
        header = (f"frame {self._frames} | {fps:.0f} fps |"
                  f" esp32 {'connected' if connected else 'DISCONNECTED'} |"
                  f" {handler_debug.detections} detection(s)")
        lines = [header]
        lines += [_hand_summary(i, diag) for i, diag in enumerate(diagnostics)]
        lines.append(_gate_line(handler_debug))
        lines += _action_lines(handler_debug)
        return lines

    @staticmethod
    def _overlay_lines(handler_debug: HandlerDebug) -> List[str]:
        """Compact version of the same state, for drawing on the preview."""
        if handler_debug.gate_ok:
            lines = ["gate OK: gestures in control"]
        else:
            missing = ", ".join(ht.name for ht in handler_debug.missing) or "none"
            lines = [f"gate BLOCKED: missing {missing} -> defaults"]

        for hand_type in (HandType.LEFT, HandType.RIGHT):
            info = handler_debug.hands.get(hand_type)
            if info is None:
                continue
            confidence = f"{info.confidence:.0%}" if info.confidence is not None else "--"
            raw = _action_name(info.raw_action) if info.raw_action is not None else "default"
            lines.append(f"{hand_type.name[0]}: {raw} -> {_action_name(info.action)}"
                         f" {confidence} {_sent_label(info.sent)}")
        return lines
