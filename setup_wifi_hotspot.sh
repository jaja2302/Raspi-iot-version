#!/bin/bash

# WiFi Hotspot Setup for Raspberry Pi Weather Station
# This script sets up the Raspberry Pi as a WiFi access point for Misol weather station

echo "Setting up WiFi Hotspot for Weather Station..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Install required packages
echo "Installing required packages..."
apt update
apt install -y hostapd dnsmasq iptables-persistent

# Stop services
systemctl stop hostapd
systemctl stop dnsmasq

# Detect available WiFi interfaces
echo "Detecting WiFi interfaces..."
WIFI_INTERFACES=$(iw dev | grep Interface | awk '{print $2}')
WIFI_COUNT=$(echo "$WIFI_INTERFACES" | wc -l)

echo "Found $WIFI_COUNT WiFi interface(s): $WIFI_INTERFACES"

if [ "$WIFI_COUNT" -eq 1 ]; then
    WIFI_CLIENT=$(echo "$WIFI_INTERFACES" | head -n1)
    WIFI_AP=$WIFI_CLIENT
    echo "⚠️  Single WiFi adapter detected: $WIFI_CLIENT"
    echo "⚠️  This will disconnect from current WiFi and create hotspot"
    echo "⚠️  Internet access will be lost unless you have Ethernet connection"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
elif [ "$WIFI_COUNT" -ge 2 ]; then
    WIFI_CLIENT=$(echo "$WIFI_INTERFACES" | head -n1)
    WIFI_AP=$(echo "$WIFI_INTERFACES" | tail -n1)
    echo "✅ Dual WiFi detected: Client=$WIFI_CLIENT, AP=$WIFI_AP"
else
    echo "❌ No WiFi interfaces found!"
    exit 1
fi

# Configure dhcpcd
echo "Configuring network interface for $WIFI_AP..."
cat >> /etc/dhcpcd.conf << EOF

# Weather Station WiFi Hotspot
interface $WIFI_AP
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOF

# Configure hostapd
echo "Configuring WiFi access point..."
cat > /etc/hostapd/hostapd.conf << EOF
interface=wlan0
driver=nl80211
ssid=WeatherStation_Pi
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=weather123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# Set hostapd config path
echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' >> /etc/default/hostapd

# Configure dnsmasq
echo "Configuring DHCP server..."
mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
cat > /etc/dnsmasq.conf << EOF
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h

# DNS hijacking for Misol weather services
# Redirect all weather service URLs to local Raspberry Pi
address=/www.ecowitt.net/192.168.4.1
address=/ecowitt.net/192.168.4.1
address=/www.wunderground.com/192.168.4.1
address=/wunderground.com/192.168.4.1
address=/www.weathercloud.net/192.168.4.1
address=/weathercloud.net/192.168.4.1
address=/www.weatherobservationswebsite.com/192.168.4.1
address=/weatherobservationswebsite.com/192.168.4.1

# Default DNS for other requests
server=8.8.8.8
server=1.1.1.1
EOF

# Configure IP forwarding
echo "Enabling IP forwarding..."
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf

# Configure iptables for internet sharing (if eth0 has internet)
echo "Setting up internet sharing..."
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT

# Save iptables rules
sh -c "iptables-save > /etc/iptables.ipv4.nat"

# Load iptables rules on boot
cat > /etc/rc.local << EOF
#!/bin/sh -e
iptables-restore < /etc/iptables.ipv4.nat
exit 0
EOF
chmod +x /etc/rc.local

# Enable services
systemctl enable hostapd
systemctl enable dnsmasq

# Create service to restore iptables on boot
cat > /etc/systemd/system/weather-station-network.service << EOF
[Unit]
Description=Weather Station Network Setup
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/iptables-restore /etc/iptables.ipv4.nat
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl enable weather-station-network

echo "WiFi Hotspot setup completed!"
echo ""
echo "WiFi Details:"
echo "SSID: WeatherStation_Pi"
echo "Password: weather123"
echo "IP Range: 192.168.4.1 - 192.168.4.20"
echo "Gateway: 192.168.4.1"
echo ""
echo "Please reboot to activate: sudo reboot"
echo ""
echo "To connect Misol weather station:"
echo "1. Connect Misol to WiFi: WeatherStation_Pi"
echo "2. Set Misol POST URL to: http://192.168.4.1:5000/post"
