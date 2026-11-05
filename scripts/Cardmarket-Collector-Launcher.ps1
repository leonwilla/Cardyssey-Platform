# Resume Cardmarket account review on the dedicated local Chrome profile.
# Authentication and login checks remain entirely in Chrome; no cookie export.
$ErrorActionPreference="Stop"
$base=Join-Path $env:LOCALAPPDATA "Cardyssey\CardmarketCollector"
$profile=Join-Path $env:LOCALAPPDATA "Cardyssey\CardmarketReviewProfile"
$runner=Join-Path $base "Cardmarket-Account-Collector.ps1"
New-Item -ItemType Directory -Force -Path $base | Out-Null
if (!(Test-Path $runner)) {throw "Cardmarket collector runner missing"}
$already=Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match "-File.*Cardmarket-Account-Collector[.]ps1" -and $_.Name -eq "powershell.exe"}
if ($already) {return}
$ready=$false
try {$null=Invoke-RestMethod -TimeoutSec 2 "http://127.0.0.1:9222/json/list";$ready=$true} catch {}
if (!$ready) {
  $existing=Get-CimInstance Win32_Process | Where-Object {$_.Name -eq "chrome.exe" -and $_.CommandLine -match "CardmarketReviewProfile" -and $_.CommandLine -notmatch "--type="} | Select-Object -First 1
  if ($existing) {
    $p=Get-Process -Id $existing.ProcessId -ErrorAction SilentlyContinue
    if ($p) {$null=$p.CloseMainWindow();Start-Sleep -Seconds 3}
  }
  $chrome="C:\Program Files\Google\Chrome\Application\chrome.exe"
  Start-Process $chrome -ArgumentList @("--user-data-dir=$profile", "--remote-debugging-port=9222", "--remote-allow-origins=http://localhost", "--no-first-run", "https://www.cardmarket.com/de/Pokemon")
  for($i=0;$i -lt 25;$i++) {
    Start-Sleep -Seconds 1
    try {$null=Invoke-RestMethod -TimeoutSec 2 "http://127.0.0.1:9222/json/list";$ready=$true;break} catch {}
  }
}
if (!$ready) {throw "Cardmarket debugging endpoint unavailable; preserve profile and retry at next login"}
Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",$runner,"-MaxCases","1460","-DelaySeconds","12") -RedirectStandardOutput (Join-Path $base "collector-stdout.log") -RedirectStandardError (Join-Path $base "collector-stderr.log")
