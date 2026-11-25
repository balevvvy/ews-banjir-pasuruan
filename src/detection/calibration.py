"""
Penyimpanan hasil kalibrasi: ROI, garis Waspada/Siaga, dan resolusi frame saat kalibrasi.
Gambar referensi disimpan terpisah (data/reference.png, lossless agar tidak menambah noise).
"""

import json
import os
from dataclasses import asdict, dataclass

import cv2

from src.config import CALIBRATION_PATH, REFERENCE_PATH


@dataclass
class Calibration:
    roi: dict            # {"x", "y", "w", "h"} dalam piksel frame asli
    y_waspada: int       # batas bawah pita kuning
    y_siaga: int         # batas bawah pita merah (lebih kecil dari y_waspada)
    frame_width: int
    frame_height: int

    def matches(self, frame) -> bool:
        h, w = frame.shape[:2]
        return w == self.frame_width and h == self.frame_height

    def validate(self) -> list[str]:
        """Daftar masalah kalibrasi; kosong berarti valid."""
        problems = []
        r = self.roi
        if r["w"] <= 0 or r["h"] <= 0:
            problems.append("ROI kosong.")
        if r["x"] < 0 or r["y"] < 0 or r["x"] + r["w"] > self.frame_width or r["y"] + r["h"] > self.frame_height:
            problems.append("ROI keluar dari frame.")
        if self.y_siaga >= self.y_waspada:
            problems.append("Garis Siaga (merah) harus berada di atas garis Waspada (kuning).")
        return problems


def load_calibration(path: str = CALIBRATION_PATH) -> Calibration | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Calibration(
            roi={k: int(data["roi"][k]) for k in ("x", "y", "w", "h")},
            y_waspada=int(data["y_waspada"]),
            y_siaga=int(data["y_siaga"]),
            frame_width=int(data["frame_width"]),
            frame_height=int(data["frame_height"]),
        )
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"[kalibrasi] File {path} rusak: {e}")
        return None


def save_calibration(calibration: Calibration, path: str = CALIBRATION_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(calibration), f, indent=4)


def load_reference(path: str = REFERENCE_PATH):
    if not os.path.exists(path):
        return None
    return cv2.imread(path)


def save_reference(frame, path: str = REFERENCE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, frame)


def file_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0
