# Conservative candidate ranking. A score cannot confirm a physical print,
# language-specific price, or product ID. Caller must verify the actual page.

function Resolve-CardmarketSearchCandidates {
 param(
   [object[]]$Links,
   [string]$PrintedNumber,
   [string]$SetSlug = '',
   [string]$Name = '',
   [string]$Stamp = '',
   [string]$Foil = '',
   [string]$PrintType = '',
   [string[]]$AllowedProductIds = @()
 )
 $ranked=[Collections.Generic.List[object]]::new()
 $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
 $expected=$PrintedNumber.Trim()
 foreach($link in @($Links)){
   $uri=$null
   try{$uri=[uri]([string]$link.url)}catch{continue}
   if(!$uri -or $uri.Scheme -ne 'https' -or $uri.Host -ne 'www.cardmarket.com') {continue}
   if($uri.AbsolutePath -notmatch '^/(de|en)/Pokemon/Products/Singles/([A-Za-z0-9-]+)/([A-Za-z0-9-]+)$'){continue}
   $actualSet=[string]$Matches[2];$productSlug=[string]$Matches[3]
   $path=$uri.GetLeftPart([UriPartial]::Path)
   if(!$seen.Add($path)){continue}
   # A verified expansion guard is a hard requirement, not a score bonus.
   if($SetSlug -and $actualSet -cne $SetSlug){continue}
   # The final collector token is the ONLY part allowed to satisfy the
   # printed number. A title like '113' never matches collector #13.
   $tail=[regex]::Match($productSlug,'(?i)(?:^|-)([A-Za-z]{0,12})([0-9]{1,4})$')
   if(!$tail.Success){continue}
   $num=[string]$tail.Groups[2].Value
   if($expected -match '^\d{1,4}$'){
     if([int]$expected -ne [int]$num){continue}
   } elseif($expected -match '^[A-Za-z]{1,12}0*[0-9]{1,4}$'){
     # Promo-style printed identifiers e.g. DP05 or SVP099.
     $expectedCode=$expected.ToUpperInvariant().TrimStart()
     if(($tail.Groups[1].Value+$num).ToUpperInvariant() -cne $expectedCode){continue}
   } else {continue}
   $title=[string]$link.text
   $searchText=($title+' '+$productSlug).ToLowerInvariant()
   $score=100
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
      printedNumber=$num;score=$score;productSlug=$productSlug})
 }
 $ordered=@($ranked | Sort-Object @{Expression='score';Descending=$true}, @{Expression='url';Descending=$false})
 $winner=$null
 $reason='NO_NUMBER_MATCH'
 if($ordered.Count -gt 0) {
   if(!$SetSlug){$reason='SET_NOT_INDEPENDENTLY_VERIFIED'}
   elseif($ordered.Count -eq 1){$winner=$ordered[0];$reason='UNIQUE_SET_NUMBER_PAGE_CANDIDATE'}
   elseif([int]$ordered[0].score -ge [int]$ordered[1].score+10){
     # Even a large score gap is only a candidate to inspect, NOT print proof.
     $winner=$ordered[0];$reason='HIGHER_SCORING_SET_NUMBER_PAGE_CANDIDATE'
   }else{$reason='MULTIPLE_SAME_SET_NUMBER_CANDIDATES'}
 }
 return [pscustomobject]@{
    candidates=$ordered;uniquePageCandidate=$winner;reason=$reason;
    candidateCount=$ordered.Count;exactPrintVerified=$false;priceVerified=$false
 }
}
