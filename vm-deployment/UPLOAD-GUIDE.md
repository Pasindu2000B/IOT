# Quick Upload Guide for VM
# Transfer files to VM: 142.93.220.152

## Files to Upload

Upload these 6 files from `vm-deployment/` folder to VM:

```
vm-deployment/
├── docker-compose-vm.yml  (1.8 KB) - Container configuration
├── mosquitto.conf         (0.6 KB) - MQTT settings
├── telegraf.conf          (1.7 KB) - Data forwarding (optional)
├── deploy-vm.sh           (3.4 KB) - Auto-deployment script
├── README.md              (7.2 KB) - Setup instructions
└── setup-tailscale.md     (6.1 KB) - VPN guide (optional)
```

**Total Size:** ~21 KB

---

## Method 1: SCP (Recommended)

### From Windows PowerShell

```powershell
# Navigate to IOT directory
cd C:\Users\Asus\Desktop\IOT

# Upload all files at once
scp -r vm-deployment/* root@142.93.220.152:/opt/iot-vm/

# Enter VM password when prompted
```

### Individual Files (if needed)

```powershell
scp vm-deployment/docker-compose-vm.yml root@142.93.220.152:/opt/iot-vm/
scp vm-deployment/mosquitto.conf root@142.93.220.152:/opt/iot-vm/
scp vm-deployment/deploy-vm.sh root@142.93.220.152:/opt/iot-vm/
```

---

## Method 2: WinSCP (GUI)

1. Download WinSCP: https://winscp.net/download/WinSCP-Setup.exe
2. Install and open WinSCP
3. Connect to VM:
   - Host: `142.93.220.152`
   - Username: `root`
   - Password: `[your VM password]`
   - Port: `22`
4. Navigate to `/opt/iot-vm/` on VM (create if doesn't exist)
5. Drag and drop files from `C:\Users\Asus\Desktop\IOT\vm-deployment\`

---

## Method 3: Git Clone (If Using GitHub)

### On VM

```bash
ssh root@142.93.220.152

# Clone repository
git clone https://github.com/Pasindu2000B/IOT.git
cd IOT/vm-deployment

# Copy files to deployment location
mkdir -p /opt/iot-vm
cp -r * /opt/iot-vm/
```

---

## Method 4: Manual Copy-Paste

If SSH file transfer doesn't work:

```bash
# SSH to VM
ssh root@142.93.220.152

# Create directory
mkdir -p /opt/iot-vm
cd /opt/iot-vm

# Create files manually
nano docker-compose-vm.yml
# Copy content from your PC file, paste, save (Ctrl+X, Y, Enter)

nano mosquitto.conf
# Copy content, paste, save

nano deploy-vm.sh
# Copy content, paste, save
```

---

## After Upload - Verify Files

```bash
# SSH to VM
ssh root@142.93.220.152

# Check files exist
ls -lh /opt/iot-vm/

# Should show:
# docker-compose-vm.yml
# mosquitto.conf
# telegraf.conf
# deploy-vm.sh
# README.md
# setup-tailscale.md

# Make deploy script executable
chmod +x /opt/iot-vm/deploy-vm.sh
```

---

## Quick Upload Command

**Copy-paste this into PowerShell:**

```powershell
cd C:\Users\Asus\Desktop\IOT
scp -r vm-deployment/* root@142.93.220.152:/opt/iot-vm/
```

---

## What Gets Created on VM

After deployment, VM will have:

```
/opt/iot-vm/
├── docker-compose-vm.yml   # Your config
├── mosquitto.conf          # Your config
├── telegraf.conf           # Your config (optional)
├── deploy-vm.sh            # Your script
├── README.md               # Your docs
└── setup-tailscale.md      # Your docs

Docker Volumes (created automatically):
├── mosquitto-data/         # MQTT messages
├── mosquitto-log/          # MQTT logs
├── influxdb-data/          # Time-series data
└── influxdb-config/        # InfluxDB settings
```

---

## Deployment Steps (After Upload)

```bash
# SSH to VM
ssh root@142.93.220.152

# Navigate to directory
cd /opt/iot-vm

# Run deployment
sudo ./deploy-vm.sh

# Wait ~2 minutes for Docker containers to start

# Verify running
docker ps
```

**Expected output:**
- vm-mosquitto (running)
- vm-influxdb (running)
- vm-telegraf (running - optional)

---

## Test Connection

```bash
# Test MQTT
mosquitto_pub -h 142.93.220.152 -t test -m "hello"

# Test InfluxDB
curl http://142.93.220.152:8086/health

# Should return: {"status":"pass"}
```

---

## Firewall Ports to Open on VM

The deployment script opens these automatically, but verify:

```bash
sudo ufw status

# Should show:
# 1883/tcp  ALLOW  (MQTT)
# 8086/tcp  ALLOW  (InfluxDB)
# 9001/tcp  ALLOW  (MQTT WebSocket)
```

---

## Summary

✅ **Upload:** 6 files (~21 KB total)
✅ **Location:** `/opt/iot-vm/`
✅ **Method:** SCP, WinSCP, or Git clone
✅ **Deploy:** Run `./deploy-vm.sh`
✅ **Result:** MQTT + InfluxDB ready to receive sensor data

**Everything your sensors need is then on the VM!**
