# Run the actual collector entry point with fixture browser responses. All
# observations stay in temporary files, with no browser or database access.
$ErrorActionPreference='Stop'
$core=Join-Path $PSScriptRoot '../core'
$fixturePath=Join-Path $core ('fixture-collector-'+[guid]::NewGuid().ToString('N')+'.ps1')
$temp=Join-Path ([IO.Path]::GetTempPath()) ('cardmarket-combined-entry-'+[guid]::NewGuid().ToString('N'))
$savedScenario=$env:CARDYSSEY_TEST_SCENARIO
$fixture=@'
function Connect-Cdp {$script:ws=[pscustomobject]@{State='Open'}}
function Start-Sleep {param($Seconds,$Milliseconds)}
function Move-To([string]$Url){
  Add-Content -LiteralPath (Join-Path $OutputDir 'fixture-navigations.jsonl') -Value ($Url | ConvertTo-Json -Compress)
  if($env:CARDYSSEY_TEST_SCENARIO -eq 'challenge'){throw 'CARDMARKET_PROVIDER_CHALLENGE'}
  $script:fixtureUrl=$Url
  return $true
}
function Js([string]$Expression,[int]$TimeoutSec){
  if($Expression -eq 'location.href'){return $script:fixtureUrl}
  if($Expression -eq 'document.querySelector("input[name=idProduct]")?.value||""'){
    if($env:CARDYSSEY_TEST_SCENARIO -eq 'wrong-id'){return '999999'}
    return '751539'
  }
  if($Expression -like '*const wanted=*'){
    $lang=if($script:fixtureUrl -like '*language=1,3&*'){'both'}elseif($script:fixtureUrl -like '*language=3&*'){'de'}else{'en'}
    $rows=@()
    if($lang -eq 'both'){
      if($env:CARDYSSEY_TEST_SCENARIO -eq 'truncated'){
        $rows=@(1..49 | ForEach-Object {@{id='de-'+$_;language='Deutsch';condition='Near Mint';price='2,00 EUR';flags=@('Reverse Holo')}})
        $rows+=@{id='en-1';language='English';condition='Near Mint';price='7,00 EUR';flags=@('Reverse Holo')}
      }else{
        $rows=@(
          @{id='de-1';language='Deutsch';condition='Near Mint';price='1,00 EUR';flags=@('Reverse Holo')},
          @{id='de-2';language='German';condition='Mint';price='3,00 EUR';flags=@('Reverse Holo')},
          @{id='en-1';language='English';condition='Near Mint';price='5,00 EUR';flags=@('Reverse Holo')},
          @{id='en-2';language='Englisch';condition='Near Mint';price='9,00 EUR';flags=@('Reverse Holo')}
        )
      }
      if($env:CARDYSSEY_TEST_SCENARIO -eq 'unknown-language'){$rows[3].language='French'}
    }else{
      $rows=@(1..20 | ForEach-Object {@{id=$lang+'-'+$_;language=$(if($lang -eq 'de'){'Deutsch'}else{'English'});condition='Near Mint';price=$(if($lang -eq 'de'){'2,00 EUR'}else{'7,00 EUR'});flags=@('Reverse Holo')}})
    }
    $productId=if($env:CARDYSSEY_TEST_SCENARIO -eq 'wrong-id'){'999999'}else{'751539'}
    return @{filtered=$true;productId=$productId;rows=$rows;hasMore=($lang -eq 'both' -and $env:CARDYSSEY_TEST_SCENARIO -eq 'truncated');page=0;totalRows=$rows.Count} | ConvertTo-Json -Depth 6 -Compress
  }
  if($Expression.Contains('const a=[...document.querySelectorAll')){return ''}
  if($Expression -like '*b.click()*'){return 'CLICKED'}
  if($Expression -like '*return b?"PRESENT":"ABSENT"*'){return 'PRESENT'}
  if($Expression -like '*#loadMoreButton*'){return $false}
  if($Expression -like '*User_Logout*'){return $true}
  throw ('Unexpected fixture browser expression '+$Expression.Substring(0,[Math]::Min(80,$Expression.Length)))
}
'@
function Assert-Fixture([bool]$Ok,[string]$Why){if(!$Ok){throw $Why}}
try {
  $source=Get-Content -Raw -Encoding UTF8 (Join-Path $core 'cardmarket-language-browser-collector.ps1')
  $anchor="try {`n  "+'$ordered=@(Get-CardmarketDueCases'
  # Accept either repository newline convention.
  $source=$source.Replace("`r`n","`n")
  Assert-Fixture ($source.Contains($anchor)) 'Collector main entry point not found'
  $source=$source.Replace($anchor,($fixture+"`n"+$anchor))
  Set-Content -Encoding UTF8 -LiteralPath $fixturePath $source
  foreach($scenario in @('complete','truncated','unknown-language','wrong-id','special','feed-only-peer','challenge')){
    $base=Join-Path $temp $scenario
    $null=New-Item -ItemType Directory -Force $base
    $env:CARDYSSEY_TEST_SCENARIO=$scenario
    foreach($lang in @('de','en')){
      $row=[ordered]@{cardyssey_karte='sv04.5-013';variante_id=$lang+'-reverse';set_id='sv04.5';kartennummer='013';
        kartenname_suche='Heat Rotom';drucktyp='Reverse';foil='';sonderdruck='';stempel='[]';
        catalog_singleton_id='751539';catalog_expansion_id='5546';cardmarket_ids='751539';candidate_status='SINGLE_SET_PRODUCT';
        routing_state='VERIFIED_PRODUCT_ID';known_url='https://www.cardmarket.com/'+$lang+'/Pokemon/Products/Singles/Paldean-Fates/Heat-Rotom-PAF013';
        scan_tier='0';needs_price='YES';existing_price_eur='';manual_scan_requested_at=''}
      if($scenario -eq 'special' -and $lang -eq 'de'){$row.foil='cosmos'}
      if($scenario -eq 'feed-only-peer' -and $lang -eq 'en'){$row.needs_price='NO';$row.existing_price_eur='14.99'}
      [pscustomobject]$row | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $base ('queue-'+$lang+'.csv'))
    }
    Set-Content -Encoding UTF8 (Join-Path $base 'verified-set-url-guards.json') '{"sv04.5":"Paldean-Fates"}'
    & $fixturePath -Language de -InputCsv (Join-Path $base 'queue-de.csv') -OutputDir $base -BatchLimit 1 -DelaySeconds 0 -MinRequestGapSeconds 4 | Out-Null
    $de=Get-Content -Encoding UTF8 (Join-Path $base 'browser-observations-de.jsonl') | Select-Object -Last 1 | ConvertFrom-Json
    $peerFile=Join-Path $base 'browser-observations-en.jsonl'
    if($scenario -eq 'complete'){
      Assert-Fixture (Test-Path $peerFile) ('Missing combined observation '+($de|ConvertTo-Json -Depth 5 -Compress))
      $en=Get-Content -Raw -Encoding UTF8 $peerFile | ConvertFrom-Json
      Assert-Fixture ($de.sample_median_eur -eq 2 -and $en.sample_median_eur -eq 7) ('Entry point mixed languages '+($de|ConvertTo-Json -Compress))
      Assert-Fixture ($en.variant_id -eq 'en-reverse' -and $de.variant_id -eq 'de-reverse') 'Wrong physical variant keys'
      Assert-Fixture ($de.offers_seen -eq 2 -and $en.offers_seen -eq 2) 'Mixed offer denominator'
      Assert-Fixture ($de.filter_mode -eq 'COMBINED_URL_DOM_VERIFIED' -and $en.all_pages_complete) 'Missing combined proof'
      $before=@(Get-Content (Join-Path $base 'fixture-navigations.jsonl')).Count
      Assert-Fixture ($before -eq 1) 'Shared page required more than one document'
      & $fixturePath -Language en -InputCsv (Join-Path $base 'queue-en.csv') -OutputDir $base -BatchLimit 1 -DelaySeconds 0 -MinRequestGapSeconds 4 | Out-Null
      Assert-Fixture (@(Get-Content (Join-Path $base 'fixture-navigations.jsonl')).Count -eq $before) 'Other language rescanned completed shared page'
    }elseif($scenario -eq 'truncated'){
      $en=Get-Content -Raw -Encoding UTF8 $peerFile | ConvertFrom-Json
      Assert-Fixture ($en.status -eq 'SINGLE_LANGUAGE_FALLBACK_REQUIRED' -and $null -eq $en.sample_median_eur) 'Truncated English bucket was accepted'
      Assert-Fixture ($de.sample_median_eur -eq 2 -and $de.filter_mode -eq 'CANONICAL_URL_DOM_VERIFIED') 'Source-language fallback did not run'
      & $fixturePath -Language en -InputCsv (Join-Path $base 'queue-en.csv') -OutputDir $base -BatchLimit 1 -DelaySeconds 0 -MinRequestGapSeconds 4 | Out-Null
      $en=Get-Content -Encoding UTF8 $peerFile | Select-Object -Last 1 | ConvertFrom-Json
      Assert-Fixture ($en.sample_median_eur -eq 7 -and $en.filter_mode -eq 'CANONICAL_URL_DOM_VERIFIED') 'Target-language fallback was skipped or combined again'
    }else{
      Assert-Fixture (!(Test-Path $peerFile)) ('Unexpected counterpart observation '+$scenario)
      if($scenario -eq 'unknown-language'){Assert-Fixture ($de.status -eq 'FILTER_NOT_APPLIED') 'Unknown row language accepted'}
      if($scenario -eq 'wrong-id'){Assert-Fixture (!$de.identity_confirmed) 'Wrong product ID accepted'}
      if($scenario -eq 'challenge'){Assert-Fixture ($de.status -eq 'BLOCKED') 'Challenge lost its stop status'}
      if($scenario -eq 'special'){Assert-Fixture ($de.non_filterable_print_attributes.Count -gt 0) 'Special print lost price protection'}
    }
    Write-Output ('COMBINED_COLLECTOR_FIXTURE_OK '+$scenario)
  }
  Write-Output 'CARDMARKET_COMBINED_COLLECTOR_TESTS_OK'
} finally {
  $env:CARDYSSEY_TEST_SCENARIO=$savedScenario
  if(Test-Path $fixturePath){Remove-Item -Force $fixturePath}
  if(Test-Path $temp){Remove-Item -Force -Recurse $temp}
}
