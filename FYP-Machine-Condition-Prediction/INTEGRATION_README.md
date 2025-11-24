# 🔗 FYP Inference System - IOT Integration

**Status:** ✅ Integrated with IOT Training System  
**Date:** November 24, 2025  
**Update:** 🆕 **Multi-Workspace Support - Monitors ALL workspaces automatically!**

---

## 🎯 What's New: Multi-Workspace Support

The FYP Inference System now:

✅ **Auto-discovers all workspaces** from InfluxDB  
✅ **Loads all workspace models** simultaneously  
✅ **Monitors all machines** in parallel  
✅ **Automatically detects new workspaces** when added  
✅ **No configuration needed** - just deploy and run!  

**Before:** One FYP instance = One workspace (manual configuration)  
**Now:** One FYP instance = ALL workspaces (automatic discovery)

---

## 🚀 Quick Start

### Prerequisites
1. IOT Training System must be deployed first
2. At least one model must be trained (check `../spark-apps/models/`)

### Deploy
```bash
# 1. Configure environment (no WORKSPACE_ID needed!)
copy .env.example .env
# Edit .env and set SENDGRID_API_KEY only

# 2. Start FYP system
docker-compose up -d --build

# 3. Check logs - you'll see all workspaces detected
docker logs fyp-inference-service -f

# 4. Test API
curl http://localhost:8000/workspaces
curl http://localhost:8000/sensor/latest
```

---

## 📊 Multi-Workspace Architecture

```
┌────────────────────────────────────────────┐
│       FYP Inference Service (Single)       │
├────────────────────────────────────────────┤
│                                            │
│  Initialization:                           │
│  • Scans AI-Model-Artifacts/               │
│  • Finds: model_lathe-1-spindle_*          │
│  •        model_cnc-mill-5-axis_*          │
│  •        model_robot-arm-02_*             │
│  • Loads ALL 3 models into memory          │
│                                            │
│  Every 10 seconds:                         │
│  • Queries InfluxDB for active workspaces  │
│  • For each workspace:                     │
│    - Maintains separate buffer (360 pts)   │
│    - Tracks separate counter               │
│    - Uses separate MongoDB collection      │
│                                            │
│  Every hour (per workspace):               │
│  • Computes hourly mean                    │
│  • Stores in hourly_means_{workspace_id}   │
│  • Retrieves 1200 lookback means           │
│  • Selects correct model from loaded set   │
│  • Runs inference                          │
│  • Sends alerts if at risk                 │
│                                            │
└────────────────────────────────────────────┘
```

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# InfluxDB (shared with IOT)
INFLUX_URL=http://influxdb:8086
INFLUX_TOKEN=GO7pQ79-Vo-k6uwpQrMmJmITzLRHxyrFbFDrnRbz8PgZbLHKe5hpwNZCWi6Z_zolPRjn7jUQ6irQk-BPe3LK9Q==
INFLUX_ORG=Ruhuna_Eng
INFLUX_BUCKET=New_Sensor

# SendGrid (REQUIRED for email alerts)
SENDGRID_API_KEY=your_actual_key_here

# MongoDB (auto-configured)
MONGO_URI=mongodb://mongo:27017

# WORKSPACE_ID - REMOVED! System monitors ALL workspaces
```

---

## 🆕 New API Endpoints

### GET `/workspaces`
**Returns all monitored workspaces and available models**

```bash
curl http://localhost:8000/workspaces
```

Response:
```json
{
  "status": "success",
  "active_workspaces": ["lathe-1-spindle", "cnc-mill-5-axis", "robot-arm-02"],
  "models_available": ["lathe-1-spindle", "cnc-mill-5-axis", "robot-arm-02"],
  "total_active": 3,
  "total_models": 3
}
```

### GET `/sensor/latest?workspace_id=lathe-1-spindle`
**Get latest data for specific workspace or all workspaces**

```bash
# Specific workspace
curl http://localhost:8000/sensor/latest?workspace_id=lathe-1-spindle

# All workspaces
curl http://localhost:8000/sensor/latest
```

### GET `/sensor/history?workspace_id=cnc-mill-5-axis`
**Get last hour of data for specific workspace or all**

```bash
# Specific workspace
curl http://localhost:8000/sensor/history?workspace_id=cnc-mill-5-axis

