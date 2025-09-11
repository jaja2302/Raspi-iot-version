#!/bin/bash

# Weather Station Raspberry Pi - PM2 Uninstall Script

echo "=========================================="
echo "Weather Station PM2 Uninstall Script"
echo "=========================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root!"
    echo "Run as regular user: ./uninstall_pm2.sh"
    exit 1
fi

# Stop and delete PM2 process
echo ""
echo "Stopping and deleting PM2 process..."
if pm2 list | grep -q "weather-station"; then
    pm2 stop weather-station
    pm2 delete weather-station
    echo "✅ PM2 process stopped and deleted"
else
    echo "ℹ️  No PM2 process found"
fi

# Save PM2 configuration
echo "Saving PM2 configuration..."
pm2 save

# Remove PM2 from startup (optional)
echo ""
echo "Do you want to remove PM2 from startup? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    pm2 unstartup
    echo "✅ PM2 removed from startup"
else
    echo "ℹ️  PM2 startup configuration kept"
fi

# Remove PM2 globally (optional)
echo ""
echo "Do you want to remove PM2 completely? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    sudo npm uninstall -g pm2
    echo "✅ PM2 removed globally"
else
    echo "ℹ️  PM2 kept installed"
fi

# Remove Node.js (optional)
echo ""
echo "Do you want to remove Node.js and npm? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    sudo apt-get remove -y nodejs npm
    sudo apt-get purge -y nodejs npm
    echo "✅ Node.js and npm removed"
else
    echo "ℹ️  Node.js and npm kept installed"
fi

# Clean up PM2 logs
echo ""
echo "Cleaning up PM2 logs..."
rm -f logs/pm2-*.log
echo "✅ PM2 logs cleaned"

# Remove ecosystem config
echo ""
echo "Do you want to remove ecosystem.config.js? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    rm -f ecosystem.config.js
    echo "✅ ecosystem.config.js removed"
else
    echo "ℹ️  ecosystem.config.js kept"
fi

echo ""
echo "=========================================="
echo "✅ PM2 UNINSTALL COMPLETE!"
echo "=========================================="
echo ""
echo "Remaining files:"
echo "================"
echo "Application: weather_station.py"
echo "Data:        data/"
echo "Logs:        logs/weather_station.log"
echo "Settings:    data/settings.json"
echo "Database:    data/weather.db"
echo ""
echo "To reinstall with systemd: ./install.sh"
echo "To reinstall with PM2:     ./install_pm2.sh"
echo "=========================================="
