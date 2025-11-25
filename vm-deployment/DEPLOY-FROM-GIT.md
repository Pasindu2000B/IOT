# Deploy IOT System on VM Using Git Clone

## 🎯 Overview

Clone the entire repository on VM, then run only the VM services (MQTT + InfluxDB). Your PC will query the VM for training/inference.

---

## 🚀 Step-by-Step Deployment

### 1️⃣ SSH to VM

```bash
ssh root@142.93.220.152
```

### 2️⃣ Install Git (if not installed)

```bash
# Check if git exists
git --version

# If not installed:
sudo apt update
sudo apt install -y git
```

### 3️⃣ Clone Repository

```bash
# Navigate to home directory
cd /root

# Clone the repo
git clone https://github.com/Pasindu2000B/IOT.git

# Navigate to vm-deployment folder
cd IOT/vm-deployment
```

### 4️⃣ Run Deployment Script

```bash
# Make script executable
chmod +x deploy-vm.sh

# Run automated deployment
sudo ./deploy-vm.sh
```

**Script will automatically:**
- ✅ Install Docker & Docker Compose
- ✅ Configure firewall (ports 1883, 8086, 9001)
- ✅ Start MQTT, InfluxDB, Telegraf containers
- ✅ Display status and memory usage

---

## ✅ Expected Output

```
========================================
IOT VM Deployment - Sensor Data Receiver
VM IP: 142.93.220.152
========================================

[1/7] Updating system... ✓
[2/7] Installing Docker... ✓
[3/7] Installing Docker Compose... ✓
[4/7] Creating deployment directory... ✓
[5/7] Setting up configuration files... ✓
[6/7] Configuring firewall... ✓
[7/7] Starting Docker services... ✓

========================================
Deployment Status
========================================
NAMES          STATUS              PORTS
vm-mosquitto   Up 5 seconds        0.0.0.0:1883->1883/tcp, 0.0.0.0:9001->9001/tcp
vm-influxdb    Up 5 seconds        0.0.0.0:8086->8086/tcp
vm-telegraf    Up 5 seconds

========================================
Memory Usage
========================================
CONTAINER       CPU %               MEM USAGE / LIMIT
vm-mosquitto    0.05%               48MiB / 64MiB
vm-influxdb     1.23%               240MiB / 256MiB
vm-telegraf     0.03%               45MiB / 64MiB

✓ VM deployment complete!
```

---

## 🔧 Configure Your Sensors

### Point sensors to VM MQTT broker:

**Host:** `142.93.220.152`  
**Port:** `1883`  
**Topic:** `machine_sensor_data`

### JSON message format:

```json
{
  "workspace_id": "lathe-1-spindle",
  "sensor_type": "industrial",
  "current": 18.45,
  "accX": 0.0023,
  "accY": -0.0012,
  "accZ": 0.9987,
  "tempA": 67.3,
  "tempB": 65.8
}
```

---

## 🧪 Test Data Flow

### Test 1: MQTT is receiving data

```bash
# On VM, subscribe to sensor topic
docker exec vm-mosquitto mosquitto_sub -t machine_sensor_data -v
```

Keep this running, then send test data from your sensor device:

```bash
# From sensor device (or another terminal)
mosquitto_pub -h 142.93.220.152 -t machine_sensor_data -m '{"workspace_id":"lathe-1-spindle","current":15.5,"accX":0.001,"accY":0.002,"accZ":0.998,"tempA":65.0,"tempB":63.5}'
```

You should see the message appear in the subscription terminal.

### Test 2: Data reaches InfluxDB

```bash
# On VM, query recent data
docker exec vm-influxdb influx query 'from(bucket:"New_Sensor") |> range(start: -10m) |> limit(n:10)'
```

Should show recent sensor readings.

### Test 3: PC can read from VM

```powershell
# On your PC, test InfluxDB connection
curl http://142.93.220.152:8086/health
```

Should return: `{"status":"pass",...}`

---

## 🖥️ PC-Side Setup (Already Done)

Your PC is already configured:
- ✅ `.env` updated: `INFLUX_URL=http://142.93.220.152:8086`
- ✅ FastAPI loads 3 trained PatchTST models
- ✅ PC queries VM's InfluxDB directly (no forwarding needed)

---

## 🔄 System Architecture

```
┌─────────────────┐
│ Sensors         │ MQTT (1883)
│ (Your machines) │──────────────┐
└─────────────────┘              │
                                 ▼
                    ┌────────────────────────┐
                    │ VM (142.93.220.152)    │
                    ├────────────────────────┤
                    │ • Mosquitto MQTT       │
                    │ • InfluxDB (8086)      │
                    │ • Telegraf (optional)  │
                    └────────────────────────┘
                                 ▲
                                 │ Query InfluxDB API
                                 │
                    ┌────────────────────────┐
                    │ Your PC                │
                    ├────────────────────────┤
                    │ • Spark (training)     │
                    │ • FastAPI (inference)  │
                    │ • 3 PatchTST models    │
                    └────────────────────────┘
                                 │
                                 │ Cloudflare Tunnel
                                 ▼
                    ┌────────────────────────┐
                    │ Public Internet        │
                    │ https://xyz.tryclou... │
                    └────────────────────────┘
```

---

## 📊 Start PC Services (Your Local Machine)

### 1. Start Docker Services (Spark + InfluxDB + MQTT)

```powershell
# Navigate to IOT directory
cd C:\Users\Asus\Desktop\IOT

# Start services
docker-compose up -d
```

### 2. Start FastAPI Inference Server

```powershell
# Navigate to FYP directory
cd C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction

# Activate virtual environment (if you have one)
# .\venv\Scripts\Activate.ps1

# Start API
python main.py
```

Server runs on: `http://localhost:8000`

