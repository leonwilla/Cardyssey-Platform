# Cardyssey eBay "verkaufte Artikel" collector (eBay.de).
#
# Owner decision 26.11.2026: sold prices are read in a SEPARATE Edge profile
# that is signed in with a separate buyer account (never the seller account),
# slowly (20-30 s between pages, max. 1,500 pages per day). It never solves or
# bypasses a robot check: on a check or a sign-in page it stops and sends a
# Telegram alert; a human confirms it in the window.
#
# Queue (written by scripts/ebay/ebay_sold_import.py --plan):
#   %LOCALAPPDATA%\Cardyssey\EbaySold\ebay-sold-queue.json  [{key, query}]
# Results (read by ebay_sold_import.py --import):
#   %LOCALAPPDATA%\Cardyssey\EbaySold\ebay-sold-results.jsonl
param(
  [ValidateRange(1,500)][int]$MaxPages = 70,
  [ValidateRange(10,120)][int]$MinGapSeconds = 20,
  [ValidateRange(10,180)][int]$MaxGapSeconds = 30,
  [ValidateRange(1,5000)][int]$DailyCap = 1500,
  [ValidateRange(5,240)][int]$RunMinutes = 50,
  [int]$CdpPort = 9224
)
$ErrorActionPreference = 'Stop'
$base = Join-Path $env:LOCALAPPDATA 'Cardyssey\EbaySold'
$cmBase = Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector'  # Telegram settings live there
$profileDir = Join-Path $env:LOCALAPPDATA 'Cardyssey\EbayTestProfile'
New-Item -ItemType Directory -Force -Path $base | Out-Null
$queueFile = Join-Path $base 'ebay-sold-queue.json'
$resultsFile = Join-Path $base 'ebay-sold-results.jsonl'
$stateFile = Join-Path $base 'ebay-sold-state.json'
$statusFile = Join-Path $base 'ebay-sold-status.json'
$logFile = Join-Path $base 'ebay-sold-collector.log'
function Note([string]$m) { "$(Get-Date -Format o) $m" | Add-Content -Encoding UTF8 $logFile }

$mutex = [Threading.Mutex]::new($false, 'Local\CardysseyEbaySoldCollector')
if (-not $mutex.WaitOne(0)) { Note 'ALREADY_RUNNING'; exit 0 }

function Send-Alert([string]$Incident, [string]$Message, [bool]$Active) {
  $token = $null; $chat = $null
  $tokenFile = Join-Path $cmBase 'telegram-bot-token.dpapi'
  $chatFile = Join-Path $cmBase 'telegram-chat-id.txt'
  try {
    if (Test-Path $tokenFile) {
      $secured = Get-Content -Raw -Encoding UTF8 $tokenFile | ConvertTo-SecureString
      $token = (New-Object System.Management.Automation.PSCredential('telegram', $secured)).GetNetworkCredential().Password
    }
    if (Test-Path $chatFile) { $chat = (Get-Content -Raw -Encoding UTF8 $chatFile).Trim() }
  } catch { Note 'TELEGRAM_UNREADABLE'; return }
  if (!$token -or $chat -notmatch '^[0-9]{6,20}$') { return }
  $path = Join-Path $base 'telegram-alert-state.json'
  $state = @{}
  if (Test-Path $path) { try { (Get-Content -Raw $path | ConvertFrom-Json).PSObject.Properties | % { $state[$_.Name] = $_.Value } } catch {} }
  if (!$Active) { if ($state.ContainsKey($Incident)) { $state.Remove($Incident); $state | ConvertTo-Json | Set-Content -Encoding UTF8 $path }; return }
  if ($state.ContainsKey($Incident)) { return }
  try {
    $reply = Invoke-RestMethod -Method Post -Uri ('https://api.telegram.org/bot' + $token + '/sendMessage') -Body @{chat_id = $chat; text = $Message} -TimeoutSec 12
    if ($reply.ok) { $state[$Incident] = [DateTime]::UtcNow.ToString('o'); $state | ConvertTo-Json | Set-Content -Encoding UTF8 $path; Note "TELEGRAM_SENT $Incident" }
  } catch { Note "TELEGRAM_FAILED $Incident" }
}

