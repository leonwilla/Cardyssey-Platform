# Read-only watch of the existing Cardmarket Edge session.
# Never solve a challenge; resume only when Cardmarket has cleared it itself.
param([switch]$ReportBlocked,[ValidateRange(0,240)][int]$BlockedAlertGraceMinutes=5,[ValidateRange(5,240)][int]$ClearanceWaitMinutes=30)
$ErrorActionPreference='Stop'
$base=Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector'
$backoffScript=Join-Path $base 'Cardmarket-Backoff-Policy.ps1'
if(!(Test-Path $backoffScript)){throw 'CARDMARKET_BACKOFF_POLICY_MISSING'}
. $backoffScript
$log=Join-Path $base 'resume-watchdog.log'
function Note($value) {
  ('{0} {1}' -f [DateTime]::UtcNow.ToString('o'),$value) | Add-Content -Path $log -Encoding UTF8
}

function Send-CardmarketTelegramAlert([string]$Incident,[string]$Message,[bool]$Active) {
  $alertLock=[Threading.Mutex]::new($false,'Local\CardysseyCardmarketAlerts')
  $ownsLock=$false
  try {
  try {$ownsLock=$alertLock.WaitOne(15000)} catch [Threading.AbandonedMutexException] {$ownsLock=$true}
  if(!$ownsLock){return}
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
  if($Incident -ne 'BLOCKED' -and ($now.TimeOfDay -ge [TimeSpan]::Parse('23:00') -or $now.TimeOfDay -lt [TimeSpan]::Parse('07:30'))){return}
  try{
    $uri='https://api.telegram.org/bot'+$token+'/sendMessage'
    $reply=Invoke-RestMethod -Method Post -Uri $uri -Body @{chat_id=$chat;text=$Message} -TimeoutSec 12
    if($reply.ok){$state[$Incident]=[DateTime]::UtcNow.ToString('o');$state|ConvertTo-Json|Set-Content -Encoding UTF8 $path;Note ('TELEGRAM_SENT '+$Incident)}
  }catch{Note ('TELEGRAM_FAILED '+$Incident)}
  } finally {
    if($ownsLock){$alertLock.ReleaseMutex()}
    $alertLock.Dispose()
  }
}
$blockMessage='Cardyssey: Cardmarket will seit über '+$BlockedAlertGraceMinutes+' Minuten eine Cloudflare-Bestätigung (Freigabe läuft stündlich ab). Bitte im Scanner-Edge die Seite neu laden (F5) und das Kästchen anklicken. Der Scanner läuft danach von selbst weiter.'
# Many challenges clear by themselves within minutes. Remember when a block
# was first seen and alert only if it is still present after the grace time.
$blockSeenFile=Join-Path $base 'telegram-block-first-seen.json'
$blockClearedFile=Join-Path $base 'telegram-block-last-cleared.json'
$BlockFlapMinutes=15
function Register-CardmarketBlockSeen([string]$ClearanceId) {
  if(Test-Path $blockSeenFile){return}
  # Remember the (expired) clearance fingerprint: resume only once Cardmarket
  # issued a new one, instead of running into the same challenge every pass.
  if(!$ClearanceId){
    try{$ClearanceId=[string]((Get-Content -Raw -Encoding UTF8 (Join-Path $base 'browser-session-status.json') | ConvertFrom-Json).clearanceId)}catch{}
  }
  # A resume that runs straight into the next challenge is still the same
  # block: keep its first-seen time, else the alert grace restarts every pass
  # and the owner never gets a message (seen 25.11.2026, 09:55-11:25 UTC).
  $first=[DateTime]::UtcNow.ToString('o')
  if(Test-Path $blockClearedFile){
    try{
      $cleared=Get-Content -Raw -Encoding UTF8 $blockClearedFile | ConvertFrom-Json
      $age=([DateTime]::UtcNow - [DateTime]::Parse([string]$cleared.clearedAt).ToUniversalTime()).TotalMinutes
      if($age -lt $BlockFlapMinutes -and $cleared.firstSeen){$first=[string]$cleared.firstSeen}
    }catch{}
  }
  @{firstSeen=$first;clearanceId=$ClearanceId} | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 $blockSeenFile
}
function Test-CardmarketClearanceRenewed([string]$CurrentId) {
  # True when the block is over: a new clearance was issued, the fingerprint is
  # unknown, or the wait limit passed (then the old resume behaviour applies).
  if(!(Test-Path $blockSeenFile)){return $true}
  try{$seen=Get-Content -Raw -Encoding UTF8 $blockSeenFile | ConvertFrom-Json}catch{return $true}
  $old=[string]$seen.clearanceId
  if(!$old -or !$CurrentId -or $old -ne $CurrentId){return $true}
  try{$first=[DateTime]::Parse([string]$seen.firstSeen).ToUniversalTime()}catch{return $true}
  return ([DateTime]::UtcNow - $first).TotalMinutes -ge $ClearanceWaitMinutes
}
function Clear-CardmarketBlockSeen {
  if(!(Test-Path $blockSeenFile)){return}
  try{
    $seen=Get-Content -Raw -Encoding UTF8 $blockSeenFile | ConvertFrom-Json
    @{firstSeen=[string]$seen.firstSeen;clearedAt=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 $blockClearedFile
  }catch{}
  Remove-Item -Force $blockSeenFile
}
function Test-CardmarketBlockResolved {
  # Over only when no new block followed the last resume for the flap window.
  if(Test-Path $blockSeenFile){return $false}
  if(!(Test-Path $blockClearedFile)){return $true}
  try{$cleared=Get-Content -Raw -Encoding UTF8 $blockClearedFile | ConvertFrom-Json
      return ([DateTime]::UtcNow - [DateTime]::Parse([string]$cleared.clearedAt).ToUniversalTime()).TotalMinutes -ge $BlockFlapMinutes}
  catch{return $true}
}
function Test-CardmarketBlockGraceElapsed {
  if(!(Test-Path $blockSeenFile)){return $false}
  try{$first=[DateTime]::Parse([string]((Get-Content -Raw -Encoding UTF8 $blockSeenFile | ConvertFrom-Json).firstSeen)).ToUniversalTime()}
  catch{return $true}
  return ([DateTime]::UtcNow - $first).TotalMinutes -ge $BlockedAlertGraceMinutes
}
if($ReportBlocked){
  Register-CardmarketBlockSeen
  Note 'BLOCK_SEEN_ALERT_AFTER_GRACE'
  return
}

try {
  # Diagnose the persistent profile on every watchdog pass, even if a scan is
  # running. Read-only: never access stored passwords or bypass the provider.
  $checker=Join-Path $base 'Cardmarket-Session-Status.ps1'
  if(!(Test-Path $checker)){Note 'SESSION_CHECKER_MISSING';return}
  $diag=& $checker | ConvertFrom-Json
  if($diag.status -eq 'BLOCKED'){
    Register-CardmarketBlockSeen ([string]$diag.clearanceId)
    if(Test-CardmarketBlockGraceElapsed){Send-CardmarketTelegramAlert 'BLOCKED' $blockMessage $true}
  } elseif($diag.status -eq 'AVAILABLE' -and !(Test-CardmarketClearanceRenewed ([string]$diag.clearanceId))){
    # Page looks normal, but the old clearance is still in place: the next
    # product page would hit the challenge again. Wait for a real renewal.
    if(Test-CardmarketBlockGraceElapsed){Send-CardmarketTelegramAlert 'BLOCKED' $blockMessage $true}
    Note 'CLEARANCE_NOT_RENEWED_WAITING'
    return
  } elseif($diag.status -eq 'AVAILABLE'){
    Clear-CardmarketBlockSeen
    # Keep the sent state while the block may come back, else a flapping
    # block sends a new message every pass.
    if(Test-CardmarketBlockResolved){Send-CardmarketTelegramAlert 'BLOCKED' $blockMessage $false}
  }
  if($diag.status -eq 'BLOCKED'){Note 'CHALLENGE_STILL_PRESENT';return}
  # Login is an incident in itself; do not wait until 50 cards have been
  # marked deferred (the entire queue stops before they are counted).
  Send-CardmarketTelegramAlert 'LOGIN_REQUIRED' 'Cardyssey: Cardmarket-Login abgelaufen. Gastscan läuft weiter, solange öffentlich verfügbare Angebotslisten vollständig sind. Für mehrseitige Angebote bitte im Edge-Profil anmelden.' ([string]$diag.login -eq 'LOGIN_REQUIRED')
  if($diag.login -eq 'LOGIN_REQUIRED'){Note 'CARDMARKET_GUEST_SESSION_AVAILABLE'}
  # Windows reboot may close Edge while leaving a valid persistent profile.
  # Only the normal launcher may bootstrap a closed browser, and only AFTER
  # the complete cooldown check below. The launcher repeats all auth checks.
  $browserNeedsBootstrap=([string]$diag.status -eq 'BROWSER_UNAVAILABLE')
  if(!$browserNeedsBootstrap -and $diag.status -ne 'AVAILABLE'){
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
    try{
      $state=Get-Content -Raw -Encoding UTF8 $progressPath | ConvertFrom-Json
      $last=[DateTime]::Parse([string]$state.updated_at).ToUniversalTime()
    }catch{
      # Empty/broken progress file (interrupted write): mark the language as
      # interrupted so the normal resume path runs instead of failing forever.
      $state=[pscustomobject]@{status='INTERRUPTED';language=$language;updated_at=[DateTime]::UtcNow.AddHours(-1).ToString('o');done=0;total=0;last_card='';provider_attempted=$false}
      $state | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 -Path $progressPath
      $last=[DateTime]::Parse([string]$state.updated_at).ToUniversalTime()
      Note ('PROGRESS_FILE_REPAIRED '+$language)
    }
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
  if(Get-CardmarketActiveCooldown $remaining $base ([string]$diag.status)){return}
  $launcher=Join-Path $base 'Cardmarket-Collector-Launcher.ps1'
  if(!(Test-Path $launcher)){Note 'COLLECTOR_LAUNCHER_MISSING';return}
  if($browserNeedsBootstrap){
    # Do not try to inspect a non-existent Edge CDP tab. Launcher starts the
    # saved profile once, performs the ordinary six-second homepage warm-up,
    # and only starts if the provider is AVAILABLE (guest accepted).
    Note 'BROWSER_COLD_START_AFTER_COOLDOWN'
    & $launcher -ResumeAfterClearance
    return
  }
  Note 'PAGE_AVAILABLE_ATTEMPT_RESUME'
  & $launcher -ResumeAfterClearance
} catch {
  Note ('WATCH_ERROR '+$_.Exception.Message.Substring(0,[Math]::Min(130,$_.Exception.Message.Length)))
}
