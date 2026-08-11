"""Hyperliquid archive — daily incremental pull of 1h klines + funding + roster snapshot.

WHY THIS IS TIME-SENSITIVE: HL's candleSnapshot endpoint is capped at 5000 rows/coin, i.e. a
ROLLING ~210-day window of hourly bars. Every day not archived is a day of history permanently
lost for any future HL backtest. fundingHistory reaches back ~1171d (2023-05-11) and is not at
immediate risk, but is backfilled here once for completeness.

Also snapshots metaAndAssetCtxs daily -> from now on we accumulate a POINT-IN-TIME roster
(listing/delisting dates, 24h volume, OI, funding), which removes the roster-survivorship caveat
for all future work without any bisecting.

READ-ONLY public /info endpoint. Short timeout + retries (the path from this host stalls ~30s on a
minority of calls; a long timeout turns a 15-minute job into a 6-hour one). Resumable: state is
written per coin, so an interrupted backfill continues where it stopped.

Layout under exports/hl_archive/:
    klines/<COIN>.npz    t,o,h,l,c,v,n          (hourly, dedup+sorted)
    funding/<COIN>.npz   time,fundingRate,premium
    roster/<YYYYMMDD>.json                       daily metaAndAssetCtxs snapshot
    _state.json                                  last-seen timestamps

Usage:
    python engine/hl_archive/pull_daily.py            # incremental (cron)
    python engine/hl_archive/pull_daily.py --backfill # first run: deep funding backfill too
"""
import argparse, json, os, time
import urllib.request
import numpy as np

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
ARC = MA + "/exports/hl_archive"
URL = "https://api.hyperliquid.xyz/info"
UA = "Mozilla/5.0 (research archive; read-only public market data)"
PAUSE = 0.9          # ~60 req/min: HL /info budget is 1200 weight/min, these calls weigh 20
TIMEOUT = 8
HOUR = 3600_000
DAY = 86400_000
CANDLE_MAX_BACK_D = 205      # stay inside the 5000-row cap
FUNDING_PAGE_H = 480         # <= the 500-row response cap
FUNDING_BACKFILL_D = 1180    # API floor is ~1171d


