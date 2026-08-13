# Script to set up Windows Scheduled Task for SkillPulse Daily Refresh
$BatchPath = "C:\Users\Kartik Kumar Singh\Desktop\skillpulse\refresh_jobs.bat"
$Action = New-ScheduledTaskAction -Execute $BatchPath
$Trigger = New-ScheduledTaskTrigger -Daily -At 06:00AM
Register-ScheduledTask -TaskName "SkillPulse_Daily_Refresh" -Action $Action -Trigger $Trigger -Force
Write-Host "✅ Task 'SkillPulse_Daily_Refresh' created successfully!"
