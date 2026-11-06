#!/usr/bin/env python3
"""Live DB integration smoke test for the separate Cardmarket review table.

Creates a uniquely named synthetic review row only; always deletes it.
"""
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).parent
CARD_ID="cardmarket-review-smoke-test-20261106"

def sql(statement):
    p=subprocess.run(["docker","exec","cardyssey-db","psql","-X","-v","ON_ERROR_STOP=1",
         "-U","cardyssey","-d","cardyssey","-At","-c",statement],
         capture_output=True,text=True,check=True)
    return p.stdout.strip()
def cli(payload):
    return subprocess.run([sys.executable,str(ROOT/"cardmarket-print-review-admin.py"),
         "--action","review"],input=json.dumps(payload),capture_output=True,text=True)
def main():
    sql(f"DELETE FROM cardmarket_print_identity_review WHERE card_id='{CARD_ID}'")
    try:
        sql(f"""INSERT INTO cardmarket_print_identity_review
           (language_code,card_id,variant_id,set_id,classification,candidate_ids,matched_set_ids)
           VALUES ('de','{CARD_ID}','v-test','s-test','TEST',
                   '["1234","9876"]'::jsonb,'["1234"]'::jsonb)""")
        base={"language":"de","cardId":CARD_ID,"variantId":"v-test",
              "status":"CONFIRMED_PRINT","exactPrintConfirmed":True,"note":"test"}
        invalid=cli({**base,"productId":"9876"})
        assert invalid.returncode==2 and "not matched" in invalid.stdout, invalid.stdout
        count=sql(f"SELECT status FROM cardmarket_print_identity_review WHERE card_id='{CARD_ID}'")
        assert count=="PENDING_REVIEW",count
        valid=cli({**base,"productId":"1234"})
        assert valid.returncode==0,valid.stdout
        state=sql(f"SELECT status||':'||selected_product_id FROM cardmarket_print_identity_review WHERE card_id='{CARD_ID}'")
        assert state=="CONFIRMED_PRINT:1234",state
        route=sql(f"SELECT verification_state||':'||provider_product_id FROM price_source_routing WHERE card_id='{CARD_ID}'")
        assert route=="VERIFIED_PRODUCT_ID:1234",route
        print("PASS: wrong ID rejected; correct ID confirmed in review + verified routing; no price write.")
    finally:
        sql(f"DELETE FROM price_source_routing WHERE card_id='{CARD_ID}'")
        sql(f"DELETE FROM cardmarket_print_identity_review WHERE card_id='{CARD_ID}'")
if __name__=="__main__":
    main()
