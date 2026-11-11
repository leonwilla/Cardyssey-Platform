# Warm up the EXISTING persistent Edge tab once after the normal provider
# cooldown. No login automation, cookie reads, challenge solving or retries.
# Returns exactly one compact JSON status for the launcher to fail closed.
$ErrorActionPreference='Stop'
$result=[ordered]@{
  checkedAt=[DateTime]::UtcNow.ToString('o')
  status='UNAVAILABLE'
  action='NONE'
  warmupSeconds=0
}
$ws=$null
try {
  $targets=Invoke-RestMethod -Uri 'http://127.0.0.1:9223/json/list' -TimeoutSec 4
  $page=$targets | Where-Object {
    $_.type -eq 'page' -and ([string]$_.url) -match '^https://www[.]cardmarket[.]com/'
  } | Select-Object -First 1
  if(!$page){
    $result.status='NO_CARDMARKET_TAB'
  } elseif([string]$page.title -match '(?i)nur einen moment|just a moment|attention required|security check|checking your browser|access denied|too many requests|cloudflare|captcha'){
    $result.status='BLOCKED'
  } elseif(!$page.webSocketDebuggerUrl) {
    $result.status='BROWSER_UNAVAILABLE'
  } else {
    $ws=[Net.WebSockets.ClientWebSocket]::new()
    $ws.Options.SetRequestHeader('Origin','http://localhost')
    $cts=[Threading.CancellationTokenSource]::new(4000)
    try{$ws.ConnectAsync([uri]$page.webSocketDebuggerUrl,$cts.Token).GetAwaiter().GetResult()|Out-Null}finally{$cts.Dispose()}
    # This is a normal, single top-level navigation in the user's dedicated
    # existing browser tab; do not replay/modify any cookies or tokens.
    $msg=@{id=121;method='Page.navigate';params=@{url='https://www.cardmarket.com/'}}|ConvertTo-Json -Compress -Depth 5
    $bytes=[Text.Encoding]::UTF8.GetBytes($msg)
    $ws.SendAsync([ArraySegment[byte]]::new($bytes),[Net.WebSockets.WebSocketMessageType]::Text,$true,[Threading.CancellationToken]::None).GetAwaiter().GetResult()|Out-Null
    $accepted=$false
    $deadline=[DateTime]::UtcNow.AddSeconds(8)
    while([DateTime]::UtcNow -lt $deadline){
      $frameBytes=New-Object byte[] 65536
      $wait=[Threading.CancellationTokenSource]::new(2500)
      try{
        $frame=$ws.ReceiveAsync([ArraySegment[byte]]::new($frameBytes),$wait.Token).GetAwaiter().GetResult()
      }catch{break}finally{$wait.Dispose()}
      if(!$frame.EndOfMessage){continue}
      $response=[Text.Encoding]::UTF8.GetString($frameBytes,0,$frame.Count)|ConvertFrom-Json
      if($response.id -ne 121){continue}
      if($response.error -or $response.result.errorText){break}
      if($response.result.frameId){$accepted=$true}
      break
    }
    if($accepted){
      Start-Sleep -Seconds 6
      $result.action='NORMAL_HOMEPAGE_NAVIGATION'
      $result.warmupSeconds=6
      $result.status='READY_FOR_HEALTH_CHECK'
    } else {
      $result.status='NAVIGATION_UNVERIFIED'
    }
  }
} catch {
  $result.status='BROWSER_UNAVAILABLE'
} finally {
  if($ws){try{$ws.Dispose()}catch{}}
}
$result|ConvertTo-Json -Compress -Depth 3
