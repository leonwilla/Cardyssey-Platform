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
Write-Output "installed=$shortcutPath"
