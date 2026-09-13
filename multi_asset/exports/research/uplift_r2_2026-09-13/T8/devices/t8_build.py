#!/usr/bin/env python3
"""t8_build.py — PREREG_T8 §7.1 preconditions G-IN / G-T / G-T2 / G2a / G3 / G3-NEG, and the target + feature arrays (§3.1, §4.2).
pod2, CPU, read-only inputs. Writes out/T8_data.npz and receipts/RECEIPT_T8_build.json; exit 0 only if every gate passes (exit 3 after
writing the receipt otherwise). No model is fitted here. Launch: devices/run_t8.sh t8_build.py"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t8_common as C
ENV = C.check_env(sys.argv)
import numpy as np
t0 = time.time()
SELF = C.sha256(os.path.abspath(__file__)); COMMON = C.sha256(C.__file__); PRE = C.check_prereg()
ST0 = C.sysstate(); assert C.gpu_idle(ST0), ("GPU not idle before start", ST0["gpu"])
print(f"T8 build start {ST0['utc']} self {SELF[:12]} common {COMMON[:12]} prereg {PRE['prereg'][:12]} amendment_1 {PRE['amendment_1'][:12]}", flush=True)
D, REP = C.load_inputs()
nW = C.N_FULL
R = dict(device="t8_build.py", self_sha256=SELF, common_sha256=COMMON, prereg_sha256=PRE, env=ENV, sys_before=ST0, **REP)
gates = {"G_IN": dict(PASS=True, note="all load_inputs assertions held (shas, config_json, rec R18==T1 bitwise, ts alignment, W_FULL/W_ALPHA counts)")}
print(f"inputs loaded {time.time()-t0:.0f}s", flush=True)

# ---- G-T target identities (W_FULL)
TK = ("NET", "LONG", "SHORT", "CARRY", "PRICE", "COST")
g = {}
for s in C.SEEDS:
    lsp = float(np.abs(D["LONG_" + s][:nW] + D["SHORT_" + s][:nW] - D["PRICE_" + s][:nW]).max())
    pcn = float(np.abs(D["PRICE_" + s][:nW] - D["CARRY_" + s][:nW] - D["COST_" + s][:nW] - D["NET_" + s][:nW]).max())
    gtp = bool((D["GT_" + s][:nW] > 0).all()); fin = all(bool(np.isfinite(D[k + "_" + s][:nW]).all()) for k in TK)
    g[s] = dict(max_abs_long_plus_short_minus_price=lsp, max_abs_price_minus_carry_cost_net=pcn, gross_total_positive=gtp, targets_finite=fin,
                PASS=bool(lsp <= 1e-8 and pcn <= 1e-8 and gtp and fin))
gates["G_T"] = g; print("G_T", {s: g[s]["PASS"] for s in C.SEEDS}, flush=True)

# ---- G-T2 independent long/short split from the r18 arm W (float32) and META y4
g = {}
for s in C.SEEDS:
    W = D["W_" + s][:nW].astype(np.float64)
    nz = np.abs(W) > 1e-12; cnt = nz.sum(1)
    mu = np.where(cnt > 0, np.where(nz, W, 0.0).sum(1) / np.maximum(cnt, 1), 0.0)
    smr = np.where(nz, W - mu[:, None], W)
    g0 = np.abs(W).sum(1); g1 = np.abs(smr).sum(1)
    smr = smr * np.where(g1 > 1e-9, g0 / np.where(g1 > 1e-9, g1, 1.0), 1.0)[:, None]
    q = np.nan_to_num(D["QVK"][C.META_OFF:C.META_OFF + nW], nan=-1.0)
    mem = (q > -0.5) & D["U"][:nW]
    yv = np.where(mem, np.nan_to_num(D["Y"][C.META_OFF:C.META_OFF + nW], nan=0.0), 0.0)
    gt = D["GT_" + s][:nW]
    L2 = (np.where(smr > 0, smr, 0.0) * yv).sum(1) * 1e4 / gt; S2 = (np.where(smr < 0, smr, 0.0) * yv).sum(1) * 1e4 / gt
    dL = np.abs(L2 - D["LONG_" + s][:nW]); dS = np.abs(S2 - D["SHORT_" + s][:nW])
    g[s] = dict(max_abs_long=float(dL.max()), max_abs_short=float(dS.max()), at_long=C.utc(D["TS"][int(dL.argmax())]), at_short=C.utc(D["TS"][int(dS.argmax())]),
                PASS=bool(dL.max() <= 1e-2 and dS.max() <= 1e-2))
    del W, nz, smr, yv, mem, q
gates["G_T2"] = g; print("G_T2", {s: (g[s]["max_abs_long"], g[s]["max_abs_short"], g[s]["PASS"]) for s in C.SEEDS}, flush=True)

# ---- features (§4.2), one function per row, both seeds
F = {s: np.full((nW, C.NF), np.nan) for s in C.SEEDS}
MKROW = np.full((nW, C.NMKT), np.nan)
for i in range(nW):
    MKROW[i] = C.market_row(D, i)
for s in C.SEEDS:
    F[s][:, :C.NMKT] = MKROW
    for i in range(nW):
        F[s][i, C.NMKT:] = C.book_row(D, i, s)
print(f"features done {time.time()-t0:.0f}s", flush=True)

# ---- G2a alignment positive control (known contemporaneous relations; W_FULL)
SP = np.full(nW, np.nan); MKT = np.full(nW, np.nan)
for i in range(nW):
    SP[i], MKT[i] = C.forward_spread_mkt(D, i)
KS = (-2, -1, 0, 1, 2, 3)
def shift_corr(a, b, k):
    x, y = (a[:nW - k], b[k:]) if k >= 0 else (a[-k:], b[:nW + k])
    ok = np.isfinite(x) & np.isfinite(y)
    return C.pearson(x[ok], y[ok])
g = dict(n_nonfinite_S=int((~np.isfinite(SP)).sum()), n_nonfinite_MKT=int((~np.isfinite(MKT)).sum()))
for s in C.SEEDS:
    cN = {k: shift_corr(D["NET_" + s][:nW], SP, k) for k in KS}
    cL = {k: shift_corr(D["LONG_" + s][:nW], MKT, k) for k in KS}
    cS = {k: shift_corr(D["SHORT_" + s][:nW], MKT, k) for k in KS}
    am = lambda c: max(KS, key=lambda k: abs(c[k]))
    g[s] = dict(c_N={str(k): v for k, v in cN.items()}, c_L={str(k): v for k, v in cL.items()}, c_S={str(k): v for k, v in cS.items()},
                argmax_abs_N=am(cN), argmax_abs_L=am(cL), argmax_abs_S=am(cS), c_N_reported_only=True,
                rule="PREREG_AMENDMENT_1_T8 §C.1: argmax|c_L|=0 & c_L(0)>0 & argmax|c_S|=0 & c_S(0)<0; c_N reported only",
                PASS=bool(am(cL) == 0 and cL[0] > 0 and am(cS) == 0 and cS[0] < 0))
gates["G2a"] = g; print("G2a", {s: g[s]["PASS"] for s in C.SEEDS}, flush=True)

# ---- G3 shuffle-future + G3-NEG
rows = np.random.default_rng([20260905, 10000]).choice(np.arange(42, nW), 60, replace=False)
rng = np.random.default_rng([20260905, 10001])
eq = {s: 0 for s in C.SEEDS}; fails = []; neg = dict(btc4_changed=0, tr1_changed=0, muf_changed=0); b = D["BTC"]
for i in (int(x) for x in rows):
    k = i + C.META_OFF; j = i
    Dp = dict(D)
    A = D["Y"].copy(); A[k:] = rng.normal(0.0, 0.05, A[k:].shape); Dp["Y"] = A
    A = D["QVK"].copy(); A[k + 1:] = rng.normal(5.0, 1.0, A[k + 1:].shape).astype(np.float32); Dp["QVK"] = A
    A = D["FN"].copy(); A[j + 1:] = rng.normal(0.0, 1e-3, A[j + 1:].shape); Dp["FN"] = A
    A = D["IV"].copy(); A[j + 1:] = rng.choice(np.array([1.0, 4.0, 8.0]), A[j + 1:].shape); Dp["IV"] = A
    A = D["TBF"].copy(); A[j + 1:] = rng.uniform(0.0, 1.0, A[j + 1:].shape); Dp["TBF"] = A
    A = D["U"].copy(); A[j + 1:] = rng.random(A[j + 1:].shape) < 0.5; Dp["U"] = A
    for s in C.SEEDS:
        A = D["W_" + s].copy(); A[i + 1:] = rng.normal(0.0, 1e-3, A[i + 1:].shape).astype(np.float32); Dp["W_" + s] = A
        for t in TK:
            A = D[t + "_" + s].copy(); A[i:] = rng.normal(0.0, 30.0, A[i:].shape); Dp[t + "_" + s] = A
    for s in C.SEEDS:
        v = C.features_row(Dp, i, s)
        if v.tobytes() == F[s][i].tobytes():
            eq[s] += 1
        else:
            fails.append(dict(row=i, at=C.utc(D["TS"][i]), seed=s, cols=[C.FEATS[q] for q in range(C.NF) if v[q:q + 1].tobytes() != F[s][i][q:q + 1].tobytes()]))
    del Dp, A
    Dn = dict(D); A = D["Y"].copy(); A[k - 1, b] += 0.01; Dn["Y"] = A
    if C.market_row(Dn, i)[0:1].tobytes() != F["42"][i][0:1].tobytes():
        neg["btc4_changed"] += 1
    Dn = dict(D); A = D["NET_42"].copy(); A[i - 1] += 1.0; Dn["NET_42"] = A
    if C.book_row(Dn, i, "42")[4:5].tobytes() != F["42"][i][C.NMKT + 4:C.NMKT + 5].tobytes():
        neg["tr1_changed"] += 1
    Dn = dict(D); A = D["FN"].copy(); A[j] = A[j] + 1e-4; Dn["FN"] = A
    if C.market_row(Dn, i)[12:13].tobytes() != F["42"][i][12:13].tobytes():
        neg["muf_changed"] += 1
    del Dn, A
gates["G3"] = dict(rows=[int(x) for x in rows], n_rows=60, bitwise_equal=eq, fails=fails[:40], PASS=bool(all(eq[s] == 60 for s in C.SEEDS)))
gates["G3_NEG"] = dict(**neg, PASS=bool(neg["btc4_changed"] == 60 and neg["tr1_changed"] == 60 and neg["muf_changed"] == 60))
print("G3", eq, "G3_NEG", neg, f"{time.time()-t0:.0f}s", flush=True)

# ---- non-outcome coverage and feature summaries
fl = C.folds(D["TS"][:nW])
cov = {}
for s in C.SEEDS:
    cov[s] = {name: dict(train_rows=int(tr.sum()), train_rows_all_features_finite=int(np.isfinite(F[s][tr]).all(1).sum()), test_rows=int(te.sum()),
                         test_nonfinite_by_feature={C.FEATS[q]: int((~np.isfinite(F[s][te, q])).sum()) for q in range(C.NF) if (~np.isfinite(F[s][te, q])).any()})
              for name, tr, te in fl}
fstats = {}
for s in C.SEEDS:
    fstats[s] = {}
    for q in range(C.NF):
        v = F[s][:, q]; ok = np.isfinite(v)
        fstats[s][C.FEATS[q]] = dict(nonfinite=int((~ok).sum()), first_finite=(C.utc(D["TS"][int(np.argmax(ok))]) if ok.any() else None), mean=float(v[ok].mean()),
                                      std=float(v[ok].std()), p01=float(np.percentile(v[ok], 1)), p99=float(np.percentile(v[ok], 99)))
R["coverage"] = cov; R["feature_summary"] = fstats; R["gates"] = gates

OUT = C.T8 + "/out/T8_data.npz"
np.savez_compressed(OUT, ts=D["TS"][:nW], feats=np.array(C.FEATS), F_42=F["42"], F_2027=F["2027"], S=SP, MKT=MKT,
                    **{t + "_" + s: D[t + "_" + s][:nW] for t in TK for s in C.SEEDS})
assert os.path.getsize(OUT) < 500 * 2 ** 20
R["out"] = dict(path=OUT, sha256=C.sha256(OUT), size=os.path.getsize(OUT))
ALL = bool(all(v["PASS"] if "PASS" in v else all(v[s]["PASS"] for s in C.SEEDS) for k, v in gates.items()))
R["ALL_PASS"] = ALL
R["sys_after"] = C.sysstate(); R["wall_s"] = round(time.time() - t0, 1)
C.jdump(R, C.T8 + "/receipts/RECEIPT_T8_build.json")
print(f"T8_BUILD_DONE ALL_PASS={ALL} G_T={all(gates['G_T'][s]['PASS'] for s in C.SEEDS)} G_T2={all(gates['G_T2'][s]['PASS'] for s in C.SEEDS)} "
      f"G2a={all(gates['G2a'][s]['PASS'] for s in C.SEEDS)} G3={gates['G3']['PASS']} G3_NEG={gates['G3_NEG']['PASS']} data_sha={R['out']['sha256'][:16]} wall_s={R['wall_s']}", flush=True)
sys.exit(0 if ALL else 3)
