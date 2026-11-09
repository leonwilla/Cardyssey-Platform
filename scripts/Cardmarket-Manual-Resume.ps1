# Admin-triggered attempt to resume; existing Edge profile and login required.
# The launcher does the definitive session and process checks. Do not bypass.
$ErrorActionPreference='Stop'
$base=Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector'
$launcher=Join-Path $base 'Cardmarket-Collector-Launcher.ps1'
if(!(Test-Path $launcher)){throw 'Cardmarket launcher missing'}
& $launcher -ManualResume
