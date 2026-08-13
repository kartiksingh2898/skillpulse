$action = New-ScheduledTaskAction -Execute "python" -Argument "$PSScriptRoot\refresh_snapshot.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 6am
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
$task = New-ScheduledTask -Action $action -Principal $principal -Trigger $trigger -Description "SkillPulse Daily Refresh"
Register-ScheduledTask -TaskName "SkillPulse_Daily_Refresh" -InputObject $task -Force
Write-Host "✅ Scheduled Task 'SkillPulse_Daily_Refresh' created successfully. It will run daily at 6:00 AM."
