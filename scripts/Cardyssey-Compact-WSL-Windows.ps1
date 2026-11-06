# Run ONCE from an elevated Windows PowerShell window after work is saved.
# Compact Ubuntu's offline WSL VHDX; never delete or rewrite database files.
$ErrorActionPreference='Stop'
$windowsUser=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if(!$windowsUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
 throw 'Administrative PowerShell required. No changes made.'
}
$root=Join-Path $env:LOCALAPPDATA 'wsl'
$virtualDisks=@(Get-ChildItem -LiteralPath $root -Recurse -Filter 'ext4.vhdx' -File -ErrorAction Stop)
if($virtualDisks.Count -ne 1){throw "Expected exactly one Ubuntu VHDX at $root; found $($virtualDisks.Count). No changes made."}
$disk=$virtualDisks[0].FullName
$before=(Get-PSDrive C).Free
$base=Join-Path $env:LOCALAPPDATA 'Cardyssey\Maintenance'
New-Item -ItemType Directory -Force $base | Out-Null
$diskpart=Join-Path $base 'ubuntu-compact-diskpart.txt'
$log=Join-Path $base 'ubuntu-compaction.log'
Write-Output "Ubuntu VHDX: $disk"
Write-Output ('C: free before: {0:N2} GiB' -f ($before/1GB))
# Ubuntu must be fully offline during compaction. Docker Desktop's separate
# docker-desktop WSL distro is deliberately not compacted or deleted.
try {
 & wsl.exe --terminate Ubuntu
 if($LASTEXITCODE -ne 0){throw 'Could not stop Ubuntu; compaction aborted'}
 @("select vdisk file=`"$disk`"", 'compact vdisk', 'exit') | Set-Content -LiteralPath $diskpart -Encoding ASCII
 $output=& diskpart.exe /s $diskpart 2>&1
 $output | Out-File -FilePath $log -Encoding utf8
 $after=(Get-PSDrive C).Free
 Write-Output ('C: free after: {0:N2} GiB (delta {1:N2} GiB)' -f ($after/1GB),(($after-$before)/1GB))
 Write-Output "Diskpart log: $log"
 if($LASTEXITCODE -ne 0){throw 'Diskpart reported a failure. See log.'}
} finally {
 # Restart the distro so enabled Cardyssey services can start again.
 & wsl.exe -d Ubuntu -u tv -- /usr/bin/true
}
