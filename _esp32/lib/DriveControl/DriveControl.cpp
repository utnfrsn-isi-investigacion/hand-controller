#include "DriveControl.h"

namespace {
// Arduino's LOW and HIGH. The library must not include Arduino.h, and only the
// LED is driven at fixed levels -- every motor and steering level is injected.
const int LEVEL_LOW = 0;
const int LEVEL_HIGH = 1;
}  // namespace

DriveControl::DriveControl(const DriveConfig& config, PinWriter writePin)
    : config_(config),
      writePin_(writePin),
      state_(DRIVE_STOPPED),
      // What distinguishes "stopped after driving the other way", which owes
      // a spin-down, from "stopped after driving this way" and "never
      // driven", which do not -- so pulling away from a stop in the direction
      // you were already going stays immediate.
      lastDirection_(DRIVE_STOPPED),
      stoppedAtMs_(0),
      // Zero also holds off the first reversalDwellMs of uptime; see engage().
      brakedAtMs_(0) {}

void DriveControl::stop(uint32_t nowMs) {
  writePin_(config_.ledPin, LEVEL_LOW);
  // Stop levels come from config.h -- verify them against the motor driver
  // wiring (see the note there).
  writePin_(config_.motorPinB, config_.stopLevelB);
  writePin_(config_.motorPinA, config_.stopLevelA);
  // Start the spin-down clock on the transition only: the client resends the
  // current action every refresh_interval, and re-stamping on each repeated
  // STOP would push the dwell permanently out of reach.
  if (state_ != DRIVE_STOPPED) {
    state_ = DRIVE_STOPPED;
    stoppedAtMs_ = nowMs;
  }
}

DriveResult DriveControl::engage(DriveState wanted, int levelA, int levelB, uint32_t nowMs) {
  if (state_ != wanted && state_ != DRIVE_STOPPED) {
    // Turning the other way right now: brake, and latch the deadline the
    // whole dwell hangs off. The earliest anything can drive again is
    // reversalDwellMs from here.
    stop(nowMs);
    brakedAtMs_ = nowMs;
    return DRIVE_BRAKED;
  }
  if (nowMs - brakedAtMs_ < config_.reversalDwellMs) {
    // Inside a latched dwell, so refuse every direction rather than only the
    // opposing one. Checking the direction here is what let the dwell be
    // restarted forever: a stray same-direction command from the gesture vote
    // passed, re-energised the motor mid spin-down, and the next opposing
    // command braked and re-stamped the clock. While the hand wavered the
    // reversal never engaged and the car kept lurching the old way.
    // The price is that a user flicking forward-neutral-forward waits out the
    // dwell too. That is the safe direction to err.
    // Elapsed-since-stamp, not now < deadline: unsigned subtraction is
    // correct across the millis() wrap.
    // The initial 0 also holds off the first reversalDwellMs of uptime.
    // Usually the Wi-Fi join outlasts it, but not always -- a fast
    // association can have a client connected inside the window, and its
    // drive commands then no-op until the next keepalive. Keeping it: the
    // pins were floating moments earlier and the motor state is unknown, so
    // refusing to drive for the first few seconds is the right default.
    return DRIVE_HELD;
  }
  if (state_ != wanted && lastDirection_ != DRIVE_STOPPED && lastDirection_ != wanted &&
      nowMs - stoppedAtMs_ < config_.reversalDwellMs) {
    // Stopped before this command arrived, but still spinning down from the
    // opposite direction -- nothing braked here, so there is no latch to
    // consult and the stop clock is what dates the spin-down.
    return DRIVE_HELD;
  }
  writePin_(config_.ledPin, LEVEL_HIGH);
  // Written in either order: there is no both-sides-driven moment to avoid.
  // Arriving from DRIVE_STOPPED the pins are at the stop levels, because the
  // conflicting-direction case brakes and returns above; arriving with the
  // state already == wanted they are at these very levels and both writes
  // are no-ops. Neither case can cross the bridge over.
  writePin_(config_.motorPinA, levelA);
  writePin_(config_.motorPinB, levelB);
  state_ = wanted;
  lastDirection_ = wanted;
  return DRIVE_ENGAGED;
}

void DriveControl::steerLeft() {
  writePin_(config_.directionPinLeft, LEVEL_HIGH);
  writePin_(config_.directionPinRight, LEVEL_LOW);
}

void DriveControl::steerRight() {
  writePin_(config_.directionPinRight, LEVEL_HIGH);
  writePin_(config_.directionPinLeft, LEVEL_LOW);
}

void DriveControl::steerStraight() {
  writePin_(config_.directionPinRight, LEVEL_LOW);
  writePin_(config_.directionPinLeft, LEVEL_LOW);
}

void DriveControl::failsafe(uint32_t nowMs) {
  stop(nowMs);
  steerStraight();
}
