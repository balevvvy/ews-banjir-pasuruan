# 4. Pengujian

Pengujian dibagi tiga:

1. **Pengujian otomatis** (unit dan integrasi) dengan pytest: memastikan setiap fungsi bekerja sesuai
   rancangan. Dapat diulang kapan saja tanpa kamera.
2. **Pengujian akurasi pada adegan sintetis**: mengukur selisih ketinggian terdeteksi dengan
   ketinggian sebenarnya, ketika ketinggian sebenarnya diketahui pasti.
3. **Pengujian dengan kamera** (DroidCam + botol): pengujian fungsional di dunia nyata.
   Tabelnya disediakan di bawah untuk diisi saat pengujian.

## 4.1 Pengujian otomatis

Menjalankan: `venv\Scripts\python.exe -m pytest -v`

Lingkungan: Windows 11, Python 3.14.0, OpenCV 5.0.0, pytest 9.2.0.
Hasil terakhir: **46 dari 46 tes lulus** (23 November 2026).

| File | Jumlah | Yang diuji |
|---|---|---|
| `test_water_level.py` | 29 | Ukuran blur; pemindaian dari dasar (mask kosong, air dari dasar, perubahan melayang di atas diabaikan, kolom terlalu pendek, celah kecil ditoleransi, celah besar menghentikan pemindaian, baris jarang bukan air); batas status termasuk tepat di garis; perhitungan persentase; pipeline lengkap pada adegan sintetis |
| `test_debounce.py` | 5 | Status baru dikonfirmasi tepat setelah 5 detik; kedipan mengulang hitungan; kembali ke NORMAL; reset |
| `test_calibration_config.py` | 8 | Simpan/muat kalibrasi; file hilang/rusak; validasi (garis terbalik, ROI di luar frame); kecocokan resolusi; parsing sumber kamera; nilai default konfigurasi |
| `test_detector_integration.py` | 4 | Detektor lengkap membaca video sintetis air naik: alert WASPADA muncul sebelum SIAGA; tanpa kalibrasi menjadi BELUM_KALIBRASI; sumber tidak ada menjadi OFFLINE; ambil referensi dan rekam video menghasilkan file |

Adegan sintetis (`tests/scene.py`) berukuran 640 × 480: latar abu-abu, penanda merah dan kuning,
botol dengan ROI `x=260, y=80, w=120, h=360`, garis Waspada Y = 260 (50% ROI) dan Siaga Y = 160
(77,8% ROI). Air digambar sebagai area kebiruan dari dasar botol; setiap frame diberi noise acak ±4.

## 4.2 Akurasi pada adegan sintetis

Referensi = botol kosong. Sensitivitas 30, blur 21. Y dalam piksel (Y kecil = lebih tinggi).

| Y air sebenarnya | % sebenarnya | Y terdeteksi | % terdeteksi | Selisih (px) | Status seharusnya | Status terdeteksi |
|---|---|---|---|---|---|---|
| (kosong) | 0,0 | (tidak ada) | 0,0 | - | NORMAL | NORMAL |
| 420 | 5,6 | 419 | 5,8 | −1 | NORMAL | NORMAL |
| 380 | 16,7 | 379 | 16,9 | −1 | NORMAL | NORMAL |
| 340 | 27,8 | 339 | 28,1 | −1 | NORMAL | NORMAL |
| 300 | 38,9 | 299 | 39,2 | −1 | NORMAL | NORMAL |
| 261 | 49,7 | 260 | 50,0 | −1 | NORMAL | **WASPADA** |
| 260 | 50,0 | 259 | 50,3 | −1 | WASPADA | WASPADA |
| 240 | 55,6 | 239 | 55,8 | −1 | WASPADA | WASPADA |
| 200 | 66,7 | 199 | 66,9 | −1 | WASPADA | WASPADA |
| 161 | 77,5 | 160 | 77,8 | −1 | WASPADA | **SIAGA** |
| 160 | 77,8 | 159 | 78,1 | −1 | SIAGA | SIAGA |
| 140 | 83,3 | 142 | 82,8 | +2 | SIAGA | SIAGA |
| 120 | 88,9 | 122 | 88,3 | +2 | SIAGA | SIAGA |

