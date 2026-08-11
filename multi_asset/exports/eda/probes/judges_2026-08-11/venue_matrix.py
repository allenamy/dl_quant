"""Venue reachability matrix from jpline (READ-ONLY public market-data endpoints).

Discipline: public market-data endpoints ONLY; no trading/account/auth endpoints; no order
placement; no geo-restriction circumvention; sequential, 1 req/host.

★ WHAT THIS MEASURES: whether OUR RESEARCH SERVER can pull a venue's public history.
  It does NOT measure whether the user can trade the venue from Singapore -- jpline sits behind
  a mainland-China egress filter (proven by the controls: fapi.binance.com and api.binance.com
  both resolve to unrelated IPs then TCP-timeout, while data.binance.vision returns 200).
  A network-level block shows as DNS-poison + TCP timeout; a venue GEO-block would instead
  complete TLS and return HTTP 403 with a body. The two are distinguishable here.

Endpoint paths for venues beyond the two named candidates are best-effort: a 403/404 still
proves NETWORK reachability (TLS completed), which is the point of the matrix.
"""
import json, socket, ssl, time
import urllib.request, urllib.error

OUT = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda/"
       "venue_matrix.json")
UA = "Mozilla/5.0 (research-data-probe; read-only public market data)"
T = 12

# (label, host, url, method, payload)
TARGETS = [
    # --- controls (validate the probe itself) ---
    ("CONTROL binance-fapi", "fapi.binance.com", "https://fapi.binance.com/fapi/v1/ping", "GET", None),
    ("CONTROL binance-spot", "api.binance.com", "https://api.binance.com/api/v3/ping", "GET", None),
    ("CONTROL binance-data-cdn", "data.binance.vision", "https://data.binance.vision/", "GET", None),
    # --- named candidates ---
    ("hyperliquid", "api.hyperliquid.xyz", "https://api.hyperliquid.xyz/info", "POST", {"type": "meta"}),
    ("dydx-v4 indexer", "indexer.dydx.trade", "https://indexer.dydx.trade/v4/perpetualMarkets", "GET", None),
    # --- other order-book perp DEXs (best-effort paths) ---
    ("paradex", "api.prod.paradex.trade", "https://api.prod.paradex.trade/v1/markets", "GET", None),
    ("aster", "fapi.asterdex.com", "https://fapi.asterdex.com/fapi/v1/exchangeInfo", "GET", None),
    ("lighter", "mainnet.zklighter.elliot.ai", "https://mainnet.zklighter.elliot.ai/api/v1/orderBooks", "GET", None),
    ("extended", "api.starknet.extended.exchange", "https://api.starknet.extended.exchange/api/v1/info/markets", "GET", None),
    ("vertex", "archive.prod.vertexprotocol.com", "https://archive.prod.vertexprotocol.com/v1", "GET", None),
    ("drift", "dlob.drift.trade", "https://dlob.drift.trade/markets24h", "GET", None),
    ("backpack", "api.backpack.exchange", "https://api.backpack.exchange/api/v1/markets", "GET", None),
    # --- CEX comparators (reachability only; SG retail access is a separate legal question) ---
    ("bybit", "api.bybit.com", "https://api.bybit.com/v5/market/time", "GET", None),
    ("okx", "www.okx.com", "https://www.okx.com/api/v5/public/time", "GET", None),
    ("gate", "api.gateio.ws", "https://api.gateio.ws/api/v4/spot/time", "GET", None),
]


def net_layer(host):
    o = {}
    t0 = time.time()
    try:
        ip = socket.gethostbyname(host)
        o["dns"] = {"ok": True, "ip": ip, "ms": round((time.time() - t0) * 1000)}
    except Exception as e:
        return {"dns": {"ok": False, "err": str(e)[:120]}}
    t0 = time.time()
    try:
        s = socket.create_connection((ip, 443), timeout=T)
        o["tcp"] = {"ok": True, "ms": round((time.time() - t0) * 1000)}
        t0 = time.time()
        try:
            ss = ssl.create_default_context().wrap_socket(s, server_hostname=host)
            o["tls"] = {"ok": True, "ms": round((time.time() - t0) * 1000), "proto": ss.version()}
            ss.close()
        except Exception as e:
            o["tls"] = {"ok": False, "err": type(e).__name__ + ": " + str(e)[:120]}
            s.close()
    except Exception as e:
        o["tcp"] = {"ok": False, "err": type(e).__name__ + ": " + str(e)[:120]}
    return o


def call(url, method, payload):
    t0 = time.time()
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"User-Agent": UA, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=T) as r:
            b = r.read()
            return {"status": r.status, "ms": round((time.time() - t0) * 1000), "bytes": len(b),
                    "head": b[:120].decode("utf8", "replace")}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "ms": round((time.time() - t0) * 1000), "http_error": True,
                "head": e.read()[:160].decode("utf8", "replace")}
    except Exception as e:
        return {"status": None, "ms": round((time.time() - t0) * 1000),
                "err": type(e).__name__, "head": str(e)[:160]}


def verdict(n, c):
    if not n.get("dns", {}).get("ok"):
        return "DNS-FAIL"
    if not n.get("tcp", {}).get("ok"):
        return "TCP-BLOCKED (network-level: DNS resolves, no TCP -- GFW signature, NOT a venue geo-block)"
    if not n.get("tls", {}).get("ok"):
        return "TLS-FAIL (possible MITM/filter)"
    s = c.get("status")
    if s == 200:
        return "OK"
    if s == 403:
        return "REACHABLE but HTTP 403 (venue-side block or auth required)"
    if s in (404, 405, 400, 422):
        return f"REACHABLE, HTTP {s} (endpoint path wrong; network is fine)"
    if s is None:
        return f"HTTP-FAIL ({c.get('err')})"
    return f"REACHABLE, HTTP {s}"


def main():
    res = {"meta": {"created": "2026-07-25", "host": socket.gethostname(),
                    "scope": ("reachability of PUBLIC market-data endpoints FROM jpline "
                              "(research server, mainland-China egress). NOT a statement about "
                              "the user's ability to access these venues from Singapore."),
                    "discipline": ("read-only public endpoints; no trading/auth endpoints; "
                                   "no geo-restriction circumvention")},
           "rows": []}
    for label, host, url, method, payload in TARGETS:
        n = net_layer(host)
        c = call(url, method, payload) if n.get("tls", {}).get("ok") else {"status": None,
                                                                           "err": "skipped-no-tls"}
        v = verdict(n, c)
        row = {"venue": label, "host": host, "url": url, "net": n, "call": c, "verdict": v}
        res["rows"].append(row)
        ip = n.get("dns", {}).get("ip", "-")
        print(f"{label:26s} {ip:16s} {v}", flush=True)
        time.sleep(0.5)
    json.dump(res, open(OUT, "w"), indent=1)
    print("\n->", OUT, flush=True)


if __name__ == "__main__":
    main()
