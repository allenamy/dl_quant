import json, time, sys
from collections import Counter
sys.path.insert(0, "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad")
from oc_income_probe import get, _calls
now = int(time.time()*1000)
floor90 = now - 90*86400_000

print("=== T4: the ONE query that actually decides it — type-filtered, whole retention, single page ===")
for it in ["FUNDING_FEE"]:
    r = get("/fapi/v1/income", {"incomeType": it, "startTime": floor90, "endTime": now, "limit": 1000}, signed=True)
    print(f"  incomeType={it} over 90d: n={len(r) if isinstance(r,list) else r}  "
          f"(<1000 => NO page boundary => the count is exact, pagination cannot be blamed)")
# also with no startTime at all (venue default = recent 7d) and with symbol-less defaults
r = get("/fapi/v1/income", {"incomeType": "FUNDING_FEE", "limit": 1000}, signed=True)
print(f"  incomeType=FUNDING_FEE, NO time params (venue default 7d): n={len(r) if isinstance(r,list) else r}")

print("\n=== T4b: alias sweep — every documented incomeType, whole retention ===")
TYPES = ["TRANSFER","WELCOME_BONUS","REALIZED_PNL","FUNDING_FEE","COMMISSION","INSURANCE_CLEAR",
         "REFERRAL_KICKBACK","COMMISSION_REBATE","API_REBATE","CONTEST_REWARD",
         "CROSS_COLLATERAL_TRANSFER","OPTIONS_PREMIUM_FEE","OPTIONS_SETTLE_PROFIT",
         "INTERNAL_TRANSFER","AUTO_EXCHANGE","DELIVERED_SETTELMENT","COIN_SWAP_DEPOSIT",
         "COIN_SWAP_WITHDRAW","POSITION_LIMIT_INCREASE_FEE","FUNDING","FUNDING_RATE"]
for t in TYPES:
    r = get("/fapi/v1/income", {"incomeType": t, "startTime": floor90, "endTime": now, "limit": 1000}, signed=True)
    if isinstance(r, dict):
        print(f"  {t:32s} REJECTED  {r.get('body','')[:90]}")
    elif r:
        print(f"  {t:32s} n={len(r)}")
print("  (types not printed with n= returned 0 rows)")

print("\n=== T5: what is in the 198-row millisecond that production pagination truncated? ===")
ms = 1785025050000
r = get("/fapi/v1/income", {"startTime": ms, "endTime": ms, "limit": 1000}, signed=True)
print(f"  ms={ms} ({time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ms/1000))}) n={len(r)} "
      f"types={dict(Counter(x['incomeType'] for x in r))}")

print("\n=== T6: TRUE total by non-lossy chunked pull (2h chunks, none can hit limit=1000) ===")
allrows, t0 = [], now - 3*86400_000
step = 2*3600_000
cur = t0
maxed = 0
while cur < now:
    hi = min(cur + step - 1, now)
    r = get("/fapi/v1/income", {"startTime": cur, "endTime": hi, "limit": 1000}, signed=True)
    if isinstance(r, dict):
        print(f"  chunk error {r}"); break
    if len(r) >= 1000:
        maxed += 1
        print(f"  !! chunk {cur} hit limit ({len(r)}) — subdividing")
        for k in range(4):
            lo2 = cur + k*(step//4); hi2 = min(lo2 + step//4 - 1, hi)
            r2 = get("/fapi/v1/income", {"startTime": lo2, "endTime": hi2, "limit": 1000}, signed=True)
            allrows.extend(r2)
            if len(r2) >= 1000: print(f"     !! subchunk still maxed {len(r2)}")
    else:
        allrows.extend(r)
    cur += step
uniq = {(x.get("tranId"), x["symbol"], x["income"], x["time"], x["incomeType"]) for x in allrows}
print(f"  chunked TRUE total (unique) = {len(uniq)}   vs production-style single-loop = 7903")
print(f"  types={dict(Counter(x[4] for x in uniq))}")

print("\n=== T7: WALLET RECONCILIATION — can funding hide OUTSIDE the income endpoint? ===")
acc = get("/fapi/v3/account", {}, signed=True)
if isinstance(acc, dict) and "__http_error__" in acc:
    acc = get("/fapi/v2/account", {}, signed=True)
usdt = None
for a in (acc.get("assets") or []):
    if a.get("asset") == "USDT": usdt = a
print(f"  totalWalletBalance={acc.get('totalWalletBalance')}  totalUnrealizedProfit={acc.get('totalUnrealizedProfit')}")
print(f"  USDT asset: walletBalance={usdt and usdt.get('walletBalance')} "
      f"unrealizedProfit={usdt and usdt.get('unrealizedProfit')}")
s_all = sum(float(x[2]) for x in uniq)
s_by = {}
for x in uniq: s_by[x[4]] = s_by.get(x[4], 0.0) + float(x[2])
print(f"  sum(ALL income rows, chunked) = {s_all:.8f}")
print(f"  by type: " + ", ".join(f"{k}={v:.6f}" for k,v in sorted(s_by.items())))
wb = float(acc.get("totalWalletBalance", "nan"))
print(f"  wallet - sum(income) = {wb - s_all:.8f}  "
      f"<- if ~0, EVERY cash movement in this account is itemised in /income; "
      f"a funding charge outside it would show up here as a residual")
json.dump({"wallet": wb, "sum_income": s_all, "by_type": s_by, "n_true": len(uniq)},
          open("/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/t7.json","w"), indent=1)
print(f"\n[calls={_calls[0]}]")
