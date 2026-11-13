# Read-only watch of the existing Cardmarket Edge session.
# Never solve a challenge; resume only when Cardmarket has cleared it itself.
$ErrorActionPreference='Stop'
$base=Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector'
$log=Join-Path $base 'resume-watchdog.log'
function Note($value) {
  ('{0} {1}' -f [DateTime]::UtcNow.ToString('o'),$value) | Add-Content -Path $log -Encoding UTF8
}

function Send-CardmarketTelegramAlert([string]$Incident,[string]$Message,[bool]$Active) {
  $token=[Environment]::GetEnvironmentVariable('CARDMARKET_TELEGRAM_BOT_TOKEN','User')
  $chat=[Environment]::GetEnvironmentVariable('CARDMARKET_TELEGRAM_CHAT_ID','User')
  $tokenFile=Join-Path $base 'telegram-bot-token.dpapi'
  $chatFile=Join-Path $base 'telegram-chat-id.txt'
  # Prefer the locally DPAPI-protected token over older environment values.
  if(Test-Path $tokenFile){
    try{
      $secured=Get-Content -Raw -Encoding UTF8 $tokenFile | ConvertTo-SecureString
      $cred=New-Object System.Management.Automation.PSCredential('telegram',$secured)
      $token=$cred.GetNetworkCredential().Password
    }catch{Note 'TELEGRAM_DPAPI_UNREADABLE';return}
  }
  if(Test-Path $chatFile){$chat=(Get-Content -Raw -Encoding UTF8 $chatFile).Trim()}
  if(!$token -or $chat -notmatch '^[0-9]{6,20}$'){
    if($Active){Note 'TELEGRAM_UNCONFIGURED'}
    return
  }
  $path=Join-Path $base 'telegram-alert-state.json'
  $state=@{}
  if(Test-Path $path){try{$loaded=Get-Content -Raw -Encoding UTF8 $path|ConvertFrom-Json;foreach($p in $loaded.PSObject.Properties){$state[$p.Name]=$p.Value}}catch{Note 'TELEGRAM_STATE_INVALID';return}}
  if(!$Active){if($state.ContainsKey($Incident)){$state.Remove($Incident);$state|ConvertTo-Json|Set-Content -Encoding UTF8 $path};return}
  if($state.ContainsKey($Incident)){return}
  $now=[DateTime]::Now
  # Quiet hours (local clock): hold the incident until the next watchdog
  # pass after 07:30; do not mark it sent during the night.
  if($now.TimeOfDay -ge [TimeSpan]::Parse('23:00') -or $now.TimeOfDay -lt [TimeSpan]::Parse('07:30')){return}
  try{
    $uri='https://api.telegram.org/bot'+$token+'/sendMessage'
    $reply=Invoke-RestMethod -Method Post -Uri $uri -Body @{chat_id=$chat;text=$Message} -TimeoutSec 12
    if($reply.ok){$state[$Incident]=[DateTime]::UtcNow.ToString('o');$state|ConvertTo-Json|Set-Content -Encoding UTF8 $path;Note ('TELEGRAM_SENT '+$Incident)}
  }catch{Note ('TELEGRAM_FAILED '+$Incident)}
}
function Get-DeferredLoginCount {
  $count=0
  foreach($language in @('de','en')){
    $file=Join-Path $base ("browser-observations-$language.jsonl")
    if(!(Test-Path $file)){continue}
    $latest=@{}
    foreach($line in [System.IO.File]::ReadLines($file)){
      try{$r=$line|ConvertFrom-Json;if($r.card_id -and $r.variant_id){$latest[([string]$r.card_id+'|'+[string]$r.variant_id)]=[string]$r.status}}catch{}
    }
    $count+=@($latest.Values|Where-Object{$_ -eq 'DEFERRED_LOGIN_REQUIRED'}).Count
  }
  return $count
}

try {
  # Diagnose the persistent profile on every watchdog pass, even if a scan is
  # running. Read-only: never access stored passwords or bypass the provider.
  $checker=Join-Path $base 'Cardmarket-Session-Status.ps1'
  if(!(Test-Path $checker)){Note 'SESSION_CHECKER_MISSING';return}
  $diag=& $checker | ConvertFrom-Json
  Send-CardmarketTelegramAlert 'BLOCKED' 'Cardyssey: Cardmarket Cloudflare-Challenge aktiv. Scanner bleibt in Schutzpause.' ([string]$diag.status -eq 'BLOCKED')
  if($diag.status -eq 'BLOCKED'){Note 'CHALLENGE_STILL_PRESENT';return}
  # Login is an incident in itself; do not wait until 50 cards have been
  # marked deferred (the entire queue stops before they are counted).
  Send-CardmarketTelegramAlert 'LOGIN_REQUIRED' 'Cardyssey: Cardmarket-Anmeldung ist abgelaufen. Der DE/EN-Scanner ist pausiert. Bitte im gespeicherten Edge-Profil auf dem Tiny anmelden.' ([string]$diag.login -eq 'LOGIN_REQUIRED')
  if($diag.login -eq 'LOGIN_REQUIRED'){Note 'CARDMARKET_LOGIN_REQUIRED';return}
  # Windows reboot may close Edge while leaving a valid persistent profile.
  # Only the normal launcher may bootstrap a closed browser, and only AFTER
  # the complete cooldown check below. The launcher repeats all auth checks.
  $browserNeedsBootstrap=([string]$diag.status -eq 'BROWSER_UNAVAILABLE')
  if(!$browserNeedsBootstrap -and
     ($diag.status -ne 'AVAILABLE' -or $diag.login -ne 'AUTHENTICATED')){
    Note 'CARDMARKET_SESSION_NOT_VERIFIED';return
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
  $launcher=Join-Path $base 'Cardmarket-Collector-Launcher.ps1'
  if(!(Test-Path $launcher)){Note 'COLLECTOR_LAUNCHER_MISSING';return}
  if($browserNeedsBootstrap){
    # Do not try to inspect a non-existent Edge CDP tab. Launcher starts the
    # saved profile once, performs the ordinary six-second homepage warm-up,
    # and refuses to scan without AVAILABLE + AUTHENTICATED.
    Note 'BROWSER_COLD_START_AFTER_COOLDOWN'
    & $launcher -ResumeAfterClearance
    return
  }
  $pages=Invoke-RestMethod -Uri 'http://127.0.0.1:9223/json/list' -TimeoutSec 5
  $active=$pages | Where-Object { $_.type -eq 'page' -and ([string]$_.url).StartsWith('https://www.cardmarket.com/') } | Select-Object -First 1
  if(!$active){Note 'NO_CARDMARKET_TAB';return}
  if([string]$active.title -match '(?i)nur einen moment|just a moment|attention required|security check|checking your browser|access denied|cloudflare to restrict access|too many requests'){
    Note 'CHALLENGE_STILL_PRESENT';return
  }
  # Title alone cannot prove a valid product page, but after a prior block
  # it can trigger one cautious attempt. Collector rechecks every response.
  Note 'PAGE_VISIBLE_ATTEMPT_RESUME'
  & $launcher -ResumeAfterClearance
} catch {
  Note ('WATCH_ERROR '+$_.Exception.Message.Substring(0,[Math]::Min(130,$_.Exception.Message.Length)))
}
