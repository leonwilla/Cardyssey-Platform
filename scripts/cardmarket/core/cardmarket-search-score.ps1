# Conservative candidate ranking. A score cannot confirm a physical print,
# language-specific price, or product ID. Caller must verify the actual page.
if(!(Get-Command Get-CardmarketGameProfile -ErrorAction SilentlyContinue)){
 $gameModule=Join-Path $PSScriptRoot 'cardmarket-game-profile.ps1'
 if(!(Test-Path $gameModule)){throw 'CARDMARKET_GAME_PROFILE_MODULE_MISSING'}
 . $gameModule
}


$stampRulesFile=Join-Path $PSScriptRoot 'cardmarket-stamp-routes.json'
if(!(Test-Path -LiteralPath $stampRulesFile)){
  $stampRulesFile=Join-Path $PSScriptRoot '../../../config/cardmarket-stamp-routes.json'
}
$cardmarketStampRules=Get-Content -Raw -Encoding UTF8 -LiteralPath $stampRulesFile | ConvertFrom-Json

function Get-CardmarketStampRoute {
  param([string]$SetId,[string]$Stamp)
  if(!$Stamp){return ''}
  try {
    $values=if($Stamp.TrimStart().StartsWith('[')){ConvertFrom-Json -InputObject $Stamp}else{$Stamp}
  } catch {return ''}
  $tokens=@($values | ForEach-Object { ([string]$_).Trim().ToLowerInvariant() -replace '[\s_]+','-' })
  $routes=@()
  if('trick-or-trade' -in $tokens -or 'pumpkin-pikachu' -in $tokens){$routes+='TRICK_OR_TRADE'}
  if('professorenprogramm' -in $tokens -or 'professor-program' -in $tokens){$routes+='PROFESSOR_PROGRAM'}
  if($SetId -match '^(?:sv|me)(?:[0-9]|[ep]$)' -and
     ('player-rewards-program' -in $tokens -or 'set-logo' -in $tokens)){$routes+='PRIZE_PACK'}
  if($SetId -match '^(?:base|ecard|ex|dp|pl|hgss|bw)' -and
     @($tokens | Where-Object { $_ -in $cardmarketStampRules.worldChampionshipStamps }).Count -gt 0){
    $routes+='WORLD_CHAMPIONSHIPS'
  }
  if($routes.Count -gt 1){return 'AMBIGUOUS_STAMP_ROUTE'}
  if($routes.Count -eq 1){return $routes[0]}
  return ''
}

function Get-CardmarketSubsetPriority {
  param([string]$Route,[string]$SetId,[string]$SetSlug,[string]$ActualSet,
        [string]$ProductSlug,[string]$PrintedNumber)
  if(!$SetId){return 0}
  $codeProperty=$cardmarketStampRules.setCodes.PSObject.Properties[$SetId]
  if(!$codeProperty -or $PrintedNumber -notmatch '^(?:[A-Za-z]{1,12})?(\d{1,4})$'){return 0}
  $number=[int]$Matches[1]
  $code=[regex]::Escape([string]$codeProperty.Value)
  $prefix=''
  $priority=2
  switch($Route){
    'TRICK_OR_TRADE' {
      if($ActualSet -match '^Trick-or-Trade-20(\d\d)$'){$prefix='BOO'+$Matches[1]+$code}
    }
    'PROFESSOR_PROGRAM' {
      if($ActualSet -eq 'Professor-Program'){$prefix='PPP'+$code}
    }
    'PRIZE_PACK' {
      if($ActualSet -match '^Play-Pokemon-Prize-Pack-Series-[A-Za-z0-9-]+$'){$prefix='PPS\d{1,2}'+$code}
      elseif($SetSlug -and $ActualSet -eq ($SetSlug+'-Additionals')){$prefix='x'+$code;$priority=1}
    }
    'WORLD_CHAMPIONSHIPS' {
      if($ActualSet -match '^WCD-20(\d\d)$'){$prefix='WCD'+$Matches[1]+$code}
    }
  }
  if($prefix -and $ProductSlug -match ('(?:^|-)'+$prefix+'-?(\d{1,4})$') -and [int]$Matches[1] -eq $number){
    return $priority
  }
  return 0
}

