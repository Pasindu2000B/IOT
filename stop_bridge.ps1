# =============================================================================
# Stop MQTT to InfluxDB Bridge (Windows)
# =============================================================================

$bridgeProcess = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -eq "python" -and $_.CommandLine -like "*mqtt_to_influx_bridge.py*"
}

if (!$bridgeProcess) {
    Write-Host "⚠️  Bridge is not running" -ForegroundColor Yellow
    exit 0
}

Write-Host "🛑 Stopping bridge (PID: $($bridgeProcess.Id))..." -ForegroundColor Yellow

Stop-Process -Id $bridgeProcess.Id -Force

Start-Sleep -Seconds 1

Write-Host "✅ Bridge stopped" -ForegroundColor Green
