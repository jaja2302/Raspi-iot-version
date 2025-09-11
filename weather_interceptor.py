#!/usr/bin/env python3
"""
Weather Data Interceptor untuk Misol HP2550
Menangkap data dari tcpdump dan menyimpannya ke database
"""

import subprocess
import re
import json
import os
import time
from datetime import datetime, timedelta
import threading
import urllib.parse
from database import WeatherDatabase

class WeatherInterceptor:
    def __init__(self):
        self.running = False
        self.db = WeatherDatabase()
        
    
    def parse_weather_data(self, data_string):
        """Parse weather data dari Misol HP2550"""
        try:
            # Parse URL parameters
            params = urllib.parse.parse_qs(data_string)
            
            # Convert to single values
            weather_data = {}
            for key, value in params.items():
                if isinstance(value, list) and len(value) > 0:
                    weather_data[key] = value[0]
                else:
                    weather_data[key] = value
            
            # Convert UTC datetime to local timezone (GMT+7)
            utc_datetime_str = weather_data.get('dateutc', '').replace('+', ' ')
            local_datetime_str = utc_datetime_str
            
            try:
                # Parse UTC datetime
                utc_dt = datetime.strptime(utc_datetime_str, '%Y-%m-%d %H:%M:%S')
                # Add 7 hours for GMT+7 (Indonesia timezone)
                local_dt = utc_dt + timedelta(hours=7)
                local_datetime_str = local_dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                print(f"⚠️  Timezone conversion error: {e}, using original time")
            
            # Convert to our format
            converted_data = {
                'device_id': 44,  # Default device ID
                'datetime': local_datetime_str,
                'windspeed_kmh': float(weather_data.get('windspeedmph', 0)) * 1.60934,
                'wind_direction': int(weather_data.get('winddir', 0)),
                'rain_rate_in': float(weather_data.get('rainratein', 0)),
                'temp_in_c': (5.0 / 9.0) * (float(weather_data.get('tempinf', 0)) - 32.0),
                'temp_out_c': (5.0 / 9.0) * (float(weather_data.get('tempf', 0)) - 32.0),
                'humidity_in': int(weather_data.get('humidityin', 0)),
                'humidity_out': int(weather_data.get('humidity', 0)),
                'uv_index': float(weather_data.get('uv', 0)),
                'wind_gust_kmh': float(weather_data.get('windgustmph', 0)) * 1.60934,
                'barometric_pressure_rel_in': float(weather_data.get('baromrelin', 0)),
                'barometric_pressure_abs_in': float(weather_data.get('baromabsin', 0)),
                'solar_radiation_wm2': float(weather_data.get('solarradiation', 0)),
                'daily_rain_in': float(weather_data.get('dailyrainin', 0)),
                'rain_today_in': float(weather_data.get('raintodayin', 0)),
                'total_rain_in': float(weather_data.get('totalrainin', 0)),
                'weekly_rain_in': float(weather_data.get('weeklyrainin', 0)),
                'monthly_rain_in': float(weather_data.get('monthlyrainin', 0)),
                'yearly_rain_in': float(weather_data.get('yearlyrainin', 0)),
                'max_daily_gust': float(weather_data.get('maxdailygust', 0)),
                'wh65_batt': float(weather_data.get('wh65batt', 0)),
                'model': weather_data.get('model', ''),
                'passkey': weather_data.get('PASSKEY', '')
            }
            
            return converted_data
            
        except Exception as e:
            print(f"❌ Parse error: {e}")
            return None
    
    def save_weather_data(self, data):
        """Save weather data to database"""
        try:
            if self.db.save_weather_data(data):
                print(f"✅ Weather data saved: {data['datetime']}")
                print(f"   Temp: {data['temp_out_c']:.1f}°C, Humidity: {data['humidity_out']}%")
                print(f"   Wind: {data['windspeed_kmh']:.1f} km/h, Direction: {data['wind_direction']}°")
                print(f"   Pressure: {data['barometric_pressure_rel_in']:.2f} inHg")
                print("-" * 50)
            else:
                print(f"❌ Failed to save weather data")
        except Exception as e:
            print(f"❌ Save error: {e}")
    
    def start_intercepting(self):
        """Start intercepting weather data"""
        self.running = True
        print("🚀 Starting Weather Data Interceptor...")
        print("Monitoring for Misol HP2550 data...")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        try:
            # Start tcpdump process
            process = subprocess.Popen([
                'sudo', 'tcpdump', '-i', 'any', '-A', '-s', '0', 
                'tcp port 80 or tcp port 443'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            while self.running:
                line = process.stdout.readline()
                if line:
                    # Check if line contains weather data
                    if any(param in line for param in ['windspeedmph=', 'tempf=', 'humidity=', 'dateutc=']):
                        print(f"🌤️  WEATHER DATA DETECTED!")
                        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # Extract data from line
                        if 'PASSKEY=' in line:
                            # Find the data part
                            start = line.find('PASSKEY=')
                            if start != -1:
                                data_string = line[start:].split()[0]  # Get first word after PASSKEY
                                
                                # Parse and save data
                                weather_data = self.parse_weather_data(data_string)
                                if weather_data:
                                    self.save_weather_data(weather_data)
                
        except KeyboardInterrupt:
            print("\n🛑 Interceptor stopped by user")
        except Exception as e:
            print(f"❌ Interceptor error: {e}")
        finally:
            self.running = False
            if 'process' in locals():
                process.terminate()
    
    def show_recent_data(self):
        """Show recent weather data"""
        try:
            results = self.db.get_recent_data(10)
            
            if results:
                print("\n📊 Recent Weather Data:")
                print("=" * 80)
                for row in results:
                    print(f"Time: {row[0]}")
                    print(f"Temp: {row[1]:.1f}°C, Humidity: {row[2]}%")
                    print(f"Wind: {row[3]:.1f} km/h, Direction: {row[4]}°")
                    print(f"Pressure: {row[5]:.2f} inHg, Model: {row[6]}, Device: {row[7]}")
                    print("-" * 80)
            else:
                print("No weather data found yet")
                
        except Exception as e:
            print(f"❌ Show data error: {e}")

def main():
    interceptor = WeatherInterceptor()
    
    # Check if running in PM2 auto mode
    import os
    if os.getenv('INTERCEPTOR_MODE') == 'auto':
        print("🌤️  Misol HP2550 Weather Data Interceptor (PM2 Auto Mode)")
        print("=" * 60)
        print("Auto-starting intercepting mode...")
        interceptor.start_intercepting()
    else:
        print("🌤️  Misol HP2550 Weather Data Interceptor")
        print("=" * 50)
        print("1. Start intercepting")
        print("2. Show recent data")
        print("3. Exit")
        
        while True:
            try:
                choice = input("\nChoose option (1-3): ").strip()
                
                if choice == '1':
                    interceptor.start_intercepting()
                elif choice == '2':
                    interceptor.show_recent_data()
                elif choice == '3':
                    print("Goodbye! 👋")
                    break
                else:
                    print("Invalid choice!")
                    
            except KeyboardInterrupt:
                print("\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()
