"""
Uji ujung-ke-ujung: detektor membaca file video sintetis (air naik dari kosong
sampai melewati garis merah), lalu harus melaporkan WASPADA kemudian SIAGA.
"""

import time

import cv2

from src.config import DEFAULTS, _merge
from src.detection.calibration import Calibration, save_calibration, save_reference
from src.detection.detector import OFFLINE, WaterLevelDetector
from tests import scene

FPS = 30


def write_rising_water_video(path, seconds=6):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (scene.WIDTH, scene.HEIGHT))
    bottom = scene.ROI["y"] + scene.ROI["h"]
    total = FPS * seconds
    empty = FPS  # 1 detik pertama botol kosong
    for i in range(total):
        if i < empty:
            water_y = None
        else:
            progress = (i - empty) / (total - empty)
            water_y = int(bottom - 20 - progress * (bottom - 20 - (scene.Y_SIAGA - 40)))
        writer.write(scene.make_frame(water_y, noise_seed=i))
    writer.release()


def make_detector(tmp_path, source):
    config = _merge(DEFAULTS, {
        "camera": {"source": str(source)},
        "detection": {"debounce_sec": 0.3, "process_fps": FPS},
        "server": {"reading_interval_sec": 0.2},
    })
    cal_path, ref_path = tmp_path / "calibration.json", tmp_path / "reference.png"
    return WaterLevelDetector(config, calibration_path=str(cal_path), reference_path=str(ref_path),
                              recordings_dir=str(tmp_path / "rec")), cal_path, ref_path


def wait_for(predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_rising_water_triggers_waspada_then_siaga(tmp_path):
    video = tmp_path / "naik.mp4"
    write_rising_water_video(video)

    detector, cal_path, ref_path = make_detector(tmp_path, video)
    save_reference(scene.make_frame(None, noise_seed=999), str(ref_path))
    save_calibration(Calibration(roi=scene.ROI, y_waspada=scene.Y_WASPADA, y_siaga=scene.Y_SIAGA,
                                 frame_width=scene.WIDTH, frame_height=scene.HEIGHT), str(cal_path))

    alerts, readings = [], []
    detector.on_alert = lambda status, pesan: alerts.append(status)
    detector.on_reading = lambda y, pct, status: readings.append((y, pct, status))
    detector.start()
    try:
        assert wait_for(lambda: "SIAGA" in alerts), f"alert yang diterima: {alerts}"
        assert alerts.index("WASPADA") < alerts.index("SIAGA")
        assert readings, "pembacaan harus dikirim ke database"
        assert detector.get_jpeg("annotated") is not None
        assert detector.get_jpeg("mask") is not None
    finally:
        detector.stop()


def test_without_calibration_reports_belum_kalibrasi(tmp_path):
    video = tmp_path / "naik.mp4"
    write_rising_water_video(video, seconds=1)
    detector, _, _ = make_detector(tmp_path, video)
    detector.start()
    try:
        assert wait_for(lambda: detector.status == "BELUM_KALIBRASI")
        assert "kalibrasi" in detector.message.lower()
        assert detector.get_jpeg("annotated") is not None   # video tetap tampil
    finally:
        detector.stop()


def test_missing_source_reports_offline(tmp_path):
    detector, _, _ = make_detector(tmp_path, tmp_path / "tidak_ada.mp4")
    detector.start()
    try:
        time.sleep(0.5)
        assert detector.status == OFFLINE
        assert not detector.camera_connected
        assert detector.get_jpeg() is None
    finally:
        detector.stop()


def test_reference_capture_and_recording(tmp_path):
    video = tmp_path / "naik.mp4"
    write_rising_water_video(video, seconds=2)
    detector, _, ref_path = make_detector(tmp_path, video)
    detector.start()
    try:
        assert wait_for(lambda: detector.camera_connected and detector.frame_size)
        ok, _ = detector.request_reference_capture()
        assert ok and ref_path.exists()

        files = detector.start_recording()
        time.sleep(1)
        info = detector.stop_recording()
        assert info["files"] == files
        for name in files:
            cap = cv2.VideoCapture(str(tmp_path / "rec" / name))
            assert cap.get(cv2.CAP_PROP_FRAME_COUNT) > 5
            cap.release()
    finally:
        detector.stop()
