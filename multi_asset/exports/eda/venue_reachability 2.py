"""Venue reachability probe (READ-ONLY public endpoints, gentle rate limit).

Discipline: public market-data endpoints ONLY. No trading/account/auth endpoints, no order
placement, no geo-restriction circumvention. One request at a time with sleeps.

Measures, per venue: DNS -> TCP/TLS -> (a) perp market list (b) hourly candle history depth
(c) funding history. Binance fapi/data.binance.vision included as CONTROLS to validate the probe
itself (fapi is known-blocked from jpline; data.binance.vision is known-reachable).

Out: exports/eda/venue_reachability.json
"""
import os
import json, socket, ssl, time, sys
import urllib.request
import urllib.error

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
OUT = (MA + "/exports/eda/"
       "venue_reachability.json")
UA = "Mozilla/5.0 (research-data-probe; read-only public market data)"
TIMEOUT = 20
PAUSE = 1.0


def http(url, method="GET", payload=None, timeout=TIMEOUT):
    t0 = time.time()
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"User-Agent": UA, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            dt = time.time() - t0
            try:
                j = json.loads(body)
            except Exception:
                j = None
            return {"ok": True, "status": r.status, "ms": round(dt * 1000), "bytes": len(body),
                    "json": j, "text": (body[:300].decode("utf8", "replace") if j is None else None)}
    except urllib.error.HTTPError as e:
        b = e.read()[:400]
        return {"ok": False, "status": e.code, "ms": round((time.time() - t0) * 1000),
                "err": "HTTPError", "text": b.decode("utf8", "replace")}
    except Exception as e:
        return {"ok": False, "ms": round((time.time() - t0) * 1000),
                "err": type(e).__name__, "text": str(e)[:300]}


def net_layer(host, port=443):
    out = {"host": host}
    t0 = time.time()
    try:
        ip = socket.gethostbyname(host)
        out["dns"] = {"ok": True, "ip": ip, "ms": round((time.time() - t0) * 1000)}
    except Exception as e:
        out["dns"] = {"ok": False, "err": str(e)[:200]}
        return out
    t0 = time.time()
    try:
        s = socket.create_connection((ip, port), timeout=TIMEOUT)
        out["tcp"] = {"ok": True, "ms": round((time.time() - t0) * 1000)}
        t0 = time.time()
        try:
            ctx = ssl.create_default_context()
            ss = ctx.wrap_socket(s, server_hostname=host)
            out["tls"] = {"ok": True, "ms": round((time.time() - t0) * 1000),
                          "proto": ss.version()}
            ss.close()
        except Exception as e:
            out["tls"] = {"ok": False, "err": type(e).__name__ + ": " + str(e)[:160]}
            s.close()
    except Exception as e:
        out["tcp"] = {"ok": False, "err": type(e).__name__ + ": " + str(e)[:160]}
    return out


def probe_hyperliquid():
    """Public info API: POST https://api.hyperliquid.xyz/info"""
    U = "https://api.hyperliquid.xyz/info"
    r = {"venue": "hyperliquid", "base": U, "net": net_layer("api.hyperliquid.xyz")}
    r["meta"] = http(U, "POST", {"type": "meta"}); time.sleep(PAUSE)
    m = r["meta"].get("json") or {}
    uni = m.get("universe") if isinstance(m, dict) else None
    r["n_perp_markets"] = len(uni) if uni else None
    r["sample_markets"] = [u.get("name") for u in uni[:15]] if uni else None
    r["meta"]["json"] = None                                     # keep file small
    # market contexts (funding / OI / 24h notional volume) -- needed for (a)/(d)
    r["metaAndAssetCtxs"] = http(U, "POST", {"type": "metaAndAssetCtxs"}); time.sleep(PAUSE)
    mc = r["metaAndAssetCtxs"].get("json")
    if isinstance(mc, list) and len(mc) == 2:
        r["ctx_fields"] = list(mc[1][0].keys()) if mc[1] else None
        r["ctx_n"] = len(mc[1])
        r["ctx_sample"] = mc[1][0] if mc[1] else None
    r["metaAndAssetCtxs"]["json"] = None
    # hourly candle history depth: walk back to find the earliest available hour for BTC
    now = int(time.time() * 1000)
    depth = {}
    for label, back_days in [("30d", 30), ("180d", 180), ("365d", 365), ("730d", 730),
                             ("1460d", 1460)]:
        st = now - back_days * 86400000
        q = http(U, "POST", {"type": "candleSnapshot",
                             "req": {"coin": "BTC", "interval": "1h",
                                     "startTime": st, "endTime": st + 7 * 86400000}})
        j = q.get("json")
        depth[label] = {"ok": q["ok"], "status": q.get("status"),
                        "n": (len(j) if isinstance(j, list) else None),
                        "first_t": (j[0].get("t") if isinstance(j, list) and j else None)}
        time.sleep(PAUSE)
    r["candle_depth_btc_1h"] = depth
    # max rows in one call (pagination limit)
    q = http(U, "POST", {"type": "candleSnapshot",
                         "req": {"coin": "BTC", "interval": "1h",
                                 "startTime": now - 400 * 86400000, "endTime": now}})
    j = q.get("json")
    r["candle_single_call_rows"] = len(j) if isinstance(j, list) else None
    time.sleep(PAUSE)
    # funding history
    q = http(U, "POST", {"type": "fundingHistory", "coin": "BTC",
                         "startTime": now - 7 * 86400000})
    j = q.get("json")
    r["fundingHistory"] = {"ok": q["ok"], "status": q.get("status"),
                           "n": (len(j) if isinstance(j, list) else None),
                           "sample": (j[0] if isinstance(j, list) and j else None)}
    time.sleep(PAUSE)
    q = http(U, "POST", {"type": "fundingHistory", "coin": "BTC",
                         "startTime": now - 1460 * 86400000,
                         "endTime": now - 1453 * 86400000})
    j = q.get("json")
    r["fundingHistory_4y_back"] = {"ok": q["ok"], "n": (len(j) if isinstance(j, list) else None),
                                   "sample": (j[0] if isinstance(j, list) and j else None)}
    return r


