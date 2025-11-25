# IOT System - VM Deployment Guide
# For receiving sensor data on VM: 142.93.220.152

## Architecture Overview

```
Real Sensors → VM (142.93.220.152) → PC (Training & Inference)
                [MQTT + InfluxDB]      [Spark + FastAPI + Tunnel]
                [~380MB RAM]           [Full Resources]
```

## Components on VM

| Service | RAM | Purpose |
|---------|-----|---------|
| Mosquitto MQTT | 50 MB | Receive sensor data |
| InfluxDB | 256 MB | Store time-series data |
| Telegraf | 50 MB | Forward data to PC |
| **Total** | **~380 MB** | Fits in 485 MB available |

## Components on PC

| Service | RAM | Purpose |
|---------|-----|---------|
| Spark Cluster | 4 GB | Model training |
| FastAPI | 1.5 GB | Inference API |
| Cloudflare Tunnel | 50 MB | Public access |

---

## Step 1: Deploy to VM

### Upload Files to VM

```bash
# From your PC
scp -r vm-deployment/* root@142.93.220.152:/root/iot-vm/
```

### Run Deployment Script

```bash
# SSH to VM
ssh root@142.93.220.152

# Navigate to directory
cd /root/iot-vm

# Make script executable
chmod +x deploy-vm.sh

# Run deployment
sudo ./deploy-vm.sh
```

### Update Telegraf Configuration

**IMPORTANT:** Since your PC's IP changes frequently, use one of these solutions:

#### Option A: Tailscale VPN (Recommended - Permanent IP) ⭐

```bash
# Install Tailscale on VM
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Install on PC: https://tailscale.com/download/windows
# Get PC's Tailscale IP (e.g., 100.64.0.1)

# Edit telegraf.conf on VM
nano /opt/iot-vm/telegraf.conf

# Use PC's Tailscale IP (never changes!)
urls = ["http://100.64.0.1:8086"]

# Restart telegraf
docker restart vm-telegraf
```

**See `setup-tailscale.md` for detailed instructions**

#### Option B: Dynamic DNS (Free with No-IP/DuckDNS)

```bash
# On PC, install Dynamic DNS client
# Your PC gets permanent hostname: mypc.ddns.net

# Edit telegraf.conf
urls = ["http://mypc.ddns.net:8086"]
```

#### Option C: Query VM from PC (Simplest)

```bash
# Don't forward data - let PC query VM instead
# VM has static IP: 142.93.220.152

# On PC, edit .env file:
INFLUX_URL=http://142.93.220.152:8086

# No Telegraf forwarding needed!
```

---

## Step 2: Configure PC to Accept Data

**Since PC IP changes frequently, choose the best option:**

### Option A: Tailscale VPN (Best Solution) ⭐

**Gives permanent IPs - works even when PC IP changes!**

```powershell
# On PC - Download and install
# https://tailscale.com/download/windows

# Get your Tailscale IP
tailscale ip -4
# Example: 100.64.0.1

# Allow InfluxDB through firewall
New-NetFirewallRule -DisplayName "InfluxDB-Tailscale" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8086 `
  -Action Allow
```

Then use `100.64.0.1` in VM's telegraf.conf - **this IP never changes!**

### Option B: PC Queries VM Directly (Simplest)

**Don't forward data - PC pulls from VM instead**

```powershell
# On PC, edit FYP-Machine-Condition-Prediction/.env
INFLUX_URL=http://142.93.220.152:8086

# VM has static IP, so no issues!
# PC queries VM's InfluxDB for training/inference
```

### Option C: Open InfluxDB Port (If on Same Network)

Only if PC and VM are on same local network:

```powershell
# Allow InfluxDB port in Windows Firewall
New-NetFirewallRule -DisplayName "InfluxDB" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8086 `
  -Action Allow

# Use PC's local IP (e.g., 192.168.1.100)
# Must update telegraf.conf whenever PC IP changes
```

---

## Step 3: Configure Sensors

### MQTT Configuration

**Broker:** `142.93.220.152`
**Port:** `1883`
**Topic:** `machine_sensor_data`

### Data Format (JSON)

```json
{
  "workspace_id": "lathe-1-spindle",
  "sensor_type": "industrial",
  "current": 18.45,
  "accX": 0.0023,
  "accY": -0.0012,
  "accZ": 0.9987,
  "tempA": 67.3,
  "tempB": 65.8,
  "timestamp": 1732502400
}
```

---

## Step 4: Verify Data Flow

### On VM

```bash
# Check MQTT messages
docker exec vm-mosquitto mosquitto_sub -t machine_sensor_data -v

# Check InfluxDB data
docker exec vm-influxdb influx query 'from(bucket:"New_Sensor") |> range(start: -10m) |> limit(n:5)'

# Check container logs
docker logs vm-mosquitto
docker logs vm-influxdb
docker logs vm-telegraf
```

### On PC

```powershell
# Check if data arriving from VM
docker exec influxdb influx query 'from(bucket:"iot_data") |> range(start: -10m) |> limit(n:5)'
```

---

## Step 5: Training & Inference on PC

### Keep Existing PC Setup

Your PC already has everything configured:
- ✅ Spark cluster for training
- ✅ FastAPI inference service
- ✅ Trained models

Just update the InfluxDB source:

```bash
# PC will query local InfluxDB (which receives data from VM via Telegraf)
# No changes needed if Telegraf is forwarding data
```

---

## Monitoring

### VM Resource Usage

```bash
# Check memory
free -h

# Check Docker stats
docker stats

# Check disk space
df -h
```

### VM Services Status

```bash
# Check all containers
docker ps

# Restart if needed
cd /opt/iot-vm
docker-compose -f docker-compose-vm.yml restart
```

---

## Troubleshooting

### VM Out of Memory

If VM runs out of memory, enable swap:

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Data Not Reaching PC

1. Check Telegraf logs: `docker logs vm-telegraf`
2. Verify PC's InfluxDB is accessible from VM
3. Test connection: `curl http://YOUR_PC_IP:8086/health`
4. Check firewall rules on both VM and PC

### MQTT Connection Failed

1. Check MQTT broker: `docker logs vm-mosquitto`
2. Test with mosquitto clients:
   ```bash
   mosquitto_pub -h 142.93.220.152 -t test -m "hello"
   mosquitto_sub -h 142.93.220.152 -t test
   ```
3. Verify port 1883 is open: `sudo ufw status`

---

## Security Recommendations

1. **Change default passwords** in docker-compose-vm.yml
2. **Enable MQTT authentication**:
   ```bash
   mosquitto_passwd -c /opt/iot-vm/passwords admin
   ```
3. **Use SSL/TLS** for MQTT and InfluxDB (Let's Encrypt)
4. **Restrict InfluxDB access** to Telegraf only
5. **Update telegraf.conf** with strong tokens

---

## Cost & Performance

### VM Usage
- Memory: ~380 MB (78% of available 485 MB)
- CPU: ~10-15% (mostly InfluxDB)
- Network: ~1 MB/min (sensor data)
- Disk: ~100 MB/day (data retention)

### Data Retention
- VM: Keep 7 days of data
- PC: Keep full history for training

---

## Summary

✅ **VM Role**: Sensor data receiver (MQTT + InfluxDB)
✅ **PC Role**: Training, inference, public API
✅ **Connection**: VM forwards data to PC via Telegraf
✅ **Public Access**: Cloudflare Tunnel on PC
✅ **Resource Fit**: VM services use ~380 MB (fits in 485 MB)

This setup maximizes your VM's limited resources while keeping compute-heavy tasks on your powerful PC!
