"""A2b — CORRECT multi-asset gate: cross-sectional rank-IC + robust per-asset Spearman
+ beta-projection floor. (A2's per-asset Pearson was the wrong metric: fat tails
kurt 22-124 corrupt Pearson, and the multi-asset thesis is CROSS-SECTIONAL ranking,
not per-asset magnitude.)

Pipeline (leakage-safe, reuse A2 fold layout):
  - per asset, walk-forward Ridge (per-fold standardize X on train; y/MAD-sigma train);
    predict CLEAN test. Collect (ts, yhat, y) per asset.
  - Assemble panel by timestamp (intersection across assets present).
  - Metrics:
      (1) cross-sectional rank-IC: per ts, spearman(yhat, y) across assets; mean + IR (mean/std*sqrt(n_ts)).
      (2) per-asset pooled Spearman (robust headline) + Pearson (for contrast).
      (3) beta-projection FLOOR: common factor = BTC Ridge yhat; causal beta_i from
          rolling past (alt y on BTC y); yhat_alt = beta_i * yhat_btc; its xsec rank-IC.
  GO/NO-GO read on xsec rank-IC + per-asset Spearman, NOT Pearson.
"""
from __future__ import annotations
import json, os.path as p, sys
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import RidgeCV

CACHE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/panel_cache"
EXPORT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda"
SYMBOLS = ["bnfbtc","bnfeth","bnfsol","bnfbnb","bnfxrp","bnfdog","bnfada",
           "bnflink","bnfbch","bnftrx","bnfltc","bnfdot","bnffil","bnfetc"]
ALPHAS = np.logspace(-2, 4, 13)
FOLDS = [dict(tr=(0,250), te=(272,312)), dict(tr=(80,330), te=(352,392)), dict(tr=(160,410), te=(432,472))]
EMBARGO = 1

def mad_sigma(x):
    x = x[np.isfinite(x)]
    if x.size == 0: return np.nan
    return float(np.median(np.abs(x - np.median(x))) * 1.4826)

def load(sym):
    d = np.load(p.join(CACHE, f"{sym}.npz"))
    return d["X"], d["y"], d["day"], d["ts"], d["clean600"]

def fold_days(uniq, fold):
    n = uniq.shape[0]
    if fold["te"][1] > n: return None
    te0, te1 = fold["te"]; tr0, tr1 = fold["tr"]
    tr_idx = np.arange(tr0, tr1); tr_idx = tr_idx[tr_idx < te0 - EMBARGO]
    return set(uniq[tr_idx].tolist()), set(uniq[te0:te1].tolist())

def predict_asset(sym):
    """Walk-forward Ridge; return dict ts->(yhat,y) over clean test (raw return units)."""
    X, y, day, ts, clean = load(sym)
    uniq = np.unique(day)
    out_ts, out_yhat, out_y = [], [], []
    for fold in FOLDS:
        r = fold_days(uniq, fold)
        if r is None: continue
        trd, ted = r
        trm = np.isin(day, list(trd))
        tem = np.isin(day, list(ted)) & clean
        if trm.sum() < 500 or tem.sum() < 20: continue
        Xtr, ytr = X[trm], y[trm]; Xte = X[tem]
        mu, sd = Xtr.mean(0), Xtr.std(0); sd = np.where(sd > 1e-12, sd, 1.0)
        sig = mad_sigma(ytr)
        if not np.isfinite(sig) or sig <= 0: continue
        m = RidgeCV(alphas=ALPHAS); m.fit((Xtr-mu)/sd, ytr/sig)
        yhat = m.predict((Xte-mu)/sd) * sig
        out_ts.append(ts[tem]); out_yhat.append(yhat); out_y.append(y[tem])
    if not out_ts: return {}
    T = np.concatenate(out_ts); H = np.concatenate(out_yhat); Y = np.concatenate(out_y)
    return {int(t): (h, yy) for t, h, yy in zip(T, H, Y)}

def main():
    preds = {s: predict_asset(s) for s in SYMBOLS}
    # per-asset pooled Spearman + Pearson
    per_asset = {}
    for s in SYMBOLS:
        if not preds[s]: per_asset[s] = None; continue
        H = np.array([v[0] for v in preds[s].values()]); Y = np.array([v[1] for v in preds[s].values()])
        per_asset[s] = dict(spearman=round(float(spearmanr(H,Y)[0]),4),
                            pearson=round(float(pearsonr(H,Y)[0]),4), n=len(H))
    # assemble panel by ts
    all_ts = sorted(set().union(*[set(preds[s].keys()) for s in SYMBOLS if preds[s]]))
    rows_ic, rows_ic_floor = [], []
    # beta-projection floor: common factor btc yhat; beta_i = rolling cov/var on aligned series
    btc = preds["bnfbtc"]
    # build aligned arrays per ts for xsec
    def xsec_rank_ic(pred_fn):
        ics = []
        for t in all_ts:
            yh, yy = [], []
            for s in SYMBOLS:
                if t in preds[s]:
                    v = pred_fn(s, t)
                    if v is None: continue
                    yh.append(v); yy.append(preds[s][t][1])
            if len(yh) >= 5:
                ic = spearmanr(yh, yy)[0]
                if np.isfinite(ic): ics.append(ic)
        ics = np.array(ics)
        return dict(mean_ic=round(float(ics.mean()),4),
                    ir=round(float(ics.mean()/ics.std()*np.sqrt(len(ics))),3) if ics.std()>0 else None,
                    n_ts=len(ics))
    # raw model xsec
    model_ic = xsec_rank_ic(lambda s,t: preds[s][t][0])
    # beta-projection floor: estimate static beta_i over the pooled aligned sample (causal-ish proxy:
    # beta from cov(alt_y, btc_y)/var(btc_y) on TRAIN-equivalent — here use all aligned as quick floor)
    betas = {}
    for s in SYMBOLS:
        if not preds[s] or s == "bnfbtc": continue
        common = [t for t in preds[s] if t in btc]
        if len(common) < 100: continue
        ay = np.array([preds[s][t][1] for t in common]); by = np.array([btc[t][1] for t in common])
        betas[s] = float(np.cov(ay,by)[0,1]/np.var(by)) if np.var(by)>0 else 0.0
    def floor_pred(s,t):
        if s == "bnfbtc": return btc[t][0] if t in btc else None
        if s not in betas or t not in btc: return None
        return betas[s]*btc[t][0]
    floor_ic = xsec_rank_ic(floor_pred)

    summary = dict(
        analysis="A2b_xsec_gate",
        note="CORRECT gate: xsec rank-IC + per-asset Spearman (Pearson corrupted by fat tails kurt 22-124)",
        per_asset=per_asset,
        per_asset_spearman_median=round(float(np.median([per_asset[s]["spearman"] for s in SYMBOLS if per_asset[s]])),4),
        per_asset_spearman_pos_count=int(sum(per_asset[s]["spearman"]>0 for s in SYMBOLS if per_asset[s])),
        model_xsec_rank_ic=model_ic,
        beta_projection_floor_xsec_rank_ic=floor_ic,
        betas={k:round(v,3) for k,v in betas.items()},
    )
    import os; os.makedirs(EXPORT, exist_ok=True)
    json.dump(summary, open(p.join(EXPORT,"a2b_xsec_gate.json"),"w"), indent=2)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