# All workspaces
curl http://localhost:8000/sensor/history
```

### GET `/sensor/hourly-mean?workspace_id=robot-arm-02`
**Get hourly mean for specific workspace or all**

### GET `/sensor/last-lookback?workspace_id=lathe-1-spindle`
**Get 1200 lookback means for specific workspace or all**

---

## 🔄 Automatic Workspace Discovery

### How It Works

**1. Model Discovery (On Startup)**
```python
# Scans: AI-Model-Artifacts/model_*_*/
# Extracts workspace IDs from directory names
# Loads latest model for each workspace
```

**2. Data Discovery (Every 10 seconds)**
```python
# Queries InfluxDB:
#   SELECT DISTINCT workspace_id FROM sensor_data
#   WHERE time > now() - 1h
# Creates buffers for any new workspaces found
```

**3. Dynamic Model Loading**
```python
# When new workspace detected:
#   - Checks if model exists in AI-Model-Artifacts/
#   - Loads model and scaler
#   - Starts monitoring automatically
```

---

## 🗄️ MongoDB Collections

Each workspace gets its own collection:

```
Database: Default
Collections:
  • hourly_means_lathe-1-spindle
  • hourly_means_cnc-mill-5-axis  
  • hourly_means_robot-arm-02
  • hourly_means_{new_workspace}  ← Auto-created
  • users
  • workspaces
```

---

## 📁 Model Directory Structure

```
AI-Model-Artifacts/ (mounted from ../spark-apps/models/)
├── model_lathe-1-spindle_20251124_120000/
│   ├── config.json
│   ├── model.safetensors
│   └── pytorch_model.bin
├── scaler_lathe-1-spindle_20251124_120000.pkl
├── model_cnc-mill-5-axis_20251124_120000/
├── scaler_cnc-mill-5-axis_20251124_120000.pkl
├── model_robot-arm-02_20251124_120000/
├── scaler_robot-arm-02_20251124_120000.pkl
└── model_{new_workspace}_*/  ← Auto-detected
    └── scaler_{new_workspace}_*.pkl
```

---

## ➕ Adding New Workspaces

### Step 1: Add to IOT System
```python
# In IOT/GenerateData.py
SENSOR_WORKSPACES = [
    "lathe-1-spindle", 
    "cnc-mill-5-axis", 
    "robot-arm-02",
    "press-machine-01"  # ← New workspace
]
```

### Step 2: Wait for Training
```bash
# Monthly training will automatically create:
# - model_press-machine-01_20251201_120000/
# - scaler_press-machine-01_20251201_120000.pkl
```

### Step 3: That's It!
FYP automatically:
1. Detects new data in InfluxDB
2. Finds new model in AI-Model-Artifacts/
3. Loads model and starts monitoring
4. Creates MongoDB collection
5. Runs inference every hour

**No restart required!** (though restart recommended for immediate model loading)

---

## 🔍 Monitoring Multiple Workspaces

### Check Status
```bash
# See all active workspaces
curl http://localhost:8000/workspaces | jq

# Check latest data for all
curl http://localhost:8000/sensor/latest | jq

# Check specific workspace
curl "http://localhost:8000/sensor/latest?workspace_id=lathe-1-spindle" | jq
```

### View Logs
```bash
# All workspaces
docker logs fyp-inference-service -f

# Look for:
# [InferenceService] Discovered 3 workspace(s)
# [InferenceService] ✓ Loaded model for workspace: lathe-1-spindle
# [RealInfluxStreamer] New workspace detected: cnc-mill-5-axis
# [RealInfluxStreamer] lathe-1-spindle: Running inference...
```

---

## 📊 Performance Metrics

### Resource Usage (3 Workspaces)
```
Memory:
  - 3 models loaded: ~150-300MB
  - 3 buffers (360 pts each): ~1-2MB
  - Total: ~200-350MB

Processing:
  - InfluxDB query: Every 10 seconds (all workspaces)
  - MongoDB write: Every hour per workspace (3/hour)
  - Inference: Every hour per workspace (3/hour)
  - Email: On-demand per workspace

