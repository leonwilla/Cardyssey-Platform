# Runs DE and EN queues sequentially against the dedicated Edge session.
# Public catalogue mode is automatic when the Cardmarket account is logged out.
param(
  [ValidateRange(1,1000)][int]$BatchLimit = 40,
  [ValidateRange(3,120)][int]$DelaySeconds = 8,
  [ValidateSet('de','en','both')][string]$Languages = 'de' 
)
$ErrorActionPreference = 'Stop'
$base = Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector'
$collector = Join-Path $base 'cardmarket-language-browser-collector.ps1'
if (!(Test-Path $collector)) { throw 'Updated language collector missing' }
$selectedLanguages = if ($Languages -eq 'both') { @('de','en') } else { @($Languages) }
foreach ($language in $selectedLanguages) {
  Write-Output ('LANGUAGE_BEGIN ' + $language + ' ' + [DateTime]::UtcNow.ToString('o'))
  & $collector -Language $language -InputCsv (Join-Path $base "queue-$language.csv") -OutputDir $base -CdpPort 9223 -BatchLimit $BatchLimit -DelaySeconds $DelaySeconds
  if (!$?) { throw "Collector failed for $language" }
  $progress = Get-Content -Raw (Join-Path $base "progress-$language.json") | ConvertFrom-Json
  Write-Output ('LANGUAGE_END ' + $language + ' status=' + $progress.status + ' processed=' + $progress.done)
  if ($progress.status -in @('BLOCKED','PROVIDER_TIMEOUT','CONNECTION_LOST')) {
    Write-Output 'STOP_ON_PROVIDER_OR_CONNECTION_ERROR'
    break
  }
}
