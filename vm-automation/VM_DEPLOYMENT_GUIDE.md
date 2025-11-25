# VM Deployment Guide - MQTT Bridge Automation

## 📦 Files for VM (Ubuntu)

Upload these files to your VM at `/root/IOT/` or your project directory:

1. **mqtt_to_influx_bridge_vm.py** (your existing bridge script)
2. **start_mqtt_bridge_vm.sh** (manual auto-restart script)
3. **mqtt-bridge.service** (systemd service file)
4. **install_mqtt_bridge_service_vm.sh** (automated installer)
5. **mqtt_bridge_control_vm.sh** (control panel)

---

## 🚀 Quick Setup on VM (3 Steps)

### **Step 1: Upload Files to VM**

From your Windows PC:
```powershell
# Option A: Using SCP
scp C:\Users\Asus\Desktop\IOT\*.sh root@142.93.220.152:/root/IOT/
scp C:\Users\Asus\Desktop\IOT\mqtt-bridge.service root@142.93.220.152:/root/IOT/

# Option B: Using WinSCP (GUI)
# Drag and drop files to /root/IOT/
```

### **Step 2: SSH to VM**
```bash
ssh root@142.93.220.152
cd /root/IOT
```

### **Step 3: Install Service**
```bash
# Make scripts executable
chmod +x *.sh

# Run installer (as root)
sudo bash install_mqtt_bridge_service_vm.sh
```

**Done!** Bridge now runs automatically on VM boot 🎉

---

## 📋 Manual Control Options

### **Option 1: Control Panel (Easiest)**
```bash
bash mqtt_bridge_control_vm.sh
```
Interactive menu with:
- Start/Stop/Restart
- Install service
- View status and logs
- Enable/Disable auto-start

### **Option 2: Direct Commands**
```bash
# Start service
sudo systemctl start mqtt-bridge

# Stop service
sudo systemctl stop mqtt-bridge

# Restart service
sudo systemctl restart mqtt-bridge

# View status
sudo systemctl status mqtt-bridge

# View real-time logs
sudo journalctl -u mqtt-bridge -f

# View last 50 log entries
sudo journalctl -u mqtt-bridge -n 50

# Disable auto-start
sudo systemctl disable mqtt-bridge

# Enable auto-start
sudo systemctl enable mqtt-bridge
```

### **Option 3: Manual Script (No Service)**
```bash
# Run in foreground (visible)
python3 mqtt_to_influx_bridge_vm.py

# Run with auto-restart
bash start_mqtt_bridge_vm.sh

# Run in background
nohup bash start_mqtt_bridge_vm.sh > mqtt_bridge.log 2>&1 &
```

---

## ✅ Verification

### **Check if service is running:**
```bash
sudo systemctl status mqtt-bridge
```

Expected output:
```
● mqtt-bridge.service - MQTT to InfluxDB Bridge Service
   Loaded: loaded (/etc/systemd/system/mqtt-bridge.service; enabled)
   Active: active (running) since Mon 2025-11-25 08:00:00 UTC
   Main PID: 12345 (python3)
```

### **Check logs:**
```bash
sudo journalctl -u mqtt-bridge -f
```

You should see:
```
✅ Connected to MQTT broker at localhost:1883
✅ Connected to InfluxDB at http://localhost:8086
📊 Data bridge active - listening for sensor data
```

### **Test data flow:**
```bash
# Publish test message
mosquitto_pub -h localhost -t sensor/data -m '{"workspace_id":"test","current":12.5,"tempA":45.0}'

# Check InfluxDB
curl -XPOST 'http://localhost:8086/api/v2/query?org=Ruhuna_Eng' \
  -H 'Authorization: Token YOUR_TOKEN' \
  -d 'from(bucket:"New_Sensor")|>range(start:-1h)'
```

---

## 🔧 Troubleshooting

### **Service won't start:**
```bash
# Check for errors
sudo journalctl -u mqtt-bridge -n 50

# Check Python dependencies
python3 mqtt_to_influx_bridge_vm.py

# Check if ports are available
sudo netstat -tulpn | grep -E ':(1883|8086)'
```

### **MQTT connection fails:**
```bash
# Check MQTT broker
sudo docker ps | grep mosquitto

# Restart MQTT broker
sudo docker restart <mosquitto-container-id>

# Test MQTT connection
mosquitto_sub -h localhost -t sensor/# -v
```

### **InfluxDB connection fails:**
```bash
# Check InfluxDB
sudo docker ps | grep influxdb

# Check InfluxDB logs
sudo docker logs <influxdb-container-id>

# Test InfluxDB API
curl http://localhost:8086/health
```

---

## 📊 System Resource Usage

The service is configured with limits:
- **Memory**: Max 512MB
- **CPU**: Max 50%

Adjust in service file if needed:
```bash
sudo nano /etc/systemd/system/mqtt-bridge.service
# Edit MemoryLimit and CPUQuota
sudo systemctl daemon-reload
sudo systemctl restart mqtt-bridge
```

---

## 🔄 Update Bridge Script

When you update `mqtt_to_influx_bridge_vm.py`:
```bash
# Upload new version
scp mqtt_to_influx_bridge_vm.py root@142.93.220.152:/root/IOT/

# Restart service
ssh root@142.93.220.152 "systemctl restart mqtt-bridge"
```

---

## 🗑️ Uninstall

```bash
# Stop and disable service
sudo systemctl stop mqtt-bridge
sudo systemctl disable mqtt-bridge

# Remove service file
sudo rm /etc/systemd/system/mqtt-bridge.service

# Reload systemd
sudo systemctl daemon-reload
```

---

## 🎯 Summary

**On VM (Ubuntu):**
- ✅ Systemd service for auto-start on boot
- ✅ Auto-restart on crash
- ✅ Centralized logging via journalctl
- ✅ Standard Linux service management

**On Windows PC:**
- ✅ Task Scheduler service for auto-start
- ✅ Background execution
- ✅ Easy control panel

**Both systems now fully automated!** 🚀
