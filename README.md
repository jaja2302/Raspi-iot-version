# Weather Station - Raspberry Pi Version

Weather station system that receives data from ESP32 devices and stores it in a database.

## Quick Start

### 1. Install & Setup (One-time)
```bash
chmod +x install.sh
./install.sh
```

This will:
- Create virtual environment
- Install dependencies
- Setup systemd service
- Start the service automatically

### 2. Manual Run (Optional)
```bash
chmod +x run.sh
./run.sh
```

### 3. Uninstall
```bash
chmod +x uninstall.sh
./uninstall.sh
```

## Service Management

```bash
# Start service
sudo systemctl start weather_station

# Stop service
sudo systemctl stop weather_station

# Restart service
sudo systemctl restart weather_station

# Check status
sudo systemctl status weather_station

# View logs
journalctl -u weather_station -f
```

## Web Interface

- **Local:** http://localhost:5000
- **Network:** http://YOUR_PI_IP:5000

## API Endpoints

- **POST /post** - Receive data from ESP32 (form data)
- **POST /api/weather** - Receive data in JSON format
- **GET /api/weather/latest** - Get latest weather data

## Configuration

- **Settings:** `data/settings.json`
- **Database:** `data/weather.db`
- **Logs:** `logs/weather_station.log`

## ESP32 Integration

Update your ESP32's `postUrl` to:
```
http://YOUR_PI_IP:5000/post
```

Include device ID in the POST data:
```json
{
  "id": "44",
  "dateutc": "2024-01-15 14:30:00",
  "tempf": "78.5",
  "windspeedmph": "12.8",
  "humidity": "68"
}
```

## File Structure

```
├── weather_station.py    # Main application
├── install.sh           # Installation script
├── uninstall.sh         # Uninstallation script
├── run.sh              # Manual run script
├── requirements.txt    # Python dependencies
├── data/               # Data storage
│   ├── weather.db     # SQLite database
│   └── settings.json  # Configuration
└── logs/              # Log files
    └── weather_station.log
```
