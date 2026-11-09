# Read-only watch of the existing Cardmarket Edge session.
# Never solve a challenge; resume only when Cardmarket has cleared it itself.
$ErrorActionPreference='Stop'
$base=Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector'
$log=Join-Path $base 'resume-watchdog.log'
function Note($value) {
  ('{0} {1}' -f [DateTime]::UtcNow.ToString('o'),$value) | Add-Content -Path $log -Encoding UTF8
}
try {
  # Diagnose the persistent profile on every watchdog pass, even if a scan is
  # running. Read-only: never access stored passwords or bypass the provider.
  $checker=Join-Path $base 'Cardmarket-Session-Status.ps1'
  if(Test-Path $checker){
    $diag=& $checker | ConvertFrom-Json
    if($diag.status -eq 'BLOCKED'){Note 'CHALLENGE_STILL_PRESENT';return}
    if($diag.login -eq 'LOGIN_REQUIRED'){Note 'CARDMARKET_LOGIN_REQUIRED';return}
  }
  $busy=@(Get-CimInstance Win32_Process | Where-Object {
     $_.Name -eq 'powershell.exe' -and $_.CommandLine -match '-File.*Cardmarket-Queue-Runner[.]ps1'
  })
  if($busy.Count -gt 0){return}
  $progressPath=Join-Path $base 'progress-de.json'
  if(!(Test-Path $progressPath)){return}
  $state=Get-Content -Raw $progressPath | ConvertFrom-Json
  if([string]$state.status -notin @('BLOCKED','PROVIDER_TIMEOUT','CONNECTION_LOST','LOGIN_REQUIRED')){return}
  $pages=@(Invoke-RestMethod -Uri 'http://127.0.0.1:9223/json/list' -TimeoutSec 5 |
      Where-Object { $_.type -eq 'page' -and ([string]$_.url).StartsWith('https://www.cardmarket.com/') })
  if(!$pages.Count){Note 'NO_CARDMARKET_TAB';return}
  $active=$pages[0]
  if([string]$active.title -match '(?i)nur einen moment|just a moment|attention required|security check|checking your browser'){
    Note 'CHALLENGE_STILL_PRESENT';return
  }
  # Title alone cannot prove a valid product page, but after a prior block
  # it can trigger one cautious attempt. Collector rechecks every response.
  $launcher=Join-Path $base 'Cardmarket-Collector-Launcher.ps1'
  Note 'PAGE_VISIBLE_ATTEMPT_RESUME'
  & $launcher -ResumeAfterClearance
} catch {
  Note ('WATCH_ERROR '+$_.Exception.Message.Substring(0,[Math]::Min(130,$_.Exception.Message.Length)))
}
