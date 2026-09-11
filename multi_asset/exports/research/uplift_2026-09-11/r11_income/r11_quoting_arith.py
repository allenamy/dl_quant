#!/usr/bin/env python3
"""R11 MEMBER (iii) — how much of the -2.6573 bps adverse selection is CHOOSABLE.
ENV WHITELIST = EMPTY SET (asserted, E-0826-D). READ-ONLY on ~/dl_quant_live. No GPU, no network, no venue call.
Caliber matched to the desk's own readout device
  multi_asset/exports/live/exec_requote_behind_2026-09-05/analyse_requote_behind.py
  = plan-level intent-to-treat all-in cost vs mid_at_anchor, bps per unit INTENDED notional,
  EXCEPT the fee: that device used orders.fee_paid; this one uses fills.commission with the BNB
  conversion, because fee_paid is documented incomplete when the fee was charged in BNB
  (live/binance_executor.py L1696 note; and k_window_180_live memory: "fee_all_usdt 字段不可用").
Bootstrap: UTC-day block, 2000 resamples, numpy.default_rng([20260905,k]).
"""
import json, os, glob, hashlib
from datetime import datetime, timezone
from collections import defaultdict, Counter
import numpy as np

_real_get = os.environ.get
def _no_env(k, d=None): raise RuntimeError("E-0826-D violation: env read %r; whitelist EMPTY" % k)
os.environ.get = _no_env

LOG = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r11_income"
SEED, NBOOT = 20260905, 2000
def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()[:16]
R = {"device": "r11_quoting_arith.py", "env_whitelist": [], "gpu_used": False, "network": False,
     "live_touched_write": False, "self_sha256": sha16(os.path.abspath(__file__))}
days = sorted(d for d in os.listdir(LOG) if d.isdigit())
def rd(day, fn):
    p = f"{LOG}/{day}/{fn}"
    if not os.path.exists(p): return
    for l in open(p):
        try: yield json.loads(l)
        except Exception: pass

bnb = {}
for d in days:
    for r in rd(d, "anchors.jsonl"):
        mv = r.get("mid_at_anchor_vector")
        if isinstance(mv, str):
            try: mv = json.loads(mv)
            except Exception: mv = {}
        if mv and mv.get("BNBUSDT"): bnb[float(r["anchor_ts"])] = float(mv["BNBUSDT"])
bts = sorted(bnb)
def bnbpx(t): return bnb[min(bts, key=lambda k: abs(k - t))] if bts else 0.0
def feeu(r):
    c = float(r.get("commission") or 0.0)
    return c * bnbpx(float(r.get("anchor_ts") or 0)) if (r.get("commission_asset") == "BNB") else c

# ---- fills deduped, indexed by (anchor_ts, symbol) --------------------------------------------
F = {}
for d in days:
    for r in rd(d, "fills.jsonl"):
        k = (r["symbol"], r["trade_id"]); cur = F.get(k)
        if cur is None: F[k] = r; continue
        if r.get("mid_at_fill_plus_60s") is not None and cur.get("mid_at_fill_plus_60s") is None: F[k] = r
BY = defaultdict(list)
for r in F.values(): BY[(r.get("anchor_ts"), r.get("symbol"))].append(r)

# ---- plans: attempt-1 maker rows carry the randomised placement arm ---------------------------
plans = {}
reject_by_arm = defaultdict(lambda: Counter())
for d in days:
    for r in rd(d, "orders.jsonl"):
        if r.get("order_type") != "maker" or int(r.get("attempt_idx") or 1) != 1: continue
        k = (r.get("anchor_ts"), r.get("symbol"))
        p = plans.setdefault(k, dict(day=d, arm=None, intended=None, mid=None, side=None, reasons=[]))
        p["arm"] = p["arm"] or r.get("placement_arm")
        if p["intended"] is None and r.get("intended_notional"): p["intended"] = abs(float(r["intended_notional"]))
        if p["mid"] is None and r.get("mid_at_anchor"): p["mid"] = float(r["mid_at_anchor"])
        if p["side"] is None and r.get("side"): p["side"] = r.get("side")
        p["reasons"].append(r.get("terminal_reason"))
        if r.get("placement_arm") in ("join", "behind"):
            reject_by_arm[(d, r["placement_arm"])][r.get("terminal_reason")] += 1

ARMS = ("join", "behind")
recs = []
for k, p in plans.items():
    if p["arm"] not in ARMS: continue
    if not p["intended"] or not p["mid"] or not p["side"]: continue
    if p["intended"] <= 0: continue
    s = 1.0 if p["side"] == "buy" else -1.0
    cost = 0.0; filled = 0.0; mo_wn = 0.0; mo_w = 0.0; mk_fill = 0.0; tk_fill = 0.0
    for f in BY.get(k, []):
        ot = f.get("order_type")
        if ot == "protective_flatten": continue      # a different event (stop-loss), not this rebalance
        nz = abs(float(f.get("fill_notional") or 0.0)); px = float(f.get("fill_px") or 0.0)
        if nz <= 0 or px <= 0: continue
        cost += s * (px - p["mid"]) / p["mid"] * 1e4 * nz + feeu(f) * 1e4
        filled += nz
        (mk_fill, tk_fill) = (mk_fill + nz, tk_fill) if ot == "maker" else (mk_fill, tk_fill + nz)
        m60 = f.get("mid_at_fill_plus_60s")
        if m60 is not None:
            mo_wn += (s * (float(m60) - px) / px) * nz; mo_w += nz
    recs.append(dict(day=p["day"], arm=p["arm"], I=p["intended"], cost=cost, filled=filled,
                     mk=mk_fill, tk=tk_fill, mo_wn=mo_wn, mo_w=mo_w))

def summarise(sel):
    S = [x for x in recs if sel(x)]
    I = sum(x["I"] for x in S); C = sum(x["cost"] for x in S)
    fl = sum(x["filled"] for x in S); mw = sum(x["mo_w"] for x in S); mn = sum(x["mo_wn"] for x in S)
    return dict(n_plans=len(S), intended=round(I, 2), filled=round(fl, 2),
                fill_rate=round(fl / I, 4) if I else None,
                itt_cost_bps_per_unit_intended=round(C / I, 4) if I else None,
                cost_bps_per_unit_filled=round(C / fl, 4) if fl else None,
                maker_share_of_fills=round(sum(x["mk"] for x in S) / fl, 4) if fl else None,
                markout60_bps=round(mn / mw * 1e4, 4) if mw else None)
R["ARM_SUMMARY"] = {a: summarise(lambda x, a=a: x["arm"] == a) for a in ARMS}

# ---- UTC-day block bootstrap on the paired arm difference -------------------------------------
bydayarm = defaultdict(lambda: {a: [0.0, 0.0] for a in ARMS})   # day -> arm -> [cost, intended]
for x in recs: bydayarm[x["day"]][x["arm"]][0] += x["cost"]; bydayarm[x["day"]][x["arm"]][1] += x["I"]
dl = sorted(bydayarm)
def ratio(idx, a):
    c = sum(bydayarm[dl[i]][a][0] for i in idx); q = sum(bydayarm[dl[i]][a][1] for i in idx)
    return c / q if q > 0 else np.nan
pt = {a: ratio(range(len(dl)), a) for a in ARMS}
diff_pt = pt["behind"] - pt["join"]
bs = []
for kk in range(NBOOT):
    rng = np.random.default_rng([SEED, kk])
    idx = rng.integers(0, len(dl), len(dl))
    v = ratio(idx, "behind") - ratio(idx, "join")
    if v == v: bs.append(v)
