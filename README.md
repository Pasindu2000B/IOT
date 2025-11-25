# IOT Predictive Maintenance System

Real-time machine condition monitoring and anomaly detection using PatchTST transformer models.

## 📁 Project Structure

```
IOT/
├── FYP-Machine-Condition-Prediction/     # Main inference application
│   ├── main.py                           # FastAPI server
│   ├── add_colab_model.py                # Helper to add Colab models
│   ├── MODEL_SETUP.md                    # Model setup guide
│   ├── services/                         # Core services
│   │   ├── inference_service.py          # Model loading & inference
│   │   └── real_influx_streamer.py       # InfluxDB data streaming
│   ├── static/                           # Web dashboard
│   │   ├── dashboard.html                # Main monitoring dashboard
│   │   └── validation.html               # Model validation page
│   └── FYP-Machine-Condition-Prediction/ # Trained models
│       ├── model_{workspace}_{timestamp}/ # PatchTST model folders
│       └── scaler_{workspace}_{timestamp}.pkl # MinMaxScaler files
│
├── spark-apps/                           # Distributed training
│   ├── train_distributed.py             # Spark-based model training
│   └── run-spark-training.ps1           # Training script
│
├── mqtt-broker/                          # MQTT configuration
│   └── config/mosquitto.conf
│
├── influxdb/                             # InfluxDB data storage
│
├── docker-compose.yml                    # VM services (MQTT + InfluxDB)
├── GenerateData.py                       # Test data generator
└── mqtt_to_influx_bridge_vm.py          # MQTT → InfluxDB bridge
```

## 🚀 Quick Start

### 1. Start VM Services (on server: 142.93.220.152)
```bash
docker-compose up -d
```

### 2. Start Data Bridge (on local PC)
```bash
python mqtt_to_influx_bridge_vm.py
```

### 3. Start Inference Server (on local PC)
```bash
cd FYP-Machine-Condition-Prediction
python main.py
```

### 4. Access Dashboards
- Main Dashboard: http://localhost:8000
- Model Validation: http://localhost:8000/validation
- API Docs: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables (.env)
```env
INFLUX_URL=http://142.93.220.152:8086
INFLUX_TOKEN=your-token
INFLUX_ORG=Ruhuna_Eng
INFLUX_BUCKET=New_Sensor
```

### VM Services
- **MQTT Broker**: 142.93.220.152:1883 (mosquitto)
- **InfluxDB**: 142.93.220.152:8086 (v2.7)

## 📊 Adding Your Trained Model

See [MODEL_SETUP.md](FYP-Machine-Condition-Prediction/MODEL_SETUP.md) for detailed instructions.

**Quick steps:**
1. Save model in Colab with correct naming
2. Copy to `FYP-Machine-Condition-Prediction/FYP-Machine-Condition-Prediction/`
3. Restart inference server

## 🎯 Training New Models

```bash
cd spark-apps
py -3.11 train_distributed.py
```

Requires Python 3.11 for Spark compatibility.

## 🌐 API Endpoints

- `GET /` - Main dashboard
- `GET /validation` - Model validation page
- `GET /workspaces` - List available models
- `GET /predict/{workspace_id}` - Get predictions
- `GET /validate/{workspace_id}` - Validate model accuracy

## 📈 Features

- **Real-time Monitoring**: 60-second inference cycles
- **Multi-workspace Support**: Independent models per machine
- **Anomaly Detection**: Automatic alert generation
- **Model Validation**: Compare predictions vs actual data
- **Distributed Training**: Spark-based parallel training
- **Interactive Dashboards**: Live charts and metrics

## 🛠️ Tech Stack

- **ML Framework**: HuggingFace Transformers (PatchTST)
- **Backend**: FastAPI + Uvicorn
- **Training**: Apache Spark 4.0.1 + PySpark
- **Time Series DB**: InfluxDB 2.7
- **Message Broker**: Eclipse Mosquitto 2.0
- **Frontend**: Chart.js + Vanilla JS
- **Data Processing**: NumPy, Pandas, PyTorch

## 📝 Model Details

- **Architecture**: PatchTST (Patch Time Series Transformer)
- **Context Length**: 50 timesteps (100 seconds)
- **Prediction Horizon**: 10 timesteps (20 seconds)
- **Features**: 6 sensors (current, accX, accY, accZ, tempA, tempB)
- **Sampling Rate**: 2 seconds per reading

## 🔍 Troubleshooting

**Server won't start:**
- Check if port 8000 is available
- Verify .env file exists with correct credentials

**No predictions:**
- Ensure workspace_id matches model name exactly
- Check InfluxDB has data for the workspace
- Verify at least 50 data points available

