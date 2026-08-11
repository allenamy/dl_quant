#!/usr/bin/env python3
"""0C INDEPENDENT venue probe — written from scratch, does NOT import dl_quant_live code.

Signs its own requests (hmac-sha256), builds its own pagination, so a defect in the
production broker/ledger cannot propagate into the verdict.

READ-ONLY: GET endpoints only.
"""
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter

BASE = "https://testnet.binancefuture.com"
ENV = "/Users/haosiyu/dl_quant_live/.env"


def load_env():
    k = s = None
    for line in open(ENV):
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        name, _, val = line.partition("=")
        val = val.strip().strip('"').strip("'")
        if name.strip() == "BINANCE_TESTNET_KEY":
            k = val
        elif name.strip() == "BINANCE_TESTNET_SECRET":
            s = val
    assert k and s, "missing testnet credentials"
    return k, s


KEY, SECRET = load_env()
_calls = [0]


def get(path, params=None, signed=False):
    p = dict(params or {})
    if signed:
        p["timestamp"] = int(time.time() * 1000)
        p["recvWindow"] = 5000
        q = urllib.parse.urlencode(p)
        sig = hmac.new(SECRET.encode(), q.encode(), hashlib.sha256).hexdigest()
        q = q + "&signature=" + sig
    else:
        q = urllib.parse.urlencode(p)
    url = f"{BASE}{path}?{q}" if q else f"{BASE}{path}"
    req = urllib.request.Request(url, headers={"X-MBX-APIKEY": KEY} if signed else {})
    _calls[0] += 1
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400]
        return {"__http_error__": e.code, "body": body}


def page_income(start_ms, end_ms, income_type=None, limit=1000, tag="", verbose=True):
    """MY pagination: advance by newest_time+1, but ALSO detect the same-ms boundary hazard."""
    out, cursor, pages = [], start_ms, 0
    seen_ids = set()
    dup = 0
    while cursor <= end_ms:
        p = {"startTime": cursor, "endTime": end_ms, "limit": limit}
        if income_type:
            p["incomeType"] = income_type
        page = get("/fapi/v1/income", p, signed=True)
        if isinstance(page, dict):
            print(f"  [{tag}] ERROR at cursor={cursor}: {page}")
            return out, {"error": page, "pages": pages}
        pages += 1
        if not page:
            break
        for r in page:
            tid = r.get("tranId")
            key = (tid, r.get("symbol"), r.get("income"), r.get("time"), r.get("incomeType"))
            if key in seen_ids:
                dup += 1
            else:
                seen_ids.add(key)
                out.append(r)
        newest = max(int(x["time"]) for x in page)
        oldest = min(int(x["time"]) for x in page)
        if verbose:
            print(f"  [{tag}] page{pages}: n={len(page)} span={oldest}..{newest} cursor_was={cursor}")
        if len(page) < limit:
            break
        if newest <= cursor:
            print(f"  [{tag}] !! no forward progress (newest {newest} <= cursor {cursor}) — "
                  f"a full page shares one ms; advancing by +1 would DROP rows. STOPPING.")
            return out, {"stalled_at": cursor, "pages": pages, "dup": dup}
        # hazard probe: how many rows on this page carry the newest ms?
        n_at_newest = sum(1 for x in page if int(x["time"]) == newest)
        if len(page) == limit and n_at_newest > 1:
            print(f"  [{tag}] note: {n_at_newest} rows share newest ms {newest} at a FULL page "
                  f"boundary -> cursor=newest+1 can drop siblings")
        cursor = newest + 1
    return out, {"pages": pages, "dup": dup}


def summarize(rows, tag):
    c = Counter(r["incomeType"] for r in rows)
    ts = [int(r["time"]) for r in rows]
    print(f"[{tag}] TOTAL={len(rows)}  types={dict(c)}")
    if ts:
        print(f"[{tag}] time span {min(ts)} .. {max(ts)}  "
              f"({time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(min(ts)/1000))} .. "
              f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(max(ts)/1000))})")
    return c


if __name__ == "__main__":
    now = int(time.time() * 1000)
    print(f"now_ms={now}  {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now/1000))}")
    which = sys.argv[1] if len(sys.argv) > 1 else "all"

    if which in ("all", "t1"):
        print("\n=== T1: unfiltered income, last 3 days (lead's claim: 7903 rows, 0 FUNDING_FEE) ===")
        rows, meta = page_income(now - 3 * 86400_000, now, None, tag="3d-all")
        c = summarize(rows, "3d-all")
        print(f"  meta={meta}")
        json.dump({"n": len(rows), "types": dict(c), "meta": meta},
                  open("/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/"
                       "6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/t1.json", "w"), indent=1)
        json.dump(rows, open("/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/"
                             "6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/t1_rows.json", "w"))
    print(f"\n[calls={_calls[0]}]")
