# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Python 3.12.x is required (MediaPipe 0.10.21 does not support 3.13+); the version is pinned in `.python-version` and managed with pyenv. The Makefile always uses `.venv/bin/python`, so no shell activation is needed.

```bash
make install    # create .venv (pyenv) and install requirements
make config     # create config.json from config.example.json
make run        # run the app (needs a webcam; ESP32 optional)
make test       # unittest discovery over tests/
make lint       # flake8 (120-char lines, max-complexity 10)
make security   # bandit + pip-audit (PYSEC-2026-1805 ignored — see Makefile comment)
make test-firmware  # ESP32 drive-logic tests on this machine (PlatformIO + Unity, no board)

# Single test file / test case
.venv/bin/python -m unittest tests.test_handlers -v
.venv/bin/python -m unittest tests.test_handlers.TestCarHandler.test_left_hand_stop -v
```

CI (GitHub Actions) runs test, lint, security and firmware (the native Unity tests plus an ESP32 compile check) on every push/PR; all four must pass.

ESP32 firmware lives in `_esp32/` (PlatformIO, not Arduino IDE): `cd _esp32 && make build` / `make test` / `make upload-monitor` / `make secrets`. The drive state machine is `_esp32/lib/DriveControl/` — Arduino-free so it compiles on the host; time comes in as an argument and pin writes go out through a callback. `main.ino` only wires it to `millis()`/`digitalWrite()`, and `_esp32/test/test_drive/` runs it under Unity against the real `config.h` values.

## Architecture

Flat Python modules at the repo root form a per-frame pipeline, orchestrated by `main.py`:

camera frame → `cv2.flip` (mirror) → `HandProcessor.process_frame()` (hand.py, MediaPipe) → `List[Hand]` → `CarHandler.process_hands()` (handlers.py) → `TCPSender.send_action()` (esp32.py) → `Drawer.draw()` overlays (draw.py)

Cross-file invariants that are easy to break:

- **Mirrored frame**: `main.py` flips every frame (selfie view) so MediaPipe handedness labels match physical hands. All x-coordinate logic in `hand.py` (e.g. index orientation) assumes larger x = further to the user's right.
- **Wire protocol**: `CarAction` enum values in handlers.py ("000", "001", …) must exactly match the `ACTION_*` constants in `_esp32/main/config.h` and have an entry in the `actions[]` table in `_esp32/main/main.ino`. Codes are newline-terminated; firmware replies are drained and discarded, so nothing may depend on them. The `esp32-protocol-reviewer` agent checks this.
- **Dead-man timing**: the handler resends the current action every `handler.refresh_interval` seconds (default 0.5) as a keepalive; the firmware stops the motors **and drops the connection** after `COMMAND_TIMEOUT_MS` (2000ms) of silence. `refresh_interval` must stay well below that. The drop is not optional: the firmware serves one client at a time inside a blocking loop, so a half-open socket (which never reports `!connected()`) would otherwise keep `tcpServer.accept()` from ever running again — a reconnecting client then completes its TCP handshake and is silently ignored, which looks exactly like "connected, sending, nothing happens".
- **Reversal dwell**: a drive command that opposes the current direction brakes the motor and is refused, and `DriveControl::engage()` (in `_esp32/lib/DriveControl/`) then latches `brakedAtMs_` — reversing a spinning motor is what destroys the H-bridge. While that deadline stands **every** direction is refused, not just the opposing one: the deadline must not be derivable from the current direction, or the stray same-direction action the gesture vote emits mid-flick passes, re-energises the motor during the spin-down and lets the next opposing command re-stamp the clock, deferring the reversal for as long as the hand wavers. The cost is that a forward-flick user waits out the dwell too, which is the safe direction to err. Use elapsed-since-stamp (`millis() - stamp < REVERSAL_DWELL_MS`), never `millis() < deadline`, so the ~49-day `millis()` wrap stays correct. `accelerate()` and `reverse()` must go through `drive.engage()`; a `digitalWrite` anywhere in `main.ino` other than the `writePin` adaptor silently removes the protection. The refusal is not queued: the client's keepalive resend is the retry, which is why `refresh_interval` doubles as the engage latency. This cannot move to Python — the ESP32 serves any TCP client, and the gesture vote below only yields ~2 frames of STOP. `_esp32/test/test_drive/` runs the interlock natively; `tests/test_firmware_safety.py` only guards the `.ino` glue around it.
- **Boot window**: `setup()` must do the `pinMode` calls and `drive.failsafe()` before `Serial.begin()` and its settle delay. Every GPIO is an input until `pinMode` runs, so the H-bridge inputs float and the motor can twitch on the noise; anything placed ahead of those lines extends that window. Reordering only shortens it to the boot ROM and bootloader, which firmware cannot touch — pull-downs on the driver inputs would close it, and this board does not have them fitted, so don't describe the reorder as eliminating the twitch. The wiring map (which GPIO lands on which INx and channel) lives in `config.h`; cite it, don't restate it.
- **Gesture smoothing**: `Handler` majority-votes each hand's action over a deque buffer (`handler.buffer_size`) to suppress jitter — every action, STOP included, must win that vote before it is sent, so `buffer_size` directly sets stop latency (~`buffer_size / 2` frames to flip a saturated buffer). Keep it small enough that a deliberate stop gesture still reacts quickly. The undetected-hand path is the fast backstop: it returns `_default_actions` (STOP) and **clears** that hand's buffer, so a hand that comes back is not outvoted by what it was doing before it left (the first frame after reacquisition is therefore unsmoothed; the firmware dwell covers a direction change there). `_get_action` also gates the left hand on `Hand.has_usable_geometry()` first: with degenerate landmarks the thumb angle cannot return NEUTRAL, so "not open" would read as ACCELERATE — the gate is what keeps every error path ending in STOP.
- **Config flow**: `config.py` dataclasses → constructor parameters, threaded explicitly through `main.py`. New tunables get a dataclass field (with a comment) plus a `config.example.json` entry. `config.json` is the user's gitignored local copy — never edit it (a hook blocks this), and never touch `_esp32/main/secrets.h` (WiFi credentials).
- **Reconnects**: `TCPSender` reconnects on a throttled background thread because mDNS resolution can block for seconds; never call `connect()` from the frame loop.

## Tests

`unittest` (not pytest). Handler tests use `Mock(spec=Hand)` with stubbed `get_hand_type`/predicates, a `Mock()` ESP32 with `send_action.return_value = True`, and a huge `refresh_interval` so only change-driven sends are observed — follow that pattern.

Firmware tests are Unity, in `_esp32/test/test_drive/test_main.cpp`, run with `make test-firmware` (or `cd _esp32 && make test`). They build only `lib/DriveControl` and the test — `main/` is never compiled on the host — and include `../../main/config.h` directly so the real pins, levels and dwell are under test. A fake pin writer records into an array; timestamps are literals (`uint32_t`, so the `millis()` wrap is real on a 64-bit host). Interlock behaviour belongs there; `tests/test_firmware_safety.py` is text-only and exists for the sketch wiring that cannot run natively.

## Security context

The ESP32 TCP server is unauthenticated by design (trusted/isolated networks only); the dead-man timeout is the safety backstop. Don't "fix" the missing auth in passing — it's a documented, deliberate trade-off (see README Security Considerations).
