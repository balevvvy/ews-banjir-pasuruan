import os

import numpy as np

from src.config import BASE_DIR, load_config, parse_source
from src.detection.calibration import Calibration, load_calibration, save_calibration


def make_cal(**overrides):
    data = dict(roi={"x": 10, "y": 20, "w": 100, "h": 200}, y_waspada=150, y_siaga=80,
                frame_width=640, frame_height=480)
    data.update(overrides)
    return Calibration(**data)


def test_roundtrip(tmp_path):
    path = tmp_path / "cal.json"
    cal = make_cal()
    save_calibration(cal, str(path))
    assert load_calibration(str(path)) == cal


def test_missing_or_broken_file_returns_none(tmp_path):
    assert load_calibration(str(tmp_path / "tidak_ada.json")) is None
    broken = tmp_path / "rusak.json"
    broken.write_text("{bukan json")
    assert load_calibration(str(broken)) is None


def test_validate_ok():
    assert make_cal().validate() == []


def test_validate_lines_reversed():
    assert make_cal(y_waspada=80, y_siaga=150).validate()


def test_validate_roi_outside_frame():
    assert make_cal(roi={"x": 600, "y": 20, "w": 100, "h": 200}).validate()


def test_matches_frame_size():
    cal = make_cal()
    assert cal.matches(np.zeros((480, 640, 3), np.uint8))
    assert not cal.matches(np.zeros((720, 1280, 3), np.uint8))


def test_parse_source():
    assert parse_source(1) == 1
    assert parse_source("2") == 2
    assert parse_source("http://192.168.1.5:4747/video") == "http://192.168.1.5:4747/video"
    assert parse_source("data/recordings/x.mp4") == os.path.join(BASE_DIR, "data/recordings/x.mp4")


def test_load_config_fills_defaults(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("camera:\n  source: 3\n")
    cfg = load_config(str(path))
    assert cfg["camera"]["source"] == 3
    assert cfg["camera"]["width"] == 1280
    assert cfg["ptz"]["enabled"] is False
