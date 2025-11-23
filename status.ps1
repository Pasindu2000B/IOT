# =============================================================================
# Check IOT System Status (Windows)
# =============================================================================

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  IOT System Status" -ForegroundColor Yellow
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🐳 Docker Containers:" -ForegroundColor Yellow
docker-compose ps
Write-Host ""

Write-Host "📊 Python Processes:" -ForegroundColor Yellow
$bridge = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*mqtt_to_influx_bridge.py*" }
$generator = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*GenerateData.py*" }

if ($bridge) {
    Write-Host "   ✅ Bridge:         Running (PID: $($bridge.Id))" -ForegroundColor Green
} else {
    Write-Host "   ❌ Bridge:         Stopped" -ForegroundColor Red
}

if ($generator) {
    Write-Host "   ✅ Data Generator: Running (PID: $($generator.Id))" -ForegroundColor Green
} else {
    Write-Host "   ❌ Data Generator: Stopped" -ForegroundColor Red
}
Write-Host ""

Write-Host "📁 Recent Models:" -ForegroundColor Yellow
$models = Get-ChildItem -Path "spark-apps\models\*.pt" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 3
if ($models) {
    $models | ForEach-Object { Write-Host "   $($_.Name)" }
} else {
    Write-Host "   No models found"
}
Write-Host ""

Write-Host "===============================================" -ForegroundColor Cyan
