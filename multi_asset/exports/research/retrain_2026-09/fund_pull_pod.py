"""全量 funding 历史拉取 @pod(2026-09-01 重训战役): /fapi/v1/fundingRate 分页, 829名, ≤4req/s;
产物 /workspace/fund_aug.json.gz = {"rates":{sym:[[t_ms,rate],...]},"intervals":{}} — panel_ext 的 AUG 全量形态."""
import json, gzip, time, urllib.request, urllib.parse

SY = open('/workspace/panel_symbols_wide.txt').read().strip().split('|')
BASE = "https://fapi.binance.com/fapi/v1/fundingRate"
rates = {}
t0 = time.time(); calls = 0
for i, s in enumerate(SY):
    rows = []; start = 1638316800000  # 2021-12-01
    while True:
        q = urllib.parse.urlencode({"symbol": s, "startTime": start, "limit": 1000})
        try:
            with urllib.request.urlopen(f"{BASE}?{q}", timeout=20) as r:
                d = json.loads(r.read())
        except Exception as e:
            print(s, "ERR", e, flush=True); d = []
        calls += 1
        el = time.time() - t0
        if calls / max(el, 1e-9) > 3.5: time.sleep(calls / 3.5 - el)
        if not d: break
        for row in d:
            rows.append([int(row["fundingTime"]), float(row["fundingRate"])])
        if len(d) < 1000: break
        start = int(d[-1]["fundingTime"]) + 1
    if rows: rates[s] = rows
    if (i + 1) % 100 == 0: print("sym", i + 1, "calls", calls, flush=True)
out = {"rates": rates, "intervals": {}}
with gzip.open("/workspace/fund_aug.json.gz", "wt") as f:
    json.dump(out, f)
print("FUND_PULL_DONE", len(rates), "syms", calls, "calls", flush=True)
