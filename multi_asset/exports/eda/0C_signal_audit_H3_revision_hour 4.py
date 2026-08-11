#!/usr/bin/env /usr/bin/python3
"""0C signal-side audit — item H, part 3: WHICH bars does the cache get wrong, and why?

H2 found exactly one differing bar per symbol out of 720, and all three sat at 07:00 / 19:00 UTC
— i.e. the bar that had just closed when an anchor (00/04/08/12/16/20 UTC) ran its refresh.
n=3 makes that a hypothesis, not a finding. This widens the sample to 15 symbols over the full
cache and tabulates the UTC hour of every differing bar.

PREDICTION IF THE MECHANISM IS "captured before the venue finished aggregating":
  differing bars cluster on hours {03,07,11,15,19,23} — the last-closed hour at each anchor.
PREDICTION IF IT IS RANDOM VENUE REVISION:
  differing hours are uniform over 0..23.

Read-only, ~30 public requests.
"""
import collections
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
    "~/Desktop/quant_research/multi_asset/exports/eda/0C_signal_audit_H3_revision_hour.json")
ANCHOR_HOURS = {0, 4, 8, 12, 16, 20}
LAST_CLOSED_AT_ANCHOR = {(h - 1) % 24 for h in ANCHOR_HOURS}     # {23,3,7,11,15,19}


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
    preds = json.load(open(os.path.join(LIVE, "state", "preds_latest.json")))
    members = [s for s in preds["symbols"] if s in syms]
    rng = np.random.default_rng(20260729)
    picks = sorted(set(["BTCUSDT", "ETHUSDT"] +
                       list(rng.choice(members, size=13, replace=False))))
    lo, hi = int(kc.ts[0]), int(kc.ts[-1])

    hour_hist = collections.Counter()
    hour_total = collections.Counter()
    rows = []
    for s in picks:
        j = syms.index(s)
        venue = {}
        cursor = lo
        while cursor <= hi:
            got = get("/fapi/v1/klines", symbol=s, interval="1h", startTime=int(cursor),
                      endTime=int(hi), limit=1000)
            if not got:
                break
            for k in got:
                venue[int(k[0])] = k
            nxt = int(got[-1][0]) + 3_600_000
            if nxt <= cursor:
                break
            cursor = nxt
        n_cmp = n_diff = 0
        for i, t in enumerate(kc.ts):
            t = int(t)
            if t not in venue:
                continue
            c = float(kc.data["quote_vol"][i, j])
            cl = float(kc.data["close"][i, j])
            if not np.isfinite(c):
                continue
            n_cmp += 1
            h = time.gmtime(t / 1000).tm_hour
            hour_total[h] += 1
            if c != float(venue[t][7]) or cl != float(venue[t][4]):
                n_diff += 1
                hour_hist[h] += 1
                rows.append({"symbol": s, "ts": t,
                             "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t / 1000)),
                             "utc_hour": h,
                             "in_last_closed_at_anchor_set": h in LAST_CLOSED_AT_ANCHOR,
                             "close_cache": cl, "close_venue": float(venue[t][4]),
                             "close_rel": abs(cl / float(venue[t][4]) - 1),
                             "qvol_rel": abs(c / max(float(venue[t][7]), 1e-12) - 1)})
        print(f"{s:14s} compared {n_cmp:5d}  differing {n_diff}", flush=True)

    n_diff = len(rows)
    n_in = sum(1 for r in rows if r["in_last_closed_at_anchor_set"])
    # what fraction of ALL compared bars sit on those six hours (the null expectation)
    tot = sum(hour_total.values())
    base_rate = sum(v for h, v in hour_total.items() if h in LAST_CLOSED_AT_ANCHOR) / max(tot, 1)
    res = {"symbols_checked": picks, "cache_span_utc":
           [time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(lo / 1000)),
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(hi / 1000))],
           "bars_compared_total": tot,
           "bars_differing_total": n_diff,
           "differ_rate": round(n_diff / max(tot, 1), 8),
           "hypothesis": "bars are captured seconds after close, before the venue has finished "
                         "aggregating them; the append-only cache then freezes the provisional "
                         "value forever",
           "last_closed_at_anchor_hours_utc": sorted(LAST_CLOSED_AT_ANCHOR),
           "differing_bars_on_those_hours": n_in,
           "share_of_differing_on_those_hours": round(n_in / max(n_diff, 1), 4),
           "null_share_if_uniform": round(base_rate, 4),
           "hour_histogram_of_differing_bars": dict(sorted(hour_hist.items())),
           "max_close_rel_error": (max(r["close_rel"] for r in rows) if rows else 0.0),
           "rows": rows}
    res["verdict"] = (
        "MECHANISM CONFIRMED — differing bars sit overwhelmingly on the hour that had just closed "
        "when an anchor refreshed" if n_diff and (n_in / n_diff) > 2 * base_rate else
        "NOT CONFIRMED on this sample — differing bars are not concentrated on the anchor hours")
    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1, default=str))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