def post(payload, retries=5):
    for k in range(retries):
        try:
            req = urllib.request.Request(URL, data=json.dumps(payload).encode(), method="POST",
                                         headers={"User-Agent": UA,
                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                out = json.loads(r.read())
            time.sleep(PAUSE)
            return out
        except Exception:
            time.sleep(0.7 * (k + 1))
    return None


def _merge(path, new, key_col=0):
    """append + dedup on key_col + sort; returns (n_total, n_added)."""
    if new is None or len(new) == 0:
        if os.path.exists(path):
            return len(np.load(path)["a"]), 0
        return 0, 0
    new = np.asarray(new, float)
    if os.path.exists(path):
        old = np.load(path)["a"]
        allr = np.vstack([old, new])
    else:
        old = np.empty((0, new.shape[1]))
        allr = new
    _, idx = np.unique(allr[:, key_col], return_index=True)
    merged = allr[np.sort(idx)]
    merged = merged[np.argsort(merged[:, key_col])]
    np.savez_compressed(path, a=merged.astype(np.float64))
    return len(merged), len(merged) - len(old)


def pull_klines(coin, since_ms, now):
    lo = max(since_ms, now - CANDLE_MAX_BACK_D * DAY)
    j = post({"type": "candleSnapshot",
              "req": {"coin": coin, "interval": "1h", "startTime": int(lo), "endTime": int(now)}})
    if not isinstance(j, list) or not j:
        return None
    return [[float(r["t"]), float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"]),
             float(r["v"]), float(r["n"])] for r in j]


def pull_funding(coin, since_ms, now):
    acc, cur = [], since_ms
    guard = 0
    while cur < now and guard < 400:
        guard += 1
        j = post({"type": "fundingHistory", "coin": coin, "startTime": int(cur),
                  "endTime": int(min(cur + FUNDING_PAGE_H * HOUR, now))})
        if isinstance(j, list) and j:
            acc += [[float(r["time"]), float(r["fundingRate"]),
                     float(r["premium"]) if r.get("premium") not in (None, "") else np.nan]
                    for r in j]
            nt = int(j[-1]["time"]) + HOUR
            cur = nt if nt > cur else cur + FUNDING_PAGE_H * HOUR
        else:
            cur += FUNDING_PAGE_H * HOUR
    return acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true",
                    help="deep funding backfill (~1171d); default is incremental from last seen")
    ap.add_argument("--max_seconds", type=int, default=0, help="0 = unlimited")
    a = ap.parse_args()
    t0 = time.time()
    for d in ("klines", "funding", "roster"):
        os.makedirs(f"{ARC}/{d}", exist_ok=True)
    spath = ARC + "/_state.json"
    state = json.load(open(spath)) if os.path.exists(spath) else {"klines": {}, "funding": {}}
    state.setdefault("klines", {}); state.setdefault("funding", {})

    now = int(time.time() * 1000)
    mc = post({"type": "metaAndAssetCtxs"})
    if not mc:
        print("[hl_archive] FATAL: metaAndAssetCtxs unreachable", flush=True)
        return 1
    uni, ctx = mc[0]["universe"], mc[1]
    stamp = time.strftime("%Y%m%d", time.gmtime(now / 1000))
    roster = {"pulled_at_ms": now, "markets": [
        {"name": u["name"], "isDelisted": u.get("isDelisted", False),
         "maxLeverage": u.get("maxLeverage"), "szDecimals": u.get("szDecimals"),
         "dayNtlVlm": c.get("dayNtlVlm"), "openInterest": c.get("openInterest"),
         "funding": c.get("funding"), "midPx": c.get("midPx"), "markPx": c.get("markPx"),
         "oraclePx": c.get("oraclePx"), "premium": c.get("premium"),
         "impactPxs": c.get("impactPxs")}
        for u, c in zip(uni, ctx)]}
    json.dump(roster, open(f"{ARC}/roster/{stamp}.json", "w"))
    coins = [u["name"] for u in uni if not u.get("isDelisted", False)]
    print(f"[hl_archive] {stamp}: {len(coins)} active perps (roster snapshot saved)", flush=True)

    nk_add = nf_add = 0
    for i, c in enumerate(coins):
        if a.max_seconds and (time.time() - t0) > a.max_seconds:
            print("[hl_archive] time budget reached; state saved, resume next run", flush=True)
            break
        safe = c.replace("/", "_")
        # ---- klines ----
        since = int(state["klines"].get(c, now - CANDLE_MAX_BACK_D * DAY))
        rows = pull_klines(c, since - 2 * HOUR, now)          # small overlap so no bar is missed
        n, added = _merge(f"{ARC}/klines/{safe}.npz", rows)
        if rows:
            state["klines"][c] = int(max(r[0] for r in rows))
        nk_add += added
        # ---- funding ----
        # --backfill must ignore the last-seen watermark: the watermark only records how far
        # FORWARD we have pulled, so resuming from it would never fill the deep history behind it.
        # Re-pulling the full range is safe (_merge dedups) and this is a one-time job.
        if a.backfill:
            fsince = now - FUNDING_BACKFILL_D * DAY
        else:
            fsince = state["funding"].get(c)
            if fsince is None:
                fsince = now - 3 * DAY
        frows = pull_funding(c, int(fsince) - HOUR, now)
        fn, fadded = _merge(f"{ARC}/funding/{safe}.npz", frows)
        if frows:
            state["funding"][c] = int(max(r[0] for r in frows))
        nf_add += fadded
        json.dump(state, open(spath, "w"))                     # resumable after every coin
        if (i + 1) % 20 == 0 or i == len(coins) - 1:
            print(f"  [{i+1}/{len(coins)}] {c}: klines {n} (+{added}) funding {fn} (+{fadded}) "
                  f"({time.time()-t0:.0f}s)", flush=True)
    print(f"[hl_archive] done: +{nk_add} kline rows, +{nf_add} funding rows "
          f"({time.time()-t0:.0f}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
