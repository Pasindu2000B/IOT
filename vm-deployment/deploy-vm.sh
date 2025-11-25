#!/bin/bash
# VM Deployment Script for IOT System
# Deploys minimal services to receive sensor data

echo "========================================"
echo "IOT VM Deployment - Sensor Data Receiver"
echo "VM IP: 142.93.220.152"
echo "========================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# Update system
echo ""
echo "[1/7] Updating system..."
apt-get update -qq

# Install Docker
echo ""
echo "[2/7] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "  Docker installed"
else
    echo "  Docker already installed"
fi

# Install Docker Compose
echo ""
echo "[3/7] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "  Docker Compose installed"
else
    echo "  Docker Compose already installed"
fi

# Create deployment directory
echo ""
echo "[4/7] Creating deployment directory..."
mkdir -p /opt/iot-vm
cd /opt/iot-vm

# Copy configuration files (assume they're in current directory)
echo ""
echo "[5/7] Setting up configuration files..."
if [ -f "./docker-compose-vm.yml" ]; then
    cp docker-compose-vm.yml /opt/iot-vm/
    cp mosquitto.conf /opt/iot-vm/
    cp telegraf.conf /opt/iot-vm/
    echo "  Configuration files copied"
else
    echo "  ERROR: Configuration files not found"
    echo "  Please upload docker-compose-vm.yml, mosquitto.conf, telegraf.conf"
    exit 1
fi

# Configure firewall
echo ""
echo "[6/7] Configuring firewall..."
ufw allow 1883/tcp comment 'MQTT'
ufw allow 8086/tcp comment 'InfluxDB'
ufw allow 9001/tcp comment 'MQTT WebSocket'
echo "  Firewall rules added"

# Start services
echo ""
echo "[7/7] Starting Docker services..."
docker-compose -f docker-compose-vm.yml up -d

# Wait for services to start
sleep 10

# Check status
echo ""
echo "========================================"
echo "Deployment Status"
echo "========================================"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "========================================"
echo "Service URLs"
echo "========================================"
echo "MQTT Broker:  142.93.220.152:1883"
echo "InfluxDB:     http://142.93.220.152:8086"
echo "WebSocket:    ws://142.93.220.152:9001"

echo ""
echo "========================================"
echo "Memory Usage"
echo "========================================"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}"

echo ""
echo "========================================"
echo "Next Steps"
echo "========================================"
echo "1. Update telegraf.conf with your PC's IP address"
echo "2. Configure sensors to send data to 142.93.220.152:1883"
echo "3. Test MQTT connection:"
echo "   mosquitto_pub -h 142.93.220.152 -t test -m 'hello'"
echo "4. Check InfluxDB: http://142.93.220.152:8086"
echo ""
echo "To restart services:"
echo "  cd /opt/iot-vm && docker-compose -f docker-compose-vm.yml restart"
echo ""
echo "To view logs:"
echo "  docker logs vm-mosquitto"
echo "  docker logs vm-influxdb"
echo ""
