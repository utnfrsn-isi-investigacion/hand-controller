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

// Wiring map, read off the board. The guides cite this block rather than
// restating it. Traction is channel B of the L298N, and the A/B naming below
// does not follow the INx numbering -- that crossed order is the trap this
// comment exists for. Which polarity is physically forward is a bench call
// with the wheels off the ground, never something to infer from this map.
//
//   GPIO 16  MOTOR_PIN_A         -> IN4   traction, channel B (ENB, OUT3/OUT4)
//   GPIO 17  MOTOR_PIN_B         -> IN3   traction, channel B
//   GPIO 4   DIRECTION_PIN_LEFT  -> IN1   steering, channel A (ENA, OUT1/OUT2)
//   GPIO 5   DIRECTION_PIN_RIGHT -> IN2   steering, channel A
const int MOTOR_PIN_A = 16;  // -> IN4
const int MOTOR_PIN_B = 17;  // -> IN3

// Pin levels that stop the motor (used by STOP and the failsafe).
// LOW/LOW is the one pair that cannot drive the motor on any of the usual
// drivers: on an L298N with the channel's enable jumpered (ENB for
// traction) the datasheet calls it "fast motor stop" (brake), on a
// DRV8833/TB6612FNG it coasts.
const int MOTOR_STOP_LEVEL_A = LOW;
const int MOTOR_STOP_LEVEL_B = LOW;

// Pin levels that drive the motor backwards (used by REVERSE).
// The inverse of ACCELERATE (A=HIGH/B=LOW), i.e. the second row of the
// H-bridge truth table -- identical on the L298N, DRV8833 and TB6612FNG.
// The rows are per channel, so the crossed map above (A -> IN4, B -> IN3)
// changes nothing here; it only means the row labels in the datasheet read
// backwards from the pin names. Only the bench says which row is forward.
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
// Steering is an H-bridge channel too (see the map above), so LEFT and RIGHT
// are the two drive rows of the steering motor and "straight" (LOW/LOW) is a
// brake on it, not a position: the wheels come back to centre only if the
// steering is spring-return, which is a property of the car, not the code.
const int DIRECTION_PIN_LEFT = 4;   // -> IN1
const int DIRECTION_PIN_RIGHT = 5;  // -> IN2

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
