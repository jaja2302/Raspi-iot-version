#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Misol HP2550 Local Server
Menerima data langsung dari Misol tanpa perlu tcpdump
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from datetime import datetime
from database import WeatherDatabase
import json
import os
import platform

class MisolHandler(BaseHTTPRequestHandler):
    # Share database instance
    db = None
    device_id = None
    
    def do_GET(self):
        """Handle GET request dari Misol"""
        try:
            # Parse URL dan query string
            if '?' in self.path:
                path, query_string = self.path.split('?', 1)
                
                # Check if this is weather data
                if any(param in query_string for param in ['windspeedmph=', 'tempf=', 'humidity=']):
                    print("\n[WEATHER] Data received!")
                    print("Time: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    print("From: {}".format(self.client_address[0]))
                    
                    # Parse and save weather data
                    weather_data = self.parse_weather_data(query_string)
                    if weather_data:
                        self.save_weather_data(weather_data)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'success\n')
            
        except Exception as e:
            print("[ERROR] Error handling request: {}".format(e))
            self.send_error(500)
    
    def do_POST(self):
        """Handle POST request"""
        self.do_GET()
    
    def parse_weather_data(self, query_string):
        """Parse weather data dari query string"""
        try:
            # Parse URL parameters
            params = urllib.parse.parse_qs(query_string)
            
            # Convert to single values
            weather_data = {}
            for key, value in params.items():
                if isinstance(value, list) and len(value) > 0:
                    weather_data[key] = value[0]
                else:
                    weather_data[key] = value
            
            # Use current datetime from Raspberry Pi
            local_datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Convert to our format
            converted_data = {
                'device_id': self.device_id or 99,
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
            print("[ERROR] Parse error: {}".format(e))
            return None
    
    def save_weather_data(self, data):
        """Save weather data to database"""
        try:
            if self.db.save_weather_data(data):
                if self.db.last_insert_duplicate:
                    print("[INFO] Duplicate data skipped")
                else:
                    print("[SUCCESS] Weather data saved!")
                    print("   Temp: {:.1f}C, Humidity: {}%".format(
                        data['temp_out_c'], data['humidity_out']))
                    print("   Wind: {:.1f} km/h, Direction: {}deg".format(
                        data['windspeed_kmh'], data['wind_direction']))
                    print("   Pressure: {:.2f} inHg".format(
                        data['barometric_pressure_rel_in']))
                    print("-" * 50)
            else:
                print("[ERROR] Failed to save weather data")
        except Exception as e:
            print("[ERROR] Save error: {}".format(e))
    
    def log_message(self, format, *args):
        """Override to suppress default logging"""
        pass

def load_device_id():
    """Load device ID from settings"""
    device_id = 99  # default
    
    # Try raspi_settings.json first
    if os.path.exists('raspi_settings.json'):
        try:
            with open('raspi_settings.json', 'r') as f:
                data = json.load(f)
                if 'device_id' in data:
                    device_id = data['device_id']
                    print("[CONFIG] Device ID from raspi_settings.json: {}".format(device_id))
                    return device_id
        except Exception as e:
            print("[WARNING] Error reading raspi_settings.json: {}".format(e))
    
    # Fallback to data/settings.json
    if os.path.exists('data/settings.json'):
        try:
            with open('data/settings.json', 'r') as f:
                data = json.load(f)
                if 'id' in data:
                    device_id = data['id']
                    print("[CONFIG] Device ID from settings.json: {}".format(device_id))
                    return device_id
        except Exception as e:
            print("[WARNING] Error reading settings.json: {}".format(e))
    
    print("[CONFIG] Using default device ID: {}".format(device_id))
    return device_id

def main():
    import sys
    
    print("Misol HP2550 Local Server")
    print("=" * 60)
    
    # Initialize database
    db = WeatherDatabase()
    db.init_database()
    
    # Load device ID
    device_id = load_device_id()
    
    # Set shared resources
    MisolHandler.db = db
    MisolHandler.device_id = device_id
    
    # Determine port (default 8080 for development, 80 for production)
    port = 8080  # Default untuk testing/Windows
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    
    # Check if running on Raspberry Pi (Linux)
    if platform.system() == 'Linux' and port == 8080:
        port = 80  # Auto gunakan port 80 di Linux
    
    # Create server
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, MisolHandler)
    
    print("[SERVER] Started on port {}".format(port))
    print("[CONFIG] Device ID: {}".format(device_id))
    print("[INFO] Listening for Misol HP2550 data...")
    if port != 80:
        print("[TEST] URL: http://localhost:{}/?tempf=75&humidity=60&windspeedmph=5".format(port))
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user")
    finally:
        httpd.server_close()

if __name__ == "__main__":
    main()