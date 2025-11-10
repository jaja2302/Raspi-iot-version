# Weather Station - Raspberry Pi Version

Sistem stasiun cuaca berbasis Raspberry Pi yang menerima data dari perangkat ESP32 dan menyimpannya ke dalam basis data lokal.

## Ringkasan Fitur
- REST API sederhana untuk menerima dan menyediakan data cuaca
- Penyimpanan data menggunakan SQLite
- Manajemen proses menggunakan PM2
- Antarmuka web untuk memantau kondisi terbaru

## Prasyarat
- Raspberry Pi dengan Raspberry Pi OS (atau distro Linux setara)
- Python 3.10 atau lebih baru serta `pip`
- Paket `python3-venv` terpasang (`sudo apt install python3-venv python3-pip`)
- Node.js dan npm terinstal (`sudo apt install nodejs npm`)
- PM2 terpasang secara global (`sudo npm install -g pm2`)
- Koneksi internet untuk mengunduh dependensi

## Instalasi
1. Masuk atau SSH ke Raspberry Pi, kemudian pindah ke direktori proyek (clone repositori terlebih dahulu bila perlu).

2. Buat virtual environment baru:
   ```bash
   python3 -m venv .venv
   ```

3. Aktifkan virtual environment:
   ```bash
   source .venv/bin/activate
   ```

4. Perbarui `pip` (opsional namun dianjurkan):
   ```bash
   pip install --upgrade pip
   ```

5. Instal seluruh dependensi Python:
   ```bash
   pip install -r requirements.txt
   ```

6. Nonaktifkan virtual environment jika sudah selesai:
   ```bash
   deactivate
   ```

## Menjalankan Aplikasi Secara Manual
Jika ingin menjalankan tanpa PM2:
```bash
source .venv/bin/activate
python weather_station.py
```
Pastikan virtual environment sudah aktif sebelum menjalankan perintah `python weather_station.py`.

## Pengelolaan Layanan dengan PM2
```bash
# Menjalankan weather system
pm2 start ecosystem.config.js

# Memeriksa status
pm2 status

# Melihat log
pm2 logs weather-system

# Menghentikan weather system
pm2 stop weather-system

# Me-restart weather system
pm2 restart weather-system

# Menghapus dari PM2
pm2 delete weather-system
```

## Antarmuka Web
- `http://localhost:5000`
- `http://ALAMAT_IP_PI_ANDA:5000`

## Endpoint API
- `POST /post` – menerima data dari ESP32 (form-data)
- `POST /api/weather` – menerima data JSON
- `GET /api/weather/latest` – mengembalikan data cuaca terbaru

## Konfigurasi & Data
- Konfigurasi aplikasi: `data/settings.json`
- Basis data SQLite: `data/weather.db`
- Log aplikasi: `logs/weather_station.log`

## Integrasi ESP32
Atur `postUrl` pada firmware ESP32 ke alamat berikut:
```
http://ALAMAT_IP_PI_ANDA:5000/post
```
Contoh payload JSON:
```json
{
  "id": "44",
  "dateutc": "2024-01-15 14:30:00",
  "tempf": "78.5",
  "windspeedmph": "12.8",
  "humidity": "68"
}
```

## Struktur Direktori
```
├── weather_station.py    # Aplikasi utama
├── ecosystem.config.js   # Konfigurasi PM2
├── requirements.txt      # Dependensi Python
├── data/                 # Data & konfigurasi
│   ├── weather.db        # Basis data SQLite
│   └── settings.json     # Pengaturan aplikasi
└── logs/                 # Berkas log
    └── weather_station.log
```