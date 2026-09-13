#!/usr/bin/env python3
"""t7_pull_identity_guard.py — rolling per-pair price-identity guard over the full pulled history (rules frozen in plan 'identity_guard').
r(t) = ln(Pkrw_i/Pkrw_BTC) - ln((Pidx_i/mult)/Pidx_BTC) on hours where all four bars exist; daily median d (>= 6 hours); trailing medians m30 (>= 10 days) and m7 (>= 3 days).
FLAG_DIVERGE: |m30| > ln 1.25. FLAG_SCALE_SUSPECT: |m30| > ln 4 or |m7(day) - m7(day-14)| > ln 4. Flags only; nothing is dropped.
Reports per pair: hours checked, checked day range, merged flagged day ranges, extreme |m30| inside flagged ranges (none reported for unflagged pairs).
Reads <root>/derived (written by t7_pull_checks.py). Output <root>/checks/IDENTITY_GUARD_T7_pull.json. No returns are computed."""
import os, json, math, hashlib, argparse, time, collections
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); A = ap.parse_args(); ROOT = A.root
_pb = open(ROOT + "/plan/PULL_PLAN_FROZEN.json", "rb").read(); assert hashlib.sha256(_pb).hexdigest() == open(ROOT + "/plan/PULL_PLAN_FROZEN.json.sha256").read().split()[0]
PLAN = json.loads(_pb)
L125, L4 = math.log(1.25), math.log(4.0)
def iso_d(t): return time.strftime("%Y-%m-%d", time.gmtime(int(t)))
def load(p):
    if not os.path.exists(p): return None
    z = np.load(p); return dict(zip(z["open_s"].tolist(), z["close"].tolist()))
def ranges(days):
    out = []
    for d in sorted(days):
        if out and d - out[-1][1] <= 86400: out[-1][1] = d
        else: out.append([d, d])
    return out
res = {"device": os.path.basename(__file__), "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "plan_sha256": hashlib.sha256(_pb).hexdigest(), "pairs": [], "summary": {}}
BIN_BTC = load(ROOT + "/derived/binance/BTCUSDT.npz")
cnt = collections.Counter()
for v in ("upbit", "bithumb"):
    KBTC = load(ROOT + "/derived/%s/KRW-BTC_60m.npz" % v)
    for p in [q for q in PLAN["pairs"] if q["venue"] == v]:
        rec = {"venue": v, "symbol": p["symbol"], "market": p["market"], "mult": p["mult"], "rule": p["rule"]}
        K = load(ROOT + "/derived/%s/%s_60m.npz" % (v, p["market"])); B = load(ROOT + "/derived/binance/%s.npz" % p["symbol"])
        if K is None or B is None or KBTC is None or BIN_BTC is None:
            rec["status"] = "NO_DATA"; rec["missing"] = [n for n, x in (("krw", K), ("binance", B), ("krw_btc", KBTC), ("binance_btc", BIN_BTC)) if x is None]
            res["pairs"].append(rec); cnt["NO_DATA"] += 1; continue
        hrs = sorted(set(K) & set(B) & set(KBTC) & set(BIN_BTC))
        rec["n_hours_checked"] = len(hrs)
        if not hrs: rec["status"] = "NO_OVERLAP"; res["pairs"].append(rec); cnt["NO_OVERLAP"] += 1; continue
        byday = collections.defaultdict(list)
        for t in hrs:
            r = math.log(K[t] / KBTC[t]) - math.log((B[t] / p["mult"]) / BIN_BTC[t]); byday[(t // 86400) * 86400].append(r)
        d = {k: float(np.median(x)) for k, x in byday.items() if len(x) >= 6}
        days = sorted(d); rec["checked_days"] = len(days); rec["checked_range"] = [iso_d(days[0]), iso_d(days[-1])] if days else None
        def trailing(day, n, need):
            vals = [d[k] for k in range(day - (n - 1) * 86400, day + 1, 86400) if k in d]
            return float(np.median(vals)) if len(vals) >= need else None
        div, scl, ext = set(), set(), 0.0
        m7 = {day: trailing(day, 7, 3) for day in days}
        for day in days:
            m30 = trailing(day, 30, 10)
            if m30 is not None and abs(m30) > L125: div.add(day); ext = max(ext, abs(m30))
            if m30 is not None and abs(m30) > L4: scl.add(day)
            a, b = m7.get(day), m7.get(day - 14 * 86400)
            if a is not None and b is not None and abs(a - b) > L4: scl.add(day)
        rec["status"] = "FLAG_SCALE_SUSPECT" if scl else ("FLAG_DIVERGE" if div else "PASS")
        if div: rec["diverge_ranges"] = [[iso_d(a), iso_d(b), int((b - a) // 86400) + 1] for a, b in ranges(div)]; rec["extreme_abs_m30_in_flagged"] = round(ext, 3)
        if scl: rec["scale_suspect_ranges"] = [[iso_d(a), iso_d(b), int((b - a) // 86400) + 1] for a, b in ranges(scl)]
        res["pairs"].append(rec); cnt[rec["status"]] += 1
res["summary"] = {"n_pairs": len(res["pairs"]), "by_status": dict(cnt),
                  "flagged": [(q["venue"], q["symbol"], q["market"], q["status"]) for q in res["pairs"] if q["status"] not in ("PASS",)]}
json.dump(res, open(ROOT + "/checks/IDENTITY_GUARD_T7_pull.json", "w"), indent=1)
print(json.dumps(res["summary"], indent=1)[:4000])
