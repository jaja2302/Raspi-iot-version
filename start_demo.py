#!/usr/bin/env python3
"""
Demo script to start the weather station with sample data
This creates a complete demo environment for testing
"""

import os
import json
import sqlite3
import time
import threading
import math
from datetime import datetime, timedelta
import random

def create_sample_data():
    """Create sample weather data for demonstration"""
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Initialize database
    conn = sqlite3.connect('data/weather.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    
    # Generate sample data for the last 7 days
    base_time = datetime.now() - timedelta(days=7)
    
    for i in range(168):  # 7 days * 24 hours = 168 data points
        current_time = base_time + timedelta(hours=i)
        
        # Generate realistic weather data with some randomness
        temp_out = 20 + 10 * random.random() + 5 * math.sin(i * 0.1)
        temp_in = temp_out - 2 + 4 * random.random()
        humidity_out = 40 + 40 * random.random()
        humidity_in = humidity_out - 10 + 20 * random.random()
        wind_speed = 5 + 15 * random.random()
        wind_direction = random.randint(0, 360)
        uv_index = max(0, 8 * random.random() - 2)
        pressure = 29.5 + 0.5 * random.random()
        solar_radiation = max(0, 1000 * random.random())
        
        cursor.execute('''
            INSERT INTO weather_data (
                datetime, windspeed_kmh, wind_direction, rain_rate_in,
                temp_in_c, temp_out_c, humidity_in, humidity_out,
                uv_index, wind_gust_kmh, barometric_pressure_rel_in,
                barometric_pressure_abs_in, solar_radiation_wm2,
                daily_rain_in, rain_today_in, total_rain_in,
                weekly_rain_in, monthly_rain_in, yearly_rain_in,
                max_daily_gust, wh65_batt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            current_time.strftime('%Y-%m-%d %H:%M:%S'),
            wind_speed,
            wind_direction,
            0.0,
            round(temp_in, 1),
            round(temp_out, 1),
            int(humidity_in),
            int(humidity_out),
            round(uv_index, 1),
            wind_speed + 5 * random.random(),
            round(pressure, 2),
            round(pressure - 0.03, 2),
            int(solar_radiation),
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            wind_speed + 10 * random.random(),
            3.2
        ))
    
    conn.commit()
    conn.close()
    
    print("✅ Sample data created successfully!")

def create_settings():
    """Create default settings file"""
    
    settings = {
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
    
    os.makedirs('data', exist_ok=True)
    with open('data/settings.json', 'w') as f:
        json.dump(settings, f, indent=2)
    
    print("✅ Settings file created!")

def start_demo():
    """Start the weather station demo"""
    
    print("🌤️ Weather Station Demo - Raspberry Pi Version")
    print("=" * 50)
    
    # Create necessary directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Create sample data
    print("Creating sample weather data...")
    create_sample_data()
    
    # Create settings
    print("Creating settings file...")
    create_settings()
    
    print("\n🚀 Starting Weather Station...")
    print("Web interface: http://localhost:5000")
    print("API endpoint: http://localhost:5000/api/weather")
    print("Press Ctrl+C to stop")
    print("\n" + "=" * 50)
    
    # Start the weather station
    try:
        from weather_station import main
        main()
    except KeyboardInterrupt:
        print("\n🛑 Demo stopped by user")
    except ImportError:
        print("❌ Error: weather_station.py not found!")
        print("Make sure you're in the correct directory.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    start_demo()