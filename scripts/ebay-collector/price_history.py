"""Persistent eBay sold-sale history and expanding-window market-price selection.

Stores sold item observations separately from the current price cache. The current
price is a median, never an average or an unsold asking price.
"""
import json
import statistics
import subprocess
from datetime import date

def sql(value):
    return "'" + str(value).replace("'", "''") + "'"


def db(query):
    proc=subprocess.run(['docker','exec','-i','cardyssey-db','psql','-X',
        '-v','ON_ERROR_STOP=1','-U','cardyssey','-d','cardyssey','-At'],
        input=query,text=True,capture_output=True,check=True,timeout=25)
    return proc.stdout.strip()


DDL = '''
CREATE TABLE IF NOT EXISTS ebay_sold_history (
 card_id text NOT NULL,
 language_code varchar(16) NOT NULL,
 variant_id text NOT NULL,
 ebay_item_id text NOT NULL,
 sold_on date NOT NULL,
 sold_eur numeric(12,4) NOT NULL CHECK (sold_eur > 0),
 condition_label text NOT NULL,
 condition_assumed boolean NOT NULL DEFAULT false,
 variant_assumed boolean NOT NULL DEFAULT false,
 title text NOT NULL,
 listing_url text NOT NULL,
 image_url text,
 identity_basis text NOT NULL,
 first_collected_at timestamptz NOT NULL DEFAULT now(),
 last_collected_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY (card_id,language_code,variant_id,ebay_item_id)
);
CREATE INDEX IF NOT EXISTS ebay_sold_history_timeline_idx
 ON ebay_sold_history(card_id,language_code,variant_id,sold_on DESC);
ALTER TABLE ebay_price_cache ADD COLUMN IF NOT EXISTS price_window_days INTEGER NOT NULL DEFAULT 30;
ALTER TABLE ebay_price_cache ADD COLUMN IF NOT EXISTS price_window_label TEXT NOT NULL DEFAULT '30 Tage';
ALTER TABLE ebay_price_cache ADD COLUMN IF NOT EXISTS low_sample BOOLEAN NOT NULL DEFAULT FALSE;
'''


def windows_for(earliest, today):
    """30, 90, 6 months, 1 year, then each additional year, to oldest sale."""
    windows = [(30, '30 Tage'), (90, '90 Tage'), (183, '6 Monate'), (365, '1 Jahr')]
    age = max(0, (today - earliest).days)
    years = 2
    while windows[-1][0] < age:
        windows.append((365 * years, f'{years} Jahre'))
        years += 1
    return windows


def choose_median(sales, today=None, desired_samples=3):
    """Prefer a recent statistically useful window; retain even one sale as fallback."""
    today = today or date.today()
    valid = [(date.fromisoformat(str(s['sold_on'])[:10]), float(s['sold_eur']), s)
             for s in sales if float(s.get('sold_eur', 0)) > 0]
    valid = [(day, amount, source) for day, amount, source in valid if day <= today]
    if not valid:
        return None
    # If no window reaches three, use all history (even one sale).
    selected = None
    for days, label in windows_for(min(day for day, _, _ in valid), today):
        matches = [s for day, _, s in valid if (today - day).days <= days]
        if len(matches) >= desired_samples:
            selected = (days, label, matches)
            break
    if selected is None:
        # Even if no window reaches three sales, do not label a recent lone
        # sale as "1 Jahr": select the *shortest* window containing the most
        # observed sold items, with low_sample clearly flagged.
        fallback=[]
        for days, label in windows_for(min(day for day, _, _ in valid), today):
            matches=[source for day, _, source in valid if (today-day).days <= days]
            if matches:fallback.append((days,label,matches))
        selected=max(fallback,key=lambda x:(len(x[2]),-x[0]))
    days, label, matches = selected
    amounts = [float(s['sold_eur']) for s in matches]
    return dict(window_days=days,window_label=label,sample_count=len(matches),
                median_eur=round(statistics.median(amounts),4),
                min_eur=min(amounts),max_eur=max(amounts),
                low_sample=len(matches)<desired_samples,
                recent_sales=sorted(matches,key=lambda s:str(s['sold_on']),reverse=True)[:10])


def ensure_history_table():
    db(DDL)


def save_sales(card_id, variant_id, rows, *, language='de'):
    """Idempotently upsert dated, verified sold observations. Don't discard old sales."""
    if not rows:
        return 0
    ensure_history_table()
    saved = []
    for r in rows:
        saved.append(dict(item_id=str(r['item_id']),date=r['sold_date'],
            price=float(r['price_eur']),condition=r.get('history_condition','NEAR_MINT'),
            condition_assumed=bool(r.get('condition_assumed')),
            variant_assumed=bool(r.get('variant_assumed')),
            title=str(r['title']),url=r['url'],image_url=r.get('image_url'),
            basis='image_and_title' if r.get('image_identity_verified') else 'title_and_number'))
    query = '''INSERT INTO ebay_sold_history
      (card_id,language_code,variant_id,ebay_item_id,sold_on,sold_eur,
       condition_label,condition_assumed,variant_assumed,title,listing_url,image_url,identity_basis)
      SELECT ''' + sql(card_id) + ',' + sql(language) + ',' + sql(variant_id) + ''',
      s.item_id,s.sold_on::date,s.price,s.condition,s.condition_assumed,
      s.variant_assumed,s.title,s.url,s.image_url,s.basis
      FROM jsonb_to_recordset(''' + sql(json.dumps([dict(item_id=r['item_id'],sold_on=r['date'],price=r['price'],condition=r['condition'],condition_assumed=r['condition_assumed'],variant_assumed=r['variant_assumed'],title=r['title'],url=r['url'],image_url=r['image_url'],basis=r['basis']) for r in saved],ensure_ascii=False)) + '''::jsonb)
      AS s(item_id text,sold_on text,price numeric,condition text,condition_assumed boolean,
           variant_assumed boolean,title text,url text,image_url text,basis text)
      ON CONFLICT(card_id,language_code,variant_id,ebay_item_id) DO UPDATE SET
        last_collected_at=now(),title=EXCLUDED.title,
        image_url=COALESCE(EXCLUDED.image_url,ebay_sold_history.image_url);
      '''
    db(query)
    return len(saved)


def stored_sales(card_id,variant_id,*,language='de'):
    ensure_history_table()
    result=db('''SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'item_id',ebay_item_id,'sold_on',sold_on,'sold_eur',sold_eur,
      'title',title,'url',listing_url,'condition',condition_label,
      'condition_assumed',condition_assumed,'variant_assumed',variant_assumed)
       ORDER BY sold_on DESC),'[]') FROM ebay_sold_history
       WHERE card_id='''+sql(card_id)+' AND language_code='+sql(language)+
       ' AND variant_id='+sql(variant_id)+" AND condition_label='NEAR_MINT';")
    return json.loads(result)
