# Shared validated Cardmarket game profile, copied to the Windows collector folder.
function Get-CardmarketGameProfile {
 param([string]$ProfileName='pokemon')
 $source=Join-Path $PSScriptRoot 'cardmarket-game-profile.json'
 if(!(Test-Path $source)){throw 'CARDMARKET_GAME_PROFILE_MISSING'}
 try{$data=Get-Content -Raw -Encoding UTF8 $source|ConvertFrom-Json}catch{throw 'CARDMARKET_GAME_PROFILE_BAD_JSON'}
 if([int]$data.schema -ne 1){throw 'CARDMARKET_GAME_PROFILE_SCHEMA'}
 $profile=$data.profiles.PSObject.Properties[$ProfileName]
 if(!$profile){throw 'CARDMARKET_GAME_PROFILE_UNKNOWN'}
 $p=$profile.Value
 if([int]$p.game_id -lt 1 -or [int]$p.game_id -gt 10000 -or
     [string]$p.game_path -notmatch '^[A-Za-z]{3,28}$' -or
     [string]$p.catalog_filename -ne ('products_singles_'+[int]$p.game_id+'.json') -or
     [string]$p.price_guide_filename -ne ('price_guide_'+[int]$p.game_id+'.json') -or
     [string]$p.base_url -ne 'https://www.cardmarket.com' -or
     [string]$p.feed_base_url -ne 'https://downloads.s3.cardmarket.com/productCatalog'){
   throw 'CARDMARKET_GAME_PROFILE_INVALID'
 }
 # Explicit allowlist: other games require verified card/set identities first.
 if($ProfileName -ne 'pokemon' -or [int]$p.game_id -ne 6 -or
    [string]$p.game_path -ne 'Pokemon'){throw 'GAME_PIPELINE_NOT_VERIFIED'}
 return $p
}
