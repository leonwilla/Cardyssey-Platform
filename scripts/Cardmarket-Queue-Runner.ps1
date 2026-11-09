# Runs DE and EN queues sequentially against the dedicated Edge session.
# Public catalogue mode is automatic when the Cardmarket account is logged out.
param(
  [ValidateRange(1,1000)][int]$BatchLimit = 40,
  [ValidateRange(3,120)][int]$DelaySeconds = 8,
  [ValidateSet('de','en','both')][string]$Languages = 'de',
  [ValidateRange(0,110)][int]$RunMinutes = 95,
  [ValidateSet('identity','missing')][string]$ScanMode='identity',
  [switch]$RequireLogin
)
$ErrorActionPreference = 'Stop'
$base = Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector'
$collector = Join-Path $base 'cardmarket-language-browser-collector.ps1'
if (!(Test-Path $collector)) { throw 'Updated language collector missing' }
$selectedLanguages = if ($Languages -eq 'both') { @('de','en') } else { @($Languages) }
# Run useful, bounded batches continuously within one scheduled session.
# The Windows task has a two-hour hard ceiling; use <110 minutes here.
$deadline=[DateTime]::UtcNow.AddMinutes($RunMinutes)
$stop=$false
foreach ($language in $selectedLanguages) {
  do {
    Write-Output ('LANGUAGE_BEGIN ' + $language + ' ' + [DateTime]::UtcNow.ToString('o'))
    & $collector -Language $language -InputCsv (Join-Path $base "queue-$language.csv") -OutputDir $base -CdpPort 9223 -BatchLimit $BatchLimit -DelaySeconds $DelaySeconds -ScanMode $ScanMode -RequireLogin:$RequireLogin
    if (!$?) { throw "Collector failed for $language" }
    $progress = Get-Content -Raw (Join-Path $base "progress-$language.json") | ConvertFrom-Json
    Write-Output ('LANGUAGE_END ' + $language + ' status=' + $progress.status + ' processed=' + $progress.done)
    if ($progress.status -in @('BLOCKED','PROVIDER_TIMEOUT','CONNECTION_LOST','LOGIN_REQUIRED','LOGIN_UNVERIFIED')) {
      Write-Output 'STOP_ON_PROVIDER_OR_CONNECTION_ERROR'
      $stop=$true
      break
    }
    if ($progress.status -eq 'COMPLETE' -or $progress.done -ge $progress.total) { break }
    # A bounded delay between batches lowers the chance of provider throttling.
    if ($RunMinutes -gt 0 -and [DateTime]::UtcNow -lt $deadline) {
      Start-Sleep -Seconds 25
    }
  } while ($RunMinutes -gt 0 -and [DateTime]::UtcNow -lt $deadline -and
           $progress.status -eq 'BATCH_COMPLETE_MORE_PENDING')
  if ($stop) { break }
}
