# Fast Cardmarket read-only review using same-origin Chrome fetch.
# One browser network request per known product URL, not Selenium navigation.
param(
 [string]$InputJson = "C:\Users\TV\AppData\Local\Cardyssey\CardmarketCollector\ten-products.json",
 [string]$OutputDir = "C:\Users\TV\AppData\Local\Cardyssey\CardmarketCollector\fast-http",
 [int]$MaxCases = 10,
 [int]$DelaySeconds = 0
)
$ErrorActionPreference="Stop"
if($MaxCases -lt 1 -or $MaxCases -gt 1000){throw "MaxCases out of range"}
if($DelaySeconds -lt 0){throw "DelaySeconds must be nonnegative"}
New-Item -ItemType Directory -Path $OutputDir -Force|Out-Null
$log=Join-Path $OutputDir "observations.jsonl"
$state=Join-Path $OutputDir "progress.json"
$cases=@(Get-Content $InputJson -Raw -Encoding UTF8|ConvertFrom-Json)
$done=@{}
if(Test-Path $log){
  Get-Content $log | ForEach-Object {
    try{$r=$_|ConvertFrom-Json;if($r.card -and $r.http -eq 200){$done[[string]$r.card]=$true}}catch{}
  }
}
$tabs=@(Invoke-RestMethod -TimeoutSec 5 "http://127.0.0.1:9222/json/list")
$tab=@($tabs|Where-Object { $_.type -eq "page" -and $_.url -like "https://www.cardmarket.com/*" })[0]
if($tab -is [array]){$tab=$tab[0]}
if(!$tab){throw "Open the existing Cardmarket Chrome tab first"}
$ws=[Net.WebSockets.ClientWebSocket]::new()
$ws.Options.SetRequestHeader("Origin","http://localhost")
$ws.ConnectAsync([uri]$tab.webSocketDebuggerUrl,[threading.cancellationtoken]::None).GetAwaiter().GetResult()|Out-Null
$id=0
function Browser-Js([string]$expression){
 $script:id++
 $payload=@{id=$script:id;method="Runtime.evaluate";params=@{expression=$expression;returnByValue=$true;awaitPromise=$true}}|ConvertTo-Json -Depth 10 -Compress
 $bytes=[text.encoding]::UTF8.GetBytes($payload)
 $cts=[threading.CancellationTokenSource]::new([TimeSpan]::FromSeconds(20))
 try{$ws.SendAsync([ArraySegment[byte]]::new($bytes),[Net.WebSockets.WebSocketMessageType]::Text,$true,$cts.Token).GetAwaiter().GetResult()|Out-Null}finally{$cts.Dispose()}
 $buf=[byte[]]::new(262144)
 for($i=0;$i -lt 40;$i++){
  $cts=[threading.CancellationTokenSource]::new([TimeSpan]::FromSeconds(20))
  try{$res=$ws.ReceiveAsync([ArraySegment[byte]]::new($buf),$cts.Token).GetAwaiter().GetResult()}finally{$cts.Dispose()}
  if($res.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close){throw "CDP_CLOSE"}
  if(!$res.EndOfMessage){throw "CDP_FRAGMENT_TOO_LARGE"}
  $reply=([text.encoding]::UTF8.GetString($buf,0,$res.Count)|ConvertFrom-Json)
  if($reply.id -ne $script:id){continue}
  if($reply.error -or $reply.result.exceptionDetails){throw "CDP_RUNTIME_ERROR"}
  return $reply.result.result.value
 }
 throw "CDP_RESPONSE_TIMEOUT"
}
function Save-State([string]$status,[string]$card) {
 $x=@{status=$status;last_card=$card;checked=$done.Count;total=[Math]::Min($MaxCases,$cases.Count);updated_at=[datetime]::UtcNow.ToString("o")}
 $x|ConvertTo-Json -Compress|Set-Content -Path $state -Encoding UTF8
}
$stopped=$false
try {
 foreach($item in ($cases|Select-Object -First $MaxCases)){
  $card=[string]$item.card_id
  if($done.ContainsKey($card)){continue}
  $uri=[uri][string]$item.url
  if($uri.Scheme -ne "https" -or $uri.Host -ne "www.cardmarket.com" -or !$uri.AbsolutePath.StartsWith("/de/Pokemon/Products/Singles/")){throw "Invalid Cardmarket URL"}
  $path=$uri.AbsolutePath+"?language=3&minCondition=2&isSigned=N&isAltered=N"
  $pathJs=ConvertTo-Json -InputObject $path -Compress
  $expectedJs=ConvertTo-Json -InputObject ([string]$item.expected_product_id) -Compress
  $cardJs=ConvertTo-Json -InputObject $card -Compress
  $expr=@'
(async()=>{
 const started=performance.now();
 const response=await fetch(__PATH__,{credentials:"include"});
 const body=await response.text();
 const documentBody=new DOMParser().parseFromString(body,"text/html");
 const productId=documentBody.querySelector('input[name="idProduct"]')?.value||null;
 const rows=[...documentBody.querySelectorAll(".article-row")];
 const filtered=documentBody.querySelector('input[name="language[3]"]')?.checked===true
   &&documentBody.querySelector('[name="minCondition"]')?.value==="2";
 const prices=[];
 for(const row of rows){
   const condition=row.querySelector(".article-condition")?.getAttribute("title")
    ||row.querySelector(".article-condition")?.getAttribute("data-bs-original-title")||"";
   const tag=row.querySelector(".price-container")?.textContent||"";
   const match=tag.match(/([0-9][0-9.,]*)\s*\u20ac/);
   if((condition==="Near Mint"||condition==="Mint")&&match){
     const value=Number(match[1].replaceAll(".","").replace(",","."));
     if(Number.isFinite(value)&&value>0)prices.push(value);
   }
 }
 prices.sort((a,b)=>a-b);
 const mid=Math.floor(prices.length/2);
 const median=prices.length?(prices.length%2?prices[mid]:(prices[mid-1]+prices[mid])/2):null;
 return JSON.stringify({
   card:__CARD__,expected_product_id:__EXPECTED__,product_id:productId,
   http:response.status,mitigation:response.headers.get("cf-mitigated"),
   elapsed_ms:Math.round(performance.now()-started),filtered,
   product_matches:productId===__EXPECTED__,rows:rows.length,accepted:prices.length,
   more_offers_possible:!!documentBody.querySelector("#loadMoreButton"),
   sample_median_eur:median,price_status:"FIRST_PAGE_ASKING_SAMPLE_UNVERIFIED",
   production_price_changed:false
 });
})()
'@
  $expr=$expr.Replace("__PATH__",$pathJs).Replace("__EXPECTED__",$expectedJs).Replace("__CARD__",$cardJs)
  try{
   $out=(Browser-Js $expr)|ConvertFrom-Json
   ($out|ConvertTo-Json -Depth 8 -Compress)|Add-Content -Path $log -Encoding UTF8
   if($out.http -in @(403,429,503) -or $out.mitigation -eq "challenge"){
    Save-State "BLOCKED" $card;$stopped=$true;break
   }
   if($out.http -ne 200){Save-State "HTTP_ERROR" $card;$stopped=$true;break}
   $done[$card]=$true
   Save-State "RUNNING" $card
  }catch{
   Save-State "CONNECTION_LOST" $card
   $stopped=$true
   break
  }
  if($DelaySeconds -gt 0){Start-Sleep -Seconds $DelaySeconds}
 }
 if(!$stopped){Save-State "FINISHED_SAMPLE_ONLY" ""}
} finally {$ws.Dispose()}
