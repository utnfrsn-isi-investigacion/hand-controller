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

# Single test file / test case
.venv/bin/python -m unittest tests.test_handlers -v
.venv/bin/python -m unittest tests.test_handlers.TestCarHandler.test_left_hand_stop -v
```

CI (GitHub Actions) runs test, lint, and security on every push/PR; all three must pass.

ESP32 firmware lives in `_esp32/` (PlatformIO, not Arduino IDE): `cd _esp32 && make build` / `make upload-monitor` / `make secrets`.

## Architecture

Flat Python modules at the repo root form a per-frame pipeline, orchestrated by `main.py`:

camera frame → `cv2.flip` (mirror) → `HandProcessor.process_frame()` (hand.py, MediaPipe) → `List[Hand]` → `CarHandler.process_hands()` (handlers.py) → `TCPSender.send_action()` (esp32.py) → `Drawer.draw()` overlays (draw.py)

Cross-file invariants that are easy to break:

- **Mirrored frame**: `main.py` flips every frame (selfie view) so MediaPipe handedness labels match physical hands. All x-coordinate logic in `hand.py` (e.g. index orientation) assumes larger x = further to the user's right.
- **Wire protocol**: `CarAction` enum values in handlers.py ("000", "001", …) must exactly match the `ACTION_*` constants in `_esp32/main/config.h` and have an entry in the `actions[]` table in `_esp32/main/main.ino`. Codes are newline-terminated; firmware replies are drained and discarded, so nothing may depend on them. The `esp32-protocol-reviewer` agent checks this.
- **Dead-man timing**: the handler resends the current action every `handler.refresh_interval` seconds (default 0.5) as a keepalive; the firmware stops the motors after `COMMAND_TIMEOUT_MS` (2000ms) of silence. `refresh_interval` must stay well below that.
- **Gesture smoothing**: `Handler` majority-votes each hand's action over a deque buffer to suppress jitter, but `_is_priority_action()` actions (STOP) bypass smoothing and take effect immediately — never trade stop latency for smoothness.
- **Config flow**: `config.py` dataclasses → constructor parameters, threaded explicitly through `main.py`. New tunables get a dataclass field (with a comment) plus a `config.example.json` entry. `config.json` is the user's gitignored local copy — never edit it (a hook blocks this), and never touch `_esp32/main/secrets.h` (WiFi credentials).
- **Reconnects**: `TCPSender` reconnects on a throttled background thread because mDNS resolution can block for seconds; never call `connect()` from the frame loop.

## Tests

`unittest` (not pytest). Handler tests use `Mock(spec=Hand)` with stubbed `get_hand_type`/predicates, a `Mock()` ESP32 with `send_action.return_value = True`, and a huge `refresh_interval` so only change-driven sends are observed — follow that pattern.

## Security context

The ESP32 TCP server is unauthenticated by design (trusted/isolated networks only); the dead-man timeout is the safety backstop. Don't "fix" the missing auth in passing — it's a documented, deliberate trade-off (see README Security Considerations).
