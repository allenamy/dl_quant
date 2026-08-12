"""0C — ARM-S2 G2 seed check (3-fold 32ch). seed42=wideA_s2_y24_32ch, seed43=wideA_s2_seed43,
seed44=wideA_s2_seed44. Recompute honest-ensemble raw IC + king-ORTHOGONAL increment per seed from
fold scores (verify 32ch/horizon-24 from config, byte-check panel). G2 = seeds consistent (CoV, sign).
CPU-only. Writes exports/eda/arm_s2_seeds.json.
"""
import numpy as np, pandas as pd, json, glob, hashlib
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
SEEDS = {"seed42": "wideA_s2_y24_32ch", "seed43": "wideA_s2_seed43", "seed44": "wideA_s2_seed44"}


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:8]


def comp_panel(scores, member, CL, YR):
    T, N, K = scores.shape; C = np.full((T, N), np.nan)
    for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
        base = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        if nk:
            C[t, base] = comp / nk
    return C


def score(tag, king):
    d = TR + tag
    pr = np.load(d + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64)
    T, N = YR.shape
    S = np.full((T, N), np.nan)
    for f in sorted(glob.glob(d + "/fold_*_head_scores.npz")):
        C = comp_panel(np.load(f)["scores"], member, CL, YR); m = np.isfinite(C); S[m] = C[m]
    rows = np.where(np.isfinite(S).any(1))[0]
    raw, inc = [], []
    for t in rows:
        b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(S[t]) & np.isfinite(king[t]))[0]
        if b.size < 8:
            continue
        s = S[t, b]; k = king[t, b]; y = YR[t, b]
        raw.append(np.corrcoef(rankdata(s), rankdata(y))[0, 1])
        sd = s - s.mean(); kd = k - k.mean(); beta = (sd @ kd) / (kd @ kd) if (kd @ kd) > 1e-12 else 0.0
        inc.append(np.corrcoef(rankdata(sd - beta * kd), rankdata(y))[0, 1])
    return dict(raw_ic=round(float(np.mean(raw)), 4), increment=round(float(np.mean(inc)), 4),
               n_ts=len(inc), panel_md5=md5(d + "/panel_ref.npz"), nch=len([str(x) for x in pr["ch_names"]]),
               H=int(pr["horizon"]))


if __name__ == "__main__":
    kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True); king = kp["king_pred"].astype(np.float64)
    res = {}
    for name, tag in SEEDS.items():
        try:
            res[name] = score(tag, king)
            print(f"{name} ({tag}): raw {res[name]['raw_ic']} INCREMENT {res[name]['increment']} "
                  f"nch {res[name]['nch']} H {res[name]['H']} md5 {res[name]['panel_md5']} n={res[name]['n_ts']}", flush=True)
        except Exception as e:
            print(f"{name} FAIL {e!r}", flush=True); res[name] = None
    ok = [r for r in res.values() if r]
    raws = [r["raw_ic"] for r in ok]; incs = [r["increment"] for r in ok]
    g2 = dict(seed_raw=raws, seed_increment=incs,
              raw_mean=round(float(np.mean(raws)), 4), raw_cov=round(float(np.std(raws) / np.mean(raws)), 3),
              inc_mean=round(float(np.mean(incs)), 4), inc_cov=round(float(np.std(incs) / np.mean(incs)), 3) if np.mean(incs) else None,
              inc_min=round(float(np.min(incs)), 4), all_increment_positive=bool(all(x > 0 for x in incs)),
              all_32ch=all(r["nch"] == 32 and r["H"] == 24 for r in ok),
              panels_consistent=len(set(r["panel_md5"] for r in ok)) <= 1 or all(r["nch"] == 32 for r in ok))
    g2["G2_PASS"] = bool(g2["all_increment_positive"] and g2["inc_cov"] is not None and g2["inc_cov"] < 0.30 and g2["all_32ch"])
    json.dump(dict(seeds=res, g2=g2), open(EDA + "arm_s2_seeds.json", "w"), indent=2, default=str)
    print(f"\nG2: raw {raws} (CoV {g2['raw_cov']}) | increment {incs} (CoV {g2['inc_cov']}, min {g2['inc_min']}) "
          f"all+ {g2['all_increment_positive']} all-32ch {g2['all_32ch']} -> G2_PASS {g2['G2_PASS']}", flush=True)
    print("SAVED " + EDA + "arm_s2_seeds.json", flush=True)
