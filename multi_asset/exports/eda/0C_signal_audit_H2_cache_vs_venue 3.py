#!/usr/bin/env /usr/bin/python3
"""0C signal-side audit — item H, part 2: does the APPEND-ONLY cache still equal the venue?

H part 1 reconciled the shipped factors and found funding_ema exact to 0.0 but dvol30 off by
~1e-7 relative. Attribution: recomputing dvol30 FROM THE CACHE reproduces the shipped number to
1.1e-16, so the residual is not arithmetic — the CACHED BARS DIFFER FROM WHAT THE VENUE RETURNS
FOR THE SAME HOURS.

That is worth measuring on its own, because the cache is APPEND-ONLY BY DESIGN: `KlineCache.
_fetch_one` resumes from `max(finite ts) + 1h`, so a bar is written once and never revisited. If a
bar is captured before the venue has finished aggregating it, the wrong value is permanent.

This bar-by-bar diff is the first check of that assumption. Read-only, ~6 requests.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np

LIVE = os.path.expanduser("~/dl_quant_live")
for p in (os.path.join(LIVE, "signal"), os.path.join(LIVE, "vendor")):
    sys.path.insert(0, p)
import live_panel as LP        # noqa: E402

BASE = "https://fapi.binance.com"
OUT = os.path.expanduser(
    "~/Desktop/quant_research/multi_asset/exports/eda/0C_signal_audit_H2_cache_vs_venue.json")
FIELDS = {"open": 1, "high": 2, "low": 3, "close": 4, "volume": 5, "quote_vol": 7}


def get(path, **params):
    url = f"{BASE}{path}?" + urllib.parse.urlencode(params)
    for a in range(3):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return json.loads(r.read().decode())
        except Exception:
            if a == 2:
                raise
            time.sleep(1.5 * (a + 1))


def main():
    syms = LP.panel_symbols()
    kc = LP.KlineCache(symbols=syms)
    newest = int(kc.ts[-1])
    res = {"cache_rows": int(len(kc.ts)), "cache_newest_ts_ms": newest,
           "cache_newest_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(newest / 1000)),
           "checked_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "symbols": {}}
    for s in ("BTCUSDT", "1000BONKUSDT", "CHRUSDT"):
        j = syms.index(s)
        lo = int(kc.ts[-720])
        rows = []
        cursor = lo
        while cursor <= newest:
            got = get("/fapi/v1/klines", symbol=s, interval="1h", startTime=int(cursor),
                      endTime=int(newest), limit=1000)
            if not got:
                break
            rows.extend(got)
            nxt = int(got[-1][0]) + 3_600_000
            if nxt <= cursor:
                break
            cursor = nxt
        venue = {int(k[0]): k for k in rows}
        entry = {"bars_compared": 0, "per_field": {}}
        idx = np.where((kc.ts >= lo) & (kc.ts <= newest))[0]
        for fname, col in FIELDS.items():
            diffs, worst = 0, {"ts": None, "cache": None, "venue": None, "rel": 0.0}
            n = 0
            for i in idx:
                t = int(kc.ts[i])
                if t not in venue:
                    continue
                c = float(kc.data[fname][i, j])
                v = float(venue[t][col])
                if not np.isfinite(c):
                    continue
                n += 1
                if c != v:
                    diffs += 1
                    rel = abs(c - v) / max(abs(v), 1e-12)
                    if rel > worst["rel"]:
                        worst = {"ts": t,
                                 "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t / 1000)),
                                 "cache": c, "venue": v, "rel": rel,
                                 "age_h_at_check": round((time.time() * 1000 - t) / 3.6e6, 1)}
            entry["bars_compared"] = n
            entry["per_field"][fname] = {"n_bars_differing": diffs,
                                         "frac_differing": round(diffs / max(n, 1), 6),
                                         "worst": worst}
        res["symbols"][s] = entry

    allq = {s: v["per_field"]["quote_vol"]["n_bars_differing"] for s, v in res["symbols"].items()}
    res["summary"] = {
        "quote_vol_bars_differing": allq,
        "interpretation": (
            "a nonzero count means the append-only cache holds bar values the venue no longer "
            "reports. The cache never re-reads a written bar, so the difference is permanent and "
            "grows monotonically with uptime. Magnitude decides whether it matters: dvol30 is a "
            "720-bar mean, so a handful of revised bars moves it by ~1e-7 relative — immaterial "
            "for the size leg, but it means 'the cache equals the venue' is an ASSUMPTION with no "
            "check behind it, and the same mechanism applied to CLOSE would move momentum "
            "channels directly.")}
    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
