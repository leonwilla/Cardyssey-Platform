#!/usr/bin/env python3
"""Recompute each historic eBay quote with an expanding rolling median.

Idempotent; no eBay requests. Safe to run daily after new history is imported.
"""
import json
from price_history import choose_median, ensure_history_table, stored_sales
from price_history import db, sql


def refresh_all():
    ensure_history_table()
    listing=db("SELECT card_id,language_code,variant_id FROM ebay_sold_history WHERE condition_label='NEAR_MINT' GROUP BY card_id,language_code,variant_id ORDER BY card_id,variant_id")
    updated=0
    for line in listing.splitlines():
        parts=line.split('|')
        if len(parts)!=3:
            continue
        card,language,variant=parts
        calc=choose_median(stored_sales(card,variant,language=language))
        if not calc:
            continue
        recent=[dict(itemId=x['item_id'],title=x['title'],soldPriceEur=float(x['sold_eur']),
                     rawCondition='Near Mint (angenommen)' if x.get('condition_assumed') else 'Near Mint (Titel)',
                     endedAt=str(x['sold_on'])[:10]+'T00:00:00Z',url=x['url']) for x in calc['recent_sales']]
        # API uses MINT base and applies 0.92 on Near Mint. Avoid double-discounting.
        values=','.join(str(round(float(calc[key])/0.92,4)) for key in ('median_eur','min_eur','max_eur'))
        query=("INSERT INTO ebay_price_cache(card_id,language_code,variant_id,source,base_eur,range_low_eur,range_high_eur,sample_count,recent_sales,price_window_days,price_window_label,low_sample,updated_at) VALUES ("+
          ','.join([sql(card),sql(language),sql(variant),sql('CARDYSSEY_EBAY'),values,str(calc['sample_count']),sql(json.dumps(recent,ensure_ascii=False))+'::jsonb',str(calc['window_days']),sql(calc['window_label']),'TRUE' if calc['low_sample'] else 'FALSE','NOW()'])+
          ") ON CONFLICT(card_id,language_code,variant_id) DO UPDATE SET base_eur=EXCLUDED.base_eur,range_low_eur=EXCLUDED.range_low_eur,range_high_eur=EXCLUDED.range_high_eur,sample_count=EXCLUDED.sample_count,recent_sales=EXCLUDED.recent_sales,price_window_days=EXCLUDED.price_window_days,price_window_label=EXCLUDED.price_window_label,low_sample=EXCLUDED.low_sample,updated_at=NOW() WHERE ebay_price_cache.source='CARDYSSEY_EBAY';")
        db(query)
        updated+=1
    print(json.dumps({'repriced':updated}))

if __name__=='__main__':
    refresh_all()
