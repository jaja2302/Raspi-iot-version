#!/bin/bash
# Safe Weather Data Sniffer untuk Misol HP2550
# Menggunakan tcpdump tanpa mengubah sistem

echo "🌤️  Safe Weather Data Sniffer for Misol HP2550"
echo "=============================================="

# Check if tcpdump is installed
if ! command -v tcpdump &> /dev/null; then
    echo "Installing tcpdump..."
    sudo apt update
    sudo apt install -y tcpdump
fi

# Get current IP
CURRENT_IP=$(hostname -I | awk '{print $1}')
echo "Current IP: $CURRENT_IP"

# Create logs directory
mkdir -p logs

# Function to start sniffing
start_sniffing() {
    echo "🔍 Starting safe packet sniffing..."
    echo "Monitoring HTTP traffic for weather data..."
    echo "Press Ctrl+C to stop"
    echo ""
    
    # Sniff HTTP traffic on port 80 and 443
    sudo tcpdump -i any -A -s 0 'tcp port 80 or tcp port 443' | \
    while read line; do
        # Check if line contains weather parameters
        if echo "$line" | grep -q -E "(windspeedmph|tempf|humidity|dateutc|rainratein|winddir)="; then
            echo "🌤️  WEATHER DATA DETECTED!"
            echo "Time: $(date)"
            echo "Data: $line"
            echo "----------------------------------------"
            
            # Save to log file
            echo "$(date): $line" >> logs/weather_sniffed.log
        fi
    done
}

# Function to show sniffed data
show_data() {
    if [ -f "logs/weather_sniffed.log" ]; then
        echo "📊 Recent Sniffed Weather Data:"
        echo "==============================="
        tail -20 logs/weather_sniffed.log
    else
        echo "No sniffed data found yet"
    fi
}

# Function to clear logs
clear_logs() {
    if [ -f "logs/weather_sniffed.log" ]; then
        rm logs/weather_sniffed.log
        echo "Logs cleared"
    else
        echo "No logs to clear"
    fi
}

# Main menu
while true; do
    echo ""
    echo "Choose option:"
    echo "1. Start sniffing (safe mode)"
    echo "2. Show sniffed data"
    echo "3. Clear logs"
    echo "4. Exit"
    echo ""
    read -p "Enter choice (1-4): " choice
    
    case $choice in
        1)
            start_sniffing
            ;;
        2)
            show_data
            ;;
        3)
            clear_logs
            ;;
        4)
            echo "Goodbye! 👋"
            exit 0
            ;;
        *)
            echo "Invalid choice!"
            ;;
    esac
done
