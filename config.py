"""Configuration management for Hand Controller."""
from dataclasses import dataclass, field
import json
import os
import sys


@dataclass
class ESP32Config:
    """ESP32 connection configuration."""
    ip: str = "esp32.local"
    port: int = 1234
    connection_timeout: int = 5
    action_cooldown: int = 2


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
            esp32=ESP32Config(**data.get('esp32', {})),
            camera=CameraConfig(**data.get('camera', {})),
            hand_detection=HandDetectionConfig(**data.get('hand_detection', {})),
            display=DisplayConfig(**data.get('display', {})),
            handler=HandlerConfig(**data.get('handler', {}))
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
        return {
            'esp32': {
                'ip': self.esp32.ip,
                'port': self.esp32.port,
                'connection_timeout': self.esp32.connection_timeout,
                'action_cooldown': self.esp32.action_cooldown
            },
            'camera': {
                'index': self.camera.index,
                'width': self.camera.width,
                'height': self.camera.height
            },
            'hand_detection': {
                'max_hands': self.hand_detection.max_hands,
                'min_detection_confidence': self.hand_detection.min_detection_confidence,
                'min_tracking_confidence': self.hand_detection.min_tracking_confidence
            },
            'display': {
                'show_landmarks': self.display.show_landmarks,
                'show_fps': self.display.show_fps,
                'window_name': self.display.window_name
            },
            'handler': {
                'buffer_size': self.handler.buffer_size
            }
        }

    def save_to_file(self, config_path: str = "config.json") -> None:
        """Save configuration to JSON file."""
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