function Test-CardmarketVintageSubtype {
  param([string]$SetId,[string]$Subtype)
  if($SetId -notin @('base1','base2','base3')){return $false}
  $token=$Subtype.Trim().ToLowerInvariant() -replace '[\s_]+','-'
  return $token -in @('1999-2000-copyright','copyright-1999-2000','missing-expansion-symbol',
                      'fehlendes-erweiterungssymbol','shadowless','schattenlos')
}

function Test-CardmarketPrintedNumber {
 param([string]$ProductSlug,[string]$PrintedNumber,[string]$SetId)
 $expected=$PrintedNumber.Trim()
 $code=[string]$cardmarketStampRules.setCodes.$SetId
 if($SetId -in @('tk-xy-w','tk-xy-b')){
   $suffix=$SetId.Substring($SetId.Length-1).ToUpperInvariant()
   $wanted=[regex]::Match($expected,'(?i)^(\d{1,4})([WB]?)$')
   $actual=[regex]::Match($ProductSlug,('(?i)-TK7-?(\d{1,4})'+$suffix+'$'))
   return ($wanted.Success -and $actual.Success -and (!$wanted.Groups[2].Value -or
           $wanted.Groups[2].Value -eq $suffix) -and [int]$wanted.Groups[1].Value -eq [int]$actual.Groups[1].Value)
 }
 if($code -match '^MCD\d{2}$'){
   $actual=[regex]::Match($ProductSlug,('(?i)-'+[regex]::Escape($code)+'-?(\d{1,4})$'))
   return ($actual.Success -and $expected -match '^\d{1,4}$' -and [int]$expected -eq [int]$actual.Groups[1].Value)
 }
 $tail=[regex]::Match($ProductSlug,'(?i)(?:^|-)([A-Za-z]{0,12})([0-9]{1,4})$')
 if(!$tail.Success){return $false}
 $num=[string]$tail.Groups[2].Value
 if($expected -match '^\d{1,4}$'){return [int]$expected -eq [int]$num}
 if($expected -match '^[A-Za-z]{1,12}0*[0-9]{1,4}$'){
   if(($tail.Groups[1].Value+$num) -eq $expected){return $true}
   # Subset numbers inside a set-code slug: printed 'H12' on 'Jolteon-V1-SKH12'.
   $sub=[regex]::Match($expected,'^([A-Za-z]{1,12})0*([0-9]{1,4})$')
   return ($tail.Groups[1].Value.Length -gt $sub.Groups[1].Value.Length -and
           $tail.Groups[1].Value.EndsWith($sub.Groups[1].Value,[StringComparison]::OrdinalIgnoreCase) -and
           [int]$sub.Groups[2].Value -eq [int]$num)
 }
 return $false
}

