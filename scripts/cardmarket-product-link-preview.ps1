# Safely inspect a single explicitly supplied Cardmarket product URL in a
# separate tab of the existing Edge profile. Never touches the scanner tab.
param([Parameter(Mandatory=$true)][string]$ProductUrl,[int]$CdpPort=9223)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$ErrorActionPreference='Stop'
$u=[uri]$ProductUrl
if($u.Scheme -ne 'https' -or $u.Host -ne 'www.cardmarket.com' -or
   ($u.AbsolutePath -notmatch '^/(de|en)/Pokemon/Products/Singles/' -and
    $u.AbsolutePath -ne '/Pokemon/Products')){throw 'NOT_A_CARDMARKET_PRODUCT_URL'}
$target=$null
$ws=$null
try {
  $newUrl='http://127.0.0.1:'+ $CdpPort +'/json/new?'+[uri]::EscapeDataString($ProductUrl)
  $target=Invoke-RestMethod -Method Put -Uri $newUrl -TimeoutSec 6
  if(!$target.webSocketDebuggerUrl){throw 'BROWSER_TAB_UNAVAILABLE'}
  $ws=[Net.WebSockets.ClientWebSocket]::new()
  $ws.Options.SetRequestHeader('Origin','http://localhost')
  $ws.ConnectAsync([uri]$target.webSocketDebuggerUrl,[Threading.CancellationToken]::None).GetAwaiter().GetResult()|Out-Null
  $js='JSON.stringify({url:location.href,title:document.title,blocked:/(nur einen moment|just a moment|attention required|checking your browser|captcha|access denied)/i.test(document.title),id:document.querySelector("input[name=idProduct]")?.value||"",heading:document.querySelector("h1")?.innerText?.trim()||"",crumbs:[...document.querySelectorAll("nav[aria-label*=breadcrumb] a,ol.breadcrumb a,.breadcrumb a")].map(e=>e.innerText.trim()).filter(Boolean).slice(-7),body:(document.body?.innerText||"").slice(0,2000),picture:document.querySelector(".product-page img,.product-image img,#product-image img")?.src||""})'
  $result=$null
  for($round=0;$round -lt 22;$round++){
    Start-Sleep -Milliseconds 650
    $id=100+$round
    $msg=@{id=$id;method='Runtime.evaluate';params=@{expression=$js;returnByValue=$true}}|ConvertTo-Json -Depth 6 -Compress
    $bytes=[Text.Encoding]::UTF8.GetBytes($msg)
    $ws.SendAsync([ArraySegment[byte]]::new($bytes),[Net.WebSockets.WebSocketMessageType]::Text,$true,[Threading.CancellationToken]::None).GetAwaiter().GetResult()|Out-Null
    $deadline=[DateTime]::UtcNow.AddSeconds(3)
    while([DateTime]::UtcNow -lt $deadline){
      $buf=New-Object byte[] 262144
      $s=[Threading.CancellationTokenSource]::new([Math]::Max(200,[int]($deadline-[DateTime]::UtcNow).TotalMilliseconds))
      try {$r=$ws.ReceiveAsync([ArraySegment[byte]]::new($buf),$s.Token).GetAwaiter().GetResult()}catch{break}finally{$s.Dispose()}
      if($r.Count -le 0){continue}
      $packet=[Text.Encoding]::UTF8.GetString($buf,0,$r.Count)|ConvertFrom-Json
      if($packet.id -ne $id){continue}
      if($packet.result.result.value){$result=$packet.result.result.value|ConvertFrom-Json}
      break
    }
    if($result -and $result.blocked){throw 'CARDMARKET_PROVIDER_CHALLENGE'}
    if($result -and $result.id -match '^[0-9]{3,12}$' -and $result.url -match '^https://www[.]cardmarket[.]com/(de|en)/Pokemon/Products/Singles/') {break}
  }
  if(!$result -or $result.id -notmatch '^[0-9]{3,12}$' -or $result.url -notmatch '^https://www[.]cardmarket[.]com/(de|en)/Pokemon/Products/Singles/'){
    throw 'PRODUCT_ID_NOT_VISIBLE_IN_BROWSER'
  }
  $result|ConvertTo-Json -Compress -Depth 5
} finally {
  if($ws){try{$ws.Dispose()}catch{}}
  if($target.id){try{Invoke-RestMethod -Method Get -Uri ('http://127.0.0.1:'+ $CdpPort +'/json/close/'+ $target.id) -TimeoutSec 4|Out-Null}catch{}}
}
