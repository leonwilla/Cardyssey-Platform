# Cardyssey Cardmarket browser review. Uses the pre-authenticated, dedicated
# Chrome profile via localhost CDP. Does not export credentials or cookies.
param(
  [string]$InputCsv = "C:\Users\TV\AppData\Local\Cardyssey\CardmarketCollector\queue.csv",
  [string]$OutputDir = "C:\Users\TV\AppData\Local\Cardyssey\CardmarketCollector",
  [int]$MaxCases = 1460,
  [int]$DelaySeconds = 12
)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$resultsPath = Join-Path $OutputDir "product-page-review.jsonl"
$progressPath = Join-Path $OutputDir "progress.json"
$targets = @(Invoke-RestMethod "http://127.0.0.1:9222/json/list")
$target = @($targets | Where-Object { $_.type -eq "page" -and $_.url -match "cardmarket.com" })[0]
if ($target -is [array]) {$target=$target[0]}
if (!$target) { throw "Open the signed-in Cardmarket page in the isolated Chrome profile with localhost debugging enabled." }
$ws = [Net.WebSockets.ClientWebSocket]::new()
$ws.Options.SetRequestHeader("Origin", "http://localhost")
$ws.ConnectAsync([uri]$target.webSocketDebuggerUrl, [threading.cancellationtoken]::None).GetAwaiter().GetResult() | Out-Null
$script:id = 0
function Send-Cdp([string]$method, [hashtable]$parameters) {
  $script:id += 1
  $currentId = $script:id
  $packet = @{id=$currentId;method=$method;params=$parameters} | ConvertTo-Json -Depth 15 -Compress
  $bytes = [text.encoding]::UTF8.GetBytes($packet)
  $ws.SendAsync([ArraySegment[byte]]::new($bytes),[Net.WebSockets.WebSocketMessageType]::Text,$true,[threading.cancellationtoken]::None).GetAwaiter().GetResult() | Out-Null
  $buffer = [byte[]]::new(262144)
  $all = New-Object System.IO.MemoryStream
  for ($i=0; $i -lt 200; $i++) {
    $response = $ws.ReceiveAsync([ArraySegment[byte]]::new($buffer),[threading.cancellationtoken]::None).GetAwaiter().GetResult()
    $all.Write($buffer,0,$response.Count)
    if (!$response.EndOfMessage) {continue}
    $raw = [text.encoding]::UTF8.GetString($all.ToArray())
    $all.SetLength(0)
    $parsed = $raw | ConvertFrom-Json
    if ($parsed.id -ne $currentId) {continue}
    if ($parsed.error) { throw "Browser protocol error: $($parsed.error.message)" }
    return $parsed
  }
  throw "Browser protocol timed out"
}
function Js([string]$expression) {
  $reply = Send-Cdp "Runtime.evaluate" @{expression=$expression;returnByValue=$true;awaitPromise=$true}
  if ($reply.result.exceptionDetails) {throw "Browser script exception"}
  return $reply.result.result.value
}
function Move-To([string]$url) {
  Send-Cdp "Page.navigate" @{url=$url} | Out-Null
  $desired = [uri]$url
  for ($i=0;$i -lt 38;$i++) {
    Start-Sleep -Milliseconds 600
    $state=Js 'JSON.stringify({path:location.pathname,href:location.href,ready:document.readyState,body:document.body?.innerText.length||0})'
    if (!$state) {continue}
    $s=$state | ConvertFrom-Json
    $actual=[uri]$s.href
    $expectedQuery=[uri]::UnescapeDataString($desired.Query.TrimStart('?').Replace('+',' '))
    $actualQuery=[uri]::UnescapeDataString($actual.Query.TrimStart('?').Replace('+',' '))
    $sameQuery=($expectedQuery -eq $actualQuery) -or ($desired.AbsolutePath -ne '/de/Pokemon/Products/Search')
    if ($s.path -eq $desired.AbsolutePath -and $sameQuery -and $s.ready -eq "complete" -and $s.body -gt 300) {return $true}
  }
  return $false
}
function Save-Progress([int]$done,[int]$total,[string]$status,[string]$card) {
  $s = @{done=$done;total=$total;status=$status;last_card=$card;updated_at=[DateTime]::UtcNow.ToString("o");file=$resultsPath}
  $s | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 -Path $progressPath
}
$cases = @(Import-Csv -Path $InputCsv -Encoding UTF8)
$processed = [Collections.Generic.HashSet[string]]::new()
if (Test-Path $resultsPath) {
  Get-Content $resultsPath | ForEach-Object {
    try { $prev=$_ | ConvertFrom-Json; if ($prev.status -ne 'ERROR') {[void]$processed.Add([string]$prev.key)} } catch {}
  }
}
$completed=0
$runTotal=[Math]::Min($cases.Count,$MaxCases)
Save-Progress $processed.Count $runTotal "RUNNING" ""
try {
  foreach ($case in ($cases | Select-Object -First $MaxCases)) {
    $key="{0}|{1}" -f $case.cardyssey_karte,$case.variante_id
    if ($processed.Contains($key)) {continue}
    $out=[ordered]@{key=$key;card_id=$case.cardyssey_karte;variant_id=$case.variante_id;number=$case.kartennummer;set_id=$case.set_id;status="STARTED";query="";product_id="";url="";offers_seen=0;de_nm_offers=0;sample_median_eur=$null;price_basis="lowest_page_active_asking_sample_not_sold";seen_at=[DateTime]::UtcNow.ToString("o")}
    try {
      $auth=Js 'document.body.innerText.includes("AUSLOGGEN")'
      if ($auth -ne $true) { Save-Progress $processed.Count $runTotal "LOGIN_REQUIRED" $case.cardyssey_karte;break }
      $name=[string]$case.kartenname_suche
      $number=[string]$case.kartennummer
      $out.query="$name $number"
      $url="https://www.cardmarket.com/de/Pokemon/Products/Search?searchString="+[uri]::EscapeDataString($out.query)
      if (!(Move-To $url)) {throw "SEARCH_PAGE_TIMEOUT"}
      $blocked = Js '/captcha|robot check|access denied|zugriff verweigert|too many requests/i.test(document.title+" "+document.body?.innerText.slice(0,1600))'
      if ($blocked) {Save-Progress $processed.Count $runTotal "BLOCKED" $case.cardyssey_karte;break}
      $stillLogged=Js 'document.body.innerText.includes("AUSLOGGEN")'
      if (!$stillLogged) {Save-Progress $processed.Count $runTotal "LOGIN_REQUIRED" $case.cardyssey_karte;break}
      $links = Js 'JSON.stringify([...document.querySelectorAll("a[href*=\u0027/Products/Singles/\u0027]")].map(a=>({text:a.innerText.trim().slice(0,140),url:a.href})).filter(x=>x.text))' | ConvertFrom-Json
      $out.search_hits=@($links).Count
      $likely=@($links | Where-Object { $_.text -match "\b0*$([regex]::Escape($number))\b" })
      if ($likely.Count -eq 1) {
        $out.url=$likely[0].url
        if (!(Move-To $out.url)) {throw "PRODUCT_PAGE_TIMEOUT"}
        $candidateId=[string](Js 'document.querySelector("input[name=idProduct]")?.value||""')
        $out.product_id=$candidateId
        $allowed=[string]$case.cardmarket_ids -split ","
        if ($allowed.Count -gt 0 -and $allowed[0] -and $candidateId -notin $allowed) {
          $out.status="PRODUCT_ID_NOT_IN_VERIFIED_SET"
        } elseif (!$candidateId) {
          $out.status="NO_PRODUCT_ID"
        } else {
          $out.status="PRODUCT_PAGE_MATCH_REVIEW"
          $filterOk = Js '(()=>{let f=[...document.forms].find(f=>f.action.includes("Product_Filter_FilterProduct"));let l=f?.querySelector("input[name=\"language[3]\"]");if(!l)return false;l.checked=true;f.querySelector("[name=minCondition]").value="2";f.querySelector("[name=\"extra[isSigned]\"]").value="N";f.querySelector("[name=\"extra[isAltered]\"]").value="N";f.requestSubmit(f.querySelector("[name=apply]"));return true})()'
          if ($filterOk) {
            Start-Sleep -Seconds 2
            $data = Js 'JSON.stringify({filtered:document.querySelector("input[name=\"language[3]\"]")?.checked===true&&document.querySelector("[name=minCondition]")?.value==="2",rows:[...document.querySelectorAll(".article-row")].slice(0,100).map(r=>({id:r.id,condition:r.querySelector(".article-condition")?.getAttribute("data-bs-original-title")||r.querySelector(".article-condition")?.getAttribute("title"),language:[...r.querySelectorAll("[data-bs-original-title],[title]")].map(n=>n.getAttribute("data-bs-original-title")||n.getAttribute("title")).find(t=>t==="Deutsch"||t==="Englisch")||null,price:r.querySelector(".price-container")?.innerText.trim()}))})' | ConvertFrom-Json
            $out.offers_seen=@($data.rows).Count
            $accepted=@($data.rows | Where-Object { $_.language -eq "Deutsch" -and $_.condition -in @("Near Mint","Mint") -and $_.price -match "[0-9]" })
            $out.de_nm_offers=$accepted.Count
            if ($data.filtered -and $accepted.Count -ge 1) {
              $nums=@($accepted | ForEach-Object { $m=[regex]::Match($_.price,"\d+(?:[.,]\d{1,2})?");if($m.Success){[double]::Parse($m.Value.Replace(",","."),[globalization.cultureinfo]::InvariantCulture)} } | Sort-Object)
              if ($nums.Count -gt 0) { $mid=[int][Math]::Floor($nums.Count/2);$out.sample_median_eur=if($nums.Count%2){$nums[$mid]}else{[math]::Round(($nums[$mid-1]+$nums[$mid])/2,2)} }
              $out.status="FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE"
            } else {$out.status="NO_CONFIRMED_FILTERED_OFFERS"}
          } else {$out.status="FILTER_UNAVAILABLE"}
        }
      } else { $out.status=if($likely.Count -gt 1){"MULTIPLE_SEARCH_HITS"}else{"NO_EXACT_NUMBER_SEARCH_HIT"} }
    } catch { $out.status="ERROR"; $out.error=$_.Exception.Message.Substring(0,[Math]::Min(180,$_.Exception.Message.Length)) }
    ($out | ConvertTo-Json -Depth 6 -Compress) | Add-Content -Encoding UTF8 -Path $resultsPath
    [void]$processed.Add($key)
    Save-Progress $processed.Count $runTotal "RUNNING" $case.cardyssey_karte
    Start-Sleep -Seconds ([Math]::Max(3,$DelaySeconds))
  }
  if ((Get-Content $progressPath -Raw | ConvertFrom-Json).status -notin @("LOGIN_REQUIRED","BLOCKED")) {Save-Progress $processed.Count $runTotal "COMPLETED_OR_LIMIT_REACHED" ""}
} finally { $ws.Dispose() }
