# Start FastAPI Inference Service
# This script ensures the API runs continuously

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting IOT Inference API" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker is running
Write-Host "[1/4] Checking Docker..." -ForegroundColor Yellow
$dockerRunning = docker ps 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Docker is not running!" -ForegroundColor Red
    Write-Host "  Please start Docker Desktop first" -ForegroundColor Yellow
    exit 1
}
Write-Host "  Docker is running" -ForegroundColor Green

# Check InfluxDB is accessible
Write-Host ""
Write-Host "[2/4] Checking InfluxDB..." -ForegroundColor Yellow
try {
    $influxTest = Invoke-WebRequest -Uri "http://localhost:8086/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "  InfluxDB is accessible" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: InfluxDB not responding" -ForegroundColor Yellow
    Write-Host "  API may not work correctly" -ForegroundColor Yellow
}

# Check data generator is running
Write-Host ""
Write-Host "[3/4] Checking data generator..." -ForegroundColor Yellow
$genProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*GenerateData.py*"}
if ($genProcess) {
    Write-Host "  Data generator is running (PID: $($genProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Data generator not detected" -ForegroundColor Yellow
    Write-Host "  To start it: python GenerateData.py" -ForegroundColor Cyan
}

# Start FastAPI
Write-Host ""
Write-Host "[4/4] Starting FastAPI service..." -ForegroundColor Yellow
Write-Host "  URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Cyan
Write-Host ""

Set-Location "C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction"

# Use uvicorn directly with proper module path
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
