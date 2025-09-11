#!/bin/bash

# Complete Weather Station Installation Script
# This script will install everything needed including WiFi hotspot

echo "================================================"
echo "Complete Weather Station Installation for Misol"
echo "================================================"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root!"
    echo "Run as regular user: ./install_complete.sh"
    exit 1
fi

echo ""
echo "This script will:"
echo "1. Install Python dependencies with PM2"
echo "2. Setup WiFi Access Point (requires sudo)"
echo "3. Configure system for Misol HP2550"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 1
fi

# Step 1: Run PM2 installation
echo ""
echo "Step 1: Installing Weather Station with PM2..."
if [ -f "install_pm2.sh" ]; then
    chmod +x install_pm2.sh
    ./install_pm2.sh
    if [ $? -ne 0 ]; then
        echo "❌ PM2 installation failed!"
        exit 1
    fi
else
    echo "❌ install_pm2.sh not found!"
    exit 1
fi

# Step 2: Setup WiFi Hotspot
echo ""
echo "Step 2: Setting up WiFi Access Point..."
echo "⚠️  This requires sudo privileges"
if [ -f "setup_wifi_hotspot.sh" ]; then
    chmod +x setup_wifi_hotspot.sh
    sudo ./setup_wifi_hotspot.sh
    if [ $? -ne 0 ]; then
        echo "❌ WiFi hotspot setup failed!"
        exit 1
    fi
else
    echo "❌ setup_wifi_hotspot.sh not found!"
    exit 1
fi

# Step 3: Update firewall for access point
echo ""
echo "Step 3: Configuring firewall..."
sudo ufw allow 5000/tcp
sudo ufw allow 53/udp
sudo ufw allow 67/udp
echo "✅ Firewall configured"

# Step 4: Create service dependency to ensure proper startup order
echo ""
echo "Step 4: Creating service dependencies..."
sudo systemctl enable hostapd.service
sudo systemctl enable dnsmasq.service

# Step 5: Final configuration check
echo ""
echo "Step 5: Checking configuration..."
if [ -f "raspi_settings.json" ]; then
    echo "✅ Raspberry Pi settings found"
else
    echo "❌ Raspberry Pi settings not found"
fi

if pm2 list | grep -q "weather-station.*online"; then
    echo "✅ Weather Station service running"
else
    echo "❌ Weather Station service not running"
fi

# Get IP addresses
IP_ADDRESS=$(hostname -I | awk '{print $1}')
if [ -z "$IP_ADDRESS" ]; then
    IP_ADDRESS="localhost"
fi

echo ""
echo "================================================"
echo "✅ COMPLETE INSTALLATION FINISHED!"
echo "================================================"
echo ""
echo "🚨 IMPORTANT: REBOOT REQUIRED!"
echo "   sudo reboot"
echo ""
echo "After reboot, your Raspberry Pi will:"
echo "- Create WiFi hotspot: WeatherStation_Pi"
echo "- Run web server on: http://192.168.4.1:5000"
echo "- Accept data from Misol on: http://192.168.4.1:5000/post"
echo ""
echo "Misol HP2550 Configuration:"
echo "==========================="
echo "1. Power on your Misol HP2550"
echo "2. Access Misol web interface (usually http://192.168.1.X)"
echo "3. Go to WiFi settings:"
echo "   - SSID: WeatherStation_Pi"
echo "   - Password: weather123"
echo "4. Go to Upload settings:"
echo "   - Server: 192.168.4.1"
echo "   - Port: 5000"
echo "   - Path: /post"
echo "   - Full URL: http://192.168.4.1:5000/post"
echo "   - Protocol: HTTP POST"
echo "   - Format: Ecowitt (if available)"
echo ""
echo "Monitoring:"
echo "==========="
echo "PM2 Status:     pm2 status"
echo "PM2 Logs:       pm2 logs weather-station"
echo "WiFi Status:    sudo systemctl status hostapd"
echo "DHCP Status:    sudo systemctl status dnsmasq"
echo "Connected WiFi: sudo iwconfig"
echo ""
echo "Troubleshooting:"
echo "================"
echo "Web Interface:  http://$IP_ADDRESS:5000"
echo "Local Web:      http://192.168.4.1:5000 (from Misol perspective)"
echo "Check logs:     tail -f logs/weather_station_*.log"
echo ""
echo "⚠️  Don't forget to reboot: sudo reboot"
echo "================================================"
