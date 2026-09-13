#!/usr/bin/env python3
"""t1_h2b_dlposthoc.py — pod2, read-only. POST-HOC DESCRIPTIVE (not a registered reading; written after t1_h2b_train.py returned s0=0.74 for the DL files).
For the DL feature files: on iv==4 cells where stored fund_ema != float16(v0), describe stored/v0 and stored/v1 ratios and when those cells occur."""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x); assert sorted(k for k in os.environ if k not in WHITE) == [], sorted(os.environ)
import numpy as np
R = "/workspace/uplift_r2_2026-09-13/T1"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
P = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); pts = P["ts"].astype(np.int64); PSYM = [str(s) for s in P["symbols"]]; prow = {int(t): j for j, t in enumerate(pts)}
V0 = P["f_fund_ema"]; V1 = P["f_fund_ema_v1"]; IV = P["f_fund_iv"]; FN = P["f_fund_now"]
C0 = np.float16(np.nan_to_num(V0, nan=0.0)); C1 = np.float16(np.nan_to_num(V1, nan=0.0))
OUT = {}
for name, fea, tg in (("dl_ext_0901", "/workspace/dlw_ext/data/dlw_fea82.npz", "/workspace/dlw_ext/data/dlw_targets.npz"), ("dl_v4raw", "/workspace/dlw_v4raw/data/dlw_fea82.npz", "/workspace/dlw_v4raw/data/dlw_targets.npz")):
    Z = np.load(fea, allow_pickle=True); names = [str(x) for x in Z["names"]]; c = names.index("fund_ema"); cn = names.index("fund_now")
    T = np.load(tg, allow_pickle=True); Ets = T["E_ts"].astype(np.int64)
    pa = Z["pair_a"].astype(np.int64); ps = Z["pair_s"].astype(np.int64); XX = Z["X"]; X = XX[:, c].astype(np.float64); Xn = XX[:, cn].astype(np.float64)
    ts = Ets[pa]; jj = np.array([prow.get(int(t), -1) for t in ts]); ok = jj >= 0
    iv = np.full(len(ok), np.nan, np.float32); iv[ok] = IV[jj[ok], ps[ok]]
    sel = ok & (iv == 4.0)
    c0 = C0[jj[sel], ps[sel]].astype(np.float64); c1 = C1[jj[sel], ps[sel]].astype(np.float64); st = X[sel]
    use = c0 != c1; eq0 = (st == c0) & use; neq = use & ~eq0
    r0 = st[neq] / c0[neq]; r1 = st[neq] / c1[neq]
    tsel = ts[sel][neq]; yrs = np.array([time.gmtime(int(t)).tm_year for t in tsel])
    # stored fund_now vs panel f_fund_now (float16 cast) on the same cells: tests whether the whole fund block is from another panel version
    fnc = np.float16(np.nan_to_num(FN[jj[sel], ps[sel]], nan=0.0)).astype(np.float64); fnst = Xn[sel]
    OUT[name] = dict(n_use=int(use.sum()), n_eq_v0=int(eq0.sum()), n_neq=int(neq.sum()),
                     ratio_stored_over_v0_pct=[float(np.percentile(r0, q)) for q in (1, 10, 50, 90, 99)] if neq.any() else None,
                     ratio_stored_over_v1_pct=[float(np.percentile(r1, q)) for q in (1, 10, 50, 90, 99)] if neq.any() else None,
                     share_neq_within_1pct_of_v0=float(np.mean(np.abs(r0 - 1) <= 0.01)) if neq.any() else None,
                     share_neq_within_1pct_of_v1=float(np.mean(np.abs(r1 - 1) <= 0.01)) if neq.any() else None,
                     neq_by_year={int(y): int((yrs == y).sum()) for y in np.unique(yrs)} if neq.any() else None,
                     eq_by_year={int(y): int(n) for y, n in zip(*np.unique(np.array([time.gmtime(int(t)).tm_year for t in ts[sel][eq0]]), return_counts=True))},
                     fund_now_share_equal_on_use_cells=float(np.mean(fnst[use] == fnc[use])), fund_now_share_equal_on_neq_cells=float(np.mean(fnst[neq] == fnc[neq])) if neq.any() else None)
    print(name, json.dumps(OUT[name]), flush=True)
json.dump(dict(self_sha256=sha(os.path.abspath(__file__)), label="POST-HOC DESCRIPTIVE", result=OUT, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())), open(R + "/receipts/RECEIPT_T1_h2b_dlposthoc.json", "w"), indent=1)
print("DONE")
