# Hand Controller

[![CI](https://github.com/utnfrsn-isi-investigacion/hand-controller/actions/workflows/ci.yml/badge.svg)](https://github.com/utnfrsn-isi-investigacion/hand-controller/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/utnfrsn-isi-investigacion/hand-controller)](LICENSE)

A real-time hand gesture recognition system that detects hand movements and sends control commands to an ESP32 microcontroller via TCP/IP. This project uses computer vision and MediaPipe to track hand gestures and translate them into actionable commands.

> **⚠️ IMPORTANT**: This project requires **Python 3.12.x** and **pyenv** for proper dependency management. MediaPipe 0.10.21 is not compatible with Python 3.13+. Please follow the installation instructions carefully.

## 🚀 Features

- **Real-time Hand Tracking**: Uses MediaPipe for accurate hand landmark detection
- **Gesture Recognition**: Detects multiple hand gestures and orientations
- **Wireless Communication**: Sends commands to ESP32 via TCP/IP
- **Multi-Action Support**: Supports actions like accelerate, stop, and directional controls
- **Dual Hand Support**: Can process both left and right hands independently

## 📋 Prerequisites

- **Python 3.12.x** (Required for MediaPipe compatibility)
- **pyenv** (Required for Python version management)
- Webcam for hand detection
- ESP32 board (optional, for hardware control)
- Linux/macOS/Windows operating system

> **⚠️ Important**: This project requires Python 3.12.x due to MediaPipe compatibility. Python 3.13+ is not supported by MediaPipe 0.10.21. We use pyenv to manage the correct Python version.

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/utnfrsn-isi-investigacion/hand-controller.git
cd hand-controller
```

### 2. Install and Configure pyenv

**Install pyenv** (if not already installed):

> ⚠️ **Security Warning:** Downloading and executing scripts directly from the internet using `curl | bash` poses security risks. You should always review the script before running it.  
> You can inspect the script at [https://pyenv.run](https://pyenv.run) before executing.  
> Alternatively, consider installing pyenv using your system's package manager or following the [manual installation instructions](https://github.com/pyenv/pyenv#installation).
```bash
# Install pyenv
curl https://pyenv.run | bash

# Add pyenv to your shell (add to ~/.bashrc or ~/.zshrc)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

# Reload shell configuration
source ~/.bashrc
```

### 3. Install Python 3.12 and Create Virtual Environment

**Install Python 3.12.11** using pyenv:

```bash
# Install Python 3.12.11 (may take several minutes)
pyenv install 3.12.11

# Set Python 3.12.11 as local version for this project
pyenv local 3.12.11

# Verify correct Python version
python --version  # Should output: Python 3.12.11

# Create virtual environment with Python 3.12
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

### 4. Install Dependencies

**Ensure you're using Python 3.12** and install the required packages:

```bash
# Verify Python version before installing
python --version  # Must be 3.12.x

# Upgrade pip
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

The following packages will be installed:
- `opencv-python==4.10.0.84` - Core OpenCV library (compatible version)
- `mediapipe==0.10.21` - Google's MediaPipe for hand tracking

> **ℹ️ Note**: Previously, this project required both `opencv-python` and `opencv-contrib-python`. We have removed `opencv-contrib-python` because the current codebase does not use contributed modules (such as SIFT, SURF, etc.). If you need advanced OpenCV features from the contrib package, you may need to install `opencv-contrib-python` manually. This change reduces dependency size and avoids potential compatibility issues, but contributed modules will not be available by default.
> **💡 Note**: We use specific versions to ensure compatibility between OpenCV and MediaPipe with Python 3.12.

### 5. Configure the Application

Create your configuration file from the example:

```bash
cp config.example.json config.json
```

Edit `config.json` to customize settings:

```json
{
  "esp32": {
    "ip": "esp32.local",            // ESP32 IP or hostname
    "port": 1234,                   // TCP port
    "connection_timeout": 5,        // Connection timeout in seconds
    "action_cooldown": 2            // Minimum seconds between actions
  },
  "camera": {
    "index": 0,                     // Camera device index
    "width": 640,                   // Camera resolution width
    "height": 480                   // Camera resolution height
  },
  "hand_detection": {
    "max_hands": 2,                 // Maximum hands to detect
    "min_detection_confidence": 0.5,
    "min_tracking_confidence": 0.5
  },
  "display": {
    "show_landmarks": true,         // Show hand landmarks
    "show_fps": false,              // Show FPS counter
    "window_name": "Hand Gesture Recognition"
  },
  "handler": {
    "buffer_size": 30               // Action buffer size for smoothing
  }
}
```

**Important**: Never commit `config.json` with sensitive information. Use `config.example.json` as a template.

### Configuration Parameters Explained

#### Handler Settings
- **buffer_size**: Number of frames to buffer for action smoothing (default: 30)
  - Higher values = smoother transitions but slower response
  - Lower values = faster response but more jittery
  - Recommended range: 15-50 frames
  - Example: At 30 FPS, buffer_size=30 smooths over 1 second of data

The handler uses a majority voting system across the buffer to determine the most consistent action, reducing noise and false detections in hand gesture recognition.

## 🎮 Usage

### Running the Hand Controller

1. **Activate the virtual environment** (if not already activated):
   ```bash
   source .venv/bin/activate
   ```

2. **Configure settings** in `config.json`:
   - Set ESP32 IP address and port
   - Configure camera index if not using default
   - Adjust other settings as needed

3. **Run the application**:
   ```bash
   python main.py
   ```

4. **Use hand gestures** in front of your webcam:
   - The application will detect your hand landmarks
   - Perform gestures to trigger different actions
   - Press `q` to quit the application

### Available Actions

- **Accelerate**: Move hand forward/specific gesture
- **Stop**: Closed fist or stop gesture
- **Direction Left**: Point index finger left
- **Direction Right**: Point index finger right
- **Direction Straight**: Point index finger forward

## 🔌 ESP32 Setup

### Hardware Requirements

- ESP32 board
- USB cable for programming
- WiFi network

### Firmware Installation

1. **Open Arduino IDE** and install ESP32 board support

2. **Configure WiFi credentials** in `_esp32/main/main.ino`:
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```

3. **Upload the sketch** to your ESP32:
   - Open `_esp32/main/main.ino` in Arduino IDE
   - Select your ESP32 board and port
   - Click Upload

4. **Note the IP address** displayed in the Serial Monitor after connection

### mDNS Access

The ESP32 is configured with mDNS, so you can access it using:
```
esp32.local
```

Instead of remembering the IP address.

## 📁 Project Structure

```
hand-controller/
├── main.py              # Main application entry point
├── hand.py              # Hand gesture detection logic
├── handlers.py          # Action handlers with buffering logic
├── esp32.py             # TCP communication with ESP32
├── config.py            # Configuration management with dataclasses
├── config.json          # Configuration file (create from example)
├── config.example.json  # Example configuration template
├── requirements.txt     # Python dependencies
├── _esp32/
│   └── main/
│       └── main.ino     # ESP32 Arduino firmware
├── docs/
│   └── todo.md          # Project todos
└── .venv/               # Virtual environment (created during setup)
```

## 🏗️ Architecture

### Python Components

- **main.py**: Orchestrates the video capture, hand detection, and ESP32 communication
- **hand.py**: Contains the `HandGestureDetector` class with MediaPipe integration
- **handlers.py**: Implements action handlers with configurable buffering for gesture smoothing
- **esp32.py**: Manages TCP socket connection and command transmission
- **config.py**: Configuration management using Python dataclasses for type safety

### ESP32 Firmware

- Connects to WiFi network
- Starts mDNS responder for easy network access
- Listens for TCP connections on port 1234
- Receives and processes action commands

## 🐛 Troubleshooting

### Configuration Issues

- **Missing config.json**: Copy `config.example.json` to `config.json` and customize
- **Invalid JSON**: Validate your config file format using a JSON validator
- **Wrong ESP32 IP**: Check ESP32 serial output for actual IP address

### Camera Not Working

- Ensure your webcam is connected and not used by another application
- Check camera permissions on your system
- Try changing the camera index in `main.py`: `cv2.VideoCapture(1)` instead of `0`

### ESP32 Connection Issues

- Verify ESP32 is on the same network as your computer
- Check firewall settings
- Use IP address instead of `esp32.local` if mDNS doesn't work
- Ensure port 1234 is not blocked

### Import Errors

- Make sure the virtual environment is activated: `source .venv/bin/activate`
- Verify Python version: `python --version` (must be 3.12.x)
- If wrong Python version, reinstall using pyenv:
  ```bash
  pyenv local 3.12.11
  rm -rf .venv
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- Reinstall dependencies: `pip install -r requirements.txt`

## � Testing

This project uses Python's `unittest` framework for testing. All tests are located in the `tests/` directory.

### Running Tests

**Run all tests:**
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

**Run a specific test file:**
```bash
python -m unittest tests.test_hand -v
python -m unittest tests.test_handlers -v
```

### Code Quality Checks

**Run linting with flake8:**
```bash
pip install flake8
flake8 .  # Uses .flake8 config (120 char line limit)
```

> **Note**: This project uses a 120-character line limit instead of PEP 8's default 79 characters for better readability on modern displays.

**Run tests with coverage:**
```bash
pip install coverage
coverage run -m unittest discover -s tests -p "test_*.py"
coverage report -m
coverage html  # Generate HTML coverage report
```

**Security scanning:**
```bash
pip install bandit pip-audit
bandit -r . --exclude=./_esp32,./tests
pip-audit --requirement requirements.txt
```

### Continuous Integration

This project uses GitHub Actions for CI. On every push and pull request, the following checks run automatically:
- ✅ Unit tests on Ubuntu, macOS, and Windows
- ✅ Code linting with flake8
- ✅ Security scans with Bandit and pip-audit

See [CI Documentation](.github/CI_DOCUMENTATION.md) for more details.

## �🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

Copyright 2025 UTN FRSN ISI Investigation Team

## 🙏 Acknowledgments

- [MediaPipe](https://google.github.io/mediapipe/) for hand tracking
- [OpenCV](https://opencv.org/) for computer vision capabilities
- [ESP32](https://www.espressif.com/en/products/socs/esp32) for wireless microcontroller support
