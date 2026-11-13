# Persistent provider backoff for both language queues.
# This file is sourced by the Windows launcher, watchdog and queue runner.
# A first failed scan run can retry after 30m ONLY when a fresh, read-only
# Cardmarket session check reports AVAILABLE. The second consecutive BLOCKED
# run restores the full 240m provider backoff, as do unreadable states.
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
      $streak=Get-CardmarketBlockedStreak $Base
      if($streak -eq 1 -and $ProviderStatus -eq 'AVAILABLE'){return 30}
      return 240
    }
    'PROVIDER_TIMEOUT' {return 90}
    'CONNECTION_LOST' {return 60}
    'BATCH_COMPLETE_MORE_PENDING' {return 45}
    'COMPLETED_WITH_DEFERRED' {return 90}
    default {return 0}
  }
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
