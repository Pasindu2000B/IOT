<#
.SYNOPSIS
    Control Panel for Inference Service automation

.DESCRIPTION
    Interactive menu to manage the inference service scheduled task
#>

$TASK_NAME = "InferenceService_AutoStart"

function Show-Menu {
    Clear-Host
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  Inference Service Control Panel" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    # Check task status
    $task = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
    if ($task) {
        $state = $task.State
        $color = switch ($state) {
            "Running" { "Green" }
            "Ready" { "Yellow" }
            "Disabled" { "Red" }
            default { "Gray" }
        }
        Write-Host "  Status: " -NoNewline -ForegroundColor White
        Write-Host "$state" -ForegroundColor $color
    } else {
        Write-Host "  Status: " -NoNewline -ForegroundColor White
        Write-Host "Not Installed" -ForegroundColor Red
    }
    
    Write-Host "`n  Dashboard: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  1. Start Service (manual)" -ForegroundColor White
    Write-Host "  2. Install Auto-Start Service" -ForegroundColor White
    Write-Host "  3. Stop Service" -ForegroundColor White
    Write-Host "  4. View Status" -ForegroundColor White
    Write-Host "  5. View Task Details" -ForegroundColor White
    Write-Host "  6. Uninstall Service" -ForegroundColor White
    Write-Host "  7. Open Dashboard in Browser" -ForegroundColor White
    Write-Host "  8. Exit" -ForegroundColor White
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Start-ManualService {
    Write-Host "`nStarting inference service manually..." -ForegroundColor Yellow
    $scriptPath = "C:\Users\Asus\Desktop\IOT\local-automation\start_inference_service.bat"
    if (Test-Path $scriptPath) {
        Start-Process cmd.exe -ArgumentList "/k", $scriptPath
        Write-Host "  Service started in new window" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: Script not found at $scriptPath" -ForegroundColor Red
    }
}

function Install-ServiceTask {
    Write-Host "`nInstalling auto-start service..." -ForegroundColor Yellow
    $installerPath = "C:\Users\Asus\Desktop\IOT\local-automation\install_inference_service.ps1"
    if (Test-Path $installerPath) {
        Start-Process powershell.exe -ArgumentList "-ExecutionPolicy Bypass -File `"$installerPath`"" -Verb RunAs -Wait
        Write-Host "  Installation complete" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: Installer not found at $installerPath" -ForegroundColor Red
    }
}

function Stop-ServiceTask {
    Write-Host "`nStopping inference service..." -ForegroundColor Yellow
    $task = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
    if ($task) {
        Stop-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
        Write-Host "  Service stopped" -ForegroundColor Green
    } else {
        Write-Host "  Service not installed" -ForegroundColor Red
    }
    
    # Also kill any running python processes
    $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
    if ($pythonProcesses) {
        Write-Host "  Stopping Python processes..." -ForegroundColor Yellow
        Stop-Process -Name python -Force -ErrorAction SilentlyContinue
        Write-Host "  Python processes stopped" -ForegroundColor Green
    }
}

function Show-ServiceStatus {
    Write-Host "`nService Status:" -ForegroundColor Yellow
    $task = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
    if ($task) {
        Write-Host "  State: $($task.State)" -ForegroundColor Cyan
        Write-Host "  Last Run: $((Get-ScheduledTaskInfo -TaskName $TASK_NAME).LastRunTime)" -ForegroundColor White
        Write-Host "  Next Run: $((Get-ScheduledTaskInfo -TaskName $TASK_NAME).NextRunTime)" -ForegroundColor White
        
        # Check if process is running
        $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
        if ($pythonProcesses) {
            Write-Host "  Python Processes: $($pythonProcesses.Count) running" -ForegroundColor Green
        } else {
            Write-Host "  Python Processes: None running" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Service is not installed" -ForegroundColor Red
    }
}

function Show-TaskDetails {
    Write-Host "`nTask Details:" -ForegroundColor Yellow
    $task = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
    if ($task) {
        $task | Format-List TaskName, State, Description
        Write-Host "Triggers:" -ForegroundColor Cyan
        $task.Triggers | Format-List
    } else {
        Write-Host "  Service is not installed" -ForegroundColor Red
    }
}

function Uninstall-ServiceTask {
    Write-Host "`nUninstalling inference service..." -ForegroundColor Yellow
    $confirm = Read-Host "Are you sure? (Y/N)"
    if ($confirm -eq "Y" -or $confirm -eq "y") {
        $task = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
        if ($task) {
            Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
            Write-Host "  Service uninstalled" -ForegroundColor Green
        } else {
            Write-Host "  Service was not installed" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Cancelled" -ForegroundColor Yellow
    }
}

function Open-Dashboard {
    Write-Host "`nOpening dashboard in browser..." -ForegroundColor Yellow
    Start-Process "http://localhost:8000"
    Write-Host "  Browser opened" -ForegroundColor Green
}

# Main loop
do {
    Show-Menu
    $choice = Read-Host "Select option"
    
    switch ($choice) {
        "1" { Start-ManualService; Pause }
        "2" { Install-ServiceTask; Pause }
        "3" { Stop-ServiceTask; Pause }
        "4" { Show-ServiceStatus; Pause }
        "5" { Show-TaskDetails; Pause }
        "6" { Uninstall-ServiceTask; Pause }
        "7" { Open-Dashboard; Pause }
        "8" { Write-Host "`nExiting...`n" -ForegroundColor Green; return }
        default { Write-Host "`nInvalid option`n" -ForegroundColor Red; Pause }
    }
} while ($true)
