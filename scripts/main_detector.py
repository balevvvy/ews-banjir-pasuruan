"""
Mode jendela (tanpa dashboard web): tampilkan hasil deteksi dan mask berdampingan.
Berguna untuk menyetel sensitivitas/blur dan menjelaskan cara kerja metode.

Tombol:  R = ambil ulang referensi    Q / ESC = keluar
"""

import os
import sys
import time

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.config import load_config
from src.detection.detector import WaterLevelDetector

DISPLAY_H = 540


def fit(img, height):
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * height / h), height))


def main():
    detector = WaterLevelDetector(load_config())
    detector.on_alert = lambda status, pesan: print(f"[{time.strftime('%H:%M:%S')}] {status}: {pesan}")
    detector.start()

    cv2.namedWindow("Settings", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Settings", 400, 120)
    cv2.createTrackbar("Sensitivity", "Settings", detector.sensitivity, 100, lambda v: None)
    cv2.createTrackbar("Blur", "Settings", detector.blur_size, 51, lambda v: None)

    try:
        while True:
            detector.sensitivity = max(cv2.getTrackbarPos("Sensitivity", "Settings"), 1)
            detector.blur_size = cv2.getTrackbarPos("Blur", "Settings")

            annotated = detector.get_frame("annotated")
            if annotated is None:
                view = np.zeros((DISPLAY_H, DISPLAY_H * 16 // 9, 3), dtype=np.uint8)
                cv2.putText(view, detector.message[:70], (20, DISPLAY_H // 2), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (180, 180, 180), 1)
            else:
                panels = [fit(annotated, DISPLAY_H)]
                mask = detector.get_frame("mask")
                if mask is not None:
                    panels.append(fit(mask, DISPLAY_H))
                view = np.hstack(panels)
            cv2.imshow("EWS Banjir", view)

            key = cv2.waitKey(30) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("r"):
                ok, message = detector.request_reference_capture()
                print(message)
    finally:
        detector.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
