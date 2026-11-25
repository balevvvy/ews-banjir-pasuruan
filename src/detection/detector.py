"""
Pipeline deteksi yang berjalan di thread terpisah:
kamera -> mask perubahan (di dalam ROI) -> Y permukaan air -> median 15 pembacaan
-> status mentah -> debounce -> status terkonfirmasi -> callback ke database.

Status yang dilaporkan:
  NORMAL / WASPADA / SIAGA  -> hasil deteksi
  OFFLINE                   -> kamera tidak terhubung
  BELUM_KALIBRASI           -> kalibrasi/referensi belum ada atau resolusi kamera berubah
"""

import threading
import time
from collections import deque

import cv2
import numpy as np

from src.camera.video_source import VideoSource, describe_source
from src.config import CALIBRATION_PATH, RECORDINGS_DIR, REFERENCE_PATH, parse_source
from src.detection import calibration as cal_store
from src.detection.debounce import DebounceAlertManager
from src.detection.recorder import VideoRecorder
from src.detection.water_level import (
    NORMAL, SIAGA, WASPADA, compute_change_mask, get_status, get_water_level_y,
    preprocess, water_percentage,
)

OFFLINE = "OFFLINE"
BELUM_KALIBRASI = "BELUM_KALIBRASI"
DETECTION_STATUSES = (NORMAL, WASPADA, SIAGA)

# Warna BGR
STATUS_COLORS = {
    NORMAL: (0, 200, 0),
    WASPADA: (0, 220, 255),
    SIAGA: (0, 0, 255),
    OFFLINE: (120, 120, 120),
    BELUM_KALIBRASI: (120, 120, 120),
}

ALERT_MESSAGES = {
    SIAGA: "Air mencapai zona MERAH!",
    WASPADA: "Air mendekati batas merah.",
    NORMAL: "Air kembali ke level normal.",
    OFFLINE: "Kamera terputus.",
}

HISTORY_SIZE = 15
NO_DETECT_RESET_FRAMES = 10
CALIBRATION_CHECK_SEC = 2.0
RECONNECT_DELAY_SEC = 2.0
MAX_READ_FAILURES = 5
STREAM_MAX_HEIGHT = 720


