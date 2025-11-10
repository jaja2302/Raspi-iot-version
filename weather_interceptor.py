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
        # Ensure database is initialized
        self.db.init_database()
        
        # Load settings
        self.settings_file = "data/settings.json"
        self.raspi_settings_file = "raspi_settings.json"
        self.device_id = None
        
        # Raw packet log file
        self.raw_log_file = "logs/misol_raw_packets.log"
        os.makedirs(os.path.dirname(self.raw_log_file), exist_ok=True)
        self.enable_raw_logging = False
        
        # Load settings from files
        self.load_settings()
        
        # Cache of last detected clients
        self.connected_clients = []
    
    def load_settings(self):
        """Load settings from JSON files"""
        try:
            # Load legacy settings first
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as file:
                    settings_data = json.load(file)
                    if 'id' in settings_data:
                        self.device_id = settings_data['id']
                        print(f"📋 Loaded device ID from settings: {self.device_id}")
            
            # Load Raspberry Pi settings
            if os.path.exists(self.raspi_settings_file):
                with open(self.raspi_settings_file, 'r') as file:
                    raspi_data = json.load(file)
                    # Use device_id from raspi_settings if available
                    if 'device_id' in raspi_data:
                        self.device_id = raspi_data['device_id']
                        print(f"📋 Loaded device ID from Raspberry Pi settings: {self.device_id}")
            
            if self.device_id is None:
                self.device_id = 99
                print("⚠️  Device ID not found in settings. Using fallback value: 99")
            
        except Exception as e:
            if self.device_id is None:
                self.device_id = 99
            print(f"⚠️  Error loading settings: {e}, using device ID: {self.device_id}")
    
    def log_connected_devices(self):
        """Detect and log Wi-Fi clients connected to the Raspberry Pi AP"""
        clients = set()
        try:
            # Prefer iw station dump for devices connected to wlan0
            iw_result = subprocess.run(
                ['iw', 'dev', 'wlan0', 'station', 'dump'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if iw_result.returncode == 0 and iw_result.stdout:
                for line in iw_result.stdout.splitlines():
                    line = line.strip()
                    if line.startswith('Station '):
                        parts = line.split()
                        if len(parts) >= 2:
                            clients.add(parts[1].lower())
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"⚠️  iw scan error: {e}")
        
        # Fallback to arp table if iw didn't return anything
        if not clients:
            try:
                arp_result = subprocess.run(
                    ['arp', '-a'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if arp_result.returncode == 0 and arp_result.stdout:
                    for line in arp_result.stdout.splitlines():
                        parts = line.split()
                        # Typical format: ? (192.168.4.2) at aa:bb:cc:dd:ee:ff [ether] on wlan0
                        if len(parts) >= 4 and parts[3] != '<incomplete>':
                            mac = parts[3].lower()
                            if self._is_mac_address(mac):
                                clients.add(mac)
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"⚠️  arp scan error: {e}")
        
        if clients:
            sorted_clients = sorted(clients)
            if sorted_clients != self.connected_clients:
                print("📡 Connected Wi-Fi clients detected:")
                for mac in sorted_clients:
                    print(f"   - {mac}")
                self.connected_clients = sorted_clients
        else:
            if self.connected_clients:
                print("📡 Tidak ada klien Wi-Fi terdeteksi saat ini.")
                self.connected_clients = []
    
    def log_raw_packet(self, line):
        """Write raw tcpdump line to log for debugging"""
        if not self.enable_raw_logging:
            return
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            line = line.rstrip('\n')
            with open(self.raw_log_file, 'a', encoding='utf-8') as logfile:
                logfile.write(f"[{timestamp}] {line}\n")
            print(f"📝 RAW: {line}")
        except Exception as e:
            print(f"⚠️  Unable to write raw packet log: {e}")
    
    @staticmethod
    def _is_mac_address(candidate):
        if len(candidate) != 17:
            return False
        allowed = set('0123456789abcdef:')
        return all(ch in allowed for ch in candidate)
    
    def reload_settings(self):
        """Reload settings from files (useful for dynamic updates)"""
        self.load_settings()
        print(f"🔄 Settings reloaded - Device ID: {self.device_id}")
        self.log_connected_devices()
    
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
                'device_id': self.device_id,  # Use device ID from settings
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
                    print(f"ℹ️  Duplicate data skipped for {data['datetime']} (device {data['device_id']})")
                else:
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
        print(f"📋 Using Device ID: {self.device_id}")
        print("Monitoring for Misol HP2550 data...")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        # Log connected devices once at startup
        self.log_connected_devices()
        
        try:
            # Start tcpdump process
            process = subprocess.Popen([
                'sudo', 'tcpdump', '-i', 'any', '-A', '-s', '0', 
                'tcp port 80 or tcp port 443'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            last_settings_reload = time.time()
            settings_reload_interval = 30  # Reload settings every 30 seconds
            
            while self.running:
                # Periodically reload settings to pick up changes
                current_time = time.time()
                if current_time - last_settings_reload > settings_reload_interval:
                    self.reload_settings()
                    last_settings_reload = current_time
                
                line = process.stdout.readline()
                if line:
                    # Record raw HTTP lines for troubleshooting
                    if 'PASSKEY=' in line or 'GET ' in line or 'POST ' in line:
                        self.log_raw_packet(line)
                    
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
    import sys
    interceptor = WeatherInterceptor()
    
    # Check command line arguments
    auto_mode = False
    show_data_only = False
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-a', '--auto', 'auto']:
            auto_mode = True
        elif sys.argv[1] in ['-d', '--data', 'data']:
            show_data_only = True
        elif sys.argv[1] in ['-h', '--help', 'help']:
            print("🌤️  Misol HP2550 Weather Data Interceptor")
            print("=" * 50)
            print("Usage:")
            print("  python weather_interceptor.py           # Interactive mode")
            print("  python weather_interceptor.py auto      # Auto-start intercepting")
            print("  python weather_interceptor.py data      # Show recent data only")
            print("  python weather_interceptor.py help      # Show this help")
            return
    
    # Check if running in PM2 auto mode
    import os
    if os.getenv('INTERCEPTOR_MODE') == 'auto' or auto_mode:
        print("🌤️  Misol HP2550 Weather Data Interceptor (Auto Mode)")
        print("=" * 60)
        print("Auto-starting intercepting mode...")
        interceptor.start_intercepting()
    elif show_data_only:
        print("🌤️  Misol HP2550 Weather Data Interceptor (Data Mode)")
        print("=" * 60)
        interceptor.show_recent_data()
    else:
        # Default behavior: start intercepting directly
        print("🌤️  Misol HP2550 Weather Data Interceptor")
        print("=" * 50)
        print(f"📋 Current Device ID: {interceptor.device_id}")
        print("Starting network sniffing automatically...")
        print("Press Ctrl+C to stop")
        print("=" * 50)
        interceptor.start_intercepting()

if __name__ == "__main__":
    main()
