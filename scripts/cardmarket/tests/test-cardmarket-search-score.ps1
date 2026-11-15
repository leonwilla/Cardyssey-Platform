$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../core/cardmarket-search-score.ps1')
. (Join-Path $PSScriptRoot '../core/cardmarket-filter-url.ps1')
function Check([bool]$value,[string]$why) {if(!$value){throw ('TEST_FAIL: '+$why)}}
$felori=@(
 @{url='https://www.cardmarket.com/de/Pokemon/Products/Singles/Scarlet-Violet/Sprigatito-V1-SVI013';text='Sprigatito [Scratch | Leafage]'},
 @{url='https://www.cardmarket.com/de/Pokemon/Products/Singles/Scarlet-Violet/Sprigatito-V2-SVI013';text='Sprigatito [Scratch | Leafage]'},
 @{url='https://www.cardmarket.com/de/Pokemon/Products/Singles/Gem-Pack-Vol-1/Sprigatito-V1-CBB1C01';text='Sprigatito'},
 @{url='https://www.cardmarket.com/de/Pokemon/Products/Singles/Scarlet-Violet/Sprigatito-V3-SVI113';text='Sprigatito'}
)
$a=Resolve-CardmarketSearchCandidates -Links $felori -PrintedNumber '013' -SetSlug 'Scarlet-Violet' -PrintType Reverse -Stamp 'grass-symbol'
Check ($a.candidateCount -eq 2 -and $null -eq $a.uniquePageCandidate) 'Felori V1 and V2 must be ambiguous'
Check ($a.reason -eq 'MULTIPLE_SAME_SET_NUMBER_CANDIDATES') 'Felori state'
Check (!$a.exactPrintVerified -and !$a.priceVerified) 'no print or price inferred'
$b=Resolve-CardmarketSearchCandidates -Links $felori -PrintedNumber '113' -SetSlug 'Scarlet-Violet'
Check ($b.candidateCount -eq 1 -and $b.uniquePageCandidate.productSlug -match 'SVI113$') '13 may not match 113'
$c=Resolve-CardmarketSearchCandidates -Links $felori -PrintedNumber '013'
Check ($c.candidateCount -eq 2 -and $null -eq $c.uniquePageCandidate -and $c.reason -eq 'SET_NOT_INDEPENDENTLY_VERIFIED') 'unknown set requires independent guard'
$joltik=@(
 @{url='https://www.cardmarket.com/de/Pokemon/Products/Singles/White-Flare-Additionals/Joltik-V1-xWHT033';text='Joltik [Surprise Attack]'},
 @{url='https://www.cardmarket.com/de/Pokemon/Products/Singles/White-Flare-Additionals/Joltik-V2-xWHT033';text='Joltik [Surprise Attack]'},
 @{url='https://www.cardmarket.com/de/Pokemon/Products/Singles/White-Flare/Joltik-V1-WHT033';text='Joltik [Surprise Attack]'}
)
$d=Resolve-CardmarketSearchCandidates -Links $joltik -PrintedNumber '033' -SetSlug 'White-Flare-Additionals' -Foil 'Pokéball'
Check ($d.candidateCount -eq 2 -and !$d.uniquePageCandidate) 'Pokeball keyword missing: do not guess V1/V2'
$e=Resolve-CardmarketSearchCandidates -Links @(@{url='https://www.cardmarket.com/de/Pokemon/Products/Singles/Wizards-Black-Star-Promos/Pikachu-WP1';text='Pikachu Promo'}) -PrintedNumber '1' -SetSlug 'Wizards-Black-Star-Promos' -Stamp 'grauer stern'
Check ($e.candidateCount -eq 1 -and !$e.exactPrintVerified) 'Promo title does not confirm stamp'
$f=Resolve-CardmarketSearchCandidates -Links @(@{url='https://evil.example/de/Pokemon/Products/Singles/Base-Set/Machamp-V1-BS8';text='Machamp 8'}) -PrintedNumber '8' -SetSlug 'Base-Set'
Check ($f.candidateCount -eq 0) 'reject fake Cardmarket domain'
$u=New-CardmarketOfferFilterUrl -ProductUrl 'https://www.cardmarket.com/de/Pokemon/Products/Singles/Scarlet-Violet/Sprigatito-V1-SVI013?language=1' -LanguageId 3 -ReverseCode Y -FirstEditionCode N
Check ($u -eq 'https://www.cardmarket.com/de/Pokemon/Products/Singles/Scarlet-Violet/Sprigatito-V1-SVI013?language=3&minCondition=2&isSigned=N&isAltered=N&isReverseHolo=Y&isFirstEd=N') 'canonical filter URL parameters'
$failed=$false
try{$null=New-CardmarketOfferFilterUrl -ProductUrl 'https://evil.example/Pokemon/Products' -LanguageId 3}catch{$failed=$true}
Check $failed 'reject hostile domain'
$failed=$false
try{$null=New-CardmarketOfferFilterUrl -ProductUrl 'https://www.cardmarket.com/de/Pokemon/Products/Singles/Scarlet-Violet/Sprigatito-V1-SVI013' -LanguageId 1}catch{$failed=$true}
Check $failed 'reject mismatched language'