**Validation fails:**
- Need 60+ data points (50 context + 10 prediction)
- Let data accumulate for a few minutes

## 📚 Documentation

- [Model Setup Guide](FYP-Machine-Condition-Prediction/MODEL_SETUP.md)
- API Documentation: http://localhost:8000/docs (when server running)

## 🎓 Academic Use

This system demonstrates:
- Transformer models for time series forecasting
- Distributed machine learning with Spark
- Real-time IoT data processing
- Predictive maintenance in industrial settings


**Distributed machine learning system for industrial equipment monitoring using MQTT, InfluxDB, and Apache Spark with HuggingFace PatchTST model.**

> **🆕 UPDATED:** System now uses research-proven PatchTST architecture from validated notebook. See [NOTEBOOK_INTEGRATION_SUMMARY.md](NOTEBOOK_INTEGRATION_SUMMARY.md) for complete details.

## 🎯 System Architecture

```
Sensor Data (GenerateData.py) - 4 features, hourly intervals
         ↓
    MQTT Broker (Eclipse Mosquitto)
         ↓
MQTT→InfluxDB Bridge (mqtt_to_influx_bridge.py)
         ↓
    InfluxDB (Time-series database)
         ↓
Spark Distributed Training (train_distributed.py)
    ↓ HuggingFace PatchTST Model
    ↓ Context: 1200 timesteps (50 days)
    ↓ Prediction: 240 timesteps (10 days)
         ↓
Per-Workspace Models (saved via save_pretrained())
```

## 🚀 Quick Deployment

### Linux/Mac
```bash
chmod +x *.sh
./deploy.sh
```

### Windows
```powershell
.\deploy.ps1
```

**First deployment time: 10-15 minutes** (includes Docker image build with ML dependencies)  
**Subsequent deployments: 5-7 minutes** (uses cached images)

## 📦 What Gets Deployed

- **MQTT Broker** - Eclipse Mosquitto 2.0 (port 1883)
- **InfluxDB** - Time-series database (port 8086)
- **Spark Cluster** - 1 Master + 2 Workers (with ML dependencies)
  - PyTorch 2.0.1
  - Transformers 4.35.0
  - Accelerate, Datasets, scikit-learn
- **Data Generator** - Simulates 3 industrial workspaces
- **MQTT Bridge** - Auto-reconnecting data pipeline
- **Training Scheduler** - Monthly automated retraining

## ⚙️ System Features

### Production-Ready
✅ **Research-proven model** - HuggingFace PatchTST from validated notebook  
✅ **Auto-reconnecting bridge** - 5 retries, exponential backoff  
✅ **Distributed training** - Spark parallelizes across workers  
✅ **Monthly automation** - Cron-scheduled retraining  
✅ **Per-workspace models** - Automatic workspace discovery  
✅ **Docker auto-restart** - All services recover from failures  
✅ **Comprehensive logging** - Full monitoring and troubleshooting  
✅ **Early stopping** - Prevents overfitting (patience=5 epochs)  
✅ **Gradient clipping** - Training stability (max_norm=1.0)

### Workspaces
- `lathe-1-spindle`
- `cnc-mill-5-axis`
- `robot-arm-02`

### Sensor Data (per workspace)
- `current` - Motor current (A) [10-25A]
- `accX, accY, accZ` - Vibration/Acceleration (g)
- `tempA` - Temperature A (°C) [55-80°C]
- `tempB` - Temperature B (°C) [55-80°C]

## 🧠 ML Model Details

### PatchTST Architecture
- **Model:** HuggingFace Transformers `PatchTSTForPrediction`
- **Context Length:** 1200 timesteps (50 days of hourly data)
- **Prediction Length:** 240 timesteps (10 days ahead)
- **Features:** 6 sensors (current, accX, accY, accZ, tempA, tempB)
- **Patch Length:** 12 timesteps
- **Patch Stride:** 3 timesteps
- **Model Dimension:** 256
- **FFN Dimension:** 512
- **Attention Heads:** 4
- **Layers:** 2
- **Dropout:** 0.1

### Training Configuration
- **Batch Size:** 128
- **Learning Rate:** 1e-5
- **Optimizer:** AdamW
- **Epochs:** 20 (with early stopping)
- **Gradient Clipping:** max_norm=1.0
- **Validation Split:** 80/20
- **Preprocessing:** MinMaxScaler(0, 1)

## 🔧 Management Commands

### Check System Status
```bash
./status.sh      # Linux/Mac
.\status.ps1     # Windows
```

### Manual Retraining
```bash
./retrain.sh     # Linux/Mac
.\retrain.ps1    # Windows
```

