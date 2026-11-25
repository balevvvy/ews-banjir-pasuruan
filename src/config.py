"""
Loader konfigurasi terpusat (config/config.yaml).
Nilai yang tidak diisi di file memakai default di bawah.
"""

import copy
import os

import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")
CALIBRATION_PATH = os.path.join(BASE_DIR, "config", "calibration.json")
REFERENCE_PATH = os.path.join(BASE_DIR, "data", "reference.png")
DB_PATH = os.path.join(BASE_DIR, "data", "ews.db")
RECORDINGS_DIR = os.path.join(BASE_DIR, "data", "recordings")

DEFAULTS = {
    "camera": {"source": 1, "width": 1280, "height": 720},
    "detection": {"sensitivity": 30, "blur_size": 21, "debounce_sec": 5, "process_fps": 15},
    "ptz": {"enabled": False, "ip": "", "username": "", "password": "", "channel": 0},
    "server": {"reading_interval_sec": 5},
}


def _merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str = CONFIG_PATH) -> dict:
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError) as e:
            print(f"[config] Gagal membaca {path}: {e}. Memakai nilai default.")
    else:
        print(f"[config] {path} tidak ada. Memakai nilai default (salin dari config.example.yaml).")
    return _merge(DEFAULTS, data)


def parse_source(value):
    """'1' / 1 -> indeks webcam (int); selain itu path file atau URL (str)."""
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    if "://" not in text and not os.path.isabs(text):
        return os.path.join(BASE_DIR, text)
    return text
