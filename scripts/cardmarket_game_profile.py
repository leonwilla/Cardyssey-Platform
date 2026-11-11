#!/usr/bin/env python3
"""Validated configuration for Cardmarket game-specific public feed endpoints.

Pokémon is the ONLY supported runtime. Future TCG profiles must supply their
own verified set/card/variant identities; changing a path is not sufficient.
"""
from __future__ import annotations
from pathlib import Path
import json,re

ROOT=Path(__file__).resolve().parent.parent
DEFAULT_PROFILE=ROOT/'config/cardmarket-game-profile.json'
def load_game_profile(path=DEFAULT_PROFILE,name=None):
    data=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if data.get("schema")!=1:raise ValueError("unsupported game profile schema")
    profiles=data.get("profiles")
    if not isinstance(profiles,dict):raise ValueError("missing profiles")
    key=name or data.get("default_profile")
    if not isinstance(key,str) or key not in profiles:raise ValueError("unknown game profile")
    item=profiles[key]
    ident=item.get("game_id")
    game=item.get("game_path")
    catalog=item.get("catalog_filename")
    guide=item.get("price_guide_filename")
    if not isinstance(ident,int) or ident<1 or ident>10000:raise ValueError("invalid game id")
    if not isinstance(game,str) or not re.fullmatch("[A-Za-z]{3,28}",game):raise ValueError("invalid game path")
    if catalog!=f"products_singles_{ident}.json" or guide!=f"price_guide_{ident}.json":
        raise ValueError("game file names do not match game id")
    if item.get("base_url")!="https://www.cardmarket.com" or item.get("feed_base_url")!="https://downloads.s3.cardmarket.com/productCatalog":
        raise ValueError("untrusted game profile host")
    return {"name":key,"game_id":ident,"game_path":game,
       "url_path":"/"+game+"/","product_url":f"https://downloads.s3.cardmarket.com/productCatalog/productList/{catalog}",
       "price_url":f"https://downloads.s3.cardmarket.com/productCatalog/priceGuide/{guide}"}
if __name__=="__main__":
    print(json.dumps(load_game_profile(),ensure_ascii=False))
