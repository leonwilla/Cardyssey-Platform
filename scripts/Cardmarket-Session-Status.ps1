# Read-only diagnosis of the SAME persistent Cardmarket Edge profile.
# Never accesses password manager contents, credentials, cookies or tokens.
$ErrorActionPreference='Stop'
$base=Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketCollector'
$dest=Join-Path $base 'browser-session-status.json'
$state=[ordered]@{checkedAt=[DateTime]::UtcNow.ToString('o');provider='CARDMARKET';status='UNKNOWN';reason='';login='UNKNOWN';profileExists=(Test-Path (Join-Path $env:LOCALAPPDATA 'Cardyssey\CardmarketEdgeProfile'))}
$ws=$null
try {
  $targets=Invoke-RestMethod -Uri 'http://127.0.0.1:9223/json/list' -TimeoutSec 4
  $page=$targets | Where-Object {$_.type -eq 'page' -and ([string]$_.url) -match '^https://www[.]cardmarket[.]com/'} | Select-Object -First 1
  if(!$page){$state.status='NO_CARDMARKET_TAB';$state.reason='Browser tab unavailable'}
  else {
    if([string]$page.title -match '(?i)nur einen moment|just a moment|attention required|security check|checking your browser|access denied|cloudflare to restrict access|too many requests'){
      $state.status='BLOCKED';$state.reason='CLOUDFLARE_CHALLENGE'
    } elseif (!$page.webSocketDebuggerUrl){
      $state.status='BROWSER_UNAVAILABLE'
    } else {
      $ws=[Net.WebSockets.ClientWebSocket]::new()
      $ws.Options.SetRequestHeader('Origin','http://localhost')
      $cts=[Threading.CancellationTokenSource]::new(5000)
      try{$ws.ConnectAsync([uri]$page.webSocketDebuggerUrl,$cts.Token).GetAwaiter().GetResult()|Out-Null}finally{$cts.Dispose()}
      $js='JSON.stringify({title:document.title,blocked:/(nur einen moment|just a moment|attention required|checking your browser|captcha|access denied|cloudflare to restrict access|too many requests)/i.test(document.title),loginForm:!!document.querySelector("form[action*=Login],form[action*=login],input[type=password]"),logoutLink:!!document.querySelector("a[href*=User_Logout],form[action*=User_Logout]"),accountHint:!!document.querySelector("a[href*=User_Profile],a[href*=User_Account],a[href*=MyAccount]"),pageReady:document.readyState})'
      $packet=@{id=7;method='Runtime.evaluate';params=@{expression=$js;returnByValue=$true}}|ConvertTo-Json -Compress -Depth 5
      $buffer=[Text.Encoding]::UTF8.GetBytes($packet)
      $ws.SendAsync([ArraySegment[byte]]::new($buffer),[Net.WebSockets.WebSocketMessageType]::Text,$true,[Threading.CancellationToken]::None).GetAwaiter().GetResult()|Out-Null
      $result=$null
      $deadline=[DateTime]::UtcNow.AddSeconds(5)
      while([DateTime]::UtcNow -lt $deadline){
        $bytes=New-Object byte[] 65536
        $wait=[Threading.CancellationTokenSource]::new(1500)
        try{$answer=$ws.ReceiveAsync([ArraySegment[byte]]::new($bytes),$wait.Token).GetAwaiter().GetResult()}catch{break}finally{$wait.Dispose()}
        if(!$answer.EndOfMessage){continue}
        $frame=[Text.Encoding]::UTF8.GetString($bytes,0,$answer.Count)|ConvertFrom-Json
        if($frame.id -ne 7){continue}
        if($frame.result.result.value){$result=$frame.result.result.value | ConvertFrom-Json}
        break
      }
      if(!$result){$state.status='BROWSER_STATE_UNREADABLE'}
      elseif($result.blocked){$state.status='BLOCKED';$state.reason='CLOUDFLARE_CHALLENGE'}
      elseif($result.logoutLink){$state.status='AVAILABLE';$state.login='AUTHENTICATED';$state.reason='VISIBLE_LOGOUT_LINK'}
      elseif($result.loginForm){$state.status='AVAILABLE';$state.login='LOGIN_REQUIRED';$state.reason='VISIBLE_LOGIN_FORM'}
      else{$state.status='AVAILABLE';$state.login='UNVERIFIED';$state.reason='NO_RELIABLE_LOGIN_INDICATOR'}
    }
  }
} catch {$state.status='BROWSER_UNAVAILABLE';$state.reason='LOCAL_BROWSER_CONNECTION_ERROR'}
finally{if($ws){try{$ws.Dispose()}catch{}}}
New-Item -ItemType Directory -Force -Path $base|Out-Null
($state|ConvertTo-Json -Compress -Depth 3)|Set-Content -Encoding UTF8 -Path $dest
$state|ConvertTo-Json -Compress -Depth 3
