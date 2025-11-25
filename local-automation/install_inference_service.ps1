#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Installs Inference Service as Windows Task Scheduler task (auto-start on boot)

.DESCRIPTION
    Creates a scheduled task that runs the inference service (main.py) automatically
    when Windows starts. The service runs in a hidden window and restarts on crash.
#>

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Inference Service Auto-Start Setup" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

$TASK_NAME = "InferenceService_AutoStart"
$SCRIPT_PATH = "C:\Users\Asus\Desktop\IOT\local-automation\start_inference_service.bat"
$WORKING_DIR = "C:\Users\Asus\Desktop\IOT\FYP-Machine-Condition-Prediction"

# Check if script exists
if (-not (Test-Path $SCRIPT_PATH)) {
    Write-Host "ERROR: Script not found at $SCRIPT_PATH" -ForegroundColor Red
    exit 1
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Task Name: $TASK_NAME" -ForegroundColor White
Write-Host "  Script: $SCRIPT_PATH" -ForegroundColor White
Write-Host "  Working Dir: $WORKING_DIR" -ForegroundColor White
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

$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$SCRIPT_PATH`"" -WorkingDirectory $WORKING_DIR
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" -LogonType Interactive -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $TASK_NAME -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Auto-start Inference Service (FastAPI) on Windows boot" | Out-Null

Write-Host "  Task created successfully!`n" -ForegroundColor Green

# Ask to start now
$startNow = Read-Host "Start the service now? (Y/N)"
if ($startNow -eq "Y" -or $startNow -eq "y") {
    Write-Host "`nStarting inference service..." -ForegroundColor Yellow
    Start-ScheduledTask -TaskName $TASK_NAME
    Start-Sleep -Seconds 3
    
    $taskInfo = Get-ScheduledTask -TaskName $TASK_NAME
    Write-Host "  Status: $($taskInfo.State)" -ForegroundColor Green
    Write-Host "`n  Dashboard: http://localhost:8000" -ForegroundColor Cyan
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nThe inference service will now:" -ForegroundColor White
Write-Host "   Auto-start when Windows boots" -ForegroundColor Green
Write-Host "   Auto-restart if it crashes" -ForegroundColor Green
Write-Host "   Run the dashboard on port 8000" -ForegroundColor Green
Write-Host "`nManagement:" -ForegroundColor Yellow
Write-Host "  View: Task Scheduler > InferenceService_AutoStart" -ForegroundColor White
Write-Host "  Start: Start-ScheduledTask -TaskName '$TASK_NAME'" -ForegroundColor White
Write-Host "  Stop: Stop-ScheduledTask -TaskName '$TASK_NAME'" -ForegroundColor White
Write-Host "  Remove: Unregister-ScheduledTask -TaskName '$TASK_NAME'" -ForegroundColor White
Write-Host ""
