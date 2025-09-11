#!/usr/bin/env python3
"""
Weather Data Sniffer untuk Misol HP2550
Menggunakan network sniffing untuk intercept data weather
"""

import socket
import struct
import json
import time
from datetime import datetime
import threading
import sqlite3
import os

class WeatherSniffer:
    def __init__(self):
        self.running = False
        self.db_file = "data/weather.db"
        self.init_database()
        
    def init_database(self):
        """Initialize database untuk menyimpan data"""
        try:
            os.makedirs('data', exist_ok=True)
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sniffed_weather_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_ip TEXT,
                    destination_ip TEXT,
                    port INTEGER,
                    data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Database init error: {e}")
    
    def save_sniffed_data(self, source_ip, dest_ip, port, data):
        """Save sniffed data to database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sniffed_weather_data (source_ip, destination_ip, port, data)
                VALUES (?, ?, ?, ?)
            ''', (source_ip, dest_ip, port, data))
            
            conn.commit()
            conn.close()
            
            print(f"Sniffed data saved: {source_ip} -> {dest_ip}:{port}")
            print(f"Data: {data[:100]}...")
            
        except Exception as e:
            print(f"Save error: {e}")
    
    def parse_weather_data(self, data):
        """Parse weather data dari HTTP request"""
        try:
            # Cari parameter weather dalam data
            if b'windspeedmph=' in data or b'tempf=' in data or b'humidity=' in data:
                print("🌤️  WEATHER DATA DETECTED!")
                
                # Extract parameters
                params = {}
                lines = data.decode('utf-8', errors='ignore').split('\n')
                
                for line in lines:
                    if '=' in line and any(param in line for param in ['windspeedmph', 'tempf', 'humidity', 'dateutc']):
                        key, value = line.split('=', 1)
                        params[key.strip()] = value.strip()
                
                if params:
                    print(f"Weather parameters: {json.dumps(params, indent=2)}")
                    return params
                    
        except Exception as e:
            print(f"Parse error: {e}")
        
        return None
    
    def sniff_packets(self):
        """Sniff network packets untuk weather data"""
        try:
            # Create raw socket
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            
            print("🔍 Starting packet sniffing...")
            print("Waiting for Misol HP2550 weather data...")
            
            while self.running:
                try:
                    # Receive packet
                    packet, addr = s.recvfrom(65535)
                    
                    # Parse IP header
                    ip_header = packet[0:20]
                    iph = struct.unpack('!BBHHHBBH4s4s', ip_header)
                    
                    source_ip = socket.inet_ntoa(iph[8])
                    dest_ip = socket.inet_ntoa(iph[9])
                    protocol = iph[6]
                    
                    # Check if it's TCP
                    if protocol == 6:
                        # Parse TCP header
                        tcp_header = packet[20:40]
                        tcph = struct.unpack('!HHLLBBHHH', tcp_header)
                        source_port = tcph[0]
                        dest_port = tcph[1]
                        
                        # Check if it's HTTP traffic (port 80 or 443)
                        if dest_port in [80, 443] or source_port in [80, 443]:
                            # Extract data
                            data = packet[40:]
                            
                            # Check if it contains weather data
                            weather_params = self.parse_weather_data(data)
                            if weather_params:
                                self.save_sniffed_data(source_ip, dest_ip, dest_port, data)
                
                except socket.error as e:
                    if self.running:
                        print(f"Socket error: {e}")
                    break
                except Exception as e:
                    print(f"Packet processing error: {e}")
                    
        except PermissionError:
            print("❌ Permission denied! Run with sudo:")
            print("sudo python3 weather_sniffer.py")
        except Exception as e:
            print(f"Sniffing error: {e}")
    
    def start_sniffing(self):
        """Start packet sniffing"""
        self.running = True
        print("🚀 Weather Data Sniffer Started")
        print("=" * 50)
        print("Monitoring for Misol HP2550 weather data...")
        print("Make sure Misol is connected to the same WiFi network")
        print("Press Ctrl+C to stop")
        print("=" * 50)
        
        try:
            self.sniff_packets()
        except KeyboardInterrupt:
            print("\n🛑 Sniffing stopped by user")
        finally:
            self.running = False
    
    def show_sniffed_data(self):
        """Show sniffed weather data"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT source_ip, destination_ip, port, data, timestamp 
                FROM sniffed_weather_data 
                ORDER BY timestamp DESC 
                LIMIT 10
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            if results:
                print("\n📊 Recent Sniffed Data:")
                print("-" * 80)
                for row in results:
                    print(f"Time: {row[4]}")
                    print(f"From: {row[0]} -> {row[1]}:{row[2]}")
                    print(f"Data: {row[3][:200]}...")
                    print("-" * 80)
            else:
                print("No sniffed data found yet")
                
        except Exception as e:
            print(f"Show data error: {e}")

def main():
    sniffer = WeatherSniffer()
    
    print("🌤️  Misol HP2550 Weather Data Sniffer")
    print("=" * 50)
    print("1. Start sniffing")
    print("2. Show sniffed data")
    print("3. Exit")
    
    while True:
        try:
            choice = input("\nChoose option (1-3): ").strip()
            
            if choice == '1':
                sniffer.start_sniffing()
            elif choice == '2':
                sniffer.show_sniffed_data()
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
