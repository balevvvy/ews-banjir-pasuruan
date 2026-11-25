"""
Fungsi inti deteksi ketinggian air (classical computer vision).

Metode: Bottom-Up Frame Differencing
  1. Frame dan gambar referensi (kondisi normal / botol kosong) diubah ke grayscale + blur.
  2. Selisih absolut keduanya di-threshold -> mask perubahan.
  3. Morfologi OPEN (hapus bintik noise) lalu CLOSE (tutup lubang).
  4. Di dalam ROI, baris dipindai dari dasar ke atas. Permukaan air adalah baris
     teratas yang masih tersambung dengan area berubah di dasar ROI.
"""

import cv2
import numpy as np

NORMAL = "NORMAL"
WASPADA = "WASPADA"
SIAGA = "SIAGA"

_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))


def normalize_blur_size(blur_size: int) -> int:
    """Ukuran kernel Gaussian harus ganjil dan minimal 3."""
    blur_size = int(blur_size)
    if blur_size % 2 == 0:
        blur_size += 1
    return max(blur_size, 3)


def preprocess(frame: np.ndarray, blur_size: int) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    k = normalize_blur_size(blur_size)
    return cv2.GaussianBlur(gray, (k, k), 0)


def compute_change_mask(reference_blur: np.ndarray, frame_blur: np.ndarray, sensitivity: int) -> np.ndarray:
    diff = cv2.absdiff(reference_blur, frame_blur)
    _, mask = cv2.threshold(diff, int(sensitivity), 255, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, _KERNEL, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, _KERNEL, iterations=3)
    return mask


def get_water_level_y(mask, roi, min_row_coverage=0.15, max_gap=20, min_water_height=10, max_bottom_offset=0.40):
    """
    Cari Y permukaan air (koordinat frame) dengan memindai baris ROI dari dasar ke atas.

    - Baris dihitung "air" jika minimal `min_row_coverage` lebarnya berubah.
    - Baris air pertama harus berada di `max_bottom_offset` bagian bawah ROI,
      sehingga perubahan yang melayang di atas (pantulan, tangan) diabaikan.
    - Celah hingga `max_gap` baris masih ditoleransi.
    - Tinggi kolom air minimal `min_water_height` piksel.

    Mengembalikan None jika tidak ada air terdeteksi.
    """
    x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
    roi_mask = mask[y:y + h, x:x + w]
    h = roi_mask.shape[0]
    if h == 0:
        return None

    row_counts = np.count_nonzero(roi_mask, axis=1)
    min_pixels = max(int(w * min_row_coverage), 4)

    water_top_rel_y = None
    first_water_r = None
    gap_count = 0
    in_water = False

    for r in range(h - 1, -1, -1):
        if row_counts[r] >= min_pixels:
            if not in_water:
                if (h - 1 - r) > (h * max_bottom_offset):
                    break
                first_water_r = r
                in_water = True
            water_top_rel_y = r
            gap_count = 0
        elif in_water:
            gap_count += 1
            if gap_count > max_gap:
                break

    if in_water and first_water_r - water_top_rel_y >= min_water_height:
        return y + water_top_rel_y
    return None


def get_status(water_y, y_waspada, y_siaga) -> str:
    """Y kecil = posisi lebih tinggi di gambar."""
    if water_y is None:
        return NORMAL
    if water_y <= y_siaga:
        return SIAGA
    if water_y <= y_waspada:
        return WASPADA
    return NORMAL


def water_percentage(water_y, roi) -> float:
    """Tinggi air sebagai persen tinggi ROI (0 = dasar ROI / tidak terdeteksi)."""
    if water_y is None:
        return 0.0
    bottom = roi["y"] + roi["h"]
    pct = (bottom - water_y) / roi["h"] * 100
    return round(max(0.0, min(100.0, pct)), 1)
