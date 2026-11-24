# Cardyssey Cardmarket expansion-list index.
# Reads Cardmarket's own expansion list pages in the existing, signed-in Edge
# tab (same-origin fetch, no navigation) and records each product tile:
# canonical URL path, printed number title and the idProduct shown in the
# product image path. This replaces per-card search for product URLs.
# Never solves or bypasses a provider challenge: on any challenge, 403 or 429
# the run stops immediately and reports BLOCKED for the normal backoff.
param(
  [ValidateRange(1,500)][int]$MaxRequests = 60,
  [ValidateRange(4,90)][int]$MinRequestGapSeconds = 11,
  [ValidateRange(1,65535)][int]$CdpPort = 9223,
  [ValidateRange(1,365)][int]$RefreshDays = 30,
  [string]$Base = (Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector')
)
$ErrorActionPreference = 'Stop'
$planFile = Join-Path $Base 'expansion-index-plan.json'
$stateFile = Join-Path $Base 'cardmarket-expansion-index.json'
$productsFile = Join-Path $Base 'cardmarket-expansion-index-products.jsonl'
$overviewFile = Join-Path $Base 'cardmarket-expansions-overview.json'
$statusFile = Join-Path $Base 'expansion-index-status.json'
$script:requests = 0
$script:lastRequest = [DateTime]::MinValue

function Write-AtomicJson([string]$Path, $Value) {
  $tmp = $Path + '.tmp'
  $Value | ConvertTo-Json -Depth 8 -Compress | Set-Content -Encoding UTF8 -LiteralPath $tmp
  Move-Item -Force -LiteralPath $tmp -Destination $Path
}

function Finish([string]$Status, [hashtable]$Extra = @{}) {
  $result = [ordered]@{status=$Status; requests=$script:requests; updated_at=[DateTime]::UtcNow.ToString('o')}
  foreach ($k in $Extra.Keys) { $result[$k] = $Extra[$k] }
  Write-AtomicJson $statusFile $result
  Write-Host ($result | ConvertTo-Json -Compress)
  if ($script:ws) { try { $script:ws.Dispose() } catch {} }
  exit 0
}

function Connect-CardmarketTab {
  $target = (Invoke-RestMethod "http://127.0.0.1:$CdpPort/json/list" -TimeoutSec 5) |
    Where-Object { $_.type -eq 'page' -and $_.url -match '^https://www[.]cardmarket[.]com/' } | Select-Object -First 1
  if (!$target) { return $false }
  $script:ws = [Net.WebSockets.ClientWebSocket]::new()
  $script:ws.Options.SetRequestHeader('Origin', 'http://localhost')
  $script:ws.ConnectAsync([uri]$target.webSocketDebuggerUrl, [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
  $script:cdpId = 500000
  return $true
}

function Invoke-PageJs([string]$Expression, [int]$TimeoutSec = 45) {
  $script:cdpId++
  $id = $script:cdpId
  $packet = @{id=$id; method='Runtime.evaluate'; params=@{expression=$Expression; returnByValue=$true; awaitPromise=$true}} |
    ConvertTo-Json -Depth 6 -Compress
  $bytes = [Text.Encoding]::UTF8.GetBytes($packet)
  $script:ws.SendAsync([ArraySegment[byte]]::new($bytes), 'Text', $true, [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
  $buffer = New-Object byte[] 1048576
  $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
  while ([DateTime]::UtcNow -lt $deadline) {
    $cts = [Threading.CancellationTokenSource]::new([TimeSpan]::FromSeconds([Math]::Max(1, ($deadline - [DateTime]::UtcNow).TotalSeconds)))
    $stream = New-Object IO.MemoryStream
    do {
      $r = $script:ws.ReceiveAsync([ArraySegment[byte]]::new($buffer), $cts.Token).GetAwaiter().GetResult()
      $stream.Write($buffer, 0, $r.Count)
    } while (-not $r.EndOfMessage)
    $message = [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
    if ($message.id -ne $id) { continue }
    if ($message.result.exceptionDetails) { throw 'PAGE_SCRIPT_EXCEPTION' }
    return $message.result.result.value
  }
  throw 'CDP_TIMEOUT'
}

function Wait-RequestGap {
  if ($script:lastRequest -ne [DateTime]::MinValue) {
    $wait = $MinRequestGapSeconds - ([DateTime]::UtcNow - $script:lastRequest).TotalSeconds
    if ($wait -gt 0) { Start-Sleep -Milliseconds ([int]($wait * 1000)) }
  }
  $script:lastRequest = [DateTime]::UtcNow
  $script:requests++
}

# One same-origin GET of a Cardmarket page, parsed in the page context.
$fetchJs = @'
(async()=>{const path=__PATH__;const r=await fetch(path,{credentials:'include',redirect:'follow'});
const h=await r.text();const d=new DOMParser().parseFromString(h,'text/html');
const title=d.title||'';const body=(d.body&&d.body.innerText)||'';
const challenge=r.status===403||r.status===429||r.status===503||
 /just a moment|nur einen moment|attention required|checking your browser|too many requests|access denied/i.test(title)||
 !!d.querySelector('#challenge-running,#cf-challenge-running,form#challenge-form');
const out={status:r.status,finalPath:new URL(r.url).pathname,title:title.slice(0,120),challenge};
if(__MODE__==='overview'){
 out.expansions=[...d.querySelectorAll('[data-url^="/en/Pokemon/Expansions/"]')].map(x=>({
  slug:x.getAttribute('data-url').split('/').pop(),name:x.getAttribute('data-local-name')||''}));
}else{
 const m=body.match(/([0-9][0-9.,]*)\s+(?:Hits|Treffer)/i);out.hits=m?parseInt(m[1].replace(/[.,]/g,''),10):null;
 const seen=new Set();out.tiles=[];
 for(const a of d.querySelectorAll('a[href*="/Products/Singles/"]')){
  const u=new URL(a.getAttribute('href'),location.origin);const parts=u.pathname.split('/');
  if(parts.length!==7||parts[4]!=='Singles')continue;
  const img=a.querySelector('img');const src=(img&&(img.getAttribute('data-echo')||img.getAttribute('src')))||'';
  const id=(src.match(/\/([0-9]{3,12})\/\1\.[a-z]{3,4}(?:\?|$)/i)||[])[1];
  if(!id||seen.has(id))continue;seen.add(id);
  const t=a.querySelector('h2,.card-title');
  out.tiles.push({id,slug:parts[5],product:parts[6],title:((t&&t.textContent)||'').replace(/\s+/g,' ').trim().slice(0,140)});
 }
}
return JSON.stringify(out);})()
'@

function Get-CardmarketPage([string]$Path, [string]$Mode = 'list') {
  Wait-RequestGap
  $js = $fetchJs.Replace('__PATH__', ($Path | ConvertTo-Json -Compress)).Replace('__MODE__', "'" + $Mode + "'")
  $page = (Invoke-PageJs $js) | ConvertFrom-Json
  if ($page.challenge) { Finish 'BLOCKED' @{path=$Path; http_status=[int]$page.status; title=[string]$page.title} }
  if ([int]$page.status -ne 200) { return $null }
  return $page
}

if (!(Connect-CardmarketTab)) { Finish 'NO_CARDMARKET_TAB' }

# 1. Expansion overview (names + URL slugs), refreshed monthly.
$overviewFresh = (Test-Path $overviewFile) -and
  ((Get-Item $overviewFile).LastWriteTimeUtc -gt [DateTime]::UtcNow.AddDays(-$RefreshDays))
if (!$overviewFresh) {
  $page = Get-CardmarketPage '/en/Pokemon/Expansions' 'overview'
  if (!$page -or @($page.expansions).Count -lt 100) { Finish 'OVERVIEW_UNREADABLE' }
  Write-AtomicJson $overviewFile ([ordered]@{schema=1; fetchedAt=[DateTime]::UtcNow.ToString('o'); expansions=@($page.expansions)})
  Finish 'OVERVIEW_UPDATED_PLAN_REBUILD_NEEDED' @{expansions=@($page.expansions).Count}
}
if (!(Test-Path $planFile)) { Finish 'NO_PLAN' }
$plan = Get-Content -Raw -Encoding UTF8 $planFile | ConvertFrom-Json
if ([int]$plan.schema -ne 1) { Finish 'INVALID_PLAN' }
if (-not $plan.overviewAvailable) { Finish 'OVERVIEW_UPDATED_PLAN_REBUILD_NEEDED' }

$state = @{}
if (Test-Path $stateFile) {
  $loaded = Get-Content -Raw -Encoding UTF8 $stateFile | ConvertFrom-Json
  foreach ($p in $loaded.expansions.PSObject.Properties) { $state[$p.Name] = $p.Value }
}
function Save-State { Write-AtomicJson $stateFile ([ordered]@{schema=1; updated_at=[DateTime]::UtcNow.ToString('o'); expansions=$state}) }
function Add-Tiles($Tiles, [string]$Slug, [string]$ExpansionId) {
  $lines = foreach ($t in @($Tiles)) {
    if ([string]$t.slug -ne $Slug) { continue }
    [ordered]@{id=[string]$t.id; slug=$Slug; product=[string]$t.product; title=[string]$t.title;
               idExpansion=$ExpansionId; seen_at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Compress
  }
  if ($lines) { Add-Content -Encoding UTF8 -LiteralPath $productsFile -Value $lines }
  return @($lines).Count
}

$pages = 0; $added = 0
$cutoff = [DateTime]::UtcNow.AddDays(-$RefreshDays)
foreach ($exp in @($plan.expansions)) {
  $key = [string]$exp.idExpansion
  $s = $state[$key]
  if ($s -and $s.status -eq 'COMPLETE' -and [DateTime]::Parse([string]$s.crawledAt).ToUniversalTime() -gt $cutoff) { continue }
  $candidates = @($exp.slugCandidates)
  if (!$s) { $s = [pscustomobject]@{slug=''; slugVerified=$false; tried=@(); pagesDone=0; pagesTotal=0; status='PENDING'; crawledAt=''} }
  if ($s.status -eq 'SLUG_NOT_FOUND' -and @($candidates | Where-Object { $_ -notin @($s.tried) }).Count -eq 0) { continue }
  if ($s.status -eq 'COMPLETE') { $s.pagesDone = 0; $s.status = 'REFRESH' }
  $expected = [Collections.Generic.HashSet[string]]::new([string[]]@($exp.expectedProductIds | ForEach-Object { [string]$_ }))
  if (-not $s.slugVerified) {
    foreach ($slug in $candidates) {
      if ($slug -in @($s.tried)) { continue }
      if ($script:requests -ge $MaxRequests) { Save-State; Finish 'BUDGET_USED' @{pages=$pages; new_products=$added} }
      $page = Get-CardmarketPage ('/en/Pokemon/Products/Singles/' + $slug)
      $s.tried = @($s.tried) + $slug
      $tiles = @(if ($page) { $page.tiles | Where-Object { [string]$_.slug -eq $slug } })
      $inside = @($tiles | Where-Object { $expected.Contains([string]$_.id) }).Count
      if ($tiles.Count -gt 0 -and $inside -ge [Math]::Ceiling(0.8 * $tiles.Count)) {
        $s.slug = $slug; $s.slugVerified = $true; $s.pagesDone = 1; $pages++
        $s.pagesTotal = if ($page.hits) { [Math]::Ceiling([int]$page.hits / 30) } else { [int]$exp.maxPages }
        $added += Add-Tiles $tiles $slug $key
        break
      }
    }
    if (-not $s.slugVerified) { $s.status = 'SLUG_NOT_FOUND'; $state[$key] = $s; Save-State; continue }
  }
  $limit = [Math]::Min([int]$s.pagesTotal, [int]$exp.maxPages + 2)
  while ([int]$s.pagesDone -lt $limit) {
    if ($script:requests -ge $MaxRequests) { $state[$key] = $s; Save-State; Finish 'BUDGET_USED' @{pages=$pages; new_products=$added} }
    $next = [int]$s.pagesDone + 1
    $page = Get-CardmarketPage ('/en/Pokemon/Products/Singles/' + $s.slug + '?site=' + $next)
    if (!$page) { break }
    $tiles = @($page.tiles | Where-Object { [string]$_.slug -eq $s.slug })
    $s.pagesDone = $next; $pages++
    if ($tiles.Count -eq 0) { break }
    $added += Add-Tiles $tiles $s.slug $key
    $state[$key] = $s; Save-State
  }
  $s.status = 'COMPLETE'; $s.crawledAt = [DateTime]::UtcNow.ToString('o')
  $state[$key] = $s; Save-State
}
Finish 'COMPLETE' @{pages=$pages; new_products=$added}
