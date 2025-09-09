# Weather Station - Raspberry Pi Version

This is a Python conversion of the ESP32 Weather Station project, designed to run on Raspberry Pi with enhanced features and better data management.

## Features

- **Web Interface**: Modern web dashboard for monitoring and configuration
- **Database Storage**: SQLite database for efficient data storage and querying
- **API Endpoints**: RESTful API for data exchange with ESP32 devices
- **File Management**: Download and manage data files
- **Real-time Monitoring**: Live serial monitor and system status
- **System Service**: Runs as a systemd service for reliability

## Hardware Requirements

- Raspberry Pi (3B+ or newer recommended)
- MicroSD card (16GB+ recommended)
- Internet connection
- Optional: Weather sensors (if running standalone)

## Installation

### Quick Install

1. Clone or download this project to your Raspberry Pi
2. Run the installation script:
```bash
chmod +x install.sh
./install.sh
```

### Manual Install

1. Install dependencies:
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv sqlite3
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Run the application:
```bash
python3 weather_station.py
```

## Configuration

### Web Interface
Access the web interface at `http://localhost:5000` to:
- Configure station settings
- View real-time weather data
- Download data files
- Monitor system logs

### Settings File
The system uses `data/settings.json` for configuration:
```json
{
  "ssid": "your_wifi_ssid",
  "password": "your_wifi_password",
  "id": 1,
  "useStaticIP": false,
  "staticIP": "192.168.1.100",
  "gateway": "192.168.1.1",
  "subnet": "255.255.255.0",
  "dnsServer": "8.8.8.8",
  "postUrl": "http://localhost:5000/api/weather"
}
```

## API Endpoints

### POST /post
Receive weather data from ESP32 devices (form data):
- `dateutc`: Date/time in UTC
- `tempf`: Outdoor temperature in Fahrenheit
- `tempinf`: Indoor temperature in Fahrenheit
- `windspeedmph`: Wind speed in mph
- `winddir`: Wind direction in degrees
- `humidity`: Outdoor humidity %
- `humidityin`: Indoor humidity %
- `uv`: UV index
- `baromrelin`: Relative barometric pressure
- `solarradiation`: Solar radiation
- And more...

### POST /api/weather
Receive weather data in JSON format:
```json
{
  "datetime": "2024-01-01 12:00:00",
  "windspeed_kmh": 15.5,
  "wind_direction": 180,
  "temp_in_c": 22.0,
  "temp_out_c": 25.5,
  "humidity_in": 60,
  "humidity_out": 65,
  "uv_index": 5.0,
  "barometric_pressure_rel_in": 29.92
}
```

### GET /api/weather/latest
Get the latest weather data in JSON format.

## Data Storage

### Database
Weather data is stored in SQLite database (`data/weather.db`) with the following schema:
- `datetime`: Timestamp
- `windspeed_kmh`: Wind speed in km/h
- `wind_direction`: Wind direction in degrees
- `temp_in_c`: Indoor temperature in Celsius
- `temp_out_c`: Outdoor temperature in Celsius
- `humidity_in`: Indoor humidity %
- `humidity_out`: Outdoor humidity %
- `uv_index`: UV index
- `barometric_pressure_rel_in`: Relative pressure
- `solar_radiation_wm2`: Solar radiation
- And more...

### CSV Files
Data is also saved to CSV files for compatibility with the original ESP32 system.

## Integration with ESP32

To integrate with your existing ESP32 weather station:

1. Update the ESP32's `postUrl` setting to point to your Raspberry Pi:
```json
{
  "postUrl": "http://YOUR_PI_IP:5000/post"
}
```

2. The ESP32 will send data to the Raspberry Pi, which will store it in the database and provide a web interface.

## System Service

The application can run as a systemd service:

```bash
# Start service
sudo systemctl start weather_station.service

# Stop service
sudo systemctl stop weather_station.service

# Enable auto-start on boot
sudo systemctl enable weather_station.service

# Check status
sudo systemctl status weather_station.service

# View logs
journalctl -u weather_station.service -f
```

## File Structure

```
Raspi-iot-version/
├── weather_station.py          # Main application
├── requirements.txt            # Python dependencies
├── install.sh                  # Installation script
├── weather_station.service     # Systemd service file
├── README.md                   # This file
├── templates/
│   └── index.html             # Web interface template
├── static/
│   ├── css/                   # CSS files
│   └── js/                    # JavaScript files
├── data/                      # Data storage directory
│   ├── weather.db            # SQLite database
│   ├── weather_data.csv      # CSV data file
│   └── settings.json         # Configuration file
└── logs/                     # Log files
    └── weather_station.log   # Application logs
```

## Troubleshooting

### Service won't start
```bash
# Check service status
sudo systemctl status weather_station.service

# View detailed logs
journalctl -u weather_station.service -f

# Check if port 5000 is in use
sudo netstat -tlnp | grep :5000
```

### Database issues
```bash
# Check database file
ls -la data/weather.db

# Test database connection
sqlite3 data/weather.db ".tables"
```

### Permission issues
```bash
# Fix ownership
sudo chown -R pi:pi /home/pi/weather-station

# Fix permissions
chmod +x weather_station.py
chmod 755 data logs
```

## Development

To run in development mode:
```bash
# Activate virtual environment
source venv/bin/activate

# Run with debug mode
export FLASK_DEBUG=1
python3 weather_station.py
```

## License

This project is based on the original ESP32 Weather Station project and maintains the same functionality while adding Raspberry Pi-specific enhancements.
