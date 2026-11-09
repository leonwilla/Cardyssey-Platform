# Cardyssey Cardmarket browser review. Uses the pre-authenticated, dedicated
# Chrome profile via localhost CDP. Does not export credentials or cookies.
param(
  [ValidateSet('de','en')]
  [string]$Language = 'de',
  [string]$InputCsv = "C:\Users\TV\AppData\Local\Cardyssey\CardmarketCollector\queue-$Language.csv",
  [string]$OutputDir = "C:\Users\TV\AppData\Local\Cardyssey\CardmarketCollector",
  [int]$MaxCases = 0,          # 0 = gesamte Warteschlange
  [int]$BatchLimit = 0,        # 0 = unbegrenzt; sonst N fällige Fälle pro Lauf
  [int]$DelaySeconds = 8,
  [ValidateSet('identity','missing')][string]$ScanMode = 'identity',
  [ValidateRange(5,180)][int]$ChallengeWaitSeconds = 90,
  [ValidateRange(1,65535)][int]$CdpPort = 9223,
  [switch]$ForcePublicMode  # diagnostic: use public behavior even if signed in
)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# --- Sprach-Parameterisierung -------------------------------------------------
$LangCfg = if ($Language -eq 'de') {
  [pscustomobject]@{
    UrlSegment     = 'de'
    PathPrefix     = '/de/Pokemon'
    LanguageId     = 3                      # language[3] = Deutsch
    LanguageNames  = @('Deutsch')
    ConditionNames = @('Near Mint','Mint')
  }
} else {
  [pscustomobject]@{
    UrlSegment     = 'en'
    PathPrefix     = '/en/Pokemon'
    LanguageId     = 1                      # language[1] = Englisch
    LanguageNames  = @('English','Englisch')
    ConditionNames = @('Near Mint','Mint')
  }
}

$resultsPath  = Join-Path $OutputDir "browser-observations-$Language.jsonl"
$unverifyPath = Join-Path $OutputDir "unverified-candidates-$Language.jsonl"
$progressPath = Join-Path $OutputDir "progress-$Language.json"
$errorPath    = Join-Path $OutputDir "connection-errors-$Language.jsonl"
$setSlugGuards = @{}
$setGuardFile=Join-Path $OutputDir 'verified-set-url-guards.json'
if(Test-Path $setGuardFile){
  try {
    $guardJson=Get-Content -Raw -Encoding UTF8 $setGuardFile | ConvertFrom-Json
    foreach($g in $guardJson.PSObject.Properties){$setSlugGuards[$g.Name]=[string]$g.Value}
  }catch{throw 'Bad verified-set-url-guards.json'}
}

# --- CDP-Empfang: nativer Pump-Thread (kein PowerShell-Runspace noetig) --------
# Der ReceiveAsync wird NIE abgebrochen (keine Timeout-Cancellation), damit der
# WebSocket nie in "Aborted" faellt. Gesamtfristen regelt Send-Cdp ueber die Queue.
if (-not ('CdpPump' -as [type])) {
  Add-Type -TypeDefinition @"
using System;
using System.Net.WebSockets;
using System.Text;
using System.Collections.Concurrent;
using System.Threading;
public static class CdpPump {
  public static void Start(ClientWebSocket ws, ConcurrentQueue<string> queue,
                            SemaphoreSlim avail, CancellationToken token) {
    var t = new Thread(() => {
      var buf = new byte[1048576];
      var ms  = new System.IO.MemoryStream();
      try {
        while (!token.IsCancellationRequested) {
          var res = ws.ReceiveAsync(new ArraySegment<byte>(buf), token).GetAwaiter().GetResult();
          ms.Write(buf, 0, res.Count);
          if (!res.EndOfMessage) continue;
          queue.Enqueue(Encoding.UTF8.GetString(ms.ToArray()));
          ms.SetLength(0);
          avail.Release();
        }
      } catch (Exception e) {
        queue.Enqueue("STREAM_DEAD|" + e.Message);
        try { avail.Release(); } catch {}
      }
    });
    t.IsBackground = true;
    t.Start();
  }
}
"@
}

$script:ws      = $null
$script:rxQueue = $null
$script:rxAvail = $null
$script:rxCts   = $null

function Connect-Cdp {
  # Alte Verbindung ordentlich beenden, falls vorhanden.
  if ($script:ws) {
    try { $script:rxCts.Cancel() } catch {}
    try { $script:ws.Dispose() } catch {}
  }
  $targets = (Invoke-RestMethod "http://127.0.0.1:$CdpPort/json/list")
  $t = $targets | Where-Object { $_.type -eq "page" -and $_.url -match "cardmarket.com" } | Select-Object -First 1
  if (!$t) { throw "NO_CDM_TARGET: signierte Cardmarket-Seite im isolierten Chrome-Profil oeffnen." }
  $script:ws = [Net.WebSockets.ClientWebSocket]::new()
  $script:ws.Options.SetRequestHeader("Origin", "http://localhost")
  $script:ws.ConnectAsync([uri]$t.webSocketDebuggerUrl, [threading.cancellationtoken]::None).GetAwaiter().GetResult() | Out-Null
  # Frische Queue + Pump fuer DIESE Socket-Instanz.
  $script:rxQueue = [System.Collections.Concurrent.ConcurrentQueue[string]]::new()
  $script:rxAvail = [System.Threading.SemaphoreSlim]::new(0, [int]::MaxValue)
  $script:rxCts   = [System.Threading.CancellationTokenSource]::new()
  [CdpPump]::Start($script:ws, $script:rxQueue, $script:rxAvail, $script:rxCts.Token)
  $script:cdpRequestId = 0
}
Connect-Cdp

