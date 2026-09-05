"""agreement.py — receipt (a) of PREREG AMENDMENT 1: per-anchor agreement between the new 2026-fold predictions (this campaign, ext data)
and (1) the existing OLD-generation file f10_V2MAIN_s{seed}.npy (port_w10 = /workspace/f8_2026-08-22, 09-01 same-device old-data run, to 2026-08-10),
(2) the 09-01 ext-data gate-run file /workspace/f8_ext/preds/f10_V2MAIN_s{seed}.npy (same recipe, same data, no saved model) — a same-recipe replication receipt.
Rank-IC vs dlw y4s (ext targets; overlap rows bitwise == old targets) per anchor; paired Δ with anchor s.e. and UTC-day-block s.e.
Prints JSON + a plain table. Read-only on all inputs."""
import numpy as np, json, time, sys, hashlib
from scipy.stats import spearmanr
ROOT = "/workspace/review_scratch/v2main_fold2026"
def ft(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def sha16(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
TE = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)
E = TE["E_ts"].astype(np.int64); y4s = TE["y4s"]; MEM = TE["members"]; yrs = TE["yrs"].astype(int); nA = len(E)
CUT = E[np.searchsorted(E, int(time.mktime(time.strptime("2026-08-10 20:00 UTC", "%Y-%m-%d %H:%M %Z"))) if False else 0)]  # placeholder, replaced below
import calendar
CUT = calendar.timegm(time.strptime("2026-08-10 20:00", "%Y-%m-%d %H:%M")); END = calendar.timegm(time.strptime("2026-08-30 20:00", "%Y-%m-%d %H:%M"))
i26 = np.where(yrs == 2026)[0]; iA = i26[E[i26] <= CUT]; iB = i26[E[i26] > CUT]
out = {"targets": "/workspace/dlw_ext/data/dlw_targets.npz", "n_2026": int(len(i26)), "n_overlap_to_0810": int(len(iA)), "n_0811_to_0830": int(len(iB)), "seeds": {}}
def pa_corr(P, Q, idx):
    v = []
    for i in idx:
        m = MEM[i]; a = P[i, m]; b = Q[i, m]; ok = np.isfinite(a) & np.isfinite(b)
        v.append(spearmanr(a[ok], b[ok]).correlation if ok.sum() >= 30 else np.nan)
    return np.array(v)
def ic(P, idx):
    v = []
    for i in idx:
        m = MEM[i]; a = P[i, m]; b = y4s[i, m]; ok = np.isfinite(a) & np.isfinite(b)
        v.append(spearmanr(a[ok], b[ok]).correlation if ok.sum() >= 30 else np.nan)
    return np.array(v)
def stats(v):
    v = v[np.isfinite(v)]; return {"n": int(len(v)), "mean": round(float(v.mean()), 4), "p5": round(float(np.percentile(v, 5)), 4), "min": round(float(v.min()), 4), "median": round(float(np.median(v)), 4)}
def paired(a, b, idx):
    d = a - b; ok = np.isfinite(d); d = d[ok]; days = (E[idx][ok] // 86400)
    ud, inv = np.unique(days, return_inverse=True); dm = np.bincount(inv, d) / np.bincount(inv)
    return {"n": int(len(d)), "mean_delta": round(float(d.mean()), 4), "se_anchor": round(float(d.std(ddof=1) / np.sqrt(len(d))), 4), "se_dayblock": round(float(dm.std(ddof=1) / np.sqrt(len(dm))), 4), "t_dayblock": (round(float(dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))), 2) if dm.std(ddof=1) > 0 else None), "n_days": int(len(dm))}
