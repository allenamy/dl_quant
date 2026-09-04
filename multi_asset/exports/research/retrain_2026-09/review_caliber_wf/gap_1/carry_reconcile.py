"""GAP#1 carry reconcile on the 52 T-GT live windows. READ-ONLY on ~/wide_shadow and ~/dl_quant_live.
Rates: producer ledger_tail (aux.json) = [ft, rate, iv] per symbol (last 400 settlements, fed by /fapi/v1/fundingRate).
device formula (w10_universe.py L280 / shadow_loop_v3.py L528): car = sum(w * r_last(N) * (4/iv)) * 1e4, positive = book pays.
settlement rule (venue): charge = sum over settlements ft in (N, N+4h] of notional * rate, on positions held at ft.
live: funding_usd from T-GT rows (sum funding_paid, settlement_ts in (N, N+4h]); funding_paid<0 = account paid.
"""
import json, os, time, sys, numpy as np
SP = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber"
WS = "/Users/haosiyu/wide_shadow"; PL = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
def fmt(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(float(t)))
rep = json.load(open(f"{SP}/gt/live_reconcile_report.json")); rows = rep["rows"]
aux = json.load(open(f"{WS}/state/aux.json")); LT = aux["ledger_tail"]
# position readback (realized notional at the post-anchor read)
RB = {}
for d in sorted(os.listdir(PL)):
    p = f"{PL}/{d}/position_readback.jsonl"
    if d.isdigit() and d >= "20260825" and os.path.exists(p):
        for r in (json.loads(x) for x in open(p) if x.strip()):
            RB.setdefault(float(r["anchor_ts"]), {})[r["symbol"]] = (float(r["venue_position_qty"]), float(r["venue_position_notional"]))
