#!/usr/bin/env python3
"""t5d_prefreeze_scan.py — pod2, READ-ONLY, structural scan BEFORE the T5d prereg (no price / carry / book number).
For every panel symbol: the funding event stream of the x0910 tail as r6_panel_splice.py assigns it (AUG + SEP REST rows with the fetch-time
interval), versus the interval implied by consecutive settlement timestamps. Counts calendar cells (2026-08-30 04Z..09-10 00Z) whose in-force
settlement interval differs, per row and per name, separately for incumbent rows (<= 08-31 00Z) and x0910 tail rows; lists names whose tail
events carry any interval mismatch (their v1 EMA differs from the first such event).
"""
import os, sys, json, gzip, time, hashlib
import numpy as np
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
def snap(x): return ALLOWED[np.argmin(np.abs(np.asarray(x, float)[:, None] - ALLOWED[None, :]), axis=1)]
PX = np.load("/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz", allow_pickle=True)
syms = [str(s) for s in PX["symbols"]]; ts = PX["ts"].astype(np.int64); row = {int(t): i for i, t in enumerate(ts)}
IV = PX["f_fund_iv"]; FN = PX["f_fund_now"]
CUT = 1788134400; CAL = [1788062400 + 14400 * k for k in range(66)]
SEP = json.loads(gzip.open("/workspace/uplift_2026-09-11/r6/dl/r6_fund_sep.json.gz", "rt").read()); AUG = json.loads(gzip.open("/workspace/fund_aug.json.gz", "rt").read())
SEP_IV = {k: float(v) for k, v in (SEP.get("intervals") or {}).items() if v}; AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v}
cells = {"incumbent": 0, "tail": 0}; cells_fn = {"incumbent": 0, "tail": 0}; per_row = {}; names_cells = {}; ema_names = []; n_checked = {"incumbent": 0, "tail": 0}
for j, s in enumerate(syms):
    ev = {}
    for t_ms, r in (AUG.get("rates") or {}).get(s, []): ev[int(t_ms) // 1000] = (float(r), AUG_IV.get(s, np.nan))
    for t_ms, r in (SEP.get("rates") or {}).get(s, []): ev[int(t_ms) // 1000] = (float(r), SEP_IV.get(s, np.nan))
    if not ev: continue
    ft = np.array(sorted(ev), np.int64); fr = np.array([ev[t][0] for t in ft]); fiv = np.array([ev[t][1] for t in ft])
    g = np.full(len(ft), np.nan); g[1:] = np.round(np.diff(ft) / 3600.0)
    ivtrue = np.where(np.isfinite(g) & (g > 0) & (g <= 24), g, np.nan)
    ivtrue = np.where(np.isfinite(ivtrue), snap(np.nan_to_num(ivtrue, nan=8.0)), np.nan)
    tail_ev = (ft > CUT) & np.isfinite(ivtrue) & np.isfinite(fiv)
    if (tail_ev & (snap(np.nan_to_num(fiv, nan=8.0)) != ivtrue)).any(): ema_names.append(s)
    for A in CAL:
        p = int(np.searchsorted(ft, A, side="right")) - 1
        if p < 1 or A - ft[p] > 12 * 3600 or not np.isfinite(ivtrue[p]): continue
        seg = "incumbent" if A <= CUT else "tail"; i = row[A]
        if not np.isfinite(IV[i, j]): continue
        n_checked[seg] += 1
        if float(IV[i, j]) != float(ivtrue[p]):
            cells[seg] += 1; per_row[U(A)] = per_row.get(U(A), 0) + 1; names_cells.setdefault(s, []).append(U(A))
        if np.isfinite(FN[i, j]) and float(np.float32(fr[p])) != float(FN[i, j]): cells_fn[seg] += 1
out = dict(label="structural scan before T5d prereg; no outcome numbers", cells_checked=n_checked, iv_mismatch_cells=cells, fn_mismatch_cells=cells_fn,
           per_row=per_row, names=sorted(names_cells), n_names=len(names_cells), cells_per_name={s: len(v) for s, v in names_cells.items()},
           first_last_per_name={s: [v[0], v[-1]] for s, v in names_cells.items()}, tail_ema_affected_names=sorted(ema_names), n_tail_ema_affected=len(ema_names),
           sep_meta=SEP.get("meta"), panel_sha256=hashlib.sha256(open("/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz", "rb").read()).hexdigest())
print(json.dumps(out, indent=1))
