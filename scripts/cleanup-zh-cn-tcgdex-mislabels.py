#!/usr/bin/env python3
"""Remove mislabeled Taiwan/traditional rows from the zh-cn mirror.

TCGdex currently exposes several SV sets under zh-cn that are byte-for-byte
catalog identities of its zh-tw rows (same set, local number and Traditional
Chinese name). This cleanup is deliberately fail-closed: it deletes only rows
that have an exact zh-tw twin and refuses to run if any unexpected zh-cn
non-CSMPiC row does not match one.
"""
import argparse
import subprocess

def db(sql: str) -> str:
    return subprocess.run(
        ["docker","exec","cardyssey-db","psql","-U","cardyssey","-d","cardyssey","-At","-F","\t","-c",sql],
        check=True,capture_output=True,text=True
    ).stdout.strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()

    total=int(db("""SELECT count(*) FROM catalog_cards_mirror
                    WHERE language_code='zh-cn' AND set_id<>'CSMPiC'""") or "0")
    exact=int(db("""SELECT count(*) FROM catalog_cards_mirror c
                    WHERE c.language_code='zh-cn' AND c.set_id<>'CSMPiC'
                      AND EXISTS (
                        SELECT 1 FROM catalog_cards_mirror t
                        WHERE t.language_code='zh-tw'
                          AND t.set_id=c.set_id
                          AND t.local_id=c.local_id
                          AND t.name=c.name
                      )""") or "0")
    stale_prices=int(db("""SELECT count(*)
                           FROM tcg_price_cache p
                           LEFT JOIN catalog_cards_mirror c
                             ON c.language_code='zh-cn' AND c.card_id=p.card_id
                           WHERE p.language_code='zh-cn'
                             AND c.card_id IS NULL""") or "0")
    stale_with_tw=int(db("""SELECT count(*)
                            FROM tcg_price_cache p
                            LEFT JOIN catalog_cards_mirror c
                              ON c.language_code='zh-cn' AND c.card_id=p.card_id
                            WHERE p.language_code='zh-cn'
                              AND c.card_id IS NULL
                              AND EXISTS (
                                SELECT 1 FROM catalog_cards_mirror t
                                WHERE t.language_code='zh-tw'
                                  AND t.card_id=p.card_id
                              )""") or "0")

    print(
        f"mislabeled_candidates={total} exact_zh_tw_twins={exact} "
        f"stale_price_rows={stale_prices} stale_price_twins={stale_with_tw} "
        f"applied={args.apply}"
    )
    if total != exact:
        raise SystemExit("refusing cleanup: not every catalog candidate has an exact zh-tw twin")
    if stale_prices != stale_with_tw:
        raise SystemExit("refusing cleanup: not every stale zh-cn price has a zh-tw twin")
    if not args.apply:
        return

    deleted=[]
    if total:
        deleted=db("""DELETE FROM catalog_cards_mirror c
                      WHERE c.language_code='zh-cn'
                        AND c.set_id<>'CSMPiC'
                        AND EXISTS (
                          SELECT 1 FROM catalog_cards_mirror t
                          WHERE t.language_code='zh-tw'
                            AND t.set_id=c.set_id
                            AND t.local_id=c.local_id
                            AND t.name=c.name
                        )
                      RETURNING c.card_id;""").splitlines()
        if len(deleted) != total:
            raise SystemExit(f"cleanup mismatch: expected {total}, deleted {len(deleted)}")

    stale_history=int(db("""SELECT count(*)
                            FROM tcg_price_history h
                            WHERE h.language_code='zh-cn'
                              AND NOT EXISTS (
                                SELECT 1 FROM catalog_cards_mirror c
                                WHERE c.language_code='zh-cn'
                                  AND c.card_id=h.card_id
                              )
                              AND EXISTS (
                                SELECT 1 FROM catalog_cards_mirror t
                                WHERE t.language_code='zh-tw'
                                  AND t.card_id=h.card_id
                              )""") or "0")

    db("""DELETE FROM tcg_price_history h
          WHERE h.language_code='zh-cn'
            AND NOT EXISTS (
              SELECT 1 FROM catalog_cards_mirror c
              WHERE c.language_code='zh-cn'
                AND c.card_id=h.card_id
            )
            AND EXISTS (
              SELECT 1 FROM catalog_cards_mirror t
              WHERE t.language_code='zh-tw'
                AND t.card_id=h.card_id
            );""")
    db("""DELETE FROM tcg_price_cache p
          WHERE p.language_code='zh-cn'
            AND NOT EXISTS (
              SELECT 1 FROM catalog_cards_mirror c
              WHERE c.language_code='zh-cn'
                AND c.card_id=p.card_id
            )
            AND EXISTS (
              SELECT 1 FROM catalog_cards_mirror t
              WHERE t.language_code='zh-tw'
                AND t.card_id=p.card_id
            );""")
    print(
        f"deleted_catalog_rows={len(deleted)} "
        f"deleted_price_rows={stale_prices} "
        f"deleted_history_rows={stale_history}"
    )

if __name__=="__main__":
    main()
