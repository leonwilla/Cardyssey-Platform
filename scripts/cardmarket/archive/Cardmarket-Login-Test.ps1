# Opens Cardmarket in a separate interactive Chrome profile. No password/session export.
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
if (-not (Test-Path $chrome)) { $chrome = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' }
if (-not (Test-Path $chrome)) { throw 'Chrome or Edge could not be found.' }
$profile = Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketReviewProfile'
New-Item -ItemType Directory -Force -Path $profile | Out-Null
Start-Process -FilePath $chrome -ArgumentList @("--user-data-dir=$profile",'--no-first-run','--new-window','https://www.cardmarket.com/de/Pokemon')
