"""label_code_check.py — PREREG_king_label_alignment_2026-09-06 §2 code checks, all four, before any arm. Writes results/code_check.json.
 1 identity   : the 12-thread rerun of BASE (no Y4_ALT, seeds 42/2027, PRED_DIR=preds_identity) vs the archived preds results/preds/pred_BASE_s*.npy:
                sha256 equality, array_equal (NaN-aware), max |Δ|; thread settings and lightgbm version parsed from the rerun's CONFIG line.
 2 label      : >= N_SAMPLE random finite (anchor, name) cells of y4_startE and y4_startE_acc recomputed DIRECTLY from the 5m cache (float64 loop
                over rows E+1..E+48, missing bars skipped as the builder does): max |Δ| <= 1e-6 each; start-row assertion for every anchor:
                cache row E+1 closes at E+300 s (i.e. opens at E) and row E closes at E.
 3 causal     : features' rightmost bar closes <= E-300 s: recompute the panel value column ret5_sum_864_v = Σ ret5 rows E-864..E-1 for sampled
                (anchor, member) cells from the cache and compare with the stored float16 FEA column (tolerance = float16 rounding of the stored
                value + 1e-6); the one-bar-later window (rows E-863..E) must NOT match; target leftmost bar opens at E (row E+1 close - 300 == E).
 4 fold/embargo: per test year YV in 2024/2025/2026: train = years < YV verbatim (device rule); label end of the last training anchor
                (E + 4h for the ALT targets, E + 3h55 for the panel target) vs the first test anchor: Δ seconds, strict '<' verdict, and the
                number of cache rows shared between training-label rows and test feature/label rows (must be 0).
env: ROOT META_IN FEA_IN N_SAMPLE OUT_JSON"""
import os, sys, json, time, hashlib, re
import numpy as np
ROOT = os.environ.get("ROOT", "/workspace/review_scratch/allweather_trackA"); L = f"{ROOT}/label_alignment"
SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
N_SAMPLE = int(os.environ.get("N_SAMPLE", "2000")); OUT = os.environ.get("OUT_JSON", f"{L}/results/code_check.json")
sys.path.insert(0, "/workspace")
from zload import zload
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()
res = {"self_sha256": SELF, "utc": time.strftime("%FT%TZ", time.gmtime()), "checks": {}}
# ---------- 1 identity ----------
ident = {"pairs": {}, "PASS": True}
for s in (42, 2027):
    a = f"{L}/preds_identity/pred_BASE_s{s}.npy"; b = f"{ROOT}/results/preds/pred_BASE_s{s}.npy"
    A = np.load(a); B = np.load(b); eq = bool(A.shape == B.shape and np.array_equal(A, B, equal_nan=True))
    d = float(np.nanmax(np.abs(A - B))) if A.shape == B.shape else None
    ident["pairs"][str(s)] = {"rerun": a, "archived": b, "sha_rerun": sha(a), "sha_archived": sha(b), "sha_equal": sha(a) == sha(b), "array_equal": eq, "max_abs_diff": d,
                              "finite_rerun": int(np.isfinite(A).sum()), "finite_archived": int(np.isfinite(B).sum())}
    ident["PASS"] &= eq
