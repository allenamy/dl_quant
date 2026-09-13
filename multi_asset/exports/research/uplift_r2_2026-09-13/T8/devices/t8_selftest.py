#!/usr/bin/env python3
"""t8_selftest.py — unit checks of t8_common on SYNTHETIC arrays only (no research input is opened): features vs brute-force loops,
reshape vs the A0 device lines, shuffle-future on synthetic data (and that the check can fail), day-block bootstrap vs direct resample,
fold preprocessing invariants, Ridge vs sklearn, LightGBM determinism, day-permutation index mapping.
Writes receipts/RECEIPT_T8_selftest.json; exit 0 only if all checks pass. Launch: devices/run_t8.sh t8_selftest.py"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t8_common as C
ENV = C.check_env(sys.argv)
import numpy as np
t0 = time.time()
SELF = C.sha256(os.path.abspath(__file__)); COMMON = C.sha256(C.__file__); PRE = C.check_prereg()
rng = np.random.default_rng(777)
NR, OFF, NN, BT = 160, 30, 70, 3
res = {}

def synth():
    D = {"OFF": OFF, "BTC": BT}
    Y = rng.normal(0, 0.02, (NR + OFF, NN)); Y[rng.random(Y.shape) < 0.03] = np.nan; Y[:, BT] = rng.normal(0, 0.01, NR + OFF)
    D["Y"] = Y; D["QVK"] = rng.normal(5, 1, (NR + OFF, NN)).astype(np.float32); D["QVK"][rng.random(D["QVK"].shape) < 0.05] = np.nan
    D["U"] = rng.random((NR, NN)) < 0.93; D["U"][:, BT] = True
    FN = rng.normal(0, 2e-4, (NR, NN)); FN[rng.random(FN.shape) < 0.03] = np.nan; D["FN"] = FN
    IV = rng.choice(np.array([1.0, 4.0, 8.0, np.nan, 0.0]), (NR, NN)); D["IV"] = IV
    D["TBF"] = rng.uniform(0.3, 0.7, (NR, NN))
    for s in C.SEEDS:
        W = rng.normal(0, 0.003, (NR, NN)); W[rng.random(W.shape) < 0.3] = 0.0; D["W_" + s] = W.astype(np.float32)
        D["NET_" + s] = rng.normal(0, 30, NR)
    return D

D = synth()

def brute_market(D, i):
    k = i + OFF; out = [np.nan] * 17; Y = D["Y"]
    def cmp(n, q):
        v = 1.0
        for r in range(k - q, k):
            if not np.isfinite(Y[r, n]): return np.nan
            v *= 1.0 + Y[r, n]
        return v - 1.0
    r4 = [Y[k - 1, n] for n in range(NN)]; r24 = [cmp(n, 6) for n in range(NN)]; r72 = [cmp(n, 18) for n in range(NN)]
    out[0], out[1], out[2] = r4[BT], r24[BT], r72[BT]
    for c, v in ((3, r4), (4, r24), (5, r72)):
        al = [v[n] for n in range(NN) if D["U"][i, n] and np.isfinite(v[n]) and n != BT]
        if len(al) >= 50 and np.isfinite(v[BT]): out[c] = np.mean(al) - v[BT]
    a4 = [r4[n] for n in range(NN) if D["U"][i, n] and np.isfinite(r4[n])]; a24 = [r24[n] for n in range(NN) if D["U"][i, n] and np.isfinite(r24[n])]
    if len(a4) >= 50: out[6] = np.mean([x > 0 for x in a4]); out[8] = np.std(a4)
    if len(a24) >= 50: out[7] = np.mean([x > 0 for x in a24]); out[9] = np.std(a24)
    def mk(ii):
        if ii < 0: return np.nan
        vv = [Y[ii + OFF - 1, n] for n in range(NN) if D["U"][ii, n] and np.isfinite(Y[ii + OFF - 1, n])]
        return np.mean(vv) if len(vv) >= 50 else np.nan
    m6 = [mk(i - q) for q in range(6)]; m42 = [mk(i - q) for q in range(42)]
    if all(np.isfinite(m6)): out[10] = np.sqrt(sum(x * x for x in m6))
    if all(np.isfinite(m42)): out[11] = np.sqrt(sum(x * x for x in m42))
    def fs(j):
        if j < 0: return np.nan, np.nan
        vv = []
        for n in range(NN):
            if D["U"][j, n] and np.isfinite(D["FN"][j, n]):
                iv = D["IV"][j, n]; iv = iv if (np.isfinite(iv) and iv > 0) else 8.0
                vv.append(D["FN"][j, n] * 8.0 / iv)
        return (1e4 * np.mean(vv), 1e4 * np.std(vv)) if len(vv) >= 50 else (np.nan, np.nan)
    mu, sg = fs(i); mu6, sg6 = fs(i - 6)
    out[12], out[13], out[14], out[15] = mu, sg, mu - mu6, sg - sg6
    tb = [D["TBF"][i, n] - 0.5 for n in range(NN) if D["U"][i, n] and np.isfinite(r24[n]) and np.isfinite(D["TBF"][i, n])]
    if len(tb) >= 50: out[16] = np.mean(tb)
    return np.array(out, float)

def device_reshape(sm):   # transcription of w10_sleeve_r18.py executor reshape lines
    nz = np.abs(sm) > 1e-12; smr = sm.copy()
    if nz.any():
        smr[nz] -= smr[nz].mean()
        _g0 = np.abs(sm).sum(); _g1 = np.abs(smr).sum()
        if _g1 > 1e-9:
            smr *= _g0 / _g1
    return smr

def brute_book(D, i, s):
    k = i + OFF; smr = device_reshape(D["W_" + s][i].astype(np.float64)); out = [np.nan] * 7
    q = np.nan_to_num(D["QVK"][k], nan=-1.0)
    for c, sgn in ((0, -1), (2, 1)):
        num = den = 0.0; num2 = den2 = 0.0
        for n in range(NN):
            if not (q[n] > -0.5 and D["U"][i, n] and np.sign(smr[n]) == sgn): continue
            iv = D["IV"][i, n]; iv = iv if (np.isfinite(iv) and iv > 0) else 8.0
            rn = D["FN"][i, n] * 8.0 / iv
            if np.isfinite(rn): num += abs(smr[n]) * rn; den += abs(smr[n])
            v = 1.0; ok = True
            for r in range(k - 18, k):
                if not np.isfinite(D["Y"][r, n]): ok = False; break
                v *= 1.0 + D["Y"][r, n]
            if ok: num2 += abs(smr[n]) * (v - 1.0); den2 += abs(smr[n])
        if den > 0: out[c] = 1e4 * num / den
        if den2 > 0: out[c + 1] = num2 / den2
    net = D["NET_" + s]
    if i >= 1: out[4] = net[i - 1]
    if i >= 6: out[5] = np.mean(net[i - 6:i])
    if i >= 42: out[6] = np.mean(net[i - 42:i])
    return np.array(out, float)

mx = 0.0; nan_mismatch = 0
for i in range(NR):
    for s in C.SEEDS:
        a = C.features_row(D, i, s); b = np.concatenate([brute_market(D, i), brute_book(D, i, s)])
        nan_mismatch += int((np.isfinite(a) != np.isfinite(b)).sum())
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.any(): mx = max(mx, float(np.max(np.abs(a[ok] - b[ok]) / np.maximum(1.0, np.abs(b[ok])))))
res["features_vs_brute"] = dict(max_rel_diff=mx, nan_mismatch=nan_mismatch, n_finite_cols_last_row=int(np.isfinite(C.features_row(D, NR - 1, "42")).sum()), PASS=bool(mx < 1e-9 and nan_mismatch == 0))

mr = 0.0
for i in range(NR):
    w = D["W_42"][i].astype(np.float64); mr = max(mr, float(np.abs(C.reshape_row(D["W_42"][i]) - device_reshape(w)).max()))
res["reshape_vs_device_lines"] = dict(max_abs=mr, PASS=bool(mr == 0.0))

# shuffle-future on synthetic data, plus a planted leak that must be caught
F0 = {s: np.array([C.features_row(D, i, s) for i in range(NR)]) for s in C.SEEDS}
eq = 0; tot = 0; prng = np.random.default_rng(5)
for i in range(45, NR, 7):
    k = i + OFF; Dp = dict(D)
    A = D["Y"].copy(); A[k:] = prng.normal(0, 0.05, A[k:].shape); Dp["Y"] = A
    A = D["QVK"].copy(); A[k + 1:] = prng.normal(5, 1, A[k + 1:].shape).astype(np.float32); Dp["QVK"] = A
    for key in ("FN", "IV", "TBF"):
        A = D[key].copy(); A[i + 1:] = prng.normal(0, 1, A[i + 1:].shape); Dp[key] = A
    A = D["U"].copy(); A[i + 1:] = prng.random(A[i + 1:].shape) < 0.5; Dp["U"] = A
    for s in C.SEEDS:
        A = D["W_" + s].copy(); A[i + 1:] = prng.normal(0, 1e-3, A[i + 1:].shape).astype(np.float32); Dp["W_" + s] = A
        A = D["NET_" + s].copy(); A[i:] = prng.normal(0, 30, A[i:].shape); Dp["NET_" + s] = A
        tot += 1; eq += int(C.features_row(Dp, i, s).tobytes() == F0[s][i].tobytes())
def leaky_market_row(D, i):   # planted defect: reads the forward row k instead of k-1
    D2 = dict(D); D2["OFF"] = D["OFF"] + 1
    return C.market_row(D2, i)
caught = 0; ntest = 0
for i in range(45, NR - 2, 7):
    k = i + OFF; Dp = dict(D); A = D["Y"].copy(); A[k:] = prng.normal(0, 0.05, A[k:].shape); Dp["Y"] = A
    ntest += 1; caught += int(leaky_market_row(Dp, i).tobytes() != leaky_market_row(D, i).tobytes())
res["shuffle_future_synthetic"] = dict(bitwise_equal=eq, total=tot, planted_leak_caught=caught, planted_leak_tests=ntest, PASS=bool(eq == tot and caught == ntest))

# bootstrap: counts vs direct replicate, Pearson-from-moments vs direct
nd = 40; day = np.repeat(np.arange(nd), 6); x = rng.normal(size=nd * 6); y = 0.3 * x + rng.normal(size=nd * 6)
Cc = C.draw_counts(nd, 0); mom = C.day_moments(x, y, day, nd); br = C.boot_r(Cc, mom); mxb = 0.0
for b in (0, 1, 7, 1999):
    idx = np.random.default_rng([20260905, b]).integers(0, nd, nd)
    rows = np.concatenate([np.nonzero(day == d)[0] for d in idx])
    mxb = max(mxb, abs(C.pearson(x[rows], y[rows]) - br[b]))
C9 = C.draw_counts(nd, 9 * C.NB); idx9 = np.random.default_rng([20260905, 18000 + 3]).integers(0, nd, nd)
res["bootstrap"] = dict(max_abs_direct_vs_moments=float(mxb), k9_stream_ok=bool(np.array_equal(C9[3], np.bincount(idx9, minlength=nd))), PASS=bool(mxb < 1e-10 and np.array_equal(C9[3], np.bincount(idx9, minlength=nd))))

# fold prep, Ridge vs sklearn, LightGBM determinism
n = 1500; Fm = rng.normal(size=(n, C.NF)); Fm[:40, 23] = np.nan; Fm[rng.random(Fm.shape) < 0.002] = np.nan; Fm[:, 5] = 1.0
tr = np.zeros(n, bool); tr[:1000] = True; te = np.zeros(n, bool); te[1000:] = True
P = C.FoldPrep(Fm, tr, te)
mu_ok = bool(np.abs(P.Xtr.mean(0)).max() < 1e-10); sd = P.Xtr.std(0); sd_ok = bool(np.all((np.abs(sd - 1.0) < 1e-10) | (np.arange(C.NF) == 5)))
res["foldprep"] = dict(n_drop=P.n_drop, n_imp=P.n_imp, zero=P.zero, test_all_finite=bool(np.isfinite(P.Xte).all()), mean0=mu_ok, sd1=sd_ok,
                       PASS=bool(np.isfinite(P.Xte).all() and mu_ok and sd_ok and P.zero == [5] and P.n_drop == int((~np.isfinite(Fm[:1000]).all(1)).sum())))
yv = Fm[:, 0] * 0.1 + rng.normal(size=n); yv = np.where(np.isfinite(yv), yv, 0.0)
pt, pin, inf = C.fit_ridge(P, yv)
from sklearn.linear_model import Ridge
yc = C.clip_target(yv[P.tr_idx]); sk = Ridge(alpha=float(len(P.tr_idx)), fit_intercept=True, solver="cholesky").fit(P.Xtr, yc)
res["ridge_vs_sklearn"] = dict(max_abs_pred=float(np.abs(sk.predict(P.Xte) - pt).max()), PASS=bool(np.abs(sk.predict(P.Xte) - pt).max() < 1e-8))
p1, _, _ = C.fit_lgbm(P, yv); p2, _, _ = C.fit_lgbm(P, yv)
res["lgbm_determinism"] = dict(bitwise=bool(p1.tobytes() == p2.tobytes()), PASS=bool(p1.tobytes() == p2.tobytes()))

# day-permutation mapping
Tt = np.arange(6 * 10, dtype=float); perm = np.random.default_rng([20260905, 7 * 2000 + 0]).permutation(10)
idx = (6 * perm[:, None] + np.arange(6)[None, :]).ravel(); Tp = Tt[idx]
res["day_perm_mapping"] = dict(PASS=bool(all(Tp[6 * d + q] == Tt[6 * perm[d] + q] for d in range(10) for q in range(6))))

ALL = bool(all(v["PASS"] for v in res.values()))
R = dict(device="t8_selftest.py", self_sha256=SELF, common_sha256=COMMON, prereg_sha256=PRE, env=ENV, synthetic_only=True, checks=res, ALL_PASS=ALL, wall_s=round(time.time() - t0, 1),
         utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
C.jdump(R, C.T8 + "/receipts/RECEIPT_T8_selftest.json")
print(f"T8_SELFTEST_DONE ALL_PASS={ALL} " + " ".join(f"{k}={v['PASS']}" for k, v in res.items()), flush=True)
sys.exit(0 if ALL else 3)
