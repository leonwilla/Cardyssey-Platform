from PIL import Image
from pathlib import Path
import urllib.request,json,os,collections

ROOT=Path("/tmp/cardyssey-match")
CACHE=Path("/tmp/cardtrader-ja-split")
CACHE.mkdir(parents=True,exist_ok=True)
MAP=Path("/home/tv/cardshop/scripts/zhtw-art-identities.json")
OUT=Path("/home/tv/cardshop/scripts/zhtw-source-blueprints.json")
TOKEN=""
for line in Path("/home/tv/cardshop/platform/.env").read_text().splitlines():
    if line.startswith("CARDTRADER_API_TOKEN="):
        TOKEN=line.split("=",1)[1].strip(); break
H={"Authorization":"Bearer "+TOKEN,"Accept":"application/json","User-Agent":"Cardyssey-ja-split-source"}

def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30) as r:return json.load(r)

def ahash(path,crop):
    try:
        im=Image.open(path).convert("L")
        w,h=im.size;x1,y1,x2,y2=crop
        im=im.crop((int(w*x1),int(h*y1),int(w*x2),int(h*y2))).resize((24,24))
        px=list(im.getdata());avg=sum(px)/len(px);bits=0
        for v in px:bits=(bits<<1)|(v>=avg)
        return bits
    except Exception:return None

CROPS=((.08,.15,.92,.56),(.04,.04,.96,.96),(.12,.18,.88,.52))
def sig(path):return tuple(ahash(path,c) for c in CROPS)
def dist(a,b):return sum((x^y).bit_count() for x,y in zip(a,b) if x is not None and y is not None)

identities=json.loads(MAP.read_text())
wanted={x["source_card_id"]:x["source_set"] for x in identities if x.get("source_set") in ("SA","SCS")}
print("split_sources",len(wanted),collections.Counter(wanted.values()),flush=True)

# Find the local Japanese source image path.
import subprocess
def db(sql):
    return subprocess.run(["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],capture_output=True,text=True,check=True).stdout.strip()
source_paths={}
if wanted:
    vals=",".join("'"+x.replace("'","''")+"'" for x in wanted)
    raw=db(f"SELECT card_id,image_local_path FROM catalog_cards_mirror WHERE language_code='ja' AND card_id IN ({vals})")
    for line in raw.splitlines():
        if "\t" in line:
            cid,path=line.split("\t",1);source_paths[cid]=path

groups={
    "SA":[3974,3975,3998,4075,4076],
    "SCS":[3822,4656],
}
bp=[]
for source_set,eids in groups.items():
    for eid in eids:
        bps=get(f"https://api.cardtrader.com/api/v2/blueprints/export?expansion_id={eid}")
        print("split_blueprints",source_set,eid,len(bps),flush=True)
        for i,b in enumerate(bps,1):
            url=b.get("image_url")
            if not url:continue
            p=CACHE/f"{eid}-{b['id']}.png"
            if not p.exists():
                try:
                    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Cardyssey-ja-split-source"}),timeout=20) as r:
                        p.write_bytes(r.read())
                except Exception:
                    continue
            bp.append((source_set,eid,int(b["id"]),str(b.get("name") or ""),str(b.get("version") or ""),sig(p)))

by_set=collections.defaultdict(list)
for row in bp:by_set[row[0]].append(row)

out={}
for i,(cid,source_set) in enumerate(sorted(wanted.items()),1):
    path=source_paths.get(cid)
    if not path:continue
    s=sig(ROOT/path)
    ranked=sorted(((dist(s,r[5]),r) for r in by_set[source_set]),key=lambda x:(x[0],x[1][2]))[:3]
    if len(ranked)<2:continue
    d1,best=ranked[0];margin=ranked[1][0]-d1
    if d1<=90 and margin>=35:
        out[cid]={"expansion_id":best[1],"blueprint_id":best[2],"distance":d1,"margin":margin,"name":best[3],"version":best[4]}
    if i%20==0 or i==len(wanted):
        print("split_match",i,"/",len(wanted),"matched",len(out),flush=True)

OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("split_mapped",len(out),"of",len(wanted),flush=True)
print("split_by_source",dict(collections.Counter(wanted[cid] for cid in out)),flush=True)
for cid,v in list(out.items())[:15]:print("sample",cid,v,flush=True)
