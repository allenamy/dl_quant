"""INSTRUMENT-2 / GATE B device: regime composition of every candidate evaluation window.
Regime variables and labelling are the ROUND-2 ones, read from trackF/regime_labels.npz
(sig_fund = 1e4*xsec sd of 8h-equiv funding; disp24 = xsec sd of f_rev_24h; expanding-median
split, BURN=2190, label at i uses strictly past rows -> verified future-shuffle invariant).
Contrast labelling (descriptive only, NOT tradable): full-sample median split of the same two
variables, so the composition statement does not inherit the expanding median's trend artefact.
Book axis = the archived A0 dyn s42 replay (10039 anchors); warm-up = first LOOK=900 anchors (E-0911-A).
"""
import numpy as np, json, time, calendar
R = "/workspace/uplift_2026-09-11/r19_trackF_reindex/fixed_trackF"
OUT = "/workspace/uplift_2026-09-11/r19_trackF_reindex/out_r3_gates"
Z = np.load(f"{R}/regime_labels.npz", allow_pickle=True)
ts_r = Z["ts"].astype(np.int64); LAB = np.asarray(Z["lab"]); LF = np.asarray(Z["lf"]); LD = np.asarray(Z["ld"])
V = np.load(f"{R}/regime_vars.npz", allow_pickle=True)
COLS = [str(c) for c in V["cols"]]; A = V["V"]; K = {c: i for i, c in enumerate(COLS)}
assert np.array_equal(A[:, 0].astype(np.int64), ts_r)
sig = A[:, K["sig_fund"]]; dsp = A[:, K["disp24"]]

# ---- contrast labelling: full-sample median (descriptive) ----
ms, md = np.nanmedian(sig), np.nanmedian(dsp)
LAB_FS = np.full(len(ts_r), -1, np.int8)
ok = np.isfinite(sig) & np.isfinite(dsp)
LAB_FS[ok] = (sig[ok] > ms).astype(np.int8) * 2 + (dsp[ok] > md).astype(np.int8)
NAMES = {-1: "UNLAB", 0: "LL", 1: "LH", 2: "HL", 3: "HH"}

# ---- book axis ----
AA = np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz", allow_pickle=True)
CO = [str(c) for c in np.asarray(AA["cols"]).ravel()]; C = {c: i for i, c in enumerate(CO)}
Rr = AA["d30_n2_c42_rec"]; ts_b = np.round(Rr[:, 0]).astype(np.int64)
g_b = Rr[:, C["net_ex"]] / Rr[:, C["gross_total"]]
WARM = 900
warm_cut = ts_b[WARM]          # first anchor kept post-warm
lmap  = {int(t): LAB[i]    for i, t in enumerate(ts_r)}
lmapF = {int(t): LAB_FS[i] for i, t in enumerate(ts_r)}
lb  = np.array([lmap .get(int(t), -1) for t in ts_b])
lbF = np.array([lmapF.get(int(t), -1) for t in ts_b])

T = lambda y, m, d, h=0: calendar.timegm((y, m, d, h, 0, 0))
HI = T(2026, 8, 10, 20)
WINDOWS = {
 "FROZEN_2025-03-01..2026-08-10_20Z": (T(2025, 3, 1), HI),
 "2024on..2026-08-10":                (T(2024, 1, 1), HI),
 "F23_2023-01-01..2026-08-10":        (T(2023, 1, 1), HI),
 "FULLCYCLE_postwarm..2026-08-10":    (int(warm_cut), HI),
 "FULLCYCLE_postwarm_ALL(incl 08-31)":(int(warm_cut), int(ts_b[-1])),
 "REF_full_history_all_anchors":      (int(ts_b[0]), int(ts_b[-1])),
 "REF_full_history_LABELLED_only":    (int(ts_b[0]), int(ts_b[-1])),
}
def comp(lo, hi, lab, restrict_labelled=False):
    m = (ts_b >= lo) & (ts_b <= hi)
    if restrict_labelled: m &= (lab >= 0)
    n = int(m.sum())
    out = {"n_anchors": n}
    for L in (-1, 0, 1, 2, 3):
        out[NAMES[L]] = round(float((lab[m] == L).mean()), 4) if n else None
    lo_ = lab[m]; nl = int((lo_ >= 0).sum())
    out["n_labelled"] = nl
    out["HH_share_of_labelled"] = round(float((lo_ == 3).sum() / nl), 4) if nl else None
    out["g_mean_bps"] = round(float(g_b[m].mean()), 4) if n else None
    out["sharpe"] = round(float(g_b[m].mean() / g_b[m].std(ddof=1) * np.sqrt(2190)), 3) if n > 3 else None
    out["se_sharpe"] = round(float(np.sqrt(2190 / n)), 3) if n else None
    return out

res = {"labelling_expanding_median_round2": {}, "labelling_fullsample_median_contrast": {}}
for nm, (lo, hi) in WINDOWS.items():
    rl = nm == "REF_full_history_LABELLED_only"
    res["labelling_expanding_median_round2"][nm] = comp(lo, hi, lb, rl)
    res["labelling_fullsample_median_contrast"][nm] = comp(lo, hi, lbF, rl)

# ---- L1 distance of each window's cell mix vs the reference mix (labelled anchors only) ----
def mix(lo, hi, lab):
    m = (ts_b >= lo) & (ts_b <= hi) & (lab >= 0)
    n = int(m.sum())
    return (np.array([float((lab[m] == L).mean()) for L in (0, 1, 2, 3)]) if n else np.full(4, np.nan)), n
for key, lab in (("labelling_expanding_median_round2", lb), ("labelling_fullsample_median_contrast", lbF)):
    ref, nref = mix(int(ts_b[0]), int(ts_b[-1]), lab)
    res[key]["_REFERENCE_MIX_LLLHHLHH"] = [round(float(x), 4) for x in ref] + ["n=%d" % nref]
    for nm, (lo, hi) in WINDOWS.items():
        w, nw = mix(lo, hi, lab)
        res[key][nm]["L1_vs_reference"] = round(float(np.abs(w - ref).sum()), 4)
        res[key][nm]["maxcell_share"] = round(float(np.nanmax(w)), 4)
        res[key][nm]["eff_cells_1_over_sumsq"] = round(float(1.0 / np.nansum(w * w)), 3)

# ---- descriptive regime-variable levels per window ----
rmap = {int(t): i for i, t in enumerate(ts_r)}
res["regime_var_levels"] = {}
for nm, (lo, hi) in WINDOWS.items():
    idx = [rmap[int(t)] for t in ts_b if (lo <= t <= hi) and int(t) in rmap]
    if not idx: continue
    res["regime_var_levels"][nm] = {"n": len(idx),
        "sig_fund_mean": round(float(np.nanmean(sig[idx])), 3), "sig_fund_med": round(float(np.nanmedian(sig[idx])), 3),
        "disp24_mean": round(float(np.nanmean(dsp[idx])), 5), "disp24_med": round(float(np.nanmedian(dsp[idx])), 5)}
res["_meta"] = {"full_sample_median_sig_fund": round(float(ms), 4), "full_sample_median_disp24": round(float(md), 6),
                "warm_cut_ts": int(warm_cut), "warm_cut_utc": time.strftime("%F %HZ", time.gmtime(int(warm_cut))),
                "n_book_anchors": len(ts_b), "BURN_round2": 2190}
json.dump(res, open(OUT + "/regime_composition.json", "w"), indent=1)
print(json.dumps(res, indent=1))
