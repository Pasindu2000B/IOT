# IOT Predictive Maintenance System - Hybrid Deployment Architecture

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL PC (Main System)                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐  ┌──────────────────┐                 │
│  │  GenerateData   │→→│  MQTT Broker     │                 │
│  │  (3 machines)   │  │  (port 1883)     │                 │
│  └─────────────────┘  └────────┬─────────┘                 │
│                                 ↓                            │
│                      ┌──────────────────┐                   │
│                      │  MQTT Bridge     │                   │
│                      └────────┬─────────┘                   │
│                               ↓                              │
│                      ┌──────────────────┐                   │
│                      │  InfluxDB        │                   │
│                      │  (time-series)   │                   │
│                      └────────┬─────────┘                   │
│                               ↓                              │
│  ┌──────────────────────────────────────┐                  │
│  │  Spark Cluster (Training)            │                  │
│  │  • Master + 2 Workers (4 cores)      │                  │
│  │  • Monthly PatchTST model training   │                  │
│  │  • Output: 3 models + scalers        │                  │
│  └──────────────────┬───────────────────┘                  │
│                     ↓                                        │
│  ┌──────────────────────────────────────┐                  │
│  │  FastAPI Inference Service           │                  │
│  │  • Port: 8000                        │                  │
│  │  • 3 PatchTST models loaded          │                  │
│  │  • Polls InfluxDB every 60s          │                  │
│  │  • 10-step ahead predictions         │                  │
│  └──────────────────┬───────────────────┘                  │
│                     ↓                                        │
└─────────────────────┼───────────────────────────────────────┘
                      ↓
         ┌────────────────────────┐
         │  Cloudflare Tunnel     │
         │  (Secure HTTPS)        │
         └────────────┬───────────┘
                      ↓
              ════════════════════
                   INTERNET
              ════════════════════
                      ↓
         ┌────────────────────────┐
         │  Public HTTPS URL      │
         │  https://xyz.trycloudflare.com │
         └────────────────────────┘
                      ↓
         ┌────────────────────────┐
         │  External Clients      │
         │  • Web dashboards      │
         │  • Mobile apps         │
         │  • Monitoring systems  │
         └────────────────────────┘
```

## Why This Architecture?

### VM Resource Constraints
- **Available RAM**: 485 MB (only 12.7% of 3.8 GB total)
- **Minimum Required**: ~2 GB for even minimal deployment
- **Risk**: High probability of OOM (Out of Memory) kills

### Solution: Hybrid Deployment
- **Keep everything on PC** where resources are adequate
- **Expose via tunnel** for internet access
- **No VM changes needed** - avoid resource issues entirely

## Components Running on Local PC

| Component | Port | RAM Usage | CPU Cores | Status |
|-----------|------|-----------|-----------|--------|
| InfluxDB | 8086 | ~500 MB | 1 | Running |
| MQTT Broker | 1883 | ~50 MB | 0.5 | Running |
| Spark Master | 7077, 8080 | ~500 MB | 1 | Running |
| Spark Workers (×2) | - | ~2 GB | 2 each | Running |
| Data Generator | - | ~50 MB | 0.2 | Running |
| MQTT Bridge | - | ~50 MB | 0.2 | Running |
| FastAPI Inference | 8000 | ~1.5 GB | 1 | Running |
| **TOTAL** | - | **~4.65 GB** | **7.1 cores** | ✅ Working |

## Cloudflare Tunnel Configuration

### What It Does
- Creates secure HTTPS tunnel from your PC to Cloudflare's network
- Provides public URL (e.g., `https://xyz.trycloudflare.com`)
- No port forwarding or firewall changes needed
- No router configuration required
- Free tier available

### How It Works
1. **cloudflared** runs on your PC
2. Connects to Cloudflare's edge network via outbound HTTPS
3. Routes all incoming traffic to `localhost:8000`
4. Provides TLS/SSL encryption automatically

## Quick Start

### 1. Start All Local Services

