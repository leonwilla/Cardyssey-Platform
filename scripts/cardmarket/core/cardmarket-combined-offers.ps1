# Share a product document only between independently catalog-matched standard
# variants. Each output retains its own language, identity and offer evidence.
function Test-CardmarketCombinedCaseDue($Case, $Previous, $Epoch, [datetime]$NowUtc) {
  if(!$Previous){return $true}
  try {$seen=[DateTimeOffset]::Parse([string]$Previous.seen_at).UtcDateTime} catch {return $true}
  if([string]$Case.manual_scan_requested_at){
    try {if([DateTimeOffset]::Parse([string]$Case.manual_scan_requested_at).UtcDateTime -gt $seen){return $true}} catch {return $false}
  }
  if(Test-CardmarketUnresolvedObservation $Previous $Epoch){return $seen -le $NowUtc.AddHours(-72)}
  if([string]$Previous.status -eq 'SINGLE_LANGUAGE_FALLBACK_REQUIRED'){return $false}
  if([string]$Previous.status -like 'DEFERRED*'){return $seen -le $NowUtc.AddHours(-2)}
  if([string]$Previous.status -in @('STARTED','ERROR','LOGIN_REQUIRED')){return $true}
  if($null -ne $Epoch){return $seen -lt $Epoch}
  $days=if([string]$Case.scan_tier -in @('0','1')){7}elseif([string]$Case.scan_tier -eq '2'){14}else{30}
  return $seen -le $NowUtc.AddDays(-$days)
}

function Find-CardmarketCombinedTarget {
  param($Case, [string]$ProductUrl, [hashtable]$PeerCases, [hashtable]$PeerLatest,
        [hashtable]$SetGuards, $Epoch, [datetime]$NowUtc)
  $catalogProductId=[string]$Case.catalog_singleton_id
  if($catalogProductId -notmatch '^[0-9]{4,12}$' -or
     !$SetGuards.ContainsKey([string]$Case.set_id) -or
     [string]$Case.catalog_expansion_id -notmatch '^[0-9]+$') {return $null}
  $u=$null
  try {$u=[uri]$ProductUrl} catch {return $null}
  if($u.Scheme -ne 'https' -or $u.Host -ne 'www.cardmarket.com' -or
     $u.AbsolutePath -notmatch '^/(de|en)/Pokemon/Products/Singles/([^/]+)/([^/]+)$' -or
     $Matches[2] -ne $SetGuards[[string]$Case.set_id] -or
     $Matches[3] -match '(?i)(?:^|-)V[1-9][0-9]?(?:-|$)'){return $null}
  $matchingCases=@(foreach($peer in @($PeerCases[[string]$Case.cardyssey_karte])){
    if(!$peer -or [string]$peer.catalog_singleton_id -ne $catalogProductId -or
       [string]$peer.catalog_expansion_id -ne [string]$Case.catalog_expansion_id -or
       [string]$peer.set_id -ne [string]$Case.set_id -or
       [string]$peer.kartennummer -ne [string]$Case.kartennummer -or
       [string]$peer.drucktyp -ne [string]$Case.drucktyp){continue}
    $compatible=$true
    foreach($row in @($Case,$peer)){
      if([string]$row.candidate_status -eq 'SET_EXPANSION_AMBIGUOUS' -or
         ([string]$row.foil).Trim() -or ([string]$row.sonderdruck).Trim() -or
         ([string]$row.stempel).Trim() -notin @('','[]','null') -or
         [string]$row.drucktyp -notmatch '(?i)^(normal|nonholo|common|holo|reverse)$' -or
         [string]$row.delta_browser_skip -eq 'YES' -or
         (Get-CardmarketBrowserQueueTier $row $false) -ge 4){$compatible=$false;break}
      $ids=@(([string]$row.cardmarket_ids) -split ',' | Where-Object {$_})
      if($ids.Count -and $catalogProductId -notin $ids){$compatible=$false;break}
      if([string]$row.known_url){
        try {$known=[uri]([string]$row.known_url)} catch {$compatible=$false;break}
        if($known.Scheme -ne 'https' -or $known.Host -ne $u.Host -or
           $known.AbsolutePath.Substring(3) -ne $u.AbsolutePath.Substring(3)){$compatible=$false;break}
      }
    }
    $key='{0}|{1}' -f $peer.cardyssey_karte,$peer.variante_id
    if($compatible -and (Test-CardmarketCombinedCaseDue $peer $PeerLatest[$key] $Epoch $NowUtc)){$peer}
  })
  if($matchingCases.Count -eq 1){return $matchingCases[0]}
  return $null
}

