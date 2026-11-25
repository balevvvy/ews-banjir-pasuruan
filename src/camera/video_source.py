"""
Sumber video seragam untuk webcam (DroidCam USB), stream URL (DroidCam WiFi / RTSP),
dan file video (diputar berulang dengan kecepatan aslinya).
"""

import os
import sys
import time

import cv2

OPEN_TIMEOUT_MS = 10000
READ_TIMEOUT_MS = 10000
WEBCAM_CHECK_SEC = 3.0
MIN_FRAME_STD = 1.0   # frame warna polos (std = 0) bukan gambar kamera


def describe_source(source) -> str:
    if isinstance(source, int):
        return f"webcam #{source}"
    if "://" in str(source):
        # Sembunyikan kredensial di URL RTSP
        scheme, rest = str(source).split("://", 1)
        return f"{scheme}://{rest.split('@')[-1]}"
    return f"file {os.path.basename(str(source))}"


class VideoSource:
    def __init__(self, source, width: int | None = None, height: int | None = None):
        self.source = source
        self.width = width
        self.height = height
        self.is_file = isinstance(source, str) and "://" not in source
        self._cap = None
        self._frame_interval = 0.0
        self._next_frame_time = 0.0

    def open(self) -> bool:
        self.release()

        if isinstance(self.source, int):
            cap = self._open_webcam()
            if cap is None:
                return False
        elif self.is_file:
            if not os.path.exists(self.source):
                return False
            cap = cv2.VideoCapture(self.source)
            fps = cap.get(cv2.CAP_PROP_FPS)
            self._frame_interval = 1.0 / fps if fps and fps > 0 else 1.0 / 15
            self._next_frame_time = time.monotonic()
        else:
            cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG, [
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, OPEN_TIMEOUT_MS,
                cv2.CAP_PROP_READ_TIMEOUT_MSEC, READ_TIMEOUT_MS,
            ])
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            cap.release()
            return False
        self._cap = cap
        return True

    def _open_webcam(self):
        # Driver DroidCam kadang "terbuka" di salah satu backend tetapi hanya mengirim frame
        # berwarna polos (misalnya hijau). Backend dipakai hanya jika terbukti mengirim gambar.
        backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW] if sys.platform == "win32" else [cv2.CAP_ANY]
        for backend in backends:
            cap = cv2.VideoCapture(self.source, backend)
            if not cap.isOpened():
                cap.release()
                continue
            if self.width and self.height:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if self._delivers_real_frames(cap):
                return cap
            cap.release()
        return None

    @staticmethod
    def _delivers_real_frames(cap, timeout: float = WEBCAM_CHECK_SEC) -> bool:
        """True jika dalam `timeout` detik ada frame yang bukan warna polos."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ok, frame = cap.read()
            if ok and frame is not None and frame.std() > MIN_FRAME_STD:
                return True
        return False

    def read(self):
        if self._cap is None:
            return False, None

        if self.is_file:
            # Jaga kecepatan putar sesuai FPS file
            delay = self._next_frame_time - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self._next_frame_time = max(self._next_frame_time, time.monotonic() - 1.0) + self._frame_interval

            ok, frame = self._cap.read()
            if not ok:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self._cap.read()
            return ok, frame

        return self._cap.read()

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None