. (Join-Path $PSScriptRoot '../core/Cardmarket-Backoff-Policy.ps1')
$baseUrl='https://www.cardmarket.com/en/Pokemon/Products/Singles/'
$routes=@(
 @{set='sv05';main='Temporal-Forces';number='159';stamp='["player-rewards-program"]';path='Play-Pokemon-Prize-Pack-Series-Six/Rescue-Board-V1-PPS6TEF-159';wrong='Play-Pokemon-Prize-Pack-Series-Six/Other-PPS6OBF-159'},
 @{set='sv03';main='Obsidian-Flames';number='130';stamp='["trick-or-trade"]';path='Trick-or-Trade-2024/Umbreon-BOO24OBF-130';wrong='Trick-or-Trade-2023/Umbreon-BOO24OBF-130'},
 @{set='sv05';main='Temporal-Forces';number='142';stamp='["Professorenprogramm"]';path='Professor-Program/Biancas-Devotion-PPPTEF-142';wrong='Temporal-Forces/Biancas-Devotion-TEF142'},
 @{set='dp6';main='Legends-Awakened';number='144';stamp='["David Cohen"]';path='WCD-2009/Mewtwo-LVX-WCD09LA-144';wrong='WCD-2009/Mewtwo-LVX-WCD09GE-144'},
 @{set='sv10.5w';main='White-Flare';number='033';stamp='["Set-Logo"]';path='White-Flare-Additionals/Joltik-V1-xWHT033';wrong='Black-Bolt-Additionals/Joltik-V1-xWHT033'}
)
foreach($route in $routes){
  $items=@(@{url=$baseUrl+$route.path},@{url=$baseUrl+$route.wrong})
  $result=Resolve-CardmarketSearchCandidates -Links $items -PrintedNumber $route.number -SetId $route.set -SetSlug $route.main -Language en -Stamp $route.stamp
  Check ($result.candidateCount -eq 1 -and $result.uniquePageCandidate.url -eq ($baseUrl+$route.path)) ('strict subset and number: '+$route.stamp)
  Check ($result.reason -eq 'SUBSET_PAGE_CANDIDATES_PRINT_UNVERIFIED' -and !$result.exactPrintVerified -and !$result.priceVerified) 'subset never proves print or price'
}
$world=@(
 @{url=$baseUrl+'WCD-2007/Holon-Mentor-V1-WCD07DF-075'},
 @{url=$baseUrl+'WCD-2007/Holon-Mentor-V2-WCD07DF-075'}
)
$w=Resolve-CardmarketSearchCandidates -Links $world -PrintedNumber 75 -SetId ex15 -SetSlug EX-Dragon-Frontiers -Stamp '["Jun Hasebe"]'
Check ($w.candidateCount -eq 2 -and !$w.uniquePageCandidate -and !$w.exactPrintVerified) 'same-set WCD V1/V2 remain separate physical-print candidates'
$wrongLocale=Resolve-CardmarketSearchCandidates -Links $world -PrintedNumber 75 -SetId ex15 -SetSlug EX-Dragon-Frontiers -Language de -Stamp '["Jun Hasebe"]'
Check ($wrongLocale.candidateCount -eq 0) 'collector requires requested language path'
$vintage=@(
 @{url=$baseUrl+'Base-Set/Machamp-V2-BS8'},
 @{url=$baseUrl+'Base-Set/Machamp-V1-BS8'},
 @{url=$baseUrl+'Base-Set-2/Machamp-BS8'},
 @{url=$baseUrl+'Base-Set/Blastoise-V1-BS2'}
)
$v=Resolve-CardmarketSearchCandidates -Links $vintage -PrintedNumber 8 -SetId base1 -SetSlug Base-Set -PreferBasePage
Check ($v.candidateCount -eq 1 -and $v.uniquePageCandidate.productSlug -eq 'Machamp-V1-BS8' -and !$v.exactPrintVerified) 'vintage base page: V1, exact set and number, print unverified'

