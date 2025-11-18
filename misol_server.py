#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Misol HP2550 All-in-One Server
DNS Server + HTTP Server dalam satu program
Tidak perlu edit config sistem!
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from datetime import datetime
from database import WeatherDatabase
import json
import os
import platform
import socket
import struct
import threading

class MisolHandler(BaseHTTPRequestHandler):
    db = None
    device_id = None
    
    def do_GET(self):
        """Handle GET request dari Misol"""
        try:
            if '?' in self.path:
                path, query_string = self.path.split('?', 1)
                
                if any(param in query_string for param in ['windspeedmph=', 'tempf=', 'humidity=']):
                    print("\n[WEATHER] Data received!")
                    print("Time: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    print("From: {}".format(self.client_address[0]))
                    
                    weather_data = self.parse_weather_data(query_string)
                    if weather_data:
                        self.save_weather_data(weather_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'success\n')
            
        except Exception as e:
            print("[ERROR] Error handling request: {}".format(e))
            self.send_error(500)
    
    def do_POST(self):
        """Handle POST request"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length).decode('utf-8')
                
                if any(param in post_data for param in ['windspeedmph=', 'tempf=', 'humidity=']):
                    print("\n[WEATHER] Data received (POST)!")
                    print("Time: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    print("From: {}".format(self.client_address[0]))
                    
                    weather_data = self.parse_weather_data(post_data)
                    if weather_data:
                        self.save_weather_data(weather_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'success\n')
            
        except Exception as e:
            print("[ERROR] Error handling POST: {}".format(e))
            self.send_error(500)
    
    def parse_weather_data(self, data_string):
        """Parse weather data dari query string"""
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


class SimpleDNSServer:
    """Simple DNS server untuk redirect domain Misol ke local IP"""
    
    def __init__(self, local_ip, port=53):
        self.local_ip = local_ip
        self.port = port
        self.running = False
        self.sock = None
        
        # Domains yang akan di-redirect
        self.redirect_domains = [
            b'api.ecowitt.net',
            b'upload.ecowitt.net',
            b'rtupdate.ecowitt.net',
            b'rtupdate.wunderground.com',
            b'weatherstation.wunderground.com'
        ]
    
    def start(self):
        """Start DNS server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('0.0.0.0', self.port))
            self.running = True
            
            print("[DNS] DNS Server started on port {}".format(self.port))
            print("[DNS] Redirecting weather domains to {}".format(self.local_ip))
            
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(512)
                    response = self.handle_dns_query(data)
                    if response:
                        self.sock.sendto(response, addr)
                except Exception as e:
                    if self.running:
                        print("[DNS ERROR] {}".format(e))
        
        except Exception as e:
            print("[DNS ERROR] Failed to start DNS server: {}".format(e))
        finally:
            if self.sock:
                self.sock.close()
    
    def handle_dns_query(self, data):
        """Handle DNS query dan return response"""
        try:
            # Parse DNS query (simplified)
            if len(data) < 12:
                return None
            
            # Extract query domain
            domain = self.extract_domain(data)
            
            # Check if domain should be redirected
            should_redirect = False
            for redirect_domain in self.redirect_domains:
                if redirect_domain in domain.lower():
                    should_redirect = True
                    print("[DNS] Redirecting {} to {}".format(
                        domain.decode('utf-8', errors='ignore'), self.local_ip))
                    break
            
            if not should_redirect:
                return None  # Let system DNS handle it
            
            # Build DNS response
            response = self.build_dns_response(data, self.local_ip)
            return response
            
        except Exception as e:
            print("[DNS ERROR] Query handling error: {}".format(e))
            return None
    
    def extract_domain(self, data):
        """Extract domain name from DNS query"""
        try:
            domain = b''
            i = 12  # Skip DNS header
            while i < len(data):
                length = data[i]
                if length == 0:
                    break
                domain += data[i+1:i+1+length] + b'.'
                i += length + 1
            return domain[:-1] if domain else b''
        except:
            return b''
    
    def build_dns_response(self, query, ip):
        """Build DNS response with local IP"""
        try:
            # DNS Response header
            transaction_id = query[0:2]
            flags = b'\x81\x80'  # Standard query response, no error
            questions = b'\x00\x01'
            answer_rrs = b'\x00\x01'
            authority_rrs = b'\x00\x00'
            additional_rrs = b'\x00\x00'
            
            # Question section (copy from query)
            question = query[12:]  # Skip header
            
            # Answer section
            # Name pointer to question
            answer_name = b'\xc0\x0c'
            # Type A (IPv4)
            answer_type = b'\x00\x01'
            # Class IN
            answer_class = b'\x00\x01'
            # TTL (60 seconds)
            answer_ttl = b'\x00\x00\x00\x3c'
            # Data length (4 bytes for IPv4)
            answer_length = b'\x00\x04'
            # IP address
            ip_parts = ip.split('.')
            answer_ip = bytes([int(p) for p in ip_parts])
            
            response = (transaction_id + flags + questions + answer_rrs + 
                       authority_rrs + additional_rrs + question + 
                       answer_name + answer_type + answer_class + 
                       answer_ttl + answer_length + answer_ip)
            
            return response
        except Exception as e:
            print("[DNS ERROR] Response building error: {}".format(e))
            return None
    
    def stop(self):
        """Stop DNS server"""
        self.running = False
        if self.sock:
            self.sock.close()


