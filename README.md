# Early Warning System (EWS) Deteksi Banjir

Sistem monitoring ketinggian air dan peringatan dini banjir berbasis kamera dan
*classical computer vision* (Bottom-Up Frame Differencing), dengan dashboard web untuk publik
dan operator.

Sistem dikembangkan saat PKL dengan kamera CCTV PTZ Dahua yang mengarah ke papan duga. Kode yang
sama juga berjalan dengan kamera HP lewat DroidCam, yang dipakai untuk pengujian dan presentasi
dengan model papan duga berupa botol berisi air.

**Dokumentasi untuk laporan dan presentasi ada di folder [`docs/`](docs/README.md).**

## Fitur

- Deteksi ketinggian air *real-time* dari kamera: webcam/DroidCam, CCTV RTSP, atau file video.
- Tiga tingkat status **NORMAL / WASPADA / SIAGA** dengan debounce 5 detik untuk mencegah alarm palsu.
- Status **OFFLINE** dan **BELUM KALIBRASI** dibedakan dari NORMAL.
- Dashboard publik: video langsung, status, persentase ketinggian, grafik tren dengan garis batas.
- Dashboard operator: kontrol PTZ, ambil ulang referensi, rekam video, tampilan mask deteksi,
  pengaturan sensitivitas/blur, riwayat alert, ekspor CSV.
- Kalibrasi interaktif langsung dari kamera.

## Persiapan (sekali saja)

1. Pasang **DroidCam** di HP dan **DroidCam Client** di laptop. Di HP aktifkan **USB debugging**
   (Pengaturan → Tentang ponsel → ketuk *Nomor bentukan* 7×, lalu Opsi pengembang → USB debugging).
2. Klik ganda **`setup.bat`**: membuat `venv`, memasang dependensi, dan membuat `config/config.yaml`.

## Memindahkan ke laptop lain

1. Salin folder proyek **tanpa folder `venv`**, atau pakai file ZIP yang sudah tidak berisi `venv`.
   Folder `venv` hanya berlaku di laptop tempat ia dibuat; kalau tetap ikut tersalin,
   `setup.bat` akan mendeteksinya dan membuat ulang.
2. Di laptop baru pasang:
   - **Python 3.12 atau lebih baru** (disarankan 3.14) dari https://www.python.org/downloads/.
     Saat instalasi centang **"Add python.exe to PATH"**.
   - **DroidCam Client**, lalu sambungkan HP seperti di bawah.
3. Jalankan **`setup.bat`** (butuh internet sekali untuk mengunduh package).
4. Lanjutkan `cek_kamera.bat`, lalu kalibrasi ulang dengan `kalibrasi.bat`. Kalibrasi selalu
   dilakukan ulang di laptop/kamera baru, karena nomor kamera dan resolusinya bisa berbeda.

Dashboard tidak memerlukan internet saat dijalankan (Chart.js sudah disertakan di
`src/web/static/vendor/`). Sistem ini dibuat untuk Windows.

## Menjalankan

1. **Sambungkan HP**: colok USB, buka DroidCam di HP, lalu di DroidCam Client pilih **USB** → **Start**.
2. **`cek_kamera.bat`**: cari nomor webcam yang menampilkan gambar HP (biasanya `1`; `0` adalah
   kamera laptop). Jika bukan `1`, ubah `camera.source` di `config/config.yaml`.
3. **Siapkan objek**: botol bening di depan latar yang diam (dinding, kertas putih), penanda batas
   (selotip/kertas kuning dan merah, opsional), air dengan **pewarna makanan**. HP tidak boleh bergerak.
4. **`kalibrasi.bat`** dengan botol **kosong**:
   - SPASI: ambil gambar referensi
   - tarik kotak ROI dari **dasar botol** sampai atas, lalu ENTER
   - klik ketinggian batas **Waspada**, lalu batas **Siaga** (lebih tinggi), lalu **S** untuk menyimpan
5. **`run.bat`**: browser membuka http://localhost:8000/operator.
   Login operator: `operator` / `ews2026`. Halaman publik: http://localhost:8000
6. Tuang air perlahan: NORMAL → WASPADA → SIAGA, masing-masing setelah stabil 5 detik.

Berhenti: klik jendela server, tekan **Ctrl+C**.

## Mengatasi masalah

| Yang terlihat | Penyebab dan solusi |
|---|---|
| OFFLINE / "Kamera tidak ditemukan" | DroidCam Client belum di-Start, atau nomor kamera di `config.yaml` salah |
| `kalibrasi.bat` tidak bisa membuka kamera | Dashboard masih berjalan; hentikan dulu (Ctrl+C) |
| BELUM KALIBRASI | Kalibrasi belum ada atau resolusi kamera berubah; jalankan `kalibrasi.bat` |
| Air terdeteksi padahal botol kosong | Cahaya berubah / HP bergeser; kosongkan botol lalu klik **Ambil Ulang Referensi** |
| Air tidak terdeteksi | Tambah pewarna, atau geser **Sensitivitas** ke kiri |
| Deteksi melonjak-lonjak | Geser **Sensitivitas** ke kanan, atau naikkan **Blur** |

## Konfigurasi (`config/config.yaml`)

| Kunci | Keterangan |
|---|---|
| `camera.source` | Nomor webcam (`1`), URL DroidCam WiFi (`http://ip-hp:4747/video`), RTSP CCTV, atau path file video |
| `camera.width/height` | Resolusi yang diminta; kalibrasi mengikuti resolusi yang benar-benar diterima |
| `detection.sensitivity` / `blur_size` | Nilai awal; dapat diubah dari dashboard operator |
| `detection.debounce_sec` | Lama status harus stabil sebelum dikonfirmasi (default 5) |
| `ptz.enabled` | `true` untuk kamera PTZ Dahua (isi `ip`, `username`, `password`); `false` untuk kamera tetap |

Rekaman dari tombol **● Rekam Video** tersimpan di `data/recordings/` (`*_raw.mp4` dan `*_deteksi.mp4`).
File `*_raw.mp4` bisa dipakai sebagai `camera.source` jika kamera bermasalah, dengan syarat
kalibrasi tidak diubah sejak perekaman.

## Struktur

```text
├── config/
│   ├── config.example.yaml   # template konfigurasi
│   ├── config.yaml           # konfigurasi lokal (dibuat oleh setup.bat)
│   └── calibration.json      # hasil kalibrasi
├── data/                     # ews.db, reference.png, recordings/
├── docs/                     # bahan laporan & presentasi, gambar tahapan metode
├── scripts/
│   ├── cek_kamera.py         # cari nomor webcam
│   ├── kalibrasi.py          # kalibrasi referensi + ROI + garis batas
│   ├── main_detector.py      # mode jendela tanpa web
│   └── gambar_tahapan.py     # gambar tiap tahap metode untuk dokumentasi
├── src/
│   ├── config.py
│   ├── camera/               # video_source.py, ptz_control.py
│   ├── detection/            # water_level.py, debounce.py, calibration.py, recorder.py, detector.py
│   └── web/                  # FastAPI, SQLite, template & static
├── tests/                    # pytest: unit + integrasi dengan video sintetis
└── setup.bat · cek_kamera.bat · kalibrasi.bat · run.bat
```

Menjalankan tes: `venv\Scripts\python.exe -m pytest`

## Teknologi

Python 3.14 · OpenCV 5.0 · NumPy · FastAPI · Uvicorn · Jinja2 · SQLite · Chart.js · pytest
