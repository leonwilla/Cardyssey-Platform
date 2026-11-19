# Exercise production pairing, splitting, medians, fallback and cooldown policy.
$ErrorActionPreference='Stop'
$core=Join-Path $PSScriptRoot '../core'
. (Join-Path $core 'Cardmarket-Backoff-Policy.ps1')
. (Join-Path $core 'cardmarket-filter-url.ps1')
. (Join-Path $core 'cardmarket-combined-offers.ps1')
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $core 'cardmarket-language-browser-collector.ps1'),[ref]$tokens,[ref]$errors)
if($errors){throw ($errors -join ' | ')}
foreach($name in @('Parse-Cardmarket-Euro','Get-CardmarketBrowserQueueTier','Set-CardmarketMediaBlocking')){
  $node=$ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
  . ([scriptblock]::Create($node.Extent.Text))
}
function Assert-Equal($Actual,$Expected,[string]$Label){
  if($Actual -ne $Expected){throw "$Label expected=$Expected actual=$Actual"}
}
function Assert-Rejected([scriptblock]$Call,[string]$Label){
  $rejected=$false
  try {& $Call | Out-Null} catch {$rejected=$true}
  if(!$rejected){throw "Unverified evidence accepted: $Label"}
}
$url='https://www.cardmarket.com/de/Pokemon/Products/Singles/Paldean-Fates/Heat-Rotom-PAF013'
$filter=New-CardmarketOfferFilterUrl -ProductUrl $url -LanguageId 3 -ReverseCode Y -CombinedLanguages
Assert-Equal ([uri]$filter).Query '?language=1,3&minCondition=2&isSigned=N&isAltered=N&isReverseHolo=Y' 'combined filter'
Assert-Rejected {New-CardmarketOfferFilterUrl -ProductUrl $url -LanguageId 1 -CombinedLanguages} 'localized path mismatch'
$source=@{cardyssey_karte='sv04.5-013';variante_id='de-reverse';set_id='sv04.5';kartennummer='013';
 catalog_singleton_id='751539';catalog_expansion_id='5546';drucktyp='Reverse';foil='';sonderdruck='';stempel='[]';
 needs_price='YES';candidate_status='SINGLE_SET_PRODUCT';cardmarket_ids='751539'}
$peer=$source.Clone();$peer.variante_id='en-reverse'
$cases=@{'sv04.5-013'=@($peer)}
$now=[datetime]::UtcNow
$epoch=$now.AddDays(-1)
function Find-Target($Latest=@{},$InputCase=$source,$InputPeer=$peer,$ProductUrl=$url){
  Find-CardmarketCombinedTarget -Case $InputCase -ProductUrl $ProductUrl -PeerCases @{'sv04.5-013'=@($InputPeer)} -PeerLatest $Latest -SetGuards @{'sv04.5'='Paldean-Fates'} -Epoch $epoch -NowUtc $now
}
Assert-Equal ([string](Find-Target).variante_id) 'en-reverse' 'independent target ID'
foreach($bad in @(@{foil='Pokéball'},@{foil='Meisterball'},@{sonderdruck='shadowless'},@{sonderdruck='V2'},
 @{stempel='["staff"]'},@{catalog_singleton_id='999999'},@{catalog_expansion_id=''},
 @{set_id='sv04'},@{kartennummer='014'},@{drucktyp='Normal'},@{candidate_status='SET_EXPANSION_AMBIGUOUS'},
 @{known_url=$url.Replace('PAF013','PAF014')},@{cardmarket_ids='999999'},@{delta_browser_skip='YES'})){
  $row=$peer.Clone();foreach($key in $bad.Keys){$row[$key]=$bad[$key]}
  Assert-Equal ($null -eq (Find-Target -InputPeer $row)) $true ('reject peer '+($bad | ConvertTo-Json -Compress))
}
Assert-Equal ($null -eq (Find-Target -ProductUrl $url.Replace('-PAF013','-V1-PAF013'))) $true 'versioned products stay separate'
$ambiguous=@{'sv04.5-013'=@($peer,$peer.Clone())}
Assert-Equal ($null -eq (Find-CardmarketCombinedTarget $source $url $ambiguous @{} @{'sv04.5'='Paldean-Fates'} $epoch $now)) $true 'multiple target variants'
foreach($status in @('FILTERED_SAMPLE_REVIEW_NOT_MARKET_WIDE','BLOCKED','PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED','SINGLE_LANGUAGE_FALLBACK_REQUIRED','DEFERRED_SOCKET')){
  $previous=@{'sv04.5-013|en-reverse'=@{status=$status;seen_at=$now.AddMinutes(-5).ToString('o')}}
  Assert-Equal ($null -eq (Find-Target -Latest $previous)) $true ('do not overwrite '+$status)
}
$old=@{'sv04.5-013|en-reverse'=@{status='ERROR';seen_at=$now.AddDays(-2).ToString('o')}}
Assert-Equal ([string](Find-Target -Latest $old).variante_id) 'en-reverse' 'old observation can be refreshed'

