# Server Deployment Guide

## 🚀 Deploy on New Linux Server

### Prerequisites

Install Docker, Git, and Python on your Linux server:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose git python3 python3-pip
sudo systemctl start docker
sudo systemctl enable docker
```

### Quick Deployment (4 Steps)

#### Step 1: Clone Repository
```bash
git clone https://github.com/Pasindu2000B/IOT.git
cd IOT
```

#### Step 2: Make Scripts Executable
```bash
chmod +x *.sh
```

#### Step 3: Deploy System
```bash
./deploy.sh
```

**Deployment Time:** 5-7 minutes (fully automated)

#### Step 4: Verify Deployment
```bash
./status.sh
```

---

## ✅ What Gets Deployed

The deployment script automatically:

1. **Starts Docker containers**
   - MQTT Broker (Mosquitto)
   - InfluxDB Database
   - Spark Cluster (1 Master + 2 Workers)
   - Training Scheduler

2. **Installs Python dependencies**
   - NumPy, Pandas
   - InfluxDB Client
   - PyTorch (CPU version)

3. **Starts data collection**
   - Data generator (3 workspaces)
   - MQTT → InfluxDB bridge (auto-reconnecting)

4. **Collects initial data**
   - Waits 2 minutes for data gathering

5. **Trains initial models**
   - Uses Spark distributed training
   - Creates one model per workspace

---

## 🌐 Access Services

After deployment, access these URLs:

- **Spark Master UI**: `http://YOUR_SERVER_IP:8080`
- **InfluxDB Dashboard**: `http://YOUR_SERVER_IP:8086`
  - Username: `Pasindu Bimsara`
  - Password: `abcdefgh`
- **MQTT Broker**: `YOUR_SERVER_IP:1883`
  - Username: `test`
  - Password: `test`

### Allow External Access (Optional)

Open firewall ports if you want external access:

```bash
sudo ufw allow 8080/tcp  # Spark UI
sudo ufw allow 8086/tcp  # InfluxDB
sudo ufw allow 1883/tcp  # MQTT Broker
sudo ufw enable
```

---

## 🔧 Management Commands

### Check System Status
```bash
./status.sh
```

Shows:
- Docker container status
- Python process status (bridge, data generator)
- Recent trained models
- System health

### View Logs

```bash
# View bridge logs (real-time)
tail -f logs/bridge.log

# View Docker container logs
docker-compose logs

# View specific container logs
docker logs mosquitto
docker logs influxdb
docker logs spark-master
```

### Manual Model Retraining

```bash
./retrain.sh
```

Triggers immediate model retraining across all workspaces using Spark distributed system.

### Stop System

```bash
./stop.sh
```

Stops all services:
- Python processes (bridge, data generator)
- Docker containers

### Restart Bridge

If the bridge stops (rare due to auto-reconnect):

```bash
./stop_bridge.sh
./start_bridge.sh
```

---

## 🤖 Automated Operations

### Continuous (Always Running)
- **Data generation**: Every 2 seconds per workspace
- **MQTT bridge**: Real-time data forwarding
- **Spark cluster**: Ready for training requests
- **Auto-reconnection**: Bridge automatically recovers from failures

### Monthly (1st of Month at Midnight)
- **Model retraining**: Automatic distributed training
- **Workspace discovery**: Detects new devices
- **Model updates**: All workspace models refreshed

---

## 📁 Important Directories

```
IOT/
├── logs/                     # System logs
│   ├── bridge.log           # MQTT bridge logs
│   └── generate_data.log    # Data generator logs
├── spark-apps/
│   ├── models/              # Trained ML models
│   └── logs/                # Training logs
├── mqtt-broker/
│   └── log/                 # MQTT broker logs
└── influxdb/
    └── data/                # Time-series data
```

---

## 🔍 Monitoring

### Check Data Flow

```bash
# Count messages in last hour
docker exec influxdb influx query '
from(bucket:"New_Sensor")
  |> range(start:-1h)
  |> filter(fn:(r) => r._measurement == "sensor_data")
  |> count()
'
```

### Check Bridge Status

```bash
# View recent bridge activity
tail -n 50 logs/bridge.log

# Check if bridge is running
ps aux | grep mqtt_to_influx_bridge
```

### Check Trained Models

```bash
# List all models
ls -lh spark-apps/models/

# Count models per workspace
ls spark-apps/models/ | grep "model_" | cut -d'_' -f2 | sort | uniq -c
```

---

## 🛠️ Troubleshooting

### Problem: Docker containers not starting

```bash
# Check Docker service
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# Try deployment again
./deploy.sh
```

### Problem: Bridge not connecting to MQTT

```bash
# Check MQTT broker
docker logs mosquitto

# Check bridge logs
tail -f logs/bridge.log

# Restart bridge
./stop_bridge.sh && ./start_bridge.sh
```

### Problem: No data in InfluxDB

