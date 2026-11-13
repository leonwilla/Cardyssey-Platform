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
      $cooldown= switch([string]$x.status){
        'BLOCKED' {240;break}
        'PROVIDER_TIMEOUT' {90;break}
        'CONNECTION_LOST' {60;break}
        'BATCH_COMPLETE_MORE_PENDING' {45;break}
        'COMPLETED_WITH_DEFERRED' {90;break}
        default {0}
      }
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
# One gentle homepage navigation AFTER all cooldown/duplicate-runner gates.
# Never solve challenges or export session tokens. Fail closed if the normal
# navigation cannot be verified. Session-Status still decides authentication.
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
# Auth is optional when the provider explicitly reports AVAILABLE.
# Cloudflare / unreadable provider access still fail closed. Guest rows must
# validate their own language/condition/variant filters and offer completeness.
$diagnose=Join-Path $base 'Cardmarket-Session-Status.ps1'
if(!(Test-Path $diagnose)){Write-Output 'CARDMARKET_SESSION_DIAGNOSTICS_MISSING';return}
if(Test-Path $diagnose){
  $health=& $diagnose | ConvertFrom-Json
  if([string]$health.status -ne 'AVAILABLE'){
    $pause=if([string]$health.status -eq 'BLOCKED'){'BLOCKED'}else{'LOGIN_UNVERIFIED'}
    $progress=Join-Path $base 'progress-de.json'
    if(Test-Path $progress){
      $x=Get-Content -Raw $progress | ConvertFrom-Json
      $x.status=$pause;$x.updated_at=[DateTime]::UtcNow.ToString('o')
      $x|ConvertTo-Json -Compress|Set-Content -Encoding UTF8 -Path $progress
    }
    Write-Output ('CARDMARKET_PAUSED '+$pause)
    return
  }
  if([string]$health.login -ne 'AUTHENTICATED'){
    Write-Output 'CARDMARKET_PUBLIC_LIMITED_SESSION_CONTINUE'
  }
}
Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",$runner,"-BatchLimit","16","-DelaySeconds","10","-MinRequestGapSeconds","10","-Languages","both","-RunMinutes","40","-ScanMode","identity") -RedirectStandardOutput (Join-Path $base "language-queue-stdout.log") -RedirectStandardError (Join-Path $base "language-queue-stderr.log")
