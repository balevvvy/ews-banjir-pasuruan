"""
Cari nomor webcam DroidCam.

DroidCam (USB maupun WiFi lewat aplikasi DroidCam Client) muncul di Windows sebagai
webcam virtual. Skrip ini mencoba webcam #0 sampai #5, lalu menampilkan cuplikannya
berdampingan supaya terlihat nomor mana yang berisi gambar dari HP.

Cara pakai:  cek_kamera.bat   (atau: venv\\Scripts\\python.exe scripts\\cek_kamera.py)
"""

import os
import sys
import time

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.camera.video_source import VideoSource
from src.config import load_config

MAX_INDEX = 5
TILE_W, TILE_H = 480, 270


def grab(index: int, width: int, height: int):
    source = VideoSource(index, width, height)
    if not source.open():
        return None
    frame = None
    deadline = time.monotonic() + 3
    # Beberapa frame pertama webcam virtual sering masih hitam
    while time.monotonic() < deadline:
        ok, f = source.read()
        if ok and f is not None:
            frame = f
            if f.mean() > 5:
                break
    source.release()
    return frame


def tile(frame, label: str):
    if frame is None:
        img = np.zeros((TILE_H, TILE_W, 3), dtype=np.uint8)
    else:
        img = cv2.resize(frame, (TILE_W, TILE_H))
    cv2.rectangle(img, (0, 0), (TILE_W, 34), (0, 0, 0), -1)
    cv2.putText(img, label, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    return img


def main():
    cam = load_config()["camera"]
    print(f"camera.source di config.yaml saat ini: {cam['source']!r}")
    print("Mencari webcam #0 sampai #%d ..." % MAX_INDEX)

    tiles = []
    for i in range(MAX_INDEX + 1):
        frame = grab(i, cam["width"], cam["height"])
        if frame is None:
            print(f"  #{i}: tidak ada")
            continue
        h, w = frame.shape[:2]
        dark = " (gambar hitam)" if frame.mean() <= 5 else ""
        print(f"  #{i}: {w}x{h}{dark}")
        tiles.append(tile(frame, f"#{i}  {w}x{h}{dark}"))

    if not tiles:
        print("\nTidak ada webcam. Pastikan DroidCam Client di laptop sudah tersambung (tombol Start).")
        return

    print("\nIsi camera.source di config/config.yaml dengan nomor yang menampilkan gambar dari HP.")
    while len(tiles) % 2:
        tiles.append(tile(None, ""))
    rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]
    cv2.imshow("Cek Kamera - tekan tombol apa saja untuk menutup", np.vstack(rows))
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
