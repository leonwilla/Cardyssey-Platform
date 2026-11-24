#!/usr/bin/env python3
"""Recompute each historic eBay quote with an expanding rolling median.

Idempotent; no eBay requests. Safe to run daily after new history is imported.
"""
import json
from price_history import choose_median, ensure_history_table, stored_sales
from price_history import db, sql


def due_variants():
    """Only revisit changed sale histories or a crossed rolling-window boundary.

    A sale leaves a 30-day window on day 31, 90-day window on day 91,
    etc. The next wider window is recalculated only when needed.
    """
    return db('''
SELECT DISTINCT h.card_id,h.language_code,h.variant_id
FROM ebay_sold_history h
LEFT JOIN ebay_price_cache p ON p.card_id=h.card_id
 AND p.language_code=h.language_code AND p.variant_id=h.variant_id
WHERE h.condition_label='NEAR_MINT'
AND (p.source IS NULL OR p.source='CARDYSSEY_EBAY')
AND (
 p.updated_at IS NULL OR h.first_collected_at > p.updated_at
 OR EXISTS (
   SELECT 1 FROM unnest(ARRAY[31,61,91,184,366]) AS b(days)
   WHERE h.sold_on+b.days > p.updated_at::date
     AND h.sold_on+b.days <= CURRENT_DATE
 )
 OR EXISTS (
   SELECT 1 FROM generate_series(2,
      GREATEST(2,(CURRENT_DATE-h.sold_on)/365+1)) AS yrs(years)
   WHERE h.sold_on+(365*yrs.years+1) > p.updated_at::date
     AND h.sold_on+(365*yrs.years+1) <= CURRENT_DATE
 )
)
ORDER BY 1,2,3''')


def refresh_all():
    ensure_history_table()
    listing=due_variants()
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