A = {}
for d in sorted(os.listdir(PL)):
    p = f"{PL}/{d}/anchors.jsonl"
    if d.isdigit() and d >= "20260825" and os.path.exists(p):
        for r in (json.loads(x) for x in open(p) if x.strip()):
            eb = r.get("external_book") or {}; nom = eb.get("nominal_ts") if isinstance(eb, dict) else None
            at = float(r["anchor_ts"]); N = int(nom) if nom is not None else int(at // 14400 * 14400)
            A[N] = at
def r_last(sym, N):
    led = LT.get(sym)
    if not led: return None
    best = None
    for ft, rate, iv in led:
        if ft <= N: best = (ft, rate, iv)
        else: break
    if best is None: return None
    if N - best[0] > 12 * 3600: return ("stale", best)
    return best
def settles(sym, N):
    led = LT.get(sym) or []
    return [(ft, rate, iv) for ft, rate, iv in led if N < ft <= N + 14400]
out = []
miss_syms = set()
for x in rows:
    N = int(x["N"]); doc = json.load(open(f"{WS}/state/target_live/{N}.json")); w = doc["weights"]
    g = sum(abs(v) for v in w.values())
    dev = 0.0; setl = 0.0; n_stale = 0; n_miss = 0; g_miss = 0.0; n8 = 0; n_settle_rows = 0
    for s, v in w.items():
        rl = r_last(s, N)
        if rl is None: n_miss += 1; g_miss += abs(v); miss_syms.add(s); continue
        if rl[0] == "stale": n_stale += 1; continue
        ft, rate, iv = rl
        dev += v * rate * (4.0 / iv)
        for ft2, rate2, iv2 in settles(s, N):
            setl += v * rate2; n_settle_rows += 1
    dev_bps = dev / g * 1e4; set_bps = setl / g * 1e4
    # realized positions (readback at the post-anchor read of N) x device rule / x settlement rule, denominator realized_gross
    pos = RB.get(A[N], {}); rg = x["realized_gross"]
    dev_real = 0.0; set_real = 0.0; g_rb = 0.0
    for s, (q, nt) in pos.items():
        if q == 0: continue
        g_rb += abs(nt)
        rl = r_last(s, N)
        if rl is None or rl[0] == "stale": continue
        ft, rate, iv = rl
        dev_real += nt * rate * (4.0 / iv)
        for ft2, rate2, iv2 in settles(s, N): set_real += nt * rate2
    live_pays = -x["funding_usd"] / rg * 1e4
    out.append({"N": N, "when": x["when"], "g_target": g, "rg": rg, "g_rb": g_rb, "n_names": len(w), "n_stale": n_stale, "n_miss": n_miss, "g_miss_frac": g_miss / g,
                "dev_target": dev_bps, "settle_target": set_bps, "dev_real": dev_real / rg * 1e4, "settle_real": set_real / rg * 1e4,
                "live_pays": live_pays, "n_settle_rows": n_settle_rows})
def st(a): a = np.array(a, float); return f"mean {a.mean():+.3f} sd {a.std(ddof=1):.3f} se {a.std(ddof=1)/np.sqrt(len(a)):.3f} n {len(a)}"
print("windows", len(out), "missing-ledger symbols", sorted(miss_syms)[:20], len(miss_syms))
print("sign convention below: POSITIVE = book pays (device carry_ex convention); live_pays = -funding_usd/realized_gross*1e4")
for k in ("dev_target", "settle_target", "dev_real", "settle_real", "live_pays"):
    print(f"{k:14s}", st([o[k] for o in out]))
gap = [o["live_pays"] - o["dev_target"] for o in out]; print("gap live_pays - dev_target :", st(gap))
gap2 = [o["live_pays"] - o["settle_target"] for o in out]; print("gap live_pays - settle_target:", st(gap2))
gap3 = [o["settle_target"] - o["dev_target"] for o in out]; print("gap settle_target - dev_target (rate staleness + pro-rata):", st(gap3))
gap4 = [o["dev_real"] - o["dev_target"] for o in out]; print("gap dev_real - dev_target (weights: realized vs target):", st(gap4))
gap5 = [o["live_pays"] - o["settle_real"] for o in out]; print("gap live_pays - settle_real (readback notional x window settlements vs venue income):", st(gap5))
# excluding the 4x rebuild anchors (rg > 100k)
sub = [o for o in out if o["rg"] < 100000]
print("--- x1 period only (rg<100k), n", len(sub))
for k in ("dev_target", "settle_target", "dev_real", "settle_real", "live_pays"):
    print(f"{k:14s}", st([o[k] for o in sub]))
print("gap live_pays - dev_target (x1):", st([o["live_pays"] - o["dev_target"] for o in sub]))
# 27-anchor overlap 08-26 04Z -> 08-30 20Z (replay meta ends 08-30 20Z)
ov = [o for o in out if 1787716800 <= o["N"] <= 1788120000]
print("--- overlap 08-26 04Z..08-30 20Z n", len(ov))
for k in ("dev_target", "settle_target", "live_pays"):
    print(f"{k:14s}", st([o[k] for o in ov]))
print("mean g_target", np.mean([o["g_target"] for o in out]), "mean rg", np.mean([o["rg"] for o in out]), "mean g_rb/rg", np.mean([o["g_rb"]/o["rg"] for o in out]))
print("stale names mean", np.mean([o["n_stale"] for o in out]), "miss names mean", np.mean([o["n_miss"] for o in out]), "g_miss_frac mean", np.mean([o["g_miss_frac"] for o in out]))
print("annualised: bps/anchor x 2190/100 = %/gross/yr:  dev_target", np.mean([o["dev_target"] for o in out])*21.9, " live_pays", np.mean([o["live_pays"] for o in out])*21.9, " gap", np.mean(gap)*21.9)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "carry_reconcile_rows.json"), "w"), indent=1)
print("N | when | dev_t | settle_t | dev_real | settle_real | live_pays | rg | stale | miss")
for o in out: print(f"{o['N']} {o['when']} {o['dev_target']:+6.2f} {o['settle_target']:+6.2f} {o['dev_real']:+6.2f} {o['settle_real']:+6.2f} {o['live_pays']:+6.2f} {o['rg']:8.0f} {o['n_stale']} {o['n_miss']}")
