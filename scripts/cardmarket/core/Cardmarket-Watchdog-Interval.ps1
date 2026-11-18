# Adjust the existing interactive task without changing its principal or actions.
$ErrorActionPreference='Stop'
$name='Cardyssey Cardmarket Resume Watchdog'
$task=Get-ScheduledTask -TaskName $name -TaskPath '\'
$repeating=@($task.Triggers | Where-Object {$_.Repetition.Interval})
if(!$repeating.Count){throw 'CARDMARKET_WATCHDOG_REPEATING_TRIGGER_MISSING'}
if(@($repeating | Where-Object {$_.Repetition.Interval -ne 'PT2M'}).Count){
  foreach($trigger in $repeating){$trigger.Repetition.Interval='PT2M'}
  Set-ScheduledTask -TaskName $name -TaskPath '\' -Trigger $task.Triggers | Out-Null
}
$registered=Get-ScheduledTask -TaskName $name -TaskPath '\'
if(!(@($registered.Triggers.Repetition.Interval) -contains 'PT2M')){throw 'CARDMARKET_WATCHDOG_INTERVAL_NOT_APPLIED'}
Write-Output 'CARDMARKET_WATCHDOG_INTERVAL=PT2M'
