# Cardyssey maintenance: only abandoned GUID-named swap.vhdx under user Temp.
# NEVER access the live Docker/Ubuntu VHDX files or delete mounted volumes.
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Temp'))
$state=Join-Path $env:LOCALAPPDATA 'Cardyssey\Maintenance'
New-Item -ItemType Directory -Force $state|Out-Null
$log=Join-Path $state 'storage-cleanup.log'
$freed=[long]0; $removed=0; $skipped=0
$guid='^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
foreach($folder in (Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue)) {
 if($folder.Name -notmatch $guid) {continue}
 $file=Join-Path $folder.FullName 'swap.vhdx'
 if(!(Test-Path -LiteralPath $file -PathType Leaf)){continue}
 $info=Get-Item -LiteralPath $file
 if($info.LastWriteTimeUtc -gt [DateTime]::UtcNow.AddHours(-48)){$skipped++;continue}
 try {
  $stream=[IO.File]::Open($file,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
  $stream.Dispose()
  Remove-Item -LiteralPath $file -Force -ErrorAction Stop
  $freed+=$info.Length;$removed++
 } catch {$skipped++}
}
$free=(Get-PSDrive C).Free
$line='{0:o} removed={1} freed_bytes={2} skipped={3} free_C_GiB={4:N2}' -f [DateTime]::UtcNow,$removed,$freed,$skipped,($free/1GB)
Add-Content -LiteralPath $log -Value $line -Encoding UTF8
if((Get-Item $log).Length -gt 1048576) {Get-Content $log -Tail 150|Set-Content $log -Encoding UTF8}
Write-Output $line
