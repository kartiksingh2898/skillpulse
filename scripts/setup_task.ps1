# SkillPulse - Windows Task Scheduler Setup
# Registers a daily task to run refresh_snapshot.py every day at 6:00 AM

$ProjectRoot = (Get-Item $PSScriptRoot).Parent.FullName
$VenvPython = "$ProjectRoot\.venv\Scripts\python.exe"
$ScriptPath = "$ProjectRoot\scripts\refresh_snapshot.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "⚠️ Warning: Virtual environment python not found at $VenvPython" -ForegroundColor Yellow
    Write-Host "Please ensure .venv is created first by running start_services.bat." -ForegroundColor Yellow
    $VenvPython = "python"
}

$action = New-ScheduledTaskAction -Execute $VenvPython -Argument "`"$ScriptPath`"" -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At 6am
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

$task = New-ScheduledTask -Action $action -Principal $principal -Trigger $trigger -Settings $settings -Description "SkillPulse Daily Live Job Ingestion & Snapshot Refresh"
Register-ScheduledTask -TaskName "SkillPulse_Daily_Refresh" -InputObject $task -Force

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ✅ Windows Task 'SkillPulse_Daily_Refresh' Created!" -ForegroundColor Green
Write-Host "  🐍 Python Target: $VenvPython" -ForegroundColor Gray
Write-Host "  📜 Script Target: $ScriptPath" -ForegroundColor Gray
Write-Host "  ⏰ Schedule: Daily at 06:00 AM" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan
