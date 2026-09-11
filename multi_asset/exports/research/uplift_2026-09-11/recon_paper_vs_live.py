#!/usr/bin/env python3
"""Reconcile producer paper score vs deployed-book paper score vs realized live P&L.
READ-ONLY on ~/wide_shadow and ~/dl_quant_live."""
import json, os, glob, time
import numpy as np

WS = "/Users/haosiyu/wide_shadow"
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"

cfg = json.load(open(f"{WS}/shadow_bundle/config.json"))
SYMS = cfg["symbols_panel"]; NW = len(SYMS)
R = np.load(f"{WS}/state/rolling.npz", allow_pickle=True)
rts = R["ts"].astype(np.int64); RD = R["data"]
row_of = {int(t): i for i, t in enumerate(rts)}

def y4(anchor):
    """EXACT replica of shadow_loop_v3.py L427-431: seg=CDf[pi+1:ai+1,:,0]; sum finite; NaN if <46 of 48."""
    pi = row_of.get(int(anchor)); ai = row_of.get(int(anchor) + 14400)
    if pi is None or ai is None: return None
    seg = RD[pi + 1:ai + 1, :, 0].astype(np.float32)
    fin = np.isfinite(seg)
    v = np.where(fin, seg, 0).sum(0).astype(np.float64)
    v[fin.sum(0) < 46] = np.nan
    return v

def gbps(w, yv):
    return float((w * np.nan_to_num(yv, nan=0.0)).sum() * 1e4)

# ---- logged score events
score = {}
for line in open(f"{WS}/shadow_log.jsonl"):
    try: d = json.loads(line)
    except Exception: continue
    if d.get("e") == "score": score[int(d["anchor_ts"])] = d

rows = []
for A in sorted(score):
    yv = y4(A)
    if yv is None: continue
    rec = {"anchor": A, "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A)),
           "logged_gross": score[A]["gross_bps"], "logged_net": score[A]["net_bps"],
           "carry": score[A]["carry_bps"], "cost": score[A]["cost_bps"]}
    # scored vector = state/weights/<A>.npz  (st.H, the 3-leg king book)
    wp = f"{WS}/state/weights/{A}.npz"
    if os.path.exists(wp):
        z = np.load(wp); wk = np.zeros(NW); wk[z["idx"].astype(np.int64)] = z["val"].astype(np.float64)
        rec["repro_king_gross"] = gbps(wk, yv); rec["king_gross_norm"] = float(np.abs(wk).sum())
        rec["king_net_w"] = float(wk.sum())
    # deployed vector = state/target_live/<A>.json
    tp = f"{WS}/state/target_live/{A}.json"
    if os.path.exists(tp):
        d = json.load(open(tp)); wd = np.zeros(NW)
        idx = {s: j for j, s in enumerate(SYMS)}
        miss = 0
        for s, v in d["weights"].items():
            j = idx.get(s)
            if j is None: miss += 1; continue
            wd[j] = float(v)
        rec["deployed_producer"] = d.get("producer", "shadow_loop_v3")[:28]
        rec["deployed_gross_norm"] = float(np.abs(wd).sum())
        rec["deployed_net_w"] = float(wd.sum())
        rec["deployed_gross_bps"] = gbps(wd, yv)
        rec["deployed_miss_syms"] = miss
        rec["n_deployed"] = int((np.abs(wd) > 1e-12).sum())
        # cos similarity between scored and deployed
        if "repro_king_gross" in rec:
            den = np.linalg.norm(wk) * np.linalg.norm(wd)
            rec["cos_king_deployed"] = float(wk @ wd / den) if den > 0 else None
            rec["l1_diff"] = float(np.abs(wk - wd).sum())
    # king backup file (what the producer would have deployed)
    kp = f"{WS}/state/target_live_king/{A}.json"
    if os.path.exists(kp):
        d = json.load(open(kp)); wkf = np.zeros(NW)
        idx = {s: j for j, s in enumerate(SYMS)}
        for s, v in d["weights"].items():
            j = idx.get(s)
            if j is not None: wkf[j] = float(v)
        rec["kingfile_gross_bps"] = gbps(wkf, yv)
    rows.append(rec)

json.dump(rows, open(f"{OUT}/recon_anchor_table.json", "w"), indent=1)

import statistics as st_
def summ(tag, sub, keys):
    print(f"\n== {tag}  n={len(sub)}")
    for k in keys:
        v = [r[k] for r in sub if r.get(k) is not None]
        if not v: print(f"  {k:24s} -- none"); continue
        print(f"  {k:24s} mean {np.mean(v):9.4f}  sd {np.std(v,ddof=1) if len(v)>1 else 0:8.3f}  n {len(v)}")

COMBO0 = 1787716800  # 2026-08-26 04:00Z
all_r = rows
combo = [r for r in rows if r["anchor"] >= COMBO0]
keys = ["logged_gross", "repro_king_gross", "kingfile_gross_bps", "deployed_gross_bps",
        "logged_net", "carry", "cost", "king_gross_norm", "deployed_gross_norm",
        "deployed_net_w", "cos_king_deployed", "l1_diff"]
summ("ALL", all_r, keys)
summ("COMBO ERA (>=2026-08-26 04:00Z)", combo, keys)

# repro fidelity
d = [(r["repro_king_gross"] - r["logged_gross"]) for r in rows if "repro_king_gross" in r]
print(f"\nrepro vs logged gross_bps: n={len(d)} max|diff|={max(abs(x) for x in d):.4f} mean diff={np.mean(d):.5f}")
bad = [(r["utc"], r["logged_gross"], r["repro_king_gross"]) for r in rows
       if "repro_king_gross" in r and abs(r["repro_king_gross"] - r["logged_gross"]) > 0.05]
print("mismatches>0.05bps:", len(bad), bad[:8])