1. Check data generator:
   ```bash
   ps aux | grep GenerateData
   tail -f logs/generate_data.log
   ```

2. Check MQTT broker:
   ```bash
   docker logs mosquitto
   ```

3. Check bridge:
   ```bash
   tail -f logs/bridge.log
   ```

### Problem: Training fails

1. Ensure at least 2 minutes of data collected:
   ```bash
   docker exec influxdb influx query '
   from(bucket:"New_Sensor")
     |> range(start:-1h)
     |> count()
   '
   ```

2. Check Spark logs:
   ```bash
   docker logs spark-master
   docker logs spark-worker-1
   docker logs spark-worker-2
   ```

3. Verify Python dependencies:
   ```bash
   docker exec spark-master pip list | grep -E "torch|numpy|pandas|influxdb"
   ```

4. Manual retry:
   ```bash
   ./retrain.sh
   ```

### Problem: System using too much resources

Check resource usage:
```bash
docker stats
```

Adjust Spark worker memory in `docker-compose.yml`:
```yaml
spark-worker-1:
  environment:
    SPARK_WORKER_MEMORY: 1G  # Reduce from 2G
    SPARK_WORKER_CORES: 1    # Reduce from 2
```

Then restart:
```bash
./stop.sh
./deploy.sh
```

---

## 📊 Adding New Devices

### Method 1: Update Data Generator (for testing)

Edit `GenerateData.py`:
```python
SENSOR_WORKSPACES = [
    "lathe-1-spindle",
    "cnc-mill-5-axis", 
    "robot-arm-02",
    "YOUR_NEW_DEVICE"  # Add new workspace
]
```

Restart data generator:
```bash
pkill -f GenerateData.py
nohup python3 GenerateData.py > logs/generate_data.log 2>&1 &
```

### Method 2: Connect Real Device

Configure your device to publish to MQTT:
- **Broker**: `YOUR_SERVER_IP:1883`
- **Username**: `test`
- **Password**: `test`
- **Topic**: `machine_sensor_data`
- **Format**: JSON with required fields

Example message:
```json
{
  "workspace_id": "new-machine-name",
  "sensor_type": "industrial",
  "current": 15.5,
  "accX": 0.12,
  "accY": -0.08,
  "accZ": 0.95,
  "tempA": 68.2,
  "tempB": 72.1
}
```

The system automatically:
1. Captures new workspace data
2. Stores in InfluxDB
3. Trains new model on next training run
4. No configuration changes needed!

---

## 📝 Configuration

### Change Training Schedule

Edit `docker-compose.yml`, training-scheduler service:

```yaml
echo '0 0 1 * * /usr/bin/bash /run_monthly_training.sh' | crontab -
#      ┬ ┬ ┬ ┬ ┬
#      │ │ │ │ └─ Day of week (0-7)
#      │ │ │ └─── Month (1-12)
#      │ │ └───── Day of month (1-31)
#      │ └─────── Hour (0-23)
#      └───────── Minute (0-59)
```

Examples:
- Weekly (Sunday midnight): `0 0 * * 0`
- Daily (midnight): `0 0 * * *`
- Twice monthly (1st & 15th): `0 0 1,15 * *`

Restart training scheduler:
```bash
docker-compose restart training-scheduler
```

### Change InfluxDB Retention

Connect to InfluxDB:
```bash
docker exec -it influxdb influx
```

Set retention policy:
```
use New_Sensor
CREATE RETENTION POLICY "one_year" ON "New_Sensor" DURATION 52w REPLICATION 1 DEFAULT
```

---

## 🔐 Security Recommendations

### For Production Deployment:

1. **Change default passwords**:
   - Edit `docker-compose.yml` (InfluxDB)
   - Edit `mqtt-broker/config/mosquitto.conf` (MQTT)
   - Update credentials in Python scripts

2. **Use SSL/TLS**:
   - Configure Mosquitto with SSL certificates
   - Enable HTTPS for InfluxDB

3. **Firewall configuration**:
   - Only open necessary ports
   - Restrict access to specific IPs

4. **Regular backups**:
   ```bash
   # Backup InfluxDB data
   tar -czf influxdb_backup_$(date +%Y%m%d).tar.gz influxdb/data/
   
   # Backup models
   tar -czf models_backup_$(date +%Y%m%d).tar.gz spark-apps/models/
   ```

---

## 📚 Additional Resources

- **Full Documentation**: See `README.md`
- **Quick Start**: See `QUICKSTART.md`
- **GitHub Repository**: https://github.com/Pasindu2000B/IOT

---

## 💡 Tips

- System needs ~2GB RAM minimum
- Docker requires ~20GB disk space
- First training needs 2+ minutes of data
- Monthly retraining happens automatically
- Bridge auto-reconnects on any failure
- New workspaces detected automatically

---

**Your system is production-ready and fully automated!** 🎉
