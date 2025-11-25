#!/bin/bash
# Auto-start MQTT to InfluxDB Bridge on VM (Ubuntu)
# This script runs continuously and auto-restarts on failure

SCRIPT_DIR="/root/IOT/vm-automation"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo "  MQTT to InfluxDB Bridge - Auto-Start (VM)"
echo "========================================================================"
echo ""
echo "Starting bridge service..."
echo "MQTT Port: 1883"
echo "InfluxDB Port: 8086"
echo "Press Ctrl+C to stop"
echo ""

RESTART_DELAY=5

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting MQTT bridge..."
    
    python3 mqtt_to_influx_bridge_vm.py
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Bridge crashed (exit code: $EXIT_CODE)"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Bridge stopped normally"
    fi
    
    echo "Restarting in $RESTART_DELAY seconds..."
    sleep $RESTART_DELAY
done
