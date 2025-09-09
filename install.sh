#!/bin/bash

# Weather Station Raspberry Pi Installation Script
echo "Installing Weather Station on Raspberry Pi..."

# Get the current directory (where the script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

echo "Installing from directory: $PROJECT_DIR"

# Check if we're in the right directory
if [ ! -f "weather_station.py" ]; then
    echo "Error: weather_station.py not found in current directory"
    echo "Please run this script from the project directory"
    exit 1
fi

# # Update system
# sudo apt update
# sudo apt upgrade -y

# Install Python3 and pip if not already installed
echo "Installing Python dependencies..."
sudo apt install -y python3 python3-pip python3-venv

# Install system dependencies
sudo apt install -y sqlite3

# Change to project directory
cd "$PROJECT_DIR"

# Create virtual environment in current directory
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python packages..."
pip install -r requirements.txt

# Create necessary directories if they don't exist
echo "Creating necessary directories..."
mkdir -p data logs

# Set permissions
chmod +x weather_station.py
chmod 755 data logs

# Create systemd service file with correct paths
echo "Setting up systemd service..."
sudo tee /etc/systemd/system/weather_station.service > /dev/null <<EOF
[Unit]
Description=Weather Station Raspberry Pi Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/weather_station.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable weather_station.service

echo ""
echo "Installation completed!"
echo "Project installed in: $PROJECT_DIR"
echo ""
echo "To start the service: sudo systemctl start weather_station.service"
echo "To check status: sudo systemctl status weather_station.service"
echo "To view logs: journalctl -u weather_station.service -f"
echo "Web interface will be available at: http://localhost:5000"