function Send-Cdp([string]$method, [hashtable]$parameters, [int]$TimeoutSec = 20) {
  $script:cdpRequestId += 1
  $currentId = [int]$script:cdpRequestId
  Write-Host ('CDP_SEND '+$method+' id='+$currentId)
  $packet = @{id=$currentId;method=$method;params=$parameters} | ConvertTo-Json -Depth 15 -Compress
  $bytes = [text.encoding]::UTF8.GetBytes($packet)
  $ws.SendAsync([ArraySegment[byte]]::new($bytes), [Net.WebSockets.WebSocketMessageType]::Text, $true,
                [threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
  $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
  while ([DateTime]::UtcNow -lt $deadline) {
    if (-not $script:rxAvail.Wait($deadline - [DateTime]::UtcNow)) { break }
    $frame = $null
    if (-not $script:rxQueue.TryDequeue([ref]$frame)) { continue }
    if ($frame -like 'STREAM_DEAD|*') { throw ('CDP_STREAM_DEAD: ' + $frame.Substring(12)) }
    $parsed = $frame | ConvertFrom-Json
    if ($parsed.id -ne $currentId) { continue }
    if ($parsed.error) { throw "Browser protocol error: $($parsed.error.message)" }
    Write-Host ('CDP_OK '+$method+' id='+$currentId)
    return $parsed
  }
  Write-Host ('CDP_NO_RESPONSE '+$method+' id='+$currentId+' ws='+$script:ws.State)
  throw 'CDP_TIMEOUT'   # Nur die Frist laeuft ab; der Socket bleibt unangetastet.
}

function Parse-Cardmarket-Euro([string]$text) {
  if ([string]::IsNullOrWhiteSpace($text)) { return $null }
  $m=[regex]::Match($text,'(?<!\d)(?:\d{1,3}(?:[., ]\d{3})+|\d+)(?:[.,]\d{1,2})?(?!\d)')
  if (!$m.Success) {return $null}
  $amount=$m.Value.Trim().Replace(' ','')
  $comma=$amount.LastIndexOf(',')
  $dot=$amount.LastIndexOf('.')
  if($comma -ge 0 -and $dot -ge 0) {
    if($comma -gt $dot){$amount=$amount.Replace('.','').Replace(',','.')}
    else {$amount=$amount.Replace(',','')}
  } elseif($comma -ge 0) {
    if($amount -match ',\d{1,2}$'){$amount=$amount.Replace(',','.')}
    else {$amount=$amount.Replace(',','')}
  } elseif($dot -ge 0 -and $amount -match '^\d{1,3}(?:\.\d{3})+$') {
    $amount=$amount.Replace('.','')
  }
  $number=0.0
  if([double]::TryParse($amount,[Globalization.NumberStyles]::AllowDecimalPoint,[Globalization.CultureInfo]::InvariantCulture,[ref]$number) -and $number -gt 0){return $number}
  return $null
}

function Js([string]$expression, [int]$TimeoutSec = 20) {
  $reply = Send-Cdp 'Runtime.evaluate' @{expression=$expression;returnByValue=$true;awaitPromise=$true} $TimeoutSec
  if ($reply.result.exceptionDetails) { throw 'Browser script exception' }
  return $reply.result.result.value
}

function Is-CardmarketChallenge([string]$title, [bool]$challenge) {
  return ($challenge -or $title -match '(?i)nur einen moment|just a moment|attention required|security check|checking your browser')
}

function Move-To([string]$url) {
  Send-Cdp 'Page.navigate' @{url=$url} | Out-Null
  $desired = [uri]$url
  $attemptStart=[DateTime]::UtcNow
  $challengeStart=$null
  # The same persistent browser profile retains lawful session data.
  # Only WAIT for Cardmarket to finish its own challenge; do not click,
  # forge clearance cookies, replay private tokens, or bypass a challenge.
  for ($i = 0; $i -lt 380; $i++) {
    Start-Sleep -Milliseconds 400
    $state = Js 'JSON.stringify({path:location.pathname,href:location.href,ready:document.readyState,body:document.body?.innerText.length||0,title:document.title,challenge:!!document.querySelector("#challenge-running,#cf-challenge-running")})' 10
    if (!$state) { continue }
    $s = $state | ConvertFrom-Json
    if (Is-CardmarketChallenge ([string]$s.title) ([bool]$s.challenge)) {
      if($null -eq $challengeStart){
        $challengeStart=[DateTime]::UtcNow
        Write-Host 'CARDMARKET_CHALLENGE_WAITING: keeping persistent Edge session open'
      }
      if (([DateTime]::UtcNow-$challengeStart).TotalSeconds -ge $ChallengeWaitSeconds) {
        throw 'CARDMARKET_PROVIDER_CHALLENGE'
      }
      continue
    }
    $actual = [uri]$s.href
    $expectedQuery = [uri]::UnescapeDataString($desired.Query.TrimStart('?').Replace('+',' '))
    $actualQuery   = [uri]::UnescapeDataString($actual.Query.TrimStart('?').Replace('+',' '))
    $sameQuery = ($expectedQuery -eq $actualQuery) -or ($desired.AbsolutePath -ne ($LangCfg.PathPrefix + '/Products/Search'))
    if ($s.path -eq $desired.AbsolutePath -and $sameQuery -and $s.ready -eq 'complete' -and $s.body -gt 300) {
      if ($null -ne $challengeStart) { Write-Host 'CARDMARKET_CHALLENGE_CLEARED: continuing current card' }
      return $true
    }
    if (([DateTime]::UtcNow-$attemptStart).TotalSeconds -gt 45 -and $null -eq $challengeStart){return $false}
  }
  return $false
}

function Save-Progress([int]$done, [int]$total, [string]$status, [string]$card) {
  $s = @{done=$done;total=$total;status=$status;last_card=$card;language=$Language;updated_at=[DateTime]::UtcNow.ToString('o');file=$resultsPath}
  $s | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 -Path $progressPath
}

# --- Warteschlange + bisheriger Stand ------------------------------------------
$allCases = @(Import-Csv -Path $InputCsv -Encoding UTF8)
# Identity is needed for ALL variants, even when they already have a price.
# Priced bulk skips the costly offer pagination but still gets ID/URL mapping.
$cases = if ($ScanMode -eq 'missing') {
  @($allCases | Where-Object { [string]$_.needs_price -eq 'YES' })
} else { $allCases }
$bulkFeedOnly = @($allCases | Where-Object {
  [string]$_.scan_tier -eq '4' -and [string]$_.needs_price -eq 'NO'
}).Count
$runTotal = if ($MaxCases -gt 0) { [Math]::Min($cases.Count, $MaxCases) } else { $cases.Count }

$processed = [Collections.Generic.HashSet[string]]::new()
$latest = @{}
if (Test-Path $resultsPath) {
  Get-Content $resultsPath | ForEach-Object {
    try {
      $prev = $_ | ConvertFrom-Json
      $key = [string]$prev.key
      if ($key) { $latest[$key] = $prev }
    } catch {}
  }
}
$nowUtc = [datetime]::UtcNow

# Identitaets-Mapping: ID + URL dauerhaft, unabhaengig vom Preis.
$knownProductPages = @{}
foreach ($record in $latest.Values) {
  if ($record.status -notin @('FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE','NO_CONFIRMED_FILTERED_OFFERS',
                              'FILTER_UNAVAILABLE','FILTER_UNVERIFIED_EMPTY','MAPPED_NO_PRICE_REQUIRED',
                              'COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED')) { continue }
  $id = [string]$record.product_id
  if ($id -notmatch '^[0-9]+$') { continue }
  try {
    $candidate = [uri](([string]$record.url).Split('?')[0])
    if ($candidate.Scheme -ne 'https' -or $candidate.Host -ne 'www.cardmarket.com' -or
        !$candidate.AbsolutePath.StartsWith($LangCfg.PathPrefix + '/Products/Singles/')) { continue }
    $knownProductPages["$($record.card_id)|$id"] = $candidate.AbsoluteUri
  } catch {}
}

foreach ($case in $cases) {
  $key = '{0}|{1}' -f $case.cardyssey_karte, $case.variante_id
  if (!$latest.ContainsKey($key)) { continue }
  $prev = $latest[$key]
  $tier = [string]$case.scan_tier
  $refreshDays = if ($tier -in @('0','1')) { 7 } elseif ($tier -eq '2') { 14 } else { 30 }
  $isRecent = $false
  try { $isRecent = ([datetime]::Parse($prev.seen_at).ToUniversalTime() -gt $nowUtc.AddDays(-$refreshDays)) } catch {}
  # The previous translated-name search was frequently a false negative.
  # Retry those exactly once using official catalog English names.
  $newSearchAvailable=([string]$case.catalog_singleton_id -match '^[0-9]+$')
  $searchNotYetUpgraded=([string]$prev.status -eq 'NO_EXACT_NUMBER_SEARCH_HIT' -and
      $newSearchAvailable -and [string]$prev.lookup_strategy -notin @('CATALOG_NAME_FIRST_V1','LOADED_RESULTS_CHECK_V2'))
  $legacyEmptyResult=([string]$prev.status -eq 'NO_EXACT_NUMBER_SEARCH_HIT' -and
      [int]$prev.search_hits -eq 0 -and
      [string]$prev.lookup_strategy -ne 'LOADED_RESULTS_CHECK_V2')
  # A human-corrected link must be rescanned even if the old translated-name
  # lookup was recently marked as completed or failed.
  $manualRefreshDue=$false
  if ([string]$case.manual_scan_requested_at) {
    try {
      $requested=[datetime]::Parse([string]$case.manual_scan_requested_at).ToUniversalTime()
      $lastObserved=[datetime]::Parse([string]$prev.seen_at).ToUniversalTime()
      $manualRefreshDue=($requested -gt $lastObserved)
    } catch { $manualRefreshDue=$true }
  }
  $routeChanged=([string]$case.routing_state -eq 'VERIFIED_PRODUCT_ID' -and
     [string]$case.known_url -and [string]$prev.url -and
     ([string]$prev.url).Split('?')[0] -ne ([string]$case.known_url).Split('?')[0])
  if (($prev.status -ne 'ERROR' -and $prev.status -notlike 'DEFERRED*' -and
       -not $searchNotYetUpgraded -and -not $legacyEmptyResult -and -not $manualRefreshDue -and -not $routeChanged -and $isRecent)) {
    [void]$processed.Add($key)
  }
}

$deferredCount = 0
$searchCache=@{}
$searchCacheHits=0
$searchCacheMisses=0
$consecutiveProviderTimeouts=0
Save-Progress $processed.Count $runTotal 'RUNNING' ''

try {
  $candidateCases = if ($MaxCases -gt 0) { @($cases | Select-Object -First $MaxCases) } else { $cases }
  # Do not get stuck on the same provider-timeout rows at every launch.
  # New, not-yet-attempted cases get priority; deferred cases retry after 2h.
  # A retry is never counted as completed until actual evidence is received.
  $due=@($candidateCases | Where-Object {
    $k = '{0}|{1}' -f $_.cardyssey_karte, $_.variante_id
    -not $processed.Contains($k)
  })
  $priority = [Collections.Generic.List[object]]::new()
  $fresh = [Collections.Generic.List[object]]::new()
  $retry = [Collections.Generic.List[object]]::new()
  foreach($item in $due) {
    $k = '{0}|{1}' -f $item.cardyssey_karte, $item.variante_id
    $prior = if ($latest.ContainsKey($k)) { $latest[$k] } else { $null }
    $manualRequested=$false
    if([string]$item.manual_scan_requested_at){
      try{
        $requested=[datetime]::Parse([string]$item.manual_scan_requested_at).ToUniversalTime()
        $manualRequested=(!$prior -or $requested -gt [datetime]::Parse([string]$prior.seen_at).ToUniversalTime())
      }catch{$manualRequested=$true}
    }
    if($manualRequested){$priority.Add($item)}
    elseif ($prior -and [string]$prior.status -eq 'NO_EXACT_NUMBER_SEARCH_HIT' -and [int]$prior.search_hits -eq 0) {
      # Never let the old 8,902 false zero-results starve new cards.
      $retry.Add($item)
    }
    elseif ($prior -and [string]$prior.status -like 'DEFERRED*') {
      $oldEnough=$false
      try { $oldEnough=([datetime]::Parse([string]$prior.seen_at).ToUniversalTime() -lt $nowUtc.AddHours(-2)) } catch {}
      if($oldEnough){ $retry.Add($item) }
    } else { $fresh.Add($item) }
  }
  $ordered=@($priority.ToArray()) + @($fresh.ToArray()) + @($retry.ToArray())
  $selected = if ($BatchLimit -gt 0) { @($ordered | Select-Object -First $BatchLimit) } else { $ordered }
  foreach ($case in $selected) {
    $key = '{0}|{1}' -f $case.cardyssey_karte, $case.variante_id
    if ($processed.Contains($key)) { continue }
    # Diagnostics only: measure actual elapsed work before tuning delays.
    $caseTimer=[Diagnostics.Stopwatch]::StartNew()

    # Bulk-Karten: Preisstufe ueberspringen, ID-/URL-Mapping NICHT (Punkt 3).
    # Collect filtered offers on the SAME validated product page if this is
    # a valuable/special print or currently unpriced. Already priced bulk
    # still needs product identity, but not another costly offer scan.
    $priceNeeded = [string]$case.scan_tier -ne '4' -or [string]$case.needs_price -eq 'YES' -or !!([string]$case.manual_scan_requested_at)

    $out = [ordered]@{
      key=$key;card_id=$case.cardyssey_karte;variant_id=$case.variante_id;number=$case.kartennummer;
      set_id=$case.set_id;language=$Language;status='STARTED';query='';product_id='';url='';
      lookup_strategy='LOADED_RESULTS_CHECK_V2';
      offers_seen=0;verified_lang_nm_offers=0;sample_median_eur=$null;
      price_basis='VISIBLE_PAGE_ONLY_NOT_ALL_OFFERS_NOT_SOLD';all_pages_complete=$false;median_all_offers_eur=$null;identity_confirmed=$false;
      access_mode='UNKNOWN';search_cache_hit=$false;observed_url_version='';language_offers_observed=$false;seen_at=[DateTime]::UtcNow.ToString('o')
    }

    try {
      # Public Cardmarket catalogue is usable without an account. Prefer the
      # logged-in session when available, but never stop the queue for logout.
      $auth = (Js '!!document.querySelector("a[href*=User_Logout]")') -and (-not $ForcePublicMode)
      $out.access_mode = if ($auth) {'AUTHENTICATED'} else {'PUBLIC_LIMITED'}

      $name = [string]$case.kartenname_suche
      $number = [string]$case.kartennummer
      $out.query = "$name $number"
      $savedUrl = ''
      $allowedIds = @([string]$case.cardmarket_ids -split ',')
      # Trusted queue mapping: skip unreliable text search, but validate the
      # actual idProduct on the destination page before accepting it.
      if ([string]$case.routing_state -eq 'VERIFIED_PRODUCT_ID' -and
          @($allowedIds | Where-Object { $_ -match '^[0-9]+$' }).Count -eq 1 -and
          -not [string]::IsNullOrWhiteSpace([string]$case.known_url)) {
        try {
          $candidate = [uri](([string]$case.known_url).Split('?')[0])
          if ($candidate.Scheme -eq 'https' -and $candidate.Host -eq 'www.cardmarket.com' -and
              $candidate.AbsolutePath.StartsWith($LangCfg.PathPrefix + '/Products/Singles/')) {
            $savedUrl = $candidate.AbsoluteUri
          }
        } catch {}
      }

      if (!$savedUrl -and $latest.ContainsKey($key)) {
        $prior = $latest[$key]
        if (([string]$prior.product_id -in $allowedIds) -and $prior.identity_confirmed -eq $true) {
          try {
            $candidate = [uri](([string]$prior.url).Split('?')[0])
            if ($candidate.Scheme -eq 'https' -and $candidate.Host -eq 'www.cardmarket.com' -and
                $candidate.AbsolutePath.StartsWith($LangCfg.PathPrefix + '/Products/Singles/')) { $savedUrl = $candidate.AbsoluteUri }
          } catch {}
        }
      }
      if (!$savedUrl) {
        $reuse = @($allowedIds | Where-Object { $_ -and $knownProductPages.ContainsKey("$($case.cardyssey_karte)|$_") })
        if ($reuse.Count -eq 1) { $savedUrl = $knownProductPages["$($case.cardyssey_karte)|$($reuse[0])"] }
      }

      if ($savedUrl) {
        $out.search_hits = 1
        $likely = @([pscustomobject]@{url=$savedUrl;text="$name $number"})
      } else {
        # Prefer the official catalog's product name, NOT the translated
        # Cardyssey name. Cardmarket's search rarely indexes localized card
        # names plus collector numbers in the same query.
        $catalogName=[string]$case.catalog_search_name
        $searchQueries = @($out.query)
        if (![string]::IsNullOrWhiteSpace($catalogName) -and
            [string]$case.catalog_singleton_id -match '^[0-9]+$') {
          $searchQueries=@($catalogName,$out.query)
        }
        $likely=@()
        foreach($queryText in $searchQueries){
          $searchPath = $LangCfg.PathPrefix + '/Products/Search'
          $encoded = [uri]::EscapeDataString([string]$queryText)
          $searchUrl = 'https://www.cardmarket.com' + $searchPath + '?searchString=' + $encoded
          if ($searchCache.ContainsKey($searchUrl)) {
            $links=@($searchCache[$searchUrl]);$out.search_cache_hit=$true;$searchCacheHits++
          } else {
            $searchCacheMisses++
            if (!(Move-To $searchUrl)) {
              $out.status='DEFERRED_PROVIDER_TIMEOUT'
              $out.error='SEARCH_PAGE_TIMEOUT'
              ($out | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Encoding UTF8 -Path $resultsPath
              $consecutiveProviderTimeouts++
              Save-Progress $processed.Count $runTotal 'RUNNING' $case.cardyssey_karte
              if ($consecutiveProviderTimeouts -ge 3) {
                Save-Progress $processed.Count $runTotal 'PROVIDER_TIMEOUT' $case.cardyssey_karte
                break
              }
              Start-Sleep -Seconds ([Math]::Max(10,$DelaySeconds))
              continue
            }
            $searchExpr = 'JSON.stringify({title:document.title,blocked:/(?:nur einen moment|just a moment|attention required|checking your browser|captcha|robot check|access denied|zugriff verweigert|too many requests)/i.test(document.title+" "+(document.body?.innerText||"").slice(0,1600)),links:[...document.querySelectorAll("a[href*=\"/Products/Singles/\"]")].map(a=>({text:a.textContent.trim().slice(0,140),url:new URL(a.getAttribute("href"),location.origin).href})).filter(x=>x.text)})'
            # Cardmarket's result list is injected AFTER document.readyState
            # becomes complete. Reading immediately caused thousands of false
            # NO_EXACT_NUMBER_SEARCH_HIT records with search_hits=0.
            $searchResult=$null
            for($loadTry=0;$loadTry -lt 18;$loadTry++) {
              $searchResult = (Js $searchExpr 12) | ConvertFrom-Json
              if($searchResult.blocked -or @($searchResult.links).Count -gt 0) { break }
              Start-Sleep -Milliseconds 400
            }
            if ($searchResult.blocked) {
              $out.status='BLOCKED'
              $out.error='CARDMARKET_PROVIDER_CHALLENGE'
              Save-Progress $processed.Count $runTotal 'BLOCKED' $case.cardyssey_karte
              break
            }
            $consecutiveProviderTimeouts=0
            $links = @($searchResult.links)
            if($links.Count -eq 0){
              $out.search_results_unverified_empty=$true
              # Keep an empty search result as unverified; retry later.
              # Previously 8,902 cards were incorrectly recorded as missing.
              $out.error='ASYNC_SEARCH_RESULT_EMPTY_OR_NOT_LOADED'
            }
            if ($links.Count -gt 0) {
              if ($searchCache.Count -ge 250) { $searchCache.Clear() }
              $searchCache[$searchUrl] = $links
            }
          }
          $out.search_hits = $links.Count
          $out.query=[string]$queryText
          if ($queryText -eq $catalogName -and
              [string]$case.catalog_singleton_id -match '^[0-9]+$') {
            # Candidate ID must STILL be independently checked on the page.
            # Do not infer print identity from a product title alone.
            $likely=@($links | Select-Object -First 6)
          } else {
            $likely=@($links | Where-Object { $_.text -match "\b0*$([regex]::Escape($number))\b" })
          }
          if ($likely.Count -gt 0) { break }
        }
        if ($out.status -eq 'DEFERRED_PROVIDER_TIMEOUT') { continue }
        if ($out.status -eq 'PROVIDER_TIMEOUT' -or $out.status -eq 'BLOCKED') { break }
        # Multiple identical card-number hits: check the REAL idProduct, not search rank.
        # Limit page visits to avoid excessive requests; unresolved stays for review.
        if ($likely.Count -gt 1 -and $allowedIds.Count -gt 0) {
          $uniqueLinks = @($likely | Group-Object { ([string]$_.url).Split('?')[0] } |
            ForEach-Object { $_.Group[0] })
          $matchesById = @()
          foreach ($link in @($uniqueLinks | Select-Object -First 6)) {
            if ([string]$link.url -notmatch '^https://www[.]cardmarket[.]com/(de|en)/Pokemon/Products/Singles/') { continue }
            if (!(Move-To ([string]$link.url))) { continue }
            $pageProductId = ''
            for ($ii = 0; $ii -lt 12; $ii++) {
              $pageProductId = [string](Js 'document.querySelector("input[name=idProduct]")?.value||""' 10)
              if ($pageProductId -match '^[0-9]+$') { break }
              Start-Sleep -Milliseconds 400
            }
            if ($pageProductId -eq [string]$case.catalog_singleton_id -or
                ([string]$case.routing_state -eq 'VERIFIED_PRODUCT_ID' -and $pageProductId -in $allowedIds)) {
              $matchesById += $link
            }
            if ($matchesById.Count -gt 0) { break }
            Start-Sleep -Seconds ([Math]::Max(3,$DelaySeconds))
          }
          if ($matchesById.Count -eq 1) {
            $likely = @($matchesById[0])
          } else {
            $likely = @($uniqueLinks)
          }
        }
      }

      if ($likely.Count -eq 1) {
        $out.url = $likely[0].url
        $versionMatch=[regex]::Match(([string]$out.url).Split('?')[0],'(?i)(?:^|[-/])V([1-9][0-9]?)(?=[-/]|$)')
        if($versionMatch.Success){$out.observed_url_version='V'+$versionMatch.Groups[1].Value}
        if (!(Move-To $out.url)) { throw 'PRODUCT_PAGE_TIMEOUT' }
        $candidateId = ''
        for ($pi = 0; $pi -lt 20; $pi++) {
          $candidateId = [string](Js 'document.querySelector("input[name=idProduct]")?.value||""')
          if ($candidateId -match '^[0-9]+$') { break }
          Start-Sleep -Milliseconds 500
        }
        $out.product_id = $candidateId
        $allowed = [string]$case.cardmarket_ids -split ','
        if (!$candidateId) {
          $out.status = 'NO_PRODUCT_ID'
          ($out | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Encoding UTF8 -Path $unverifyPath
        } elseif ($setSlugGuards.ContainsKey([string]$case.set_id) -and
                  ([string]$out.url -notmatch ('/Products/Singles/'+[regex]::Escape($setSlugGuards[[string]$case.set_id])+'(?:/|-)'))) {
          $out.status='PRODUCT_SET_SLUG_MISMATCH'
          $out.error='PRODUCT_IS_IN_DIFFERENT_CARDMARKET_EXPANSION'
          ($out | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Encoding UTF8 -Path $unverifyPath
        } elseif ($candidateId -ne [string]$case.catalog_singleton_id -and
                  -not ([string]$case.routing_state -eq 'VERIFIED_PRODUCT_ID' -and $candidateId -in $allowed)) {
          # A nonempty scraped ID is NOT proof of this exact card print. Only
          # a verified human route or a verified-set catalog singleton can
          # promote this product URL to a durable mapped identity.
          $out.status = 'PRODUCT_ID_NOT_IN_VERIFIED_SET'
          $out.error = 'UNVERIFIED_SET_OR_AMBIGUOUS_PRINT'
          ($out | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Encoding UTF8 -Path $unverifyPath
        } else {
          # Identitaet bestaetigt: ID + URL dauerhaft, unabhaengig vom Preis.
          $out.identity_confirmed = $true
          if (-not $priceNeeded) {
            $out.status = 'MAPPED_NO_PRICE_REQUIRED'
          } else {
            $out.status = 'PRODUCT_PAGE_MATCH_REVIEW'
            $reverseCode = if ([string]$case.drucktyp -match '(?i)reverse') { 'Y' } elseif ([string]$case.drucktyp -match '(?i)normal') { 'N' } else { '0' }
            $firstCode = if ([string]$case.stempel -match '(?i)1\. auflage|first.edition') { 'Y' } elseif ([string]$case.sonderdruck -match '(?i)^(unbegrenzt|unlimited)$') { 'N' } else { '0' }
            $out.expected_reverse_holo = $reverseCode
            $out.expected_first_edition = $firstCode
            $filterName = 'input[name=\"language[' + $LangCfg.LanguageId + ']\"]'
            $langNames = ($LangCfg.LanguageNames | ForEach-Object { '"'+$_+'"' }) -join ','
            $filterOk = Js ('(()=>{let f=[...document.forms].find(f=>f.action.includes("Product_Filter_FilterProduct"));let l=f?.querySelector("' + $filterName + '");if(!l)return false;[...f.querySelectorAll("input")].filter(x=>x.name.startsWith("language[")).forEach(x=>x.checked=false);l.checked=true;f.querySelector("[name=minCondition]").value="2";f.querySelector("[name=\"extra[isSigned]\"]").value="N";f.querySelector("[name=\"extra[isAltered]\"]").value="N";const choices=[["extra[isReverseHolo]","'+$reverseCode+'"],["extra[isFirstEd]","'+$firstCode+'"]];for(const [name,want] of choices){const el=f.elements.namedItem(name);if(!el){if(want==="Y")return false;continue;}el.value=want;}f.requestSubmit(f.querySelector("[name=apply]"));return true})()')
            if ($filterOk) {
              $rowsExpr = 'JSON.stringify({filtered:document.querySelector("' + $filterName + '")?.checked===true&&[...document.querySelectorAll("input")].filter(x=>x.name.startsWith("language[")&&x.checked).length===1&&new URL(location.href).searchParams.get("language")==="'+$LangCfg.LanguageId+'"&&new URL(location.href).searchParams.get("minCondition")==="2"&&document.querySelector("[name=minCondition]")?.value==="2"&&[["isReverseHolo","'+$reverseCode+'"],["isFirstEd","'+$firstCode+'"]].every(([k,v])=>{const u=new URL(location.href);const f=[...document.forms].find(x=>x.action.includes("Product_Filter_FilterProduct"));const e=f?.elements.namedItem("extra["+k+"]");return v==="0"?(!u.searchParams.has(k)||u.searchParams.get(k)==="0"):(e?(u.searchParams.get(k)===v&&e.value===v):(v==="N"&&!u.searchParams.has(k)))}),rows:[...document.querySelectorAll(".article-row")].slice(0,300).map(r=>({id:r.id,condition:r.querySelector(".article-condition")?.getAttribute("data-bs-original-title")||r.querySelector(".article-condition")?.getAttribute("title"),language:[...r.querySelectorAll("[data-bs-original-title],[title]")].map(n=>n.getAttribute("data-bs-original-title")||n.getAttribute("title")).find(t=>[' + $langNames + '].includes(t)),price:r.querySelector(".price-container")?.innerText.trim(),flags:[...r.querySelectorAll("[title],[data-bs-original-title]")].map(x=>x.getAttribute("data-bs-original-title")||x.getAttribute("title")).filter(x=>x==="Reverse Holo"||x==="First Edition")})),hasMore:!!document.querySelector("#loadMoreButton"),page:Number(document.querySelector("#articlePage")?.value||0),totalRows:document.querySelectorAll(".article-row").length})'
              $data = $null
              for ($fi = 0; $fi -lt 12; $fi++) {
                Start-Sleep -Milliseconds 500
                $data = Js $rowsExpr | ConvertFrom-Json
                if ($data -and $data.filtered) { break }
              }
              if (!$data) { throw 'FILTER_STATE_UNREADABLE' }
              $out.offer_pages_attempted=0
              $out.pagination_failure=''
              # Public mode collects visible rows, without assuming that a
              # public session can paginate or that its sample is exhaustive.
              if (-not $auth) { $out.pagination_failure='PUBLIC_SESSION_LIMITED_SAMPLE' }
              # Logged-in mode progressively appends batches (site may cap at 300).
              if ($data.filtered -and $auth) {
                for ($pageAttempt=0; $pageAttempt -lt 6 -and $data.hasMore; $pageAttempt++) {
                  $beforeRows=[int]$data.totalRows
                  if ($beforeRows -ge 300) { $out.pagination_failure='CARDMARKET_300_CAP';break }
                  $out.offer_pages_attempted++
                  # Do not mistake a hidden/disabled load-more button for a successful click.
                  $clicked=Js '(()=>{const b=document.querySelector("#loadMoreButton");if(!b)return "MISSING";if(b.disabled||b.classList.contains("d-none")||getComputedStyle(b).display==="none")return "DISABLED";b.click();return "CLICKED"})()'
                  if ($clicked -ne 'CLICKED') {
                    $out.pagination_failure=if($clicked -eq 'DISABLED') {'LOAD_MORE_DISABLED_OR_LIMIT_REACHED'} else {'LOAD_MORE_BUTTON_LOST'}
                    break
                  }
                  $progressed=$false
                  for ($wait=0; $wait -lt 18; $wait++) {
                    Start-Sleep -Milliseconds 500
                    $next=Js $rowsExpr | ConvertFrom-Json
                    if (!$next.filtered) { $out.pagination_failure='FILTER_CHANGED_DURING_PAGINATION';break }
                    if ([int]$next.totalRows -gt $beforeRows) {
                      $progressed=$true
                      $data=$next
                      break
                    }
                  }
                  if (!$progressed) {
                    if (!$out.pagination_failure) {
                      $disabled=Js '(()=>{const b=document.querySelector("#loadMoreButton");return !!b&&(b.disabled||b.classList.contains("d-none")||getComputedStyle(b).display==="none")})()'
                      $out.pagination_failure=if ($disabled) {'LOAD_MORE_DISABLED_OR_LIMIT_REACHED'} else {'LOAD_MORE_NO_NEW_OFFERS'}
                    }
                    break
                  }
                  Start-Sleep -Milliseconds 800
                }
              }
              # Login may expire while fetching pages; a public result is
              # never promoted into a full-market price on that transition.
              $stillSignedIn = (Js '!!document.querySelector("a[href*=User_Logout]")') -and (-not $ForcePublicMode)
              if (-not $stillSignedIn) {
                $auth=$false
                $out.access_mode='PUBLIC_LIMITED'
                if (-not $out.pagination_failure) { $out.pagination_failure='SESSION_EXPIRED_OR_PUBLIC' }
              }
              $out.all_pages_complete=($auth -and $data.filtered -and
                -not $data.hasMore -and [int]$data.totalRows -lt 300 -and
                -not $out.pagination_failure)
              # Qualitaetskontrolle (Punkt 5): nur Zeilen, die Sprach- UND
              # Zustandskriterium einzeln erfuellen, zaehlen als Filtertreffer.
              $out.offers_seen = @($data.rows).Count
              $accepted = @($data.rows | Where-Object {
                $_.language -in $LangCfg.LanguageNames -and
                $_.condition -in $LangCfg.ConditionNames -and
                ($_.condition -notmatch 'Played|Poor|Damaged') -and
                $_.price -match '[0-9]' -and
                ($reverseCode -eq '0' -or
                  (($reverseCode -eq 'Y') -eq ('Reverse Holo' -in @($_.flags)))) -and
                ($firstCode -eq '0' -or
                  (($firstCode -eq 'Y') -eq ('First Edition' -in @($_.flags))))
              })
              $out.verified_lang_nm_offers = $accepted.Count
              $out.language_offers_observed=($accepted.Count -gt 0)
              $seenOfferIds=@($data.rows | ForEach-Object { [string]$_.id })
              $uniqueOfferIds=@($seenOfferIds | Sort-Object -Unique)
              if ($uniqueOfferIds.Count -ne [int]$data.totalRows -or $seenOfferIds -contains '') {
                $out.all_pages_complete=$false
                $out.pagination_failure='DUPLICATE_OR_MISSING_OFFER_ID'
              }
              if ($accepted.Count -ne [int]$data.totalRows) {
                $out.all_pages_complete=$false
                if (!$out.pagination_failure) { $out.pagination_failure='MISMATCHED_OFFER_FILTER_FLAGS' }
              }

              if ($data.filtered -and $accepted.Count -ge 1) {
                $nums = @($accepted | ForEach-Object {
                  Parse-Cardmarket-Euro ([string]$_.price)
                } | Where-Object { $_ -ne $null } | Sort-Object)
                if ($nums.Count -gt 0) {
                  $out.lowest_ask_eur=$nums[0]
                  $cheapest=@($nums | Select-Object -First 5)
                  $out.entry_five_median_eur=if($cheapest.Count%2) {$cheapest[[int][Math]::Floor($cheapest.Count/2)]}else{[Math]::Round(($cheapest[$cheapest.Count/2-1]+$cheapest[$cheapest.Count/2])/2,2)}
                  $mid = [int][Math]::Floor($nums.Count/2)
                  $out.sample_median_eur = if ($nums.Count % 2) { $nums[$mid] } else { [math]::Round(($nums[$mid-1]+$nums[$mid])/2, 2) }
                }
                $out.median_all_offers_eur=if($out.all_pages_complete) {$out.sample_median_eur} else {$null}
                $out.status=if($out.all_pages_complete) {'COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED'} else {'FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE'}
              } elseif ($data.filtered) {
                $out.status = 'FILTER_UNVERIFIED_EMPTY'
              } else {
                $out.status = 'FILTER_NOT_APPLIED'
              }
            } else {
              $out.status = 'FILTER_UNAVAILABLE'
            }
          }
          if ($out.identity_confirmed -and $out.product_id -match '^[0-9]+$') {
            $knownProductPages["$($case.cardyssey_karte)|$($out.product_id)"] = $out.url.Split('?')[0]
          }
        }
      } else {
        $out.status = if ($likely.Count -gt 1) { 'MULTIPLE_SEARCH_HITS' } elseif ($out.search_results_unverified_empty -eq $true) { 'DEFERRED_SEARCH_RESULTS_UNVERIFIED' } else { 'NO_EXACT_NUMBER_SEARCH_HIT' }
        if ($out.status -eq 'NO_EXACT_NUMBER_SEARCH_HIT') { $out.error='NAME_NUMBER_TEXT_SEARCH_NOT_CONCLUSIVE' }
        ($out | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Encoding UTF8 -Path $unverifyPath
      }
    } catch {
      $message = $_.Exception.Message
      if ($message -match 'CARDMARKET_PROVIDER_CHALLENGE') {
        $out.status = 'BLOCKED'
        $out.error = 'CARDMARKET_PROVIDER_CHALLENGE'
        $out.elapsed_ms=[int]$caseTimer.ElapsedMilliseconds
        ($out | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Encoding UTF8 -Path $resultsPath
        Save-Progress $processed.Count $runTotal 'BLOCKED' $case.cardyssey_karte
        break
      }
      $socketDead = ($ws.State -ne [Net.WebSockets.WebSocketState]::Open) -or
                    ($message -match 'CDP_STREAM_DEAD|CDP_TIMEOUT|WebSocket|websocket|abgebrochen|cancelled|canceled')
      if ($socketDead) {
        $out.status = 'DEFERRED_SOCKET'
        $out.error = $message.Substring(0, [Math]::Min(180, $message.Length))
        ($out | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Encoding UTF8 -Path $resultsPath
        [pscustomobject]@{at=[DateTime]::UtcNow.ToString('o');card=$case.cardyssey_karte;message=$message;socket=[string]$ws.State} |
          ConvertTo-Json -Compress | Add-Content -Encoding UTF8 -Path $errorPath
        [void]$processed.Add($key)
        $deferredCount++
        Save-Progress $processed.Count $runTotal 'RUNNING' $case.cardyssey_karte
        if ($deferredCount -gt 25) {
          Save-Progress $processed.Count $runTotal 'CONNECTION_LOST' $case.cardyssey_karte
          break
        }
        Start-Sleep -Seconds 5
        try {
          Connect-Cdp
          # Re-evaluate access mode on the next card; lost login is not fatal.
          $auth = (Js '!!document.querySelector("a[href*=User_Logout]")') -and (-not $ForcePublicMode)
        } catch {
          Save-Progress $processed.Count $runTotal 'CONNECTION_LOST' $case.cardyssey_karte
          break
        }
        continue
      }
      $out.status = 'ERROR'
      $out.error = $message.Substring(0, [Math]::Min(180, $message.Length))
    }

    $caseTimer.Stop()
    $out.elapsed_ms=[int]$caseTimer.ElapsedMilliseconds
    ($out | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Encoding UTF8 -Path $resultsPath
    [void]$processed.Add($key)
    Save-Progress $processed.Count $runTotal 'RUNNING' $case.cardyssey_karte

    if ($out.status -in @('MULTIPLE_SEARCH_HITS','NO_EXACT_NUMBER_SEARCH_HIT','PRODUCT_ID_NOT_IN_VERIFIED_SET')) {
      Start-Sleep -Seconds ([Math]::Max(4, [Math]::Min(6, $DelaySeconds)))
    } else {
      Start-Sleep -Seconds ([Math]::Max(3, $DelaySeconds))
    }
  }

  # --- Qualitaetskontroll-Bericht (Punkt 7) --------------------------------
  $currentStatus=(Get-Content $progressPath -Raw | ConvertFrom-Json).status
  if ($currentStatus -notin @('LOGIN_REQUIRED','BLOCKED','PROVIDER_TIMEOUT','CONNECTION_LOST')) {
    if ($deferredCount -gt 0) { Save-Progress $processed.Count $runTotal 'COMPLETED_WITH_DEFERRED' '' }
    elseif ($processed.Count -ge $runTotal) { Save-Progress $processed.Count $runTotal 'COMPLETED' '' }
    else { Save-Progress $processed.Count $runTotal 'BATCH_COMPLETE_MORE_PENDING' '' }
  }
  $statuses = @{}
  if (Test-Path $resultsPath) {
    Get-Content $resultsPath | ForEach-Object {
      try { $e = $_ | ConvertFrom-Json; if ($e.key) { $statuses[[string]$e.key] = $e } } catch {}
    }
  }
  $validIdentityStatuses = @('FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE','NO_CONFIRMED_FILTERED_OFFERS','FILTER_UNAVAILABLE','FILTER_UNVERIFIED_EMPTY','MAPPED_NO_PRICE_REQUIRED','FILTER_NOT_APPLIED','COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED')
  $confirmed = @($statuses.Values | Where-Object { $_.identity_confirmed -eq $true -and $_.status -in $validIdentityStatuses })
  $withUrl   = @($confirmed | Where-Object { $_.url })
  # Nur bestaetigte Angebots-Mediane zaehlen als verifizierte Preise.
  # Angebotsmedian != offizieller Cardmarket-Trendpreis (daher die Kennzeichnung).
  $withPrice = @($statuses.Values | Where-Object { $_.sample_median_eur -ne $null -and
                 $_.status -in @('FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE','COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED') })
  $missing = @($selected | Where-Object {
      $k = '{0}|{1}' -f $_.cardyssey_karte,$_.variante_id
      (-not $statuses.ContainsKey($k)) -or ($statuses[$k].identity_confirmed -ne $true) -or ($statuses[$k].status -notin $validIdentityStatuses)
  })
  $reasons = @($missing | ForEach-Object {
      $k = '{0}|{1}' -f $_.cardyssey_karte,$_.variante_id
      if (!$statuses.ContainsKey($k)) { 'NOT_ATTEMPTED' } else { [string]$statuses[$k].status }
  } | Group-Object | ForEach-Object { '{0}: {1}' -f $_.Name,$_.Count })
  $report = [ordered]@{
    language               = $Language
    expected_variants      = $runTotal
    bulk_feed_only_variants = $bulkFeedOnly
    search_cache_hits = $searchCacheHits
    search_cache_misses = $searchCacheMisses
    progress_status        = (Get-Content $progressPath -Raw | ConvertFrom-Json).status
    reviewed_variants      = $statuses.Count
    assigned_product_ids   = $confirmed.Count
    stored_urls            = $withUrl.Count
    filtered_offer_sample_quotes = $withPrice.Count
    complete_filtered_asking_medians_print_unverified = @($statuses.Values | Where-Object { $_.status -eq 'COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED' }).Count
    verified_language_variant_prices = 0
    price_basis            = 'active_asking_offers_not_sold; full_only_if_completed'
    missing_assignments    = $missing.Count
    missing_by_reason      = $reasons
    unreviewed_variants    = [Math]::Max(0,$runTotal-$statuses.Count)
    deferred_socket_errors = $deferredCount
    generated_at           = [DateTime]::UtcNow.ToString('o')
  }
  ($report | ConvertTo-Json -Depth 4) | Set-Content -Encoding UTF8 -Path (Join-Path $OutputDir "qc-report-$Language.json")
  Write-Host ($report | ConvertTo-Json -Depth 4)
} finally {
  try { $script:rxCts.Cancel() } catch {}
  try { $ws.Dispose() } catch {}
}
