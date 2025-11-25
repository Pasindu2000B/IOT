# Tailscale Setup - Permanent IP Solution
# Solves the problem of PC IP changing frequently

## Why Tailscale?

❌ **Problem:** Your PC's IP address changes (DHCP, different networks, ISP changes)
✅ **Solution:** Tailscale gives you a permanent IP (e.g., `100.64.0.1`) that never changes

## Benefits

- 🔒 **Secure:** Encrypted VPN tunnel (WireGuard)
- 🆓 **Free:** Up to 100 devices
- 🌐 **Works Everywhere:** PC can be anywhere (home, office, cafe)
- 🚀 **Fast:** Direct peer-to-peer connection
- 📱 **Cross-Platform:** Windows, Linux, Mac, mobile

---

## Step 1: Install on Windows PC

### Download & Install

1. Go to: https://tailscale.com/download/windows
2. Download and install Tailscale
3. Sign in with Google/GitHub/Microsoft account
4. Note your Tailscale IP (shown in system tray icon)

### PowerShell Commands

```powershell
# Check your Tailscale IP
tailscale ip -4

# Example output: 100.64.0.1
```

### Allow InfluxDB Through Firewall

```powershell
# Allow InfluxDB on Tailscale interface
New-NetFirewallRule -DisplayName "InfluxDB-Tailscale" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8086 `
  -Action Allow `
  -Profile Any
```

---

## Step 2: Install on VM (Ubuntu/Linux)

### SSH to VM

```bash
ssh root@142.93.220.152
```

### Install Tailscale

```bash
# Install
curl -fsSL https://tailscale.com/install.sh | sh

# Start and authenticate
sudo tailscale up

# Get VM's Tailscale IP
tailscale ip -4
# Example output: 100.64.0.2
```

---

## Step 3: Test Connection

### From VM to PC

```bash
# Test if VM can reach PC's InfluxDB via Tailscale
curl http://100.64.0.1:8086/health

# Should return: {"name":"influxdb","message":"ready for queries and writes","status":"pass"}
```

### From PC to VM

```powershell
# Test if PC can reach VM's MQTT via Tailscale
curl http://100.64.0.2:1883
```

---

## Step 4: Update Telegraf Configuration

### On VM

```bash
# Edit telegraf.conf
nano /opt/iot-vm/telegraf.conf

# Change to your PC's Tailscale IP
urls = ["http://100.64.0.1:8086"]  # Replace with actual Tailscale IP

# Restart Telegraf
docker restart vm-telegraf

# Check logs
docker logs -f vm-telegraf
```

---

## Step 5: Update PC's InfluxDB URL

### In FYP-Machine-Condition-Prediction/.env

```bash
# If you want PC to query VM's InfluxDB instead
INFLUX_URL=http://100.64.0.2:8086  # VM's Tailscale IP
```

---

## Architecture with Tailscale

```
┌─────────────────────────────────────────┐
│  Real Sensors                            │
│  Send to: 142.93.220.152:1883          │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  VM (142.93.220.152)                    │
│  Tailscale IP: 100.64.0.2               │
│  ┌─────────┐  ┌──────────┐             │
│  │  MQTT   │→→│ InfluxDB │             │
│  └─────────┘  └────┬─────┘             │
└────────────────────┼─────────────────────┘
                     ↓ Telegraf forwards via Tailscale
┌─────────────────────────────────────────┐
│  PC (Your Computer)                     │
│  Tailscale IP: 100.64.0.1 (permanent!) │
│  ┌──────────┐  ┌───────┐  ┌─────────┐ │
│  │ InfluxDB │  │ Spark │  │ FastAPI │ │
│  └──────────┘  └───────┘  └─────────┘ │
└─────────────────────────────────────────┘
```

---

## Troubleshooting

### Can't Reach PC from VM

```bash
# On VM
ping 100.64.0.1

# Check Tailscale status
sudo tailscale status

# Check if PC is online
tailscale ping 100.64.0.1
```

### Firewall Blocking Connection

```powershell
# On PC - Allow all Tailscale traffic
New-NetFirewallRule -DisplayName "Tailscale-Allow-All" `
  -Direction Inbound `
  -InterfaceAlias "Tailscale" `
  -Action Allow
```

### Check Telegraf Connection

```bash
# On VM
docker logs vm-telegraf | grep -i error

# Test InfluxDB write
curl -X POST "http://100.64.0.1:8086/api/v2/write?org=Ruhuna_Eng&bucket=New_Sensor" \
  -H "Authorization: Token GO7pQ79-Vo-k6uwpQrMmJmITzLRHxyrFbFDrnRbz8PgZbLHKe5hpwNZCWi6Z_zolPRjn7jUQ6irQk-BPe3LK9Q==" \
  -d "test,location=vm value=1"
```

---

## Alternative: Use VM as Primary Storage

If you prefer, you can **keep all data on VM** and have PC query it:

### Benefits
- No data forwarding needed
- VM is always online (stable IP: 142.93.220.152)
- PC only used for training/inference

### Setup

1. **Don't use Telegraf forwarding**
2. **Update PC to query VM's InfluxDB:**

```powershell
# Edit .env on PC
INFLUX_URL=http://100.64.0.2:8086  # VM's Tailscale IP
```

3. **Or expose VM's InfluxDB publicly:**

```bash
# On VM - allow port 8086 from anywhere
sudo ufw allow 8086/tcp

# Use public IP on PC
INFLUX_URL=http://142.93.220.152:8086
```

---

## Summary

✅ **Install Tailscale on both PC and VM**
✅ **Use Tailscale IPs (100.x.x.x) - permanent!**
✅ **Update telegraf.conf with PC's Tailscale IP**
✅ **No more IP change issues!**

**Tailscale IPs never change, even if:**
- PC changes networks (WiFi, Ethernet)
- PC gets new DHCP IP
- PC uses mobile hotspot
- ISP changes public IP

This is the **recommended solution** for your setup! 🎯
