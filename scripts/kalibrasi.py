"""
Kalibrasi lengkap dalam satu alur, langsung dari kamera:

  Langkah 1  Live kamera. Pastikan botol KOSONG dan HP tidak bergerak,
             lalu tekan SPASI untuk mengambil gambar referensi.
  Langkah 2  Tarik kotak ROI mengelilingi botol (dari dasar botol sampai atas),
             lalu tekan ENTER.
  Langkah 3  Klik ketinggian batas WASPADA (kuning), lalu batas SIAGA (merah)
             yang lebih tinggi. Bisa mengikuti penanda di botol (selotip, spidol,
             kertas) atau ditentukan bebas. Tekan S untuk menyimpan.

Hasil: config/calibration.json dan data/reference.png.
Jika dashboard sedang berjalan, hasil kalibrasi otomatis dimuat ulang. Namun webcam
biasanya hanya bisa dipakai satu program, jadi matikan dashboard dulu.

Cara pakai:  kalibrasi.bat   (atau: venv\\Scripts\\python.exe scripts\\kalibrasi.py)
"""

import os
import sys

import cv2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.camera.video_source import VideoSource, describe_source
from src.config import CALIBRATION_PATH, REFERENCE_PATH, load_config, parse_source
from src.detection.calibration import Calibration, save_calibration, save_reference

WINDOW = "Kalibrasi EWS"
MAX_DISPLAY_H = 720
YELLOW, RED, GREEN = (0, 255, 255), (0, 0, 255), (0, 255, 0)


def banner(img, lines, color=(255, 255, 255)):
    h_line = 26
    cv2.rectangle(img, (0, 0), (img.shape[1], 12 + h_line * len(lines)), (0, 0, 0), -1)
    for i, text in enumerate(lines):
        cv2.putText(img, text, (10, 28 + i * h_line), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1, cv2.LINE_AA)
    return img


class Display:
    """Konversi koordinat antara frame asli dan jendela yang diperkecil."""

    def __init__(self, frame):
        h, w = frame.shape[:2]
        self.scale = min(1.0, MAX_DISPLAY_H / h)
        self.size = (int(w * self.scale), int(h * self.scale))

    def show(self, frame):
        return cv2.resize(frame, self.size) if self.scale != 1.0 else frame.copy()

    def to_frame(self, v):
        return int(round(v / self.scale))

    def to_display(self, v):
        return int(round(v * self.scale))


def step_live(source):
    """Tampilkan live kamera sampai SPASI ditekan. Mengembalikan frame referensi atau None."""
    while True:
        ok, frame = source.read()
        if not ok or frame is None:
            print("Gagal membaca frame dari kamera.")
            return None
        h, w = frame.shape[:2]
        disp = Display(frame)
        img = banner(disp.show(frame), [
            f"LANGKAH 1/3  Kamera: {describe_source(source.source)}  {w}x{h}",
            "Pastikan botol KOSONG dan HP tidak bergerak.",
            "SPASI = ambil gambar referensi    Q = keluar",
            "Layar hitam / tulisan 'Start DroidCam'? DroidCam belum tersambung: tekan Q,",
            "buka DroidCam di HP, klik Start di DroidCam Client, lalu jalankan lagi.",
        ])
        cv2.imshow(WINDOW, img)
        key = cv2.waitKey(1) & 0xFF
        if key == ord(" "):
            return frame
        if key in (ord("q"), 27):
            return None


def step_roi(reference):
    disp = Display(reference)
    img = banner(disp.show(reference), [
        "LANGKAH 2/3  Tarik kotak mengelilingi botol, dari DASAR botol sampai atas.",
        "ENTER / SPASI = lanjut    C = ulangi dari langkah 1",
    ])
    rect = cv2.selectROI(WINDOW, img, showCrosshair=True, fromCenter=False)
    x, y, w, h = rect
    if w == 0 or h == 0:
        return None
    return {"x": disp.to_frame(x), "y": disp.to_frame(y), "w": disp.to_frame(w), "h": disp.to_frame(h)}


