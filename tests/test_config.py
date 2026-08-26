import unittest
import tempfile
import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config, ConfigError  # noqa: E402


class TestConfig(unittest.TestCase):

    def test_defaults_from_empty_dict(self):
        config = Config.from_dict({})
        self.assertEqual(config.esp32.ip, "esp32.local")
        self.assertEqual(config.esp32.port, 1234)
        self.assertEqual(config.handler.buffer_size, 10)
        self.assertEqual(config.hand_detection.open_threshold_ratio, 0.6)

    def test_debug_defaults_to_off(self):
        """Debug is opt-in: an existing config.json without the section stays quiet."""
        config = Config.from_dict({})
        self.assertFalse(config.debug.enabled)
        self.assertTrue(config.debug.show_panel)
        self.assertEqual(config.debug.log_interval, 1.0)

    def test_debug_section_is_loaded(self):
        config = Config.from_dict({'debug': {'enabled': True, 'log_interval': 0.25}})
        self.assertTrue(config.debug.enabled)
        self.assertEqual(config.debug.log_interval, 0.25)

    def test_unknown_keys_are_ignored(self):
        """Stale keys in an old config.json must not break loading."""
        config = Config.from_dict({'esp32': {'ip': 'car.local', 'action_cooldown': 2}})
        self.assertEqual(config.esp32.ip, 'car.local')
        self.assertFalse(hasattr(config.esp32, 'action_cooldown'))

    def test_missing_file_raises_config_error(self):
        with self.assertRaises(ConfigError):
            Config.from_file(os.path.join(tempfile.gettempdir(), 'does-not-exist.json'))

    def test_invalid_json_raises_config_error(self):
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
            f.write('{ not valid json')
            path = f.name
        try:
            with self.assertRaises(ConfigError):
                Config.from_file(path)
        finally:
            os.unlink(path)

    def test_round_trip_through_dict(self):
        config = Config()
        self.assertEqual(Config.from_dict(config.to_dict()), config)


if __name__ == '__main__':
    unittest.main()
