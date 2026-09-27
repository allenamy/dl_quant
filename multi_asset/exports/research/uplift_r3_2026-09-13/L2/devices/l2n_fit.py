#!/usr/bin/env python3
"""l2n_fit.py — S1 step 5a (AMENDMENT_L2_NC_population_2026-09-27 §2–§3). Committed before it is run. Out-of-sample scores only; NO
statistic of scores against targets is computed here.

REAL fits (L2 §6 family verbatim through l2_b_common.fit_predict): seeds {42, 2027} x targets {A_res (main), B_res (descriptive)} x models
{R, L} x test years {2023, 2024, 2025, 2026}; X = the 10 L2 features (FULL); training rows E < Y-01-01 - 24h with a finite target;
test rows of year Y with a finite target. -> out/L2N_oos_s{seed}.npz  keys p_{R,L}_{A,B}.
RESOLUTION arm (lead §1 "分辨力先测"), target A only, per seed: y_perm = uA_res permuted WITHIN each anchor with
default_rng([20260927, 3, anchor]) (destroys any real association, keeps the anchor structure); planted column
x_p = c * g + e, g = the within-anchor centred rank of y_perm, e ~ N(0, 1) from default_rng([20260927, 4, seed]); c is set ONCE on the whole
sample (a pure function of the synthetic target) so that the mean within-anchor Spearman(x_p, y_perm) = 0.015 (bisection, |err| < 2e-4,
recorded). Fits: FULL + x_p (PLANT) and FULL alone (NULL), both models, the same years. -> out/L2N_resolution_s{seed}.npz
keys p_{R,L}_{PLANT,NULL}, y_perm.
usage: /workspace/venv/bin/python -B l2n_fit.py <whitelist>
"""
import os, sys, time, json, calendar
import numpy as np
from scipy.stats import rankdata, spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_b_common as B

T0 = time.time()
envrep = C.check_env(sys.argv); st0 = C.sysstate()
L2 = C.L2; OUT = f"{L2}/out"; REC = f"{L2}/receipts"; YEARS = B.TEST_YEARS; PLANT_IC = 0.015
import lightgbm as lgb
assert lgb.__version__ == "4.7.0", lgb.__version__
BR = json.load(open(f"{REC}/RECEIPT_L2N_build.json"))
rep = dict(device="l2n_fit.py", device_sha256={f: C.sha256(os.path.join(L2, "devices", f)) for f in ("l2_common.py", "l2_b_common.py", "l2n_fit.py")},
           env=envrep, sys_before=st0, build_receipt_sha256=C.sha256(f"{REC}/RECEIPT_L2N_build.json"), lightgbm=lgb.__version__, fits={}, resolution={})


def run(model, X, y, E, YR, tag):
    p = np.full(E.size, np.nan)
    for Y in YEARS:
        y0 = calendar.timegm((Y, 1, 1, 0, 0, 0)); tr = (E < y0 - 86400) & np.isfinite(y); te = (YR == Y) & np.isfinite(y)
        if te.sum() == 0 or tr.sum() == 0: continue
        t1 = time.time(); pred, info = B.fit_predict(model, X[tr], y[tr], X[te]); assert np.isfinite(pred).all(), (tag, Y)
        p[te] = pred; info.update(fit_s=round(time.time() - t1, 1), train_last=C.utc(E[tr].max()), test_first=C.utc(E[te].min()), test_last=C.utc(E[te].max()))
        info.pop("beta", None) if model == "L" else None
        rep["fits"][f"{tag}|{model}|{Y}"] = info
        print(f"fit {tag} {model} {Y} n_train {info['n_train']} n_test {info['n_test']} {info['fit_s']}s", flush=True)
    return p


def mean_anchor_spearman(x, y, i):
    ok = np.isfinite(x) & np.isfinite(y); o = np.argsort(i[ok], kind="stable"); xi, yi, ii = x[ok][o], y[ok][o], i[ok][o]
    b = np.flatnonzero(np.diff(ii)) + 1; st = np.concatenate([[0], b]); en = np.concatenate([b, [ii.size]]); v = []
    for a, e in zip(st, en):
        if e - a >= 10: v.append(spearmanr(xi[a:e], yi[a:e])[0])
    return float(np.nanmean(v))


for s in ("42", "2027"):
    info = BR["per_seed"][s]; assert C.sha256(info["out"]) == info["out_sha256"]
    Z = np.load(info["out"]); E = Z["E"].astype(np.int64); YR = Z["year"].astype(np.int64); F = Z["F"]; i = Z["i"].astype(np.int64)
    out = {}
    for T in ("A", "B"):
        y = Z[f"u{T}_res"]
        for m in ("R", "L"): out[f"p_{m}_{T}"] = run(m, F, y, E, YR, f"s{s}|{T}_res")
    op = f"{OUT}/L2N_oos_s{s}.npz"; np.savez_compressed(op + ".tmp.npz", **out); os.replace(op + ".tmp.npz", op)
    rep.setdefault("out", {})[s] = dict(path=op, sha256=C.sha256(op))
    # resolution arm
    y = Z["uA_res"].copy(); ok = np.isfinite(y); yp = np.full(y.size, np.nan)
    idx = np.flatnonzero(ok); o = idx[np.argsort(i[idx], kind="stable")]; b = np.flatnonzero(np.diff(i[o])) + 1
    for seg in np.split(o, b):
        if seg.size: yp[seg] = y[seg][np.random.default_rng([20260927, 3, int(i[seg[0]])]).permutation(seg.size)]
    g = np.full(y.size, np.nan)
    for seg in np.split(o, b):
        if seg.size: g[seg] = rankdata(yp[seg]) / max(seg.size - 1, 1) - 0.5
    e = np.random.default_rng([20260927, 4, int(s)]).standard_normal(y.size)
    lo, hi = 0.0, 1.0
    for _ in range(40):
        c = 0.5 * (lo + hi); ic = mean_anchor_spearman(c * np.nan_to_num(g) + e, yp, i)
        if ic < PLANT_IC: lo = c
        else: hi = c
        if abs(ic - PLANT_IC) < 2e-4: break
    xp = c * np.nan_to_num(g) + e
    rep["resolution"][s] = dict(c=c, achieved_mean_anchor_spearman=ic, target=PLANT_IC)
    res = {"y_perm": yp}
    for m in ("R", "L"):
        res[f"p_{m}_PLANT"] = run(m, np.column_stack([F, xp]), yp, E, YR, f"s{s}|PLANT")
        res[f"p_{m}_NULL"] = run(m, F, yp, E, YR, f"s{s}|NULL")
    rp = f"{OUT}/L2N_resolution_s{s}.npz"; np.savez_compressed(rp + ".tmp.npz", **res); os.replace(rp + ".tmp.npz", rp)
    rep["resolution"][s].update(path=rp, sha256=C.sha256(rp))
rep["sys_after"] = C.sysstate(); rep["wall_s"] = round(time.time() - T0, 1)
C.jdump(rep, f"{REC}/RECEIPT_L2N_fit.json")
print("L2N_FIT DONE fits=%d %s" % (len(rep["fits"]), C.sha256(f"{REC}/RECEIPT_L2N_fit.json")[:16]), flush=True)
