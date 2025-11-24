# ============================================================================
# Deploy Integrated IOT Training + FYP Inference System
# ============================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Integrated IOT Predictive Maintenance System Deployment" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Deploy IOT Training System
Write-Host "Step 1: Deploying IOT Training System..." -ForegroundColor Yellow
Write-Host ""

if (Test-Path ".\docker-compose.yml") {
    Write-Host "  Starting IOT containers..." -ForegroundColor Green
    docker-compose up -d
    
    Write-Host "  Waiting for services to start (30 seconds)..." -ForegroundColor Green
    Start-Sleep -Seconds 30
    
    Write-Host "  Checking IOT service health..." -ForegroundColor Green
    docker-compose ps
} else {
    Write-Host "  ERROR: docker-compose.yml not found in IOT directory" -ForegroundColor Red
    exit 1
}

# Step 2: Start IOT Data Generation
Write-Host ""
Write-Host "Step 2: Starting IOT data generation..." -ForegroundColor Yellow

if (!(Test-Path ".\logs")) {
    New-Item -ItemType Directory -Path ".\logs" | Out-Null
}

Write-Host "  Starting GenerateData.py..." -ForegroundColor Green
$generateDataJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python GenerateData.py
}
$generateDataJob.Id | Out-File ".\logs\generate_data.pid" -Encoding ASCII
Write-Host "  Data generator started (Job ID: $($generateDataJob.Id))" -ForegroundColor Green

# Step 3: Start MQTT Bridge
Write-Host ""
Write-Host "Step 3: Starting MQTT to InfluxDB bridge..." -ForegroundColor Yellow

if (Test-Path ".\start_bridge.ps1") {
    & ".\start_bridge.ps1"
} else {
    Write-Host "  Starting bridge manually..." -ForegroundColor Green
    $bridgeJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        python mqtt_to_influx_bridge.py
    }
    $bridgeJob.Id | Out-File ".\logs\bridge.pid" -Encoding ASCII
    Write-Host "  Bridge started (Job ID: $($bridgeJob.Id))" -ForegroundColor Green
}

# Step 4: Wait for Initial Data Collection
Write-Host ""
Write-Host "Step 4: Collecting initial data (2 minutes)..." -ForegroundColor Yellow
Write-Host "  This allows the system to gather training data..." -ForegroundColor Gray

for ($i = 120; $i -gt 0; $i--) {
    Write-Progress -Activity "Collecting Data" -Status "$i seconds remaining" -PercentComplete ((120-$i)/120*100)
    Start-Sleep -Seconds 1
}
Write-Progress -Activity "Collecting Data" -Completed

# Step 5: Run Initial Training
Write-Host ""
Write-Host "Step 5: Running initial distributed model training..." -ForegroundColor Yellow
Write-Host "  This may take 5-10 minutes..." -ForegroundColor Gray

docker exec spark-master bash -c "/opt/spark/bin/spark-submit --master spark://spark-master:7077 --executor-memory 1g --total-executor-cores 4 --conf spark.executor.cores=2 --conf spark.task.cpus=1 --conf spark.python.worker.reuse=true /opt/spark-apps/train_distributed.py"

# Step 6: Verify Models Exist
Write-Host ""
Write-Host "Step 6: Verifying trained models..." -ForegroundColor Yellow

if (Test-Path ".\spark-apps\models") {
    $modelCount = (Get-ChildItem ".\spark-apps\models" -Directory -Filter "model_*").Count
    Write-Host "  Found $modelCount trained model(s)" -ForegroundColor Green
    
    if ($modelCount -eq 0) {
        Write-Host "  WARNING: No models found. Training may have failed." -ForegroundColor Red
        Write-Host "  Check logs: docker logs spark-master" -ForegroundColor Yellow
    }
} else {
    Write-Host "  WARNING: Models directory not found" -ForegroundColor Red
}

