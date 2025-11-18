#!/usr/bin/env python3
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
                    print(f"\n🌤️  WEATHER DATA RECEIVED!")
                    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"From: {self.client_address[0]}")
                    
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
            print(f"❌ Error handling request: {e}")
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
            print(f"❌ Parse error: {e}")
            return None
    
    def save_weather_data(self, data):
        """Save weather data to database"""
        try:
            if self.db.save_weather_data(data):
                if self.db.last_insert_duplicate:
                    print(f"ℹ️  Duplicate data skipped")
                else:
                    print(f"✅ Weather data saved!")
                    print(f"   Temp: {data['temp_out_c']:.1f}°C, Humidity: {data['humidity_out']}%")
                    print(f"   Wind: {data['windspeed_kmh']:.1f} km/h, Direction: {data['wind_direction']}°")
                    print(f"   Pressure: {data['barometric_pressure_rel_in']:.2f} inHg")
                    print("-" * 50)
            else:
                print(f"❌ Failed to save weather data")
        except Exception as e:
            print(f"❌ Save error: {e}")
    
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
                    print(f"📋 Device ID from raspi_settings.json: {device_id}")
                    return device_id
        except Exception as e:
            print(f"⚠️  Error reading raspi_settings.json: {e}")
    
    # Fallback to data/settings.json
    if os.path.exists('data/settings.json'):
        try:
            with open('data/settings.json', 'r') as f:
                data = json.load(f)
                if 'id' in data:
                    device_id = data['id']
                    print(f"📋 Device ID from settings.json: {device_id}")
                    return device_id
        except Exception as e:
            print(f"⚠️  Error reading settings.json: {e}")
    
    print(f"📋 Using default device ID: {device_id}")
    return device_id

def main():
    print("🌤️  Misol HP2550 Local Server")
    print("=" * 60)
    
    # Initialize database
    db = WeatherDatabase()
    db.init_database()
    
    # Load device ID
    device_id = load_device_id()
    
    # Set shared resources
    MisolHandler.db = db
    MisolHandler.device_id = device_id
    
    # Create server
    server_address = ('0.0.0.0', 80)
    httpd = HTTPServer(server_address, MisolHandler)
    
    print(f"🚀 Server started on port 80")
    print(f"📋 Device ID: {device_id}")
    print(f"🌐 Listening for Misol HP2550 data...")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    finally:
        httpd.server_close()

if __name__ == "__main__":
    main()