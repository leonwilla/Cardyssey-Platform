
$ErrorActionPreference='Stop'
$root=Join-Path $PSScriptRoot '..\core'
$collector=Join-Path $root 'cardmarket-language-browser-collector.ps1'
$tokens=$null
$errors=$null
$parsed=[System.Management.Automation.Language.Parser]::ParseFile($collector,[ref]$tokens,[ref]$errors)
if($errors){throw ($errors -join ' | ')}
$functions=@('Move-To','Wait-CardmarketRequestBudget','Is-CardmarketChallenge','Get-CardmarketBrowserQueueTier')
foreach($definition in $parsed.FindAll({
  param($node)
  $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -in $functions
},$true)){
  . ([scriptblock]::Create($definition.Extent.Text))
}
. (Join-Path $root 'cardmarket-filter-url.ps1')

function Assert-Equal($Actual,$Expected,[string]$Message){
  if($Actual -ne $Expected){throw "$Message (expected $Expected, got $Actual)"}
}

$fixtures=@(
  @{Row=@{needs_price='YES';scan_tier='4'};Tier=0},
  @{Row=@{needs_price='NO';existing_price_eur='9.99995';drucktyp='normal'};Tier=4},
  @{Row=@{needs_price='NO';existing_price_eur='10.00';drucktyp='normal'};Tier=1},
  @{Row=@{needs_price='NO';existing_price_eur='1';stempel='["staff"]';routing_state='VERIFIED_PRODUCT_ID'};Tier=2},
  @{Row=@{needs_price='NO';existing_price_eur='1';foil='cosmos'};HumanConfirmed=$true;Tier=2},
  @{Row=@{needs_price='NO';existing_price_eur='1';foil='cosmos';routing_state='HUMAN_CONFIRMED'};Tier=2},
  @{Row=@{needs_price='NO';existing_price_eur='1';foil='cosmos';routing_state='UNVERIFIED'};Tier=4},
  @{Row=@{needs_price='NO';existing_price_eur='1';drucktyp='reverse';routing_state='VERIFIED_PRODUCT_ID'};Tier=4},
  @{Row=@{needs_price='NO';existing_price_eur='1';drucktyp='holo';stempel='[]';routing_state='VERIFIED_PRODUCT_ID'};Tier=4},
  @{Row=@{needs_price='NO';existing_price_eur='1';manual_scan_requested_at='2026-11-18T09:00:00Z'};Tier=3}
)
foreach($fixture in $fixtures){
  Assert-Equal (Get-CardmarketBrowserQueueTier $fixture.Row ([bool]$fixture.HumanConfirmed)) $fixture.Tier 'browser eligibility'
}

# Exercise the production navigation and pacing functions without opening a
# Cardmarket request or using the live Edge session.
$script:events=[Collections.Generic.List[string]]::new()
$script:document=@{ready='complete';body=600;title='Pokémon';challenge=$false;httpStatus=200}
function Start-Sleep([int]$Milliseconds) { $script:events.Add("sleep:$Milliseconds") }
function Send-Cdp([string]$Method,[hashtable]$Arguments) {
  Assert-Equal $Method 'Page.navigate' 'CDP document navigation'
  $script:events.Add("navigate:$($Arguments.url)")
  $script:document.href=$Arguments.url
  $script:document.path=([uri]$Arguments.url).AbsolutePath
}
$script:responseStatuses=[Collections.Generic.Queue[int]]::new()
function Js([string]$Expression,[int]$TimeoutSec) {
  if($script:responseStatuses.Count){$script:document.httpStatus=$script:responseStatuses.Dequeue()}
  return $script:document | ConvertTo-Json -Compress
}

$MinRequestGapSeconds=16
$ChallengeWaitSeconds=0
$script:lastProviderRequestUtc=[datetime]::MinValue
$LangCfg=@{PathPrefix='/de/Pokemon'}
$deSearch='https://www.cardmarket.com/de/Pokemon/Products/Search?searchString=Pikachu'
$de=New-CardmarketOfferFilterUrl -ProductUrl 'https://www.cardmarket.com/de/Pokemon/Products/Singles/Base-Set/Pikachu-V1-BS58' -LanguageId 3 -ReverseCode N
Assert-Equal (Move-To $deSearch) $true 'DE search navigation'
Assert-Equal (Move-To $de) $true 'DE filtered product navigation'
Assert-Equal $script:events[0] "navigate:$deSearch" 'search is a document request'
Assert-Equal $script:events[3] "navigate:$de" 'product is a document request'
if($script:events[2] -notmatch '^sleep:(\d+)$' -or [int]$Matches[1] -lt 12000){throw 'Missing request pacing'}
Assert-Equal ([uri]$de).Query '?language=3&minCondition=2&isSigned=N&isAltered=N&isReverseHolo=N' 'DE filter URL'

$LangCfg=@{PathPrefix='/en/Pokemon'}
$en=New-CardmarketOfferFilterUrl -ProductUrl 'https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Pikachu-V1-BS58?old=1' -LanguageId 1 -ReverseCode Y -FirstEditionCode N
Assert-Equal ([uri]$en).Query '?language=1&minCondition=2&isSigned=N&isAltered=N&isReverseHolo=Y&isFirstEd=N' 'EN filter URL'
Assert-Equal (Move-To $en) $true 'EN filtered product navigation'

$ChallengeWaitSeconds=15
$script:responseStatuses.Enqueue(403)
$script:responseStatuses.Enqueue(200)
$before=@($script:events | Where-Object {$_ -like 'navigate:*'}).Count
Assert-Equal (Move-To $en) $true 'the current document clears its own challenge'
$after=@($script:events | Where-Object {$_ -like 'navigate:*'}).Count
Assert-Equal ($after-$before) 1 'no new navigation during a challenge'
$ChallengeWaitSeconds=0

$script:document.httpStatus=403
try {
  [void](Move-To $en)
  throw 'A blocked product returned success'
} catch {
  Assert-Equal $_.Exception.Message 'CARDMARKET_PROVIDER_CHALLENGE' 'blocked product'
}
Assert-Equal $script:providerBlock.stage 'PRODUCT_PAGE' 'blocked navigation stage'
Assert-Equal $script:providerBlock.httpStatus 403 'blocked navigation HTTP status'
Assert-Equal $script:providerBlock.signal 'HTTP_STATUS' 'blocked navigation signal'

$script:document.httpStatus=0
$script:document.challenge=$true
try {
  [void](Move-To 'https://www.cardmarket.com/en/Pokemon/Products/Search?searchString=Pikachu')
  throw 'A challenge page returned success'
} catch {
  Assert-Equal $_.Exception.Message 'CARDMARKET_PROVIDER_CHALLENGE' 'search challenge'
}
Assert-Equal $script:providerBlock.stage 'SEARCH_PAGE' 'search challenge stage'
Assert-Equal $script:providerBlock.signal 'PAGE_MARKER' 'search challenge signal'
Write-Output 'CARDMARKET_BROWSER_NAVIGATION_TESTS_OK'

