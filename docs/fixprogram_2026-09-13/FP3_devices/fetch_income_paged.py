#!/usr/bin/env python3
"""Paginated read-only income pull. Raw pages land on disk untouched; nothing is written to any ledger.
usage: fetch_income_paged.py <startMs> <endMs> <out.json> [label]"""
import hashlib, hmac, json, os, sys, time, urllib.parse, urllib.request

kv = {}
for line in open(os.path.expanduser("~/.quant_readonly.env")):
    line = line.strip()
    if line and not line.startswith("#"):
        for sep in ("=", ":"):
            if sep in line:
                k, v = line.split(sep, 1); kv[k.strip()] = v.strip(); break
K, SEC = kv["QUANT_RO_API_KEY"], kv["QUANT_RO_API_SECRET"]
BASE = "https://fapi.binance.com"; _last = [0.0]


def get(params):
    dt = time.time() - _last[0]
    if dt < 0.35: time.sleep(0.35 - dt)
    p = dict(params); p["timestamp"] = int(time.time() * 1000); p["recvWindow"] = 5000
    q = urllib.parse.urlencode(p, safe=",")
    sig = hmac.new(SEC.encode(), q.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(f"{BASE}/fapi/v1/income?{q}&signature={sig}", headers={"X-MBX-APIKEY": K})
    _last[0] = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode()), dict(r.headers)
    except urllib.error.HTTPError as e:
        try: b = json.loads(e.read().decode())
        except Exception: b = {"raw": "unparsable"}
        return e.code, b, dict(e.headers)


s, e, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
label = sys.argv[4] if len(sys.argv) > 4 else ""
pages, rows, cur, seen = [], [], s, set()
while True:
    st, body, hdr = get({"startTime": cur, "endTime": e, "limit": 1000})
    pages.append({"startTime": cur, "status": st, "n": len(body) if isinstance(body, list) else 0, "weight": hdr.get("X-MBX-USED-WEIGHT-1M")})
    if st != 200 or not isinstance(body, list):
        print(f"{label} PAGE FAIL rc {st} {json.dumps(body)[:140]}"); break
    new = [r for r in body if (r.get("tranId"), r.get("incomeType"), r.get("symbol"), r.get("time"), r.get("income")) not in seen]
    for r in new: seen.add((r.get("tranId"), r.get("incomeType"), r.get("symbol"), r.get("time"), r.get("income")))
    rows += new
    if len(body) < 1000: break
    nxt = max(int(r["time"]) for r in body) + 1
    if nxt <= cur: break
    cur = nxt
json.dump({"endpoint": "/fapi/v1/income", "label": label, "startTime": s, "endTime": e,
           "fetched_utc": time.strftime("%FT%TZ", time.gmtime()), "pages": pages, "n_rows": len(rows), "body": rows},
          open(out, "w"), indent=1)
import collections
print(f"{label} rows {len(rows)} pages {len(pages)} types {dict(collections.Counter(r['incomeType'] for r in rows))}")
