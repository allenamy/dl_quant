"""Hyperliquid L2 order-book snapshot for the panel-overlap coins (READ-ONLY public /info).

Gives a DIRECT depth/impact measure for the capacity question (3d) instead of inferring impact
from volume: for each coin, walk the book to price a market order of $X notional and record the
slippage vs mid.

CAVEAT: a SINGLE snapshot at one wall-clock moment. Depth is time-varying (thinner on weekends /
in stress). Treat as an order-of-magnitude read, not a time-averaged execution cost.

Out: exports/eda/hl_l2_snapshot.json
"""
import json, time
import urllib.request
import numpy as np

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
URL = "https://api.hyperliquid.xyz/info"
UA = "Mozilla/5.0 (research-data-probe; read-only public market data)"
PAUSE = 2.0
NOTIONALS = [5_000, 25_000, 50_000, 150_000, 500_000]


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


def hl_to_binance(name):
    return ("1000" + name[1:] + "USDT") if name.startswith("k") else (name + "USDT")


def walk(levels, notional, mid, side):
    """VWAP slippage in bps to fill `notional` USD by sweeping `levels`. None if book too thin."""
    got = 0.0; cost = 0.0
    for lv in levels:
        px = float(lv["px"]); sz = float(lv["sz"])
        avail = px * sz
        take = min(avail, notional - got)
        cost += take
        got += take
        if got >= notional - 1e-9:
            # weighted avg price of the sweep
            break
    if got < notional - 1e-9:
        return None
    # recompute VWAP properly
    got = 0.0; qty = 0.0
    for lv in levels:
        px = float(lv["px"]); sz = float(lv["sz"])
        avail = px * sz
        take = min(avail, notional - got)
        qty += take / px
        got += take
        if got >= notional - 1e-9:
            break
    vwap = notional / qty
    return (vwap - mid) / mid * 1e4 * (1 if side == "buy" else -1)


def main():
    now = int(time.time() * 1000)
    meta = json.load(open(MA + "/exports/eda/hl_meta.json"))
    W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
    panel = set(str(s) for s in W["symbols"])
    rows = [d for d in meta["markets"]
            if not d["isDelisted"] and hl_to_binance(d["name"]) in panel]
    print(f"[l2] snapshotting {len(rows)} overlap coins", flush=True)
    out = {"pulled_at_ms": now,
           "pulled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now / 1000)),
           "caveat": ("single L2 snapshot; depth is time-varying. Slippage = VWAP-vs-mid in bps "
                      "for a one-shot TAKER sweep of the given USD notional."),
           "notionals": NOTIONALS, "by_coin": {}}
    for i, d in enumerate(rows):
        c = d["name"]
        j = post({"type": "l2Book", "coin": c})
        if not j or "levels" not in j:
            out["by_coin"][c] = {"err": "no book"}
            continue
        bids, asks = j["levels"][0], j["levels"][1]
        if not bids or not asks:
            out["by_coin"][c] = {"err": "empty side"}
            continue
        bb, ba = float(bids[0]["px"]), float(asks[0]["px"])
        mid = 0.5 * (bb + ba)
        rec = {"binance": hl_to_binance(c), "mid": mid,
               "top_spread_bps": round((ba - bb) / mid * 1e4, 3),
               "depth_usd_bid": round(sum(float(l["px"]) * float(l["sz"]) for l in bids)),
               "depth_usd_ask": round(sum(float(l["px"]) * float(l["sz"]) for l in asks)),
               "dayNtlVlm": d["dayNtlVlm"], "openInterest_usd": (d["openInterest"] * mid
                                                                if d["openInterest"] else None),
               "slip_bps": {}}
        for n in NOTIONALS:
            sb = walk(asks, n, mid, "buy")
            ss = walk(bids, n, mid, "sell")
            rec["slip_bps"][str(n)] = {
                "buy": (round(sb, 2) if sb is not None else None),
                "sell": (round(ss, 2) if ss is not None else None),
                "roundtrip": (round(sb + ss, 2) if (sb is not None and ss is not None) else None)}
        out["by_coin"][c] = rec
        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(rows)}] {c} spread={rec['top_spread_bps']:.2f}bps "
                  f"depth=${rec['depth_usd_bid']/1e3:.0f}k", flush=True)
    json.dump(out, open(MA + "/exports/eda/hl_l2_snapshot.json", "w"), indent=1)
    print("-> hl_l2_snapshot.json", flush=True)


if __name__ == "__main__":
    main()
