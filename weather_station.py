#!/usr/bin/env python3
"""
Weather Station Raspberry Pi Version
Converted from ESP32 C++ code
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from flask_cors import CORS
import threading
import time
import requests
from pathlib import Path
import subprocess
import socket

app = Flask(__name__)
CORS(app)

# Setup logging with daily log files
def setup_logging():
    """Setup logging with daily log files"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Generate log filename with current date
    today = datetime.now().strftime('%Y%m%d')
    log_filename = f'logs/weather_station_{today}.log'
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    
    # Disable Flask request logging to reduce spam
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

# Custom logging filter to exclude /serial requests
class NoSerialLogFilter(logging.Filter):
    def filter(self, record):
        # Exclude /serial requests from logging
        return '/serial' not in record.getMessage()

# Apply filter to werkzeug logger
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(NoSerialLogFilter())

# Configuration
class Config:
    def __init__(self):
        self.data_file = "data/weather_data.csv"
        self.settings_file = "data/settings.json"
        self.raspi_settings_file = "raspi_settings.json"
        self.db_file = "data/weather.db"
        self.station_id = 1
        self.post_interval = 3  # seconds
        self.watchdog_timeout = 60  # seconds
        self.sync_queue = []  # Queue for data that needs to be synced to external server
        
        # Default settings (legacy support)
        self.settings = {
            "ssid": "weather_station",
            "password": "research",
            "id": 1,
            "useStaticIP": False,
            "staticIP": "192.168.8.1",
            "gateway": "192.168.8.1",
            "subnet": "255.255.255.0",
            "dnsServer": "8.8.8.8",
            "postUrl": "http://localhost:5000/api/weather"
        }
        
        # Raspberry Pi specific settings
        self.raspi_settings = {
            "device_name": "WeatherStation_RaspberryPi",
            "device_id": 44,
            "wifi_mode": "access_point",
            "ap_ssid": "WeatherStation_Pi",
            "ap_password": "weather123",
            "ap_ip": "192.168.4.1",
            "ap_gateway": "192.168.4.1",
            "ap_subnet": "255.255.255.0",
            "dhcp_start": "192.168.4.2",
            "dhcp_end": "192.168.4.20",
            "dns_server": "8.8.8.8",
            "web_server_port": 5000,
            "misol_endpoint": "/post",
            "api_endpoint": "/api/weather",
            "external_sync": {
                "enabled": True,
                "server_url": "http://srs-ssms.com/iot/post-aws-to-api.php",
                "sync_interval_minutes": 15,
                "retry_attempts": 3,
                "timeout_seconds": 30
            },
            "data_storage": {
                "database_file": "data/weather.db",
                "csv_file": "data/weather_data.csv",
                "auto_cleanup_days": 60,
                "max_storage_mb": 500
            },
            "network": {
                "internet_check_url": "http://8.8.8.8",
                "internet_check_interval": 60,
                "fallback_dns": ["8.8.8.8", "1.1.1.1"]
            }
        }
        
        # Serial buffer for logging
        self.serial_buffer = []
        self.serial_buffer_size = 20
        self.serial_buffer_index = 0
        
        # Watchdog
        self.watchdog_timer = 0
        self.last_activity = time.time()

config = Config()

def add_to_serial_buffer(message):
    """Add message to serial buffer (equivalent to addToSerialBuffer in C++)"""
    timestamped_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}"
    logger.info(timestamped_message)
    
    # Initialize buffer if not already done
    if not config.serial_buffer:
        config.serial_buffer = [""] * config.serial_buffer_size
    
    config.serial_buffer[config.serial_buffer_index] = timestamped_message
    config.serial_buffer_index = (config.serial_buffer_index + 1) % config.serial_buffer_size

def load_settings():
    """Load settings from JSON file (equivalent to loadSettings in C++)"""
    add_to_serial_buffer("Starting to load settings...")
    
    # Load legacy settings first
    if os.path.exists(config.settings_file):
        add_to_serial_buffer("Legacy settings file found. Attempting to read...")
        try:
            with open(config.settings_file, 'r') as file:
                settings_data = json.load(file)
                config.settings.update(settings_data)
                add_to_serial_buffer("Legacy settings loaded successfully")
        except Exception as e:
            add_to_serial_buffer(f"Failed to read legacy settings file: {str(e)}")
    
    # Load Raspberry Pi settings
    if os.path.exists(config.raspi_settings_file):
        add_to_serial_buffer("Raspberry Pi settings file found. Attempting to read...")
        try:
            with open(config.raspi_settings_file, 'r') as file:
                raspi_data = json.load(file)
                config.raspi_settings.update(raspi_data)
                add_to_serial_buffer("Raspberry Pi settings loaded successfully")
                add_to_serial_buffer(f"WiFi SSID: {config.raspi_settings['ap_ssid']}")
                add_to_serial_buffer(f"Device ID: {config.raspi_settings['device_id']}")
                add_to_serial_buffer(f"Access Point IP: {config.raspi_settings['ap_ip']}")
        except Exception as e:
            add_to_serial_buffer(f"Failed to read Raspberry Pi settings file: {str(e)}")
    else:
        add_to_serial_buffer("Raspberry Pi settings file not found. Using default settings...")
        save_raspi_settings()

