#!/usr/bin/env python3
"""
Main Application Launcher
Menjalankan Weather Station dan Weather Interceptor secara bersamaan
"""

import subprocess
import threading
import time
import signal
import sys
import os
from datetime import datetime

class WeatherSystemLauncher:
    def __init__(self):
        self.weather_station_process = None
        self.weather_interceptor_process = None
        self.running = True
        
    def start_weather_station(self):
        """Start Weather Station Flask application"""
        try:
            print("🌐 Starting Weather Station...")
            creationflags = 0
            if os.name == 'nt':
                # Open in a new console window on Windows
                creationflags = subprocess.CREATE_NEW_CONSOLE
            self.weather_station_process = subprocess.Popen(
                [sys.executable, 'weather_station.py'],
                creationflags=creationflags,
            )
            print(f"✅ Weather Station started (PID: {self.weather_station_process.pid})")
                
        except Exception as e:
            print(f"❌ Error starting Weather Station: {e}")
    
    def start_weather_interceptor(self):
        """Start Weather Interceptor for network sniffing"""
        try:
            print("🌤️  Starting Weather Interceptor...")
            creationflags = 0
            if os.name == 'nt':
                # Open in a new console window on Windows
                creationflags = subprocess.CREATE_NEW_CONSOLE
            self.weather_interceptor_process = subprocess.Popen(
                [sys.executable, 'weather_interceptor.py'],
                creationflags=creationflags,
            )
            print(f"✅ Weather Interceptor started (PID: {self.weather_interceptor_process.pid})")
                
        except Exception as e:
            print(f"❌ Error starting Weather Interceptor: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}. Shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def shutdown(self):
        """Gracefully shutdown all processes"""
        self.running = False
        
        print("🔄 Shutting down Weather Station...")
        if self.weather_station_process:
            self.weather_station_process.terminate()
            try:
                self.weather_station_process.wait(timeout=5)
                print("✅ Weather Station stopped")
            except subprocess.TimeoutExpired:
                print("⚠️  Weather Station didn't stop gracefully, forcing...")
                self.weather_station_process.kill()
        
        print("🔄 Shutting down Weather Interceptor...")
        if self.weather_interceptor_process:
            self.weather_interceptor_process.terminate()
            try:
                self.weather_interceptor_process.wait(timeout=5)
                print("✅ Weather Interceptor stopped")
            except subprocess.TimeoutExpired:
                print("⚠️  Weather Interceptor didn't stop gracefully, forcing...")
                self.weather_interceptor_process.kill()
        
        print("👋 All services stopped. Goodbye!")
    
    # Removed auto-restart monitor to avoid multiple instances and PID growth
    
    def run(self):
        """Main run method"""
        print("=" * 60)
        print("🌤️  WEATHER SYSTEM LAUNCHER")
        print("=" * 60)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🚀 Starting all weather services...")
        print("=" * 60)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Start Weather Station in a separate thread
            weather_station_thread = threading.Thread(target=self.start_weather_station, daemon=True)
            weather_station_thread.start()
            
            # Wait a moment for weather station to initialize
            time.sleep(3)
            
            # Start Weather Interceptor in a separate thread
            weather_interceptor_thread = threading.Thread(target=self.start_weather_interceptor, daemon=True)
            weather_interceptor_thread.start()
            
            print("✅ All services started successfully!")
            print("📋 System Status:")
            print(f"   - Weather Station: {'Running' if self.weather_station_process else 'Stopped'}")
            print(f"   - Weather Interceptor: {'Running' if self.weather_interceptor_process else 'Stopped'}")
            print("=" * 60)
            print("Press Ctrl+C to stop all services")
            print("=" * 60)
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        finally:
            self.shutdown()

def main():
    """Main entry point"""
    launcher = WeatherSystemLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