bs = np.array(bs)
R["ARM_ITT_DIFF_behind_minus_join"] = {
    "unit": "bps per unit INTENDED notional; POSITIVE = behind is MORE EXPENSIVE",
    "point": round(diff_pt, 4), "CI95": [round(np.percentile(bs, 2.5), 4), round(np.percentile(bs, 97.5), 4)],
    "n_days": len(dl), "n_boot": len(bs),
    "join_cost": round(pt["join"], 4), "behind_cost": round(pt["behind"], 4)}
# markout difference, same block bootstrap
bydayarm_mo = defaultdict(lambda: {a: [0.0, 0.0] for a in ARMS})
for x in recs: bydayarm_mo[x["day"]][x["arm"]][0] += x["mo_wn"]; bydayarm_mo[x["day"]][x["arm"]][1] += x["mo_w"]
def moratio(idx, a):
    n = sum(bydayarm_mo[dl[i]][a][0] for i in idx); w = sum(bydayarm_mo[dl[i]][a][1] for i in idx)
    return n / w * 1e4 if w > 0 else np.nan
mpt = {a: moratio(range(len(dl)), a) for a in ARMS}
mbs = []
for kk in range(NBOOT):
    rng = np.random.default_rng([SEED, kk]); idx = rng.integers(0, len(dl), len(dl))
    v = moratio(idx, "behind") - moratio(idx, "join")
    if v == v: mbs.append(v)
mbs = np.array(mbs)
R["ARM_MARKOUT_DIFF_behind_minus_join"] = {
    "unit": "bps markout60; NEGATIVE = behind is MORE adversely selected",
    "point": round(mpt["behind"] - mpt["join"], 4),
    "CI95": [round(np.percentile(mbs, 2.5), 4), round(np.percentile(mbs, 97.5), 4)],
    "join_markout": round(mpt["join"], 4), "behind_markout": round(mpt["behind"], 4)}

# ---- reject rate by arm, over time ------------------------------------------------------------
rr = defaultdict(lambda: Counter())
for (d, a), c in reject_by_arm.items():
    rr[a][ "n"] += sum(c.values()); rr[a]["rej"] += c.get("venue_reject", 0)
R["REJECT_RATE_by_arm_whole_window"] = {a: {"n_attempt1_maker_lines": rr[a]["n"], "venue_reject": rr[a]["rej"],
    "reject_rate": round(rr[a]["rej"] / rr[a]["n"], 4)} for a in ARMS}
wk = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for (d, a), c in reject_by_arm.items():
    wk[d[:6] + ("A" if int(d[6:]) <= 10 else ("B" if int(d[6:]) <= 20 else "C"))][a][0] += sum(c.values())
    wk[d[:6] + ("A" if int(d[6:]) <= 10 else ("B" if int(d[6:]) <= 20 else "C"))][a][1] += c.get("venue_reject", 0)
R["REJECT_RATE_by_arm_by_third_of_month"] = {p: {a: (round(v[a][1] / v[a][0], 4) if v[a][0] else None)
    for a in ARMS} for p, v in sorted(wk.items())}
# resting time
rest = []
for d in days:
    for r in rd(d, "orders.jsonl"):
        if r.get("submit_ts") and r.get("cancel_ts"): rest.append(float(r["cancel_ts"]) - float(r["submit_ts"]))
rest = np.array(rest)
R["QUOTE_WINDOW_MEASURED"] = {"n": len(rest), "median_s": round(float(np.median(rest)), 1),
    "p10_s": round(float(np.percentile(rest, 10)), 1), "p90_s": round(float(np.percentile(rest, 90)), 1),
    "config_k_seconds": 900,
    "CORRECTION": "the live quote window is k=900s (measured median rest 970.8s = k + ~70s latency), "
                  "NOT the 180s named in the task brief. 180 was deployed and rolled back 2026-08-10 with "
                  "ZERO anchors run at 180 (config/book.json _k_seconds_rollback_2026_08_10; memory "
                  "maker_slippage_is_negative)."}
json.dump(R, open(f"{OUT}/receipts/RECEIPT_r11_M3_quoting.json", "w"), indent=1)
os.environ.get = _real_get
print(json.dumps(R, indent=1))