def save_settings():
    """Save legacy settings to JSON file (equivalent to saveSettings in C++)"""
    try:
        os.makedirs(os.path.dirname(config.settings_file), exist_ok=True)
        with open(config.settings_file, 'w') as file:
            json.dump(config.settings, file, indent=2)
        add_to_serial_buffer("Legacy settings saved successfully")
    except Exception as e:
        add_to_serial_buffer(f"Failed to save legacy settings: {str(e)}")

def save_raspi_settings():
    """Save Raspberry Pi settings to JSON file"""
    try:
        with open(config.raspi_settings_file, 'w') as file:
            json.dump(config.raspi_settings, file, indent=4)
        add_to_serial_buffer("Raspberry Pi settings saved successfully")
    except Exception as e:
        add_to_serial_buffer(f"Failed to save Raspberry Pi settings: {str(e)}")

def check_internet_connection():
    """Check if internet connection is available"""
    try:
        # Try to connect to Google DNS
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        try:
            # Fallback: try Cloudflare DNS
            socket.create_connection(("1.1.1.1", 53), timeout=5)
            return True
        except OSError:
            return False

def sync_data_to_server(weather_data):
    """Sync weather data to external server if internet is available"""
    if not config.raspi_settings['external_sync']['enabled']:
        return False
    
    if not check_internet_connection():
        # Add to sync queue for later
        config.sync_queue.append(weather_data.copy())
        add_to_serial_buffer(f"No internet connection. Data queued for sync (queue size: {len(config.sync_queue)})")
        return False
    
    try:
        sync_config = config.raspi_settings['external_sync']
        
        # Prepare data for external server (same format as ESP32 was sending)
        sync_data = {
            'id': weather_data.get('device_id', config.raspi_settings['device_id']),
            'dateutc': weather_data.get('datetime', ''),
            'windspeedmph': weather_data.get('windspeed_kmh', 0) / 1.60934,  # Convert back to mph
            'winddir': weather_data.get('wind_direction', 0),
            'rainratein': weather_data.get('rain_rate_in', 0),
            'tempinf': weather_data.get('temp_in_c', 0) * 9.0/5.0 + 32.0,  # Convert back to Fahrenheit
            'tempf': weather_data.get('temp_out_c', 0) * 9.0/5.0 + 32.0,    # Convert back to Fahrenheit
            'humidityin': weather_data.get('humidity_in', 0),
            'humidity': weather_data.get('humidity_out', 0),
            'uv': weather_data.get('uv_index', 0),
            'windgustmph': weather_data.get('wind_gust_kmh', 0) / 1.60934,  # Convert back to mph
            'baromrelin': weather_data.get('barometric_pressure_rel_in', 0),
            'baromabsin': weather_data.get('barometric_pressure_abs_in', 0),
            'solarradiation': weather_data.get('solar_radiation_wm2', 0),
            'dailyrainin': weather_data.get('daily_rain_in', 0),
            'raintodayin': weather_data.get('rain_today_in', 0),
            'totalrainin': weather_data.get('total_rain_in', 0),
            'weeklyrainin': weather_data.get('weekly_rain_in', 0),
            'monthlyrainin': weather_data.get('monthly_rain_in', 0),
            'yearlyrainin': weather_data.get('yearly_rain_in', 0),
            'maxdailygust': weather_data.get('max_daily_gust', 0),
            'wh65batt': weather_data.get('wh65_batt', 0)
        }
        
        # Send to external server
        response = requests.post(
            sync_config['server_url'],
            data=sync_data,
            timeout=sync_config['timeout_seconds']
        )
        
        if response.status_code == 200:
            add_to_serial_buffer(f"Data synced to external server successfully")
            return True
        else:
            add_to_serial_buffer(f"Failed to sync data to external server: HTTP {response.status_code}")
            config.sync_queue.append(weather_data.copy())
            return False
            
    except Exception as e:
        add_to_serial_buffer(f"Error syncing data to external server: {str(e)}")
        config.sync_queue.append(weather_data.copy())
        return False