$rows=@(
 @{id='a';language='Deutsch';condition='Near Mint';price='1,00 €';flags=@('Reverse Holo')},
 @{id='b';language='German';condition='Mint';price='3,00 €';flags=@('Reverse Holo')},
 @{id='c';language='English';condition='Near Mint';price='5,00 €';flags=@('Reverse Holo')},
 @{id='d';language='Englisch';condition='Near Mint';price='9,00 €';flags=@('Reverse Holo')}
)
$data=[pscustomobject]@{filtered=$true;productId='751539';totalRows=4;rows=$rows;hasMore=$false;page=0}
$split=Split-CardmarketCombinedOffers $data '751539' Y 0
Assert-Equal $split.de_offers.Count 2 'German offers'
Assert-Equal $split.en_offers.Count 2 'English offers'
$observation=[ordered]@{key='sv04.5-013|de-reverse';card_id='sv04.5-013';variant_id='de-reverse';set_id='sv04.5';number='013';
 language='de';url=$url;product_id='751539';identity_confirmed=$true;card_number_url_verified=$true;
 all_pages_complete=$true;offers_seen=4;offer_pages_attempted=0;pagination_failure='';seen_at=$now.ToString('o')}
$en=New-CardmarketPeerObservation $observation $peer en $split.en_offers $false
Assert-Equal $en.sample_median_eur 7 'English-only median'
Assert-Equal $en.offers_seen 2 'language-specific denominator'
Assert-Equal $en.variant_id 'en-reverse' 'destination variant key'
Assert-Equal $en.source_filter_language_ids '1,3' 'combined filter evidence'
Assert-Equal $en.combined_offers_seen 4 'shared window count'
Assert-Equal $en.url ($url.Replace('/de/','/en/')) 'destination canonical URL'
Assert-Equal $en.status 'COMPLETE_FILTERED_ASKING_MEDIAN_PRINT_UNVERIFIED' 'complete window'
$de=New-CardmarketPeerObservation $observation $source de $split.de_offers $false
Assert-Equal $de.sample_median_eur 2 'German-only median'
Assert-Equal (Test-CardmarketCombinedFallback $observation @()) $false 'complete lists prove absence'
foreach($bad in @(@{language='French'},@{condition='Light Played'},@{price=''},@{id=''},@{flags=@()})){
  $badRows=@($rows | ForEach-Object {$_.Clone()})
  foreach($k in $bad.Keys){$badRows[0][$k]=$bad[$k]}
  $broken=[pscustomobject]@{filtered=$true;productId='751539';totalRows=4;rows=$badRows}
  Assert-Rejected {Split-CardmarketCombinedOffers $broken '751539' Y 0} ($bad | ConvertTo-Json -Compress)
}
$duplicate=[pscustomobject]@{filtered=$true;productId='751539';totalRows=4;rows=@($rows[0],$rows[0],$rows[2],$rows[3])}
Assert-Rejected {Split-CardmarketCombinedOffers $duplicate '751539' Y 0} 'duplicate offer'
Assert-Rejected {Split-CardmarketCombinedOffers $data '999999' Y 0} 'wrong product'
$data.filtered=$false
Assert-Rejected {Split-CardmarketCombinedOffers $data '751539' Y 0} 'changed filter'
$data.filtered=$true
$observation.all_pages_complete=$false
$observation.offer_pages_attempted=3
$observation.pagination_failure='MORE_OFFERS_STILL_VISIBLE'
Assert-Equal (Test-CardmarketCombinedFallback $observation $split.en_offers) $true 'underrepresented language'
Assert-Equal (Test-CardmarketCombinedFallback $observation @(1..20)) $false 'sufficient bounded sample'
$pending=New-CardmarketPeerObservation $observation $peer en $split.en_offers $true
Assert-Equal $pending.status 'SINGLE_LANGUAGE_FALLBACK_REQUIRED' 'separate single-language retry'
Assert-Equal ($null -eq $pending.sample_median_eur) $true 'fallback never publishes a price'
$due=@(Get-CardmarketDueCases @($peer) @{'sv04.5-013|en-reverse'=[pscustomobject]$pending} ([Collections.Generic.HashSet[string]]::new()) $now $epoch)
Assert-Equal $due.Count 1 'fallback is due immediately'

$script:blockedUrls=@()
function Send-Cdp([string]$Method,[hashtable]$Parameters){
  Assert-Equal $Method 'Network.setBlockedURLs' 'only media CDP setting'
  $script:blockedUrls=$Parameters.urls
}
Set-CardmarketMediaBlocking $true
Assert-Equal $script:blockedUrls.Count 24 'media patterns'
if(@($script:blockedUrls | Where-Object {$_ -match '\.js|challenge|challenges[.]cloudflare'}).Count){throw 'Challenge or script blocking'}
Set-CardmarketMediaBlocking $false
Assert-Equal $script:blockedUrls.Count 0 'release target media after scan'
Assert-Equal (Get-CardmarketCooldownMinutes BATCH_COMPLETE_MORE_PENDING '' AVAILABLE) 8 'normal pause'
Assert-Equal (Get-CardmarketCooldownMinutes BLOCKED '' BLOCKED) 240 'blocked pause preserved'
Assert-Equal (Get-CardmarketCooldownMinutes BLOCKED '' AVAILABLE) 0 'human clearance resumes'
Write-Output 'CARDMARKET_COMBINED_OFFERS_TESTS_OK'
