# Persistent provider backoff for both language queues.
# This file is sourced by the Windows launcher, watchdog and queue runner.
# Only a fresh check of the collector tab can release an active provider block.
function Get-CardmarketBlockedStreak([string]$Base) {
  $path=Join-Path $Base 'cardmarket-blocked-streak.json'
  if(!(Test-Path -LiteralPath $path)){return 2}  # unknown = conservative
  try {
    $row=Get-Content -Raw -Encoding UTF8 -LiteralPath $path | ConvertFrom-Json
    if([string]$row.lastStatus -ne 'BLOCKED'){return 0}
    if([int]$row.count -lt 1){return 2}
    return [Math]::Min([int]$row.count,2)
  } catch {
    return 2
  }
}
function Get-CardmarketCooldownMinutes([string]$Status,[string]$Base,[string]$ProviderStatus) {
  switch($Status) {
    'BLOCKED' {
      if($ProviderStatus -eq 'AVAILABLE'){return 0}
      return 240
    }
    'PROVIDER_TIMEOUT' {return 90}
    'CONNECTION_LOST' {return 60}
    'BATCH_COMPLETE_MORE_PENDING' {return 3}
    'COMPLETED_WITH_DEFERRED' {return 90}
    default {return 0}
  }
}
function Get-CardmarketActiveCooldown($States,[string]$Base,[string]$ProviderStatus) {
  $latest=$States | Sort-Object last -Descending | Select-Object -First 1
  $resumeBlock=($ProviderStatus -eq 'AVAILABLE' -and $latest.status -eq 'BLOCKED')
  $now=[DateTime]::UtcNow
  $active=foreach($entry in $States){
    # A recent cleared block takes precedence over the preceding routine batch pause.
    if($resumeBlock -and $entry.status -eq 'BATCH_COMPLETE_MORE_PENDING'){continue}
    $minutes=Get-CardmarketCooldownMinutes $entry.status $Base $ProviderStatus
    if($minutes -gt 0){
      $until=$entry.last.AddMinutes($minutes)
      if($now -lt $until){
        [pscustomobject]@{language=$entry.language;status=$entry.status;until=$until}
      }
    }
  }
  return $active | Sort-Object until -Descending | Select-Object -First 1
}

function Update-CardmarketBlockedStreak([string]$Base,[string]$Status,
                                       [string]$Language,[string]$ProgressAt,
                                       [string]$RunId) {
  if($Status -notin @('BLOCKED','BATCH_COMPLETE_MORE_PENDING',
                     'COMPLETED_WITH_DEFERRED','COMPLETED','COMPLETE')){return}
  $path=Join-Path $Base 'cardmarket-blocked-streak.json'
  $previous=Get-CardmarketBlockedStreak $Base
  # Reading 2 for a missing or unreadable file is a fail-closed gate, not a
  # count suitable for incrementing. The runner always writes fresh state
  # before the next launch; unusual corrupt state remains full-backoff.
  $stateIsValid=$false
  if(Test-Path -LiteralPath $path) {
    try {
      $old=Get-Content -Raw -Encoding UTF8 -LiteralPath $path | ConvertFrom-Json
      $stateIsValid=([int]$old.count -ge 0 -and
        [string]$old.lastStatus -in @('BLOCKED','BATCH_COMPLETE_MORE_PENDING',
                                    'COMPLETED_WITH_DEFERRED','COMPLETED','COMPLETE'))
      if($stateIsValid -and [string]$old.lastRunId -eq $RunId -and
         [string]$old.lastLanguage -eq $Language -and
         [string]$old.lastProgressAt -eq $ProgressAt){return}
    } catch {$stateIsValid=$false}
  }
  if(-not $stateIsValid){
    # A completely new installation starts its first recorded failure at 1.
    # A corrupt existing history is treated as a previous unknown block.
    $previous=if(Test-Path -LiteralPath $path){1}else{0}
  }
  $count=if($Status -eq 'BLOCKED'){[Math]::Min(2,([int]$previous+1))}else{0}
  $record=[ordered]@{
    count=$count
    lastStatus=$Status
    lastLanguage=$Language
    lastProgressAt=$ProgressAt
    lastRunId=$RunId
    updatedAt=[DateTime]::UtcNow.ToString('o')
  }
  $tmp=Join-Path $Base ('cm-streak-'+[guid]::NewGuid().ToString('N')+'.tmp')
  try {
    $record|ConvertTo-Json -Compress|Set-Content -Encoding UTF8 -LiteralPath $tmp
    Move-Item -LiteralPath $tmp -Destination $path -Force
  } finally {
    if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp -Force}
  }
}

# Keep semantic ambiguities and blocked products out of consecutive batches.
function Test-CardmarketUnresolvedObservation {
  param($Observation, $Epoch)
  if(!$Observation){return $false}
  $status=[string]$Observation.status
  if($status -eq 'BLOCKED'){return $true}
  if($status -notin @('MULTIPLE_SEARCH_HITS','NO_EXACT_NUMBER_SEARCH_HIT',
                     'PRODUCT_ID_NOT_VERIFIED_FOR_CARD','PRODUCT_IN_VERIFIED_SET_PRINT_UNVERIFIED')){
    return $false
  }
  try {
    return ($null -eq $Epoch -or [DateTimeOffset]::Parse([string]$Observation.seen_at).UtcDateTime -ge $Epoch)
  } catch {return $true}
}