def probe_dydx():
    """dYdX v4 public indexer REST."""
    B = "https://indexer.dydx.trade/v4"
    r = {"venue": "dydx_v4", "base": B, "net": net_layer("indexer.dydx.trade")}
    q = http(B + "/perpetualMarkets"); time.sleep(PAUSE)
    j = q.get("json") or {}
    mk = j.get("markets") if isinstance(j, dict) else None
    r["markets_call"] = {"ok": q["ok"], "status": q.get("status"), "ms": q.get("ms"),
                         "err": q.get("err"), "text": q.get("text")}
    r["n_perp_markets"] = len(mk) if mk else None
    r["sample_markets"] = list(mk.keys())[:15] if mk else None
    r["market_fields"] = list(next(iter(mk.values())).keys()) if mk else None
    r["market_sample"] = next(iter(mk.values())) if mk else None
    q = http(B + "/candles/perpetualMarkets/BTC-USD?resolution=1HOUR&limit=100"); time.sleep(PAUSE)
    j = q.get("json") or {}
    c = j.get("candles") if isinstance(j, dict) else None
    r["candles"] = {"ok": q["ok"], "status": q.get("status"), "n": len(c) if c else None,
                    "newest": c[0].get("startedAt") if c else None,
                    "oldest": c[-1].get("startedAt") if c else None,
                    "fields": list(c[0].keys()) if c else None, "text": q.get("text")}
    # history depth probe: ask for candles ending 2 years ago
    import datetime as dt
    for label, back in [("365d", 365), ("730d", 730), ("1095d", 1095)]:
        ts = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=back)).strftime("%Y-%m-%dT%H:%M:%SZ")
        q = http(B + f"/candles/perpetualMarkets/BTC-USD?resolution=1HOUR&limit=10&toISO={ts}")
        j = q.get("json") or {}
        c = j.get("candles") if isinstance(j, dict) else None
        r.setdefault("candle_depth_btc_1h", {})[label] = {
            "ok": q["ok"], "status": q.get("status"), "n": len(c) if c else None,
            "oldest": c[-1].get("startedAt") if c else None}
        time.sleep(PAUSE)
    q = http(B + "/historicalFunding/BTC-USD?limit=100"); time.sleep(PAUSE)
    j = q.get("json") or {}
    f = j.get("historicalFunding") if isinstance(j, dict) else None
    r["historicalFunding"] = {"ok": q["ok"], "status": q.get("status"),
                              "n": len(f) if f else None,
                              "newest": f[0] if f else None, "oldest": f[-1] if f else None,
                              "text": q.get("text")}
    return r


def probe_controls():
    out = {}
    out["binance_fapi"] = {"net": net_layer("fapi.binance.com"),
                           "call": http("https://fapi.binance.com/fapi/v1/ping", timeout=10)}
    time.sleep(PAUSE)
    out["binance_data_vision"] = {
        "net": net_layer("data.binance.vision"),
        "call": http("https://data.binance.vision/?prefix=data/futures/um/daily/klines/", timeout=15)}
    for k in out:
        out[k]["call"]["json"] = None
        if out[k]["call"].get("text"):
            out[k]["call"]["text"] = out[k]["call"]["text"][:200]
    time.sleep(PAUSE)
    out["binance_api_spot"] = {"net": net_layer("api.binance.com"),
                               "call": http("https://api.binance.com/api/v3/ping", timeout=10)}
    out["binance_api_spot"]["call"]["json"] = None
    return out


def main():
    res = {"meta": {"created": "2026-07-25", "host": socket.gethostname(),
                    "discipline": ("read-only PUBLIC market-data endpoints only; no trading/auth "
                                   "endpoints touched; no geo-restriction circumvention; "
                                   "1 req/s")},
           "controls": probe_controls()}
    print("[controls]", json.dumps(res["controls"], indent=1)[:1200], flush=True)
    for fn in (probe_hyperliquid, probe_dydx):
        try:
            r = fn()
        except Exception as e:
            r = {"venue": fn.__name__, "fatal": type(e).__name__ + ": " + str(e)[:300]}
        res[r.get("venue", fn.__name__)] = r
        print("\n[%s] %s" % (r.get("venue"), json.dumps(r, indent=1)[:2500]), flush=True)
    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print("\n->", OUT, flush=True)


if __name__ == "__main__":
    main()
