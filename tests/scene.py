"""Adegan sintetis untuk pengujian: botol di depan kertas kuning/merah, diisi air dari bawah."""

import cv2
import numpy as np

WIDTH, HEIGHT = 640, 480
ROI = {"x": 260, "y": 80, "w": 120, "h": 360}       # botol: y 80..440
Y_WASPADA = 260                                      # batas bawah kertas kuning
Y_SIAGA = 160                                        # batas bawah kertas merah


def make_frame(water_y=None, noise_seed=None):
    """water_y = Y permukaan air (None = botol kosong)."""
    img = np.full((HEIGHT, WIDTH, 3), (200, 200, 200), dtype=np.uint8)
    x, w = ROI["x"], ROI["w"]
    cv2.rectangle(img, (x - 40, 100), (x + w + 40, Y_SIAGA), (40, 40, 220), -1)        # merah
    cv2.rectangle(img, (x - 40, Y_SIAGA), (x + w + 40, Y_WASPADA), (40, 220, 240), -1)  # kuning
    bottom = ROI["y"] + ROI["h"]
    cv2.rectangle(img, (x + 10, ROI["y"]), (x + w - 10, bottom), (230, 230, 230), 2)    # dinding botol
    if water_y is not None:
        water = img[water_y:bottom, x + 12:x + w - 12].astype(np.int16)
        water = water * np.array([1.0, 0.6, 0.4]) + np.array([60, 0, 0])               # air kebiruan
        img[water_y:bottom, x + 12:x + w - 12] = np.clip(water, 0, 255).astype(np.uint8)
    if noise_seed is not None:
        rng = np.random.default_rng(noise_seed)
        img = np.clip(img.astype(np.int16) + rng.integers(-4, 5, img.shape), 0, 255).astype(np.uint8)
    return img
