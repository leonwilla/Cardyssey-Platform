# Install an automatic resume shortcut for the existing isolated browser scanner.
$ErrorActionPreference = "Stop"
$base = Join-Path $env:LOCALAPPDATA "Cardyssey\CardmarketCollector"
$launcher = Join-Path $base "Cardmarket-Collector-Launcher.ps1"
if (!(Test-Path $launcher)) {throw "Collector launcher does not exist"}
$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "Cardyssey Cardmarket Collector.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$launcher`""
$shortcut.WorkingDirectory = $base
$shortcut.Description = "Cardyssey: resume filtered Cardmarket review after login"
$shortcut.WindowStyle = 7
$shortcut.Save()
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$launcher`""
$trigger = New-ScheduledTaskTrigger -Daily -At '04:35'
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -StartWhenAvailable
Register-ScheduledTask -TaskName 'Cardyssey Cardmarket Daily Refresh' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Output "startup_installed=$shortcutPath daily_refresh_installed=true"
