"""Targeted HL history pull for (3b) price consistency + (3c) funding transferability.

Scope chosen for wall-clock: the path to HL from this host stalls ~30s on a minority of calls,
so the full 210d-funding pull needed ~6h. Instead:
  - candles: full API range (1 call/coin, 5000 rows = 210d) -> (3b) over 2025-12-27..2026-06-30
  - funding: FUND_DAYS window ending at the panel's last timestamp (3 calls/coin) -> (3c)
Short timeout + retries so a stalled call is abandoned fast rather than blocking 25s.

READ-ONLY public /info. Out: exports/eda/hl_hist.npz
"""
import os
import json, time, sys
import urllib.request
import numpy as np

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
URL = "https://api.hyperliquid.xyz/info"
UA = "Mozilla/5.0 (research-data-probe; read-only public market data)"
PAUSE = 0.6
TIMEOUT = 8
HOUR = 3600_000
FUND_DAYS = 60
PANEL_END_MS = None      # filled from the panel


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
            time.sleep(0.8 * (k + 1))
    return None


def hl_to_binance(name):
    return ("1000" + name[1:] + "USDT") if name.startswith("k") else (name + "USDT")


def main():
    now = int(time.time() * 1000)
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
    syms = [str(s) for s in W["symbols"]]
    panel_end = int(W["ts"][-1])
    coins = [d["name"] for d in meta["markets"]
             if not d["isDelisted"] and hl_to_binance(d["name"]) in set(syms)]
    print(f"[hist2] {len(coins)} coins | panel ends "
          f"{time.strftime('%Y-%m-%d', time.gmtime(panel_end/1000))}", flush=True)

    fund_start = panel_end - FUND_DAYS * 86400_000
    C, F = {}, {}
    t0 = time.time()
    for i, c in enumerate(coins):
        k = post({"type": "candleSnapshot",
                  "req": {"coin": c, "interval": "1h", "startTime": now - 210 * 86400_000,
                          "endTime": now}})
        if isinstance(k, list) and k:
            C[c] = np.array([[float(r["t"]), float(r["o"]), float(r["h"]), float(r["l"]),
                              float(r["c"]), float(r["v"]), float(r["n"])] for r in k])
        acc, cur = [], fund_start
        while cur < panel_end:
            f = post({"type": "fundingHistory", "coin": c, "startTime": int(cur),
                      "endTime": int(min(cur + 480 * HOUR, panel_end))})
            if isinstance(f, list) and f:
                acc += [[float(r["time"]), float(r["fundingRate"]),
                         float(r["premium"]) if r.get("premium") not in (None, "") else np.nan]
                        for r in f]
                nt = int(f[-1]["time"]) + HOUR
                cur = nt if nt > cur else cur + 480 * HOUR
            else:
                cur += 480 * HOUR
        if acc:
            a = np.array(acc)
            _, u = np.unique(a[:, 0], return_index=True)
            F[c] = a[np.sort(u)]
        if (i + 1) % 10 == 0 or i == len(coins) - 1:
            print(f"  [{i+1}/{len(coins)}] {c}: candles={len(C.get(c,[]))} "
                  f"funding={len(F.get(c,[]))} ({time.time()-t0:.0f}s)", flush=True)
    np.savez(MA + "/exports/eda/hl_hist.npz",
             coins=np.array(list(C.keys()), dtype=object),
             candles=np.array([C[c] for c in C], dtype=object),
             fcoins=np.array(list(F.keys()), dtype=object),
             funding=np.array([F[c] for c in F], dtype=object),
             pulled_at_ms=np.array([now]), fund_days=np.array([FUND_DAYS]))
    print(f"-> hl_hist.npz ({len(C)} candle, {len(F)} funding series, {time.time()-t0:.0f}s)",
          flush=True)


if __name__ == "__main__":
    main()
