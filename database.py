#!/usr/bin/env python3
"""
Shared Database Module for Weather Station
Provides consistent database operations for both weather_station.py and weather_interceptor.py
"""

import sqlite3
import os
from datetime import datetime, timedelta

class WeatherDatabase:
    def __init__(self, db_file="data/weather.db"):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Initialize database with proper schema"""
        try:
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Create the table with complete schema
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
                    model TEXT,
                    passkey TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Check existing schema and add missing columns
            cursor.execute("PRAGMA table_info(weather_data)")
            columns = cursor.fetchall()
            existing_columns = [col[1] for col in columns]
            
            # Define required columns with their definitions
            required_columns = {
                'device_id': 'INTEGER NOT NULL DEFAULT 44',
                'model': 'TEXT',
                'passkey': 'TEXT'
            }
            
            # Add missing columns
            for column_name, column_def in required_columns.items():
                if column_name not in existing_columns:
                    try:
                        cursor.execute(f'ALTER TABLE weather_data ADD COLUMN {column_name} {column_def}')
                        print(f"[OK] Added missing column: {column_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" in str(e).lower():
                            print(f"[INFO] Column {column_name} already exists")
                        else:
                            print(f"[WARN] Could not add column {column_name}: {e}")
            
            conn.commit()
            conn.close()
            print("[OK] Database initialized successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Database init error: {e}")
            return False
    
    def save_weather_data(self, data):
        """Save weather data to database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO weather_data (
                    device_id, datetime, windspeed_kmh, wind_direction, rain_rate_in,
                    temp_in_c, temp_out_c, humidity_in, humidity_out,
                    uv_index, wind_gust_kmh, barometric_pressure_rel_in,
                    barometric_pressure_abs_in, solar_radiation_wm2,
                    daily_rain_in, rain_today_in, total_rain_in,
                    weekly_rain_in, monthly_rain_in, yearly_rain_in,
                    max_daily_gust, wh65_batt, model, passkey
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('device_id', 99),
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
                data.get('wh65_batt', 0),
                data.get('model', ''),
                data.get('passkey', '')
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Save error: {e}")
            return False
    
    def get_recent_data(self, limit=10):
        """Get recent weather data"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT datetime, temp_out_c, humidity_out, windspeed_kmh, 
                       wind_direction, barometric_pressure_rel_in, model, device_id
                FROM weather_data 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            return results
            
        except Exception as e:
            print(f"❌ Get data error: {e}")
            return []
    
    def get_latest_data(self):
        """Get latest weather data"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM weather_data 
                ORDER BY created_at DESC 
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            return result
            
        except Exception as e:
            print(f"❌ Get latest data error: {e}")
            return None
    
    def get_database_info(self):
        """Get database information"""
        try:
            conn = sqlite3.connect(self.db_file)
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
            db_size = os.path.getsize(self.db_file) if os.path.exists(self.db_file) else 0
            
            conn.close()
            
            return {
                "total_records": total_records,
                "oldest_record": oldest_date,
                "newest_record": newest_date,
                "database_size_bytes": db_size,
                "database_size_mb": round(db_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            print(f"❌ Get database info error: {e}")
            return None
    
    def cleanup_old_data(self, days=60):
        """Clean up data older than specified days"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
            
            # Count records to be deleted
            cursor.execute('SELECT COUNT(*) FROM weather_data WHERE created_at < ?', (cutoff_str,))
            count_to_delete = cursor.fetchone()[0]
            
            if count_to_delete > 0:
                # Delete old records
                cursor.execute('DELETE FROM weather_data WHERE created_at < ?', (cutoff_str,))
                conn.commit()
                
                # Vacuum database to reclaim space
                cursor.execute('VACUUM')
                
                print(f"✅ Cleanup completed - {count_to_delete} old records deleted (older than {cutoff_str})")
            else:
                print("ℹ️  No old records found to delete")
            
            conn.close()
            return True, count_to_delete
            
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
            return False, 0
    
    def reset_database(self):
        """Reset database - clear all weather data"""
        try:
            conn = sqlite3.connect(self.db_file)
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
            
            print(f"✅ Database reset successfully - {count_before} records deleted")
            return True, count_before
            
        except Exception as e:
            print(f"❌ Reset database error: {e}")
            return False, 0

# Global database instance
db = WeatherDatabase()
