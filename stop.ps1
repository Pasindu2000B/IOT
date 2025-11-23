# =============================================================================
# Stop IOT Predictive Maintenance System (Windows)
# =============================================================================

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Stopping IOT System" -ForegroundColor Yellow
Write-Host "===============================================" -ForegroundColor Cyan

# Stop Python processes
Write-Host "`n🛑 Stopping Python processes..." -ForegroundColor Yellow

& .\stop_bridge.ps1 2>$null

Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*GenerateData.py*"
} | Stop-Process -Force

Write-Host "   ✅ Python processes stopped" -ForegroundColor Green

# Stop Docker containers
Write-Host "`n🐳 Stopping Docker containers..." -ForegroundColor Yellow
docker-compose down

Write-Host "`n===============================================" -ForegroundColor Cyan
Write-Host "  ✅ System Stopped Successfully" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
