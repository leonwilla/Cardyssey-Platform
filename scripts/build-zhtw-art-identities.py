from PIL import Image
import subprocess,os,json,collections
ROOT="/tmp/cardyssey-match"
ZHSETS=('SC1a','SC1b','SCC','SC1D','SCD','SC2D','SCB','SC2a','SC2b','SCA')
JASETS=('S1H','S1W','S1a','S2','S2a','S3','S3a','S4','S4a')
def db(sql):
 return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],capture_output=True,text=True,check=True).stdout.strip()
def getrows(sql):
 out=[]
 for line in db(sql).splitlines():
  z=line.split("\t",5)
  if len(z)==6: out.append(z)
 return out
zh=getrows("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,c.image_local_path
FROM tcg_price_cache p JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='zh-tw' AND p.resolution_status='NO_PRICE' AND p.legacy_variant='NORMAL'
AND c.set_id IN ('SC1a','SC1b','SCC','SC1D','SCD','SC2D','SCB','SC2a','SC2b','SCA')
AND v.value->>'id'=p.variant_id
AND NOT COALESCE(v.value ? 'foil',false) OR TRUE
ORDER BY c.set_id,c.local_id""")
# reject special variants in Python via a clean query instead
zh=getrows("""SELECT c.card_id,c.set_id,c.local_id,c.name,p.variant_id,c.image_local_path
FROM tcg_price_cache p JOIN catalog_cards_mirror c ON c.card_id=p.card_id AND c.language_code=p.language_code
CROSS JOIN LATERAL jsonb_array_elements(c.variants) v(value)
WHERE p.language_code='zh-tw' AND p.resolution_status='NO_PRICE' AND p.legacy_variant='NORMAL'
AND c.set_id IN ('SC1a','SC1b','SCC','SC1D','SCD','SC2D','SCB','SC2a','SC2b','SCA')
AND v.value->>'id'=p.variant_id
AND COALESCE(v.value->>'foil','')='' AND COALESCE(v.value->>'subtype','')=''
AND COALESCE(jsonb_array_length(COALESCE(v.value->'stamps','[]'::jsonb)),0)=0
AND LOWER(COALESCE(v.value->>'size','standard'))='standard'
AND c.image_local_path IS NOT NULL
ORDER BY c.set_id,c.local_id""")
ja=getrows("""SELECT card_id,set_id,local_id,name,'',image_local_path
FROM catalog_cards_mirror WHERE language_code='ja'
AND set_id IN ('S1H','S1W','S1a','S2','S2a','S3','S3a','S4','S4a','S5I','S5R','S5a','S6H','S6K','S6a','S7D','S7R','S8','SA','SC','SC2','SCS','SD','SEF','SEK','SGG','SGI','SP1','SP2','SP3','SP4','SP5','SP6','SPD','SPZ')
AND image_local_path IS NOT NULL ORDER BY set_id,local_id""")
def ahash(path,crop):
 try:
  im=Image.open(os.path.join(ROOT,path)).convert("L")
  w,h=im.size; x1,y1,x2,y2=crop
  im=im.crop((int(w*x1),int(h*y1),int(w*x2),int(h*y2))).resize((24,24))
  px=list(im.getdata()); avg=sum(px)/len(px); bits=0
  for v in px:bits=(bits<<1)|(v>=avg)
  return bits
 except:return None
crops=((.08,.15,.92,.56),(.04,.04,.96,.96))
def sig(r):return tuple(ahash(r[5],c) for c in crops)
JS=[]
for i,r in enumerate(ja,1):
 JS.append((r,sig(r)))
 if i%200==0 or i==len(ja):
  print("art_source_signature",i,"/",len(ja),flush=True)
def distance(a,b):
 return sum((x^y).bit_count() for x,y in zip(a,b) if x is not None and y is not None)
results=[]
for i,zr in enumerate(zh,1):
 zs=sig(zr)
 ranked=sorted((distance(zs,js),jr) for jr,js in JS)[:2]
 if len(ranked)<2: continue
 d1,jr=ranked[0]
 margin=ranked[1][0]-d1
 results.append((zr,d1,margin,jr))
 if i%200==0 or i==len(zh):
  print("art_identity",i,"/",len(zh),flush=True)

maps=[]
cnt=collections.Counter()
for zr,d1,margin,jr in results:
 if d1<=80 and margin>=50:
  maps.append({"card_id":zr[0],"variant_id":zr[4],"target_set":zr[1],"target_local_id":zr[2],"source_card_id":jr[0],"source_set":jr[1],"source_local_id":jr[2],"distance":d1,"margin":margin})
  cnt[zr[1]]+=1
print("mapped",len(maps),"byset",dict(cnt))
for th in [(60,40),(70,40),(80,40),(80,50),(100,50)]:
 c=sum(1 for _,d1,margin,_ in results if d1<=th[0] and margin>=th[1])
 print("threshold",th,"count",c)
Path="/home/tv/cardshop/scripts/zhtw-art-identities.json"
open(Path,"w").write(json.dumps(maps,ensure_ascii=False,indent=2)+"\n")
print("wrote",Path)