function New-CardmarketOfferRowsExpression {
  param([int[]]$LanguageIds, [string]$ReverseCode, [string]$FirstCode)
  $ids=@($LanguageIds | Sort-Object -Unique)
  if(!$ids.Count -or @($ids | Where-Object {$_ -notin @(1,3)}).Count){throw 'INVALID_OFFER_LANGUAGES'}
  if($ReverseCode -notin @('Y','N','0') -or $FirstCode -notin @('Y','N','0')){throw 'INVALID_OFFER_FLAGS'}
  # ConvertTo-Json -AsArray is unavailable in Windows PowerShell 5.1.
  $expected='['+($ids -join ',')+']'
  # A product without a reverse print has no isReverseHolo field; the URL
  # may still carry isReverseHolo=N (every offer is non-reverse anyway).
  $expression=@'
JSON.stringify((()=>{
 const wanted=__IDS__, reverse="__REVERSE__", first="__FIRST__";
 const u=new URL(location.href);
 const f=[...document.forms].find(x=>x.action.includes("Product_Filter_FilterProduct"));
 const checked=[...document.querySelectorAll("input")].filter(x=>x.name.startsWith("language[")&&x.checked).map(x=>Number(x.name.match(/\[(\d+)\]/)?.[1])).sort();
 const requested=(u.searchParams.get("language")||"").split(",").map(Number).sort();
 const same=x=>JSON.stringify(x)===JSON.stringify(wanted);
 const filtered=!!f&&same(checked)&&same(requested)&&u.searchParams.get("minCondition")==="2"&&f.elements.namedItem("minCondition")?.value==="2"&&
   ["isSigned","isAltered"].every(k=>u.searchParams.get(k)==="N"&&f.elements.namedItem("extra["+k+"]")?.value==="N")&&
   [["isReverseHolo",reverse],["isFirstEd",first]].every(([k,v])=>{
     const e=f.elements.namedItem("extra["+k+"]");
     return v==="0"?(!u.searchParams.has(k)||u.searchParams.get(k)==="0"):(e?(u.searchParams.get(k)===v&&e.value===v):(v==="N"&&(!u.searchParams.has(k)||u.searchParams.get(k)==="N")));
   });
 return {filtered,productId:document.querySelector("input[name=idProduct]")?.value||"",rows:[...document.querySelectorAll(".article-row")].slice(0,1200).map(r=>({
   id:r.id,condition:r.querySelector(".article-condition")?.getAttribute("data-bs-original-title")||r.querySelector(".article-condition")?.getAttribute("title"),
   language:[...r.querySelectorAll("[data-bs-original-title],[title]")].map(n=>n.getAttribute("data-bs-original-title")||n.getAttribute("title")).find(t=>["Deutsch","German","English","Englisch"].includes(t)),
   price:r.querySelector(".price-container")?.textContent?.trim(),
   comment:r.querySelector(".article-comment,.article-remarks,.article-comment-text,[data-testid=article-comment]")?.textContent?.trim()||null,
   commentVisible:!!r.querySelector(".article-comment,.article-remarks,.article-comment-text,[data-testid=article-comment]"),
   flags:[...r.querySelectorAll("[title],[data-bs-original-title]")].map(x=>x.getAttribute("data-bs-original-title")||x.getAttribute("title")).filter(x=>x==="Reverse Holo"||x==="First Edition")
 })),hasMore:!!document.querySelector("#loadMoreButton"),page:Number(document.querySelector("#articlePage")?.value||0),totalRows:document.querySelectorAll(".article-row").length};
})())
'@
  return $expression.Replace('__IDS__',$expected).Replace('__REVERSE__',$ReverseCode).Replace('__FIRST__',$FirstCode)
}

