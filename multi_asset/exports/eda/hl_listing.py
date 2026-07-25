"""Per-coin Hyperliquid listing date, by bisecting fundingHistory (reaches back 1171d).

Needed so the HL-overlap universe can be applied POINT-IN-TIME. Using today's HL roster over
2022-2026 history would be roster survivorship (we would be assuming HL listed, in 2023, the
coins we can see it lists in 2026).

READ-ONLY public /info endpoint, 1 req/1.05s (HL budget: 1200 weight/min, these calls weigh 20).
Out: exports/eda/hl_listing_dates.json
"""
import json, time
import urllib.request

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
URL = "https://api.hyperliquid.xyz/info"
UA = "Mozilla/5.0 (research-data-probe; read-only public market data)"
PAUSE = 1.05
DAY = 86400_000


def post(payload, retries=3):
    for k in range(retries):
        try:
            req = urllib.request.Request(URL, data=json.dumps(payload).encode(), method="POST",
                                         headers={"User-Agent": UA,
                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                out = json.loads(r.read())
            time.sleep(PAUSE)
            return out
        except Exception:
            if k == retries - 1:
                return None
            time.sleep(2.0 * (k + 1))
    return None


def has_funding(coin, t0):
    j = post({"type": "fundingHistory", "coin": coin, "startTime": int(t0),
              "endTime": int(t0 + 2 * DAY)})
    return bool(isinstance(j, list) and j)


def hl_to_binance(name):
    return ("1000" + name[1:] + "USDT") if name.startswith("k") else (name + "USDT")


def main():
    import numpy as np
    now = int(time.time() * 1000)
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
    panel = set(str(s) for s in W["symbols"])
    coins = [d["name"] for d in meta["markets"]
             if not d["isDelisted"] and hl_to_binance(d["name"]) in panel]
    print(f"[listing] dating {len(coins)} HL coins that map into the panel", flush=True)
    out = {"pulled_at_ms": now, "method": ("bisect earliest fundingHistory hit; API floor is "
                                           "~1171d (2023-05-11) so anything at the floor means "
                                           "'listed at or before the API horizon'"),
           "api_floor_days": 1171, "by_coin": {}}
    for i, c in enumerate(coins):
        # bracket: lo = known-present (recent), hi = known-absent (old)
        lo, hi = 3, 1200
        if not has_funding(c, now - lo * DAY):
            out["by_coin"][c] = {"listed_days_ago": None, "note": "no recent funding"}
            continue
        if has_funding(c, now - hi * DAY):
            out["by_coin"][c] = {"listed_days_ago": hi, "at_api_floor": True,
                                 "listed_on_or_before": time.strftime(
                                     "%Y-%m-%d", time.gmtime((now - hi * DAY) / 1000))}
            print(f"  [{i+1}/{len(coins)}] {c}: at API floor (>= {hi}d)", flush=True)
            continue
        while hi - lo > 30:            # month resolution is enough for a monthly-refresh mask
            mid = (lo + hi) // 2
            if has_funding(c, now - mid * DAY):
                lo = mid
            else:
                hi = mid
        out["by_coin"][c] = {"listed_days_ago": lo, "at_api_floor": False,
                             "listed_approx": time.strftime("%Y-%m-%d",
                                                            time.gmtime((now - lo * DAY) / 1000))}
        print(f"  [{i+1}/{len(coins)}] {c}: listed ~{out['by_coin'][c]['listed_approx']} "
              f"({lo}d ago)", flush=True)
        if (i + 1) % 20 == 0:
            json.dump(out, open(MA + "/exports/eda/hl_listing_dates.json", "w"), indent=1)
    json.dump(out, open(MA + "/exports/eda/hl_listing_dates.json", "w"), indent=1)
    print("-> hl_listing_dates.json", flush=True)


if __name__ == "__main__":
    main()
