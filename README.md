# Hand Controller

A real-time hand gesture recognition system that detects hand movements and sends control commands to an ESP32 microcontroller via TCP/IP. This project uses computer vision and MediaPipe to track hand gestures and translate them into actionable commands.

## 🚀 Features

- **Real-time Hand Tracking**: Uses MediaPipe for accurate hand landmark detection
- **Gesture Recognition**: Detects multiple hand gestures and orientations
- **Wireless Communication**: Sends commands to ESP32 via TCP/IP
- **Multi-Action Support**: Supports actions like accelerate, stop, and directional controls
- **Dual Hand Support**: Can process both left and right hands independently

## 📋 Prerequisites

- Python 3.13 or higher
- Webcam for hand detection
- ESP32 board (optional, for hardware control)
- Linux/macOS/Windows operating system

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/utnfrsn-isi-investigacion/hand-controller.git
cd hand-controller
```

### 2. Create Virtual Environment

Create and activate a Python virtual environment:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate
```

### 3. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

The following packages will be installed:
- `opencv-contrib-python==4.11.0.86` - OpenCV with extra modules
- `opencv-python==4.12.0.88` - Core OpenCV library
- `mediapipe==0.10.21` - Google's MediaPipe for hand tracking

### 4. Configure the Application

Create your configuration file from the example:

```bash
cp config.example.json config.json
```

Edit `config.json` to customize settings:

```json
{
  "esp32": {
    "ip": "esp32.local",           // ESP32 IP or hostname
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
  }
}
```

**Important**: Never commit `config.json` with sensitive information. Use `config.example.json` as a template.

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

- Make sure the virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.13+)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is part of the UTN FRSN ISI research project.

## 👥 Authors

- UTN FRSN ISI Investigation Team

## 🙏 Acknowledgments

- [MediaPipe](https://google.github.io/mediapipe/) for hand tracking
- [OpenCV](https://opencv.org/) for computer vision capabilities
- [ESP32](https://www.espressif.com/en/products/socs/esp32) for wireless microcontroller support
