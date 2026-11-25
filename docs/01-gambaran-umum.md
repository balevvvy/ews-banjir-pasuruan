# 1. Gambaran Umum

## 1.1 Latar belakang

Banjir membutuhkan peringatan dini agar warga dan petugas sempat bersiap. Pemantauan ketinggian air
secara manual (membaca papan duga di lokasi) membutuhkan petugas yang terus berjaga. Sistem ini
memanfaatkan **kamera** yang mengarah ke papan duga, lalu membaca ketinggian air secara otomatis
dengan **computer vision** dan menampilkan status peringatan di dashboard web.

Sistem dikembangkan selama PKL di **[isi sendiri: nama instansi, lokasi, periode PKL]** dengan kamera
CCTV PTZ Dahua yang mengarah ke papan duga. Setelah PKL berakhir, kamera tersebut tidak lagi dapat
diakses, sehingga untuk pengujian dan presentasi sistem dijalankan dengan kamera HP (DroidCam) dan
model papan duga berupa botol berisi air.

## 1.2 Tujuan

1. Mendeteksi ketinggian permukaan air dari citra kamera secara otomatis dan *real-time*.
2. Mengklasifikasikan kondisi menjadi tiga tingkat: **NORMAL**, **WASPADA**, **SIAGA**.
3. Mencegah peringatan palsu akibat gangguan sesaat (pantulan, noise, benda lewat).
4. Menyajikan status, video, grafik tren, dan riwayat peringatan melalui dashboard web
   untuk publik dan operator.

## 1.3 Ruang lingkup dan batasan

- Metode yang dipakai adalah *classical computer vision* (frame differencing dan operasi morfologi),
  **tanpa** deep learning, sehingga tidak memerlukan data latih maupun GPU.
- Kamera harus **diam** terhadap papan duga. Pada kamera PTZ, posisi dikembalikan dengan fitur reset
  PTZ; pada kamera tetap, kamera harus dipasang kokoh.
- Ketinggian dinyatakan dalam **persen tinggi area pantau (ROI)**, bukan dalam satuan cm.
- Sistem membutuhkan **gambar referensi** kondisi normal (air rendah / botol kosong). Perubahan
  pencahayaan yang besar mengharuskan referensi diambil ulang.
- Dashboard berjalan di jaringan lokal; autentikasi operator bersifat sederhana (satu akun).

## 1.4 Konfigurasi perangkat

| | Di lokasi PKL | Pengujian dan presentasi |
|---|---|---|
| Kamera | CCTV PTZ Dahua | Kamera HP lewat DroidCam (USB), terbaca sebagai webcam |
| Koneksi video | RTSP (H.264) | DirectShow (webcam virtual) |
| Objek | Papan duga di sungai/saluran | Botol bening berisi air berwarna, penanda batas kuning/merah |
| Kontrol posisi | PTZ lewat HTTP CGI Dahua, koreksi *closed-loop* | Tidak ada (kamera tetap); tombol PTZ hanya menampilkan keterangan |
| Server | Laptop/PC dengan Python | Laptop yang sama dengan kamera |

Kedua konfigurasi memakai kode yang sama. Perbedaannya hanya pada isi `config/config.yaml`
(`camera.source` dan `ptz.enabled`).

## 1.5 Fitur

**Halaman publik**: video langsung dengan overlay garis batas, status saat ini, persentase
ketinggian air, grafik tren 10 menit dengan garis batas Waspada/Siaga.

**Halaman operator** (perlu login):
- Kontrol PTZ "Kembalikan Kamera ke Papan Duga" (untuk kamera Dahua PTZ)
- Ambil ulang gambar referensi
- Rekam video (video asli dan video hasil deteksi)
- Pilihan tampilan video: kamera atau *mask* deteksi
- Pengaturan sensitivitas dan blur secara langsung
- Riwayat alert dan ekspor data ke CSV

**Alat pendukung**: pencarian nomor kamera (`cek_kamera.bat`), kalibrasi dari kamera
(`kalibrasi.bat`), mode jendela tanpa web (`scripts/main_detector.py`), pembuat gambar tahapan
metode untuk laporan (`scripts/gambar_tahapan.py`).