```powershell
# Ensure Docker containers are running
docker ps

# Ensure data generation is active
# (Should have 2 Python processes running GenerateData.py)

# Ensure MQTT bridge is running
# (Should see [OK] messages in logs)

# Start FastAPI inference service
cd C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction
python -m uvicorn main:app --reload --port 8000
```

### 2. Setup Tunnel

```powershell
# Run the automated setup script
cd C:\Users\Asus\Desktop\IOT
.\setup-tunnel.ps1
```

This will:
- Download cloudflared (if needed)
- Authenticate with Cloudflare
- Create tunnel named "iot-predictive-maintenance"

### 3. Start Tunnel

```powershell
# Quick tunnel (gets random URL, good for testing)
$env:USERPROFILE\cloudflared.exe tunnel --url http://localhost:8000
```

Output will show your public URL:
```
+--------------------------------------------------------------------------------------------+
|  Your quick tunnel has been created! Visit it at (it may take some time to be reachable): |
|  https://abc-def-ghi.trycloudflare.com                                                     |
+--------------------------------------------------------------------------------------------+
```

### 4. Test Public API

```powershell
# Replace YOUR-TUNNEL-URL with actual URL from step 3

# Get service info
curl https://YOUR-TUNNEL-URL/

# List available models
curl https://YOUR-TUNNEL-URL/workspaces

# Get inference status
curl https://YOUR-TUNNEL-URL/inference/status

# Get predictions for specific workspace
curl https://YOUR-TUNNEL-URL/predict/cnc-mill-5-axis
```

## API Endpoints (Now Public)

| Endpoint | Method | Description | Example Response |
|----------|--------|-------------|------------------|
| `/` | GET | Service info | `{"service": "IOT Inference", "status": "running"}` |
| `/workspaces` | GET | List loaded models | `["cnc-mill-5-axis", "lathe-1-spindle", "robot-arm-02"]` |
| `/inference/status` | GET | Streaming status | `{"interval_seconds": 60, "lookback_minutes": 10}` |
| `/predict/{workspace_id}` | GET | Get predictions | JSON with 10-step forecast for 6 features |

## Permanent Tunnel Setup (Optional)

For production use, configure tunnel to run as Windows service:

### 1. Create Configuration File

Create `C:\Users\Asus\.cloudflared\config.yml`:

```yaml
tunnel: iot-predictive-maintenance
credentials-file: C:\Users\Asus\.cloudflared\<TUNNEL-ID>.json

ingress:
  - hostname: iot-api.yourdomain.com  # Your custom domain
    service: http://localhost:8000
  - service: http_status:404
```

### 2. Route Domain (If Using Custom Domain)

```powershell
$env:USERPROFILE\cloudflared.exe tunnel route dns iot-predictive-maintenance iot-api.yourdomain.com
```

### 3. Install as Windows Service

```powershell
$env:USERPROFILE\cloudflared.exe service install
$env:USERPROFILE\cloudflared.exe service start
```

### 4. Verify Service

```powershell
Get-Service cloudflared
```

## Monthly Model Training Workflow

### 1. Train New Models (Local PC)

```powershell
# Submit training job to Spark cluster
docker exec spark-master /opt/spark/bin/spark-submit `
  --master spark://spark-master:7077 `
  --conf spark.executor.memory=2g `
  --conf spark.driver.memory=1g `
  /opt/spark-apps/train_distributed.py
```

Training output: `spark-apps/models/model_*_YYYYMMDD_HHMMSS/`

### 2. Restart Inference Service

```powershell
# Stop current inference
# (Press Ctrl+C in terminal running uvicorn)

# Start with new models
cd C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction
python -m uvicorn main:app --reload --port 8000
```

Service automatically loads latest models on startup.

### 3. Verify New Models Loaded

```powershell
curl http://localhost:8000/workspaces
# Should return updated model list
```

## Monitoring & Maintenance

### Check System Health

```powershell
# Docker containers status
docker ps

# InfluxDB data
docker exec influxdb influx query 'from(bucket:"iot_data") |> range(start: -10m) |> limit(n:5)'

# Spark cluster
# Visit: http://localhost:8080

