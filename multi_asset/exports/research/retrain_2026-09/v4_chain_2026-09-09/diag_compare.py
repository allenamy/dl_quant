"""Compare the 202507 single-fold diagnostics: D2 (v4 data + f8_ext legs), D3 (ext data + f8_ext legs, retrained today), v4 CLIP fold (v4 data + v4 legs),
the 09-06 FIX7 fold model (ext data, trained 09-06; preds on ext features) and HF2 (same 09-06 model re-inferred on holefix features), in-service yearly.
Per-anchor Spearman: k0 IC (pred vs y4s), k-1 (pred vs previous anchor's y4s), and pairwise pred correlations, on the 202507 test anchors (members)."""
import numpy as np, time, json
from scipy.stats import spearmanr
def load_fold(p):
    z = np.load(p); return int(z["first_te"]), int(z["last_te"]), z["P"]
TG = np.load("/workspace/dlw_hf3/data/dlw_targets.npz", allow_pickle=True); E = TG["E_ts"].astype(np.int64); Y = TG["y4s"]; M = TG["members"]
TX = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); EX = TX["E_ts"].astype(np.int64); rx = {int(t): i for i, t in enumerate(EX)}
def on_v4_axis(first, last, P, axis_E):   # map a fold pred block (rows first..last of its own axis) onto the v4 axis by E_ts
    out = np.full((len(E), 829), np.nan, np.float32); r = {int(t): i for i, t in enumerate(E)}
    for k in range(last - first + 1):
        i = r.get(int(axis_E[first + k]))
        if i is not None and k < len(P): out[i] = P[k]
    return out
preds = {}
f, l, P = load_fold("/workspace/diag_legs/mwf_D2/preds_fold/mE1cX7_202507.npz"); preds["D2 v4data+extlegs"] = on_v4_axis(f, l, P, E)
f, l, P = load_fold("/workspace/diag_legs/mwf_D3/preds_fold/mE1cX7_202507.npz"); preds["D3 extdata retrain"] = on_v4_axis(f, l, P, EX)
f, l, P = load_fold("/workspace/f8_v4/mwf/CLIP_s42/shard2/preds_fold/mE1cX7_202507.npz"); preds["v4 CLIP (v4 legs)"] = on_v4_axis(f, l, P, E)
f, l, P = load_fold("/workspace/review_scratch/allweather_trackB/earlystop/FIX7/shard2/preds_fold/mE1cX7_202507.npz"); preds["FIX7 09-06 (ext)"] = on_v4_axis(f, l, P, EX)
preds["HF2 (09-06 model on holefix fea)"] = np.load("/workspace/review_scratch/health_check/dev_hf2/f8_2026-08-22/preds/f10_gate_mE1cX7_R0_spl42_hf2.npy")
PX = np.load("/workspace/f8_ext/preds/f10_V2MAIN_s42.npy"); preds["in-service yearly"] = on_v4_axis(0, len(EX) - 1, PX, EX)
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in E]); idx = np.where(ym == 202507)[0]
names = list(preds); res = {n: {"k0": [], "km1": []} for n in names}; pair = {(a, b): [] for a in names for b in names if a < b}
for i in idx:
    m = M[i]; y = Y[i, m]; yp = Y[i - 1, m]; ok0 = np.isfinite(y)
    vals = {n: preds[n][i, m] for n in names}
    for n in names:
        v = vals[n]; ok = ok0 & np.isfinite(v)
        if ok.sum() >= 30: res[n]["k0"].append(spearmanr(v[ok], y[ok]).correlation); okp = ok & np.isfinite(yp); res[n]["km1"].append(spearmanr(v[okp], yp[okp]).correlation)
    for (a, b) in pair:
        ok = np.isfinite(vals[a]) & np.isfinite(vals[b])
        if ok.sum() >= 30: pair[(a, b)].append(spearmanr(vals[a][ok], vals[b][ok]).correlation)
print(f"202507 test anchors n={len(idx)}"); out = {}
for n in names: out[n] = {"k0": float(np.nanmean(res[n]["k0"])), "km1": float(np.nanmean(res[n]["km1"])), "n": len(res[n]["k0"])}; print(f"  {n:34s} k0 IC {out[n]['k0']:+.4f}  k-1 {out[n]['km1']:+.4f}  (n={out[n]['n']})")
print("pairwise pred rank-corr (mean over anchors):")
for (a, b), v in pair.items():
    if v: print(f"  {a:34s} vs {b:34s} {np.mean(v):+.3f}")
for p_, cfg in (("D2", "/workspace/diag_legs/mwf_D2/models/mE1cX7_202507_config.json"), ("D3", "/workspace/diag_legs/mwf_D3/models/mE1cX7_202507_config.json"), ("v4CLIP", "/workspace/f8_v4/mwf/CLIP_s42/shard2/models/mE1cX7_202507_config.json"), ("FIX7 09-06", "/workspace/review_scratch/allweather_trackB/earlystop/FIX7/shard2/models/mE1cX7_202507_config.json")):
    try: c = json.load(open(cfg)); print(f"  {p_:10s} best_ep {c['best_epoch']} va@7 {c['va_curve'][7]:+.3f} alpha {c['alpha_final']:.4f} net {c['net_mean_bps']:+.3f} turnover {c['turnover_mean']:.4f} self_sha {c['self_sha256'][:10]} legs_sha {c.get('legs_sha256','?')[:10]} torch {c.get('torch','?')}")
    except Exception as e: print(p_, "cfg err", e)
json.dump({"ic": out, "pair": {f"{a}|{b}": float(np.mean(v)) for (a, b), v in pair.items() if v}}, open("/workspace/review_scratch/v4_gates/diag_202507.json", "w"), indent=1); print("DIAG_COMPARE_DONE")
