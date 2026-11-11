# Canonical, first-party Cardmarket offer-filter URLs. Never assume that
# query parameters alone prove filtering; the caller must validate the DOM.
if(!(Get-Command Get-CardmarketGameProfile -ErrorAction SilentlyContinue)){
 $gameModule=Join-Path $PSScriptRoot 'cardmarket-game-profile.ps1'
 if(!(Test-Path $gameModule)){throw 'CARDMARKET_GAME_PROFILE_MODULE_MISSING'}
 . $gameModule
}
function New-CardmarketOfferFilterUrl {
 param([string]$ProductUrl,[ValidateSet(1,3)][int]$LanguageId,
       [ValidateSet('Y','N','0')][string]$ReverseCode='0',
       [ValidateSet('Y','N','0')][string]$FirstEditionCode='0')
 $game=Get-CardmarketGameProfile
 $gamePath=[string]$game.game_path
 $u=$null
 try{$u=[uri]$ProductUrl}catch{throw 'INVALID_FILTER_BASE_URL'}
 if(!$u -or $u.Scheme -ne 'https' -or $u.Host -ne 'www.cardmarket.com' -or
    $u.AbsolutePath -notmatch ('^/(de|en)/'+$gamePath+'/Products/Singles/[A-Za-z0-9-]+/[A-Za-z0-9-]+$')){
    throw 'INVALID_FILTER_BASE_URL'
 }
 $country=if($LanguageId -eq 3){'de'}else{'en'}
 if($u.AbsolutePath -notmatch ('^/'+$country+'/'+$gamePath+'/')){throw 'FILTER_LANGUAGE_PATH_MISMATCH'}
 $q='language='+$LanguageId+'&minCondition=2&isSigned=N&isAltered=N'
 if($ReverseCode -ne '0'){$q+='&isReverseHolo='+$ReverseCode}
 if($FirstEditionCode -ne '0'){$q+='&isFirstEd='+$FirstEditionCode}
 return $u.GetLeftPart([UriPartial]::Path)+'?'+$q
}
