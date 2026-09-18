#!/usr/bin/env python3
"""Read-only credential controls. Prints VERDICTS ONLY — never the key, never the secret, never a signature.
POSITIVE: GET /fapi/v3/account must succeed (the key can read the futures account).
NEGATIVE: POST /fapi/v1/order/test must be REFUSED with -2015 (no trade permission). The `test` endpoint validates
          and never sends an order; a 200 here would mean the key CAN trade, which is a stop condition."""
import hashlib, hmac, json, os, time, urllib.parse, urllib.request

P = os.path.expanduser("~/.quant_readonly.env")
kv = {}
for line in open(P):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    for sep in (":", "="):
        if sep in line:
            k, v = line.split(sep, 1); kv[k.strip()] = v.strip(); break
K = kv.get("QUANT_RO_API_KEY"); SEC = kv.get("QUANT_RO_API_SECRET")
print("keys present:", bool(K), bool(SEC), "| key length", len(K or ""), "| secret length", len(SEC or ""))
BASE = "https://fapi.binance.com"


def signed(path, params=None, method="GET"):
    p = dict(params or {}); p["timestamp"] = int(time.time() * 1000); p["recvWindow"] = 5000
    q = urllib.parse.urlencode(p, safe=",")
    sig = hmac.new(SEC.encode(), q.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE}{path}?{q}&signature={sig}"
    req = urllib.request.Request(url, method=method, headers={"X-MBX-APIKEY": K})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read().decode())
        except Exception: body = {"raw": "unparsable"}
        return e.code, body
    except Exception as e:   # noqa: BLE001
        return None, {"transport_error": type(e).__name__}


print("\n[POSITIVE] GET /fapi/v3/account")
st, body = signed("/fapi/v3/account")
if st == 200:
    print("  rc 200 OK | totalWalletBalance present:", "totalWalletBalance" in body,
          "| n positions:", len(body.get("positions") or []), "| canTrade flag:", body.get("canTrade"),
          "| canDeposit:", body.get("canDeposit"), "| canWithdraw:", body.get("canWithdraw"))
else:
    print("  rc", st, "|", json.dumps(body)[:200])

print("\n[NEGATIVE] POST /fapi/v1/order/test  (validates only, never sends)")
st2, body2 = signed("/fapi/v1/order/test", {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0.001"}, method="POST")
code = body2.get("code")
print("  rc", st2, "| venue code", code, "|", str(body2.get("msg"))[:90])
if st2 == 200:
    print("  *** STOP: the key ACCEPTED an order test — it HAS trade permission. Do not use it. ***")
elif code == -2015:
    print("  OK: refused with -2015 (invalid API-key, IP, or permissions) — consistent with a read-only key")
elif code in (-2014, -1022):
    print("  signature/key format problem, not a permission verdict")
else:
    print("  refused, but not with -2015 — read the code above before concluding")
