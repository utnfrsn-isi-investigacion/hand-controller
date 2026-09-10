#ifndef DRIVE_CONTROL_H
#define DRIVE_CONTROL_H

#include <stdint.h>

// The traction and steering state machine, kept free of Arduino so it runs on
// the host. The reversal interlock in here is what protects the H-bridge, and
// a regression in it has to fail in CI rather than on the bench -- so time
// comes in as an argument and pin writes go out through a callback. main.ino
// supplies millis() and digitalWrite(); the tests supply literal timestamps
// and an array.

enum DriveState { DRIVE_STOPPED, DRIVE_FORWARD, DRIVE_REVERSE };

// What engage() did with a request. Only DRIVE_ENGAGED energises the motor.
// The two refusals are told apart so the caller can log the brake, which is
// the one moment worth a serial line.
enum DriveResult { DRIVE_ENGAGED, DRIVE_BRAKED, DRIVE_HELD };

typedef void (*PinWriter)(int pin, int level);

// Everything the state machine needs from config.h, handed over by main.ino:
// a library cannot see main/, and config.h stays the one place pins and
// levels are defined.
struct DriveConfig {
  int ledPin;
  int motorPinA;
  int motorPinB;
  int stopLevelA;
  int stopLevelB;
  int directionPinLeft;
  int directionPinRight;
  // 32-bit on purpose: that is what millis() is on the ESP32, and the wrap
  // every ~49 days is part of what the tests cover. On a 64-bit host an
  // unsigned long would never wrap and the test would prove nothing.
  uint32_t reversalDwellMs;
};

class DriveControl {
 public:
  DriveControl(const DriveConfig& config, PinWriter writePin);

  // Motor to the stop levels, LED off. Stamps the spin-down clock on the
  // driving-to-stopped transition only.
  void stop(uint32_t nowMs);

  // Drive the traction motor, enforcing the reversal dwell. A refused request
  // leaves the motor stopped and is not queued: the client's keepalive resend
  // is the retry.
  DriveResult engage(DriveState wanted, int levelA, int levelB, uint32_t nowMs);

  void steerLeft();
  void steerRight();
  void steerStraight();

  // Stop and centre: the state to be in when nobody is in control.
  void failsafe(uint32_t nowMs);

  DriveState state() const { return state_; }
  DriveState lastDirection() const { return lastDirection_; }

 private:
  DriveConfig config_;
  PinWriter writePin_;
  DriveState state_;
  DriveState lastDirection_;
  uint32_t stoppedAtMs_;
  uint32_t brakedAtMs_;
};

#endif
