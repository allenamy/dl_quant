"""Hyperliquid public market-data pull (READ-ONLY, gentle rate limit).

Discipline: public /info endpoint only. No trading/auth endpoints, no geo-circumvention.

Stage 1 (--stage meta): full perp market list + asset contexts (funding / openInterest /
  dayNtlVlm / midPx) + precise history-depth bisection for 1h candles and fundingHistory.
Stage 2 (--stage hist): 1h candles + funding history for the coins that overlap MEMBER110,
  over the window that overlaps our panel.

Out: exports/eda/hl_meta.json, exports/eda/hl_hist.npz
"""
import json, time, sys, argparse
import urllib.request, urllib.error
import numpy as np

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
URL = "https://api.hyperliquid.xyz/info"
UA = "Mozilla/5.0 (research-data-probe; read-only public market data)"
PAUSE = 0.35            # overridden by --pause; HL /info budget is 1200 weight/min, most
                        # calls weigh 20 -> 60 req/min, so the bulk stage runs at ~1.05s/req
HOUR = 3600_000


def post(payload, retries=3, timeout=25):
    for k in range(retries):
        try:
            req = urllib.request.Request(URL, data=json.dumps(payload).encode(), method="POST",
                                         headers={"User-Agent": UA,
                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read())
            time.sleep(PAUSE)
            return out
        except Exception as e:
            if k == retries - 1:
                print(f"    !! {type(e).__name__}: {str(e)[:120]}", flush=True)
                return None
            time.sleep(2.0 * (k + 1))
    return None


def candles(coin, st, en, interval="1h"):
    j = post({"type": "candleSnapshot",
              "req": {"coin": coin, "interval": interval, "startTime": int(st),
                      "endTime": int(en)}})
    return j if isinstance(j, list) else []


def funding(coin, st, en):
    j = post({"type": "fundingHistory", "coin": coin, "startTime": int(st), "endTime": int(en)})
    return j if isinstance(j, list) else []


def bisect_earliest(probe, now, max_back_days=2000):
    """Smallest back-days D such that a 2-day window at now-D returns rows. Returns (days, ms)."""
    lo, hi = 3, max_back_days          # lo=3d back: window [now-3d, now-1d], certainly populated
    if not probe(now - lo * 86400000):
        return 0, now                  # even 3d back is empty -> no usable history
    if probe(now - max_back_days * 86400000):
        return max_back_days, now - max_back_days * 86400000
    while hi - lo > 2:
        mid = (lo + hi) // 2
        if probe(now - mid * 86400000):
            lo = mid
        else:
            hi = mid
    return lo, now - lo * 86400000


def stage_meta():
    now = int(time.time() * 1000)
    out = {"pulled_at_ms": now, "pulled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now / 1000))}
    mc = post({"type": "metaAndAssetCtxs"})
    uni = mc[0]["universe"]; ctx = mc[1]
    mk = []
    for u, c in zip(uni, ctx):
        mk.append({"name": u["name"], "szDecimals": u.get("szDecimals"),
                   "maxLeverage": u.get("maxLeverage"), "isDelisted": u.get("isDelisted", False),
                   "onlyIsolated": u.get("onlyIsolated", False),
                   "dayNtlVlm": float(c["dayNtlVlm"]) if c.get("dayNtlVlm") else None,
                   "openInterest": float(c["openInterest"]) if c.get("openInterest") else None,
                   "midPx": float(c["midPx"]) if c.get("midPx") else None,
                   "markPx": float(c["markPx"]) if c.get("markPx") else None,
                   "funding_hourly": float(c["funding"]) if c.get("funding") else None,
                   "premium": float(c["premium"]) if c.get("premium") not in (None, "") else None,
                   "impactPxs": c.get("impactPxs")})
    mk.sort(key=lambda d: -(d["dayNtlVlm"] or 0))
    out["n_markets"] = len(mk)
    out["n_active"] = sum(1 for d in mk if not d["isDelisted"])
    out["markets"] = mk
    tot = sum(d["dayNtlVlm"] or 0 for d in mk)
    out["total_dayNtlVlm_usd"] = tot
    print(f"[meta] {len(mk)} markets, active {out['n_active']}, 24h ntl ${tot/1e9:.2f}B", flush=True)
    print("  top15 by 24h ntl vol: " + ", ".join(
        f"{d['name']}=${(d['dayNtlVlm'] or 0)/1e6:.0f}M" for d in mk[:15]), flush=True)

    # ---- history depth ----
    depth = {}
    for coin in ("BTC", "ETH", "SOL"):
        d, ms = bisect_earliest(lambda st: len(candles(coin, st, st + 2 * 86400000)) > 0, now)
        depth[coin] = {"candle_1h_max_back_days": d,
                       "earliest_ok": time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))}
        print(f"[depth] {coin} 1h candles reach back {d}d -> {depth[coin]['earliest_ok']}", flush=True)
    d, ms = bisect_earliest(lambda st: len(funding("BTC", st, st + 2 * 86400000)) > 0, now)
    depth["BTC_funding"] = {"max_back_days": d,
                            "earliest_ok": time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))}
    print(f"[depth] BTC fundingHistory reaches back {d}d -> {depth['BTC_funding']['earliest_ok']}",
          flush=True)
    # rows per call
    c = candles("BTC", now - 400 * 86400000, now)
    depth["candle_rows_per_call"] = len(c)
    f = funding("BTC", now - 400 * 86400000, now)
    depth["funding_rows_per_call"] = len(f)
    out["history_depth"] = depth
    json.dump(out, open(MA + "/exports/eda/hl_meta.json", "w"), indent=1)
    print("-> hl_meta.json", flush=True)
    return out


