# Cloudflare Tunnel Setup Script for IOT Predictive Maintenance System
# This script sets up a secure tunnel to expose your FastAPI inference API

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IOT System - Cloudflare Tunnel Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Download cloudflared
Write-Host "[1/5] Downloading cloudflared..." -ForegroundColor Yellow
$downloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
$installPath = "$env:USERPROFILE\cloudflared.exe"

try {
    if (Test-Path $installPath) {
        Write-Host "  cloudflared already exists at: $installPath" -ForegroundColor Green
    } else {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $installPath -UseBasicParsing
        Write-Host "  Downloaded to: $installPath" -ForegroundColor Green
    }
} catch {
    Write-Host "  ERROR: Failed to download cloudflared" -ForegroundColor Red
    Write-Host "  Please download manually from: $downloadUrl" -ForegroundColor Yellow
    exit 1
}

# Step 2: Verify FastAPI is running
Write-Host ""
Write-Host "[2/5] Checking if FastAPI is running on port 8000..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 5 -UseBasicParsing
    Write-Host "  FastAPI is running!" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: FastAPI not responding on http://localhost:8000/" -ForegroundColor Red
    Write-Host "  Please start the inference API first:" -ForegroundColor Yellow
    Write-Host "  cd FYP-Machine-Condition-Prediction" -ForegroundColor Yellow
    Write-Host "  python -m uvicorn main:app --reload --port 8000" -ForegroundColor Yellow
    exit 1
}

# Step 3: Login to Cloudflare (one-time)
Write-Host ""
Write-Host "[3/5] Cloudflare Authentication" -ForegroundColor Yellow
Write-Host "  This will open a browser window for authentication." -ForegroundColor Cyan
Write-Host "  If you don't have a Cloudflare account, create one (it's free)." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press ENTER to continue or Ctrl+C to cancel..." -ForegroundColor Yellow
Read-Host

try {
    & $installPath tunnel login
    Write-Host "  Authentication successful!" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Authentication failed" -ForegroundColor Red
    exit 1
}

# Step 4: Create tunnel
Write-Host ""
Write-Host "[4/5] Creating tunnel..." -ForegroundColor Yellow
$tunnelName = "iot-predictive-maintenance"

$existingTunnel = & $installPath tunnel list 2>&1 | Select-String $tunnelName
if ($existingTunnel) {
    Write-Host "  Tunnel '$tunnelName' already exists" -ForegroundColor Green
} else {
    try {
        & $installPath tunnel create $tunnelName
        Write-Host "  Tunnel '$tunnelName' created successfully!" -ForegroundColor Green
    } catch {
        Write-Host "  ERROR: Failed to create tunnel" -ForegroundColor Red
        exit 1
    }
}

# Step 5: Instructions for running tunnel
Write-Host ""
Write-Host "[5/5] Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Run the tunnel with this command:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  $installPath tunnel --url http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host "This will:" -ForegroundColor Cyan
Write-Host "  1. Create a public HTTPS URL (e.g., https://xyz.trycloudflare.com)" -ForegroundColor Cyan
Write-Host "  2. Route all traffic securely to your local FastAPI on port 8000" -ForegroundColor Cyan
Write-Host "  3. Keep running until you press Ctrl+C" -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Your API:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Once tunnel is running, test these endpoints:" -ForegroundColor Yellow
Write-Host "  GET https://YOUR-TUNNEL-URL/              # Service info" -ForegroundColor White
Write-Host "  GET https://YOUR-TUNNEL-URL/workspaces    # List models" -ForegroundColor White
Write-Host "  GET https://YOUR-TUNNEL-URL/inference/status  # Status" -ForegroundColor White
Write-Host "  GET https://YOUR-TUNNEL-URL/predict/cnc-mill-5-axis  # Predictions" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Run as Background Service (Optional):" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run tunnel permanently in background:" -ForegroundColor Yellow
Write-Host "  $installPath service install" -ForegroundColor White
Write-Host "  $installPath service start" -ForegroundColor White
Write-Host ""
Write-Host "Note: This requires a config file. See tunnel-config.yml" -ForegroundColor Cyan
Write-Host ""
