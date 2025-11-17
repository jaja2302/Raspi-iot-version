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
        self.interceptor_log_thread = None
        
    def start_weather_station(self):
        """Start Weather Station Flask application"""
        try:
            print("🌐 Starting Weather Station...")
            
            if os.name == 'nt':
                # Windows: Open in new console window
                self.weather_station_process = subprocess.Popen(
                    [sys.executable, 'weather_station.py'],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                # Linux/Raspberry Pi: Try screen first, then tmux, then background
                if self._check_command('screen'):
                    # Use screen to create new terminal session
                    self.weather_station_process = subprocess.Popen([
                        'screen', '-dmS', 'weather_station', 
                        sys.executable, 'weather_station.py'
                    ])
                elif self._check_command('tmux'):
                    # Use tmux to create new terminal session
                    self.weather_station_process = subprocess.Popen([
                        'tmux', 'new-session', '-d', '-s', 'weather_station',
                        sys.executable, 'weather_station.py'
                    ])
                else:
                    # Fallback: run in background with nohup
                    self.weather_station_process = subprocess.Popen([
                        'nohup', sys.executable, 'weather_station.py'
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            print(f"✅ Weather Station started (PID: {self.weather_station_process.pid})")
            if os.name != 'nt':
                print("   - Use 'screen -r weather_station' to attach to Weather Station terminal")
                print("   - Or 'tmux attach -t weather_station' if using tmux")
            
        except Exception as e:
            print(f"❌ Error starting Weather Station: {e}")
    
    def start_weather_interceptor(self):
        """Start Weather Interceptor for network sniffing"""
        try:
            print("🌤️  Starting Weather Interceptor...")
            
            if os.name == 'nt':
                # Windows: Open in new console window
                self.weather_interceptor_process = subprocess.Popen(
                    [sys.executable, 'weather_interceptor.py'],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                # Linux/Raspberry Pi: Capture output and display in real-time
                # Create log file for backup
                os.makedirs('logs', exist_ok=True)
                log_file_path = 'logs/weather_interceptor.log'
                
                # Start process with captured output
                self.weather_interceptor_process = subprocess.Popen(
                    [sys.executable, 'weather_interceptor.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr to stdout
                    text=True,
                    bufsize=1,  # Line buffered
                    universal_newlines=True
                )
                
                # Start thread to read and display output in real-time
                self.interceptor_log_thread = threading.Thread(
                    target=self._read_subprocess_output_with_log,
                    args=(self.weather_interceptor_process, "[INTERCEPTOR]", log_file_path),
                    daemon=True
                )
                self.interceptor_log_thread.start()
            
            print(f"✅ Weather Interceptor started (PID: {self.weather_interceptor_process.pid})")
            if os.name != 'nt':
                print("   - Logs will be displayed here in real-time")
                print("   - Logs also saved to: logs/weather_interceptor.log")
            
        except Exception as e:
            print(f"❌ Error starting Weather Interceptor: {e}")
    
    def _read_subprocess_output_with_log(self, process, prefix, log_file_path):
        """Read subprocess output, display in real-time, and save to log file"""
        try:
            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                while self.running and process.poll() is None:
                    line = process.stdout.readline()
                    if line:
                        # Remove trailing newline
                        line_clean = line.rstrip('\n\r')
                        if line_clean:  # Only process non-empty lines
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            # Display in console
                            print(f"{timestamp} {prefix} {line_clean}")
                            sys.stdout.flush()  # Ensure immediate output
                            # Write to log file
                            log_file.write(f"{timestamp} {line}")
                            log_file.flush()
        except Exception as e:
            print(f"⚠️  Error reading interceptor output: {e}")
    
    def _check_command(self, command):
        """Check if a command is available on the system"""
        try:
            subprocess.run(['which', command], check=True, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
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
            if os.name == 'nt':
                # Windows: terminate process
                self.weather_station_process.terminate()
                try:
                    self.weather_station_process.wait(timeout=5)
                    print("✅ Weather Station stopped")
                except subprocess.TimeoutExpired:
                    print("⚠️  Weather Station didn't stop gracefully, forcing...")
                    self.weather_station_process.kill()
            else:
                # Linux: kill screen/tmux sessions or process
                try:
                    if self._check_command('screen'):
                        subprocess.run(['screen', '-S', 'weather_station', '-X', 'quit'], 
                                     check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif self._check_command('tmux'):
                        subprocess.run(['tmux', 'kill-session', '-t', 'weather_station'], 
                                     check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        self.weather_station_process.terminate()
                        self.weather_station_process.wait(timeout=5)
                    print("✅ Weather Station stopped")
                except Exception as e:
                    print(f"⚠️  Weather Station stop error: {e}")
                    if self.weather_station_process:
                        self.weather_station_process.kill()
        
        print("🔄 Shutting down Weather Interceptor...")
        if self.weather_interceptor_process:
            if os.name == 'nt':
                # Windows: terminate process
                self.weather_interceptor_process.terminate()
                try:
                    self.weather_interceptor_process.wait(timeout=5)
                    print("✅ Weather Interceptor stopped")
                except subprocess.TimeoutExpired:
                    print("⚠️  Weather Interceptor didn't stop gracefully, forcing...")
                    self.weather_interceptor_process.kill()
            else:
                # Linux: terminate process directly (no longer using screen/tmux)
                try:
                    self.weather_interceptor_process.terminate()
                    try:
                        self.weather_interceptor_process.wait(timeout=5)
                        print("✅ Weather Interceptor stopped")
                    except subprocess.TimeoutExpired:
                        print("⚠️  Weather Interceptor didn't stop gracefully, forcing...")
                        self.weather_interceptor_process.kill()
                except Exception as e:
                    print(f"⚠️  Weather Interceptor stop error: {e}")
                    if self.weather_interceptor_process:
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
