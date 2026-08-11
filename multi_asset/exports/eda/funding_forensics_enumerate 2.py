import json, time, sys
from collections import Counter
sys.path.insert(0, "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad")
from oc_income_probe import get, _calls

now = int(time.time()*1000)
THROTTLE = 1.2   # /fapi/v1/income weight=30; stay far under the live process's budget

def q(lo, hi):
    time.sleep(THROTTLE)
    r = get("/fapi/v1/income", {"startTime": lo, "endTime": hi, "limit": 1000}, signed=True)
    if isinstance(r, dict):
        raise SystemExit(f"venue error {r}")
    return r

seen = {}
def enumerate_window(lo, hi, depth=0):
    """Recursively bisect until every window returns <1000 rows => complete, no boundary loss."""
    r = q(lo, hi)
    if len(r) < 1000 or lo >= hi:
        for x in r:
            seen[(x.get("tranId"), x["symbol"], x["income"], x["time"], x["incomeType"])] = x
        if len(r) >= 1000 and lo >= hi:
            print(f"    !! single-ms window {lo} still returns {len(r)} — TRUE hard limit hit")
        return
    mid = (lo + hi) // 2
    enumerate_window(lo, mid, depth+1)
    enumerate_window(mid+1, hi, depth+1)

print("=== T8: COMPLETE enumeration by recursive bisection (no window may return >=1000) ===")
t0 = now - 3*86400_000
enumerate_window(t0, now)
c = Counter(k[4] for k in seen)
print(f"  COMPLETE unique rows = {len(seen)}   types={dict(c)}")
print(f"  vs lead's / my single-loop 'full pagination' = 7903  -> DELTA = {len(seen)-7903}")
s_by = {}
for k, x in seen.items():
    s_by[k[4]] = s_by.get(k[4], 0.0) + float(x["income"])
s_all = sum(s_by.values())
print(f"  sum(income) complete = {s_all:.8f}   by type: " +
      ", ".join(f"{k}={v:.6f}" for k, v in sorted(s_by.items())))

print("\n=== T9: wallet reconciliation against the COMPLETE set ===")
time.sleep(THROTTLE)
acc = get("/fapi/v3/account", {}, signed=True)
wb = float(acc["totalWalletBalance"])
print(f"  totalWalletBalance = {wb:.8f}")
print(f"  sum(complete income) = {s_all:.8f}")
print(f"  RESIDUAL (wallet - income) = {wb - s_all:.8f} USDT")
print(f"  -> a funding charge NOT itemised in /income would appear here. |residual| tolerance: "
      f"rows landing between the two calls.")

print("\n=== T10: does testnet publish the funding MECHANISM at all? ===")
time.sleep(0.3)
pi = get("/fapi/v1/premiumIndex", {"symbol": "BTCUSDT"})
print(f"  premiumIndex BTCUSDT: lastFundingRate={pi.get('lastFundingRate')} "
      f"nextFundingTime={pi.get('nextFundingTime')} "
      f"({time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(pi['nextFundingTime'])/1000)) if pi.get('nextFundingTime') else '-'})")
time.sleep(0.3)
fr = get("/fapi/v1/fundingRate", {"symbol": "BTCUSDT", "limit": 10})
if isinstance(fr, list) and fr:
    print(f"  fundingRate history BTCUSDT: n={len(fr)} newest="
          f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(fr[-1]['fundingTime'])/1000))} "
          f"rate={fr[-1]['fundingRate']}")
    print(f"    (settlements published on THIS venue in the last rows: "
          f"{[time.strftime('%m-%dT%H:%MZ', time.gmtime(int(x['fundingTime'])/1000)) for x in fr[-6:]]})")
else:
    print(f"  fundingRate history: {fr}")
time.sleep(0.3)
fi = get("/fapi/v1/fundingInfo")
print(f"  fundingInfo: n={len(fi) if isinstance(fi,list) else fi}")

json.dump({"complete_n": len(seen), "types": dict(c), "sum_by_type": s_by,
           "wallet": wb, "residual": wb - s_all},
          open("/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/t8.json","w"), indent=1)
print(f"\n[calls={_calls[0]}]")