function Split-CardmarketCombinedOffers {
  param($Data, [string]$ProductId, [string]$ReverseCode, [string]$FirstCode)
  if(!$Data.filtered -or [string]$Data.productId -ne $ProductId -or
     @($Data.rows).Count -ne [int]$Data.totalRows){throw 'COMBINED_FILTER_OR_PRODUCT_UNVERIFIED'}
  $ids=[Collections.Generic.HashSet[string]]::new()
  $de=[Collections.Generic.List[object]]::new()
  $en=[Collections.Generic.List[object]]::new()
  foreach($row in @($Data.rows)){
    if(![string]$row.id -or !$ids.Add([string]$row.id) -or
       [string]$row.condition -notin @('Near Mint','Mint') -or
       $null -eq (Parse-Cardmarket-Euro ([string]$row.price)) -or
       ($ReverseCode -ne '0' -and (($ReverseCode -eq 'Y') -ne ('Reverse Holo' -in @($row.flags)))) -or
       ($FirstCode -ne '0' -and (($FirstCode -eq 'Y') -ne ('First Edition' -in @($row.flags))))){throw 'COMBINED_OFFER_ROW_UNVERIFIED'}
    switch([string]$row.language){
      {$_ -in @('Deutsch','German')} {$de.Add($row);break}
      {$_ -in @('English','Englisch')} {$en.Add($row);break}
      default {throw 'COMBINED_OFFER_LANGUAGE_UNVERIFIED'}
    }
  }
  return @{de_offers=$de.ToArray();en_offers=$en.ToArray()}
}

function New-CardmarketLanguageBucket($Data, [object[]]$Rows) {
  return [pscustomobject]@{filtered=$Data.filtered;productId=$Data.productId;rows=$Rows;
    totalRows=$Rows.Count;hasMore=$Data.hasMore;page=$Data.page}
}

function Test-CardmarketCombinedFallback($Observation, [object[]]$Rows) {
  # Complete combined lists prove absence too. A truncated mixed list must
  # not starve the less represented language or relax the existing sample gate.
  return !$Observation.all_pages_complete -and
    ($Rows.Count -lt 20 -or [int]$Observation.offer_pages_attempted -lt 3 -or
     [string]$Observation.pagination_failure -ne 'MORE_OFFERS_STILL_VISIBLE')
}

function New-CardmarketPeerObservation {
  param([System.Collections.IDictionary]$Source, $Peer, [string]$Language,
        [object[]]$Rows, [bool]$Fallback)
  $out=[ordered]@{}
  foreach($key in $Source.Keys){$out[$key]=$Source[$key]}
  $out.key='{0}|{1}' -f $Peer.cardyssey_karte,$Peer.variante_id
  $out.card_id=[string]$Peer.cardyssey_karte
  $out.variant_id=[string]$Peer.variante_id
  $out.set_id=[string]$Peer.set_id
  $out.number=[string]$Peer.kartennummer
  $out.language=$Language
  $out.query=[string]$Peer.kartenname_suche+' '+[string]$Peer.kartennummer
  $out.source_product_url=([string]$Source.url).Split('?')[0]
  $out.url=([string]$Source.url).Split('?')[0] -replace '/(de|en)/Pokemon/',('/'+$Language+'/Pokemon/')
  $out.filter_mode='COMBINED_URL_DOM_VERIFIED'
  $out.source_filter_language_ids='1,3'
  $out.combined_product_id_verified=[string]$Source.product_id
  $out.combined_offers_seen=[int]$Source.offers_seen
  $out.offers_seen=$Rows.Count
  $out.verified_lang_nm_offers=$Rows.Count
  $out.language_offers_observed=($Rows.Count -gt 0)
  $out.sample_median_eur=$null
  $out.median_all_offers_eur=$null
  $out.lowest_ask_eur=$null
  $out.entry_five_median_eur=$null
  $out.all_pages_complete=(!$Fallback -and [bool]$Source.all_pages_complete -and $Rows.Count -gt 0)
  if($Fallback){
    $out.status='SINGLE_LANGUAGE_FALLBACK_REQUIRED'
    $out.pagination_failure='MIXED_LANGUAGE_SAMPLE_INCOMPLETE'
    return $out
  }
  $prices=@($Rows | ForEach-Object {Parse-Cardmarket-Euro ([string]$_.price)} | Sort-Object)
  if($prices.Count -eq 0){$out.status='FILTER_UNVERIFIED_EMPTY';return $out}
  $mid=[int][Math]::Floor($prices.Count/2)
  $out.sample_median_eur=if($prices.Count%2){$prices[$mid]}else{[Math]::Round(($prices[$mid-1]+$prices[$mid])/2,2)}
  $out.lowest_ask_eur=$prices[0]
  $cheapest=@($prices | Select-Object -First 5)
  $mid=[int][Math]::Floor($cheapest.Count/2)
  $out.entry_five_median_eur=if($cheapest.Count%2){$cheapest[$mid]}else{[Math]::Round(($cheapest[$mid-1]+$cheapest[$mid])/2,2)}
  $out.median_all_offers_eur=if($out.all_pages_complete){$out.sample_median_eur}else{$null}
  $out.status=if($out.all_pages_complete){'COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED'}else{'FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE'}
  return $out
}
