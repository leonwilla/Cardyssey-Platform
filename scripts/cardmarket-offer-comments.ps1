# Cardmarket seller remarks are diagnostic evidence, not an automatic print ID.
# In particular an absent comment does not mean Pokeball for Japanese reverse.
function Get-CardmarketOfferCommentClassification {
 param([string]$Comment,[string]$TargetPrint)
 $text=[string]$Comment
 $target=[string]$TargetPrint
 if([string]::IsNullOrWhiteSpace($text)){return 'MISSING'}
 $mb=($text -match '(?i)(?<!\w)(?:master\s*ball|meister\s*ball|masterball|meisterball)(?!\w)')
 $pb=($text -match '(?i)(?<!\w)(?:pok[eé]\s*ball|pok[eé]ball)(?!\w)')
 $no=($text -match '(?i)\b(?:no|not|kein(?:e|en|er|es)?|ohne|non|nicht|sin|sans)\s+(?:(?:a|ein|eine|an)\s+)?(?:master\s*ball|meister\s*ball|masterball|pok[eé]\s*ball|pok[eé]ball)')
 if($no){return 'AMBIGUOUS'}
 if($target -eq 'masterball'){
   if($pb){return 'CONTRADICTION'}
   if($mb){return 'POSITIVE'}
   return 'MISSING'
 }
 if($target -eq 'pokeball'){
   if($mb){return 'CONTRADICTION'}
   if($pb){return 'POSITIVE'}
   return 'MISSING'
 }
 if($target -like 'stamp:*'){
   $stamp=$target.Substring(6)
   switch($stamp){
     'prerelease' {$ok=($text -match '(?i)\b(?:prerelease|pre.release)\b')}
     'professor-program' {$ok=($text -match '(?i)\b(?:professor.?s?\s+program(?:me)?|professorenprogramm)\b')}
     'play-pokemon' {$ok=($text -match '(?i)\bplay!?\s*pok[eé]mon\b')}
     'cosmos' {$ok=($text -match '(?i)\bcosmos\b')}
     default {$ok=$false}
   }
   if($ok){return 'POSITIVE'}
   return 'MISSING'
 }
 return 'NOT_APPLICABLE'
}
