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
        self.db_file = "data/weather.db"
        self.station_id = 1
        self.post_interval = 3  # seconds
        self.watchdog_timeout = 60  # seconds
        
        # Default settings
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
    
    if os.path.exists(config.settings_file):
        add_to_serial_buffer("Settings file found. Attempting to read...")
        try:
            with open(config.settings_file, 'r') as file:
                settings_data = json.load(file)
                config.settings.update(settings_data)
                add_to_serial_buffer("Settings loaded successfully")
                add_to_serial_buffer(f"SSID: {config.settings['ssid']}")
                add_to_serial_buffer(f"ID: {config.settings['id']}")
        except Exception as e:
            add_to_serial_buffer(f"Failed to read settings file: {str(e)}")
    else:
        add_to_serial_buffer("Settings file not found. Using default settings...")
        save_settings()

def save_settings():
    """Save settings to JSON file (equivalent to saveSettings in C++)"""
    try:
        os.makedirs(os.path.dirname(config.settings_file), exist_ok=True)
        with open(config.settings_file, 'w') as file:
            json.dump(config.settings, file, indent=2)
        add_to_serial_buffer("Settings saved successfully")
    except Exception as e:
        add_to_serial_buffer(f"Failed to save settings: {str(e)}")

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
    """Scheduler for automatic cleanup - runs daily"""
    last_cleanup = time.time()
    cleanup_interval = 24 * 60 * 60  # Run cleanup every 24 hours
    
    while True:
        time.sleep(60)  # Check every minute
        current_time = time.time()
        
        # Check if it's time for cleanup (every 24 hours)
        if current_time - last_cleanup >= cleanup_interval:
            add_to_serial_buffer("Starting daily cleanup...")
            
            # 1. Cleanup old database records (> 2 months)
            cleanup_old_data()
            
            # 2. Clear old log files (not from today)
            clear_old_logs()
            
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
def handle_post():
    """Handle weather data POST (equivalent to handlePost in C++)"""
    try:
        # Parse weather data from request
        # Use device ID from ESP32 settings as default if not provided
        device_id = request.form.get('id')
        if device_id:
            device_id = int(device_id)
        else:
            # Use ID from ESP32 settings file as default
            device_id = config.settings.get('id', 1)
        
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
    
    # Load settings
    load_settings()
    
    # Initialize database
    init_database()
    
    # Start watchdog timer in background
    watchdog_thread = threading.Thread(target=watchdog_timer, daemon=True)
    watchdog_thread.start()
    
    # Start cleanup scheduler in background
    cleanup_thread = threading.Thread(target=cleanup_scheduler, daemon=True)
    cleanup_thread.start()
    
    # Get Raspberry Pi IP address
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "localhost"
    
    add_to_serial_buffer("Weather Station started successfully")
    add_to_serial_buffer(f"Web interface available at: http://{local_ip}:5000")
    add_to_serial_buffer(f"API endpoint: http://{local_ip}:5000/api/weather")
    add_to_serial_buffer("Auto-cleanup enabled - will clean data older than 2 months every 24 hours")
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
