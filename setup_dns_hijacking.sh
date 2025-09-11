#!/bin/bash
# DNS Hijacking Setup untuk Misol HP2550
# Redirect weather server ke Raspberry Pi lokal

echo "Setting up DNS hijacking for Misol HP2550..."

# Backup original hosts file
sudo cp /etc/hosts /etc/hosts.backup

# Get current IP
CURRENT_IP=$(hostname -I | awk '{print $1}')
echo "Current IP: $CURRENT_IP"

# Add DNS hijacking entries
echo "" | sudo tee -a /etc/hosts
echo "# Misol HP2550 DNS Hijacking" | sudo tee -a /etc/hosts
echo "# Redirect weather servers to local Raspberry Pi" | sudo tee -a /etc/hosts

# Wunderground servers
echo "$CURRENT_IP rtupdate.wunderground.com" | sudo tee -a /etc/hosts
echo "$CURRENT_IP weatherstation.wunderground.com" | sudo tee -a /etc/hosts

# WeatherCloud servers
echo "$CURRENT_IP api.weathercloud.net" | sudo tee -a /etc/hosts

# Ecowitt servers
echo "$CURRENT_IP ecowitt.net" | sudo tee -a /etc/hosts
echo "$CURRENT_IP api.ecowitt.net" | sudo tee -a /etc/hosts

# WOW (Weather Observations Website)
echo "$CURRENT_IP wow.metoffice.gov.uk" | sudo tee -a /etc/hosts

# Weather Underground API
echo "$CURRENT_IP api.wunderground.com" | sudo tee -a /etc/hosts

echo "DNS hijacking setup complete!"
echo "Misol HP2550 will now send data to your Raspberry Pi at $CURRENT_IP"
echo ""
echo "To revert changes, run:"
echo "sudo cp /etc/hosts.backup /etc/hosts"
