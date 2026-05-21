# JW OBS Monitor

## Overview
JW OBS Monitor is a Windows desktop utility that watches a JW Library display or window and automatically switches OBS Studio to a media scene when visual media appears. When media disappears, it can revert OBS back to the previous scene.

The app uses a Flet UI, `mss` screen capture, Pillow/numpy image analysis, and OBS WebSocket through `obsws-python`.

## Features
- Monitor either a numbered display or a window title.
- Preview the captured source inside the app.
- Detect media using RMS, brightness, and baseline comparison.
- Save a baseline RMS value from the preview.
- Connect to OBS WebSocket and switch to a configured media scene.
- Revert to the previous OBS scene after media is absent for the configured frame count.
- Persist OBS and threshold settings in `~/.jw_obs_monitor.json`.
- Support vertical and horizontal scrolling for low-resolution displays.

## Project Structure
```text
jw-obs-monitor
├── src
│   ├── main.py                  # Small Flet entry point
│   ├── config.py                # Default thresholds, polling, and OBS settings
│   ├── detector.py              # Detection worker and media/default heuristics
│   ├── obs_controller.py        # OBS WebSocket wrapper
│   ├── screen_monitor.py        # Monitor/window capture classes
│   ├── ui
│   │   ├── app.py               # UI controller, event handlers, worker lifecycle
│   │   ├── config_store.py      # Load/save helpers for user config
│   │   ├── layout.py            # Flet layout and component construction
│   │   └── __init__.py
│   └── utils
│       └── image_processing.py  # Shared image metric helpers
├── tests
│   ├── test_detector.py
│   └── test_obs_controller.py
├── requirements.txt
├── pyproject.toml
├── jw-obs-monitor.spec
└── README.md
```

## Installation
Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage
Start the app:

```bash
python src/main.py
```

In the UI:
- Choose `Monitor` or `Window Title` capture mode.
- Enter the monitor index or window title.
- Enter the OBS host, port, password, and media scene name.
- Use `Preview Capture` to verify the source.
- Use `Set baseline` while JW Library is showing its normal/default state.
- Click `Connect OBS`, then `Start`.

## Configuration
Default values live in `src/config.py`. User-saved settings are stored in:

```text
~/.jw_obs_monitor.json
```

Saved keys include:
- `obs_host`
- `obs_port`
- `obs_password`
- `threshold`
- `baseline_rms`
- `baseline_rms_delta`

Note: the OBS password is currently stored locally in plaintext.

## Tests
Run the unit tests:

```bash
python -m pytest
```

The tests use fake page, monitor, worker, OBS, `mss`, and `win32gui` objects, so they do not require OBS Studio, a real Flet window, or live screen capture.

## Packaging
To build a Windows executable using PyInstaller:

```bash
pip install -r requirements.txt
pyinstaller jw-obs-monitor.spec
```

The executable will be created under `dist/`.

Build on Windows for the most reliable result, especially because window capture uses `pywin32`.

## Notes
- OBS Studio must have WebSocket enabled for scene switching.
- OBS WebSocket 5.x normally uses port `4455`.
- Monitor indexes are 1-based because they come from `mss.monitors`.