function Resolve-CardmarketSearchCandidates {
 param(
   [object[]]$Links,
   [string]$PrintedNumber,
   [string]$SetSlug = '',
   [string]$Name = '',
   [string]$Stamp = '',
   [string]$Foil = '',
   [string]$PrintType = '',
   [string[]]$AllowedProductIds = @(),
   [string]$SetId = '',
   [string]$Language = '',
   [switch]$PreferBasePage
 )
 $gamePath=[string](Get-CardmarketGameProfile).game_path
 $ranked=[Collections.Generic.List[object]]::new()
 $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
 $expected=$PrintedNumber.Trim()
 $stampRoute=Get-CardmarketStampRoute -SetId $SetId -Stamp $Stamp
 foreach($link in @($Links)){
   $uri=$null
   try{$uri=[uri]([string]$link.url)}catch{continue}
   if(!$uri -or $uri.Scheme -ne 'https' -or $uri.Host -ne 'www.cardmarket.com') {continue}
   if($uri.AbsolutePath -notmatch ('^/(de|en)/'+$gamePath+'/Products/Singles/([A-Za-z0-9-]+)/([A-Za-z0-9-]+)$')){continue}
   if($Language -and [string]$Matches[1] -ne $Language){continue}
   $actualSet=[string]$Matches[2];$productSlug=[string]$Matches[3]
   $path=$uri.GetLeftPart([UriPartial]::Path)
   if(!$seen.Add($path)){continue}
   if($stampRoute){
     $subsetPriority=Get-CardmarketSubsetPriority -Route $stampRoute -SetId $SetId -SetSlug $SetSlug -ActualSet $actualSet -ProductSlug $productSlug -PrintedNumber $expected
     if(!$subsetPriority){continue}
     $ranked.Add([pscustomobject]@{url=$path;text=[string]$link.text;setSlug=$actualSet;
       printedNumber=$expected;score=$subsetPriority;productSlug=$productSlug})
     continue
   }
   # A verified expansion guard is a hard requirement for the main print.
   if($SetSlug -and $actualSet -cne $SetSlug){continue}
   if($PreferBasePage){
     if(!$SetSlug -or $productSlug -match '(?:^|-)V(?:[2-9]|[1-9]\d+)(?:-|$)'){continue}
     $codeProperty=$cardmarketStampRules.setCodes.PSObject.Properties[$SetId]
     if(!$codeProperty -or $productSlug -notmatch ('-'+[regex]::Escape([string]$codeProperty.Value)+'\d{1,4}$')){continue}
   }
   # The final collector token is the ONLY part allowed to satisfy the
   # printed number. A title like '113' never matches collector #13.
   if(!(Test-CardmarketPrintedNumber $productSlug $expected $SetId)){continue}
   $title=[string]$link.text
   $searchText=($title+' '+$productSlug).ToLowerInvariant()
   $score=100
   if($PreferBasePage -and $productSlug -match '(?:^|-)V1(?:-|$)'){$score+=20}
   if($SetSlug){$score+=40}
   if($Stamp.Trim()){
     $stampText=$Stamp -replace '^[\[\]"\s]+|[\[\]"\s]+$',''
     if($stampText -and $searchText.Contains($stampText.ToLowerInvariant())){$score+=12}
     # 'Promo' alone does NOT prove a specific stamp.
   } elseif($actualSet -match '(?i)promo' -and !$SetSlug){$score-=3}
   if($Foil.Trim() -and $searchText.Contains($Foil.ToLowerInvariant())){$score+=5}
   if($PrintType -match '(?i)^reverse$'){
     if($searchText.Contains('reverse holo')){$score+=3}
   } elseif($searchText.Contains('reverse holo')){$score-=3}
   if($Name.Trim() -and $title.ToLowerInvariant().Contains($Name.ToLowerInvariant())){$score+=2}
   # V2 and bracketed attack names are NOT evidence of a stamp.
   $ranked.Add([pscustomobject]@{url=$path;text=$title;setSlug=$actualSet;
      printedNumber=$expected;score=$score;productSlug=$productSlug})
 }
 $ordered=@($ranked | Sort-Object @{Expression='score';Descending=$true}, @{Expression='url';Descending=$false})
 $winner=$null
 $reason='NO_NUMBER_MATCH'
 if($stampRoute){
   $reason=if($ordered.Count -gt 0){'SUBSET_PAGE_CANDIDATES_PRINT_UNVERIFIED'}else{'SUBSET_PAGE_NOT_FOUND'}
   if($ordered.Count -eq 1){$winner=$ordered[0]}
 } elseif($ordered.Count -gt 0) {
   if(!$SetSlug){$reason='SET_NOT_INDEPENDENTLY_VERIFIED'}
   elseif($ordered.Count -eq 1){$winner=$ordered[0];$reason='UNIQUE_SET_NUMBER_PAGE_CANDIDATE'}
   elseif([int]$ordered[0].score -ge [int]$ordered[1].score+10){
     # Even a large score gap is only a candidate to inspect, NOT print proof.
     $winner=$ordered[0];$reason='HIGHER_SCORING_SET_NUMBER_PAGE_CANDIDATE'
   }else{$reason='MULTIPLE_SAME_SET_NUMBER_CANDIDATES'}
 }
 return [pscustomobject]@{
    candidates=$ordered;uniquePageCandidate=$winner;reason=$reason;
    candidateCount=$ordered.Count;exactPrintVerified=$false;priceVerified=$false;stampRoute=$stampRoute
 }
}
