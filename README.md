# Proyek Aggregator Event (UTS Sistem Terdistribusi)
---
Proyek ini adalah implementasi dari sistem _event aggregator_ yang tangguh (robust), _idempotent_, dan _persistent_. Sistem ini dibangun menggunakan Python (FastAPI), SQLite, dan di-kontainerisasi dengan Docker.

Arsitektur ini dirancang untuk menangani pengiriman _event_ "at-least-once" dengan memastikan tidak ada duplikasi data yang diproses, bahkan jika server mengalami _restart_ atau _crash_.

---
---

## 1. Tautan Deliverables

- **Repositori GitHub:** `(https://github.com/Aozora09/Pubsub-Aggregator-UTS)`
- **Video Demo YouTube (7 Menit):** `(https://youtu.be/sAMplR2sMa8)`
- **Laporan Desain (PDF):** `[report.pdf](report.pdf)`

---

---

## 2. Struktur Repositori

```bash

/ (PUBSUB_AGGREGATOR) ├── .gitignore # Mengabaikan file .venv, pycache, .db, dll. ├── Dockerfile # Instruksi untuk membangun image aggregator ├── docker-compose.yml # (Bonus) Menjalankan aggregator & publisher bersamaan ├── main.py # Titik masuk (entrypoint) FastAPI/Uvicorn ├── publisher.py # Skrip publisher untuk demo at-least-once ├── pytest.ini # Konfigurasi untuk Pytest ├── README.md <-- File utama (dokumentasi ini) ├── report.pdf <-- LOKASI LAPORAN ├── requirements.txt # Daftar dependensi Python ├── stress_test.py # Skrip untuk demo skala uji (5.000+ event) │ ├── src/ <-- Kode sumber utama aplikasi │ ├── init.py │ ├── aggregator.py <-- Logika inti (worker, queue, stats) │ ├── dedup_store.py <-- Logika persistensi SQLite │ └── models.py <-- Model data Pydantic │ └── tests/ <-- Unit tests ├── init.py ├── conftest.py └── test_main.py
```

```
## 3. Cara Build & Run

Ada dua cara untuk menjalankan proyek ini. Cara (A) adalah yang paling direkomendasikan untuk demo penuh.

### A. Cara 1: Menggunakan Docker Compose (Direkomendasikan)

Metode ini akan secara otomatis membangun dan menjalankan _service_ `aggregator` dan `publisher` dalam satu jaringan Docker, serta mengelola _volume_ data secara otomatis. Ini adalah cara terbaik untuk mendemonstrasikan persistensi.

**Langkah 1: Build & Jalankan (Run 1)**
(Membersihkan sisa _run_ sebelumnya, memulai `aggregator`, dan menjalankan `publisher` sekali)

```bash
# Hapus container & volume lama (jika ada/jika baru mulai, abaikan saja)
docker-compose down -v

# Bangun image dan jalankan aggregator di background
docker-compose up -d --build aggregator

# Jalankan publisher untuk mengirim batch event pertama
docker-compose run publisher

# Akses link untuk melihat hasil pengujian
http://localhost:8080/stats
```

**Langkah 2: Verifikasi & Simulasi Crash (Stop) (Periksa log Run 1 dan hentikan server)**

```bash
# Periksa log aggregator, Anda akan melihat stats Run 1
docker-compose logs aggregator

# Hentikan server (simulasi crash), volume data akan tetap aman
docker-compose down

# Akses link untuk melihat hasil pengujian
http://localhost:8080/stats
```

**Langkah 3: Restart & Verifikasi Persistensi (Run 2) (Mulai ulang server dan kirim batch event yang sama untuk membuktikan dedup store)**
```bash

# Mulai ulang aggregator (TANPA --build)
docker-compose up -d aggregator

# Cek log startup, Anda HARUS melihat "LOAD STATE: Berhasil memuat state..."
docker-compose logs aggregator

# Jalankan publisher lagi (mengirim data yang sama atau acak)
docker-compose run publisher

# Cek log final untuk melihat bukti persistensi (unique events bertambah dgn benar)
docker-compose logs aggregator

# Akses link untuk melihat hasil pengujian
http://localhost:8080/stats
```

### B. Cara 2: Perintah Docker Manual (Berdasarkan Tugas)

Metode ini hanya menjalankan service aggregator saja. kita harus mengirim event secara manual menggunakan curl atau Postman.

**Langkah 1: Build Image**
```bash
docker build -t uts-aggregator .
```

**Langkah 2: Run Container (Perintah ini sudah dimodifikasi untuk menyertakan named volume)**
```bash
docker run -d -p 8080:8080 \
 --name aggregator_service \
 -v aggregator_data:/app/data \
 uts-aggregator
```
```bash
● -d: Berjalan di background.

● -p 8080:8080: Memetakan port.

● --name ...: Memberi nama container.

● -v ...: Penting, untuk menghubungkan named volume aggregator_data ke folder /app/data di container, tempat database SQLite disimpan.
```

**Langkah 3: Uji dengan Postman / Curl Server aggregator Anda sekarang berjalan di http://localhost:8080.**

---
## 4. Asumsi Desain
● Konsistensi > Performa: Sistem ini menggunakan SQLite dengan background worker tunggal untuk penulisan ke DB. Ini menjamin konsistensi data (tidak ada race condition penulisan) dengan mengorbankan throughput paralel.

● Ordering: Total ordering (urutan event) tidak dijamin. Sistem ini hanya menjamin deduplication (setiap event unik diproses sekali).

● At-Least-Once: Publisher dirancang untuk mengirim duplikat (atau event acak), mensimulasikan at-least-once delivery. Aggregator dirancang untuk idempotent terhadap skenario ini.

---
---
## 5. Endpoints API
● POST /publish: Menerima satu event atau batch event (array JSON).

● GET /stats: Menampilkan statistik pemrosesan (received_events, unique_events, duplicates, dll).

● GET /events: Mengembalikan daftar semua event unik yang telah diproses.

● Parameter Opsional: GET /events?topic=NAMA_TOPIK

---