Scalability:
  - Tested: 3 workspaces
  - Estimated capacity: 10-20 workspaces per instance
  - For >20: Deploy multiple FYP instances
```

---

## 🐛 Troubleshooting

### "No models loaded"
```bash
# Check IOT models directory
ls ../spark-apps/models/

# Verify models exist
docker exec fyp-inference-service ls -la /app/AI-Model-Artifacts/
```

### "Workspace not detected"
```bash
# Check if data exists in InfluxDB
docker exec influxdb influx query '
from(bucket:"New_Sensor")
  |> range(start:-1h)
  |> filter(fn:(r) => r._measurement == "sensor_data")
  |> keep(columns: ["workspace_id"])
  |> distinct(column: "workspace_id")
'

# Check FYP logs
docker logs fyp-inference-service | grep "workspace detected"
```

### "Model not found for workspace"
```bash
# Verify model exists and matches workspace name
ls ../spark-apps/models/ | grep {workspace_id}

# Restart FYP to reload models
docker-compose restart app
```

---

## ✅ Integration Checklist

- [x] Multi-workspace model loading
- [x] Dynamic workspace discovery from InfluxDB
- [x] Separate buffers per workspace
- [x] Separate MongoDB collections per workspace  
- [x] Parallel inference for all workspaces
- [x] API endpoints support workspace filtering
- [x] Automatic new workspace detection
- [x] No WORKSPACE_ID configuration needed
- [x] Documentation updated

---

## 🎉 Benefits

✅ **Zero Configuration** - No workspace IDs to set  
✅ **Automatic Scaling** - New workspaces detected automatically  
✅ **Efficient** - Single instance monitors all machines  
✅ **Parallel Processing** - All workspaces monitored simultaneously  
✅ **Flexible API** - Query specific workspace or all at once  
✅ **Future-Proof** - Add unlimited workspaces without code changes  

---

**System ready for multi-workspace deployment!** 🎉

For full deployment guide, see `../INTEGRATION_GUIDE.md`

This FYP Inference System has been **fully integrated** with the IOT Training System. It now:

✅ Reads data from IOT's InfluxDB (`sensor_data` measurement)  
✅ Uses IOT's 6-feature format (current, accX, accY, accZ, tempA, tempB)  
✅ Loads models trained by IOT Spark system  
✅ Shares network and database with IOT system  
✅ Auto-detects latest trained models per workspace  

---

## 🚀 Quick Start

### Prerequisites
1. IOT Training System must be deployed first
2. At least one model must be trained (check `../spark-apps/models/`)

### Deploy
```bash
# 1. Configure environment
copy .env.example .env
# Edit .env and set WORKSPACE_ID and SENDGRID_API_KEY

# 2. Start FYP system
docker-compose up -d --build

# 3. Check logs
docker logs fyp-inference-service -f

# 4. Test API
curl http://localhost:8000/sensor/latest
```

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# InfluxDB (shared with IOT)
INFLUX_URL=http://influxdb:8086
INFLUX_TOKEN=GO7pQ79-Vo-k6uwpQrMmJmITzLRHxyrFbFDrnRbz8PgZbLHKe5hpwNZCWi6Z_zolPRjn7jUQ6irQk-BPe3LK9Q==
INFLUX_ORG=Ruhuna_Eng
INFLUX_BUCKET=New_Sensor

# Workspace Selection (REQUIRED)
WORKSPACE_ID=lathe-1-spindle
# Options: lathe-1-spindle, cnc-mill-5-axis, robot-arm-02

# SendGrid (REQUIRED for email alerts)
SENDGRID_API_KEY=your_actual_key_here
```

---

## 📁 Data Format (IOT Compatible)

### InfluxDB Query
```flux
from(bucket: "New_Sensor")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "sensor_data")
  |> filter(fn: (r) => r.workspace_id == "lathe-1-spindle")
```

### Fields (6 features)
- `current` - Motor current (10-25A)
- `accX` - X-axis acceleration (-0.5 to 0.5g)
- `accY` - Y-axis acceleration (-0.5 to 0.5g)
- `accZ` - Z-axis acceleration (0.8 to 1.2g)
- `tempA` - Temperature sensor A (55-80°C)
- `tempB` - Temperature sensor B (55-80°C)

