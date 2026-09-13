#!/usr/bin/env python3
"""t4_kings.py — pod2, CPU, READ-ONLY on every input (PREREG_T4 §2). Builds the score-layer arms and runs their gates.
Rows = exactly pod_export_bundle_v3.py L38-47 (anchor order, members[i][isfinite(y4)], >= 50, float32 of the stored float16
features, keep columns). Boosters: 2026 = saved slow2026.txt (8d79186b); 2024/2025 = folds retrained with the exporter's
recipe (L56-60) because the originals were never saved. Arms: K0 = stored v0 in col 76; K1 = float32(nan->0(f_fund_ema_v1));
K0f = float32(nan->0(f_fund_ema)). Predictions are written into (anchor x 829) float32 arrays exactly as the exporter
(PRED[a, m[okm]] = pv). Gates: K26 (2026 K0 == archived pinned, bitwise, must pass), KF (2024/2025 K0 vs archived, decides
the base), AL (archived aligned to the v4 axis == SLOW_v3_on_v4axis), S0 (rows with identical col 76 have identical scores).
Writes kings/{K0,K1,K0f}_{v3axis,v4axis}.npy, kings/fold_{2024,2025}.txt, receipts/RECEIPT_T4_kings.json.
Launch: env -i PATH=... HOME=/root /workspace/venv/bin/python devices/t4_kings.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata, spearmanr
T4 = "/workspace/uplift_r2_2026-09-13/T4"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
PREREG = T4 + "/PREREG_T4_king_feature_skew_2026-09-13.md"; PREREG_SHA = "0f94b754c9ca4c6e65c3f2a63146dab7036f37862abd2210cbbfcef661aab4dd"
assert sha(PREREG) == PREREG_SHA, ("PREREG SHA", sha(PREREG))
t0 = time.time()
FEA_P = "/workspace/data/wide_fea_v2ext.npy"; META_P = "/workspace/data/wide_fea_v2ext_meta.npz"; PAN_P = "/workspace/data/wide_panel_4h_v2ext.npz"
B26_P = "/workspace/shadow_bundle_v3/slow2026.txt"; P3_P = "/workspace/shadow_bundle_v3/slow_pred_pinned.npy"
K3_P = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"; M4_P = "/workspace/data/wide_fea_v4_meta.npz"
EXP = {FEA_P: "f88b07205bf19870aefd1ea6f8eaf6f14e78f3587c973f36514b43ea691d4097", META_P: "4b1b6047107d25573244a84df69d45bc987ada89b6731e826c867a230e247082",
       PAN_P: "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116", B26_P: "8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282",
       P3_P: "158cd4ac8f8f30f7f41a5a6cba0bd19a450ce756727e4aeae3d4e4b0b67d0054", K3_P: "647673183e6af44ac5b2570b856692c9d2d51ab9f17194bfebb7a0d3dbbd9009",
       M4_P: "12ea42c4557093f10f954f648db9239f4dd8283ea365ba299f31bd81e7e5ab51"}
INPUTS = {p: sha(p) for p in EXP}
for p, h in EXP.items(): assert INPUTS[p] == h, ("INPUT SHA", p, INPUTS[p])
os.makedirs(T4 + "/kings", exist_ok=True)
FEA = np.load(FEA_P, mmap_mode="r"); MT = np.load(META_P, allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; names = [str(n) for n in MT["names"]]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert len(keep) == 78 and keep.index(80) == 76 and keep.index(81) == 77
PW = np.load(PAN_P, allow_pickle=True); pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
V0 = PW["f_fund_ema"]; V1 = PW["f_fund_ema_v1"]
rows_X, rows_y, rows_a, c_v1, c_v0f, rowcells = [], [], [], [], [], []
n_nan_mismatch = 0
for i in range(nA):
    m = members[i]; yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
    mk = np.asarray(m, dtype=np.int64)[ok]
    x = np.asarray(FEA[i, mk][:, keep]).astype(np.float32)
    rows_X.append(x); rows_y.append(rr.astype(np.float32)); rows_a.append(np.full(ok.sum(), i, np.int32)); rowcells.append(mk)
    j = pw_row.get(int(E_ts[i]))
    if j is None:
        v1 = np.full(len(mk), np.nan, np.float32); v0f = v1.copy()
        n_nan_mismatch += int((~np.isnan(x[:, 76])).sum())
    else:
        v1 = np.nan_to_num(V1[j, mk], nan=0.0).astype(np.float32); v0f = np.nan_to_num(V0[j, mk], nan=0.0).astype(np.float32)
        n_nan_mismatch += int(np.isnan(x[:, 76]).sum())
    c_v1.append(v1); c_v0f.append(v0f)
assert n_nan_mismatch == 0, ("stored col-80 NaN pattern != no-panel-row pattern", n_nan_mismatch)
X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a); CV1 = np.concatenate(c_v1); CV0F = np.concatenate(c_v0f); CELLS = np.concatenate(rowcells)
del rows_X, rows_y, c_v1, c_v0f
YRA = yrs[A]; print("rows", X.shape, round(time.time() - t0, 1), flush=True)
import lightgbm as lgb
PRED = {k: np.full((nA, NW), np.nan, np.float32) for k in ("K0", "K1", "K0f")}
starts = np.r_[0, np.nonzero(np.diff(A))[0] + 1]; ends = np.r_[starts[1:], len(A)]; aidx = A[starts]
def write(key, te_mask, pv):
    full = np.full(len(A), np.nan, np.float64); full[te_mask] = pv
    for s, e, a in zip(starts, ends, aidx):
        if te_mask[s]:
            assert te_mask[s:e].all()
            PRED[key][a, CELLS[s:e]] = full[s:e]
S0 = {}; FOLD = {}
def score(booster_predict, te, tag):
    Xte = X[te]; pv0 = booster_predict(Xte)
    X1 = Xte.copy(); X1[:, 76] = CV1[te]; pv1 = booster_predict(X1)
    Xf = Xte.copy(); Xf[:, 76] = CV0F[te]; pvf = booster_predict(Xf)
    eq1 = (X1[:, 76] == Xte[:, 76]) | (np.isnan(X1[:, 76]) & np.isnan(Xte[:, 76])); eqf = (Xf[:, 76] == Xte[:, 76]) | (np.isnan(Xf[:, 76]) & np.isnan(Xte[:, 76]))
    S0[tag] = dict(rows=int(te.sum()), rows_col76_equal_K1=int(eq1.sum()), maxabs_score_diff_on_equal_K1=float(np.abs(pv1[eq1] - pv0[eq1]).max()) if eq1.any() else 0.0,
                   rows_col76_equal_K0f=int(eqf.sum()), maxabs_score_diff_on_equal_K0f=float(np.abs(pvf[eqf] - pv0[eqf]).max()) if eqf.any() else 0.0)
    write("K0", te, pv0); write("K1", te, pv1); write("K0f", te, pvf)
PARAMS = dict(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1)
for YV in (2024, 2025):
    tr_ = YRA < YV; te_ = YRA == YV; t1 = time.time()
    g2 = lgb.LGBMRegressor(**PARAMS).fit(X[tr_], Y[tr_])
    mp = T4 + f"/kings/fold_{YV}.txt"; g2.booster_.save_model(mp)
    score(g2.predict, te_, f"fold{YV}")
    FOLD[YV] = dict(train_rows=int(tr_.sum()), test_rows=int(te_.sum()), fit_s=round(time.time() - t1, 1), model=mp, model_sha256=sha(mp))
    print("fold", YV, FOLD[YV], flush=True)
b26 = lgb.Booster(model_file=B26_P); te26 = YRA == 2026
score(b26.predict, te26, "y2026_booster_8d79186b")
P3 = np.load(P3_P)
def bitwise(a, b):
    na, nb = np.isnan(a), np.isnan(b); same_nan = bool(np.array_equal(na, nb))
    eq = bool(same_nan and np.array_equal(a[~na], b[~nb]))
    both = ~na & ~nb
    return dict(bitwise=eq, same_nan=same_nan, maxabs=float(np.abs(a[both] - b[both]).max()) if both.any() else 0.0, n_finite=int(both.sum()), n_unequal=int((a[both] != b[both]).sum()))
GATE = {}
r26 = yrs == 2026; GATE["K26"] = bitwise(PRED["K0"][r26], P3[r26]); GATE["K26"]["PASS"] = GATE["K26"]["bitwise"]
for YV in (2024, 2025):
    r = yrs == YV; g = bitwise(PRED["K0"][r], P3[r])
    rho = []
    for i in np.nonzero(r)[0]:
        ok = np.isfinite(PRED["K0"][i]) & np.isfinite(P3[i])
        if ok.sum() >= 50: rho.append(spearmanr(PRED["K0"][i][ok], P3[i][ok])[0])
    g["per_anchor_spearman_min"] = float(np.min(rho)) if rho else None; g["per_anchor_spearman_median"] = float(np.median(rho)) if rho else None
    GATE[f"KF_{YV}"] = g
GATE["KF_PASS_bitwise"] = bool(GATE["KF_2024"]["bitwise"] and GATE["KF_2025"]["bitwise"])
GATE["BASE"] = "K0 == archived pinned (bitwise)" if GATE["KF_PASS_bitwise"] else "K0r (retrained folds' own v0 predictions for 2024/2025; 2026 = saved booster)"
other = ~np.isin(yrs, (2024, 2025, 2026)); GATE["P3_nonfold_rows_all_nan"] = bool(np.isnan(P3[other]).all()); GATE["K0_nonfold_rows_all_nan"] = bool(np.isnan(PRED["K0"][other]).all())
GATE["S0"] = S0; GATE["S0_PASS"] = all(v["maxabs_score_diff_on_equal_K1"] == 0.0 and v["maxabs_score_diff_on_equal_K0f"] == 0.0 for v in S0.values())
M4 = np.load(M4_P, allow_pickle=True); E4 = M4["E_ts"].astype(np.int64)
def align(P, src_E, dst_E):   # build_dev_v4.py L34-39 verbatim semantics
    o = np.full((len(dst_E), P.shape[1]), np.nan, np.float32); r = {int(t): i for i, t in enumerate(src_E)}
    for k, t in enumerate(dst_E):
        i = r.get(int(t))
        if i is not None: o[k] = P[i]
    return o
K3 = np.load(K3_P); GATE["AL"] = bitwise(align(P3, E_ts, E4), K3); GATE["AL"]["PASS"] = GATE["AL"]["bitwise"]
OUT = {}
for k in ("K0", "K1", "K0f"):
    p3 = T4 + f"/kings/{k}_v3axis.npy"; p4 = T4 + f"/kings/{k}_v4axis.npy"
    np.save(p3, PRED[k]); A4 = align(PRED[k], E_ts, E4); np.save(p4, A4)
    OUT[k] = dict(v3axis=p3, v3axis_sha256=sha(p3), v4axis=p4, v4axis_sha256=sha(p4), finite_cells=int(np.isfinite(PRED[k]).sum()),
                  first_finite_anchor=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(E_ts[np.nonzero(np.isfinite(PRED[k]).any(1))[0][0]]))))
OUT["K0_v4axis_equals_SLOW_v3_on_v4axis"] = bitwise(np.load(OUT["K0"]["v4axis"]), K3)
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, inputs=INPUTS, params=PARAMS, lightgbm=lgb.__version__, numpy=np.__version__,
          folds=FOLD, gates=GATE, outputs=OUT, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}),
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(T4 + "/receipts/RECEIPT_T4_kings.json", "w"), indent=1, default=str)
print(json.dumps(dict(gates={k: v for k, v in GATE.items() if k != "S0"}, S0_PASS=GATE["S0_PASS"], outputs=OUT), indent=1, default=str))
assert GATE["K26"]["PASS"], "GATE K26 FAIL — stop (arms would not be the research king)"
assert GATE["S0_PASS"], "GATE S0 FAIL — stop"
assert GATE["AL"]["PASS"], "GATE AL FAIL"
print("DONE_t4_kings", RC["wall_s"])
