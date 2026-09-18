#!/usr/bin/env python3
"""FP3 I: read-only venue fetch. Raw responses land on disk untouched; nothing is written to any ledger.
usage: fetch_trades.py trades <SYMBOL> <startMs> <endMs> <out.json>
       fetch_trades.py income <startMs> <endMs> <out.json> [incomeType]"""
import hashlib, hmac, json, os, sys, time, urllib.parse, urllib.request

kv = {}
for line in open(os.path.expanduser("~/.quant_readonly.env")):
    line = line.strip()
    if line and not line.startswith("#"):
        for sep in (":", "="):
            if sep in line:
                k, v = line.split(sep, 1); kv[k.strip()] = v.strip(); break
K, SEC = kv["QUANT_RO_API_KEY"], kv["QUANT_RO_API_SECRET"]
BASE = "https://fapi.binance.com"
_last = [0.0]


def get(path, params):
    dt = time.time() - _last[0]
    if dt < 0.35: time.sleep(0.35 - dt)
    p = dict(params); p["timestamp"] = int(time.time() * 1000); p["recvWindow"] = 5000
    q = urllib.parse.urlencode(p, safe=",")
    sig = hmac.new(SEC.encode(), q.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(f"{BASE}{path}?{q}&signature={sig}", headers={"X-MBX-APIKEY": K})
    _last[0] = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode()), dict(r.headers)
    except urllib.error.HTTPError as e:
        try: b = json.loads(e.read().decode())
        except Exception: b = {"raw": "unparsable"}
        return e.code, b, dict(e.headers)


mode = sys.argv[1]
if mode == "trades":
    sym, s, e, out = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    st, body, hdr = get("/fapi/v1/userTrades", {"symbol": sym, "startTime": s, "endTime": e, "limit": 1000})
    json.dump({"endpoint": "/fapi/v1/userTrades", "symbol": sym, "startTime": s, "endTime": e, "status": st,
               "fetched_utc": time.strftime("%FT%TZ", time.gmtime()), "weight_used": hdr.get("X-MBX-USED-WEIGHT-1M"), "body": body},
              open(out, "w"), indent=1)
    n = len(body) if isinstance(body, list) else 0
    print(f"{sym} rc {st} rows {n}" + ("" if st == 200 else f" | {json.dumps(body)[:160]}"))
elif mode == "income":
    s, e, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    t = sys.argv[5] if len(sys.argv) > 5 else None
    p = {"startTime": s, "endTime": e, "limit": 1000}
    if t: p["incomeType"] = t
    st, body, hdr = get("/fapi/v1/income", p)
    json.dump({"endpoint": "/fapi/v1/income", "startTime": s, "endTime": e, "incomeType": t, "status": st,
               "fetched_utc": time.strftime("%FT%TZ", time.gmtime()), "weight_used": hdr.get("X-MBX-USED-WEIGHT-1M"), "body": body},
              open(out, "w"), indent=1)
    n = len(body) if isinstance(body, list) else 0
    print(f"income {t or 'ALL'} rc {st} rows {n}" + ("" if st == 200 else f" | {json.dumps(body)[:160]}"))
