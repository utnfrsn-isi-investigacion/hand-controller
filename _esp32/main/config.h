#ifndef CONFIG_H
#define CONFIG_H

//////////////////////
// NETWORK CONFIGURATION
//////////////////////
// TCP server port
const uint16_t TCP_PORT = 1234;

// Dead-man timeout: if no command arrives within this window, motors are
// stopped. The Python client resends the current action every
// handler.refresh_interval seconds (default 0.5s), so this must stay well
// above that.
const unsigned long COMMAND_TIMEOUT_MS = 2000;

//////////////////////
// HARDWARE CONFIGURATION
//////////////////////
// LED pin for visual feedback
// Common values:
//   - Most ESP32 boards: 2
//   - ESP32-CAM: 33 (white LED) or 4 (flash)
//   - ESP32-S2: 15
//   - ESP32-C3: 8
const int LED_PIN = 2;

// Motor control pins
const int MOTOR_PIN_A = 16;  // Motor control A
const int MOTOR_PIN_B = 17;  // Motor control B

// Direction control pins
const int DIRECTION_PIN_LEFT = 4;   // Direction left control
const int DIRECTION_PIN_RIGHT = 5;  // Direction right control

// Serial baud rate
const unsigned long SERIAL_BAUD = 115200;

//////////////////////
// ACTION CODES
//////////////////////
// Command codes received from the client
const char* ACTION_ACCELERATE = "001";
const char* ACTION_STOP = "000";
const char* ACTION_LEFT = "101";
const char* ACTION_RIGHT = "110";
const char* ACTION_STRAIGHT = "111";

#endif
