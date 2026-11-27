# Cardmarket scanning is scheduled on Windows and shares one Edge CDP tab.
# Rotate German/English batches so neither backlog can starve the other.
# Never bypass a provider challenge or queue a retry indefinitely.
param(
  [ValidateRange(1,1000)][int]$BatchLimit = 200,
  [ValidateRange(4,120)][int]$DelaySeconds = 8,
  [ValidateRange(4,90)][int]$MinRequestGapSeconds = 8,
  [ValidateRange(1,90)][int]$MinAjaxGapSeconds = 3,
  [ValidateSet('de','en','both')][string]$Languages = 'de',
  [ValidateRange(0,110)][int]$RunMinutes = 50,
  [ValidateRange(0,500)][int]$IndexRequestsPerRun = 100,
  [ValidateSet('identity','missing')][string]$ScanMode='identity',
  [switch]$SingleBatch,
  [switch]$RequireLogin  # optional diagnostics only; production launcher omits it
)
$ErrorActionPreference='Stop'
$base=Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector'
$collector=Join-Path $base 'cardmarket-language-browser-collector_test.ps1'
$backoffScript=Join-Path $base 'Cardmarket-Backoff-Policy.ps1'
if(!(Test-Path $backoffScript)){throw 'CARDMARKET_BACKOFF_POLICY_MISSING'}
. $backoffScript
$runnerId=[guid]::NewGuid().ToString('N')
# The official, validated DE/EN product-page leads are rebuilt locally after
# a language batch. The target scanner still checks its own idProduct and
# printed number; a localized URL is not a price or print confirmation.
function Update-CrossLanguagePageCache {
  $script='/home/tv/cardshop/scripts/cardmarket/core/cardmarket-build-cross-language-page-cache.py'
  $output='/mnt/c/Users/TV/AppData/Local/Cardyssey/CardmarketCollector/cardmarket-cross-language-page-cache.json'
  $wsl='C:\Windows\System32\wsl.exe'
  if(!(Test-Path $wsl)){Write-Output 'CROSS_LANGUAGE_CACHE_SKIPPED_NO_WSL';return}
  $args=@('-d','Ubuntu','-e','python3',$script,'--output',$output)
  $proc=$null
  try {
    $proc=Start-Process -FilePath $wsl -ArgumentList $args -WindowStyle Hidden -PassThru
    if(-not $proc.WaitForExit(25000)){
      try{$proc.Kill()}catch{}
      Write-Output 'CROSS_LANGUAGE_CACHE_TIMEOUT_USING_PREVIOUS_CACHE'
    } elseif($proc.ExitCode -eq 0){Write-Output 'CROSS_LANGUAGE_CACHE_REFRESHED'}
    else{Write-Output ('CROSS_LANGUAGE_CACHE_NONZERO '+$proc.ExitCode)}
  }catch{Write-Output ('CROSS_LANGUAGE_CACHE_FAILED '+$_.Exception.GetType().Name)}
  finally{if($proc){$proc.Dispose()}}
}
if(!(Test-Path $collector)){throw 'Updated language collector missing'}
function Invoke-WslPython([string]$Script,[string[]]$Arguments=@(),[int]$TimeoutSec=240) {
  $wsl='C:\Windows\System32\wsl.exe'
  if(!(Test-Path $wsl)){return 'NO_WSL'}
  $proc=$null
  try {
    $proc=Start-Process -FilePath $wsl -ArgumentList (@('-d','Ubuntu','-e','python3',$Script)+$Arguments) -WindowStyle Hidden -PassThru
    if(-not $proc.WaitForExit($TimeoutSec*1000)){try{$proc.Kill()}catch{};return 'TIMEOUT'}
    return ('EXIT '+$proc.ExitCode)
  }catch{return ('FAILED '+$_.Exception.GetType().Name)}
  finally{if($proc){$proc.Dispose()}}
}
# Expansion-list index: a bounded slice of Cardmarket's own expansion lists
# per run gives direct product URLs, so the collector needs no search.
# Same request gap; a challenge stops everything exactly like a scan block.
$indexScript=Join-Path $base 'Cardmarket-Expansion-Index.ps1'
if($IndexRequestsPerRun -gt 0 -and (Test-Path $indexScript)){
  $linuxCore='/home/tv/cardshop/scripts/cardmarket/core/'
  & $indexScript -MaxRequests $IndexRequestsPerRun -MinRequestGapSeconds $MinRequestGapSeconds | Out-Null
  $indexState=Get-Content -Raw -Encoding UTF8 (Join-Path $base 'expansion-index-status.json') | ConvertFrom-Json
  Write-Output ('EXPANSION_INDEX '+$indexState.status+' requests='+$indexState.requests+' pages='+$indexState.pages)
  if($indexState.status -eq 'BLOCKED'){
    $progressFile=Join-Path $base 'progress-de.json'
    if(Test-Path $progressFile){
      $x=Get-Content -Raw -Encoding UTF8 $progressFile | ConvertFrom-Json
      $x.status='BLOCKED'
      $x.updated_at=[DateTime]::UtcNow.ToString('o')
      $x | Add-Member NoteProperty provider_block_stage 'EXPANSION_INDEX' -Force
      $x | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 -Path $progressFile
      Update-CardmarketBlockedStreak -Base $base -Status 'BLOCKED' -Language 'de' -ProgressAt ([string]$x.updated_at) -RunId $runnerId
    }
    & (Join-Path $base 'Cardmarket-Resume-Watchdog.ps1') -ReportBlocked
    Write-Output 'STOP_ON_PROVIDER_OR_CONNECTION_ERROR'
    return
  }
  if($indexState.status -eq 'OVERVIEW_UPDATED_PLAN_REBUILD_NEEDED'){
    Write-Output ('EXPANSION_INDEX_PLAN '+(Invoke-WslPython ($linuxCore+'build-cardmarket-expansion-index-plan.py')))
  }
  $queueHeader=[string](Get-Content -TotalCount 1 -Encoding UTF8 (Join-Path $base 'queue-de.csv'))
  if([int]$indexState.pages -gt 0 -or $queueHeader -notmatch 'index_status'){
    Write-Output ('EXPANSION_INDEX_APPLY '+(Invoke-WslPython ($linuxCore+'apply-cardmarket-expansion-index.py')))
  }
}
$selectedLanguages=@(Get-CardmarketLanguageOrder -Base $base -Languages $Languages)
$done=@{}
foreach($l in $selectedLanguages){$done[$l]=$false}
$deadline=[DateTime]::UtcNow.AddMinutes($RunMinutes)
$stop=$false
do {
  foreach($language in $selectedLanguages){
    if($done[$language]){continue}
    if($SingleBatch -and $Languages -eq 'both'){
      $saved=Join-Path $base "progress-$language.json"
      if(Test-Path $saved){
        $savedState=Get-Content -Raw -Encoding UTF8 $saved | ConvertFrom-Json
        if($savedState.status -in @('COMPLETED','COMPLETE')){$done[$language]=$true;continue}
      }
    }
    if($RunMinutes -gt 0 -and [DateTime]::UtcNow -ge $deadline){break}
    # The collector stops itself at the wall clock. Handing it the remaining
    # seconds keeps the batch inside the live clearance instead of relying on
    # a fixed case count.
    $runSeconds=if($RunMinutes -gt 0){[int][Math]::Max(60,($deadline-[DateTime]::UtcNow).TotalSeconds)}else{0}
    Write-Output ('LANGUAGE_BEGIN '+$language+' '+[DateTime]::UtcNow.ToString('o'))
    & $collector -Language $language -InputCsv (Join-Path $base "queue-$language.csv") -OutputDir $base -CdpPort 9223 -BatchLimit $BatchLimit -DelaySeconds $DelaySeconds -MinRequestGapSeconds $MinRequestGapSeconds -MinAjaxGapSeconds $MinAjaxGapSeconds -RunSeconds $runSeconds -ScanMode $ScanMode -RequireLogin:$RequireLogin
    if(!$?){throw "Collector failed for $language"}
    $progress=Get-Content -Raw (Join-Path $base "progress-$language.json") | ConvertFrom-Json
    Write-Output ('LANGUAGE_END '+$language+' status='+$progress.status+' processed='+$progress.done)
    # Durable streak is updated ONCE per completed language run.
    # Provider/connection errors keep prior streak; verified normal batches
    # reset it. Neither queue nor observation files are modified here.
    if($progress.provider_attempted -ne $false -or $progress.status -eq 'BLOCKED'){
      Update-CardmarketBlockedStreak -Base $base -Status ([string]$progress.status) -Language $language -ProgressAt ([string]$progress.updated_at) -RunId $runnerId
    }
    if($progress.status -eq 'BATCH_COMPLETE_MORE_PENDING' -and $selectedLanguages.Count -gt 1){
      Update-CrossLanguagePageCache
    }
    if($progress.status -in @('BLOCKED','PROVIDER_TIMEOUT','CONNECTION_LOST','LOGIN_REQUIRED','LOGIN_UNVERIFIED')){
      # A provider challenge/login failure may affect both language sessions.
      # Do not hammer the other queue. The Windows task safely resumes later.
      if($progress.status -eq 'BLOCKED'){
        $watchdog=Join-Path $base 'Cardmarket-Resume-Watchdog.ps1'
        & $watchdog -ReportBlocked
      }
      Write-Output 'STOP_ON_PROVIDER_OR_CONNECTION_ERROR'
      $stop=$true;break
    }
    if($progress.status -in @('COMPLETE','COMPLETED','COMPLETED_WITH_DEFERRED') -or
       [int]$progress.done -ge [int]$progress.total){
      $done[$language]=$true
    } elseif($progress.status -ne 'BATCH_COMPLETE_MORE_PENDING'){
      Write-Output ('UNEXPECTED_PROGRESS_STATE '+$language+' '+$progress.status)
      $stop=$true;break
    }
    if($SingleBatch){break}
    # Each collector process starts with an empty request clock, so the gap
    # to the previous language's last request is held here.
    if($RunMinutes -gt 0 -and [DateTime]::UtcNow -lt $deadline){
      Start-Sleep -Seconds $MinRequestGapSeconds
    }
  }
  if($stop -or $SingleBatch -or $RunMinutes -eq 0 -or [DateTime]::UtcNow -ge $deadline){break}
  $pending=@($selectedLanguages | Where-Object {-not $done[$_]})
  if($pending.Count -eq 0){break}
  Start-Sleep -Seconds $MinRequestGapSeconds  # new collector process: keep the provider gap
}while($true)
Write-Output ('RUNNER_END '+[DateTime]::UtcNow.ToString('o')+
  ' completed='+(@($selectedLanguages | Where-Object {$done[$_]} ) -join ',')+
  ' stopped='+$stop)
