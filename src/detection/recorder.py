"""
Perekam video: menyimpan dua file sekaligus.
  *_raw.mp4     -> frame asli kamera; bisa dipakai lagi sebagai camera.source (sumber cadangan)
  *_deteksi.mp4 -> frame dengan overlay ROI, garis batas, dan status (untuk ditonton)
"""

import os
import threading
import time

import cv2


class VideoRecorder:
    def __init__(self, directory: str, fps: float):
        self.directory = directory
        self.fps = fps
        self._lock = threading.Lock()
        self._writers = None
        self._size = None
        self.started_at = None
        self.files = []

    @property
    def active(self) -> bool:
        return self._writers is not None

    def start(self, frame_size: tuple[int, int]) -> list[str]:
        with self._lock:
            if self._writers is not None:
                return self.files
            os.makedirs(self.directory, exist_ok=True)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            names = [f"rekaman_{stamp}_raw.mp4", f"rekaman_{stamp}_deteksi.mp4"]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writers = [cv2.VideoWriter(os.path.join(self.directory, n), fourcc, self.fps, frame_size) for n in names]
            if not all(w.isOpened() for w in writers):
                for w in writers:
                    w.release()
                raise RuntimeError("Gagal membuat file video di " + self.directory)
            self._writers = writers
            self._size = frame_size
            self.started_at = time.time()
            self.files = names
            return names

    def write(self, raw_frame, annotated_frame):
        with self._lock:
            if self._writers is None:
                return
            h, w = raw_frame.shape[:2]
            if (w, h) != self._size:
                return
            self._writers[0].write(raw_frame)
            self._writers[1].write(annotated_frame)

    def stop(self) -> dict:
        with self._lock:
            if self._writers is None:
                return {"files": [], "duration_sec": 0}
            for w in self._writers:
                w.release()
            info = {"files": self.files, "duration_sec": round(time.time() - self.started_at, 1)}
            self._writers = None
            self._size = None
            self.started_at = None
            return info
