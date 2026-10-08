#!/usr/bin/env python3
import subprocess

sql="""
UPDATE tcg_price_cache
SET resolution_status='NO_PRICE',
    failure_detail='Market availability window reached; retrying public providers',
    next_attempt_at=NOW()
WHERE resolution_status='NO_PUBLIC_PRICE'
  AND next_attempt_at IS NOT NULL
  AND next_attempt_at<=NOW();
"""
subprocess.run(
    ["docker","exec","-i","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-v","ON_ERROR_STOP=1","-q"],
    input=sql,text=True,check=True,
)
print("reactivated_pending_market_prices",flush=True)
