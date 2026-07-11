---
name: flash-esp32
description: Build and flash the ESP32 car firmware with PlatformIO, then verify boot over the serial monitor
disable-model-invocation: true
---

# flash-esp32

Firmware lives in `_esp32/` (PlatformIO, env `esp32dev`, Arduino framework). Run all commands from `_esp32/`.

## Prerequisites

- `pio` (PlatformIO CLI) on PATH.
- ESP32 board connected over USB.
- `main/secrets.h` present — create it once with `make secrets`, then the user fills in WiFi credentials. NEVER read or edit `secrets.h` (a hook blocks edits).

## Flash

```bash
cd _esp32
make build            # compile only
make upload-monitor   # flash + open serial monitor (115200 baud)
```

## Verify boot

Watch the serial monitor for, in order:

1. `Wi-Fi connected!` followed by the IP address
2. `mDNS started: <name>.local`
3. `TCP server listening on port 1234`

If WiFi never connects it prints dots forever — the credentials in `main/secrets.h` are wrong or the network is down.

## Smoke-test the protocol

With the firmware booted, send an action code from the host:

```bash
printf '000\n' | nc -w 2 esp32.local 1234   # expect reply: STOP (LED OFF)
```

Action codes are defined in `main/config.h` (`ACTION_*`) and must match `CarAction` in `handlers.py`. Exit the monitor with Ctrl+C.
