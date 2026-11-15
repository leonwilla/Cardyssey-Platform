# Exercise the Windows launcher in an isolated profile with no network requests.
$ErrorActionPreference='Stop'
$launcher=Join-Path $PSScriptRoot '../core/Cardmarket-Collector-Launcher.ps1'
$policy=Join-Path $PSScriptRoot '../core/Cardmarket-Backoff-Policy.ps1'
$temp=Join-Path ([IO.Path]::GetTempPath()) ('cardmarket-launcher-test-'+[guid]::NewGuid().ToString('N'))
$savedLocalAppData=$env:LOCALAPPDATA

function Assert-Test([bool]$ok,[string]$message) {
    if(!$ok){throw $message}
}
function Get-CimInstance { }
function Invoke-RestMethod {
    param($TimeoutSec,$Uri)
    $fixture.connectionProbes++
    if($fixture.coldBrowser -and $fixture.connectionProbes -eq 1){throw 'Fixture browser unavailable'}
    return @()
}
function Start-Process {
    param($FilePath,$ArgumentList,$WindowStyle,$RedirectStandardOutput,$RedirectStandardError)
    $fixture.launches.Add([pscustomobject]@{file=$FilePath;args=$ArgumentList})
}
function Start-Sleep { param($Seconds) }

try {
    $env:LOCALAPPDATA=$temp
    $base=Join-Path $temp 'Cardyssey\CardmarketCollector'
    $null=New-Item -ItemType Directory -Path $base -Force
    Copy-Item $policy $base
    Set-Content (Join-Path $base 'Cardmarket-Queue-Runner.ps1') '# Runner fixture'
    Set-Content (Join-Path $base 'Cardmarket-Session-Warmup.ps1') @'
param([switch]$AllowBlankBootstrap)
if(!$AllowBlankBootstrap){throw 'Warmup may open only a freshly started browser tab'}
Add-Content (Join-Path $env:LOCALAPPDATA 'warmup.log') 'bootstrap'
'{"status":"READY_FOR_HEALTH_CHECK"}'
'@
    Set-Content (Join-Path $base 'Cardmarket-Session-Status.ps1') @'
Get-Content -Raw (Join-Path $env:LOCALAPPDATA 'fixture-session.json')
'@
    $session=Join-Path $temp 'fixture-session.json'
    $warmupLog=Join-Path $temp 'warmup.log'
    $progress=Join-Path $base 'progress-de.json'
    $fixture=@{launches=[Collections.Generic.List[object]]::new();connectionProbes=0;coldBrowser=$false}

    Set-Content $session '{"status":"AVAILABLE","login":"LOGIN_REQUIRED"}'
    $guest=@(& $launcher -ManualResume)
    Assert-Test ($guest -contains 'CARDMARKET_PUBLIC_LIMITED_SESSION_CONTINUE') 'Guest mode should start the scanner'
    Assert-Test ($fixture.launches.Count -eq 1 -and $fixture.launches[0].file -eq 'powershell.exe') 'Expected only the scanner process'
    Assert-Test (!(Test-Path $warmupLog)) 'Existing available tab was reloaded'

    Set-Content $progress '{"status":"BLOCKED","updated_at":"2026-11-01T10:00:00Z","done":758,"total":16381}'
    $previous=Get-Content -Raw $progress
    Set-Content $session '{"status":"BLOCKED","login":"UNKNOWN"}'
    $fixture.launches.Clear()
    $blocked=@(& $launcher -ManualResume)
    Assert-Test ($blocked -contains 'CARDMARKET_PAUSED BLOCKED') 'Active challenge must stop the runner'
    Assert-Test ($fixture.launches.Count -eq 0 -and !(Test-Path $warmupLog)) 'Blocked tab was used for new requests'
    Assert-Test ((Get-Content -Raw $progress) -eq $previous) 'Re-reading a challenge restarted the cooldown'

    @{status='BLOCKED';updated_at=[DateTime]::UtcNow.AddMinutes(-10).ToString('o')} | ConvertTo-Json | Set-Content $progress
    Set-Content $session '{"status":"AVAILABLE","login":"AUTHENTICATED"}'
    $fixture.connectionProbes=0
    $waiting=@(& $launcher -ManualResume)
    Assert-Test ($waiting[0] -like 'CARDMARKET_COOLDOWN*' -and $fixture.connectionProbes -eq 0) 'Active cooldown must gate the normal resume'

    Remove-Item -LiteralPath $progress
    $fixture.coldBrowser=$true
    $fixture.connectionProbes=0
    $cold=@(& $launcher)
    Assert-Test ($cold -contains 'CARDMARKET_WARMUP_DONE_6S') 'Fresh browser still needs its bootstrap page'
    Assert-Test ($fixture.launches.Count -eq 2 -and $fixture.launches[1].file -eq 'powershell.exe') 'Expected Edge followed by scanner'
    Assert-Test (@(Get-Content $warmupLog).Count -eq 1) 'Expected exactly one cold-start navigation'
    Write-Output 'CARDMARKET_LAUNCHER_TESTS_OK'
} finally {
    $env:LOCALAPPDATA=$savedLocalAppData
    if(Test-Path $temp){Remove-Item -LiteralPath $temp -Recurse}
}
