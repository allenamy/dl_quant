"""0C — GPU-queue pre-check: per-fold cross-sectional rank corr of each arm's predictions vs the new
xattn king (lam_orth=0 + xattn). Same validated method as the xattn<->QIM precheck (0.42 → predicted
+0.028). All arms 3-fold same panel 39f5cc4e. CPU-only. Writes exports/eda/queue_precheck.json.

Pre-reg read (aux-MTL focus): corr <=~0.6 -> aux supervision may add independent increment on
clean+xattn -> queue 'aux+xattn combo' (high EV). corr >0.8 -> covered by xattn book -> low EV.
"""
import numpy as np, json, glob
from scipy.stats import rankdata

TR = "multi_asset/exports/train/"
EDA = "multi_asset/exports/eda/"
KING = "wideA_lamorth0_xattn"
ARMS = {"aux_MTL": "wideA_auxmtl", "pred_smooth": "wideA_psmooth03",
        "conformer_ref": "wideA_conformer_ref", "lamorth0": "wideA_lamorth0", "QIM": "wideA_qim"}


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


def folds(tag):
    return sorted(glob.glob(TR + tag + "/fold_*_head_scores.npz"),
                  key=lambda x: int(x.split("fold_")[1].split("_")[0]))


if __name__ == "__main__":
    pr = np.load(TR + KING + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64)
    king_C = [comp_panel(np.load(f)["scores"], member, CL, YR) for f in folds(KING)]

    out = {}
    for name, tag in ARMS.items():
        arm_f = folds(tag)
        percorr = []
        for fi, f in enumerate(arm_f):
            Ca = comp_panel(np.load(f)["scores"], member, CL, YR)
            Ck = king_C[fi]
            cors = []
            for t in np.where(np.isfinite(Ca).any(1) & np.isfinite(Ck).any(1))[0]:
                b = np.where(member[t] & CL[t] & np.isfinite(Ca[t]) & np.isfinite(Ck[t]))[0]
                if b.size >= 5:
                    c = np.corrcoef(rankdata(Ca[t, b]), rankdata(Ck[t, b]))[0, 1]
                    if np.isfinite(c):
                        cors.append(c)
            percorr.append(round(float(np.mean(cors)), 3))
        out[name] = dict(per_fold_corr=percorr, mean_corr=round(float(np.mean(percorr)), 3))
        print(f"{name:14s} vs xattn-king: per-fold {percorr} mean {out[name]['mean_corr']}", flush=True)

    aux = out["aux_MTL"]["mean_corr"]
    aux_read = ("QUEUE aux+xattn combo (HIGH EV): corr<=~0.6 -> aux supervision likely independent of xattn"
                if aux <= 0.62 else
                ("BORDERLINE (0.6-0.8): modest EV, queue below cheaper arms" if aux <= 0.8 else
                 "LOW EV: aux content covered by xattn -> yield queue to ARM-MIX/FinPFN"))
    result = dict(title="GPU-queue precheck: family pred-corr vs xattn king", created="2026-07-12",
                  auditor="0C", panel_md5="39f5cc4e (all arms, byte-identical)", ref_arm=KING,
                  method="per-ts xsec rank corr of composite preds, per fold, averaged (same as xattn<->QIM precheck)",
                  arms=out, aux_mtl_mean_corr=aux, aux_mtl_reading=aux_read)
    json.dump(result, open(EDA + "queue_precheck.json", "w"), indent=2, default=str)
    print(f"\n★ aux-MTL mean corr {aux} -> {aux_read}", flush=True)
    print("SAVED " + EDA + "queue_precheck.json", flush=True)
