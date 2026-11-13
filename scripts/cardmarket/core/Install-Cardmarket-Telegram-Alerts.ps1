# Run once in the interactive Windows PowerShell session of user TV.
# Never paste the bot token into ChatGPT, a command argument, or Git.
$ErrorActionPreference='Stop'
$base=Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector'
New-Item -ItemType Directory -Force -Path $base | Out-Null
$chatId='8739002054'
$secureToken=Read-Host 'Paste the NEW Telegram bot token (input is hidden)' -AsSecureString
if($secureToken.Length -lt 20){throw 'Bot token missing or too short'}
$protected=$secureToken | ConvertFrom-SecureString
$tokenPath=Join-Path $base 'telegram-bot-token.dpapi'
[System.IO.File]::WriteAllText($tokenPath,$protected,[System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText((Join-Path $base 'telegram-chat-id.txt'),$chatId,[System.Text.UTF8Encoding]::new($false))
$credentials=New-Object System.Management.Automation.PSCredential('telegram',$secureToken)
$clearToken=$credentials.GetNetworkCredential().Password
try{
  $result=Invoke-RestMethod -Method Post -Uri ('https://api.telegram.org/bot'+$clearToken+'/sendMessage') -Body @{
    chat_id=$chatId
    text='Cardyssey Telegram-Test: Verbindung eingerichtet. Warnungen bei Cloudflare oder Cardmarket-Loginproblemen sind aktiv.'
  } -TimeoutSec 20 -ErrorAction Stop
  if(-not $result.ok){throw 'Telegram API did not confirm delivery'}
  Write-Host 'TELEGRAM_TEST_OK: test message sent to your bot chat.'
}catch{
  # Avoid leaking the token from a verbose exception or URL.
  Write-Host 'TELEGRAM_TEST_FAILED: check the bot token, bot /start, and chat ID.'
  throw 'Telegram delivery could not be confirmed. The encrypted token was stored locally.'
}finally{
  $clearToken=$null
  $credentials=$null
  $secureToken.Dispose()
}
