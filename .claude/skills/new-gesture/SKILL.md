---
name: new-gesture
description: Add a new hand gesture end-to-end — detection in hand.py, action in handlers.py, config threshold, firmware action code, and tests
---

# new-gesture

Checklist for adding a gesture to the pipeline. The flow is:
camera frame → `HandProcessor.process_frame()` → `Hand` predicates → `Handler._get_action()` → `CarAction` code → TCP → ESP32 firmware.

Work through every step; skipping one is the usual source of "gesture detected but nothing happens" bugs. All paths are relative to the repo root.

## 1. Detection (hand.py)

- Add a predicate method to `Hand` (model it on `is_open()` / `get_index_orientation()`).
- Landmarks come from `mp_hands.HandLandmark`; normalize distances by hand size (WRIST→MIDDLE_FINGER_MCP, see `is_open`).
- Any tunable threshold becomes a constructor parameter with a default — never a hardcoded constant.
- The frame is mirrored (selfie view): larger x means further to the user's right.

## 2. Configuration (config.py + config.example.json)

- Add the threshold to `HandDetectionConfig` with a comment explaining units and meaning.
- Mirror it in `config.example.json`. NEVER edit `config.json` — it is the user's gitignored local config (a hook blocks edits).
- Thread it through the wiring: `main.py` → `HandProcessor.__init__` → `Hand` constructor.

## 3. Action (handlers.py)

- Add a member to `CarAction` (3-digit string code) or extend the relevant handler.
- Map gesture → action in `CarHandler._get_action()`.
- Safety-critical actions (like STOP) must bypass majority smoothing: extend `_is_priority_action()`.

## 4. Firmware (_esp32/main/) — only if a new action code was added

- Declare the code in `config.h` (`ACTION_*` constants) — must match the Python enum value exactly.
- Add a handler function and an `actions[]` table entry in `main.ino`.
- Make sure the failsafe (`failsafeStop()`) still leaves the hardware in a safe state with the new action.

## 5. Overlay (draw.py)

- `Drawer` shows `action.name` (plus confidence) automatically — usually nothing to do.
- New standalone visuals go in a `_draw_*` method behind a `DisplayConfig` toggle.

## 6. Tests (tests/)

- Follow `tests/test_handlers.py`: `Mock(spec=Hand)` with stubbed `get_hand_type` / predicate methods; `Mock()` ESP32 with `send_action.return_value = True`; a large `refresh_interval` so tests only observe change-driven sends.
- Threshold/geometry logic gets direct tests in the style of `tests/test_hand.py`.

## 7. Verify

```bash
make test
make lint
```

For a live end-to-end check, use the run-hand-controller skill.