class WaterLevelDetector:
    def __init__(self, config: dict, calibration_path: str = CALIBRATION_PATH,
                 reference_path: str = REFERENCE_PATH, recordings_dir: str = RECORDINGS_DIR):
        cam, det = config["camera"], config["detection"]
        self.calibration_path = calibration_path
        self.reference_path = reference_path
        self.source = parse_source(cam["source"])
        self.source_label = describe_source(self.source)
        self._width = cam.get("width")
        self._height = cam.get("height")

        self.sensitivity = int(det["sensitivity"])
        self.blur_size = int(det["blur_size"])
        self.debounce = DebounceAlertManager(duration_sec=det["debounce_sec"])
        self._min_process_interval = 1.0 / max(float(det["process_fps"]), 1.0)
        self.reading_interval_sec = float(config["server"]["reading_interval_sec"])

        # Status publik (dibaca oleh web server)
        self.status = OFFLINE
        self.raw_status = OFFLINE
        self.message = "Menghubungkan ke kamera..."
        self.water_y = None
        self.water_pct = None
        self.camera_connected = False
        self.frame_size = None
        self.last_frame_time = 0.0

        self.on_reading = None   # fn(water_y, water_pct, status)
        self.on_alert = None     # fn(status, pesan)

        self.recorder = VideoRecorder(recordings_dir, fps=max(float(det["process_fps"]), 1.0))

        self._calibration = None
        self._reference_gray = None
        self._reference_blur = None
        self._reference_blur_key = None
        self._files_mtime = (0.0, 0.0)
        self._last_calibration_check = 0.0

        self._y_history = deque(maxlen=HISTORY_SIZE)
        self._no_detect_count = 0
        self._last_reading_time = 0.0
        self._was_connected = False

        self._frame_lock = threading.Lock()
        self._latest = {"annotated": None, "mask": None}
        self._frame_id = 0
        self._jpeg_cache = {}

        self._reference_request = threading.Event()
        self._reference_done = threading.Event()
        self._reference_result = (False, "")

        self._stop_event = threading.Event()
        self._thread = None

    # ------------------------------------------------------------------ kontrol

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._load_calibration_files(force=True)
        self._thread = threading.Thread(target=self._run, name="detector", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self.recorder.stop()

    def request_reference_capture(self, timeout: float = 5.0) -> tuple[bool, str]:
        """Jadikan frame kamera berikutnya sebagai gambar referensi baru."""
        if not self.camera_connected:
            return False, "Kamera belum terhubung."
        self._reference_done.clear()
        self._reference_request.set()
        if not self._reference_done.wait(timeout):
            self._reference_request.clear()
            return False, "Tidak ada frame dari kamera."
        return self._reference_result

    def start_recording(self) -> list[str]:
        if not self.camera_connected or self.frame_size is None:
            raise RuntimeError("Kamera belum terhubung.")
        return self.recorder.start(self.frame_size)

    def stop_recording(self) -> dict:
        return self.recorder.stop()

    # ------------------------------------------------------------------ data untuk web

    @property
    def calibration(self):
        return self._calibration

    def get_status_dict(self) -> dict:
        cal = self._calibration
        rec = self.recorder
        data = {
            "status": self.status,
            "raw_status": self.raw_status,
            "message": self.message,
            "water_y": self.water_y,
            "water_pct": self.water_pct,
            "waspada_pct": None,
            "siaga_pct": None,
            "camera_connected": self.camera_connected,
            "source": self.source_label,
            "frame_size": list(self.frame_size) if self.frame_size else None,
            "timestamp": self.last_frame_time,
            "recording": rec.active,
            "recording_sec": round(time.time() - rec.started_at, 1) if rec.active else 0,
        }
        if cal is not None:
            data["waspada_pct"] = water_percentage(cal.y_waspada, cal.roi)
            data["siaga_pct"] = water_percentage(cal.y_siaga, cal.roi)
        return data

    def get_frame(self, view: str = "annotated"):
        """Frame terbaru (BGR). Frame tidak pernah diubah setelah dipublikasikan."""
        with self._frame_lock:
            return self._latest.get(view)

    def get_jpeg(self, view: str = "annotated") -> bytes | None:
        with self._frame_lock:
            frame = self._latest.get(view)
            key = (self._frame_id, view)
            cached = self._jpeg_cache.get(key)
        if frame is None:
            return None
        if cached is not None:
            return cached

        h, w = frame.shape[:2]
        if h > STREAM_MAX_HEIGHT:
            scale = STREAM_MAX_HEIGHT / h
            frame = cv2.resize(frame, (int(w * scale), STREAM_MAX_HEIGHT))
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            return None
        data = buf.tobytes()
        with self._frame_lock:
            if self._frame_id == key[0]:
                self._jpeg_cache = {k: v for k, v in self._jpeg_cache.items() if k[0] == key[0]}
                self._jpeg_cache[key] = data
        return data

    # ------------------------------------------------------------------ loop kamera

    def _run(self):
        source = VideoSource(self.source, self._width, self._height)
        while not self._stop_event.is_set():
            if not source.open():
                self._go_offline(f"Kamera tidak ditemukan ({self.source_label}). Mencoba lagi...")
                self._stop_event.wait(RECONNECT_DELAY_SEC)
                continue

            print(f"[detektor] Terhubung ke {self.source_label}")
            self.camera_connected = True
            self._was_connected = True
            self._reset_tracking()
            failures = 0
            last_processed = 0.0

            while not self._stop_event.is_set():
                ok, frame = source.read()
                if not ok or frame is None:
                    failures += 1
                    if failures >= MAX_READ_FAILURES:
                        break
                    time.sleep(0.1)
                    continue
                failures = 0
                self.last_frame_time = time.time()

                if self._reference_request.is_set():
                    self._capture_reference(frame)

                now = time.monotonic()
                if now - last_processed < self._min_process_interval:
                    continue
                last_processed = now
                self._process_frame(frame)

            source.release()
            if not self._stop_event.is_set():
                self._go_offline(f"Kamera terputus ({self.source_label}). Menyambung ulang...")
                self._stop_event.wait(RECONNECT_DELAY_SEC)

        source.release()

    def _go_offline(self, message: str):
        was_online = self.camera_connected
        self.camera_connected = False
        self.status = OFFLINE
        self.raw_status = OFFLINE
        self.message = message
        self.water_y = None
        self.water_pct = None
        with self._frame_lock:
            self._latest = {"annotated": None, "mask": None}
            self._frame_id += 1
        if self.recorder.active:
            self.recorder.stop()
        if was_online and self.on_alert:
            self.on_alert(OFFLINE, ALERT_MESSAGES[OFFLINE])

    def _reset_tracking(self):
        self._y_history.clear()
        self._no_detect_count = 0
        self.debounce.reset(NORMAL)

    # ------------------------------------------------------------------ kalibrasi & referensi

    def _load_calibration_files(self, force: bool = False):
        mtimes = (cal_store.file_mtime(self.calibration_path), cal_store.file_mtime(self.reference_path))
        if not force and mtimes == self._files_mtime:
            return
        self._files_mtime = mtimes
        self._calibration = cal_store.load_calibration(self.calibration_path)
        reference = cal_store.load_reference(self.reference_path)
        self._reference_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY) if reference is not None else None
        self._reference_blur_key = None
        self._reset_tracking()
        if not force:
            print("[detektor] File kalibrasi/referensi berubah, dimuat ulang.")

    def _capture_reference(self, frame):
        try:
            cal_store.save_reference(frame, self.reference_path)
            self._reference_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self._reference_blur_key = None
            self._files_mtime = (self._files_mtime[0], cal_store.file_mtime(self.reference_path))
            self._reset_tracking()
            self._reference_result = (True, "Referensi baru disimpan.")
        except Exception as e:
            self._reference_result = (False, f"Gagal menyimpan referensi: {e}")
        self._reference_request.clear()
        self._reference_done.set()

    def _calibration_problem(self, frame) -> str | None:
        cal = self._calibration
        if cal is None:
            return "Belum dikalibrasi. Jalankan kalibrasi.bat"
        if self._reference_gray is None:
            return "Gambar referensi belum ada. Jalankan kalibrasi.bat"
        h, w = frame.shape[:2]
        if not cal.matches(frame):
            return (f"Resolusi kamera {w}x{h} berbeda dengan kalibrasi "
                    f"{cal.frame_width}x{cal.frame_height}. Jalankan kalibrasi.bat")
        if self._reference_gray.shape[:2] != (h, w):
            return "Ukuran gambar referensi tidak cocok. Ambil ulang referensi."
        problems = cal.validate()
        if problems:
            return "Kalibrasi tidak valid: " + " ".join(problems)
        return None

    # ------------------------------------------------------------------ pemrosesan frame

    def _process_frame(self, frame):
        now = time.monotonic()
        if now - self._last_calibration_check >= CALIBRATION_CHECK_SEC:
            self._last_calibration_check = now
            self._load_calibration_files()

        h, w = frame.shape[:2]
        self.frame_size = (w, h)

        problem = self._calibration_problem(frame)
        if problem:
            self.status = BELUM_KALIBRASI
            self.raw_status = BELUM_KALIBRASI
            self.message = problem
            self.water_y = None
            self.water_pct = None
            annotated = self._draw_uncalibrated(frame, problem)
            self._publish(frame, annotated, None)
            return

        cal = self._calibration
        mask = self._compute_mask(frame, cal.roi)
        raw_y = get_water_level_y(mask, cal.roi)

        if raw_y is not None:
            self._y_history.append(raw_y)
            self._no_detect_count = 0
            self.water_y = int(np.median(self._y_history))
        else:
            self._no_detect_count += 1
            if self._no_detect_count > NO_DETECT_RESET_FRAMES:
                self._y_history.clear()
                self.water_y = None

        self.water_pct = water_percentage(self.water_y, cal.roi)
        self.raw_status = get_status(self.water_y, cal.y_waspada, cal.y_siaga)
        confirmed, changed = self.debounce.update(self.raw_status)
        self.status = confirmed
        self.message = ""

        if changed and self.on_alert:
            self.on_alert(confirmed, ALERT_MESSAGES[confirmed])

        if self.on_reading and time.time() - self._last_reading_time >= self.reading_interval_sec:
            self._last_reading_time = time.time()
            self.on_reading(self.water_y, self.water_pct, confirmed)

        annotated = self._draw_overlay(frame, cal)
        mask_view = self._draw_mask_view(mask, cal)
        self._publish(frame, annotated, mask_view)

    def _compute_mask(self, frame, roi) -> np.ndarray:
        """Mask perubahan berukuran frame penuh, tetapi hanya dihitung di dalam ROI."""
        x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
        blur_key = (self.blur_size, x, y, w, h)
        if self._reference_blur_key != blur_key:
            self._reference_blur = preprocess(self._reference_gray[y:y + h, x:x + w], self.blur_size)
            self._reference_blur_key = blur_key

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_blur = preprocess(gray[y:y + h, x:x + w], self.blur_size)
        roi_mask = compute_change_mask(self._reference_blur, frame_blur, self.sensitivity)

        mask = np.zeros(gray.shape, dtype=np.uint8)
        mask[y:y + h, x:x + w] = roi_mask
        return mask

    def _publish(self, raw, annotated, mask_view):
        with self._frame_lock:
            self._latest = {"annotated": annotated, "mask": mask_view}
            self._frame_id += 1
        self.recorder.write(raw, annotated)

    # ------------------------------------------------------------------ gambar overlay

    @staticmethod
    def _scale(frame) -> float:
        return max(frame.shape[0] / 720, 0.5)

    def _draw_status_box(self, img, text):
        s = self._scale(img)
        color = STATUS_COLORS.get(self.status, (120, 120, 120))
        font_scale = 1.4 * s
        thickness = max(int(3 * s), 1)
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        pad = int(14 * s)
        cv2.rectangle(img, (0, 0), (tw + 2 * pad, th + 2 * pad), color, -1)
        cv2.putText(img, text, (pad, th + pad), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)

    def _draw_lines(self, img, cal):
        s = self._scale(img)
        r = cal.roi
        rx, ry, rw, rh = r["x"], r["y"], r["w"], r["h"]
        fs, t = 0.6 * s, max(int(2 * s), 1)
        cv2.rectangle(img, (rx, ry), (rx + rw, ry + rh), (0, 255, 0), t)
        cv2.line(img, (rx, cal.y_waspada), (rx + rw, cal.y_waspada), (0, 255, 255), t)
        cv2.putText(img, "WASPADA", (rx + rw + 5, cal.y_waspada + 5), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 255, 255), t)
        cv2.line(img, (rx, cal.y_siaga), (rx + rw, cal.y_siaga), (0, 0, 255), t)
        cv2.putText(img, "SIAGA", (rx + rw + 5, cal.y_siaga + 5), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 255), t)
        if self.water_y is not None:
            cv2.line(img, (rx, self.water_y), (rx + rw, self.water_y), (255, 100, 0), t + 1)
            cv2.putText(img, f"Air {self.water_pct}%", (rx + rw + 5, self.water_y + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 100, 0), t)

    def _draw_overlay(self, frame, cal):
        img = frame.copy()
        self._draw_lines(img, cal)
        self._draw_status_box(img, self.status)
        return img

    def _draw_mask_view(self, mask, cal):
        img = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        self._draw_lines(img, cal)
        self._draw_status_box(img, "MASK")
        return img

    def _draw_uncalibrated(self, frame, message):
        img = frame.copy()
        self._draw_status_box(img, "BELUM KALIBRASI")
        s = self._scale(img)
        y = img.shape[0] - int(20 * s)
        cv2.putText(img, message, (int(12 * s), y), cv2.FONT_HERSHEY_SIMPLEX, 0.55 * s, (0, 0, 0), max(int(4 * s), 2))
        cv2.putText(img, message, (int(12 * s), y), cv2.FONT_HERSHEY_SIMPLEX, 0.55 * s, (255, 255, 255), max(int(1.5 * s), 1))
        return img
