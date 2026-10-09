#!/usr/bin/env python3
"""Repair the former blanket NO_PUBLIC_PRICE classification; dry-run by default.

No search can establish that a card has no price anywhere on the public web.
Only the three messages emitted by the old blanket finalizer are reopened.
Explicit manual deferrals (for example unreleased promos) remain untouched.
"""
import argparse
import subprocess

LEGACY_REASONS = (
    'NO_PUBLIC_PRICE: exact variant identity verified; full Cardmarket/CardTrader/TCGCSV/public-retailer pass found no usable exact market price',
    'NO_PUBLIC_PRICE: card identity verified but no exact variant-specific public market price after full provider/web pass',
    'NO_PUBLIC_PRICE: no exact provider identity or supported public-retailer match after full provider/web pass',
)
REASONS_SQL = ','.join("'" + value.replace("'", "''") + "'" for value in LEGACY_REASONS)
PREDICATE = """resolution_status='NO_PUBLIC_PRICE'
AND language_code IN ('de','en','ja','ko','zh-cn','zh-tw')
AND failure_detail IN (""" + REASONS_SQL + ')'
REPAIR_SQL = """WITH changed AS (
UPDATE tcg_price_cache
SET resolution_status='NO_PRICE',
 failure_detail='Search incomplete: previous blanket NO_PUBLIC_PRICE classification reopened; verify exact identity and provider coverage. Previous diagnostic: ' || failure_detail,
 next_attempt_at=NOW()+INTERVAL '7 days'
WHERE """ + PREDICATE + """
RETURNING language_code
) SELECT language_code,COUNT(*) FROM changed GROUP BY language_code ORDER BY language_code;
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    sql = REPAIR_SQL if args.apply else (
        'SELECT language_code,COUNT(*) FROM tcg_price_cache WHERE ' + PREDICATE
        + ' GROUP BY language_code ORDER BY language_code;'
    )
    result = subprocess.run(
        ['docker','exec','-i','cardyssey-db','psql','-U','cardyssey','-d','cardyssey',
         '-X','-qAt','-v','ON_ERROR_STOP=1'],
        input="BEGIN; SET LOCAL statement_timeout='20s';\n" + sql + '\nCOMMIT;',
        text=True,capture_output=True,check=True,timeout=30,
    )
    print(('reopened' if args.apply else 'would_reopen') + '\n' + result.stdout.strip())


if __name__ == '__main__':
    main()