rows = []
for S in (42, 2027):
    new = np.load(f"{ROOT}/preds/f10_V2MAIN_ext2026_s{S}.npy"); old = np.load(f"/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s{S}.npy"); e01 = np.load(f"/workspace/f8_ext/preds/f10_V2MAIN_s{S}.npy")
    assert new.shape == (nA, 829) and e01.shape == (nA, 829) and old.shape == (10086, 829)
    oldp = np.full((nA, 829), np.nan, np.float32); oldp[:10086] = old
    fr = np.where(np.isfinite(new).any(1))[0]
    r = {"files": {"new": f"{ROOT}/preds/f10_V2MAIN_ext2026_s{S}.npy", "old": f"/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s{S}.npy", "ext0901": f"/workspace/f8_ext/preds/f10_V2MAIN_s{S}.npy"},
         "sha16": {"new": sha16(f"{ROOT}/preds/f10_V2MAIN_ext2026_s{S}.npy"), "old": sha16(f"/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s{S}.npy"), "ext0901": sha16(f"/workspace/f8_ext/preds/f10_V2MAIN_s{S}.npy")},
         "new_finite_rows": int(len(fr)), "new_first_finite": ft(E[fr[0]]), "new_last_finite": ft(E[fr[-1]]), "new_pre2026_finite_entries": int(np.isfinite(new[yrs < 2026]).sum()),
         "new_finite_entries_per_2026_row_mean": round(float(np.isfinite(new[i26]).sum(1).mean()), 1), "old_finite_entries_per_row_mean_overlap": round(float(np.isfinite(oldp[iA]).sum(1).mean()), 1)}
    c_no = pa_corr(new, oldp, iA); c_ne = pa_corr(new, e01, i26); c_oe = pa_corr(oldp, e01, iA)
    r["per_anchor_spearman"] = {"new_vs_old_overlap_0101_0810": stats(c_no), "new_vs_ext0901_2026_full": stats(c_ne), "new_vs_ext0901_0811_0830": stats(c_ne[np.isin(i26, iB)]), "old_vs_ext0901_overlap": stats(c_oe)}
    icn = ic(new, i26); ico = ic(oldp, i26); ice = ic(e01, i26); mA = np.isin(i26, iA); mB = ~mA
    r["rank_ic_vs_y4s"] = {"new_2026_full": stats(icn), "new_overlap_0101_0810": stats(icn[mA]), "new_0811_0830": stats(icn[mB]), "old_overlap_0101_0810": stats(ico[mA]),
                           "ext0901_2026_full": stats(ice), "ext0901_overlap": stats(ice[mA]), "ext0901_0811_0830": stats(ice[mB]),
                           "paired_new_minus_old_overlap": paired(icn[mA], ico[mA], iA), "paired_new_minus_ext0901_full2026": paired(icn, ice, i26), "paired_new_minus_ext0901_0811_0830": paired(icn[mB], ice[mB], iB)}
    # training-frame book proxy (trainer's own hard-rank test replay of the fold; NOT the final device caliber)
    def fold26(p):
        try: j = json.load(open(p)); f = j["folds"]["2026"]; return {k: f.get(k) for k in ("n_test", "net_mean_bps", "es5_bps", "turnover_mean", "best_va", "alpha_final", "wall_s")}
        except Exception as ex: return {"error": str(ex)}
    r["training_frame_fold2026"] = {"new": fold26(f"{ROOT}/results/f10_V2MAIN_ext2026_s{S}.json"), "ext0901_to_0830": fold26(f"/workspace/f8_ext/results/f10_V2MAIN_s{S}.json"), "old_to_0810": fold26(f"/workspace/f8_2026-08-22/results/f10_V2MAIN_s{S}.json")}
    r["new_vs_ext0901_2026_rows_bitwise_equal"] = bool(np.array_equal(np.nan_to_num(new[i26], nan=-9), np.nan_to_num(e01[i26], nan=-9)))
    out["seeds"][str(S)] = r
    rows.append(f"| s{S} | {r['per_anchor_spearman']['new_vs_old_overlap_0101_0810']['mean']} / {r['per_anchor_spearman']['new_vs_old_overlap_0101_0810']['p5']} / {r['per_anchor_spearman']['new_vs_old_overlap_0101_0810']['min']} | {r['per_anchor_spearman']['new_vs_ext0901_2026_full']['mean']} / {r['per_anchor_spearman']['new_vs_ext0901_2026_full']['p5']} / {r['per_anchor_spearman']['new_vs_ext0901_2026_full']['min']} | {r['rank_ic_vs_y4s']['new_overlap_0101_0810']['mean']} | {r['rank_ic_vs_y4s']['old_overlap_0101_0810']['mean']} | {r['rank_ic_vs_y4s']['paired_new_minus_old_overlap']['mean_delta']} ± {r['rank_ic_vs_y4s']['paired_new_minus_old_overlap']['se_dayblock']} | {r['rank_ic_vs_y4s']['new_0811_0830']['mean']} | {r['rank_ic_vs_y4s']['ext0901_0811_0830']['mean']} |")
json.dump(out, open(f"{ROOT}/results/agreement.json", "w"), indent=1)
print("| seed | ρ(new,old) overlap mean/p5/min | ρ(new,ext0901) 2026 mean/p5/min | IC new overlap | IC old overlap | Δ IC new−old (± day-block se) | IC new 08-11→08-30 | IC ext0901 08-11→08-30 |"); print("|---|---|---|---|---|---|---|---|"); print("\n".join(rows))
print(json.dumps(out, indent=1))
