#!/bin/bash

########################################
# IOT Dashboard Deployment on VM
# Deploy FastAPI Dashboard with Public Access
# VM IP: 142.93.220.152
########################################

set -e

echo "========================================"
echo "IOT Dashboard Deployment - Public Access"
echo "VM IP: 142.93.220.152"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "[1/8] Updating system..."
apt-get update -qq

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "[2/8] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "[2/8] Docker already installed ✓"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "[3/8] Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    echo "[3/8] Docker Compose already installed ✓"
fi

# Create deployment directory
DEPLOY_DIR="/opt/iot-dashboard"
echo "[4/8] Creating deployment directory: $DEPLOY_DIR"
mkdir -p $DEPLOY_DIR
mkdir -p $DEPLOY_DIR/models
mkdir -p $DEPLOY_DIR/static
mkdir -p $DEPLOY_DIR/services
mkdir -p $DEPLOY_DIR/influxdb-data
mkdir -p $DEPLOY_DIR/mqtt-data
mkdir -p $DEPLOY_DIR/mqtt-log

# Copy files (assumes script is run from deployment folder)
echo "[5/8] Setting up configuration files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy configs
cp "$SCRIPT_DIR/docker-compose-dashboard.yml" "$DEPLOY_DIR/docker-compose.yml" 2>/dev/null || echo "Note: Copy files manually"
cp "$SCRIPT_DIR/Dockerfile" "$DEPLOY_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/requirements.txt" "$DEPLOY_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/mosquitto.conf" "$DEPLOY_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/telegraf-vm.conf" "$DEPLOY_DIR/telegraf.conf" 2>/dev/null || true

echo "⚠️  IMPORTANT: You need to manually copy these from your PC:"
echo "   - FYP-Machine-Condition-Prediction/main.py"
echo "   - FYP-Machine-Condition-Prediction/services/ (entire folder)"
echo "   - FYP-Machine-Condition-Prediction/static/ (entire folder)"
echo "   - FYP-Machine-Condition-Prediction/.env"
echo "   - FYP-Machine-Condition-Prediction/FYP-Machine-Condition-Prediction/models/*.pkl (3 model files)"
echo ""
echo "Use: scp -r FYP-Machine-Condition-Prediction/* root@142.93.220.152:$DEPLOY_DIR/"
echo ""
read -p "Press Enter once you've copied the files..."

# Configure firewall
echo "[6/8] Configuring firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp      # HTTP for dashboard
    ufw allow 8000/tcp    # Alternative port
    ufw allow 1883/tcp    # MQTT
    ufw allow 8086/tcp    # InfluxDB
    ufw allow 9001/tcp    # MQTT WebSocket
    ufw allow 22/tcp      # SSH (keep open!)
    echo "y" | ufw enable
    echo "✓ Firewall configured"
else
    echo "⚠ UFW not found, configure firewall manually"
fi

# Navigate to deployment directory
cd $DEPLOY_DIR

# Start services
echo "[7/8] Starting Docker services..."
docker-compose down -v 2>/dev/null || true
docker-compose up -d --build

# Wait for services to start
echo "[8/8] Waiting for services to start..."
sleep 10

# Display status
echo ""
echo "========================================"
echo "Deployment Status"
echo "========================================"
docker-compose ps

echo ""
echo "========================================"
echo "Memory Usage"
echo "========================================"
docker stats --no-stream

echo ""
echo "========================================"
echo "✓ Dashboard deployment complete!"
echo "========================================"
echo ""
echo "Public Access URLs:"
echo "  http://142.93.220.152          (Dashboard - Port 80)"
echo "  http://142.93.220.152:8000     (Dashboard - Port 8000)"
echo "  http://142.93.220.152:8000/docs (API Documentation)"
echo ""
echo "API Endpoints:"
echo "  GET http://142.93.220.152:8000/workspaces"
echo "  GET http://142.93.220.152:8000/predict/{workspace_id}"
echo "  GET http://142.93.220.152:8000/inference/status"
echo ""
echo "Sensor Configuration:"
echo "  MQTT Host: 142.93.220.152"
echo "  MQTT Port: 1883"
echo "  Topic: machine_sensor_data"
echo ""
echo "Service Management:"
echo "  View logs:    docker-compose logs -f dashboard"
echo "  Restart:      docker-compose restart"
echo "  Stop:         docker-compose stop"
echo "  Remove:       docker-compose down -v"
echo ""
echo "Monitoring:"
echo "  Check health: curl http://localhost:8000/api"
echo "  Check InfluxDB: curl http://localhost:8086/health"
echo "  MQTT test: docker exec vm-mosquitto mosquitto_sub -t machine_sensor_data -v"
echo ""
echo "⚠️  Note: If dashboard shows 'No predictions available', wait for:"
echo "   1. Sensors to send data to MQTT"
echo "   2. Data to flow to InfluxDB"
echo "   3. Inference engine to run (60s cycles)"
echo ""
