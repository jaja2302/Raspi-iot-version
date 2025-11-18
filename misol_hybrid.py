#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Misol HP2550 Hybrid Server
Sniff traffic + HTTP Server untuk dapat data dengan/tanpa LAN
"""

import subprocess
import threading
import urllib.parse
from datetime import datetime
from database import WeatherDatabase
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

class MisolHandler(BaseHTTPRequestHandler):
    db = None
    device_id = None
    
    def do_GET(self):
        self._handle_request()
    
    def do_POST(self):
        self._handle_request()
    
    def _handle_request(self):
        try:
            query_string = ""
            
            # GET request
            if '?' in self.path:
                query_string = self.path.split('?', 1)[1]
            
            # POST request
            if self.command == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    query_string = self.rfile.read(content_length).decode('utf-8')
            
            # Check weather data
            if query_string and any(param in query_string for param in ['windspeedmph=', 'tempf=', 'humidity=']):
                print("\n[HTTP-SERVER] Weather data received!")
                print("Time: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                print("From: {}".format(self.client_address[0]))
                
                weather_data = self.parse_weather_data(query_string)
                if weather_data:
                    self.save_weather_data(weather_data, source="HTTP")
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'success\n')
            
        except Exception as e:
            print("[ERROR] Request error: {}".format(e))
    
    def parse_weather_data(self, data_string):
        try:
            params = urllib.parse.parse_qs(data_string)
            weather_data = {}
            for key, value in params.items():
                if isinstance(value, list) and len(value) > 0:
                    weather_data[key] = value[0]
                else:
                    weather_data[key] = value
            
            local_datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
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
    
    def save_weather_data(self, data, source="UNKNOWN"):
        try:
            if self.db.save_weather_data(data):
                if self.db.last_insert_duplicate:
                    print("[INFO] Duplicate data skipped [{}]".format(source))
                else:
                    print("[SUCCESS] Data saved [{}]".format(source))
                    print("   Temp: {:.1f}C, Humidity: {}%".format(
                        data['temp_out_c'], data['humidity_out']))
                    print("   Wind: {:.1f} km/h".format(data['windspeed_kmh']))
                    print("-" * 50)
        except Exception as e:
            print("[ERROR] Save error: {}".format(e))
    
    def log_message(self, format, *args):
        pass


class TcpdumpSniffer:
    def __init__(self, db, device_id):
        self.db = db
        self.device_id = device_id
        self.running = False
    
    def start(self):
        self.running = True
        print("[TCPDUMP] Sniffer started")
        
        try:
            process = subprocess.Popen([
                'sudo', 'tcpdump', '-i', 'wlan0', '-A', '-s', '0',
                'host', '10.42.0.235', 'and', 'port', '80'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            while self.running:
                line = process.stdout.readline()
                if line and any(param in line for param in ['windspeedmph=', 'tempf=', 'humidity=']):
                    print("\n[TCPDUMP] Weather data detected!")
                    print("Time: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    
                    if 'PASSKEY=' in line or 'tempf=' in line:
                        data_string = self.extract_data(line)
                        if data_string:
                            weather_data = self.parse_weather_data(data_string)
                            if weather_data:
                                self.save_weather_data(weather_data, source="TCPDUMP")
        except Exception as e:
            print("[TCPDUMP ERROR] {}".format(e))
        finally:
            if 'process' in locals():
                process.terminate()
    
    def extract_data(self, line):
        # Extract query string dari tcpdump output
        for keyword in ['PASSKEY=', 'tempf=', 'windspeedmph=']:
            if keyword in line:
                start = line.find(keyword)
                if start != -1:
                    # Get until space or newline
                    data = line[start:].split()[0]
                    return data
        return None
    
    def parse_weather_data(self, data_string):
        # Same as MisolHandler
        try:
            params = urllib.parse.parse_qs(data_string)
            weather_data = {}
            for key, value in params.items():
                if isinstance(value, list) and len(value) > 0:
                    weather_data[key] = value[0]
                else:
                    weather_data[key] = value
            
            local_datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            converted_data = {
                'device_id': self.device_id,
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
        except:
            return None
    
    def save_weather_data(self, data, source="UNKNOWN"):
        try:
            if self.db.save_weather_data(data):
                if self.db.last_insert_duplicate:
                    print("[INFO] Duplicate data skipped [{}]".format(source))
                else:
                    print("[SUCCESS] Data saved [{}]".format(source))
                    print("   Temp: {:.1f}C, Humidity: {}%".format(
                        data['temp_out_c'], data['humidity_out']))
        except Exception as e:
            print("[ERROR] Save error: {}".format(e))
    
    def stop(self):
        self.running = False


def load_device_id():
    device_id = 99
    if os.path.exists('raspi_settings.json'):
        try:
            with open('raspi_settings.json', 'r') as f:
                data = json.load(f)
                if 'device_id' in data:
                    return data['device_id']
        except:
            pass
    if os.path.exists('data/settings.json'):
        try:
            with open('data/settings.json', 'r') as f:
                data = json.load(f)
                if 'id' in data:
                    return data['id']
        except:
            pass
    return device_id


def setup_iptables():
    """Setup iptables redirect"""
    try:
        # Check if rule exists
        check = subprocess.run(
            ['sudo', 'iptables', '-t', 'nat', '-C', 'PREROUTING', '-i', 'wlan0', '-p', 'tcp', '--dport', '80', '-j', 'REDIRECT', '--to-port', '80'],
            capture_output=True
        )
        
        if check.returncode != 0:
            # Add rule
            subprocess.run([
                'sudo', 'iptables', '-t', 'nat', '-A', 'PREROUTING',
                '-i', 'wlan0', '-p', 'tcp', '--dport', '80',
                '-j', 'REDIRECT', '--to-port', '80'
            ], check=True)
            print("[IPTABLES] Redirect rule added")
            return True
        else:
            print("[IPTABLES] Redirect rule already exists")
            return True
    except Exception as e:
        print("[IPTABLES ERROR] {}".format(e))
        return False


def main():
    print("=" * 60)
    print("Misol HP2550 Hybrid Server")
    print("HTTP Server + Tcpdump Sniffer")
    print("=" * 60)
    
    # Init database
    db = WeatherDatabase()
    db.init_database()
    device_id = load_device_id()
    print("[CONFIG] Device ID: {}".format(device_id))
    
    # Setup iptables
    print("\n[SETUP] Configuring iptables redirect...")
    setup_iptables()
    
    # Set handler
    MisolHandler.db = db
    MisolHandler.device_id = device_id
    
    # Start tcpdump sniffer in background
    sniffer = TcpdumpSniffer(db, device_id)
    sniffer_thread = threading.Thread(target=sniffer.start, daemon=True)
    sniffer_thread.start()
    
    # Start HTTP server
    try:
        httpd = HTTPServer(('0.0.0.0', 80), MisolHandler)
        print("[HTTP] HTTP Server started on port 80")
        print("\n[INFO] All systems ready!")
        print("[INFO] Mode: DUAL (HTTP + Sniffer)")
        print("[INFO] Dapat data dengan LAN atau tanpa LAN")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped")
        sniffer.stop()
    except Exception as e:
        print("[ERROR] {}".format(e))


if __name__ == "__main__":
    main()