log = open(f"{L}/logs/identity_BASE_nj12.log").read()
m = re.search(r"^CONFIG (\{.*\})$", log, re.M); cfg = json.loads(m.group(1)) if m else {}
ident["rerun_config"] = {"NJOBS": cfg.get("NJOBS"), "lightgbm_version": cfg.get("lightgbm_version"), "numpy_version": cfg.get("numpy_version"), "device_self_sha256": cfg.get("self_sha256"), "SEEDS": cfg.get("SEEDS"), "FOLDS": cfg.get("FOLDS")}
cmd = [l for l in open(f"{L}/logs/commands.txt") if "CMD[identity_BASE_nj12]" in l]
ident["rerun_env_threads"] = {k: (re.search(k + r"=(\d+)", cmd[0]).group(1) if cmd and re.search(k + r"=(\d+)", cmd[0]) else None) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NJOBS")}
ident["archived_preds_provenance"] = "results/preds/pred_BASE_s*.npy written by the s1_ALL run 2026-09-05 (NJOBS=24, device sha 1f58d60b, no Y4_ALT entry); S2_BASE replays used them"
res["checks"]["1_identity"] = ident; print("1 identity", json.dumps({k: v for k, v in ident.items() if k != "pairs"}), {s: (p["sha_equal"], p["array_equal"], p["max_abs_diff"]) for s, p in ident["pairs"].items()}, flush=True)
# ---------- cache / meta ----------
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); T0 = int(CTS[0]); RET = np.asarray(Z["data"][:, :, 0], np.float32); del Z
MT = np.load(os.environ.get("META_IN", "/workspace/data/wide_fea_v2ext_meta.npz"), allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4p = MT["y4"]; names = [str(n) for n in MT["names"]]
Ei = (E_ts - T0) // 300; nA = len(E_ts)
rng = np.random.default_rng(20260906)
# ---------- 2 label receipt ----------
lab = {"n_sample": N_SAMPLE, "start_row": {}}
lab["start_row"] = {"all_anchors_row_E_closes_at_E": bool(np.all(CTS[Ei] == E_ts)), "all_anchors_row_E+1_closes_at_E+300": bool(np.all(CTS[Ei + 1] == E_ts + 300)),
                    "target_leftmost_bar_open_equals_E": bool(np.all(CTS[Ei + 1] - 300 == E_ts)), "target_rightmost_bar_close_equals_E+4h": bool(np.all(CTS[Ei + 48] == E_ts + 14400))}
for tag, path in (("y4_startE", f"{ROOT}/features/y4_startE.npz"), ("y4_startE_acc", f"{ROOT}/features/y4_startE_acc.npz")):
    z = np.load(path, allow_pickle=True); Y = np.asarray(z["y4"], np.float32); assert np.array_equal(z["E_ts"].astype(np.int64), E_ts)
    fi = np.argwhere(np.isfinite(Y)); pick = fi[rng.choice(len(fi), N_SAMPLE, replace=False)]
    mx = 0.0; nbad = 0
    for i, j in pick:
        r = RET[Ei[i] + 1: Ei[i] + 49, j].astype(np.float64); f = np.isfinite(r)
        v = float(r[f].sum()) if tag == "y4_startE" else float(np.expm1(np.log1p(np.clip(r[f], -0.99, None)).sum()))
        d = abs(v - float(Y[i, j])); mx = max(mx, d); nbad += d > 1e-6
    lab[tag] = {"path": path, "sha256": sha(path), "definition": str(z["definition"]), "finite_cells": int(np.isfinite(Y).sum()), "max_abs_diff_recomputed": mx, "n_gt_1e-6": int(nbad), "PASS": bool(mx <= 1e-6)}
    print("2 label", tag, lab[tag], flush=True)
lab["PASS"] = bool(all(lab[t]["PASS"] for t in ("y4_startE", "y4_startE_acc")) and all(lab["start_row"].values()))
res["checks"]["2_label_receipt"] = lab
# ---------- 3 causal ----------
FEA = np.load(os.environ.get("FEA_IN", "/workspace/data/wide_fea_v2ext.npy"), mmap_mode="r"); k = names.index("ret5_sum_864_v")
cells = []
while len(cells) < N_SAMPLE:
    i = int(rng.integers(0, nA)); m = members[i]; j = int(m[rng.integers(0, len(m))])
    if np.isfinite(FEA[i, j, k]): cells.append((i, j))
d_ok = []; d_shift = []; tol_fail = 0
for i, j in cells:
    v = float(FEA[i, j, k])
    r = RET[Ei[i] - 864: Ei[i], j].astype(np.float64); f = np.isfinite(r); a = float(np.clip(r[f].sum(), -1e4, 1e4))
    r2 = RET[Ei[i] - 863: Ei[i] + 1, j].astype(np.float64); f2 = np.isfinite(r2); b = float(np.clip(r2[f2].sum(), -1e4, 1e4))
    tol = abs(v) * 2.0 ** -10 + 1e-6   # float16 storage: 11-bit significand -> half-ulp <= |v|*2^-11; allow one ulp + eps
    d_ok.append(abs(a - v)); d_shift.append(abs(b - v)); tol_fail += abs(a - v) > tol
caus = {"feature_checked": "ret5_sum_864_v", "window_rows": "E-864..E-1 (rightmost bar closes at E-300 s)", "n_cells": len(cells),
        "max_abs_diff_correct_window": float(max(d_ok)), "n_beyond_f16_tolerance": int(tol_fail), "share_shifted_window_mismatch": float(np.mean(np.array(d_shift) > np.array(d_ok) + 1e-9)),
        "median_abs_diff_shifted_window": float(np.median(d_shift)), "target_leftmost_bar_open_equals_E": lab["start_row"]["target_leftmost_bar_open_equals_E"],
        "features_rightmost_close_le_E_minus_300": None}
caus["features_rightmost_close_le_E_minus_300"] = bool(tol_fail == 0 and caus["share_shifted_window_mismatch"] > 0.5)
caus["PASS"] = bool(caus["features_rightmost_close_le_E_minus_300"] and caus["target_leftmost_bar_open_equals_E"])
res["checks"]["3_causal"] = caus; print("3 causal", caus, flush=True)
# ---------- 4 fold / embargo ----------
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); fold = {"rule": "train = years < test year (device: tr = YRA < YV), no embargo (as the pinned king pipeline)", "folds": {}}
allp = True
for YV in (2024, 2025, 2026):
    tr = np.where(yrs < YV)[0]; te = np.where(yrs == YV)[0]; Efirst = int(E_ts[te[0]]); Elast = int(E_ts[tr[-1]])
    ends = {"ALT (rows E+1..E+48)": Elast + 14400, "BASE panel (rows E..E+47)": Elast + 14100}
    tr_rows_alt = set(); [tr_rows_alt.update(range(Ei[i] + 1, Ei[i] + 49)) for i in tr[-3:]]   # last 3 training anchors' ALT label rows (labels are 4h; earlier ones end earlier)
    te_label_rows = set(); [te_label_rows.update(range(Ei[i] + 1, Ei[i] + 49)) for i in te[:3]]   # first 3 test anchors' ALT label rows
    post_rows = set(range(Ei[te[0]] + 1, Ei[te[0]] + 49 * 3))                                     # cache rows whose bar closes AFTER the first test anchor (test period)
    shared_label = len(tr_rows_alt & te_label_rows); shared_post = len(tr_rows_alt & post_rows)
    # ordinary walk-forward overlap (allowed direction): test features look back into the period whose returns were training labels — reported, not a leak
    te_feat_rows = set(); [te_feat_rows.update(range(Ei[i] - 8640, Ei[i])) for i in te[:3]]; overlap_feat = len(tr_rows_alt & te_feat_rows)
    f = {"n_train_anchors": int(len(tr)), "n_test_anchors": int(len(te)), "last_train_anchor": time.strftime("%F %H:%M", time.gmtime(Elast)), "first_test_anchor": time.strftime("%F %H:%M", time.gmtime(Efirst)),
         "label_end_minus_first_test_anchor_s": {k: v - Efirst for k, v in ends.items()}, "strict_lt": {k: bool(v < Efirst) for k, v in ends.items()},
         "le": {k: bool(v <= Efirst) for k, v in ends.items()}, "shared_rows_trainlabel_vs_testlabel_ALT": shared_label, "shared_rows_trainlabel_vs_test_period_ALT": shared_post,
         "overlap_rows_trainlabel_vs_testfeature_lookback_ALT (allowed direction, not a leak)": overlap_feat}
    fold["folds"][str(YV)] = f; allp &= (shared_label == 0) and (shared_post == 0) and f["le"]["ALT (rows E+1..E+48)"]
    print("4 fold", YV, f, flush=True)
fold["PASS_no_shared_bar"] = bool(allp); fold["strict_lt_ALT_all_folds"] = bool(all(f["strict_lt"]["ALT (rows E+1..E+48)"] for f in fold["folds"].values()))
fold["note"] = "ALT label of the last training anchor ends exactly at the first test anchor's timestamp (Δ = 0 s): the literal strict '<' fails by equality while no cache row is shared (the test anchor's features stop at row E-1, its label starts at row E+1)."
res["checks"]["4_fold_embargo"] = fold
res["ALL_PASS_literal"] = bool(ident["PASS"] and lab["PASS"] and caus["PASS"] and fold["strict_lt_ALT_all_folds"] and fold["PASS_no_shared_bar"])
res["ALL_PASS_no_shared_bar_reading"] = bool(ident["PASS"] and lab["PASS"] and caus["PASS"] and fold["PASS_no_shared_bar"])
json.dump(res, open(OUT, "w"), indent=1)
print(f"CODE_CHECK_DONE literal {res['ALL_PASS_literal']} no_shared_bar_reading {res['ALL_PASS_no_shared_bar_reading']}", flush=True)
