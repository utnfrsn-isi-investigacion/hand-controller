#ifndef CONFIG_H
#define CONFIG_H

//////////////////////
// NETWORK CONFIGURATION
//////////////////////
// TCP server port
const uint16_t TCP_PORT = 1234;

// Dead-man timeout: if no command arrives within this window, the motors are
// stopped and the client is dropped so a reconnecting one can be served.
// The Python client resends the current action every
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

// Pin levels that stop the motor (used by STOP and the failsafe).
// LOW/LOW is the one pair that cannot drive the motor on any of the usual
// drivers: on an L298N with ENA jumpered the datasheet calls it "fast
// motor stop" (brake), on a DRV8833/TB6612FNG it coasts.
const int MOTOR_STOP_LEVEL_A = LOW;
const int MOTOR_STOP_LEVEL_B = LOW;

// Pin levels that drive the motor backwards (used by REVERSE).
// The inverse of ACCELERATE (A=HIGH/B=LOW), i.e. the second row of the
// H-bridge truth table -- identical on the L298N, DRV8833 and TB6612FNG.
// Assumes MOTOR_PIN_A -> IN1 and MOTOR_PIN_B -> IN2.
const int MOTOR_REVERSE_LEVEL_A = LOW;
const int MOTOR_REVERSE_LEVEL_B = HIGH;

// Minimum time the motor must sit at the stop levels before the firmware will
// drive it the other way. Reversing a motor that is still spinning puts the
// supply across the winding on top of its own back-EMF; the resulting spike is
// roughly twice stall current, and what gives way is the H-bridge, the motor,
// or the regulator the ESP32 runs off.
// This has to live in the firmware because it must hold for whatever client
// connects: the Python side's gesture smoothing only produces a stop of a few
// frames (~65ms at the default buffer_size), and a fast enough flick emits
// ACCELERATE followed directly by REVERSE.
// Seconds, not milliseconds -- it covers the mechanical spin-down of a loaded
// drivetrain, not just the electrical transient. A drive command arriving
// during the dwell is refused, never queued: the client's keepalive resend
// (handler.refresh_interval, default 0.5s) retries it, so the direction
// engages within one refresh of the dwell expiring.
const unsigned long REVERSAL_DWELL_MS = 3000;

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
const char* ACTION_REVERSE = "010";
const char* ACTION_STOP = "000";
const char* ACTION_LEFT = "101";
const char* ACTION_RIGHT = "110";
const char* ACTION_STRAIGHT = "111";

#endif
