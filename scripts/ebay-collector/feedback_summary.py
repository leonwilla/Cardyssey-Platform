#!/usr/bin/env python3
"""Reviewed eBay correction examples grouped by decision (no auto model training).

Use the saved title/ID to create reproducible parser tests and verify that
proposed matching improvements help multiple cards before deployment.
"""
import json
from price_history import db

def summary():
    raw=db("SELECT decision,count(*) FROM ebay_listing_feedback GROUP BY decision ORDER BY count(*) DESC,decision")
    return {'categories':{line.split('|')[0]:int(line.split('|')[1]) for line in raw.splitlines() if '|' in line},
            'process':'review examples -> general rule -> regression test -> deploy; no automatic price edits'}

if __name__=='__main__':print(json.dumps(summary(),ensure_ascii=False))
