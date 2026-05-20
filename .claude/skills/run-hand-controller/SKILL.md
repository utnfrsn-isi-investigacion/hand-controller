---
name: run-hand-controller
description: run, start, launch, screenshot, smoke-test the hand-controller app — real-time hand gesture recognition with MediaPipe and OpenCV
---

# run-hand-controller

Real-time hand gesture recognition app. Opens a webcam window and streams hand landmark overlays. Driven by `smoke.sh` for agent verification; launched directly with `python main.py` for human use. Requires a real webcam and `DISPLAY`.

All paths are relative to the repo root.

## Prerequisites

```bash
# libffi-dev must be installed BEFORE building Python via pyenv
sudo apt-get install -y libffi-dev
```

Python 3.12.11 must be built by pyenv **after** `libffi-dev` is installed (see Gotchas). If already installed without it, force-rebuild:

```bash
pyenv install --force 3.12.11
```

## Setup

```bash
# Create venv (uses .python-version → 3.12.11)
pyenv exec python -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# Create config (safe to re-run; skips if exists)
cp config.example.json config.json
```

## Run (agent path)

Use the smoke driver. It verifies ctypes, imports, config, launches the app, and confirms it stays alive for 6 seconds:

```bash
bash .claude/skills/run-hand-controller/smoke.sh
```

Expected tail output:
```
==> App is alive after 6s — PASS
==> Done.
```

## Run (human path)

```bash
source .venv/bin/activate
python main.py
# webcam window opens — press q to quit
```

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
```

## Gotchas

- **`ModuleNotFoundError: No module named '_ctypes'`** — pyenv-built Python 3.12.11 compiled without `libffi-dev` headers. Fix: `sudo apt-get install -y libffi-dev && pyenv install --force 3.12.11`, then recreate the venv. Runtime `libffi.so.8` being present is not enough; the dev headers must exist at compile time.

- **`config.json` missing** — the repo gitignores it. Copy from `config.example.json` before first run. The smoke driver does this automatically.

- **ESP32 connection failure on startup** — expected if no ESP32 is on the network. The app logs the error and continues; hand detection still works. To suppress, set `"ip": ""` or handle the timeout in `config.json`.

- **Multiple `inference_feedback_manager` warnings** — harmless MediaPipe noise about the hand-tracking model lacking feedback tensor support. Does not affect detection quality.

- **Camera index wrong** — default is `0`. Change `config.json → camera.index` if the webcam is on a different index.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No module named '_ctypes'` | Install `libffi-dev`, force-rebuild pyenv Python, recreate venv |
| `No module named 'cv2'` | Venv not activated or deps not installed: `.venv/bin/pip install -r requirements.txt` |
| App exits immediately | Check `DISPLAY` is set (`echo $DISPLAY`); needs an X server |
| Webcam black / no feed | Another process holds the camera; or try `camera.index: 1` |
