# Dokumentasi EWS Banjir

Bahan untuk menulis laporan dan menyiapkan presentasi.

| Dokumen | Isi | Cocok untuk |
|---|---|---|
| [01-gambaran-umum.md](01-gambaran-umum.md) | Latar belakang, tujuan, ruang lingkup, konfigurasi perangkat | Bab Pendahuluan |
| [02-arsitektur-sistem.md](02-arsitektur-sistem.md) | Komponen, alur data, modul, API, database | Bab Perancangan Sistem |
| [03-metode-deteksi.md](03-metode-deteksi.md) | Tahapan computer vision, rumus, parameter, keterbatasan | Bab Metodologi / Landasan Teori |
| [04-pengujian.md](04-pengujian.md) | Pengujian otomatis, hasil, format tabel pengujian dengan kamera | Bab Hasil dan Pembahasan |
| [05-panduan-presentasi.md](05-panduan-presentasi.md) | Alur demo, daftar periksa, pertanyaan yang mungkin muncul | Presentasi |

## Gambar

Folder [`gambar/`](gambar/) berisi gambar tiap tahap metode deteksi.

- `ilustrasi_*.png` dibuat dari **adegan sintetis** (gambar buatan program), bukan foto kamera.
  Jika dipakai di laporan, beri keterangan "ilustrasi".
- Untuk gambar dari kamera sungguhan: lakukan kalibrasi, isi botol dengan air, matikan dashboard,
  lalu jalankan

  ```
  venv\Scripts\python.exe scripts\gambar_tahapan.py
  ```

  Hasilnya tersimpan di folder yang sama tanpa awalan `ilustrasi_`.

Diagram di dokumen 02 dan 03 ditulis dengan Mermaid. Diagram tampil langsung di GitHub atau VS Code
(ekstensi *Markdown Preview Mermaid Support*). Untuk dijadikan gambar di laporan, salin kodenya ke
https://mermaid.live lalu ekspor sebagai PNG/SVG.

Bagian bertanda **[isi sendiri]** berisi informasi yang hanya Anda ketahui (nama instansi PKL,
tanggal, hasil pengujian dengan kamera).
