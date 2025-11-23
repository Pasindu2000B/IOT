# =============================================================================
# Start MQTT to InfluxDB Bridge as a System Service (Windows)
# =============================================================================

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "mqtt_to_influx_bridge.py"
$logDir = Join-Path $scriptDir "logs"

# Create logs directory
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# Check if already running
$bridgeProcess = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -eq "python" -and $_.CommandLine -like "*mqtt_to_influx_bridge.py*"
}

if ($bridgeProcess) {
    Write-Host "⚠️  Bridge is already running (PID: $($bridgeProcess.Id))" -ForegroundColor Yellow
    exit 1
}

# Start bridge in background
Write-Host "🚀 Starting MQTT to InfluxDB Bridge..." -ForegroundColor Green

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "python"
$psi.Arguments = $pythonScript
$psi.WorkingDirectory = $scriptDir
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.WindowStyle = "Hidden"

$process = [System.Diagnostics.Process]::Start($psi)

# Wait a moment and check if it's running
Start-Sleep -Seconds 2

if (!$process.HasExited) {
    Write-Host "✅ Bridge started successfully (PID: $($process.Id))" -ForegroundColor Green
    Write-Host "📝 Logs: Get-Content $logDir\bridge.log -Wait" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to start bridge" -ForegroundColor Red
    exit 1
}
