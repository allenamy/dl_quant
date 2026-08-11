#!/usr/bin/env python3
"""Densify the S2-pred OOS panel from CL24 -> CL4 by re-inferring the 5 saved fold checkpoints.

Strict fold attribution unchanged: each ts uses ONLY its own test-fold's model (causal OOS).
Re-runs each fold model at CL4-anchor hours over its test year (model forward is defined at any t;
inference mask = member so xattn attends all members, matching training's member-attention).
Composite via the king_pred recipe (per-ts z-mean of the 6 heads). -> s2_pred_panel_cl4.npz.
"""
import sys, glob, json, numpy as np, torch, pandas as pd
REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, REPO)
from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.model.wide_harness import WideFactorModel, ConformerPanelEncoder

MA = REPO + "/multi_asset"
NPZ = MA + "/exports/wide_dl_full.npz"        # 32ch (matches wideA_s2_y24_5yr input_proj 64x32)
XK = MA + "/exports/train/wideA_s2_y24_5yr"
OUT = MA + "/exports/eda/s2_pred_panel_cl4.npz"
DEV = "cuda"
C, D, NBLK, KER, DROP, K = 32, 64, 2, 15, 0.2, 6

W = np.load(NPZ, allow_pickle=True)
member = W["MEMBER110"]; CL4 = W["CL4"]; YR4 = W["YR4"]; Y4 = W["Y4"]
ts = W["ts"].astype(np.int64); day = np.arange(len(ts)) // 24
yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
T, N = member.shape


def comp_panel(scores, mem, CL, YR):
    Tt, Nn, Kk = scores.shape
    Cc = np.full((Tt, Nn), np.nan)
    for t in np.where((mem & CL & np.isfinite(YR)).any(1))[0]:
        base = np.where(mem[t] & CL[t] & np.isfinite(YR[t]))[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size); nk = 0
        for k in range(Kk):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        if nk:
            Cc[t, base] = comp / nk
    return Cc


def predict(model, data, te_days, bh=64):
    model.eval()
    out = np.full((T, N, K), np.nan, np.float32)
    with torch.no_grad():
        for b in data.iter_batches(te_days, batch_hours=bh, rng=None, shuffle=False):
            x = torch.from_numpy(b["Xseq"]).to(DEV)
            m = torch.from_numpy(b["mask"]).to(DEV)
            sc = model(x, m)["factor_scores"].detach().cpu().numpy()
            mm = b["mask"] > 0.5
            out[b["rows"]] = np.where(mm[:, :, None], sc, np.nan)
    return out


S2 = np.full((T, N), np.nan, np.float32)
overlap = 0; cov = {}
folds = sorted(glob.glob(XK + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0]))
for f in folds:
    i = int(f.split("fold_")[1].split("_")[0])
    z = np.load(f)
    te_rows = z["te_rows"]; te_days = z["te_days"]
    te_year = int(np.bincount(yr[te_rows] - yr[te_rows].min()).argmax() + yr[te_rows].min())
    # fresh dataset; override valid_hour -> CL4 anchors, CL -> member (member-based inference mask)
    data = WidePanelData(path=NPZ, target_horizon=24)
    ok = np.arange(T) >= (data.W - 1)
    data.valid_hour = np.zeros(T, bool); data.valid_hour[ok] = CL4[ok].any(1)
    data.CL = member.copy()
    day_year = np.array([int(yr[data.day == dd][0]) for dd in data.uniq_days])
    tr_days = data.uniq_days[day_year < te_year]
    data.set_fold(tr_days)
    model = WideFactorModel(ConformerPanelEncoder(C, d=D, n_blocks=NBLK, kernel_size=KER, dropout=DROP),
                            n_factor_heads=K, xattn=True, n_xattn=1, dropout=DROP).to(DEV)
    missing, unexpected = model.load_state_dict(torch.load(XK + "/fold_%d_model.pt" % i, map_location=DEV), strict=False)
    assert not missing and not unexpected, "state_dict mismatch fold %d: missing=%s unexpected=%s" % (i, missing, unexpected)
    sc = predict(model, data, te_days)
    Cc = comp_panel(sc, member, CL4, YR4)
    m = np.isfinite(Cc)
    overlap += int((m & np.isfinite(S2)).sum())
    S2[m] = Cc[m].astype(np.float32)
    cov[te_year] = int(m.any(1).sum())
    print("fold %d te=%d: CL4 anchor-rows filled=%d" % (i, te_year, int(m.any(1).sum())), flush=True)

np.savez(OUT, ts=ts, s2_pred=S2, member=member, CL=CL4, YR=W["YR4"].astype(np.float32),
         Yraw=Y4.astype(np.float32), day=day, year=yr)
rep = {"out": OUT, "s2_pred_finite_frac_CL4": round(float(np.isfinite(S2).mean()), 4),
       "cov_rows": int(np.isfinite(S2).any(1).sum()), "cross_fold_overlap": overlap,
       "cov_by_year": cov, "note": "densified CL24->CL4 via re-inference of 5 saved fold checkpoints (32ch)"}
json.dump(rep, open(MA + "/exports/eda/s2_pred_panel_cl4_report.json", "w"), indent=1)
print(json.dumps(rep, indent=1))
