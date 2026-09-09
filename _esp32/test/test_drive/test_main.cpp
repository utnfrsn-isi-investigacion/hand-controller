// Host-side tests for the drive state machine (run with `make test` in _esp32,
// or `make test-firmware` at the repo root). Reversing a motor that is still
// spinning is what kills the H-bridge, so the interlock in DriveControl is
// exercised here against the real pins, levels and dwell from config.h, with
// literal timestamps standing in for millis() and an array for the GPIOs.
#include <stdint.h>
#include <unity.h>
#include <DriveControl.h>

// Arduino's values. config.h spells the stop and reverse levels as LOW/HIGH
// and the library never includes Arduino.h, so they have to exist here.
#define LOW 0x0
#define HIGH 0x1
// Relative on purpose: config.h is the one home of pins, levels and the dwell,
// and lib/ deliberately cannot see main/. Testing against the real values is
// what makes the dwell and stop-level assertions mean something.
#include "../../main/config.h"

// The mechanical spin-down this has to cover is a matter of seconds; anything
// below this would be back to protecting only against the electrical
// transient.
static_assert(REVERSAL_DWELL_MS >= 1000, "REVERSAL_DWELL_MS is too short to cover the motor spinning down");

namespace {

const uint32_t DWELL = REVERSAL_DWELL_MS;
// Comfortably past the boot hold, so tests that are not about it start clean.
const uint32_t T0 = 10000;
const int UNWRITTEN = -1;

const int PIN_COUNT = 64;
static_assert(LED_PIN < PIN_COUNT && MOTOR_PIN_A < PIN_COUNT && MOTOR_PIN_B < PIN_COUNT &&
              DIRECTION_PIN_LEFT < PIN_COUNT && DIRECTION_PIN_RIGHT < PIN_COUNT,
              "a pin number in config.h is outside the fake GPIO array");

int pins[PIN_COUNT];

void fakeWrite(int pin, int level) { pins[pin] = level; }

DriveConfig configFromHeader() {
  DriveConfig config = {LED_PIN, MOTOR_PIN_A, MOTOR_PIN_B, MOTOR_STOP_LEVEL_A, MOTOR_STOP_LEVEL_B,
                        DIRECTION_PIN_LEFT, DIRECTION_PIN_RIGHT, DWELL};
  return config;
}

// The two calls exactly as the handlers in main.ino make them.
DriveResult forward(DriveControl& drive, uint32_t now) { return drive.engage(DRIVE_FORWARD, HIGH, LOW, now); }
DriveResult reverse(DriveControl& drive, uint32_t now) {
  return drive.engage(DRIVE_REVERSE, MOTOR_REVERSE_LEVEL_A, MOTOR_REVERSE_LEVEL_B, now);
}

void assertMotorStopped() {
  TEST_ASSERT_EQUAL_INT(MOTOR_STOP_LEVEL_A, pins[MOTOR_PIN_A]);
  TEST_ASSERT_EQUAL_INT(MOTOR_STOP_LEVEL_B, pins[MOTOR_PIN_B]);
  TEST_ASSERT_EQUAL_INT(LOW, pins[LED_PIN]);
}

void assertMotorForward() {
  TEST_ASSERT_EQUAL_INT(HIGH, pins[MOTOR_PIN_A]);
  TEST_ASSERT_EQUAL_INT(LOW, pins[MOTOR_PIN_B]);
  TEST_ASSERT_EQUAL_INT(HIGH, pins[LED_PIN]);
}

void assertMotorReverse() {
  TEST_ASSERT_EQUAL_INT(MOTOR_REVERSE_LEVEL_A, pins[MOTOR_PIN_A]);
  TEST_ASSERT_EQUAL_INT(MOTOR_REVERSE_LEVEL_B, pins[MOTOR_PIN_B]);
  TEST_ASSERT_EQUAL_INT(HIGH, pins[LED_PIN]);
}

}  // namespace

void setUp() {
  for (int i = 0; i < PIN_COUNT; i++) pins[i] = UNWRITTEN;
}

void tearDown() {}

void test_dwell_is_seconds_scale() {
  // Runtime twin of the static_assert, so the constant shows in the report.
  TEST_ASSERT_GREATER_OR_EQUAL_UINT32(1000, DWELL);
}

void test_forward_from_cold_engages_and_drives_the_pins() {
  DriveControl drive(configFromHeader(), fakeWrite);
  TEST_ASSERT_EQUAL_INT(DRIVE_ENGAGED, forward(drive, T0));
  assertMotorForward();
  TEST_ASSERT_EQUAL_INT(DRIVE_FORWARD, drive.state());
  TEST_ASSERT_EQUAL_INT(DRIVE_FORWARD, drive.lastDirection());
}

