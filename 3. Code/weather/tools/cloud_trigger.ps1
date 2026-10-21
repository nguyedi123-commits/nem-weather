# W-024 back-up: GitHub's own timer has not started a job yet (21 Oct), so this PC starts the cloud job.
# Run by Windows Task Scheduler (tasks "Weather cloud ..."), see SKILL.md. Duplicates are harmless: jobs queue,
# and a job with nothing new publishes nothing.
#   powershell -File cloud_trigger.ps1 light|full
param([string]$Mode = "light")
$log = Join-Path $PSScriptRoot "..\..\..\data\cloud_trigger.log"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$out = & $gh workflow run refresh.yml --repo nguyedi123-commits/nem-weather -f "mode=$Mode" 2>&1
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Mode exit=$LASTEXITCODE $out" | Out-File -Append -Encoding utf8 $log
