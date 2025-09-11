#!/bin/bash

# Weather Station Raspberry Pi - Uninstallation Script
# This script will remove the weather station systemd service

echo "=========================================="
echo "Weather Station Uninstallation Script"
echo "=========================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root!"
    echo "Run as regular user: ./uninstall.sh"
    exit 1
fi

# Stop the service if running
echo "Stopping Weather Station service..."
if sudo systemctl is-active --quiet weather_station.service; then
    sudo systemctl stop weather_station.service
    echo "✅ Service stopped"
else
    echo "ℹ️  Service was not running"
fi

# Disable the service
echo "Disabling Weather Station service..."
sudo systemctl disable weather_station.service
echo "✅ Service disabled"

# Remove service file
echo "Removing systemd service file..."
if [ -f "/etc/systemd/system/weather_station.service" ]; then
    sudo rm /etc/systemd/system/weather_station.service
    echo "✅ Service file removed"
else
    echo "ℹ️  Service file not found"
fi

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "✅ Systemd daemon reloaded"

# Kill any remaining processes
echo "Checking for remaining processes..."
if pgrep -f "weather_station.py" > /dev/null; then
    echo "Killing remaining weather station processes..."
    pkill -f "weather_station.py"
    sleep 2
    echo "✅ Processes killed"
else
    echo "ℹ️  No remaining processes found"
fi

# Ask if user wants to keep data
echo ""
echo "Data Cleanup Options:"
echo "===================="
echo "1. Keep all data (database, logs, settings)"
echo "2. Remove logs only"
echo "3. Remove everything (WARNING: This will delete all data!)"
echo ""
read -p "Choose option (1-3): " choice

case $choice in
    1)
        echo "✅ Keeping all data files"
        ;;
    2)
        echo "Removing log files..."
        rm -rf logs/*
        echo "✅ Log files removed"
        ;;
    3)
        echo "⚠️  WARNING: Removing all data files..."
        read -p "Are you sure? Type 'yes' to confirm: " confirm
        if [ "$confirm" = "yes" ]; then
            rm -rf data logs
            echo "✅ All data files removed"
        else
            echo "ℹ️  Data files kept"
        fi
        ;;
    *)
        echo "ℹ️  Invalid choice, keeping all data"
        ;;
esac

# Ask if user wants to remove virtual environment
echo ""
read -p "Remove virtual environment? (y/N): " remove_venv
if [[ $remove_venv =~ ^[Yy]$ ]]; then
    rm -rf venv
    echo "✅ Virtual environment removed"
else
    echo "ℹ️  Virtual environment kept"
fi

# Remove local service file
if [ -f "weather_station.service" ]; then
    rm weather_station.service
    echo "✅ Local service file removed"
fi

echo ""
echo "=========================================="
echo "✅ UNINSTALLATION COMPLETE!"
echo "=========================================="
echo ""
echo "What was removed:"
echo "================="
echo "✅ systemd service (weather_station.service)"
echo "✅ service auto-start on boot"
echo "✅ running processes"
echo ""
echo "What was kept (unless you chose to remove):"
echo "==========================================="
echo "📁 data/ directory (database, settings)"
echo "📁 logs/ directory (unless removed)"
echo "📁 venv/ directory (unless removed)"
echo "📄 Python files (weather_station.py, etc.)"
echo ""
echo "To reinstall: ./install.sh"
echo "=========================================="
