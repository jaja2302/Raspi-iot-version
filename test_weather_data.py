#!/usr/bin/env python3
"""
Test script to send sample weather data to the weather station
This simulates data from an ESP32 weather station
"""

import requests
import json
import time
from datetime import datetime, timedelta

def send_test_data():
    """Send test weather data to the weather station"""
    
    # Base URL for the weather station
    base_url = "http://localhost:5000"
    
    # Sample weather data (simulating MISOL weather station data)
    test_data = {
        "dateutc": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tempf": "75.2",           # Outdoor temperature in Fahrenheit
        "tempinf": "72.1",         # Indoor temperature in Fahrenheit
        "windspeedmph": "8.5",     # Wind speed in mph
        "windgustmph": "12.3",     # Wind gust in mph
        "winddir": "180",          # Wind direction in degrees
        "rainratein": "0.0",       # Rain rate in inches per hour
        "humidity": "65",          # Outdoor humidity %
        "humidityin": "60",        # Indoor humidity %
        "uv": "5.2",               # UV index
        "baromrelin": "29.92",     # Relative barometric pressure
        "baromabsin": "29.89",     # Absolute barometric pressure
        "solarradiation": "450",   # Solar radiation W/m²
        "dailyrainin": "0.0",      # Daily rain in inches
        "raintodayin": "0.0",      # Rain today in inches
        "totalrainin": "0.0",      # Total rain in inches
        "weeklyrainin": "0.0",     # Weekly rain in inches
        "monthlyrainin": "0.0",    # Monthly rain in inches
        "yearlyrainin": "0.0",     # Yearly rain in inches
        "maxdailygust": "15.2",    # Max daily gust
        "wh65batt": "3.2"          # Battery voltage
    }
    
    try:
        # Send data using the /post endpoint (form data)
        print(f"Sending test data to {base_url}/post...")
        response = requests.post(f"{base_url}/post", data=test_data)
        
        if response.status_code == 200:
            print("✅ Data sent successfully!")
            print(f"Response: {response.text}")
        else:
            print(f"❌ Error sending data: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the weather station is running on localhost:5000")
    except Exception as e:
        print(f"❌ Error: {e}")

def send_json_data():
    """Send test weather data in JSON format"""
    
    base_url = "http://localhost:5000"
    
    # Sample JSON data
    json_data = {
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "windspeed_kmh": 13.7,
        "wind_direction": 180,
        "rain_rate_in": 0.0,
        "temp_in_c": 22.3,
        "temp_out_c": 24.0,
        "humidity_in": 60,
        "humidity_out": 65,
        "uv_index": 5.2,
        "wind_gust_kmh": 19.8,
        "barometric_pressure_rel_in": 29.92,
        "barometric_pressure_abs_in": 29.89,
        "solar_radiation_wm2": 450,
        "daily_rain_in": 0.0,
        "rain_today_in": 0.0,
        "total_rain_in": 0.0,
        "weekly_rain_in": 0.0,
        "monthly_rain_in": 0.0,
        "yearly_rain_in": 0.0,
        "max_daily_gust": 24.5,
        "wh65_batt": 3.2
    }
    
    try:
        print(f"Sending JSON data to {base_url}/api/weather...")
        response = requests.post(
            f"{base_url}/api/weather", 
            json=json_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            print("✅ JSON data sent successfully!")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Error sending JSON data: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the weather station is running on localhost:5000")
    except Exception as e:
        print(f"❌ Error: {e}")

def get_latest_data():
    """Get the latest weather data from the API"""
    
    base_url = "http://localhost:5000"
    
    try:
        print(f"Getting latest data from {base_url}/api/weather/latest...")
        response = requests.get(f"{base_url}/api/weather/latest")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Latest weather data:")
            print(json.dumps(data, indent=2))
        elif response.status_code == 404:
            print("ℹ️ No weather data available yet")
        else:
            print(f"❌ Error getting data: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the weather station is running on localhost:5000")
    except Exception as e:
        print(f"❌ Error: {e}")

def continuous_test(interval=10):
    """Send test data continuously"""
    print(f"Starting continuous test (every {interval} seconds)")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            print(f"\n--- Test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
            send_test_data()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "form":
            send_test_data()
        elif command == "json":
            send_json_data()
        elif command == "get":
            get_latest_data()
        elif command == "continuous":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            continuous_test(interval)
        else:
            print("Usage: python3 test_weather_data.py [form|json|get|continuous] [interval]")
    else:
        print("Weather Station Test Script")
        print("==========================")
        print("1. Send form data (simulating ESP32)")
        print("2. Send JSON data")
        print("3. Get latest data")
        print("4. Continuous test")
        print()
        
        choice = input("Select option (1-4): ")
        
        if choice == "1":
            send_test_data()
        elif choice == "2":
            send_json_data()
        elif choice == "3":
            get_latest_data()
        elif choice == "4":
            interval = input("Enter interval in seconds (default 10): ")
            interval = int(interval) if interval else 10
            continuous_test(interval)
        else:
            print("Invalid choice")
