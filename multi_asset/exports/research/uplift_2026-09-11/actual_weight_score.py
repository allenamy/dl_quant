#!/usr/bin/env python3
"""Score the ACTUAL live position vector on the SAME panel/window as the producer's scorer,
to separate (b) fill/weight shortfall from (e) price-instrument/timing."""
import json, glob, os, time
import numpy as np
WS = "/Users/haosiyu/wide_shadow"; PL = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); SYMS = cfg["symbols_panel"]; NW = len(SYMS)
IDX = {s: j for j, s in enumerate(SYMS)}
R = np.load(f"{WS}/state/rolling.npz", allow_pickle=True)
rts = R["ts"].astype(np.int64); RD = R["data"]; row_of = {int(t): i for i, t in enumerate(rts)}
def y4(A):
    pi = row_of.get(int(A)); ai = row_of.get(int(A) + 14400)
    if pi is None or ai is None: return None
    seg = RD[pi+1:ai+1, :, 0].astype(np.float32); fin = np.isfinite(seg)
    v = np.where(fin, seg, 0).sum(0).astype(np.float64); v[fin.sum(0) < 46] = np.nan; return v

pos = {}
for d in sorted(glob.glob(f"{PL}/2026*")):
    p = f"{d}/position_readback.jsonl"
    if not os.path.exists(p): continue
    for l in open(p):
        r = json.loads(l)
        pos.setdefault(float(r["anchor_ts"]), {})[r["symbol"]] = float(r.get("venue_position_notional") or 0.0)

rows = []
for ets, book in sorted(pos.items()):
    A = int(ets // 14400 * 14400)
    yv = y4(A)
    if yv is None: continue
    tp = f"{WS}/state/target_live/{A}.json"
    if not os.path.exists(tp): continue
    dtl = json.load(open(tp))
    gross = sum(abs(v) for v in book.values())
    if gross <= 0: continue
    wa = np.zeros(NW); off_panel = 0.0
    for s, nt in book.items():
        j = IDX.get(s)
        if j is None: off_panel += abs(nt); continue
        wa[j] += nt / gross            # actual weights, sum|w| = 1 (minus off-panel)
    wd = np.zeros(NW); gd = 0.0
    for s, v in dtl["weights"].items():
        j = IDX.get(s)
        if j is not None: wd[j] = float(v); gd += abs(float(v))
    wdn = wd / gd if gd else wd        # deployed target normalised to sum|w|=1
    nanmask = ~np.isfinite(yv)
    rows.append({"A": A, "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A)),
        "gross_usdt": gross, "off_panel_frac": off_panel / gross,
        "paper_on_target_bps": float((wdn * np.nan_to_num(yv)).sum() * 1e4),
        "paper_on_actual_bps": float((wa * np.nan_to_num(yv)).sum() * 1e4),
        "l1_target_vs_actual": float(np.abs(wdn - wa).sum()),
        "cos_target_actual": float(wdn @ wa / (np.linalg.norm(wdn) * np.linalg.norm(wa))),
        "actual_gross_on_nan_names": float(np.abs(wa[nanmask]).sum()),
        "actual_net_w": float(wa.sum()), "target_net_w": float(wdn.sum())})
json.dump(rows, open(f"{OUT}/actual_weight_table.json", "w"), indent=1)
C = [r for r in rows if r["A"] >= 1787716800]
def a(k, sub=C): return np.array([x[k] for x in sub], float)
print("combo-era anchors with readback+target:", len(C), C[0]["utc"], "->", C[-1]["utc"])
for k in ("paper_on_target_bps", "paper_on_actual_bps", "l1_target_vs_actual", "cos_target_actual",
          "off_panel_frac", "actual_gross_on_nan_names", "actual_net_w", "target_net_w"):
    v = a(k); print(f"  {k:28s} mean {v.mean():9.4f}  sd {v.std(ddof=1):8.4f}")
print(f"  (b) target->actual weights delta  : {(a('paper_on_actual_bps')-a('paper_on_target_bps')).mean():+.4f} bps/anchor")
