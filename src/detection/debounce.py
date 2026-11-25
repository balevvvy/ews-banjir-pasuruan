"""
Debounce status: status mentah harus bertahan sama selama `duration_sec`
sebelum menjadi status terkonfirmasi. Mencegah alarm palsu akibat kedipan sesaat.
"""

import time

from src.detection.water_level import NORMAL


class DebounceAlertManager:
    def __init__(self, duration_sec: float = 5, initial_status: str = NORMAL, clock=time.monotonic):
        self.duration_sec = duration_sec
        self._clock = clock
        self.confirmed_status = initial_status
        self.pending_status = initial_status
        self.pending_since = clock()

    def update(self, raw_status: str) -> tuple[str, bool]:
        """Mengembalikan (status_terkonfirmasi, baru_saja_berubah)."""
        now = self._clock()
        if raw_status != self.pending_status:
            self.pending_status = raw_status
            self.pending_since = now
            return self.confirmed_status, False

        if self.pending_status != self.confirmed_status and now - self.pending_since >= self.duration_sec:
            self.confirmed_status = self.pending_status
            return self.confirmed_status, True

        return self.confirmed_status, False

    def reset(self, status: str = NORMAL):
        self.confirmed_status = status
        self.pending_status = status
        self.pending_since = self._clock()
