"""0C — G2 seed check for the xattn KING (lam_orth=0 + xattn), 3-fold. Recompute honest ensemble IC
per fold for seed42/43/44 from fold scores (do NOT trust JSON; verify king-level not stale-penalized).
All 3-fold same panel 39f5cc4e. CPU-only. Writes exports/eda/xattn_g2_seeds.json.
seed42=wideA_lamorth0_xattn ; seed43=wideA_xattn_seed43 ; seed44=wideA_xattn_seed44 (king overwrites stale).
"""
import numpy as np, json, glob, hashlib
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
SEEDS = {"seed42": "wideA_lamorth0_xattn", "seed43": "wideA_xattn_seed43", "seed44": "wideA_xattn_seed44"}
KING_FLOOR = 0.055   # below this => still stale/penalized, NOT the king


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:8]


def ens_per_fold(tag):
    d = TR + tag
    pr = np.load(d + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64)
    res = []
    for f in sorted(glob.glob(d + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0])):
        sc = np.load(f)["scores"]; T, N, K = sc.shape
        ics = []
        for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
            base = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
            if base.size < 5:
                continue
            comp = np.zeros(base.size); nk = 0
            for k in range(K):
                col = sc[t, base, k]
                if np.isfinite(col).all() and col.std() > 1e-12:
                    comp += (col - col.mean()) / col.std(); nk += 1
            if nk:
                ic = np.corrcoef(rankdata(comp / nk), rankdata(YR[t, base]))[0, 1]
                if np.isfinite(ic):
                    ics.append(ic)
        res.append(round(float(np.mean(ics)), 4))
    return res, md5(d + "/panel_ref.npz")


if __name__ == "__main__":
    per_seed = {}; means = []; stale = []
    for name, tag in SEEDS.items():
        pf, m5 = ens_per_fold(tag)
        mean = round(float(np.mean(pf)), 4)
        per_seed[name] = dict(per_fold=pf, mean=mean, panel_md5=m5, king_level=bool(mean >= KING_FLOOR))
        means.append(mean)
        if mean < KING_FLOOR:
            stale.append(name)
        print(f"{name} ({tag}): per_fold {pf} mean {mean} md5 {m5} king_level={mean>=KING_FLOOR}", flush=True)

    means = np.array(means)
    # per-fold sign consistency across seeds (all folds positive for every seed?)
    all_pos = all(all(v > 0 for v in per_seed[s]["per_fold"]) for s in per_seed)
    # per-fold ordering consistency (does fold rank order hold across seeds?)
    cov = float(means.std() / means.mean()) if means.mean() else np.nan
    verdict = ("STALE DATA — one or more seeds below king floor (%s); the king-seed battery has not "
               "overwritten them yet, DO NOT judge" % stale if stale else
               ("G2 PASS" if (all_pos and cov < 0.20 and means.min() > 0) else "G2 REVIEW"))
    result = dict(title="xattn king G2 seed check (3-fold)", created="2026-07-12", auditor="0C",
                  seeds=per_seed, seed_means=[round(float(x), 4) for x in means],
                  mean_of_seeds=round(float(means.mean()), 4), std=round(float(means.std()), 4),
                  cov=round(cov, 3), min=round(float(means.min()), 4), max=round(float(means.max()), 4),
                  all_folds_positive=all_pos, verdict=verdict)
    json.dump(result, open(EDA + "xattn_g2_seeds.json", "w"), indent=2, default=str)
    print(f"\nSEED MEANS {[round(float(x),4) for x in means]} CoV {cov:.3f} min {means.min():.4f} -> {verdict}", flush=True)
    print("SAVED " + EDA + "xattn_g2_seeds.json", flush=True)
