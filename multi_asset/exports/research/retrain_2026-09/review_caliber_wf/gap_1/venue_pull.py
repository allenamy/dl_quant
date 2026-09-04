"""Second instrument: public /fapi/v1/fundingRate history for every symbol in any of the 52 target_live files, 08-24 00Z -> now. Public endpoint, no key."""
import json, os, time, urllib.request, urllib.parse
SP = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber"
WS = "/Users/haosiyu/wide_shadow"
rows = json.load(open(f"{SP}/gt/live_reconcile_report.json"))["rows"]
syms = set()
for x in rows:
    syms |= set(json.load(open(f"{WS}/state/target_live/{int(x['N'])}.json"))["weights"])
syms = sorted(syms); print("symbols", len(syms), flush=True)
def get(path, params):
    u = "https://fapi.binance.com" + path + "?" + urllib.parse.urlencode(params)
    for k in range(4):
        try:
            with urllib.request.urlopen(u, timeout=20) as r: return json.loads(r.read())
        except Exception as e:
            time.sleep(1.5 * (k + 1)); err = e
    return {"_err": repr(err)}
out = {}; t0 = 1787529600 * 1000; t1 = int(time.time() * 1000)
for i, s in enumerate(syms):
    r = get("/fapi/v1/fundingRate", {"symbol": s, "startTime": t0, "endTime": t1, "limit": 1000})
    out[s] = r if isinstance(r, list) else {"_err": str(r)}
    if i % 50 == 0: print(i, s, len(r) if isinstance(r, list) else r, flush=True)
    time.sleep(0.05)
info = get("/fapi/v1/fundingInfo", {})
json.dump({"pulled_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rates": out, "fundingInfo": info}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "venue_funding_rates.json"), "w"))
print("done", sum(1 for v in out.values() if isinstance(v, list)), "ok;", sum(1 for v in out.values() if not isinstance(v, list)), "err")