void test_same_direction_pull_away_is_immediate() {
  // A plain stop in the direction already driven owes no spin-down.
  DriveControl drive(configFromHeader(), fakeWrite);
  forward(drive, T0);
  drive.stop(T0 + 100);
  assertMotorStopped();
  TEST_ASSERT_EQUAL_INT(DRIVE_ENGAGED, forward(drive, T0 + 101));
  assertMotorForward();
}

void test_opposing_command_while_driving_brakes_and_refuses() {
  DriveControl drive(configFromHeader(), fakeWrite);
  forward(drive, T0);
  TEST_ASSERT_EQUAL_INT(DRIVE_BRAKED, reverse(drive, T0 + 100));
  assertMotorStopped();
  TEST_ASSERT_EQUAL_INT(DRIVE_STOPPED, drive.state());
  // The brake does not count as having driven backwards.
  TEST_ASSERT_EQUAL_INT(DRIVE_FORWARD, drive.lastDirection());
}

void test_latched_dwell_refuses_every_direction_until_it_passes() {
  // The regression that motivated the latch: a same-direction command during
  // the spin-down used to pass the direction check, re-energise the motor and
  // let the next opposing command restart the clock.
  DriveControl drive(configFromHeader(), fakeWrite);
  forward(drive, T0);
  const uint32_t brakedAt = T0 + 100;
  TEST_ASSERT_EQUAL_INT(DRIVE_BRAKED, reverse(drive, brakedAt));

  TEST_ASSERT_EQUAL_INT(DRIVE_HELD, forward(drive, brakedAt + 100));
  assertMotorStopped();
  TEST_ASSERT_EQUAL_INT(DRIVE_HELD, reverse(drive, brakedAt + DWELL - 1));
  assertMotorStopped();

  TEST_ASSERT_EQUAL_INT(DRIVE_ENGAGED, reverse(drive, brakedAt + DWELL));
  assertMotorReverse();
  TEST_ASSERT_EQUAL_INT(DRIVE_REVERSE, drive.state());
}

void test_wavering_vote_never_reenergises_the_old_direction() {
  // The gesture vote oscillating REVERSE, REVERSE, ACCELERATE every 100 ms for
  // six seconds. The motor must never go forward again, and reverse must
  // engage on the first retry after the dwell -- not be deferred by the
  // wavering.
  DriveControl drive(configFromHeader(), fakeWrite);
  forward(drive, T0);
  const uint32_t brakedAt = T0 + 100;
  uint32_t now = T0;
  int forwardEngagements = 0;
  uint32_t reverseEngagedAt = 0;
  for (int i = 0; i < 60; i++) {
    now += 100;
    const bool wantReverse = (i % 3 != 1);
    const DriveResult result = wantReverse ? reverse(drive, now) : forward(drive, now);
    if (!wantReverse && result == DRIVE_ENGAGED) forwardEngagements++;
    if (wantReverse && result == DRIVE_ENGAGED && reverseEngagedAt == 0) {
      reverseEngagedAt = now;
      assertMotorReverse();
    }
  }
  TEST_ASSERT_EQUAL_INT(0, forwardEngagements);
  TEST_ASSERT_NOT_EQUAL(0, reverseEngagedAt);
  TEST_ASSERT_GREATER_OR_EQUAL_UINT32(brakedAt + DWELL, reverseEngagedAt);
  // Within one period of the oscillation after the dwell expired.
  TEST_ASSERT_LESS_THAN_UINT32(brakedAt + DWELL + 300, reverseEngagedAt);
  // The vote is still wavering, so the stray forward command after that
  // engagement brakes the reverse run in turn -- correct, and the reason the
  // handler's smoothing exists. What matters is that it never went forward.
  TEST_ASSERT_EQUAL_INT(DRIVE_STOPPED, drive.state());
  assertMotorStopped();
}

void test_opposite_direction_after_a_plain_stop_waits_out_the_spin_down() {
  // Nothing braked, so there is no latch: the stop clock dates the spin-down.
  DriveControl drive(configFromHeader(), fakeWrite);
  forward(drive, T0);
  const uint32_t stoppedAt = T0 + 100;
  drive.stop(stoppedAt);
  TEST_ASSERT_EQUAL_INT(DRIVE_HELD, reverse(drive, stoppedAt + DWELL - 1));
  assertMotorStopped();
  TEST_ASSERT_EQUAL_INT(DRIVE_ENGAGED, reverse(drive, stoppedAt + DWELL));
  assertMotorReverse();
}

