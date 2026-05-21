"""Persistence helpers for the UI configuration."""

import json
import os
from pathlib import Path


def obs_config_path():
    return Path(os.path.expanduser("~")) / ".jw_obs_monitor.json"


def load_obs_config(path=None):
    path = path or obs_config_path()
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_obs_config(config, path=None):
    path = path or obs_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f)
    return path
