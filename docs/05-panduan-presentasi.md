# 5. Panduan Presentasi

## 5.1 Daftar periksa sehari sebelumnya

- [ ] Latihan penuh sekali: sambungkan HP, kalibrasi, jalankan, tuang air sampai SIAGA.
- [ ] Rekam latihan dengan tombol **● Rekam Video** sebagai cadangan (`data/recordings/`).
- [ ] Siapkan: botol bening, air + pewarna makanan, wadah untuk menuang, lap, penanda batas
      (selotip warna/kertas), tripod atau penyangga HP, kabel USB, latar polos (kertas HVS/kardus).
- [ ] Baterai HP penuh; mode jangan ganggu aktif agar notifikasi tidak menutupi kamera.
- [ ] Buka `docs/gambar/` dan dokumen metode untuk ditunjukkan bila diminta.

## 5.2 Persiapan di ruangan (± 5 menit)

1. Pasang botol dan HP. Seluruh botol terlihat dari dasar sampai atas, latar belakang diam.
2. HP: buka DroidCam, sambungkan USB. Laptop: DroidCam Client → USB → **Start**.
3. `kalibrasi.bat` dengan botol **kosong**: SPASI → tarik kotak dari dasar botol → ENTER →
   klik batas Waspada → klik batas Siaga → **S**.
4. `run.bat` → login `operator` / `ews2026`.

Jika kamera bermasalah, gunakan rekaman latihan: ubah `camera.source` di `config/config.yaml`
menjadi path file `rekaman_..._raw.mp4`, lalu jalankan ulang `run.bat`.

## 5.3 Alur demo (± 5–7 menit)

| Urutan | Yang dilakukan | Yang dijelaskan |
|---|---|---|
| 1 | Tunjukkan halaman publik | Video langsung, status, grafik tren dengan garis batas |
| 2 | Botol kosong → status NORMAL | Gambar referensi = kondisi normal |
| 3 | Pindah ke tab **Mask Deteksi** | Frame differencing: putih = bagian yang berubah dari referensi |
| 4 | Tuang air sedikit (di bawah batas kuning) | Mask putih muncul dari dasar, persentase naik, status tetap NORMAL |
| 5 | Tuang sampai melewati batas kuning | Status mentah berubah, tetapi tampilan baru WASPADA setelah ± 5 detik: debounce |
| 6 | Tangan melintas cepat di depan botol | Status tidak ikut berubah: syarat kolom dari dasar + median + debounce |
| 7 | Tuang sampai melewati batas merah | SIAGA, alert tercatat di Riwayat Alert |
| 8 | Tunjukkan Riwayat Alert, grafik, Export CSV | Data tersimpan di SQLite |
| 9 | Klik "Kembalikan Kamera ke Papan Duga" | Fitur untuk kamera PTZ Dahua di lokasi PKL; kamera HP tidak punya PTZ |
| 10 | (Opsional) geser slider sensitivitas | Pengaruh threshold terlihat langsung di mask |
| 11 | Buang air | Kembali ke NORMAL setelah 5 detik |

## 5.4 Pertanyaan yang mungkin muncul

**Kenapa tidak memakai deep learning / YOLO?**
Deep learning butuh banyak gambar berlabel dari lokasi yang sama dan perangkat yang lebih kuat.
Kamera EWS selalu mengarah ke papan duga yang sama, sehingga cukup membandingkan dengan kondisi
normal. Metode klasik berjalan di CPU biasa, tidak perlu data latih, dan setiap tahapnya bisa
ditunjukkan (tab Mask Deteksi).

**Kenapa dipindai dari bawah ke atas?**
Air selalu naik dari dasar papan duga. Dengan mensyaratkan area berubah tersambung dari dasar,
perubahan yang hanya muncul di bagian atas (pantulan, tangan, serangga) tidak dianggap air.

**Apa fungsi debounce?**
Mencegah alarm palsu. Status harus stabil 5 detik sebelum diumumkan, sehingga gangguan sesaat
tidak memicu peringatan. Konsekuensinya, peringatan terlambat paling lama 5 detik, yang tidak
berarti dibanding laju kenaikan air banjir.

**Bagaimana jika cahaya berubah, misalnya siang ke malam?**
Perubahan cahaya besar membuat banyak piksel berbeda dari referensi. Operator dapat mengambil
ulang referensi dari dashboard. Pengembangan berikutnya: referensi otomatis per waktu, atau kamera
dengan inframerah dan referensi khusus malam.

**Kenapa ketinggian dalam persen, bukan cm?**
Sistem mengukur posisi dalam piksel relatif terhadap ROI. Konversi ke cm membutuhkan skala papan
duga yang diketahui (misalnya jarak dua garis skala dalam piksel), dan dapat ditambahkan sebagai
pengembangan.

**Bagaimana jika kamera bergeser?**
Di lokasi PKL, kamera PTZ dikembalikan ke posisi papan duga dengan koordinat tersimpan dan koreksi
*closed-loop* (tombol di dashboard). Untuk kamera tetap, kamera harus dipasang kokoh; jika bergeser,
lakukan kalibrasi ulang.

**Bagaimana jika kamera mati?**
Status menjadi OFFLINE (bukan NORMAL), alert "Kamera terputus" tercatat, dan sistem menyambung ulang
otomatis.

**Seberapa akurat?**
Pada adegan sintetis, selisih maksimum 2 piksel (0,6% tinggi ROI). Untuk kamera sungguhan, lihat
hasil pengujian di dokumen 04 bagian 4.4 **[isi setelah pengujian]**.

## 5.5 Pengembangan selanjutnya

- Konversi ketinggian ke cm berdasarkan skala papan duga.
- Pembaruan referensi otomatis untuk mengatasi perubahan cahaya.
- Notifikasi keluar (WhatsApp/Telegram/SMS) saat SIAGA.
- Beberapa kamera / beberapa titik pantau dalam satu dashboard.
- Manajemen akun operator dengan password yang dapat diubah.
