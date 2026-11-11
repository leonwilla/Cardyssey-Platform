# Shared comment grammar: config/cardmarket-comment-rules.json copied beside
# this script on Tiny. Neither a bare MB/PB abbreviation nor an empty seller
# comment proves a physical print; it remains a review/price diagnostic hint.
$rulePath=Join-Path $PSScriptRoot 'cardmarket-comment-rules.json'
if(!(Test-Path $rulePath)){throw 'CARDMARKET_COMMENT_RULES_MISSING'}
try {
  $script:cmCommentRules=Get-Content -Raw -Encoding UTF8 $rulePath | ConvertFrom-Json
  if([int]$script:cmCommentRules.schema -ne 1 -or
     [string]$script:cmCommentRules.source -ne 'CARDYSSEY_DIAGNOSTIC_ONLY'){
    throw 'INVALID_COMMENT_RULES_SCHEMA'
  }
} catch {throw 'CARDMARKET_COMMENT_RULES_INVALID'}
function Get-CardmarketOfferCommentClassification {
 param([string]$Comment,[string]$TargetPrint)
 $text=[string]$Comment
 $target=[string]$TargetPrint
 if([string]::IsNullOrWhiteSpace($text)){return 'MISSING'}
 if($text -match [string]$script:cmCommentRules.negation){return 'AMBIGUOUS'}
 $mb=($text -match [string]$script:cmCommentRules.explicit.masterball)
 $pb=($text -match [string]$script:cmCommentRules.explicit.pokeball)
 $mbShort=($text -match [string]$script:cmCommentRules.shorthand.masterball)
 $pbShort=($text -match [string]$script:cmCommentRules.shorthand.pokeball)
 if($target -eq 'masterball'){
   if($pb -or $pbShort){return 'CONTRADICTION'}
   if($mb){return 'POSITIVE'}
   if($mbShort){return 'SHORTHAND_HINT'}
   return 'MISSING'
 }
 if($target -eq 'pokeball'){
   if($mb -or $mbShort){return 'CONTRADICTION'}
   if($pb){return 'POSITIVE'}
   if($pbShort){return 'SHORTHAND_HINT'}
   return 'MISSING'
 }
 if($target -like 'stamp:*'){
   $stamp=$target.Substring(6)
   $pattern=$script:cmCommentRules.stamps.PSObject.Properties[$stamp]
   if($pattern -and $text -match [string]$pattern.Value -and
      $text -notmatch '(?i)\b(?:no|not|kein(?:e|en|er|es)?|ohne|nicht|wrong|falsch)\b'){
     return 'POSITIVE'
   }
   return 'MISSING'
 }
 return 'NOT_APPLICABLE'
}