### 3. (Optional) Start Cloudflare Tunnel for Public Access

```powershell
# In another terminal
& "$env:USERPROFILE\cloudflared.exe" tunnel --url http://localhost:8000
```

You'll get a public URL like: `https://abc-xyz-123.trycloudflare.com`

---

## 🎯 Test Complete System

### 1. Send sensor data to VM

```bash
# From any device on network
mosquitto_pub -h 142.93.220.152 -t machine_sensor_data -m '{"workspace_id":"lathe-1-spindle","current":18.5,"accX":0.0023,"accY":-0.0012,"accZ":0.9987,"tempA":67.3,"tempB":65.8}'
```

### 2. Check FastAPI detects data

```powershell
# On PC, check workspaces endpoint
curl http://localhost:8000/workspaces
```

Should return:
```json
{
  "workspaces": ["lathe-1-spindle", "cnc-mill-5-axis", "robot-arm-02"],
  "total": 3
}
```

### 3. Get predictions

```powershell
# Get latest predictions for a workspace
curl http://localhost:8000/predict/lathe-1-spindle
```

Returns 10-step ahead predictions with anomaly scores.

---

## 🛠️ Useful Commands

### On VM:

```bash
# Check service status
docker ps

# View logs
docker logs vm-mosquitto
docker logs vm-influxdb
docker logs vm-telegraf

# Monitor resource usage
docker stats --no-stream

# Restart services
cd /root/IOT/vm-deployment
docker-compose -f docker-compose-vm.yml restart

# Stop services
docker-compose -f docker-compose-vm.yml stop

# Start services
docker-compose -f docker-compose-vm.yml up -d

# Remove everything
docker-compose -f docker-compose-vm.yml down -v
```

### On PC:

```powershell
# Check Docker services
docker ps

# Check Spark UI
start http://localhost:8080

# Check InfluxDB UI (local)
start http://localhost:8086

# Check FastAPI docs
start http://localhost:8000/docs

# Test VM connection
curl http://142.93.220.152:8086/health
```

---

## 🔍 Troubleshooting

### VM: Services won't start

```bash
# Check Docker is running
sudo systemctl status docker
sudo systemctl start docker

# Check memory
free -h

# If memory too low, enable swap
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### VM: Ports already in use

```bash
# Find what's using port 1883
sudo lsof -i :1883
sudo lsof -i :8086

# Kill process if needed
sudo kill -9 <PID>
```

### VM: Can't connect from PC

```bash
# Check firewall on VM
sudo ufw status
sudo ufw allow 1883/tcp
sudo ufw allow 8086/tcp
sudo ufw allow 9001/tcp

# Test from VM locally first
curl http://localhost:8086/health
```

### PC: Can't query VM InfluxDB

```powershell
# Check .env file
cat C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction\.env

# Should show:
# INFLUX_URL=http://142.93.220.152:8086

# Test connection
curl http://142.93.220.152:8086/health

# Check if VM firewall blocking
ping 142.93.220.152
```

### PC: FastAPI not loading models

```powershell
# Check models exist
ls C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction\FYP-Machine-Condition-Prediction\models\

# Should show 3 files:
# - lathe-1-spindle_patchtst_model.pkl
# - cnc-mill-5-axis_patchtst_model.pkl
# - robot-arm-02_patchtst_model.pkl

# Check logs when starting
python main.py
# Look for: "Loaded model for lathe-1-spindle"
```

---

## 🎉 Success Checklist

- [ ] VM services running (3 containers)
- [ ] Sensors sending to 142.93.220.152:1883
- [ ] MQTT receiving messages on VM
- [ ] Data visible in InfluxDB on VM
- [ ] PC can query VM InfluxDB (curl test passes)
- [ ] PC Docker services running (Spark, etc.)
- [ ] FastAPI running on PC with 3 models loaded
- [ ] FastAPI can read data from VM
- [ ] Predictions endpoint returns results
- [ ] (Optional) Cloudflare Tunnel providing public access

---

## 📝 Configuration Summary

### VM (142.93.220.152)
- **Role:** Receive sensor data, store in InfluxDB
- **Services:** MQTT (1883), InfluxDB (8086), Telegraf (optional)
- **RAM Usage:** ~380MB
- **Repo Location:** `/root/IOT`
- **Config Location:** `/opt/iot-vm/`

### Your PC
- **Role:** Query VM data, train models, run inference API
- **Services:** Spark cluster, FastAPI, (local InfluxDB + MQTT for testing)
- **InfluxDB URL:** `http://142.93.220.152:8086` (points to VM)
- **API Port:** 8000
- **Repo Location:** `C:\Users\Asus\Desktop\IOT`

---

## 🔐 Security Notes (Production)

Before going to production:

1. **Change default InfluxDB password** in `docker-compose-vm.yml`
2. **Enable MQTT authentication:**
   ```bash
   # On VM
   docker exec vm-mosquitto mosquitto_passwd -c /mosquitto/config/passwd your_username
   # Update mosquitto.conf: allow_anonymous false
   ```
3. **Use SSL/TLS certificates** for MQTT and InfluxDB
4. **Restrict InfluxDB access** with firewall rules (only from your PC IP)
5. **Use environment variables** instead of hardcoded tokens
6. **Regular backups** of InfluxDB data

---

## 📚 Additional Resources

- **VM Setup Guide:** `README.md` in vm-deployment folder
- **Tailscale VPN Guide:** `setup-tailscale.md` (if PC IP changes)
- **Upload Guide:** `UPLOAD-GUIDE.md` (alternative to git clone)
- **FastAPI Docs:** http://localhost:8000/docs (when running)
- **Cloudflare Tunnel:** https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/

---

**Questions?** Check the README files or run `docker logs <container_name>` to see what's happening.
