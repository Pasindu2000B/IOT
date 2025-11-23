# QuickStart Guide - IOT Predictive Maintenance System

## 🚀 Deploy in 3 Steps

### Linux/Mac Server
```bash
chmod +x *.sh
./deploy.sh
```

### Windows Server
```powershell
.\deploy.ps1
```

**Time: 5-7 minutes**

---

## ✅ What Happens

1. **Starts Docker** (Mosquitto, InfluxDB, Spark)
2. **Installs dependencies** (NumPy, PyTorch, etc.)
3. **Starts data collection** (3 workspaces)
4. **Trains initial models** (distributed)

---

## 📊 After Deployment

### Access Services
- Spark UI: http://localhost:8080
- InfluxDB: http://localhost:8086

### Check Status
```bash
./status.sh      # Linux
.\status.ps1     # Windows
```

### View Logs
```bash
tail -f logs/bridge.log             # Linux
Get-Content logs\bridge.log -Wait   # Windows
```

---

## 🎯 Daily Operations

### Retrain Models (Manual)
```bash
./retrain.sh     # Linux
.\retrain.ps1    # Windows
```

### Stop System
```bash
./stop.sh        # Linux
.\stop.ps1       # Windows
```

---

## 🤖 Automatic Features

✅ **Monthly retraining** - 1st of month  
✅ **Auto-reconnecting bridge** - Never breaks  
✅ **New workspace detection** - Automatic  
✅ **Service auto-restart** - Docker handles it

---

## 📁 Key Files

- `GenerateData.py` - Sensor simulator
- `mqtt_to_influx_bridge.py` - Data pipeline
- `spark-apps/train_distributed.py` - ML training
- `spark-apps/models/` - Trained models
- `logs/` - All system logs

---

## 🔧 Troubleshooting

### No data flowing?
```bash
./start_bridge.sh    # Linux
.\start_bridge.ps1   # Windows
```

### Training fails?
Wait 2+ minutes for data collection, then:
```bash
./retrain.sh         # Linux
.\retrain.ps1        # Windows
```

---

## 📚 Full Documentation

See `README.md` for complete details.

---

**That's it! System is production-ready** 🎉
