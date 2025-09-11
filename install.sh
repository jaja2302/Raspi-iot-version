#!/bin/bash

# Weather Station Raspberry Pi - Installation Script
# This script will install and setup the weather station as a systemd service

echo "=========================================="
echo "Weather Station Installation Script"
echo "=========================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root!"
    echo "Run as regular user: ./install.sh"
    exit 1
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Installing Python 3..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Installing pip..."
    sudo apt install -y python3-pip
fi

echo "✅ Python 3 and pip are available"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data logs templates static/css static/js
chmod 755 data logs templates static
echo "✅ Directories created"

# Create systemd service file
echo ""
echo "Creating systemd service file..."
cat > weather_station.service << EOF
[Unit]
Description=Weather Station Raspberry Pi Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/weather_station.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment variables
Environment=PATH=$SCRIPT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created"

# Copy service file to systemd directory
echo ""
echo "Installing systemd service..."
sudo cp weather_station.service /etc/systemd/system/

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
echo "Enabling Weather Station service (auto-start on boot)..."
sudo systemctl enable weather_station.service

# Start the service
echo ""
echo "Starting Weather Station service..."
sudo systemctl start weather_station.service

# Wait a moment for service to start
sleep 3

# Check service status
echo ""
echo "Checking service status..."
if sudo systemctl is-active --quiet weather_station.service; then
    echo "✅ Weather Station service is running!"
else
    echo "❌ Weather Station service failed to start"
    echo "Check logs with: journalctl -u weather_station -f"
    exit 1
fi

# Get Raspberry Pi IP address
echo ""
echo "Getting Raspberry Pi IP address..."
IP_ADDRESS=$(hostname -I | awk '{print $1}')
if [ -z "$IP_ADDRESS" ]; then
    IP_ADDRESS="localhost"
fi

echo ""
echo "=========================================="
echo "✅ INSTALLATION COMPLETE!"
echo "=========================================="
echo ""
echo "Service Status:"
echo "==============="
echo "Start:    sudo systemctl start weather_station"
echo "Stop:     sudo systemctl stop weather_station"
echo "Restart:  sudo systemctl restart weather_station"
echo "Status:   sudo systemctl status weather_station"
echo "Logs:     journalctl -u weather_station -f"
echo ""
echo "Web Interface:"
echo "=============="
echo "Local:    http://localhost:5000"
echo "Network:  http://$IP_ADDRESS:5000"
echo ""
echo "API Endpoints:"
echo "=============="
echo "POST:     http://$IP_ADDRESS:5000/post"
echo "JSON:     http://$IP_ADDRESS:5000/api/weather"
echo ""
echo "Configuration:"
echo "=============="
echo "Settings: data/settings.json"
echo "Database: data/weather.db"
echo "Logs:     logs/weather_station.log"
echo ""
echo "To uninstall: ./uninstall.sh"
echo "=========================================="
