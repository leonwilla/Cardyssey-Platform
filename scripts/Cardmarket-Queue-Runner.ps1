# Cardmarket scanning is scheduled on Windows and shares one Edge CDP tab.
# Rotate German/English batches so neither backlog can starve the other.
# Never bypass a provider challenge or queue a retry indefinitely.
param(
  [ValidateRange(1,1000)][int]$BatchLimit = 40,
  [ValidateRange(3,120)][int]$DelaySeconds = 8,
  [ValidateSet('de','en','both')][string]$Languages = 'de',
  [ValidateRange(0,110)][int]$RunMinutes = 95,
  [ValidateSet('identity','missing')][string]$ScanMode='identity',
  [switch]$RequireLogin
)
$ErrorActionPreference='Stop'
$base=Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector'
$collector=Join-Path $base 'cardmarket-language-browser-collector.ps1'
if(!(Test-Path $collector)){throw 'Updated language collector missing'}
$selectedLanguages=if($Languages -eq 'both'){@('de','en')}else{@($Languages)}
$done=@{}
foreach($l in $selectedLanguages){$done[$l]=$false}
$deadline=[DateTime]::UtcNow.AddMinutes($RunMinutes)
$stop=$false
do {
  foreach($language in $selectedLanguages){
    if($done[$language]){continue}
    if($RunMinutes -gt 0 -and [DateTime]::UtcNow -ge $deadline){break}
    Write-Output ('LANGUAGE_BEGIN '+$language+' '+[DateTime]::UtcNow.ToString('o'))
    & $collector -Language $language -InputCsv (Join-Path $base "queue-$language.csv") -OutputDir $base -CdpPort 9223 -BatchLimit $BatchLimit -DelaySeconds $DelaySeconds -ScanMode $ScanMode -RequireLogin:$RequireLogin
    if(!$?){throw "Collector failed for $language"}
    $progress=Get-Content -Raw (Join-Path $base "progress-$language.json") | ConvertFrom-Json
    Write-Output ('LANGUAGE_END '+$language+' status='+$progress.status+' processed='+$progress.done)
    if($progress.status -in @('BLOCKED','PROVIDER_TIMEOUT','CONNECTION_LOST','LOGIN_REQUIRED','LOGIN_UNVERIFIED')){
      # A provider challenge/login failure may affect both language sessions.
      # Do not hammer the other queue. The Windows task safely resumes later.
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
    if($RunMinutes -gt 0 -and [DateTime]::UtcNow -lt $deadline){
      Start-Sleep -Seconds 12
    }
  }
  if($stop -or $RunMinutes -eq 0 -or [DateTime]::UtcNow -ge $deadline){break}
  $pending=@($selectedLanguages | Where-Object {-not $done[$_]})
  if($pending.Count -eq 0){break}
  Start-Sleep -Seconds 25
}while($true)
Write-Output ('RUNNER_END '+[DateTime]::UtcNow.ToString('o')+
  ' completed='+(@($selectedLanguages | Where-Object {$done[$_]} ) -join ',')+
  ' stopped='+$stop)