# The expansion index found a direct product URL after an older (search based)
# observation: scan again, even if that older attempt failed in this epoch.
# Skip only when the same product page already gave a complete result.
function Test-CardmarketIndexUpgradeDue($Case, $Prior) {
  if(!$Prior){return $false}
  if([string]$Case.index_status -notlike 'DIRECT_*' -or ![string]$Case.index_product_url){return $false}
  if([string]$Prior.lookup_strategy -eq 'EXPANSION_INDEX_DIRECT_V1'){return $false}
  $samePath=$false
  try{$samePath=(([uri][string]$Prior.url).AbsolutePath -eq ([uri][string]$Case.index_product_url).AbsolutePath)}catch{}
  return -not ($samePath -and [string]$Prior.status -like 'COMPLETE*')
}

function Get-CardmarketDueCases {
  param([object[]]$Cases, [hashtable]$Latest, $Processed, [datetime]$NowUtc, $Epoch)
  $priority=[Collections.Generic.List[object]]::new()
  $corrected=[Collections.Generic.List[object]]::new()
  $upgrade=[Collections.Generic.List[object]]::new()
  $fresh=[Collections.Generic.List[object]]::new()
  $retry=[Collections.Generic.List[object]]::new()
  $unresolved=[Collections.Generic.List[object]]::new()
  foreach($item in $Cases){
    $key='{0}|{1}' -f $item.cardyssey_karte,$item.variante_id
    if($Processed.Contains($key)){continue}
    $prior=$Latest[$key]
    $seen=$null
    if($prior){
      try {$seen=[DateTimeOffset]::Parse([string]$prior.seen_at).UtcDateTime} catch {}
    }
    if(Test-CardmarketIndexUpgradeDue $item $prior){
      # Corrected product IDs first: the old price may belong to another card.
      if([string]$item.index_status -eq 'DIRECT_PRODUCT_URL_ID_CORRECTED' -or [string]$prior.status -like 'COMPLETE*'){$corrected.Add($item)}
      else{$upgrade.Add($item)}
      continue
    }
    if(Test-CardmarketUnresolvedObservation $prior $Epoch){
      if($null -ne $seen -and $seen -le $NowUtc.AddHours(-72)){$unresolved.Add($item)}
      continue
    }
    $manualRequested=$false
    if([string]$item.manual_scan_requested_at){
      try {
        $requested=[DateTimeOffset]::Parse([string]$item.manual_scan_requested_at).UtcDateTime
        $manualRequested=($null -eq $seen -or $requested -gt $seen)
      } catch {}
    }
    if($manualRequested -or [string]$prior.status -eq 'SINGLE_LANGUAGE_FALLBACK_REQUIRED'){$priority.Add($item)}
    elseif($prior -and $prior.status -like 'DEFERRED*'){
      if($null -ne $seen -and $seen -le $NowUtc.AddHours(-2)){$retry.Add($item)}
    }
    elseif($prior -and ($prior.status -eq 'ERROR' -or
           ($prior.status -eq 'NO_EXACT_NUMBER_SEARCH_HIT' -and [int]$prior.search_hits -eq 0))){
      $retry.Add($item)
    }
    else {$fresh.Add($item)}
  }
  return $priority.ToArray() + $corrected.ToArray() + $upgrade.ToArray() + @(Sort-CardmarketByValue $fresh.ToArray()) + $retry.ToArray() + $unresolved.ToArray()
}

# Within one tier the most valuable cards first, so the daily refresh of
# expensive cards is not stuck behind thousands of cheaper ones.
function Sort-CardmarketByValue([object[]]$Items) {
  $i=0
  return @($Items | ForEach-Object {
    [decimal]$price=0
    [void][decimal]::TryParse(([string]$_.existing_price_eur).Trim(),
      [Globalization.NumberStyles]::AllowDecimalPoint,[Globalization.CultureInfo]::InvariantCulture,[ref]$price)
    $tier=0; [void][int]::TryParse([string]$_.scan_tier,[ref]$tier)
    [pscustomobject]@{Case=$_;Tier=$tier;Price=$price;Index=$i}
    $i++
  } | Sort-Object Tier,@{Expression='Price';Descending=$true},Index | ForEach-Object { $_.Case })
}

function Get-CardmarketLanguageOrder {
  param([string]$Base, [string]$Languages)
  if($Languages -ne 'both'){return $Languages}
  $states=foreach($language in @('de','en')){
    try {
      $progress=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $Base "progress-$language.json") | ConvertFrom-Json
      [pscustomobject]@{language=$language;status=[string]$progress.status;
        last=[DateTimeOffset]::Parse([string]$progress.updated_at).UtcDateTime}
    } catch {
      [pscustomobject]@{language=$language;status='';last=[datetime]::MinValue}
    }
  }
  $ordered=@($states | Sort-Object -Property last,language)
  if($ordered[-1].status -eq 'BLOCKED'){[array]::Reverse($ordered)}
  return $ordered.language
}
