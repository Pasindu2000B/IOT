# =============================================================================
# IOT Predictive Maintenance System - Windows Deployment Script
# =============================================================================

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  IOT Predictive Maintenance System Setup" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Create logs directory
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Step 1: Start Docker containers
Write-Host "📦 Step 1: Starting Docker containers..." -ForegroundColor Yellow
docker-compose up -d

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to start (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Step 2: Check service health
Write-Host "`n🔍 Step 2: Checking service health..." -ForegroundColor Yellow
docker-compose ps

# Step 3: Setup Spark workers with Python dependencies
Write-Host "`n📚 Step 3: Installing Python dependencies on Spark workers..." -ForegroundColor Yellow
Write-Host "   This may take 2-3 minutes..." -ForegroundColor Gray

$jobs = @()
$jobs += Start-Job -ScriptBlock { docker exec -u root spark-master bash -c "pip install --quiet numpy pandas influxdb-client torch torchvision --index-url https://download.pytorch.org/whl/cpu" }
$jobs += Start-Job -ScriptBlock { docker exec -u root spark-worker-1 bash -c "pip install --quiet numpy pandas influxdb-client torch torchvision --index-url https://download.pytorch.org/whl/cpu" }
$jobs += Start-Job -ScriptBlock { docker exec -u root spark-worker-2 bash -c "pip install --quiet numpy pandas influxdb-client torch torchvision --index-url https://download.pytorch.org/whl/cpu" }

# Wait for all installations
$jobs | Wait-Job | Out-Null
$jobs | Remove-Job

Write-Host "   ✅ All dependencies installed!" -ForegroundColor Green

# Step 4: Start data generation
Write-Host "`n📊 Step 4: Starting sensor data generation..." -ForegroundColor Yellow
Start-Process python -ArgumentList "GenerateData.py" -WindowStyle Hidden -RedirectStandardOutput "logs\generate_data.log" -RedirectStandardError "logs\generate_data_error.log"
Write-Host "   ✅ Data generator started" -ForegroundColor Green

# Step 5: Start MQTT to InfluxDB bridge
Write-Host "`n🌉 Step 5: Starting MQTT to InfluxDB bridge..." -ForegroundColor Yellow
& .\start_bridge.ps1

# Step 6: Wait for data collection
Write-Host "`n⏳ Step 6: Collecting initial data (2 minutes)..." -ForegroundColor Yellow
Write-Host "   This allows the system to gather training data..." -ForegroundColor Gray
Start-Sleep -Seconds 120

# Step 7: Run initial distributed training
Write-Host "`n🎯 Step 7: Running initial distributed model training..." -ForegroundColor Yellow
docker exec spark-master bash -c "/opt/spark/bin/spark-submit --master spark://spark-master:7077 --executor-memory 1g --total-executor-cores 4 --conf spark.executor.cores=2 --conf spark.task.cpus=1 --conf spark.python.worker.reuse=true /opt/spark-apps/train_distributed.py"

# Step 8: Display summary
Write-Host "`n===============================================" -ForegroundColor Cyan
Write-Host "  ✅ System Successfully Deployed!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Service URLs:" -ForegroundColor Yellow
Write-Host "   • Spark Master UI:  http://localhost:8080"
Write-Host "   • InfluxDB UI:      http://localhost:8086"
Write-Host "   • MQTT Broker:      localhost:1883"
Write-Host ""
Write-Host "📁 Important Directories:" -ForegroundColor Yellow
Write-Host "   • Models:           .\spark-apps\models\"
Write-Host "   • Logs:             .\logs\"
Write-Host ""
Write-Host "🔧 Useful Commands:" -ForegroundColor Yellow
Write-Host "   • View logs:        Get-Content logs\bridge.log -Wait"
Write-Host "   • Check status:     .\status.ps1"
Write-Host "   • Stop system:      .\stop.ps1"
Write-Host "   • Retrain models:   .\retrain.ps1"
Write-Host ""
Write-Host "📝 Latest Models:" -ForegroundColor Yellow
Get-ChildItem -Path "spark-apps\models\*.pt" | Sort-Object LastWriteTime -Descending | Select-Object -First 3 | ForEach-Object { Write-Host "   $($_.Name)" }
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
