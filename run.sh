#!/bin/bash

# Weather Station Raspberry Pi - Run Script

echo "Starting Weather Station..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/pyvenv.cfg" ] || [ requirements.txt -nt venv/pyvenv.cfg ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Create necessary directories
mkdir -p data logs

# Set permissions
chmod 755 data logs

# Run the application
echo "Starting Weather Station application..."
echo "Web interface will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop"

python3 weather_station.py
