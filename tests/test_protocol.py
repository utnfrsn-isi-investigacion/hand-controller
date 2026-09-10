"""Guards the wire protocol shared by the Python client and the ESP32 firmware.

CarAction values, the ACTION_* constants in the firmware header, and the
actions[] dispatch table all have to agree. Nothing enforces that at build
time -- the client sends a string and the firmware answers "Unknown command"
into a reply stream that is drained and discarded, so drift is silent and only
shows up as a car that ignores a gesture on real hardware.
"""
import os
import re
import sys
import unittest

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from handlers import CarAction  # noqa: E402

_FIRMWARE_DIR = os.path.join(os.path.dirname(__file__), '..', '_esp32', 'main')
_CONFIG_H = os.path.join(_FIRMWARE_DIR, 'config.h')
_MAIN_INO = os.path.join(_FIRMWARE_DIR, 'main.ino')

# const char* ACTION_ACCELERATE = "001";
_CONSTANT_RE = re.compile(r'const\s+char\*\s+(ACTION_\w+)\s*=\s*"([^"]*)"\s*;')
# {ACTION_ACCELERATE, accelerate},
_TABLE_ENTRY_RE = re.compile(r'\{\s*(ACTION_\w+)\s*,\s*(\w+)\s*\}')


def _read(path):
    with open(path, 'r') as f:
        return f.read()


class TestWireProtocol(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.constants = dict(_CONSTANT_RE.findall(_read(_CONFIG_H)))
        cls.table = dict(_TABLE_ENTRY_RE.findall(_read(_MAIN_INO)))

    def test_firmware_sources_were_parsed(self):
        """Guard against the regexes silently matching nothing."""
        self.assertTrue(self.constants, f"no ACTION_* constants found in {_CONFIG_H}")
        self.assertTrue(self.table, f"no actions[] entries found in {_MAIN_INO}")

    def test_codes_match_car_actions(self):
        """Every CarAction has a firmware constant with the same code, and vice versa."""
        self.assertEqual(
            sorted(a.value for a in CarAction),
            sorted(self.constants.values()),
            "CarAction values and firmware ACTION_* codes have drifted apart")

    def test_codes_are_unique(self):
        """Two actions sharing a code would make one of them unreachable."""
        codes = list(self.constants.values())
        self.assertEqual(len(codes), len(set(codes)), f"duplicate action codes: {codes}")

    def test_every_constant_is_dispatched(self):
        """A constant missing from actions[] is answered with 'Unknown command'."""
        self.assertEqual(sorted(self.constants), sorted(self.table),
                         "ACTION_* constants and the actions[] table disagree")

    def test_each_action_has_its_own_handler(self):
        """Two codes sharing a handler is almost always a copy-paste slip."""
        handlers = list(self.table.values())
        self.assertEqual(len(handlers), len(set(handlers)),
                         f"actions[] reuses a handler: {handlers}")


if __name__ == '__main__':
    unittest.main()
