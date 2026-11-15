# Resume Cardmarket account review on the dedicated local Chrome profile.
# Authentication and login checks remain entirely in Chrome; no cookie export.
param([switch]$ResumeAfterClearance,[switch]$ManualResume)
$ErrorActionPreference="Stop"
$base=Join-Path $env:LOCALAPPDATA "Cardyssey\CardmarketCollector"
$profile=Join-Path $env:LOCALAPPDATA "Cardyssey\CardmarketEdgeProfile"
$runner=Join-Path $base "Cardmarket-Queue-Runner.ps1"
New-Item -ItemType Directory -Force -Path $base | Out-Null
if (!(Test-Path $runner)) {throw "Cardmarket queue runner missing"}
$already=Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match "-File.*Cardmarket-Queue-Runner[.]ps1" -and $_.Name -eq "powershell.exe"}
if ($already) {return}
$backoffScript=Join-Path $base 'Cardmarket-Backoff-Policy.ps1'
if(!(Test-Path $backoffScript)){Write-Output 'CARDMARKET_BACKOFF_POLICY_MISSING';return}
. $backoffScript
# Query the saved Cardmarket tab read-only for a first-block retry.
# The normal homepage can be available while product redirects remain blocked.
# A failed check gives the full 240-minute fallback; never assume clearance.
$firstBlocked=(Get-CardmarketBlockedStreak $base) -eq 1
$providerStatusForBackoff='UNKNOWN'
if($firstBlocked){
  try {
    $checker=Join-Path $base 'Cardmarket-Session-Status.ps1'
    if(Test-Path $checker){
      $sessionResult=& $checker | ConvertFrom-Json
      $providerStatusForBackoff=[string]$sessionResult.status
    }
  } catch {$providerStatusForBackoff='UNKNOWN'}
}
# Durable provider-specific cooldown across Windows Task Scheduler launches.
# Never assume that a persistent login or cf_clearance guarantees access.
# The provider cooldown is mandatory even for the dashboard's manual
# resume button. A working homepage is not proof the product-ID endpoint
# has recovered; repeated manual restarts previously retriggered BLOCKED.
foreach($lang in @('de','en')){
    $progressFile=Join-Path $base ("progress-$lang.json")
    if(-not (Test-Path $progressFile)){continue}
    try{
      $x=Get-Content -Raw -Encoding UTF8 $progressFile | ConvertFrom-Json
      $last=[datetime]::Parse([string]$x.updated_at).ToUniversalTime()
      $cooldown=Get-CardmarketCooldownMinutes -Status ([string]$x.status) -Base $base -ProviderStatus $providerStatusForBackoff
      if($cooldown -gt 0 -and [DateTime]::UtcNow -lt $last.AddMinutes($cooldown)){
        Write-Output ('CARDMARKET_COOLDOWN '+$lang+' '+$x.status+' until '+$last.AddMinutes($cooldown).ToString('o'))
        return
      }
    }catch{
      Write-Output ('CARDMARKET_PROGRESS_UNREADABLE '+$lang)
      return
    }
  }

$ready=$false
$browserNewlyStarted=$false
try {$null=Invoke-RestMethod -TimeoutSec 2 "http://127.0.0.1:9223/json/list";$ready=$true} catch {}
if (!$ready) {
  $existing=Get-CimInstance Win32_Process | Where-Object {$_.Name -eq "msedge.exe" -and $_.CommandLine -match "CardmarketEdgeProfile" -and $_.CommandLine -notmatch "--type="} | Select-Object -First 1
  if ($existing) {
    $p=Get-Process -Id $existing.ProcessId -ErrorAction SilentlyContinue
    if ($p) {$null=$p.CloseMainWindow();Start-Sleep -Seconds 3}
  }
  $chrome="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
  Start-Process $chrome -ArgumentList @("--user-data-dir=$profile", "--remote-debugging-port=9223", "--remote-allow-origins=http://localhost", "--no-first-run", "about:blank")
  $browserNewlyStarted=$true
  for($i=0;$i -lt 25;$i++) {
    Start-Sleep -Seconds 1
    try {$null=Invoke-RestMethod -TimeoutSec 2 "http://127.0.0.1:9223/json/list";$ready=$true;break} catch {}
  }
}
if (!$ready) {throw "Cardmarket browser debugging endpoint unavailable; preserve profile and retry later"}
# Bootstrap a newly started browser once. An existing tab is verified in
# place, so a manual clearance or normal page survives a scheduled resume.
if($browserNewlyStarted){
  $warmupScript=Join-Path $base 'Cardmarket-Session-Warmup.ps1'
  if(!(Test-Path $warmupScript)){
    Write-Output 'CARDMARKET_WARMUP_MISSING_NO_SCAN'
    return
  }
  try{
    $warmup=& $warmupScript -AllowBlankBootstrap:$browserNewlyStarted | ConvertFrom-Json
    if([string]$warmup.status -ne 'READY_FOR_HEALTH_CHECK'){
      Write-Output ('CARDMARKET_WARMUP_PAUSED '+[string]$warmup.status)
      return
    }
    Write-Output 'CARDMARKET_WARMUP_DONE_6S'
  }catch{
    Write-Output 'CARDMARKET_WARMUP_UNVERIFIED_NO_SCAN'
    return
  }
}
# Auth is optional when the provider explicitly reports AVAILABLE.
# Cloudflare / unreadable provider access still fail closed. Guest rows must
# validate their own language/condition/variant filters and offer completeness.
$diagnose=Join-Path $base 'Cardmarket-Session-Status.ps1'
if(!(Test-Path $diagnose)){Write-Output 'CARDMARKET_SESSION_DIAGNOSTICS_MISSING';return}
$health=& $diagnose | ConvertFrom-Json
if([string]$health.status -ne 'AVAILABLE'){
  # Looking at an existing challenge is not a new failed request. Only a
  # block after a fresh bootstrap navigation gets a new cooldown timestamp.
  if($browserNewlyStarted -and $health.status -eq 'BLOCKED'){
    $progress=Join-Path $base 'progress-de.json'
    if(Test-Path $progress){
      $x=Get-Content -Raw -Encoding UTF8 $progress | ConvertFrom-Json
      $x.status='BLOCKED'
      $x.updated_at=[DateTime]::UtcNow.ToString('o')
      $x | Add-Member NoteProperty provider_block_stage 'SESSION_BOOTSTRAP' -Force
      $x | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 -Path $progress
    }
  }
  Write-Output ('CARDMARKET_PAUSED '+[string]$health.status)
  return
}
if([string]$health.login -ne 'AUTHENTICATED'){
  Write-Output 'CARDMARKET_PUBLIC_LIMITED_SESSION_CONTINUE'
}
Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",$runner,"-BatchLimit","16","-DelaySeconds","10","-MinRequestGapSeconds","10","-Languages","both","-RunMinutes","40","-ScanMode","identity") -RedirectStandardOutput (Join-Path $base "language-queue-stdout.log") -RedirectStandardError (Join-Path $base "language-queue-stderr.log")
