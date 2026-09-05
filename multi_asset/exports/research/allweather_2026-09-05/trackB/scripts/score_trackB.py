"""score_trackB.py — Track B score level (diagnostic, not in the frozen gate): per-anchor rank IC (Spearman over members with finite score and finite y4s,
>= 30 pairs) by year for each fit vs the same-seed ext baseline; plus the side-conditional IC (within the bottom half of the model's own ranking = the
names it shorts, and within the top half = the names it longs; PREREG_l1ss ③ mechanism intermediate). Paired ΔIC with UTC-day-block bootstrap 2000,
seed 20260905. Also summarises the DRO era-weight logs from the fit json (max W, min W, effective number of eras 1/Σp² at the last epoch, per fold).
usage: score_trackB.py <LABEL:SEED> [...]   → results/score_trackB.json"""
import sys, json, time, calendar
import numpy as np
from scipy.stats import spearmanr
B = "/workspace/review_scratch/allweather_trackB"; NB = 2000; SEED = 20260905
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; Y4 = A["y4s"]; yrs = A["yrs"].astype(int); nA = len(E)
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); days = E // 86400
rng = np.random.default_rng(SEED)
def boot(x, m):
    v = x[m]; d = days[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud); s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "mean": float(v.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5)), "P>0": float((means > 0).mean())}
def ic_series(P):
    ic = np.full(nA, np.nan); icl = np.full(nA, np.nan); ics = np.full(nA, np.nan)
    for i in range(nA):
        if not np.isfinite(P[i]).any(): continue
        m = MEM[i]; s = P[i, m]; y = Y4[i, m]; ok = np.isfinite(s) & np.isfinite(y)
        if ok.sum() < 30: continue
        s, y = s[ok], y[ok]; ic[i] = spearmanr(s, y).correlation; med = np.median(s); lo = s <= med; hi = s > med
        if lo.sum() >= 15: ics[i] = spearmanr(s[lo], y[lo]).correlation
        if hi.sum() >= 15: icl[i] = spearmanr(s[hi], y[hi]).correlation
    return ic, icl, ics
WIN = {"2023": yrs == 2023, "2024": yrs == 2024, "2025": yrs == 2025, "2026<=cut": (yrs == 2026) & (E <= CUT), "2024->26<=cut": (yrs >= 2024) & (E <= CUT)}
OUT = {"levels": {}, "delta_vs_ext_baseline": {}, "dro": {}}; REF = {}
for spec in sys.argv[1:]:
    L, S = spec.split(":"); P = np.load(f"{B}/f8_out/preds/f10_V2MAIN_{L}_s{S}.npy")
    if S not in REF: REF[S] = ic_series(np.load(f"/workspace/f8_ext/preds/f10_V2MAIN_s{S}.npy"))
    ic, icl, ics = ic_series(P); r_ic, r_icl, r_ics = REF[S]
    for w, m in WIN.items():
        mm = m & np.isfinite(ic) & np.isfinite(r_ic)
        OUT["levels"][f"{L}_s{S}/{w}"] = {"n": int(mm.sum()), "IC": float(ic[mm].mean()), "IC_long_half": float(np.nanmean(icl[mm])), "IC_short_half": float(np.nanmean(ics[mm])),
                                          "ref_IC": float(r_ic[mm].mean()), "ref_IC_long_half": float(np.nanmean(r_icl[mm])), "ref_IC_short_half": float(np.nanmean(r_ics[mm]))}
        OUT["delta_vs_ext_baseline"][f"{L}_s{S}/{w}"] = {"dIC": boot(ic - r_ic, mm), "dIC_short_half": boot(np.nan_to_num(ics - r_ics), mm & np.isfinite(ics) & np.isfinite(r_ics)), "dIC_long_half": boot(np.nan_to_num(icl - r_icl), mm & np.isfinite(icl) & np.isfinite(r_icl))}
        d = OUT["delta_vs_ext_baseline"][f"{L}_s{S}/{w}"]; lv = OUT["levels"][f"{L}_s{S}/{w}"]
        print(f"{L}_s{S} {w:14s} n={mm.sum():5d} IC {lv['IC']:+.4f} (ref {lv['ref_IC']:+.4f}) ΔIC {d['dIC']['mean']:+.4f} [{d['dIC']['lo']:+.4f},{d['dIC']['hi']:+.4f}] | short-half IC {lv['IC_short_half']:+.4f} (ref {lv['ref_IC_short_half']:+.4f}) Δ {d['dIC_short_half']['mean']:+.4f} [{d['dIC_short_half']['lo']:+.4f},{d['dIC_short_half']['hi']:+.4f}] | long-half IC {lv['IC_long_half']:+.4f} (ref {lv['ref_IC_long_half']:+.4f}) Δ {d['dIC_long_half']['mean']:+.4f} [{d['dIC_long_half']['lo']:+.4f},{d['dIC_long_half']['hi']:+.4f}]", flush=True)
    J = json.load(open(f"{B}/f8_out/results/f10_V2MAIN_{L}_s{S}.json")); OUT["dro"][f"{L}_s{S}"] = {"dro_t": J.get("dro_t"), "ss_w": J.get("ss_w"), "folds": {}}
    for yv, f in J["folds"].items():
        dl = f.get("dro", [])
        if dl:
            last = dl[-1]; Wv = np.array(list(last["W"].values())); p = Wv / Wv.sum()
            OUT["dro"][f"{L}_s{S}"]["folds"][yv] = {"n_eras": len(Wv), "last_ep": last["ep"], "W_max": float(Wv.max()), "W_min": float(Wv.min()), "n_eff": float(1.0 / (p ** 2).sum()), "era_mean_net_last": last["era_mean_net"], "W_last": last["W"],
                                                    "W_max_by_epoch": [max(x["W"].values()) for x in dl], "argmax_era_by_epoch": [max(x["W"], key=x["W"].get) for x in dl]}
            print(f"{L}_s{S} fold {yv} DRO: eras {len(Wv)} last-epoch W max {Wv.max():.2f} min {Wv.min():.2f} n_eff {1.0/(p**2).sum():.2f}; argmax era by epoch {OUT['dro'][f'{L}_s{S}']['folds'][yv]['argmax_era_by_epoch']}")
        OUT["dro"][f"{L}_s{S}"]["folds"].setdefault(yv, {}).update({"net_mean_bps": f["net_mean_bps"], "es5_bps": f["es5_bps"], "turnover_mean": f["turnover_mean"], "best_va": f["best_va"], "alpha_final": f["alpha_final"]})
json.dump(OUT, open(f"{B}/results/score_trackB.json", "w"), indent=1); print("SCORE_DONE", flush=True)
