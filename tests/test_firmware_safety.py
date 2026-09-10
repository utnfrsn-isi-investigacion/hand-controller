"""Guards the .ino glue around the firmware's drive state machine.

The reversal interlock itself -- the dwell, its latch, the stop clock -- lives
in _esp32/lib/DriveControl and runs on the host under Unity
(_esp32/test/test_drive, `make test-firmware`), compiled and executed by CI.
What cannot run on a host is the sketch that wires it to the board, and that
is what this file reads as text, the way test_protocol.py does:

- the action handlers reach the motor only through DriveControl, because a
  digitalWrite(MOTOR_PIN_*) anywhere in main.ino drives the bridge without
  consulting the dwell;
- setup() drives the pins to their safe state before anything else, because
  every GPIO is an input until pinMode() runs and the bridge sees floating
  inputs until then.
"""
import os
import re
import sys
import unittest

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

_MAIN_INO = os.path.join(os.path.dirname(__file__), '..', '_esp32', 'main', 'main.ino')

# The body of a top-level function definition, up to the closing brace in
# column 0. Anchored at the start of a line so call sites do not match.
_FUNCTION_BODY_RE = r'^(?:\w+\s+)+{name}\s*\([^)]*\)\s*\{{(.*?)\n\}}'


def _read(path):
    with open(path, 'r') as f:
        return f.read()


def _function_body(source, name):
    match = re.search(_FUNCTION_BODY_RE.format(name=name), source, re.DOTALL | re.MULTILINE)
    return match.group(1) if match else None


class TestSketchGlue(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.main = _read(_MAIN_INO)

    def test_drive_handlers_go_through_drive_control(self):
        """The handlers must reach the motor only through the state machine.

        A direct pin write in a handler drives the bridge without consulting
        the dwell, which is exactly the failure the interlock exists to
        prevent -- and the one thing the native tests cannot see, because
        they never compile this file.
        """
        for name, call in (('accelerate', 'drive.engage('), ('reverse', 'drive.engage('),
                           ('stopAction', 'drive.stop(')):
            with self.subTest(handler=name):
                body = _function_body(self.main, name)
                self.assertIsNotNone(body, f"handler {name}() not found in {_MAIN_INO}")
                self.assertIn(call, body, f"{name}() bypasses DriveControl")
                self.assertNotIn('digitalWrite(', body, f"{name}() writes a pin directly")

    def test_the_only_pin_write_is_the_adaptor(self):
        """Every GPIO write goes through the injected writer.

        Once a second digitalWrite appears in the sketch, some path to the
        bridge exists that the host tests do not exercise.
        """
        adaptor = _function_body(self.main, 'writePin')
        self.assertIsNotNone(adaptor, f"writePin() adaptor not found in {_MAIN_INO}")
        self.assertIn('digitalWrite(', adaptor)
        self.assertEqual(self.main.count('digitalWrite('), 1,
                         "main.ino writes a pin somewhere other than the writePin() adaptor")

    def test_setup_drives_the_pins_before_anything_else(self):
        """Pin init and the safe-state writes must lead setup().

        Every GPIO is an input until pinMode() runs, so the H-bridge inputs
        float and the motor can twitch on the noise they pick up. Serial and
        its settle delay used to run first, holding that state for an extra
        second. Reordering only shortens the window to the boot ROM and
        bootloader; pull-downs on the driver inputs are what actually close
        it, so this test guards the part the firmware controls.
        """
        body = _function_body(self.main, 'setup')
        self.assertIsNotNone(body, f"setup() not found in {_MAIN_INO}")

        motor_pin_mode = re.search(r'pinMode\(MOTOR_PIN_', body)
        serial_begin = re.search(r'Serial\.begin\(', body)
        safe_state = re.search(r'drive\.failsafe\(', body)
        first_delay = re.search(r'delay\(', body)
        for name, match in (('pinMode(MOTOR_PIN_*)', motor_pin_mode), ('Serial.begin()', serial_begin),
                            ('drive.failsafe()', safe_state), ('delay()', first_delay)):
            self.assertIsNotNone(match, f"{name} not found in setup()")

        self.assertLess(
            motor_pin_mode.start(), serial_begin.start(),
            "setup() opens the serial port before driving the motor pins, which leaves the "
            "bridge inputs floating for longer than it has to")
        self.assertLess(
            safe_state.start(), first_delay.start(),
            "setup() delays before writing the safe output state")


if __name__ == '__main__':
    unittest.main()
