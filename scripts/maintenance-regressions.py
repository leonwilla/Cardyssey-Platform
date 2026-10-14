#!/usr/bin/env python3
"""Run offline matching regressions; report all failures without hiding earlier errors."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parent
names=["test-price-coverage.py","test-price-source-round2.py","test-price-round3.py",
"test-price-round5.py","test-price-round6.py","test-price-round7.py","test-price-round8.py",
"test-price-round9.py","test-price-round11.py","test-price-round12.py","test-price-round13.py",
"test-price-round15.py","test-price-round16.py","test-pokewallet-client.py","test-pokewallet-prices.py",
"test-missing-price-batch-gate.py","test-supplemental-catalog.py","test-cardtrader-ko-art.py"]
failed=[]
for name in names:
    print("RUN "+name,flush=True)
    try:
        result=subprocess.run([sys.executable,str(ROOT/name)],cwd=ROOT.parent,timeout=120)
        if result.returncode:
            failed.append(name)
    except subprocess.TimeoutExpired:
        failed.append(name+" (timeout)")
print("FAILED: "+", ".join(failed) if failed else "ALL OFFLINE REGRESSIONS PASSED",flush=True)
raise SystemExit(bool(failed))