**Pembahasan:**
- Selisih maksimum 2 piksel (0,6% tinggi ROI). Botol kosong tidak menghasilkan deteksi palsu.
- 11 dari 13 kasus menghasilkan status yang benar. Dua kasus berbeda terjadi ketika air hanya
  **1 piksel di bawah garis batas**: deteksi yang 1 piksel lebih tinggi membuat status naik lebih
  awal. Pada penggunaan nyata, selisih 1 piksel jauh lebih kecil dari ketelitian penempatan garis
  batas saat kalibrasi.
- Adegan sintetis memiliki kontras tinggi dan pencahayaan tetap, sehingga angka ini adalah batas
  atas akurasi. Akurasi di dunia nyata perlu diukur dengan pengujian 4.3.

## 4.3 Pengujian end-to-end dengan video simulasi

Dashboard dijalankan dengan video sintetis 32 detik (air naik dari kosong sampai di atas garis merah,
lalu berulang) sebagai sumber kamera (19 November 2026). Hasil yang diamati dari `/api/status`:

| Pengamatan | Hasil |
|---|---|
| Sebelum kalibrasi | Status BELUM_KALIBRASI, video tetap tampil dengan pesan |
| Kalibrasi ditulis saat server berjalan | Dimuat ulang otomatis tanpa restart |
| Status mentah menjadi WASPADA | Pada ketinggian ±51% (garis Waspada 50%) |
| Status mentah menjadi SIAGA | Pada ketinggian ±79% (garis Siaga 77,8%) |
| Status terkonfirmasi | Menyusul ±5 detik setelah status mentah (debounce) |
| Riwayat alert | WASPADA → SIAGA → NORMAL tercatat berurutan |
| Pembacaan tersimpan | Setiap 5 detik |
| Tombol PTZ (kamera tetap) | Menampilkan keterangan, tidak error |
| Ambil ulang referensi, rekam video, ubah sensitivitas/blur | Berhasil |
| API operator tanpa login (dicoba pada `/api/ptz/reset`) | Ditolak (HTTP 401) |
| Halaman operator tanpa login | Dialihkan ke halaman login |

## 4.4 Pengujian dengan kamera (isi sendiri)

Perangkat: **[isi: tipe HP, resolusi DroidCam, ukuran botol]**. Tanggal: **[isi]**.
Ukur tinggi air dengan penggaris dari dasar botol. Tinggi ROI = tinggi botol yang masuk kotak ROI.

### a. Akurasi ketinggian

| No | Tinggi air diukur (cm) | % sebenarnya (= tinggi air / tinggi ROI × 100) | % di dashboard | Selisih (%) |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

### b. Perubahan status dan waktu respons

| No | Skenario | Status diharapkan | Status di dashboard | Waktu sampai status berubah (dtk) |
|---|---|---|---|---|
| 1 | Botol kosong | NORMAL | | |
| 2 | Air di bawah penanda kuning | NORMAL | | |
| 3 | Air melewati penanda kuning | WASPADA | | |
| 4 | Air melewati penanda merah | SIAGA | | |
| 5 | Air dibuang sampai kosong | NORMAL | | |

### c. Ketahanan terhadap gangguan

| No | Gangguan | Hasil diharapkan | Hasil | Keterangan |
|---|---|---|---|---|
| 1 | Tangan melintas di depan botol < 5 detik | Status terkonfirmasi tidak berubah (debounce) | | |
| 2 | Lampu ruangan dimatikan | Kemungkinan deteksi palsu; pulih setelah "Ambil Ulang Referensi" | | |
| 3 | Kabel USB dicabut | OFFLINE, alert "Kamera terputus" | | |
| 4 | Kabel USB dipasang kembali | Tersambung ulang otomatis | | |
| 5 | Air bening tanpa pewarna | [amati] | | |
| 6 | Sensitivitas diubah 15 / 30 / 60 | [amati pengaruhnya pada mask] | | |
