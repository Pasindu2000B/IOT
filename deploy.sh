#!/bin/bash
# =============================================================================
# IOT Predictive Maintenance System - Deployment Script
# =============================================================================

set -e  # Exit on error

echo "==============================================="
echo "  IOT Predictive Maintenance System Setup"
echo "==============================================="
echo ""

# Step 1: Start Docker containers
echo "📦 Step 1: Starting Docker containers..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start (30 seconds)..."
sleep 30

# Step 2: Check service health
echo ""
echo "🔍 Step 2: Checking service health..."
docker-compose ps

# Step 3: Setup Spark workers with Python dependencies
echo ""
echo "📚 Step 3: Installing Python dependencies on Spark workers..."
echo "   This may take 2-3 minutes..."

docker exec -u root spark-master bash -c "pip install --quiet numpy pandas influxdb-client torch torchvision --index-url https://download.pytorch.org/whl/cpu" &
PID1=$!

docker exec -u root spark-worker-1 bash -c "pip install --quiet numpy pandas influxdb-client torch torchvision --index-url https://download.pytorch.org/whl/cpu" &
PID2=$!

docker exec -u root spark-worker-2 bash -c "pip install --quiet numpy pandas influxdb-client torch torchvision --index-url https://download.pytorch.org/whl/cpu" &
PID3=$!

# Wait for all installations to complete
wait $PID1
wait $PID2
wait $PID3

echo "   ✅ All dependencies installed!"

# Step 4: Start data generation
echo ""
echo "📊 Step 4: Starting sensor data generation..."
nohup python3 GenerateData.py > logs/generate_data.log 2>&1 &
echo $! > logs/generate_data.pid
echo "   ✅ Data generator started (PID: $(cat logs/generate_data.pid))"

# Step 5: Start MQTT to InfluxDB bridge
echo ""
echo "🌉 Step 5: Starting MQTT to InfluxDB bridge..."
chmod +x start_bridge.sh
./start_bridge.sh

# Step 6: Wait for data collection
echo ""
echo "⏳ Step 6: Collecting initial data (2 minutes)..."
echo "   This allows the system to gather training data..."
sleep 120

# Step 7: Run initial distributed training
echo ""
echo "🎯 Step 7: Running initial distributed model training..."
docker exec spark-master bash -c "/opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --executor-memory 1g \
  --total-executor-cores 4 \
  --conf spark.executor.cores=2 \
  --conf spark.task.cpus=1 \
  --conf spark.python.worker.reuse=true \
  /opt/spark-apps/train_distributed.py"

# Step 8: Display summary
echo ""
echo "==============================================="
echo "  ✅ System Successfully Deployed!"
echo "==============================================="
echo ""
echo "📊 Service URLs:"
echo "   • Spark Master UI:  http://localhost:8080"
echo "   • InfluxDB UI:      http://localhost:8086"
echo "   • MQTT Broker:      localhost:1883"
echo ""
echo "📁 Important Directories:"
echo "   • Models:           ./spark-apps/models/"
echo "   • Logs:             ./logs/"
echo ""
echo "🔧 Useful Commands:"
echo "   • View logs:        tail -f logs/bridge.log"
echo "   • Check status:     ./status.sh"
echo "   • Stop system:      ./stop.sh"
echo "   • Retrain models:   ./retrain.sh"
echo ""
echo "📝 Training Summary:"
docker exec spark-master ls -lh /opt/spark-apps/models/ | grep "^-" | tail -6
echo ""
echo "==============================================="
