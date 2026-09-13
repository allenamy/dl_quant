#!/usr/bin/env python3
"""t8_null.py <r_lo> <r_hi> — PREREG_T8 §7.2 G1: UTC-day block permutation null. For r in [r_lo, r_hi):
pi_r = default_rng([20260905, 7*2000 + r]).permutation(1673); day d's 6 target rows <- day pi_r(d)'s rows (NET/LONG/SHORT jointly, s42);
features fixed; refit the 6 substantive cells with the frozen family (§5) and record pooled OOS Pearson on W_ALPHA and the family max M_r.
Requires RECEIPT_T8_build.json ALL_PASS. Writes receipts/RECEIPT_T8_null_<r_lo>_<r_hi>.json. Launch: devices/run_t8.sh t8_null.py <r_lo> <r_hi>"""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t8_common as C
ENV = C.check_env(sys.argv)
import numpy as np
import lightgbm
t0 = time.time()
assert len(sys.argv) == 4, "usage: t8_null.py WHITELIST r_lo r_hi"
r_lo, r_hi = int(sys.argv[2]), int(sys.argv[3]); assert 0 <= r_lo < r_hi <= C.NNULL
SELF = C.sha256(os.path.abspath(__file__)); COMMON = C.sha256(C.__file__); PRE = C.check_prereg()
ST0 = C.sysstate(); assert C.gpu_idle(ST0), ("GPU not idle before start", ST0["gpu"])
BPATH = C.T8 + "/receipts/RECEIPT_T8_build.json"; B = json.load(open(BPATH))
assert B["ALL_PASS"] is True, "build gates did not pass"
assert B["common_sha256"] == COMMON and B["self_sha256"] == C.sha256(C.T8 + "/devices/t8_build.py"), "build receipt from a different device version"
DATA = C.T8 + "/out/T8_data.npz"; assert C.sha256(DATA) == B["out"]["sha256"], "data file changed since build"
Z = np.load(DATA, allow_pickle=False)
ts = Z["ts"].astype(np.int64); F = np.asarray(Z["F_42"], np.float64)
assert ts[0] % 86400 == 0 and np.array_equal(ts, ts[0] + 14400 * np.arange(C.N_FULL, dtype=np.int64))
T = {t: np.asarray(Z[t + "_42"], np.float64) for t in C.SUBST}
preps = [C.FoldPrep(F, tr, te) for _, tr, te in C.folds(ts)]
A = np.arange(C.ALPHA0, C.N_FULL)
rows = []; undefined = 0
print(f"T8 null start r=[{r_lo},{r_hi}) {ST0['utc']} self {SELF[:12]}", flush=True)
for r in range(r_lo, r_hi):
    perm = np.random.default_rng([20260905, 7 * 2000 + r]).permutation(C.NDAYS_FULL)
    idx = (6 * perm[:, None] + np.arange(6)[None, :]).ravel()
    row = {"r": r}
    for t in C.SUBST:
        tp = T[t][idx]
        for m in C.MODELS:
            p, _, _ = C.oos(preps, tp, m)
            v = C.pearson(p[A], tp[A])
            if not np.isfinite(v):
                undefined += 1; v = 0.0
            row[m + "_" + t] = v
    row["M"] = max(row[m + "_" + t] for m in C.MODELS for t in C.SUBST)
    rows.append(row)
    if (r - r_lo) % 20 == 19:
        print(f"  r {r} done {time.time()-t0:.0f}s", flush=True)
R = dict(device="t8_null.py", self_sha256=SELF, common_sha256=COMMON, prereg_sha256=PRE, env=ENV, lightgbm=lightgbm.__version__, sys_before=ST0,
         build_receipt_sha256=C.sha256(BPATH), data_sha256=B["out"]["sha256"], r_lo=r_lo, r_hi=r_hi, undefined_replaced_by_0=undefined,
         prep=[dict(fold=nm, n_train=int(len(P.tr_idx)), n_drop=P.n_drop, n_test=int(len(P.te_idx)), n_imputed=P.n_imp, zero_std=P.zero) for (nm, _, _), P in zip(C.folds(ts), preps)],
         rows=rows)
R["sys_after"] = C.sysstate(); R["wall_s"] = round(time.time() - t0, 1)
C.jdump(R, C.T8 + f"/receipts/RECEIPT_T8_null_{r_lo}_{r_hi}.json")
print(f"T8_NULL_DONE r=[{r_lo},{r_hi}) n={len(rows)} undefined={undefined} wall_s={R['wall_s']}", flush=True)
