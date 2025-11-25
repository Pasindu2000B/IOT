#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Schedules monthly model training using Task Scheduler

.DESCRIPTION
    Creates a scheduled task that runs model training on the 1st day of every month at 2 AM.
    Uses the existing run_monthly_training.sh script.
#>

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Monthly Model Training Setup" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

$TASK_NAME = "ModelTraining_Monthly"
$SCRIPT_PATH = "C:\Users\Asus\Desktop\IOT\run_monthly_training.sh"
$WORKING_DIR = "C:\Users\Asus\Desktop\IOT"

# Check if script exists
if (-not (Test-Path $SCRIPT_PATH)) {
    Write-Host "ERROR: Training script not found at $SCRIPT_PATH" -ForegroundColor Red
    exit 1
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Task Name: $TASK_NAME" -ForegroundColor White
Write-Host "  Script: $SCRIPT_PATH" -ForegroundColor White
Write-Host "  Schedule: 1st day of every month at 2:00 AM" -ForegroundColor White
Write-Host ""

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Task already exists. Removing old task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
    Write-Host "  Removed old task`n" -ForegroundColor Green
}

# Create scheduled task
Write-Host "Creating scheduled task..." -ForegroundColor Yellow

# Action: Run bash script (assuming Git Bash or WSL is available)
# Try to find bash.exe
$bashPath = $null
$possiblePaths = @(
    "C:\Program Files\Git\bin\bash.exe",
    "C:\Windows\System32\bash.exe",  # WSL
    "C:\msys64\usr\bin\bash.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $bashPath = $path
        break
    }
}

if (-not $bashPath) {
    Write-Host "ERROR: bash.exe not found. Please install Git Bash or WSL." -ForegroundColor Red
    Write-Host "  Or run training manually using: bash run_monthly_training.sh" -ForegroundColor Yellow
    exit 1
}

Write-Host "  Using bash at: $bashPath" -ForegroundColor Cyan

$Action = New-ScheduledTaskAction -Execute $bashPath -Argument "-c `"cd '$WORKING_DIR' && bash run_monthly_training.sh`"" -WorkingDirectory $WORKING_DIR

# Trigger: Monthly on the 1st at 2 AM
$Trigger = New-ScheduledTaskTrigger -Monthly -DaysOfMonth 1 -At 2am

$Principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" -LogonType Interactive -RunLevel Highest

$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 12)

Register-ScheduledTask -TaskName $TASK_NAME -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Monthly model training for IoT condition prediction" | Out-Null

Write-Host "  Task created successfully!`n" -ForegroundColor Green

# Ask to run test
$runTest = Read-Host "Run a test training now? (Y/N)"
if ($runTest -eq "Y" -or $runTest -eq "y") {
    Write-Host "`nStarting model training (this may take a while)..." -ForegroundColor Yellow
    Start-ScheduledTask -TaskName $TASK_NAME
    Start-Sleep -Seconds 3
    
    $taskInfo = Get-ScheduledTask -TaskName $TASK_NAME
    Write-Host "  Status: $($taskInfo.State)" -ForegroundColor Green
    Write-Host "`n  Check Task Scheduler for progress" -ForegroundColor Cyan
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nModel training will now:" -ForegroundColor White
Write-Host "   Run automatically on the 1st of every month at 2 AM" -ForegroundColor Green
Write-Host "   Train models for all workspaces" -ForegroundColor Green
Write-Host "   Update models in FYP-Machine-Condition-Prediction/" -ForegroundColor Green
Write-Host "`nNext scheduled run:" -ForegroundColor Yellow
$nextRun = (Get-ScheduledTaskInfo -TaskName $TASK_NAME).NextRunTime
Write-Host "  $nextRun" -ForegroundColor White
Write-Host "`nManagement:" -ForegroundColor Yellow
Write-Host "  View: Task Scheduler > ModelTraining_Monthly" -ForegroundColor White
Write-Host "  Start: Start-ScheduledTask -TaskName '$TASK_NAME'" -ForegroundColor White
Write-Host "  Disable: Disable-ScheduledTask -TaskName '$TASK_NAME'" -ForegroundColor White
Write-Host "  Remove: Unregister-ScheduledTask -TaskName '$TASK_NAME'" -ForegroundColor White
Write-Host ""
