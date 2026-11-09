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
# Avoid hammering the same stalled Cardmarket request overnight.
$progressFile=Join-Path $base "progress-de.json"
if (Test-Path $progressFile) {
  try {
    $progress=Get-Content -Raw $progressFile | ConvertFrom-Json
    $last=[datetime]::Parse([string]$progress.updated_at).ToUniversalTime()
    if (!$ResumeAfterClearance -and !$ManualResume -and
        $progress.status -in @("CONNECTION_LOST","PROVIDER_TIMEOUT","BLOCKED","LOGIN_REQUIRED","LOGIN_UNVERIFIED") -and
        $last -gt [datetime]::UtcNow.AddHours(-2)) {return}
  } catch {}
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
Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",$runner,"-BatchLimit","40","-DelaySeconds","8","-Languages","both","-RunMinutes","95","-ScanMode","identity","-RequireLogin") -RedirectStandardOutput (Join-Path $base "language-queue-stdout.log") -RedirectStandardError (Join-Path $base "language-queue-stderr.log")
