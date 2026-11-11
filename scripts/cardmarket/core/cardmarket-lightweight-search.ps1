# Same-origin search request in the already authenticated Cardmarket tab.
# The server response is parsed as inert HTML; scripts are not executed.
# If Cardmarket renders results dynamically, safely fall back to the
# existing full-page flow. Any challenge response halts the collector.
if(!(Get-Command Get-CardmarketGameProfile -ErrorAction SilentlyContinue)){
 $gameModule=Join-Path $PSScriptRoot 'cardmarket-game-profile.ps1'
 if(!(Test-Path $gameModule)){throw 'CARDMARKET_GAME_PROFILE_MODULE_MISSING'}
 . $gameModule
}
function Search-CardmarketSameOrigin {
 param([string]$SearchPath,[bool]$Authenticated=$false)
 if(!$Authenticated){return $null}
 $gamePath=[string](Get-CardmarketGameProfile).game_path
 if($SearchPath -notmatch ('^/(de|en)/'+$gamePath+'/Products/Search[?]searchString=[^#]+$')){return $null}
 $origin=[string](Js 'location.origin' 6)
 if($origin -ne 'https://www.cardmarket.com'){return $null}
 Wait-CardmarketRequestBudget
 $pathJson=ConvertTo-Json -InputObject $SearchPath -Compress
 $expr=@"
(async () => {
  const route=$pathJson;
  const abort=new AbortController();
  const timer=setTimeout(()=>abort.abort(),13000);
  try {
    const response=await fetch(route,{
      credentials:"same-origin",signal:abort.signal,
      headers:{"Accept":"text/html"}
    });
    const final=new URL(response.url);
    if(final.origin!==location.origin){
      return JSON.stringify({status:0,error:"REDIRECT_OTHER_ORIGIN",links:[]});
    }
    const html=await response.text();
    const doc=new DOMParser().parseFromString(html,"text/html");
    const preview=(doc.title+" "+(doc.body?.textContent||"").slice(0,1800));
    const blocked=/(?:nur einen moment|just a moment|attention required|checking your browser|captcha|robot check|access denied|zugriff verweigert|you have been blocked|too many requests|error 1020)/i.test(preview);
    const hrefs=[...doc.querySelectorAll('a[href*="/Products/Singles/"]')]
      .map(a=>({text:(a.textContent||"").trim().slice(0,140),
                url:new URL(a.getAttribute("href"),final.href).href}))
      .filter(x=>x.text&&x.url.startsWith("https://www.cardmarket.com/"));
    const signedIn=!!doc.querySelector('a[href*="User_Logout"],form[action*="User_Logout"]');
    return JSON.stringify({status:response.status,blocked,
      signedIn,links:hrefs.slice(0,150),finalPath:final.pathname});
  } catch(e){
    return JSON.stringify({status:0,error:e.name==="AbortError"?"TIMEOUT":"REQUEST_FAILED",links:[]});
  } finally {clearTimeout(timer)}
})()
"@
 $reply=Js $expr 18 | ConvertFrom-Json
 if($reply.blocked -or [int]$reply.status -in @(403,429,503)){
   throw 'CARDMARKET_PROVIDER_CHALLENGE'
 }
 if([int]$reply.status -ne 200 -or !$reply.signedIn){return $null}
 if([string]$reply.finalPath -notmatch ('^/(de|en)/'+$gamePath+'/Products/Search$')){return $null}
 $links=@($reply.links | Where-Object {
    [string]$_.url -match ('^https://www[.]cardmarket[.]com/(de|en)/'+$gamePath+'/Products/Singles/')
 })
 if($links.Count -eq 0){return $null}
 return [pscustomobject]@{links=$links;mode='SAME_ORIGIN_HTML_SEARCH_CANDIDATES'}
}