# Step 7: Configure FYP System
Write-Host ""
Write-Host "Step 7: Configuring FYP Inference System..." -ForegroundColor Yellow

$fypPath = ".\FYP-Machine-Condition-Prediction"

if (Test-Path $fypPath) {
    Set-Location $fypPath
    
    # Check if .env exists, if not create from example
    if (!(Test-Path ".\.env")) {
        if (Test-Path ".\.env.example") {
            Write-Host "  Creating .env file from example..." -ForegroundColor Green
            Copy-Item ".\.env.example" ".\.env"
            Write-Host "  IMPORTANT: Edit .env and set WORKSPACE_ID and SENDGRID_API_KEY" -ForegroundColor Yellow
        } else {
            Write-Host "  WARNING: .env.example not found" -ForegroundColor Red
        }
    } else {
        Write-Host "  .env file already exists" -ForegroundColor Green
    }
    
    Set-Location ..
} else {
    Write-Host "  WARNING: FYP directory not found at $fypPath" -ForegroundColor Red
}

# Step 8: Deploy FYP System
Write-Host ""
Write-Host "Step 8: Deploying FYP Inference System..." -ForegroundColor Yellow

if (Test-Path $fypPath) {
    Set-Location $fypPath
    
    Write-Host "  Building and starting FYP containers..." -ForegroundColor Green
    docker-compose up -d --build
    
    Write-Host "  Waiting for FYP services to start (20 seconds)..." -ForegroundColor Green
    Start-Sleep -Seconds 20
    
    Write-Host "  Checking FYP service health..." -ForegroundColor Green
    docker-compose ps
    
    Set-Location ..
} else {
    Write-Host "  Skipping FYP deployment (directory not found)" -ForegroundColor Yellow
}

# Step 9: Display Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "IOT Training System:" -ForegroundColor Yellow
Write-Host "  Spark Master UI:  http://localhost:8080" -ForegroundColor White
Write-Host "  InfluxDB UI:      http://localhost:8086" -ForegroundColor White
Write-Host "    Username: Pasindu Bimsara" -ForegroundColor Gray
Write-Host "    Password: abcdefgh" -ForegroundColor Gray
Write-Host "  MQTT Broker:      localhost:1883" -ForegroundColor White
Write-Host ""
Write-Host "FYP Inference System:" -ForegroundColor Yellow
Write-Host "  API Endpoints:    http://localhost:8000" -ForegroundColor White
Write-Host "  MongoDB:          localhost:27017" -ForegroundColor White
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Yellow
Write-Host "  Check IOT status:     .\status.ps1" -ForegroundColor White
Write-Host "  Check FYP logs:       docker logs fyp-inference-service -f" -ForegroundColor White
Write-Host "  Test FYP API:         curl http://localhost:8000/sensor/latest" -ForegroundColor White
Write-Host "  View bridge logs:     Get-Content logs\bridge.log -Wait" -ForegroundColor White
Write-Host "  Retrain models:       .\retrain.ps1" -ForegroundColor White
Write-Host "  Stop all:             .\stop.ps1; cd FYP-Machine-Condition-Prediction; docker-compose down" -ForegroundColor White
Write-Host ""
Write-Host "Models Directory:" -ForegroundColor Yellow
Get-ChildItem ".\spark-apps\models" -Directory -Filter "model_*" | Select-Object -First 3 | ForEach-Object {
    Write-Host "  $($_.Name)" -ForegroundColor White
}
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Edit FYP-Machine-Condition-Prediction\.env" -ForegroundColor White
Write-Host "  2. Set WORKSPACE_ID (lathe-1-spindle, cnc-mill-5-axis, or robot-arm-02)" -ForegroundColor White
Write-Host "  3. Set SENDGRID_API_KEY for email alerts" -ForegroundColor White
Write-Host "  4. Restart FYP: cd FYP-Machine-Condition-Prediction; docker-compose restart app" -ForegroundColor White
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