def get_wlan_ip():
    """Get IP address of wlan0"""
    try:
        import subprocess
        result = subprocess.run(['ip', 'addr', 'show', 'wlan0'], 
                              capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'inet ' in line:
                ip = line.strip().split()[1].split('/')[0]
                return ip
    except:
        pass
    return '10.42.0.1'  # Default


def load_device_id():
    """Load device ID from settings"""
    device_id = 99
    
    if os.path.exists('raspi_settings.json'):
        try:
            with open('raspi_settings.json', 'r') as f:
                data = json.load(f)
                if 'device_id' in data:
                    device_id = data['device_id']
                    print("[CONFIG] Device ID: {}".format(device_id))
                    return device_id
        except Exception as e:
            print("[WARNING] Error reading raspi_settings.json: {}".format(e))
    
    if os.path.exists('data/settings.json'):
        try:
            with open('data/settings.json', 'r') as f:
                data = json.load(f)
                if 'id' in data:
                    device_id = data['id']
                    print("[CONFIG] Device ID: {}".format(device_id))
                    return device_id
        except Exception as e:
            print("[WARNING] Error reading settings.json: {}".format(e))
    
    print("[CONFIG] Using default device ID: {}".format(device_id))
    return device_id


def main():
    import sys
    
    print("=" * 60)
    print("Misol HP2550 All-in-One Server")
    print("DNS Server + HTTP Server")
    print("=" * 60)
    
    # Get local IP
    local_ip = get_wlan_ip()
    print("[NETWORK] Detected wlan0 IP: {}".format(local_ip))
    
    # Initialize database
    db = WeatherDatabase()
    db.init_database()
    
    # Load device ID
    device_id = load_device_id()
    
    # Set shared resources
    MisolHandler.db = db
    MisolHandler.device_id = device_id
    
    # Determine HTTP port
    http_port = 80
    if len(sys.argv) > 1:
        try:
            http_port = int(sys.argv[1])
        except:
            pass
    
    # Start DNS server in background thread
    dns_server = SimpleDNSServer(local_ip, port=53)
    dns_thread = threading.Thread(target=dns_server.start, daemon=True)
    dns_thread.start()
    
    # Give DNS server time to start
    import time
    time.sleep(1)
    
    # Create HTTP server
    try:
        server_address = ('0.0.0.0', http_port)
        httpd = HTTPServer(server_address, MisolHandler)
        
        print("[HTTP] HTTP Server started on port {}".format(http_port))
        print("[INFO] All systems ready!")
        print("[INFO] Waiting for Misol data...")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user")
    except Exception as e:
        print("[ERROR] HTTP Server error: {}".format(e))
    finally:
        dns_server.stop()
        if 'httpd' in locals():
            httpd.server_close()


if __name__ == "__main__":
    main()