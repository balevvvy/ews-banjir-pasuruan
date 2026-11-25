"""
Buat gambar setiap tahap metode deteksi untuk laporan/presentasi (docs/gambar/).

  1 referensi      gambar kondisi normal (botol kosong)
  2 frame          frame saat ini (ada air)
  3 selisih        |referensi - frame| setelah grayscale + blur
  4 threshold      selisih > sensitivitas
  5 morfologi      setelah opening + closing
  6 pemindaian     jumlah piksel berubah per baris di ROI, dipindai dari dasar ke atas
  7 hasil          overlay ROI, garis batas, permukaan air, dan status

Cara pakai (setelah kalibrasi, dengan air di dalam botol):
  venv\\Scripts\\python.exe scripts\\gambar_tahapan.py                 # ambil frame dari kamera
  venv\\Scripts\\python.exe scripts\\gambar_tahapan.py --frame foto.png
  venv\\Scripts\\python.exe scripts\\gambar_tahapan.py --sintetis      # adegan buatan (ilustrasi)
"""

import argparse
import os
import sys

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.camera.video_source import VideoSource
from src.config import load_config, parse_source
from src.detection.calibration import Calibration, load_calibration, load_reference
from src.detection.water_level import (
    compute_change_mask, get_status, get_water_level_y, preprocess, water_percentage,
)

OUT_DIR = os.path.join(BASE_DIR, "docs", "gambar")
STATUS_COLORS = {"NORMAL": (0, 200, 0), "WASPADA": (0, 220, 255), "SIAGA": (0, 0, 255)}


def crop(img, roi, margin=0.25):
    """Potong area sekitar ROI supaya detail terlihat di laporan."""
    h, w = img.shape[:2]
    mx, my = int(roi["w"] * margin) + 20, int(roi["h"] * 0.1) + 20
    x0, y0 = max(roi["x"] - mx, 0), max(roi["y"] - my, 0)
    x1, y1 = min(roi["x"] + roi["w"] + mx, w), min(roi["y"] + roi["h"] + my, h)
    return img[y0:y1, x0:x1]


def to_bgr(img):
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img.copy()


def draw_lines(img, cal, water_y=None):
    r = cal.roi
    cv2.rectangle(img, (r["x"], r["y"]), (r["x"] + r["w"], r["y"] + r["h"]), (0, 255, 0), 2)
    cv2.line(img, (r["x"], cal.y_waspada), (r["x"] + r["w"], cal.y_waspada), (0, 255, 255), 2)
    cv2.line(img, (r["x"], cal.y_siaga), (r["x"] + r["w"], cal.y_siaga), (0, 0, 255), 2)
    if water_y is not None:
        cv2.line(img, (r["x"], water_y), (r["x"] + r["w"], water_y), (255, 100, 0), 3)
    return img


def scan_plot(mask, cal, water_y, min_row_coverage=0.15):
    """Grafik batang horizontal: jumlah piksel berubah per baris ROI."""
    r = cal.roi
    counts = np.count_nonzero(mask[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]], axis=1)
    width = 300
    plot = np.full((r["h"], width, 3), 255, dtype=np.uint8)
    for i, c in enumerate(counts):
        length = int(c / max(r["w"], 1) * (width - 20))
        cv2.line(plot, (0, i), (length, i), (180, 120, 40), 1)
    min_px = int(min_row_coverage * (width - 20))
    cv2.line(plot, (min_px, 0), (min_px, r["h"]), (0, 0, 200), 1)
    for y, color in ((cal.y_waspada, (0, 200, 255)), (cal.y_siaga, (0, 0, 255))):
        cv2.line(plot, (0, y - r["y"]), (width, y - r["y"]), color, 1)
    if water_y is not None:
        cv2.line(plot, (0, water_y - r["y"]), (width, water_y - r["y"]), (255, 100, 0), 2)
    cv2.arrowedLine(plot, (width - 12, r["h"] - 10), (width - 12, 10), (80, 80, 80), 2, tipLength=0.03)
    return plot


def synthetic_inputs():
    from tests import scene
    reference = scene.make_frame(None, noise_seed=1)
    frame = scene.make_frame(200, noise_seed=2)
    cal = Calibration(roi=scene.ROI, y_waspada=scene.Y_WASPADA, y_siaga=scene.Y_SIAGA,
                      frame_width=scene.WIDTH, frame_height=scene.HEIGHT)
    return reference, frame, cal


def camera_frame(cfg):
    cam = cfg["camera"]
    source = VideoSource(parse_source(cam["source"]), cam["width"], cam["height"])
    if not source.open():
        sys.exit("Kamera tidak bisa dibuka. Matikan dashboard dulu jika sedang berjalan.")
    frame = None
    for _ in range(10):   # buang beberapa frame awal
        ok, f = source.read()
        if ok:
            frame = f
    source.release()
    if frame is None:
        sys.exit("Tidak ada frame dari kamera.")
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--frame", help="file gambar sebagai frame (default: ambil dari kamera)")
    parser.add_argument("--sintetis", action="store_true", help="pakai adegan buatan, tanpa kamera/kalibrasi")
    args = parser.parse_args()
    cfg = load_config()
    det = cfg["detection"]

    if args.sintetis:
        reference, frame, cal = synthetic_inputs()
        prefix = "ilustrasi_"
    else:
        cal, reference = load_calibration(), load_reference()
        if cal is None or reference is None:
            sys.exit("Belum dikalibrasi. Jalankan kalibrasi.bat dulu.")
        frame = cv2.imread(args.frame) if args.frame else camera_frame(cfg)
        if frame is None or frame.shape[:2] != reference.shape[:2]:
            sys.exit("Ukuran frame tidak sama dengan gambar referensi.")
        prefix = ""

    ref_blur = preprocess(reference, det["blur_size"])
    frame_blur = preprocess(frame, det["blur_size"])
    diff = cv2.absdiff(ref_blur, frame_blur)
    _, thresh = cv2.threshold(diff, det["sensitivity"], 255, cv2.THRESH_BINARY)
    mask = compute_change_mask(ref_blur, frame_blur, det["sensitivity"])
    water_y = get_water_level_y(mask, cal.roi)
    status = get_status(water_y, cal.y_waspada, cal.y_siaga)

    diff_vis = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
    result = draw_lines(frame.copy(), cal, water_y)

    images = {
        "1_referensi": draw_lines(reference.copy(), cal),
        "2_frame": frame.copy(),
        "3_selisih": to_bgr(diff_vis),
        "4_threshold": to_bgr(thresh),
        "5_morfologi": draw_lines(to_bgr(mask), cal, water_y),
        "7_hasil": result,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, img in images.items():
        img = crop(img, cal.roi).copy()
        if name == "7_hasil":
            label = f"{status} {water_percentage(water_y, cal.roi)}%"
            cv2.rectangle(img, (0, 0), (img.shape[1], 30), STATUS_COLORS[status], -1)
            cv2.putText(img, label, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.imwrite(os.path.join(OUT_DIR, f"{prefix}{name}.png"), img)
    cv2.imwrite(os.path.join(OUT_DIR, f"{prefix}6_pemindaian.png"), scan_plot(mask, cal, water_y))

    print(f"Gambar disimpan di {OUT_DIR} (awalan '{prefix}')")
    print(f"Hasil: water_y={water_y}, ketinggian={water_percentage(water_y, cal.roi)}%, status={status}")


if __name__ == "__main__":
    main()
