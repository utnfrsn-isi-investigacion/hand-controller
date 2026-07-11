"""Configuration management for Hand Controller."""
from dataclasses import dataclass, field, fields, asdict
import json
import logging
import os
from typing import List, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConfigError(Exception):
    """Raised when the configuration file is missing or invalid."""


@dataclass
class ESP32Config:
    """ESP32 connection configuration."""
    ip: str = "esp32.local"
    port: int = 1234
    connection_timeout: int = 5


@dataclass
class CameraConfig:
    """Camera configuration."""
    index: int = 0
    width: int = 640
    height: int = 480


@dataclass
class HandDetectionConfig:
    """Hand detection configuration."""
    max_hands: int = 2
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    # Normalized tip-to-knuckle distance (relative to hand size) above which
    # a finger counts as extended; all five must pass for an open hand.
    open_threshold_ratio: float = 0.6
    # Horizontal tip-to-knuckle offset (normalized image coords) beyond which
    # the index finger counts as pointing left/right instead of straight.
    index_orientation_threshold: float = 0.05


@dataclass
class DisplayConfig:
    """Display configuration."""
    # Master toggle: disables every overlay (landmarks, text, status, FPS)
    show_overlays: bool = True
    show_landmarks: bool = True
    show_confidence: bool = True
    show_fps: bool = False
    window_name: str = "Hand Gesture Recognition"
    # Overlay colors in BGR order (OpenCV convention)
    left_hand_color: List[int] = field(default_factory=lambda: [0, 255, 0])
    right_hand_color: List[int] = field(default_factory=lambda: [0, 0, 255])
    text_scale: float = 1.0
    text_thickness: int = 2


@dataclass
class HandlerConfig:
    """Handler configuration."""
    buffer_size: int = 30
    # Seconds between keepalive resends of the current action; must stay well
    # below the firmware's COMMAND_TIMEOUT_MS dead-man timeout.
    refresh_interval: float = 0.5


def _build_section(section_cls: Type[T], data: dict, section: str) -> T:
    """Build a config section, warning about and ignoring unknown keys."""
    valid = {f.name for f in fields(section_cls)}  # type: ignore[arg-type]
    unknown = set(data) - valid
    if unknown:
        logger.warning("Ignoring unknown '%s' config keys: %s", section, ', '.join(sorted(unknown)))
    return section_cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class Config:
    """Main configuration class."""
    esp32: ESP32Config = field(default_factory=ESP32Config)
    camera: CameraConfig = field(default_factory=CameraConfig)
    hand_detection: HandDetectionConfig = field(default_factory=HandDetectionConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    handler: HandlerConfig = field(default_factory=HandlerConfig)

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """Create Config from dictionary."""
        return cls(
            esp32=_build_section(ESP32Config, data.get('esp32', {}), 'esp32'),
            camera=_build_section(CameraConfig, data.get('camera', {}), 'camera'),
            hand_detection=_build_section(HandDetectionConfig, data.get('hand_detection', {}), 'hand_detection'),
            display=_build_section(DisplayConfig, data.get('display', {}), 'display'),
            handler=_build_section(HandlerConfig, data.get('handler', {}), 'handler')
        )

    @classmethod
    def from_file(cls, config_path: str = "config.json") -> 'Config':
        """Load configuration from JSON file.

        Raises ConfigError if the file is missing or invalid.
        """
        if not os.path.exists(config_path):
            raise ConfigError(
                f"Configuration file '{config_path}' not found. "
                "Create one by copying config.example.json (make config)."
            )

        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in '{config_path}': {e}") from e
        except TypeError as e:
            raise ConfigError(f"Invalid configuration structure in '{config_path}': {e}") from e

    def to_dict(self) -> dict:
        """Convert Config to dictionary."""
        return asdict(self)

    def save_to_file(self, config_path: str = "config.json") -> None:
        """Save configuration to JSON file."""
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
