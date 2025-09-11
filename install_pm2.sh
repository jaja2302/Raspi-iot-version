#!/bin/bash

# Weather Station Raspberry Pi - PM2 Installation Script
# This script will install PM2 and setup the weather station with PM2

echo "=========================================="
echo "Weather Station PM2 Installation Script"
echo "=========================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root!"
    echo "Run as regular user: ./install_pm2.sh"
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

# Install Node.js and npm (required for PM2)
echo ""
echo "Installing Node.js and npm..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo "✅ Node.js installed"
else
    echo "✅ Node.js already installed"
fi

# Install PM2 globally
echo ""
echo "Installing PM2..."
if ! command -v pm2 &> /dev/null; then
    sudo npm install -g pm2
    echo "✅ PM2 installed"
else
    echo "✅ PM2 already installed"
fi

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

# Update ecosystem.config.js with correct path
echo ""
echo "Updating PM2 configuration..."
sed -i "s|/home/pi/Raspi-iot-version|$SCRIPT_DIR|g" ecosystem.config.js
echo "✅ PM2 configuration updated"

# Stop existing systemd service if running
echo ""
echo "Stopping existing systemd service..."
if sudo systemctl is-active --quiet weather_station.service; then
    sudo systemctl stop weather_station.service
    sudo systemctl disable weather_station.service
    echo "✅ Systemd service stopped and disabled"
else
    echo "ℹ️  No systemd service running"
fi

# Start with PM2
echo ""
echo "Starting Weather Station with PM2..."
pm2 start ecosystem.config.js

# Save PM2 configuration
echo "Saving PM2 configuration..."
pm2 save

# Setup PM2 startup script
echo "Setting up PM2 startup script..."
pm2 startup
echo "⚠️  Please run the command shown above to enable PM2 auto-start on boot"

# Wait a moment for service to start
sleep 3

# Check PM2 status
echo ""
echo "Checking PM2 status..."
if pm2 list | grep -q "weather-station.*online"; then
    echo "✅ Weather Station is running with PM2!"
else
    echo "❌ Weather Station failed to start with PM2"
    echo "Check logs with: pm2 logs weather-station"
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
echo "✅ PM2 INSTALLATION COMPLETE!"
echo "=========================================="
echo ""
echo "PM2 Commands:"
echo "============="
echo "Start:    pm2 start weather-station"
echo "Stop:     pm2 stop weather-station"
echo "Restart:  pm2 restart weather-station"
echo "Status:   pm2 status"
echo "Logs:     pm2 logs weather-station"
echo "Monitor:  pm2 monit"
echo "Delete:   pm2 delete weather-station"
echo ""
echo "Log Files:"
echo "=========="
echo "Combined: logs/pm2-combined.log"
echo "Output:   logs/pm2-out.log"
echo "Error:    logs/pm2-error.log"
echo "App Log:  logs/weather_station.log"
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
echo "PM2 Config: ecosystem.config.js"
echo ""
echo "To uninstall PM2: ./uninstall_pm2.sh"
echo "=========================================="
