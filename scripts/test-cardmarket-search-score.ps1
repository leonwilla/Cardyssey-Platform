$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'cardmarket-search-score.ps1')
. (Join-Path $PSScriptRoot 'cardmarket-filter-url.ps1')
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
Write-Output 'CARDMARKET_SCORE_FILTER_TESTS_OK (9 checks)'
