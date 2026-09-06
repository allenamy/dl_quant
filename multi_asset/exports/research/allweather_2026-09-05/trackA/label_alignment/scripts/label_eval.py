"""label_eval.py — PREREG_king_label_alignment_2026-09-06 §3 score-level readings. For each arm prediction file (BASE / ALT_SUM / ALT_ACC × seeds):
mean per-anchor Spearman rank-IC against FOUR targets — panel y4 (meta, rows E..E+47), y4_startE (Σ ret5 rows E+1..E+48), y4_startE_acc
(Π form, rows E+1..E+48), meta_exec25 (prod caliber Π over rows E+6..E+48 = executable window) — per fold 2024/2025/2026 and pooled 2024->26;
and the PAIRED per-anchor IC difference ALT − BASE (same seed) on every target with a UTC-day-block bootstrap CI95 (2000 resamples, seed 20260905)
per fold and pooled. The executable-window Δ (target meta_exec25) with its CI is the quantity used by the frozen reading §4 (A)/(B).
env: ROOT META_IN PRED_DIR (files pred_<ARM>_s<seed>.npy) ARMS (comma) SEEDS (comma) OUT_JSON"""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import spearmanr
ROOT = os.environ.get("ROOT", "/workspace/review_scratch/allweather_trackA"); L = f"{ROOT}/label_alignment"
SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
PRED_DIR = os.environ.get("PRED_DIR", f"{L}/preds"); ARMS = os.environ.get("ARMS", "BASE,ALT_SUM,ALT_ACC").split(","); SEEDS = [int(s) for s in os.environ.get("SEEDS", "42,2027").split(",")]
OUT = os.environ.get("OUT_JSON", f"{L}/results/label_eval.json"); NB = 2000; BSEED = 20260905
MT = np.load(os.environ.get("META_IN", "/workspace/data/wide_fea_v2ext_meta.npz"), allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; nA = len(E_ts)
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); days = E_ts // 86400
TGT = {"panel_y4_E-5m": np.asarray(MT["y4"], np.float32)}
for tag, p in (("y4_startE_sum", f"{ROOT}/features/y4_startE.npz"), ("y4_startE_acc", f"{ROOT}/features/y4_startE_acc.npz"), ("exec25_prod", f"{ROOT}/features/meta_exec25.npz")):
    z = np.load(p, allow_pickle=True); assert np.array_equal(z["E_ts"].astype(np.int64), E_ts), p; TGT[tag] = np.asarray(z["y4"], np.float32)
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def boot(x, d):
    ok = np.isfinite(x); x = x[ok]; d = d[ok]
    if len(x) < 10: return [None, None]
    ud, inv = np.unique(d, return_inverse=True); s1 = np.bincount(inv, x); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(BSEED); idx = rng.integers(0, len(ud), size=(NB, len(ud))); m = s1[idx].sum(1) / c[idx].sum(1)
    return [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)]
IC = {}   # (arm, seed, target) -> per-anchor IC array (NaN outside test rows)
res = {"self_sha256": SELF, "targets": {k: {"finite_cells": int(np.isfinite(v).sum())} for k, v in TGT.items()}, "bootstrap": {"blocks": "UTC day", "n": NB, "seed": BSEED}, "ic": {}, "delta_vs_BASE": {}}
WIN = {"2024": yrs == 2024, "2025": yrs == 2025, "2026": yrs == 2026, "2024->26": yrs >= 2024}
for arm in ARMS:
    for s in SEEDS:
        p = f"{PRED_DIR}/pred_{arm}_s{s}.npy"; P = np.load(p); rows = np.where(np.isfinite(P).any(1))[0]
        for tg, Y in TGT.items():
            v = np.full(nA, np.nan)
            for i in rows: m = members[i]; v[i] = sp(P[i, m], Y[i, m])
            IC[(arm, s, tg)] = v
        res["ic"][f"{arm}_s{s}"] = {"pred": p, "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()[:16], "n_rows": int(len(rows)),
                                    "by_target": {tg: {w: round(float(np.nanmean(IC[(arm, s, tg)][mk])), 4) for w, mk in WIN.items()} for tg in TGT}}
        print(f"IC {arm} s{s}: " + " | ".join(f"{tg} " + "/".join(f"{res['ic'][f'{arm}_s{s}']['by_target'][tg][w]:.4f}" for w in WIN) for tg in TGT), flush=True)
for arm in ARMS:
    if arm == "BASE": continue
    for s in SEEDS:
        res["delta_vs_BASE"][f"{arm}_s{s}"] = {}
        for tg in TGT:
            d = IC[(arm, s, tg)] - IC[("BASE", s, tg)]
            res["delta_vs_BASE"][f"{arm}_s{s}"][tg] = {w: {"mean": round(float(np.nanmean(d[mk])), 4), "ci95": boot(d[mk], days[mk]), "n": int(np.isfinite(d[mk]).sum())} for w, mk in WIN.items()}
        e = res["delta_vs_BASE"][f"{arm}_s{s}"]["exec25_prod"]["2024->26"]
        print(f"DELTA {arm} s{s} exec25 2024->26 {e['mean']:+.4f} CI {e['ci95']} | " + " | ".join(f"{tg} {res['delta_vs_BASE'][f'{arm}_s{s}'][tg]['2024->26']['mean']:+.4f} {res['delta_vs_BASE'][f'{arm}_s{s}'][tg]['2024->26']['ci95']}" for tg in TGT if tg != "exec25_prod"), flush=True)
json.dump(res, open(OUT, "w"), indent=1); print("LABEL_EVAL_DONE", flush=True)
