#!/usr/bin/env python3
"""FP3 I: read-only venue fetch. Raw responses land on disk untouched; nothing is written to any ledger.
usage: fetch_trades.py trades <SYMBOL> <startMs> <endMs> <out.json>
BOUNDARY (independent review round 14): `trades` also sends ONE request with limit=1000 — a full page means the window may be TRUNCATED, so the
receipt records `saturated` and the caller must narrow the window or page. The `income` mode is refused here; use fetch_income_paged.py.
This is a one-round evidence tool, not a certified long-running ledger synchroniser: the 0.35 s single-process throttle says nothing about
multi-process rate limits or 429 handling, and the writes are not atomic."""
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
    sat = (n >= 1000)
    d = json.load(open(out)); d["saturated"] = sat; d["completeness"] = ("UNPROVEN: the page is full, the window may be truncated" if sat else "page short of the limit ⇒ window complete")
    json.dump(d, open(out, "w"), indent=1)
    print(f"{sym} rc {st} rows {n}" + ("  ★SATURATED, completeness UNPROVEN" if sat else "") + ("" if st == 200 else f" | {json.dumps(body)[:160]}"))
elif mode == "income":
    # ★ R14-I2 (independent review round 14): this mode used to send ONE request with limit=1000 and no pagination, so a full page was
    #   indistinguishable from a complete window — two real pulls came back at exactly 1,000 rows. Use fetch_income_paged.py instead;
    #   this entry point now refuses rather than producing a receipt whose completeness is unknown.
    print("REFUSED: single-shot income is not complete-by-construction (a full 1000-row page cannot be told from a finished window).")
    print("         Use fetch_income_paged.py <startMs> <endMs> <out.json> [label], which pages until a short page and records every page.")
    sys.exit(2)
