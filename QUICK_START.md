# Quick Start - Weather Station Raspberry Pi

## 🚀 Install dalam 5 Menit

### 1. Copy Files ke Raspberry Pi
```bash
# Dari Windows/Linux/Mac
scp -r Raspi-iot-version/ pi@YOUR_PI_IP:/home/pi/weather-station
```

### 2. SSH ke Raspberry Pi
```bash
ssh pi@YOUR_PI_IP
```

### 3. Install & Jalankan
```bash
cd /home/pi/weather-station
chmod +x install.sh
./install.sh
```

### 4. Start Service
```bash
sudo systemctl start weather_station.service
sudo systemctl enable weather_station.service
```

### 5. Buka Web Interface
Buka browser: `http://YOUR_PI_IP:5000`

## ✅ Test Installation

```bash
# Test web interface
curl http://localhost:5000

# Test dengan sample data
python3 test_weather_data.py

# Check status
sudo systemctl status weather_station.service
```

## 🔧 Troubleshooting

### Service tidak jalan?
```bash
# Check logs
journalctl -u weather_station.service -f

# Restart service
sudo systemctl restart weather_station.service
```

### Port 5000 sudah digunakan?
```bash
# Check port
sudo netstat -tlnp | grep :5000

# Kill process yang menggunakan port 5000
sudo fuser -k 5000/tcp
```

### Permission error?
```bash
# Fix ownership
sudo chown -R pi:pi /home/pi/weather-station

# Fix permissions
chmod +x weather_station.py
```

## 📱 Integrasi ESP32

1. Update `esp32_settings.json`:
```json
{
  "ssid": "YOUR_WIFI_SSID",
  "password": "YOUR_WIFI_PASSWORD",
  "postUrl": "http://YOUR_PI_IP:5000/post"
}
```

2. Copy ke microSD ESP32 sebagai `settings.json`

3. Monitor data masuk:
```bash
journalctl -u weather_station.service -f
```

## 🎯 Quick Commands

```bash
# Start/Stop/Restart
sudo systemctl start weather_station.service
sudo systemctl stop weather_station.service
sudo systemctl restart weather_station.service

# Check status
sudo systemctl status weather_station.service

# View logs
journalctl -u weather_station.service -f

# Check database
sqlite3 data/weather.db "SELECT COUNT(*) FROM weather_data;"
```

## 📊 Web Interface Features

- **Dashboard** - Data cuaca real-time
- **Settings** - Konfigurasi station
- **File Management** - Download/delete data
- **System Log** - Monitor aktivitas
- **API Endpoints** - `/post` dan `/api/weather`

## 🔗 URLs

- **Web Interface**: `http://YOUR_PI_IP:5000`
- **API Endpoint**: `http://YOUR_PI_IP:5000/api/weather`
- **ESP32 Post**: `http://YOUR_PI_IP:5000/post`

## 📁 File Locations

- **Database**: `data/weather.db`
- **Settings**: `data/settings.json`
- **Logs**: `logs/weather_station.log`
- **CSV Data**: `data/weather_data.csv`

## 🆘 Need Help?

1. Check logs: `journalctl -u weather_station.service -f`
2. Check status: `sudo systemctl status weather_station.service`
3. Test connection: `curl http://localhost:5000`
4. Check database: `sqlite3 data/weather.db ".tables"`

**Happy Weather Monitoring! 🌤️**