def step_lines(reference, roi):
    """Mengembalikan (y_waspada, y_siaga), "ulang", atau None (keluar)."""
    disp = Display(reference)
    clicks = []
    message = [""]

    def on_mouse(event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN or len(clicks) >= 2:
            return
        fy = disp.to_frame(y)
        if not (roi["y"] <= fy <= roi["y"] + roi["h"]):
            message[0] = "Garis harus berada di dalam kotak ROI (hijau)."
            return
        clicks.append(fy)
        message[0] = ""

    cv2.setMouseCallback(WINDOW, on_mouse)

    while True:
        img = disp.show(reference)
        rx, ry = disp.to_display(roi["x"]), disp.to_display(roi["y"])
        rw, rh = disp.to_display(roi["w"]), disp.to_display(roi["h"])
        cv2.rectangle(img, (rx, ry), (rx + rw, ry + rh), GREEN, 2)
        for i, fy in enumerate(clicks):
            color, label = (YELLOW, "WASPADA") if i == 0 else (RED, "SIAGA")
            dy = disp.to_display(fy)
            cv2.line(img, (rx, dy), (rx + rw, dy), color, 2)
            cv2.putText(img, label, (rx + rw + 6, dy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if len(clicks) == 0:
            hint = "Klik ketinggian batas WASPADA (kuning)."
        elif len(clicks) == 1:
            hint = "Klik ketinggian batas SIAGA (merah), lebih tinggi dari WASPADA."
        else:
            hint = "S = simpan    R = ulangi klik"
        lines = ["LANGKAH 3/3  " + hint, "R = ulangi klik    C = ulangi dari langkah 1    Q = keluar"]
        if message[0]:
            lines.append(message[0])
        cv2.imshow(WINDOW, banner(img, lines))

        key = cv2.waitKey(20) & 0xFF
        if key == ord("r"):
            clicks.clear()
            message[0] = ""
        elif key == ord("c"):
            return "ulang"
        elif key in (ord("q"), 27):
            return None
        elif key == ord("s") and len(clicks) == 2:
            y_waspada, y_siaga = clicks
            if y_siaga >= y_waspada:
                message[0] = "Garis MERAH harus di atas garis KUNING. Tekan R lalu klik ulang."
                continue
            return y_waspada, y_siaga


def main():
    cam = load_config()["camera"]
    source = VideoSource(parse_source(cam["source"]), cam["width"], cam["height"])
    print(f"Membuka {describe_source(source.source)} ...")
    if not source.open():
        print("Kamera tidak bisa dibuka.")
        print("- Pastikan DroidCam Client sudah tersambung ke HP.")
        print("- Jalankan cek_kamera.bat untuk memastikan nomor webcam di config.yaml.")
        print("- Matikan dashboard (run.bat) jika sedang berjalan, karena webcam sedang dipakai.")
        return

    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    try:
        while True:
            reference = step_live(source)
            if reference is None:
                print("Dibatalkan, tidak ada yang disimpan.")
                return

            roi = step_roi(reference)
            if roi is None:
                continue

            result = step_lines(reference, roi)
            if result == "ulang":
                continue
            if result is None:
                print("Dibatalkan, tidak ada yang disimpan.")
                return

            y_waspada, y_siaga = result
            h, w = reference.shape[:2]
            calibration = Calibration(roi=roi, y_waspada=y_waspada, y_siaga=y_siaga, frame_width=w, frame_height=h)
            problems = calibration.validate()
            if problems:
                print("Kalibrasi tidak valid:", " ".join(problems))
                continue

            save_reference(reference)
            save_calibration(calibration)
            print("=" * 60)
            print("KALIBRASI TERSIMPAN")
            print(f"  Resolusi : {w}x{h}")
            print(f"  ROI      : {roi}")
            print(f"  Waspada  : Y={y_waspada}")
            print(f"  Siaga    : Y={y_siaga}")
            print(f"  File     : {CALIBRATION_PATH}")
            print(f"             {REFERENCE_PATH}")
            print("=" * 60)
            return
    finally:
        source.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
