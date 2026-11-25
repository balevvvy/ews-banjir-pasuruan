import numpy as np
import pytest

from src.detection.water_level import (
    NORMAL, SIAGA, WASPADA, compute_change_mask, get_status, get_water_level_y,
    normalize_blur_size, preprocess, water_percentage,
)
from tests import scene

ROI = {"x": 10, "y": 10, "w": 50, "h": 100}   # dasar ROI di y=110


def mask_with_rows(rows, width=100, height=150, x0=10, x1=60):
    mask = np.zeros((height, width), dtype=np.uint8)
    for r in rows:
        mask[r, x0:x1] = 255
    return mask


class TestNormalizeBlurSize:
    @pytest.mark.parametrize("given, expected", [(21, 21), (20, 21), (1, 3), (0, 3), (4, 5)])
    def test_result_is_odd_and_at_least_3(self, given, expected):
        assert normalize_blur_size(given) == expected


class TestGetWaterLevelY:
    def test_empty_mask_returns_none(self):
        assert get_water_level_y(mask_with_rows([]), ROI) is None

    def test_water_from_bottom_returns_top_row(self):
        mask = mask_with_rows(range(70, 110))
        assert get_water_level_y(mask, ROI) == 70

    def test_change_floating_near_top_is_ignored(self):
        # Pantulan/tangan di bagian atas ROI, tidak tersambung ke dasar
        mask = mask_with_rows(range(15, 40))
        assert get_water_level_y(mask, ROI) is None

    def test_column_shorter_than_min_height_is_ignored(self):
        mask = mask_with_rows(range(104, 110))
        assert get_water_level_y(mask, ROI) is None

    def test_small_gap_is_tolerated(self):
        rows = list(range(90, 110)) + list(range(60, 80))   # celah 10 baris
        assert get_water_level_y(mask_with_rows(rows), ROI) == 60

    def test_large_gap_stops_scan(self):
        rows = list(range(90, 110)) + list(range(20, 50))   # celah 40 baris
        assert get_water_level_y(mask_with_rows(rows), ROI) == 90

    def test_sparse_rows_below_coverage_are_not_water(self):
        mask = np.zeros((150, 100), dtype=np.uint8)
        mask[60:110, 10:13] = 255                           # hanya 3 piksel per baris
        assert get_water_level_y(mask, ROI) is None


class TestGetStatus:
    @pytest.mark.parametrize("water_y, expected", [
        (None, NORMAL),
        (300, NORMAL),
        (261, NORMAL),
        (260, WASPADA),   # tepat di garis kuning
        (200, WASPADA),
        (160, SIAGA),     # tepat di garis merah
        (100, SIAGA),
    ])
    def test_thresholds(self, water_y, expected):
        assert get_status(water_y, y_waspada=260, y_siaga=160) == expected


class TestWaterPercentage:
    def test_none_is_zero(self):
        assert water_percentage(None, ROI) == 0.0

    def test_bottom_and_top(self):
        assert water_percentage(110, ROI) == 0.0
        assert water_percentage(10, ROI) == 100.0

    def test_middle(self):
        assert water_percentage(60, ROI) == 50.0

    def test_clamped(self):
        assert water_percentage(0, ROI) == 100.0
        assert water_percentage(140, ROI) == 0.0


class TestPipelineOnSyntheticScene:
    def detect(self, water_y, sensitivity=30, blur=21):
        ref = preprocess(scene.make_frame(None, noise_seed=1), blur)
        frame = preprocess(scene.make_frame(water_y, noise_seed=2), blur)
        mask = compute_change_mask(ref, frame, sensitivity)
        return get_water_level_y(mask, scene.ROI)

    def test_empty_bottle_detects_nothing(self):
        assert self.detect(None) is None

    @pytest.mark.parametrize("true_y", [380, 300, 220, 150])
    def test_detected_level_is_close_to_true_level(self, true_y):
        detected = self.detect(true_y)
        assert detected is not None
        assert abs(detected - true_y) <= 15

    def test_status_follows_water_level(self):
        statuses = [get_status(self.detect(y), scene.Y_WASPADA, scene.Y_SIAGA) for y in (380, 220, 140)]
        assert statuses == [NORMAL, WASPADA, SIAGA]
