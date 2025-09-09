#!/bin/bash

# Weather Station Raspberry Pi Installation Script
echo "Installing Weather Station on Raspberry Pi..."

# Update system
sudo apt update
sudo apt upgrade -y

# Install Python3 and pip if not already installed
sudo apt install -y python3 python3-pip python3-venv

# Install system dependencies
sudo apt install -y sqlite3

# Create project directory
sudo mkdir -p /home/pi/weather-station
sudo chown pi:pi /home/pi/weather-station

# Copy files to project directory
cp -r * /home/pi/weather-station/

# Create virtual environment
cd /home/pi/weather-station
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p data logs

# Set permissions
chmod +x weather_station.py
chmod 755 data logs

# Copy systemd service file
sudo cp weather_station.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable weather_station.service

echo "Installation completed!"
echo "To start the service: sudo systemctl start weather_station.service"
echo "To check status: sudo systemctl status weather_station.service"
echo "To view logs: journalctl -u weather_station.service -f"
echo "Web interface will be available at: http://localhost:5000"
