"""Configuration management for Hand Controller."""
from dataclasses import dataclass, field, fields, asdict
import json
import os
import sys
from typing import Type, TypeVar

T = TypeVar('T')


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


@dataclass
class DisplayConfig:
    """Display configuration."""
    show_landmarks: bool = True
    show_fps: bool = False
    window_name: str = "Hand Gesture Recognition"


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
        print(f"Warning: ignoring unknown '{section}' config keys: {', '.join(sorted(unknown))}")
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
        """Load configuration from JSON file."""
        if not os.path.exists(config_path):
            print(f"Error: Configuration file '{config_path}' not found.")
            print("Please create a config.json file or copy from config.example.json")
            sys.exit(1)

        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in configuration file: {e}")
            sys.exit(1)
        except TypeError as e:
            print(f"Error: Invalid configuration structure: {e}")
            sys.exit(1)

    def to_dict(self) -> dict:
        """Convert Config to dictionary."""
        return asdict(self)

    def save_to_file(self, config_path: str = "config.json") -> None:
        """Save configuration to JSON file."""
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
