#!/bin/bash
# Install MQTT Bridge as systemd service on Ubuntu VM
# Run this script as root on the VM

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================================================"
echo "  MQTT Bridge - Systemd Service Installer (Ubuntu VM)"
echo -e "========================================================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ ERROR: This script must be run as root${NC}"
    echo "Use: sudo bash install_mqtt_bridge_service_vm.sh"
    exit 1
fi

echo -e "${GREEN}✅ Running as root${NC}"
echo ""

# Define paths
SERVICE_NAME="mqtt-bridge"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(pwd)"
MQTT_BRIDGE_SCRIPT="${SCRIPT_DIR}/mqtt_to_influx_bridge_vm.py"

# Check if script exists
if [ ! -f "$MQTT_BRIDGE_SCRIPT" ]; then
    echo -e "${RED}❌ ERROR: MQTT bridge script not found: $MQTT_BRIDGE_SCRIPT${NC}"
    echo "Make sure you're running this from the correct directory"
    exit 1
fi

echo -e "${YELLOW}📋 Service Configuration:${NC}"
echo "   Service Name: $SERVICE_NAME"
echo "   Script: $MQTT_BRIDGE_SCRIPT"
echo "   Working Directory: $SCRIPT_DIR"
echo "   Python: $(which python3)"
echo ""

# Stop and disable existing service if present
if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${YELLOW}🔄 Stopping existing service...${NC}"
    systemctl stop $SERVICE_NAME
fi

if systemctl is-enabled --quiet $SERVICE_NAME 2>/dev/null; then
    echo -e "${YELLOW}🔄 Disabling existing service...${NC}"
    systemctl disable $SERVICE_NAME
fi

# Create systemd service file
echo -e "${YELLOW}📝 Creating systemd service file...${NC}"
cat > $SERVICE_FILE << EOF
[Unit]
Description=MQTT to InfluxDB Bridge Service
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $MQTT_BRIDGE_SCRIPT
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment="PYTHONUNBUFFERED=1"

# Resource limits
MemoryLimit=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Service file created: $SERVICE_FILE${NC}"
echo ""

# Reload systemd
echo -e "${YELLOW}🔄 Reloading systemd...${NC}"
systemctl daemon-reload

# Enable service
echo -e "${YELLOW}🔄 Enabling service...${NC}"
systemctl enable $SERVICE_NAME

# Start service
echo -e "${YELLOW}🚀 Starting service...${NC}"
systemctl start $SERVICE_NAME

# Wait a moment for service to start
sleep 2

# Check status
echo ""
echo -e "${CYAN}========================================================================${NC}"
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo -e "${CYAN}========================================================================${NC}"
echo ""

# Show status
echo -e "${YELLOW}📊 Service Status:${NC}"
systemctl status $SERVICE_NAME --no-pager -l

echo ""
echo -e "${YELLOW}💡 Service Control Commands:${NC}"
echo -e "   ${CYAN}Start:${NC}   sudo systemctl start $SERVICE_NAME"
echo -e "   ${CYAN}Stop:${NC}    sudo systemctl stop $SERVICE_NAME"
echo -e "   ${CYAN}Restart:${NC} sudo systemctl restart $SERVICE_NAME"
echo -e "   ${CYAN}Status:${NC}  sudo systemctl status $SERVICE_NAME"
echo -e "   ${CYAN}Logs:${NC}    sudo journalctl -u $SERVICE_NAME -f"
echo -e "   ${CYAN}Disable:${NC} sudo systemctl disable $SERVICE_NAME"
echo ""

echo -e "${GREEN}🎯 What happens now:${NC}"
echo "   ✅ Bridge is running in background"
echo "   ✅ Will start automatically on VM boot"
echo "   ✅ Will auto-restart if it crashes"
echo "   ✅ Logs available via journalctl"
echo ""

echo -e "${YELLOW}📝 View real-time logs:${NC}"
echo "   sudo journalctl -u $SERVICE_NAME -f"
echo ""

echo -e "${CYAN}========================================================================${NC}"