function Finish([string]$Status, [int]$Pages) {
  [ordered]@{status = $Status; pages = $Pages; updated_at = [DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 $statusFile
  Note "END $Status pages=$Pages"
  if ($script:ws) { try { $script:ws.Dispose() } catch {} }
  $mutex.ReleaseMutex()
  exit 0
}

# Daily page budget
$today = (Get-Date).ToString('yyyy-MM-dd')
$state = @{day = $today; pages = 0; done = @(); queueVersion = ''}
if (Test-Path $stateFile) {
  try { $s = Get-Content -Raw -Encoding UTF8 $stateFile | ConvertFrom-Json; if ($s.day -eq $today) { $state.pages = [int]$s.pages }; $state.done = @($s.done); $state.queueVersion = [string]$s.queueVersion } catch {}
}
if ($state.pages -ge $DailyCap) { Finish 'DAILY_CAP_REACHED' 0 }
if (!(Test-Path $queueFile)) { Finish 'NO_QUEUE' 0 }
# Windows PowerShell 5.1 emits a JSON array as ONE pipeline object; unroll it.
$queueParsed = Get-Content -Raw -Encoding UTF8 $queueFile | ConvertFrom-Json
$queue = @($queueParsed | ForEach-Object { $_ })
$queueVersion = (Get-Item $queueFile).LastWriteTimeUtc.ToString('o')
if ($state.queueVersion -ne $queueVersion) { $state.done = @() }
$doneSet = New-Object 'System.Collections.Generic.HashSet[string]'
foreach ($d in $state.done) { [void]$doneSet.Add([string]$d) }

# Separate Edge profile on its own debugging port (never the seller account).
$up = $false
try { Invoke-RestMethod "http://127.0.0.1:$CdpPort/json/version" -TimeoutSec 3 | Out-Null; $up = $true } catch {}
if (!$up) {
  $edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
  if (!(Test-Path $edge)) { $edge = "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe" }
  Start-Process $edge -WindowStyle Minimized -ArgumentList "--remote-debugging-port=$CdpPort", "--user-data-dir=`"$profileDir`"",
    '--remote-allow-origins=http://localhost', '--no-first-run', '--no-default-browser-check', 'https://www.ebay.de/'
  Start-Sleep -Seconds 10
}
$target = (Invoke-RestMethod "http://127.0.0.1:$CdpPort/json/list" -TimeoutSec 5) | ? { $_.type -eq 'page' -and $_.url -match '^https?:' } | Select-Object -First 1
if (!$target) { Finish 'NO_BROWSER_TAB' 0 }
$script:ws = [Net.WebSockets.ClientWebSocket]::new(); $script:ws.Options.SetRequestHeader('Origin', 'http://localhost')
$script:ws.ConnectAsync([uri]$target.webSocketDebuggerUrl, [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
$script:cdpId = 0
function Js([string]$expr) {
  $script:cdpId++; $id = $script:cdpId
  $b = [Text.Encoding]::UTF8.GetBytes((@{id = $id; method = 'Runtime.evaluate'; params = @{expression = $expr; returnByValue = $true; awaitPromise = $true}} | ConvertTo-Json -Depth 5 -Compress))
  $script:ws.SendAsync([ArraySegment[byte]]::new($b), 'Text', $true, [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
  $buf = New-Object byte[] 4194304
  $deadline = [DateTime]::UtcNow.AddSeconds(45)
  while ([DateTime]::UtcNow -lt $deadline) {
    $ms = New-Object IO.MemoryStream
    do { $r = $script:ws.ReceiveAsync([ArraySegment[byte]]::new($buf), [Threading.CancellationToken]::None).GetAwaiter().GetResult(); $ms.Write($buf, 0, $r.Count) } while (-not $r.EndOfMessage)
    $m = [Text.Encoding]::UTF8.GetString($ms.ToArray()) | ConvertFrom-Json
    if ($m.id -eq $id) { return $m.result.result.value }
  }
  throw 'CDP_TIMEOUT'
}
$extract = @'
(()=>{const t=document.title||'';const body=(document.body&&document.body.innerText)||'';
const robot=/captcha|splashui|pardon our interruption|sicherheitsma(ss|ß)nahme|kein roboter|not a robot|verify yourself/i.test(location.href+' '+t+' '+body.slice(0,800));
const login=/signin\.ebay|einloggen oder neu anmelden/i.test(location.href+' '+t);
const items=[];for(const li of document.querySelectorAll('li.s-item, li.s-card, ul.srp-results > li')){
 const a=li.querySelector('a[href*="/itm/"]');if(!a)continue;
 const titleEl=li.querySelector('.s-item__title, .s-card__title, [role=heading]');
 items.push({url:a.href.split('?')[0],title:((titleEl&&titleEl.innerText)||a.innerText||'').replace(/\s+/g,' ').trim().slice(0,200),
   text:(li.innerText||'').replace(/\s+/g,' ').trim().slice(0,400)});}
return JSON.stringify({url:location.href,title:t.slice(0,120),robot,login,items:items.slice(0,240)});})()
'@

Note "START queue=$($queue.Count) pagesToday=$($state.pages)"
$deadline = [DateTime]::Now.AddMinutes($RunMinutes)
$pages = 0
foreach ($q in $queue) {
  $key = [string]$q.key
  if ($doneSet.Contains($key)) { continue }
  if ($pages -ge $MaxPages -or $state.pages -ge $DailyCap -or [DateTime]::Now -ge $deadline) { break }
  $url = 'https://www.ebay.de/sch/i.html?_nkw=' + [uri]::EscapeDataString([string]$q.query) + '&_sacat=183454&LH_Sold=1&LH_Complete=1&_ipg=240'
  Js ('location.href=' + ($url | ConvertTo-Json -Compress)) | Out-Null
  Start-Sleep -Seconds 7
  $page = (Js $extract) | ConvertFrom-Json
  $pages++; $state.pages++
  if ($page.robot) {
    Send-Alert 'EBAY_ROBOT_CHECK' 'Cardyssey eBay-Verkaufsscanner: eBay zeigt eine Robot-Pruefung. Bitte im Fenster "eBay Test-Browser (Cardyssey)" bestaetigen. Der Scanner wartet.' $true
    Finish 'BLOCKED_ROBOT_CHECK' $pages
  }
  if ($page.login) {
    Send-Alert 'EBAY_LOGIN' 'Cardyssey eBay-Verkaufsscanner: Abgemeldet. Bitte im Fenster "eBay Test-Browser (Cardyssey)" mit dem separaten Kaeuferkonto (NICHT dem Verkaeuferkonto) anmelden.' $true
    Finish 'LOGIN_REQUIRED' $pages
  }
  Send-Alert 'EBAY_ROBOT_CHECK' '' $false
  Send-Alert 'EBAY_LOGIN' '' $false
  ([ordered]@{key = $key; query = [string]$q.query; at = [DateTime]::UtcNow.ToString('o'); items = @($page.items)} | ConvertTo-Json -Depth 5 -Compress) | Add-Content -Encoding UTF8 $resultsFile
  [void]$doneSet.Add($key)
  [ordered]@{day = $today; pages = $state.pages; queueVersion = $queueVersion; done = @($doneSet)} | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 $stateFile
  Start-Sleep -Seconds (Get-Random -Minimum $MinGapSeconds -Maximum ($MaxGapSeconds + 1))
}
Finish 'OK' $pages
