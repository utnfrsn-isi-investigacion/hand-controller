"""Guards the firmware-side reversal interlock.

Reversing a motor that is still spinning is what kills the H-bridge, so the
firmware refuses a drive command that opposes the current direction until the
motor has sat stopped for REVERSAL_DWELL_MS. The Python client cannot carry
that guarantee -- the ESP32 serves whatever TCP client connects, and the
gesture smoothing only produces a stop of a few frames -- so these tests pin
the ways the firmware could silently lose it: the constant shrinking below a
spin-down, a drive handler writing the motor pins directly instead of going
through engageDrive(), and the stop clock being restarted by the keepalive.

They read the firmware sources as text, the way test_protocol.py does: nothing
here is compiled by CI, so a lost interlock would otherwise only show up as a
dead H-bridge on the bench.
"""
import os
import re
import sys
import unittest

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

_FIRMWARE_DIR = os.path.join(os.path.dirname(__file__), '..', '_esp32', 'main')
_CONFIG_H = os.path.join(_FIRMWARE_DIR, 'config.h')
_MAIN_INO = os.path.join(_FIRMWARE_DIR, 'main.ino')

# const unsigned long REVERSAL_DWELL_MS = 3000;
_DWELL_RE = re.compile(r'const\s+unsigned\s+long\s+REVERSAL_DWELL_MS\s*=\s*(\d+)\s*;')
# The body of a top-level function definition, up to the closing brace in
# column 0. Anchored at the start of a line so call sites do not match.
_FUNCTION_BODY_RE = r'^(?:\w+\s+)+{name}\s*\([^)]*\)\s*\{{(.*?)\n\}}'

# The mechanical spin-down this has to cover is a matter of seconds; anything
# below this would be back to protecting only against the electrical transient.
_MIN_DWELL_MS = 1000


def _read(path):
    with open(path, 'r') as f:
        return f.read()


def _function_body(source, name):
    match = re.search(_FUNCTION_BODY_RE.format(name=name), source, re.DOTALL | re.MULTILINE)
    return match.group(1) if match else None


class TestReversalInterlock(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = _read(_CONFIG_H)
        cls.main = _read(_MAIN_INO)

    def test_dwell_constant_covers_a_spin_down(self):
        """The dwell exists and is still seconds-scale."""
        match = _DWELL_RE.search(self.config)
        self.assertIsNotNone(match, f"REVERSAL_DWELL_MS not found in {_CONFIG_H}")
        self.assertGreaterEqual(
            int(match.group(1)), _MIN_DWELL_MS,
            "REVERSAL_DWELL_MS is too short to cover the motor spinning down")

    def test_drive_handlers_go_through_engage_drive(self):
        """accelerate() and reverse() must not touch the motor pins directly.

        A direct digitalWrite(MOTOR_PIN_*) in either handler drives the bridge
        without consulting the dwell, which is exactly the failure this
        interlock exists to prevent.
        """
        for name in ('accelerate', 'reverse'):
            with self.subTest(handler=name):
                body = _function_body(self.main, name)
                self.assertIsNotNone(body, f"handler {name}() not found in {_MAIN_INO}")
                self.assertIn('engageDrive(', body, f"{name}() bypasses the reversal dwell")
                self.assertNotIn('digitalWrite(MOTOR_PIN_', body,
                                 f"{name}() writes the motor pins directly")

    def test_engage_drive_consults_the_dwell(self):
        """Guard against the interlock being reduced to a state assignment."""
        body = _function_body(self.main, 'engageDrive')
        self.assertIsNotNone(body, f"engageDrive() not found in {_MAIN_INO}")
        self.assertIn('REVERSAL_DWELL_MS', body, "engageDrive() no longer applies the dwell")

    def test_stop_clock_only_restarts_on_the_transition(self):
        """applyStop() must stamp the clock only when it was actually driving.

        The client resends the current action every refresh_interval, so an
        unconditional stamp would restart the dwell on every repeated STOP and
        the opposite direction would never engage.
        """
        body = _function_body(self.main, 'applyStop')
        self.assertIsNotNone(body, f"applyStop() not found in {_MAIN_INO}")
        self.assertRegex(
            body, r'if\s*\(\s*driveState\s*!=\s*DRIVE_STOPPED\s*\)[^}]*driveStoppedAtMs\s*=',
            "applyStop() stamps driveStoppedAtMs outside the transition guard")


if __name__ == '__main__':
    unittest.main()
