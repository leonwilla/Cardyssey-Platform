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
# Manual resume is still allowed only after the same live login/Block check.
if (-not $ManualResume){
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
        'LOGIN_REQUIRED' {20;break}
        'LOGIN_UNVERIFIED' {20;break}
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
}

$ready=$false
try {$null=Invoke-RestMethod -TimeoutSec 2 "http://127.0.0.1:9223/json/list";$ready=$true} catch {}
if (!$ready) {
  $existing=Get-CimInstance Win32_Process | Where-Object {$_.Name -eq "msedge.exe" -and $_.CommandLine -match "CardmarketEdgeProfile" -and $_.CommandLine -notmatch "--type="} | Select-Object -First 1
  if ($existing) {
    $p=Get-Process -Id $existing.ProcessId -ErrorAction SilentlyContinue
    if ($p) {$null=$p.CloseMainWindow();Start-Sleep -Seconds 3}
  }
  $chrome="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
  Start-Process $chrome -ArgumentList @("--user-data-dir=$profile", "--remote-debugging-port=9223", "--remote-allow-origins=http://localhost", "--no-first-run", "https://www.cardmarket.com/de/Pokemon")
  for($i=0;$i -lt 25;$i++) {
    Start-Sleep -Seconds 1
    try {$null=Invoke-RestMethod -TimeoutSec 2 "http://127.0.0.1:9223/json/list";$ready=$true;break} catch {}
  }
}
if (!$ready) {throw "Cardmarket browser debugging endpoint unavailable; preserve profile and retry later"}
# Both automatic and manual resume obey the same provider/login gate.
$diagnose=Join-Path $base 'Cardmarket-Session-Status.ps1'
if(Test-Path $diagnose){
  $health=& $diagnose | ConvertFrom-Json
  $progress=Join-Path $base 'progress-de.json'
  if($health.status -ne 'AVAILABLE' -or $health.login -ne 'AUTHENTICATED'){
    $pause=if($health.status -eq 'BLOCKED'){'BLOCKED'}elseif($health.login -eq 'LOGIN_REQUIRED'){'LOGIN_REQUIRED'}else{'LOGIN_UNVERIFIED'}
    if(Test-Path $progress){
      $x=Get-Content -Raw $progress | ConvertFrom-Json
      $x.status=$pause;$x.updated_at=[DateTime]::UtcNow.ToString('o')
      $x|ConvertTo-Json -Compress|Set-Content -Encoding UTF8 -Path $progress
    }
    Write-Output ('CARDMARKET_PAUSED '+$pause)
    return
  }
}
Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",$runner,"-BatchLimit","16","-DelaySeconds","10","-MinRequestGapSeconds","10","-Languages","both","-RunMinutes","40","-ScanMode","identity","-RequireLogin") -RedirectStandardOutput (Join-Path $base "language-queue-stdout.log") -RedirectStandardError (Join-Path $base "language-queue-stderr.log")
