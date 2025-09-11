#!/bin/bash

# Weather Station Raspberry Pi - Manual Run Script

echo "Starting Weather Station manually..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found!"
    echo "Please run ./install.sh first"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Create necessary directories
mkdir -p data logs templates static/css static/js
chmod 755 data logs templates static

# Get Raspberry Pi IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')
if [ -z "$IP_ADDRESS" ]; then
    IP_ADDRESS="localhost"
fi

# Run the application
echo ""
echo "=========================================="
echo "Weather Station Starting..."
echo "=========================================="
echo "Web interface: http://$IP_ADDRESS:5000"
echo "API endpoint:  http://$IP_ADDRESS:5000/post"
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

python3 weather_station.py
