#!/usr/bin/env python3
"""t7_s1_derive_krw.py — pre-derives every planned KRW market's 60m series (open, close, volume, KRW turnover) from the raw pages into
/Users/haosiyu/cc_tmp/krw_pull/derived_s1 via t7_s1_common.derive_krw (body sha verified per page). No returns; no network."""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_s1_common as C
PLAN = C.plan(); t0 = time.time(); n = 0; bars = 0
for v in ("upbit", "bithumb"):
    for m in PLAN["krw"][v]:
        d = C.derive_krw(v, m["market"]); n += 1; bars += len(d["open_s"])
print(json.dumps({"markets": n, "bars": int(bars), "elapsed_s": round(time.time() - t0, 1)}))
