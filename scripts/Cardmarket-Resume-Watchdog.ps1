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
    if($diag.status -ne 'AVAILABLE' -or $diag.login -ne 'AUTHENTICATED'){Note 'CARDMARKET_SESSION_NOT_VERIFIED';return}
  }
  $busy=@(Get-CimInstance Win32_Process | Where-Object {
     $_.Name -eq 'powershell.exe' -and $_.CommandLine -match '-File.*Cardmarket-Queue-Runner[.]ps1'
  })
  if($busy.Count -gt 0){return}
  $states=@()
  foreach($language in @('de','en')){
    $progressPath=Join-Path $base ("progress-$language.json")
    if(-not (Test-Path $progressPath)){continue}
    $state=Get-Content -Raw -Encoding UTF8 $progressPath | ConvertFrom-Json
    $last=[DateTime]::Parse([string]$state.updated_at).ToUniversalTime()
    $stalled=($state.status -eq 'RUNNING' -and $last -lt [DateTime]::UtcNow.AddMinutes(-6))
    if($stalled){
      $state.status='INTERRUPTED'
      $state.updated_at=[DateTime]::UtcNow.ToString('o')
      $state | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 -Path $progressPath
      $last=[DateTime]::UtcNow
      Note ('STALE_RUNNING_INTERRUPTED '+$language)
    }
    $states+= [pscustomobject]@{language=$language;status=[string]$state.status;last=$last}
  }
  if($states.Count -eq 0){return}
  $remaining=@($states | Where-Object { $_.status -notin @('COMPLETED','COMPLETE') })
  if($remaining.Count -eq 0){return}
  # Do not restart a blocked provider immediately just because a static page
  # or cached logout link can still be read. Only read-only probes are allowed
  # before the full backoff expires. After normal batches use shorter breaks.
  foreach($s in $remaining){
    $minutes=switch($s.status){
      'BLOCKED' {240;break}
      'PROVIDER_TIMEOUT' {90;break}
      'CONNECTION_LOST' {60;break}
      'LOGIN_REQUIRED' {20;break}
      'LOGIN_UNVERIFIED' {20;break}
      'BATCH_COMPLETE_MORE_PENDING' {45;break}
      'COMPLETED_WITH_DEFERRED' {90;break}
      default {0}
    }
    if($minutes -gt 0 -and [DateTime]::UtcNow -lt $s.last.AddMinutes($minutes)){
      return
    }
  }
  $pages=Invoke-RestMethod -Uri 'http://127.0.0.1:9223/json/list' -TimeoutSec 5
  $active=$pages | Where-Object { $_.type -eq 'page' -and ([string]$_.url).StartsWith('https://www.cardmarket.com/') } | Select-Object -First 1
  if(!$active){Note 'NO_CARDMARKET_TAB';return}
  if([string]$active.title -match '(?i)nur einen moment|just a moment|attention required|security check|checking your browser|access denied|cloudflare to restrict access|too many requests'){
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