void test_repeated_stop_does_not_restart_the_dwell() {
  // The client resends STOP every refresh_interval; only the transition may
  // stamp the clock, or the opposite direction would never engage.
  DriveControl drive(configFromHeader(), fakeWrite);
  forward(drive, T0);
  const uint32_t stoppedAt = T0 + 100;
  drive.stop(stoppedAt);
  for (uint32_t t = stoppedAt + 500; t < stoppedAt + DWELL; t += 500) drive.stop(t);
  TEST_ASSERT_EQUAL_INT(DRIVE_ENGAGED, reverse(drive, stoppedAt + DWELL));
}

void test_boot_hold_covers_the_first_dwell() {
  // The latch starts at zero, so nothing drives for the first dwell of
  // uptime: the pins were floating moments earlier and the motor state is
  // unknown.
  DriveControl drive(configFromHeader(), fakeWrite);
  TEST_ASSERT_EQUAL_INT(DRIVE_HELD, forward(drive, 500));
  TEST_ASSERT_EQUAL_INT(UNWRITTEN, pins[MOTOR_PIN_A]);
  TEST_ASSERT_EQUAL_INT(DRIVE_ENGAGED, forward(drive, DWELL));
  assertMotorForward();
}

void test_dwell_survives_the_millis_wrap() {
  // millis() wraps every ~49.7 days. A brake stamped just before the wrap
  // must still hold for the full dwell, and release after it.
  DriveControl drive(configFromHeader(), fakeWrite);
  forward(drive, 0xFFFFF000u);
  TEST_ASSERT_EQUAL_INT(DRIVE_BRAKED, reverse(drive, 0xFFFFFF00u));   // 256 ms before the wrap
  TEST_ASSERT_EQUAL_INT(DRIVE_HELD, reverse(drive, 0x00000100u));     // 512 ms elapsed
  TEST_ASSERT_EQUAL_INT(DRIVE_HELD, reverse(drive, 0x00000100u + DWELL - 600));
  TEST_ASSERT_EQUAL_INT(DRIVE_ENGAGED, reverse(drive, 0x00000100u + DWELL));
  assertMotorReverse();
}

void test_failsafe_stops_and_centres() {
  DriveControl drive(configFromHeader(), fakeWrite);
  forward(drive, T0);
  drive.steerLeft();
  const uint32_t failedAt = T0 + 100;
  drive.failsafe(failedAt);
  assertMotorStopped();
  TEST_ASSERT_EQUAL_INT(LOW, pins[DIRECTION_PIN_LEFT]);
  TEST_ASSERT_EQUAL_INT(LOW, pins[DIRECTION_PIN_RIGHT]);
  TEST_ASSERT_EQUAL_INT(DRIVE_STOPPED, drive.state());
  // The failsafe is a real stop: it stamped the spin-down clock.
  TEST_ASSERT_EQUAL_INT(DRIVE_HELD, reverse(drive, failedAt + 1));
}

void test_steering_is_mutually_exclusive() {
  DriveControl drive(configFromHeader(), fakeWrite);
  drive.steerLeft();
  TEST_ASSERT_EQUAL_INT(HIGH, pins[DIRECTION_PIN_LEFT]);
  TEST_ASSERT_EQUAL_INT(LOW, pins[DIRECTION_PIN_RIGHT]);
  drive.steerRight();
  TEST_ASSERT_EQUAL_INT(LOW, pins[DIRECTION_PIN_LEFT]);
  TEST_ASSERT_EQUAL_INT(HIGH, pins[DIRECTION_PIN_RIGHT]);
  drive.steerStraight();
  TEST_ASSERT_EQUAL_INT(LOW, pins[DIRECTION_PIN_LEFT]);
  TEST_ASSERT_EQUAL_INT(LOW, pins[DIRECTION_PIN_RIGHT]);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_dwell_is_seconds_scale);
  RUN_TEST(test_forward_from_cold_engages_and_drives_the_pins);
  RUN_TEST(test_same_direction_pull_away_is_immediate);
  RUN_TEST(test_opposing_command_while_driving_brakes_and_refuses);
  RUN_TEST(test_latched_dwell_refuses_every_direction_until_it_passes);
  RUN_TEST(test_wavering_vote_never_reenergises_the_old_direction);
  RUN_TEST(test_opposite_direction_after_a_plain_stop_waits_out_the_spin_down);
  RUN_TEST(test_repeated_stop_does_not_restart_the_dwell);
  RUN_TEST(test_boot_hold_covers_the_first_dwell);
  RUN_TEST(test_dwell_survives_the_millis_wrap);
  RUN_TEST(test_failsafe_stops_and_centres);
  RUN_TEST(test_steering_is_mutually_exclusive);
  return UNITY_END();
}
