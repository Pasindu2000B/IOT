# Deploy Dashboard to VM with Public Access

## 🎯 Goal
Host the FastAPI dashboard on VM (142.93.220.152) so anyone can access predictions via:
- `http://142.93.220.152` (Port 80)
- `http://142.93.220.152:8000`

## 📦 What Gets Deployed on VM

```
VM (142.93.220.152)
├── MQTT Broker (port 1883) - Receives sensor data
├── InfluxDB (port 8086) - Stores time-series data
├── Telegraf - MQTT → InfluxDB bridge
└── FastAPI Dashboard (port 80/8000) - PUBLIC ACCESS
    ├── 3 trained models (lathe, cnc, robot)
    ├── Real-time inference engine
    └── Interactive web UI
```

**Total RAM Usage:** ~900MB (Dashboard: 512MB + InfluxDB: 256MB + Others: ~150MB)

⚠️ **Your VM has 485MB available** - This deployment requires **more RAM**. Options:
1. Upgrade VM to 2GB RAM ($12/month on DigitalOcean)
2. Keep dashboard on PC + use Cloudflare Tunnel (free, already working)
3. Deploy to different server

---

## 🚀 Deployment Steps (If VM has enough RAM)

### Step 1: Prepare Files on PC

```powershell
# On your PC, navigate to IOT directory
cd C:\Users\Asus\Desktop\IOT

# Create a deployment package
New-Item -ItemType Directory -Force -Path "vm-deployment\app"

# Copy FastAPI files
Copy-Item "FYP-Machine-Condition-Prediction\main.py" "vm-deployment\app\"
Copy-Item "FYP-Machine-Condition-Prediction\services" "vm-deployment\app\" -Recurse
Copy-Item "FYP-Machine-Condition-Prediction\static" "vm-deployment\app\" -Recurse
Copy-Item "FYP-Machine-Condition-Prediction\.env" "vm-deployment\app\"

# Copy trained models (critical!)
Copy-Item "FYP-Machine-Condition-Prediction\FYP-Machine-Condition-Prediction\models\*.pkl" "vm-deployment\app\models\"
```

### Step 2: Upload to VM

```powershell
# Upload entire vm-deployment folder
scp -r vm-deployment\* root@142.93.220.152:/root/iot-dashboard/
```

### Step 3: Deploy on VM

```bash
# SSH to VM
ssh root@142.93.220.152

# Navigate to deployment directory
cd /root/iot-dashboard

# Make script executable
chmod +x deploy-dashboard.sh

# Run deployment
sudo ./deploy-dashboard.sh
```

The script will:
- ✅ Install Docker & Docker Compose
- ✅ Configure firewall (ports 80, 1883, 8086, 8000)
- ✅ Build dashboard container with models
- ✅ Start all services
- ✅ Show public access URLs

---

## 🌐 After Deployment

### Public URLs (Anyone can access):

```
http://142.93.220.152              → Dashboard UI
http://142.93.220.152:8000         → Dashboard UI (alt port)
http://142.93.220.152:8000/docs    → API Documentation

API Endpoints:
http://142.93.220.152:8000/workspaces
http://142.93.220.152:8000/predict/lathe-1-spindle
http://142.93.220.152:8000/predict/cnc-mill-5-axis
http://142.93.220.152:8000/predict/robot-arm-02
http://142.93.220.152:8000/inference/status
```

### Test Access:

```bash
# From anywhere in the world
curl http://142.93.220.152:8000/workspaces

# Or open in browser
firefox http://142.93.220.152
```

---

## 🔧 Service Management on VM

```bash
# View logs
docker-compose logs -f dashboard

# Restart dashboard
docker-compose restart dashboard

# Stop all services
docker-compose stop

# Start all services
docker-compose up -d

# View resource usage
docker stats --no-stream

# Check if running
docker ps
```

---

## ⚠️ RECOMMENDED APPROACH (VM RAM Constraint)

Since your VM only has **485MB RAM available** and this deployment needs **900MB**, I recommend:

### **Keep Current Architecture (Already Working!):**

1. **VM (142.93.220.152):** MQTT + InfluxDB (~380MB) ✅
2. **Your PC:** FastAPI Dashboard + Models + Spark
3. **Public Access:** Cloudflare Tunnel (free, no RAM needed)

### **To make dashboard publicly accessible:**

```powershell
# On your PC
cd C:\Users\Asus\Desktop\IOT
.\start-dashboard.ps1
```

This gives you a public URL like:
```
https://abc-xyz-123.trycloudflare.com
```

**Share this URL** - works from anywhere, no VM deployment needed!

---

## 🔄 Alternative: Custom Domain

If you want `http://142.93.220.152` to show the dashboard, use **nginx reverse proxy**:

### On VM (minimal RAM):

```bash
# Install nginx (only ~10MB RAM)
apt install nginx

# Configure nginx as proxy to your PC
cat > /etc/nginx/sites-available/dashboard << 'EOF'
server {
    listen 80;
    server_name 142.93.220.152;
    
    location / {
        proxy_pass https://YOUR-CLOUDFLARE-TUNNEL-URL.trycloudflare.com;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

Now `http://142.93.220.152` shows your dashboard without deploying FastAPI on VM!

---

## 📊 RAM Comparison

| Option | VM RAM Used | PC Requirement | Public Access |
|--------|-------------|----------------|---------------|
| **Full VM Deployment** | 900MB ❌ | None | ✅ Direct IP |
| **Current + Cloudflare** | 380MB ✅ | 2GB+ | ✅ Tunnel URL |
| **Nginx Proxy** | 400MB ✅ | 2GB+ | ✅ Direct IP |

**Best Choice:** Current setup + Cloudflare Tunnel (already working, no changes needed!)

---

## 🎯 Quick Decision Guide

**Want:** `http://142.93.220.152` to work directly
**Solution:** Nginx reverse proxy (adds 20MB RAM to VM)

**Want:** Public access ASAP  
**Solution:** Use Cloudflare Tunnel (already set up!)

**Want:** Full deployment on VM  
**Solution:** Upgrade VM to 2GB RAM first

---

Which approach do you prefer?
