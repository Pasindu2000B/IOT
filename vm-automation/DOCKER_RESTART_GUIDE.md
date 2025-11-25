# Docker Auto-Restart Configuration Guide

## Overview
This guide explains how to configure Docker containers on the VM to automatically restart on crashes and VM reboots.

## Files
- `setup_docker_restart.sh` - Automated setup script for all containers

## Quick Setup

### Option 1: Use Setup Script (Recommended)

**1. Upload script to VM:**
```bash
scp C:\Users\Asus\Desktop\IOT\vm-automation\setup_docker_restart.sh root@142.93.220.152:/root/
```

**2. SSH to VM:**
```bash
ssh root@142.93.220.152
```

**3. Run setup:**
```bash
cd /root
chmod +x setup_docker_restart.sh
sudo bash setup_docker_restart.sh
```

The script will automatically set `restart=unless-stopped` for all containers.

---

### Option 2: Manual Commands

**1. SSH to VM:**
```bash
ssh root@142.93.220.152
```

**2. List all containers:**
```bash
docker ps -a
```

**3. Set restart policy for each container:**

Replace `<container-name-or-id>` with your actual container names:

```bash
# MQTT Broker (Mosquitto)
docker update --restart=unless-stopped <mqtt-container>

# InfluxDB
docker update --restart=unless-stopped <influxdb-container>

# Telegraf
docker update --restart=unless-stopped <telegraf-container>

# Any other containers
docker update --restart=unless-stopped <other-container>
```

**Example with typical container names:**
```bash
docker update --restart=unless-stopped mosquitto
docker update --restart=unless-stopped influxdb
docker update --restart=unless-stopped telegraf
```

**Or update ALL containers at once:**
```bash
docker ps -aq | xargs docker update --restart=unless-stopped
```

---

## Verification

**Check restart policies:**
```bash
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.RestartPolicy}}"
```

You should see `unless-stopped` for all containers.

**Inspect specific container:**
```bash
docker inspect <container-name> | grep -A 3 RestartPolicy
```

---

## Restart Policy Options

| Policy | Description |
|--------|-------------|
| `no` | Never restart (default) |
| `always` | Always restart, even if manually stopped |
| `unless-stopped` | Always restart, UNLESS manually stopped ✅ |
| `on-failure[:max-retries]` | Only restart on crash |

**Recommended:** `unless-stopped` - Best balance of automation and control.

---

## Testing

**1. Test crash recovery:**
```bash
# Kill a container process
docker kill <container-name>

# Wait 5 seconds
sleep 5

# Check if it restarted
docker ps | grep <container-name>
```

**2. Test VM reboot:**
```bash
# Reboot VM
sudo reboot

# After reboot, SSH back and check
ssh root@142.93.220.152
docker ps -a
```

All containers should be running automatically.

---

## Troubleshooting

**Container not restarting:**
```bash
# Check logs
docker logs <container-name>

# Check restart count
docker inspect <container-name> | grep RestartCount

# Manually start
docker start <container-name>
```

**View restart history:**
```bash
docker events --filter 'event=restart' --since 1h
```

**Reset restart policy:**
```bash
docker update --restart=no <container-name>
```

---

## Docker Compose Alternative

If you're using `docker-compose.yml`, add to each service:

```yaml
services:
  mosquitto:
    restart: unless-stopped
    # ... other config
  
  influxdb:
    restart: unless-stopped
    # ... other config
  
  telegraf:
    restart: unless-stopped
    # ... other config
```

Then restart compose:
```bash
docker-compose down
docker-compose up -d
```

---

## Summary

✅ **After setup:**
- Containers survive crashes (auto-restart)
- Containers survive VM reboots (auto-start)
- Manual stops are respected (won't restart if you stop them)

🔧 **Maintenance:**
- No ongoing maintenance required
- Policies persist across container updates
- Check policies after recreating containers