# FastAPI logs
# Check terminal where uvicorn is running
```

### Resource Monitoring

```powershell
# CPU/Memory usage
docker stats --no-stream

# Disk usage
docker system df
```

### Logs Location

- **Docker containers**: `docker logs <container-name>`
- **FastAPI**: Terminal output where uvicorn runs
- **Cloudflare Tunnel**: Terminal output where cloudflared runs

## Troubleshooting

### Tunnel Connection Issues

**Problem**: Tunnel fails to connect

```powershell
# Check cloudflared version
$env:USERPROFILE\cloudflared.exe --version

# Test authentication
$env:USERPROFILE\cloudflared.exe tunnel list

# Test local API
curl http://localhost:8000/
```

### API Not Responding

**Problem**: 502 Bad Gateway on tunnel URL

```powershell
# Verify FastAPI running
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

# Check port 8000
netstat -ano | findstr :8000

# Restart API
cd C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction
python -m uvicorn main:app --reload --port 8000
```

### Model Not Found

**Problem**: "No active workspaces found"

```powershell
# Check model files exist
ls C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction\FYP-Machine-Condition-Prediction\model_*

# Verify InfluxDB has data
docker exec influxdb influx query 'from(bucket:"iot_data") |> range(start: -1h) |> count()'

# Ensure data generator running
Get-Process | Where-Object {$_.Path -like "*GenerateData.py*"}
```

### High CPU Usage

**Problem**: PC slowing down

```powershell
# Stop Spark workers if not training
docker stop spark-worker-1 spark-worker-2

# Reduce inference interval (edit real_influx_streamer.py)
# Change: interval_seconds=60 to interval_seconds=300

# Restart API
```

## Security Recommendations

### 1. API Authentication (Future)

Add API key authentication to FastAPI:

```python
# In main.py
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

@app.get("/predict/{workspace_id}")
async def predict(workspace_id: str, api_key: str = Depends(api_key_header)):
    if api_key != "your-secret-key":
        raise HTTPException(status_code=403)
    # ... rest of code
```

### 2. Rate Limiting

Use `slowapi` to prevent abuse:

```powershell
pip install slowapi
```

### 3. HTTPS Only

Cloudflare Tunnel provides HTTPS automatically, but enforce it:

```python
@app.middleware("http")
async def https_redirect(request: Request, call_next):
    if request.headers.get("x-forwarded-proto") == "http":
        return RedirectResponse(url=request.url.replace("http://", "https://"))
    return await call_next(request)
```

## Benefits of This Architecture

| Benefit | Description |
|---------|-------------|
| ✅ **No VM Changes** | Keep limited RAM VM as-is, no deployment needed |
| ✅ **Working System** | Everything already functional on PC |
| ✅ **Internet Access** | Public HTTPS URL via Cloudflare Tunnel |
| ✅ **Zero Config Firewall** | No port forwarding or router changes |
| ✅ **Free Tier** | Cloudflare Tunnel free for personal use |
| ✅ **Automatic HTTPS** | TLS/SSL encryption included |
| ✅ **Easy Maintenance** | Single location for updates (PC) |
| ✅ **Low Latency** | Direct access to local resources |
| ✅ **Scalable** | Can add more Spark workers on PC if needed |

## Next Steps

1. ✅ Run `setup-tunnel.ps1` to install cloudflared
2. ⏳ Start tunnel: `cloudflared tunnel --url http://localhost:8000`
3. ⏳ Test public API endpoints
4. ⏳ (Optional) Configure custom domain
5. ⏳ (Optional) Install tunnel as Windows service for auto-start
6. ⏳ (Optional) Add API authentication for production use

## Cost Comparison

| Approach | PC Resources | VM Resources | Internet | Monthly Cost |
|----------|--------------|--------------|----------|--------------|
| **Option 1** (VM Only) | Idle | 8GB RAM needed | Yes | ~$20-40 |
| **Option 3B** (Hybrid) | Running | 485MB OK | Yes | **$0** |

**Recommended**: Option 3B saves money and uses existing working system.