### View Logs
```bash
tail -f logs/bridge.log                    # Linux/Mac
Get-Content logs\bridge.log -Wait          # Windows
```

### Stop System
```bash
./stop.sh        # Linux/Mac
.\stop.ps1       # Windows
```

## 🌐 Access URLs

After deployment:
- **Spark Master UI**: http://localhost:8080
- **InfluxDB UI**: http://localhost:8086
  - Username: `Pasindu Bimsara`
  - Password: `abcdefgh`
- **MQTT Broker**: localhost:1883
  - Username: `test`
  - Password: `test`

## 📁 Directory Structure

```
IOT/
├── GenerateData.py              # Sensor data simulator
├── mqtt_to_influx_bridge.py     # MQTT→InfluxDB pipeline
├── docker-compose.yml           # Service orchestration
├── deploy.sh / deploy.ps1       # Deployment scripts
├── stop.sh / stop.ps1           # Stop scripts
├── retrain.sh / retrain.ps1     # Manual training
├── status.sh / status.ps1       # Health checks
├── start_bridge.sh/.ps1         # Bridge management
├── stop_bridge.sh/.ps1          # Bridge management
├── run_monthly_training.sh      # Cron training script
├── spark-apps/
│   ├── train_distributed.py     # Distributed ML training
│   ├── models/                  # Trained models
│   └── logs/                    # Training logs
├── logs/                        # System logs
└── mqtt-broker/                 # Mosquitto config
```

## 🤖 Automated Operations

### Continuous (Always Running)
- Data generation (every 2 seconds)
- MQTT→InfluxDB bridge (real-time)
- Spark cluster (ready for training)

### Monthly (1st of month at midnight)
- Model retraining across all workspaces
- Uses Spark distributed system
- Automatic workspace discovery

## 📊 Model Details
### Model Requirements
- **Minimum Data:** 1440 hourly data points per workspace (1 day)
- **Recommended:** 2400+ points (100 days) for quality training
- **Training Time:** 5-10 minutes per workspace
- **Model Size:** 5-10MB per workspace (HuggingFace checkpoint)
- **Storage:** Model directory + scaler pickle file per workspace

## 🔍 Monitoring

### Check Data Flow
```bash
# View bridge logs
tail -f logs/bridge.log

# Query InfluxDB
docker exec influxdb influx query '
from(bucket:"New_Sensor")
  |> range(start:-1h)
  |> filter(fn:(r) => r._measurement == "sensor_data")
  |> count()
'
```

### Check Training
```bash
# View training logs
docker logs training-scheduler

# List models (HuggingFace format)
ls -lh spark-apps/models/model_*/
```

## 🛠️ Troubleshooting

### Bridge Not Running
```bash
./start_bridge.sh    # Linux/Mac
.\start_bridge.ps1   # Windows
```

### No Data in InfluxDB
1. Check MQTT broker: `docker logs mosquitto`
2. Check bridge logs: `tail -f logs/bridge.log`
3. Check data generator: `ps aux | grep GenerateData`

### Training Fails
1. Ensure 1440+ hourly data points collected per workspace
2. Check Spark logs: `docker logs spark-master`
3. Verify ML dependencies: `docker exec spark-master pip list | grep transformers`
4. Check available memory: Training requires 2GB+ RAM per worker

## 📝 Configuration

### Change Training Schedule
Edit `docker-compose.yml`, training-scheduler service:
```yaml
echo '0 0 1 * * /usr/bin/bash /run_monthly_training.sh' | crontab -
#      ┬ ┬ ┬ ┬ ┬
#      │ │ │ │ └─ Day of week (0-7, Sunday=0 or 7)
#      │ │ │ └─── Month (1-12)
#      │ │ └───── Day of month (1-31)
#      │ └─────── Hour (0-23)
#      └───────── Minute (0-59)
```

### Add New Workspace
Add to `GenerateData.py`:
```python
SENSOR_WORKSPACES = ["lathe-1-spindle", "cnc-mill-5-axis", "robot-arm-02", "YOUR_NEW_WORKSPACE"]
```
System auto-discovers and trains new model!

## 📚 Dependencies

- Docker & Docker Compose
- Python 3.8+
- paho-mqtt
- influxdb-client
- torch (CPU version)
- numpy, pandas

## 🎓 References

- **PatchTST**: https://arxiv.org/abs/2211.14730
- **InfluxDB**: https://docs.influxdata.com/
- **Apache Spark**: https://spark.apache.org/docs/latest/
- **MQTT**: https://mqtt.org/

## 📄 License

MIT License

## 👤 Author

Pasindu Bimsara  
University of Ruhuna - Engineering Faculty