# ------------------------------------------------------------------ symbol mapping
def hl_to_binance(name):
    """HL coin name -> our panel symbol. HL uses bare coin names; kMEME prefix for 1000x."""
    if name.startswith("k"):                      # kPEPE, kBONK, kSHIB, kFLOKI, kLUNC, kNEIRO, kDOGS
        return "1000" + name[1:] + "USDT"
    return name + "USDT"


def stage_hist(days=210):
    now = int(time.time() * 1000)
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
    syms = [str(s) for s in W["symbols"]]
    mem = W["MEMBER110"]
    last_member = mem[-1]
    panel_syms = set(syms)
    # HL markets mapped onto our symbol space
    rows = [d for d in meta["markets"] if not d["isDelisted"]]
    mapped = []
    for d in rows:
        b = hl_to_binance(d["name"])
        mapped.append({**d, "binance": b, "in_panel": b in panel_syms,
                       "in_member_last": bool(b in panel_syms and last_member[syms.index(b)])})
    ov = [d for d in mapped if d["in_panel"]]
    print(f"[map] HL active {len(rows)} | maps into panel-140: {len(ov)} | "
          f"of which in last MEMBER110: {sum(d['in_member_last'] for d in mapped)}", flush=True)

    st = now - days * 86400000
    coins = [d["name"] for d in mapped if d["in_panel"]]
    C, F = {}, {}
    for i, c in enumerate(coins):
        k = candles(c, st, now)
        if k:
            C[c] = np.array([[float(r["t"]), float(r["o"]), float(r["h"]), float(r["l"]),
                              float(r["c"]), float(r["v"]), float(r["n"])] for r in k])
        # funding: 500 rows/call -> page backwards
        acc, cur = [], st
        while cur < now:
            f = funding(c, cur, min(cur + 480 * HOUR, now))
            if not f:
                cur += 480 * HOUR
                continue
            acc += [[float(r["time"]), float(r["fundingRate"]),
                     float(r["premium"]) if r.get("premium") not in (None, "") else np.nan]
                    for r in f]
            nt = int(f[-1]["time"]) + HOUR
            cur = nt if nt > cur else cur + 480 * HOUR
        if acc:
            a = np.array(acc)
            _, u = np.unique(a[:, 0], return_index=True)
            F[c] = a[np.sort(u)]
        if (i + 1) % 10 == 0 or i == len(coins) - 1:
            print(f"  [{i+1}/{len(coins)}] {c}: candles={len(C.get(c, []))} funding={len(F.get(c, []))}",
                  flush=True)
    np.savez(MA + "/exports/eda/hl_hist.npz",
             coins=np.array(list(C.keys()), dtype=object),
             candles=np.array([C[c] for c in C], dtype=object),
             fcoins=np.array(list(F.keys()), dtype=object),
             funding=np.array([F[c] for c in F], dtype=object),
             mapped=np.array(json.dumps(mapped), dtype=object),
             pulled_at_ms=np.array([now]))
    print(f"-> hl_hist.npz ({len(C)} candle series, {len(F)} funding series)", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="meta", choices=["meta", "hist"])
    ap.add_argument("--days", type=int, default=210)
    ap.add_argument("--pause", type=float, default=None)
    a = ap.parse_args()
    if a.pause:
        PAUSE = a.pause
    if a.stage == "meta":
        stage_meta()
    else:
        stage_hist(a.days)