def process_sync_queue():
    """Process queued data when internet becomes available"""
    if not check_internet_connection():
        return
    
    if not config.sync_queue:
        return
    
    add_to_serial_buffer(f"Internet connection detected. Processing sync queue ({len(config.sync_queue)} items)...")
    
    successful_syncs = 0
    failed_syncs = 0
    
    # Process queue (make a copy to avoid modification during iteration)
    queue_copy = config.sync_queue.copy()
    config.sync_queue.clear()
    
    for weather_data in queue_copy:
        if sync_data_to_server(weather_data):
            successful_syncs += 1
        else:
            failed_syncs += 1
    
    add_to_serial_buffer(f"Sync queue processed: {successful_syncs} successful, {failed_syncs} failed")
    
    # Limit queue size to prevent memory issues
    if len(config.sync_queue) > 1000:
        removed_items = len(config.sync_queue) - 1000
        config.sync_queue = config.sync_queue[-1000:]
        add_to_serial_buffer(f"Sync queue size limited: removed {removed_items} oldest items")

def init_database():
    """Initialize SQLite database for weather data"""
    try:
        os.makedirs(os.path.dirname(config.db_file), exist_ok=True)
        conn = sqlite3.connect(config.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                windspeed_kmh REAL,
                wind_direction INTEGER,
                rain_rate_in REAL,
                temp_in_c REAL,
                temp_out_c REAL,
                humidity_in INTEGER,
                humidity_out INTEGER,
                uv_index REAL,
                wind_gust_kmh REAL,
                barometric_pressure_rel_in REAL,
                barometric_pressure_abs_in REAL,
                solar_radiation_wm2 REAL,
                daily_rain_in REAL,
                rain_today_in REAL,
                total_rain_in REAL,
                weekly_rain_in REAL,
                monthly_rain_in REAL,
                yearly_rain_in REAL,
                max_daily_gust REAL,
                wh65_batt REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        add_to_serial_buffer("Database initialized successfully")
    except Exception as e:
        add_to_serial_buffer(f"Failed to initialize database: {str(e)}")

def cleanup_old_data():
    """Clean up data older than 2 months to prevent memory issues"""
    try:
        conn = sqlite3.connect(config.db_file)
        cursor = conn.cursor()
        
        # Calculate date 2 months ago
        two_months_ago = datetime.now() - timedelta(days=60)
        cutoff_date = two_months_ago.strftime('%Y-%m-%d %H:%M:%S')
        
        # Count records to be deleted
        cursor.execute('SELECT COUNT(*) FROM weather_data WHERE created_at < ?', (cutoff_date,))
        count_to_delete = cursor.fetchone()[0]
        
        if count_to_delete > 0:
            # Delete old records
            cursor.execute('DELETE FROM weather_data WHERE created_at < ?', (cutoff_date,))
            conn.commit()
            
            # Vacuum database to reclaim space
            cursor.execute('VACUUM')
            
            add_to_serial_buffer(f"Auto-cleanup completed - {count_to_delete} old records deleted (older than {cutoff_date})")
        else:
            add_to_serial_buffer("Auto-cleanup: No old records found to delete")
        
        conn.close()
        return True, count_to_delete
        
    except Exception as e:
        add_to_serial_buffer(f"Failed to cleanup old data: {str(e)}")
        return False, 0

def clear_old_logs():
    """Clear log files that are not from today"""
    try:
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            return True, 0
        
        files_deleted = 0
        today = datetime.now().strftime('%Y%m%d')
        current_log = f'weather_station_{today}.log'  # Today's log file
        
        for filename in os.listdir(log_dir):
            file_path = os.path.join(log_dir, filename)
            if os.path.isfile(file_path) and filename != current_log:
                try:
                    os.remove(file_path)
                    files_deleted += 1
                    add_to_serial_buffer(f"Deleted old log file: {filename}")
                except OSError as e:
                    add_to_serial_buffer(f"Could not delete {filename}: {str(e)}")
        
        if files_deleted > 0:
            add_to_serial_buffer(f"Old log files cleared - {files_deleted} files deleted")
        else:
            add_to_serial_buffer("No old log files found to delete")
        
        return True, files_deleted
        
    except Exception as e:
        add_to_serial_buffer(f"Failed to clear old logs: {str(e)}")
        return False, 0

def reset_database():
    """Reset database - clear all weather data"""
    try:
        conn = sqlite3.connect(config.db_file)
        cursor = conn.cursor()
        
        # Count records before deletion
        cursor.execute('SELECT COUNT(*) FROM weather_data')
        count_before = cursor.fetchone()[0]
        
        # Delete all records from weather_data table
        cursor.execute('DELETE FROM weather_data')
        
        # Reset auto-increment counter
        cursor.execute('DELETE FROM sqlite_sequence WHERE name="weather_data"')
        
        conn.commit()
        conn.close()
        
        # Also clear CSV file
        if os.path.exists(config.data_file):
            with open(config.data_file, 'w') as file:
                file.write('')  # Clear the file
        
        add_to_serial_buffer(f"Database reset successfully - {count_before} records deleted")
        return True, count_before
        
    except Exception as e:
        add_to_serial_buffer(f"Failed to reset database: {str(e)}")
        return False, 0

def save_weather_data(data):
    """Save weather data to database and CSV file"""
    try:
        # Save to database
        conn = sqlite3.connect(config.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO weather_data (
                device_id, datetime, windspeed_kmh, wind_direction, rain_rate_in,
                temp_in_c, temp_out_c, humidity_in, humidity_out,
                uv_index, wind_gust_kmh, barometric_pressure_rel_in,
                barometric_pressure_abs_in, solar_radiation_wm2,
                daily_rain_in, rain_today_in, total_rain_in,
                weekly_rain_in, monthly_rain_in, yearly_rain_in,
                max_daily_gust, wh65_batt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('device_id', 1),
            data.get('datetime', ''),
            data.get('windspeed_kmh', 0),
            data.get('wind_direction', 0),
            data.get('rain_rate_in', 0),
            data.get('temp_in_c', 0),
            data.get('temp_out_c', 0),
            data.get('humidity_in', 0),
            data.get('humidity_out', 0),
            data.get('uv_index', 0),
            data.get('wind_gust_kmh', 0),
            data.get('barometric_pressure_rel_in', 0),
            data.get('barometric_pressure_abs_in', 0),
            data.get('solar_radiation_wm2', 0),
            data.get('daily_rain_in', 0),
            data.get('rain_today_in', 0),
            data.get('total_rain_in', 0),
            data.get('weekly_rain_in', 0),
            data.get('monthly_rain_in', 0),
            data.get('yearly_rain_in', 0),
            data.get('max_daily_gust', 0),
            data.get('wh65_batt', 0)
        ))
        
        conn.commit()
        conn.close()
        
        # Save to CSV file (for compatibility with original system)
        csv_line = f"{data.get('datetime', '')},{data.get('windspeed_kmh', 0)},{data.get('wind_direction', 0)},{data.get('rain_rate_in', 0)},{data.get('temp_in_c', 0)},{data.get('temp_out_c', 0)},{data.get('humidity_in', 0)},{data.get('humidity_out', 0)},{data.get('uv_index', 0)},{data.get('wind_gust_kmh', 0)},{data.get('barometric_pressure_rel_in', 0)},{data.get('barometric_pressure_abs_in', 0)},{data.get('solar_radiation_wm2', 0)},{data.get('daily_rain_in', 0)},{data.get('rain_today_in', 0)},{data.get('total_rain_in', 0)},{data.get('weekly_rain_in', 0)},{data.get('monthly_rain_in', 0)},{data.get('yearly_rain_in', 0)},{data.get('max_daily_gust', 0)},{data.get('wh65_batt', 0)}"
        
        os.makedirs(os.path.dirname(config.data_file), exist_ok=True)
        with open(config.data_file, 'a') as file:
            file.write(csv_line + '\n')
        
        add_to_serial_buffer("Weather data saved successfully")
        
        # Try to sync data to external server if internet is available
        sync_data_to_server(data)
        
        return True
        
    except Exception as e:
        add_to_serial_buffer(f"Failed to save weather data: {str(e)}")
        return False

def get_connected_devices():
    """Get list of connected devices (simplified version)"""
    # This would need to be implemented based on your network setup
    return "Connected devices: 0 (Raspberry Pi version)"

def watchdog_timer():
    """Watchdog timer to monitor system health"""
    while True:
        time.sleep(1)
        config.watchdog_timer += 1
        
        # Reset watchdog if there's recent activity (web requests, data saves, etc.)
        current_time = time.time()
        if current_time - config.last_activity < 30:  # Reset if activity within 30 seconds
            config.watchdog_timer = 0
        
        if config.watchdog_timer >= config.watchdog_timeout:
            add_to_serial_buffer("Watchdog timeout! System appears idle, resetting watchdog...")
            # Just reset the watchdog, don't actually restart
            config.watchdog_timer = 0
            config.last_activity = time.time()  # Update last activity

def cleanup_scheduler():
    """Scheduler for automatic cleanup and sync - runs daily"""
    last_cleanup = time.time()
    last_sync_check = time.time()
    cleanup_interval = 24 * 60 * 60  # Run cleanup every 24 hours
    sync_check_interval = config.raspi_settings['external_sync']['sync_interval_minutes'] * 60  # Convert to seconds
    
    while True:
        time.sleep(60)  # Check every minute
        current_time = time.time()
        
        # Check sync queue periodically
        if current_time - last_sync_check >= sync_check_interval:
            if config.sync_queue:
                process_sync_queue()
            last_sync_check = current_time
        
        # Check if it's time for cleanup (every 24 hours)
        if current_time - last_cleanup >= cleanup_interval:
            add_to_serial_buffer("Starting daily cleanup...")
            
            # 1. Cleanup old database records (> 2 months)
            cleanup_old_data()
            
            # 2. Clear old log files (not from today)
            clear_old_logs()
            
            # 3. Process any remaining sync queue
            if config.sync_queue:
                process_sync_queue()
            
            last_cleanup = current_time
            add_to_serial_buffer("Daily cleanup completed")

# Flask Routes
@app.route('/')
def handle_root():
    """Main web interface (equivalent to handleRoot in C++)"""
    try:
        # Update last activity for watchdog
        config.last_activity = time.time()
        
        # Get recent weather data
        conn = sqlite3.connect(config.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM weather_data ORDER BY created_at DESC LIMIT 10')
        recent_data = cursor.fetchall()
        conn.close()
        
        # Get file list
        files = []
        if os.path.exists('data'):
            files = [f for f in os.listdir('data') if os.path.isfile(os.path.join('data', f))]
        
        return render_template('index.html', 
                             settings=config.settings,
                             recent_data=recent_data,
                             files=files,
                             connected_devices=get_connected_devices())
    except Exception as e:
        add_to_serial_buffer(f"Error in handle_root: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/save', methods=['POST'])
def handle_save_settings():
    """Save settings (equivalent to handleSaveSettings in C++)"""
    try:
        config.settings['ssid'] = request.form.get('ssid', config.settings['ssid'])
        config.settings['password'] = request.form.get('password', config.settings['password'])
        config.settings['id'] = int(request.form.get('id', config.settings['id']))
        config.settings['useStaticIP'] = 'useStaticIP' in request.form
        config.settings['staticIP'] = request.form.get('staticIP', config.settings['staticIP'])
        config.settings['gateway'] = request.form.get('gateway', config.settings['gateway'])
        config.settings['subnet'] = request.form.get('subnet', config.settings['subnet'])
        config.settings['dnsServer'] = request.form.get('dnsServer', config.settings['dnsServer'])
        config.settings['postUrl'] = request.form.get('postUrl', config.settings['postUrl'])
        
        save_settings()
        add_to_serial_buffer("Settings saved successfully")
        
        return redirect(url_for('handle_root'))
    except Exception as e:
        add_to_serial_buffer(f"Error saving settings: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/post', methods=['POST'])
@app.route('/data/report', methods=['POST'])  # Ecowitt endpoint
@app.route('/weatherstation/updateweatherstation.php', methods=['POST'])  # Wunderground endpoint
@app.route('/v1/current_conditions', methods=['POST'])  # WeatherCloud endpoint
def handle_post():
    """Handle weather data POST from various weather services (Ecowitt, Wunderground, etc.)"""
    try:
        # Parse weather data from request
        # Use device ID from Raspberry Pi settings as default if not provided
        device_id = request.form.get('id')
        if device_id:
            device_id = int(device_id)
        else:
            # Use ID from Raspberry Pi settings file as default
            device_id = config.raspi_settings.get('device_id', config.settings.get('id', 1))
        
        weather_data = {
            'device_id': device_id,
            'datetime': request.form.get('dateutc', ''),
            'windspeed_kmh': float(request.form.get('windspeedmph', 0)) * 1.60934,
            'wind_direction': int(request.form.get('winddir', 0)),
            'rain_rate_in': float(request.form.get('rainratein', 0)),
            'temp_in_c': (5.0 / 9.0) * (float(request.form.get('tempinf', 0)) - 32.0),
            'temp_out_c': (5.0 / 9.0) * (float(request.form.get('tempf', 0)) - 32.0),
            'humidity_in': int(request.form.get('humidityin', 0)),
            'humidity_out': int(request.form.get('humidity', 0)),
            'uv_index': float(request.form.get('uv', 0)),
            'wind_gust_kmh': float(request.form.get('windgustmph', 0)) * 1.60934,
            'barometric_pressure_rel_in': float(request.form.get('baromrelin', 0)),
            'barometric_pressure_abs_in': float(request.form.get('baromabsin', 0)),
            'solar_radiation_wm2': float(request.form.get('solarradiation', 0)),
            'daily_rain_in': float(request.form.get('dailyrainin', 0)),
            'rain_today_in': float(request.form.get('raintodayin', 0)),
            'total_rain_in': float(request.form.get('totalrainin', 0)),
            'weekly_rain_in': float(request.form.get('weeklyrainin', 0)),
            'monthly_rain_in': float(request.form.get('monthlyrainin', 0)),
            'yearly_rain_in': float(request.form.get('yearlyrainin', 0)),
            'max_daily_gust': float(request.form.get('maxdailygust', 0)),
            'wh65_batt': float(request.form.get('wh65batt', 0))
        }
        
        # Adjust timezone (add 7 hours for GMT+7)
        if weather_data['datetime']:
            dt = datetime.strptime(weather_data['datetime'], '%Y-%m-%d %H:%M:%S')
            dt += timedelta(hours=7)
            weather_data['datetime'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        add_to_serial_buffer(f"Received weather data from device {weather_data['device_id']}: {weather_data['datetime']}")
        
        if save_weather_data(weather_data):
            config.last_activity = time.time()
            config.watchdog_timer = 0
            return "Data saved to database.", 200
        else:
            return "Failed to save data.", 500
            
    except Exception as e:
        add_to_serial_buffer(f"Error in handle_post: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/serial')
def handle_serial():
    """Get serial monitor output (equivalent to handleSerial in C++)"""
    # Update last activity for watchdog (but don't log this request)
    config.last_activity = time.time()
    
    output = ""
    for i in range(config.serial_buffer_size):
        index = (config.serial_buffer_index + i) % config.serial_buffer_size
        if config.serial_buffer[index]:
            output += config.serial_buffer[index] + "\n"
    return output

@app.route('/download')
def handle_download():
    """Download file (equivalent to handleDownload in C++)"""
    filename = request.args.get('file')
    if filename and os.path.exists(f'data/{filename}'):
        return send_file(f'data/{filename}', as_attachment=True)
    return "File not found", 404

@app.route('/delete')
def handle_delete():
    """Delete file (equivalent to handleDelete in C++)"""
    filename = request.args.get('file')
    if filename and os.path.exists(f'data/{filename}'):
        os.remove(f'data/{filename}')
        add_to_serial_buffer(f"File {filename} deleted")
        return redirect(url_for('handle_root'))
    return "File not found", 404

@app.route('/restart')
def handle_restart():
    """Restart system (equivalent to handleRestart in C++)"""
    add_to_serial_buffer("System restart requested")
    # In a real implementation, you might want to restart the service
    return "System restart initiated", 200

@app.route('/reset-database', methods=['POST'])
def handle_reset_database():
    """Reset database - clear all weather data"""
    try:
        success, count = reset_database()
        if success:
            return jsonify({
                "status": "success", 
                "message": f"Database reset successfully - {count} records deleted"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to reset database"
            }), 500
    except Exception as e:
        add_to_serial_buffer(f"Error in handle_reset_database: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/database/reset', methods=['POST'])
def api_reset_database():
    """API endpoint to reset database"""
    try:
        success, count = reset_database()
        if success:
            return jsonify({
                "status": "success", 
                "message": f"Database reset successfully - {count} records deleted",
                "records_deleted": count
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to reset database"
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/database/info')
def api_database_info():
    """API endpoint to get database information"""
    try:
        conn = sqlite3.connect(config.db_file)
        cursor = conn.cursor()
        
        # Get total records count
        cursor.execute('SELECT COUNT(*) FROM weather_data')
        total_records = cursor.fetchone()[0]
        
        # Get oldest and newest records
        cursor.execute('SELECT MIN(created_at), MAX(created_at) FROM weather_data')
        date_range = cursor.fetchone()
        oldest_date = date_range[0] if date_range[0] else None
        newest_date = date_range[1] if date_range[1] else None
        
        # Get database file size
        db_size = os.path.getsize(config.db_file) if os.path.exists(config.db_file) else 0
        
        # Get CSV file size
        csv_size = os.path.getsize(config.data_file) if os.path.exists(config.data_file) else 0
        
        conn.close()
        
        return jsonify({
            "status": "success",
            "database_info": {
                "total_records": total_records,
                "oldest_record": oldest_date,
                "newest_record": newest_date,
                "database_size_bytes": db_size,
                "database_size_mb": round(db_size / (1024 * 1024), 2),
                "csv_size_bytes": csv_size,
                "csv_size_mb": round(csv_size / (1024 * 1024), 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/cleanup', methods=['POST'])
def api_cleanup():
    """API endpoint to manually trigger cleanup - only database > 2 months"""
    try:
        add_to_serial_buffer("Manual database cleanup requested")
        
        # Only cleanup old database records (> 2 months)
        db_success, db_count = cleanup_old_data()
        
        if db_success:
            return jsonify({
                "status": "success",
                "message": f"Database cleanup completed - {db_count} old records deleted"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Database cleanup failed"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/logs/clear', methods=['POST'])
def api_clear_logs():
    """API endpoint to clear old log files (not from today)"""
    try:
        add_to_serial_buffer("Manual log clear requested")
        
        success, count = clear_old_logs()
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Old log files cleared - {count} files deleted"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to clear old log files"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/weather', methods=['POST'])
def api_weather():
    """API endpoint for receiving weather data from ESP32"""
    try:
        data = request.get_json()
        
        # Add device_id if not provided
        if 'device_id' not in data:
            data['device_id'] = config.settings.get('id', 1)
        
        if save_weather_data(data):
            return jsonify({"status": "success", "message": "Data saved"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to save data"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/weather/latest')
def api_weather_latest():
    """API endpoint to get latest weather data"""
    try:
        conn = sqlite3.connect(config.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM weather_data ORDER BY created_at DESC LIMIT 1')
        data = cursor.fetchone()
        conn.close()
        
        if data:
            return jsonify({
                "datetime": data[1],
                "windspeed_kmh": data[2],
                "wind_direction": data[3],
                "temp_in_c": data[5],
                "temp_out_c": data[6],
                "humidity_in": data[7],
                "humidity_out": data[8],
                "uv_index": data[9],
                "barometric_pressure_rel_in": data[11],
                "solar_radiation_wm2": data[13]
            })
        else:
            return jsonify({"message": "No data available"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/network/info')
def api_network_info():
    """API endpoint to get current network information"""
    try:
        network_info = get_network_info()
        server_port = config.raspi_settings.get('web_server_port', 5000)
        
        return jsonify({
            "status": "success",
            "network_info": {
                "local_ip": network_info['local_ip'],
                "wifi_ssid": network_info['wifi_ssid'],
                "wifi_mode": network_info['wifi_mode'],
                "network_interfaces": network_info['network_interfaces'],
                "server_port": server_port,
                "web_interface_url": f"http://{network_info['local_ip']}:{server_port}",
                "api_endpoint": f"http://{network_info['local_ip']}:{server_port}/api/weather",
                "misol_endpoint": f"http://{network_info['local_ip']}:{server_port}/post",
                "misol_config": {
                    "wifi_ssid": network_info['wifi_ssid'] if network_info['wifi_ssid'] else "Any WiFi (connect to same network)",
                    "server_url": f"http://{network_info['local_ip']}:{server_port}/post"
                }
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def get_network_info():
    """Get network information including IP, SSID, and connection type"""
    try:
        import subprocess
        import socket
        
        # Get IP address
        local_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass
        
        # Get WiFi SSID (if connected to WiFi)
        wifi_ssid = None
        wifi_mode = "unknown"
        
        try:
            # Method 1: Try iwgetid command
            result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True)
            add_to_serial_buffer(f"DEBUG: iwgetid result: returncode={result.returncode}, output='{result.stdout.strip()}'")
            if result.returncode == 0 and result.stdout.strip():
                wifi_ssid = result.stdout.strip()
                wifi_mode = "client"
                add_to_serial_buffer(f"DEBUG: Found SSID via iwgetid: {wifi_ssid}")
            else:
                # Method 2: Try iwconfig command
                result = subprocess.run(['iwconfig'], capture_output=True, text=True)
                add_to_serial_buffer(f"DEBUG: iwconfig result: returncode={result.returncode}")
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    add_to_serial_buffer(f"DEBUG: iwconfig output lines: {len(lines)}")
                    for line in lines:
                        if 'ESSID:' in line and 'off/any' not in line:
                            add_to_serial_buffer(f"DEBUG: Found ESSID line: {line}")
                            # Extract SSID from line like: wlan0     IEEE 802.11  ESSID:"pi-raspi"
                            if 'ESSID:"' in line:
                                start = line.find('ESSID:"') + 7
                                end = line.find('"', start)
                                if start < end:
                                    wifi_ssid = line[start:end]
                                    wifi_mode = "client"
                                    add_to_serial_buffer(f"DEBUG: Found SSID via iwconfig: {wifi_ssid}")
                                    break
                
                # Method 3: Check if running as access point
                if not wifi_ssid:
                    result = subprocess.run(['systemctl', 'is-active', 'hostapd'], capture_output=True, text=True)
                    if result.returncode == 0 and 'active' in result.stdout:
                        wifi_mode = "access_point"
                        # Try to get AP SSID from hostapd config
                        try:
                            with open('/etc/hostapd/hostapd.conf', 'r') as f:
                                for line in f:
                                    if line.startswith('ssid='):
                                        wifi_ssid = line.split('=')[1].strip()
                                        break
                        except Exception:
                            pass
                
                # Method 4: Try nmcli (NetworkManager)
                if not wifi_ssid:
                    try:
                        result = subprocess.run(['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi'], capture_output=True, text=True)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')
                            for line in lines:
                                if line.startswith('yes:'):
                                    wifi_ssid = line.split(':', 1)[1]
                                    wifi_mode = "client"
                                    break
                    except Exception:
                        pass
                
                # Method 5: Try wpa_cli
                if not wifi_ssid:
                    try:
                        result = subprocess.run(['wpa_cli', '-i', 'wlan0', 'status'], capture_output=True, text=True)
                        add_to_serial_buffer(f"DEBUG: wpa_cli result: returncode={result.returncode}")
                        if result.returncode == 0:
                            add_to_serial_buffer(f"DEBUG: wpa_cli output: {result.stdout}")
                            for line in result.stdout.split('\n'):
                                if line.startswith('ssid='):
                                    wifi_ssid = line.split('=', 1)[1]
                                    wifi_mode = "client"
                                    add_to_serial_buffer(f"DEBUG: Found SSID via wpa_cli: {wifi_ssid}")
                                    break
                    except Exception as e:
                        add_to_serial_buffer(f"DEBUG: wpa_cli error: {str(e)}")
                        pass
                        
        except Exception:
            pass
        
        # Get all network interfaces
        network_interfaces = []
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            if result.returncode == 0:
                ips = result.stdout.strip().split()
                for ip in ips:
                    if ip and not ip.startswith('127.'):
                        network_interfaces.append(ip)
        except Exception:
            pass
        
        # Debug summary
        add_to_serial_buffer(f"DEBUG: Network detection summary - IP: {local_ip}, SSID: {wifi_ssid}, Mode: {wifi_mode}")
        
        return {
            'local_ip': local_ip,
            'wifi_ssid': wifi_ssid,
            'wifi_mode': wifi_mode,
            'network_interfaces': network_interfaces
        }
    except Exception:
        return {
            'local_ip': '127.0.0.1',
            'wifi_ssid': None,
            'wifi_mode': 'unknown',
            'network_interfaces': []
        }

def get_network_ip():
    """Get the actual network IP address of the Raspberry Pi"""
    network_info = get_network_info()
    return network_info['local_ip']

def main():
    """Main function to start the weather station"""
    add_to_serial_buffer("Weather Station Raspberry Pi Version Starting...")
    
    # Initialize directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Initialize serial buffer
    config.serial_buffer = [""] * config.serial_buffer_size
    
    # Load settings (both legacy and Raspberry Pi settings)
    load_settings()
    
    # Initialize database
    init_database()
    
    # Start watchdog timer in background
    watchdog_thread = threading.Thread(target=watchdog_timer, daemon=True)
    watchdog_thread.start()
    
    # Start cleanup scheduler in background
    cleanup_thread = threading.Thread(target=cleanup_scheduler, daemon=True)
    cleanup_thread.start()
    
    # Get network information dynamically
    network_info = get_network_info()
    local_ip = network_info['local_ip']
    wifi_ssid = network_info['wifi_ssid']
    wifi_mode = network_info['wifi_mode']
    network_interfaces = network_info['network_interfaces']
    
    # Get server port from settings
    server_port = config.raspi_settings.get('web_server_port', 5000)
    
    add_to_serial_buffer("Weather Station started successfully")
    
    # Display network information dynamically
    if wifi_mode == "client" and wifi_ssid:
        add_to_serial_buffer(f"WiFi Mode: CLIENT - Connected to: {wifi_ssid}")
    elif wifi_mode == "access_point" and wifi_ssid:
        add_to_serial_buffer(f"WiFi Mode: ACCESS POINT - SSID: {wifi_ssid}")
    else:
        add_to_serial_buffer(f"WiFi Mode: {wifi_mode.upper()}")
        if wifi_ssid:
            add_to_serial_buffer(f"WiFi SSID: {wifi_ssid}")
    
    add_to_serial_buffer(f"Network IP: {local_ip}")
    if len(network_interfaces) > 1:
        add_to_serial_buffer(f"All IPs: {', '.join(network_interfaces)}")
    
    add_to_serial_buffer(f"Web interface available at: http://{local_ip}:{server_port}")
    add_to_serial_buffer(f"API endpoint: http://{local_ip}:{server_port}/api/weather")
    add_to_serial_buffer(f"Misol endpoint: http://{local_ip}:{server_port}/post")
    
    # Show Misol configuration info
    add_to_serial_buffer("=" * 50)
    add_to_serial_buffer("MISOL CONFIGURATION:")
    add_to_serial_buffer(f"WiFi SSID: {wifi_ssid if wifi_ssid else 'Any WiFi (connect to same network)'}")
    add_to_serial_buffer(f"Server URL: http://{local_ip}:{server_port}/post")
    add_to_serial_buffer("=" * 50)
    
    add_to_serial_buffer("Auto-cleanup enabled - will clean data older than 2 months every 24 hours")
    add_to_serial_buffer(f"External sync enabled: {config.raspi_settings['external_sync']['enabled']}")
    if config.raspi_settings['external_sync']['enabled']:
        add_to_serial_buffer(f"External server: {config.raspi_settings['external_sync']['server_url']}")
    
    # Start Flask app
    app.run(host='0.0.0.0', port=server_port, debug=False)

if __name__ == '__main__':
    main()