$now=[DateTimeOffset]::Parse('2026-11-15T12:00:00Z').UtcDateTime
$scanEpoch=$now.AddDays(-6)
$finished=[Collections.Generic.HashSet[string]]::new()
$prior=@{}
$queue=@()
$states=@('MULTIPLE_SEARCH_HITS','NO_EXACT_NUMBER_SEARCH_HIT','PRODUCT_ID_NOT_VERIFIED_FOR_CARD',
          'PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED','BLOCKED')
for($i=0;$i -lt 20;$i++){
  $queue+=[pscustomobject]@{cardyssey_karte="recent-$i";variante_id='v1';manual_scan_requested_at=$now.ToString('o')}
  $prior["recent-$i|v1"]=@{status=$states[$i%$states.Count];seen_at=$now.AddHours(-71).ToString('o')}
}
$queue+=[pscustomobject]@{cardyssey_karte='cooled';variante_id='v1'}
$prior['cooled|v1']=@{status='MULTIPLE_SEARCH_HITS';seen_at=$now.AddHours(-72).ToString('o')}
for($i=0;$i -lt 16;$i++){
  $queue+=[pscustomobject]@{cardyssey_karte="new-$i";variante_id='v1'}
}
$queue+=[pscustomobject]@{cardyssey_karte='done';variante_id='v1'}
[void]$finished.Add('done|v1')
$next=@(Get-CardmarketDueCases -Cases $queue -Latest $prior -Processed $finished -NowUtc $now -Epoch $scanEpoch)
Check ($next.Count -eq 17 -and $next[0].cardyssey_karte -eq 'new-0' -and $next[15].cardyssey_karte -eq 'new-15' -and $next[16].cardyssey_karte -eq 'cooled') '72h defer manual and blocked variants, old retries behind fresh batch'

$temps=Join-Path ([IO.Path]::GetTempPath()) ('cardmarket-fairness-'+[guid]::NewGuid().ToString('N'))
try{
  $null=New-Item -ItemType Directory -Path $temps
  @{status='BLOCKED';updated_at=$now.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $temps 'progress-de.json')
  @{status='BATCH_COMPLETE_MORE_PENDING';updated_at=$now.AddDays(-2).ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $temps 'progress-en.json')
  $langs=@(Get-CardmarketLanguageOrder -Base $temps -Languages both)
  Check (($langs -join ',') -eq 'en,de') 'after DE block, resume with EN after shared backoff'
} finally {
  Remove-Item -Recurse -LiteralPath $temps
}
Write-Output 'CARDMARKET_SCORE_FILTER_QUEUE_TESTS_OK'