### MongoDB Documents (Hourly Means)
```json
{
  "_id": ObjectId("..."),
  "workspace_id": "lathe-1-spindle",
  "current_mean": 17.5,
  "accX_mean": 0.02,
  "accY_mean": -0.01,
  "accZ_mean": 0.98,
  "tempA_mean": 68.3,
  "tempB_mean": 72.1,
  "num_points_used": 360,
  "alert_message": "Machine Condition Normal (Checked at: 2025-11-24T10:00:00)"
}
```

---

## 🧠 Model Loading

### Auto-Detection
The system automatically finds the **latest trained model** for your configured workspace:

```python
# Searches for: AI-Model-Artifacts/model_{WORKSPACE_ID}_*
# Example: model_lathe-1-spindle_20251124_120000/

# Loads:
# - HuggingFace PatchTST model (from directory)
# - MinMax scaler (corresponding .pkl file)
```

### Model Directory Structure
```
AI-Model-Artifacts/ (mounted from ../spark-apps/models/)
├── model_lathe-1-spindle_20251124_120000/
│   ├── config.json
│   ├── model.safetensors
│   └── pytorch_model.bin
├── scaler_lathe-1-spindle_20251124_120000.pkl
├── model_cnc-mill-5-axis_20251124_120000/
├── scaler_cnc-mill-5-axis_20251124_120000.pkl
└── ...
```

---

## 🔄 Workflow

### Every 10 Seconds
1. Query InfluxDB for latest data point
2. Add to buffer (max 360 points)

### Every Hour (after 360 points)
1. Compute hourly means for 6 features
2. Store mean in MongoDB
3. Retrieve last 1200 means (50 days)
4. Load latest IOT-trained model
5. Run inference (predict 240 hours ahead)
6. Detect anomalies (forecast vs historical range)
7. Send email alerts if at risk

---

## 📊 API Endpoints

### GET `/sensor/latest`
Returns most recent data point from buffer

### GET `/sensor/history`
Returns last 360 points (1 hour of data)

### GET `/sensor/hourly-mean`
Returns current hourly mean calculation

### GET `/sensor/means-history-db`
Returns recent hourly means from MongoDB

### GET `/sensor/last-lookback`
Returns last 1200 means used for inference

---

## 🐛 Troubleshooting

### "No trained models found"
```bash
# Check if IOT system has trained models
ls ../spark-apps/models/

# If empty, run training
cd ..
.\retrain.ps1
```

### "Can't connect to InfluxDB"
```bash
# Verify IOT network exists
docker network ls | grep iot-network

# Check if in correct network
docker inspect fyp-inference-service | grep iot-network

# Restart with network
docker-compose down
docker-compose up -d
```

### "No data from InfluxDB"
```bash
# Check if IOT bridge is running
Get-Content ..\logs\bridge.log -Wait

# Query InfluxDB directly
docker exec influxdb influx query '
from(bucket:"New_Sensor")
  |> range(start:-1h)
  |> filter(fn:(r) => r._measurement == "sensor_data")
  |> count()
'
```

### "Buffer not filling"
```bash
# Check workspace_id matches IOT data
docker logs fyp-inference-service | grep "workspace_id"

# Verify .env WORKSPACE_ID setting
cat .env | grep WORKSPACE_ID
```

---

## 📚 Related Documentation

- **Integration Guide:** `../INTEGRATION_GUIDE.md`
- **IOT System:** `../README.md`
- **Original Workflow:** `./final_project_workflow.md`

---

## ✅ Integration Checklist

- [x] InfluxDB measurement changed to `sensor_data`
- [x] Tag changed from `machine_id` to `workspace_id`
- [x] Fields updated to 6 IOT features
- [x] Statistics service computes 6 feature means
- [x] Inference service handles 6-feature input
- [x] Model loading auto-detects latest per workspace
- [x] Docker compose connects to iot-network
- [x] Model directory mounted from IOT system
- [x] Environment variables configured
- [x] Documentation updated

---

**System ready for deployment!** 🎉

For full deployment guide, see `../INTEGRATION_GUIDE.md`
