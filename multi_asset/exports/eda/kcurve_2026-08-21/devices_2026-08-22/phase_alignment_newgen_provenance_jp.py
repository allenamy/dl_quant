"""PH 附属 · newgen 预测的来源核验 @jpline(2026-08-22, Session 6737834a-PH)。
事实: probe_artifacts/king_pred_newgen.npz ≠ comp_panel(run 目录冻结 fold_k_head_scores)(相关 0.978, max|Δ| 3.96), 而本装置在因果训练面板
(wide_dl_full_corrfund_causal_v1)上的推理与冻结 head_scores 逐位相同 ⇒ newgen 来自对另一张面板的推理。本脚本对 king fold 0(te=2022)在三张候选面板上
各推理一次(同一 fold 模型; 归一统计按同一 fold 的训练日在该面板上重算), 合成后与 newgen 在 2022 年 CL4 行比 corr / max|Δ|, 找出 ≈1.0 的那张。
候选: wide_dl_full_serve_v1.npz(ch31 SERVE 截断 13 抽头) / wide_dl_full_fundfix.npz(ch31 centered 'same', 含前视) / wide_dl_full_corrfund_causal_v1.npz(对照, 已知 0.978)。
只读; 输出 probe_artifacts/phase_alignment_newgen_provenance_2026-08-22.json。
"""
import sys, json, time, glob, numpy as np, pandas as pd, torch
REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"; MA = REPO + "/multi_asset"; PD = "/mnt/storage/private/work_hsy/probe_artifacts"
sys.path.insert(0, REPO)
from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.model.wide_harness import WideFactorModel, ConformerPanelEncoder
DEV = "cuda"; RUN = MA + "/exports/train/wideA_lamorth0_xattn_5yr_corrfund_v1"
CANDS = ["wide_dl_full_serve_v1.npz", "wide_dl_full_fundfix.npz", "wide_dl_full_corrfund_causal_v1.npz"]
ng = np.load(f"{PD}/king_pred_newgen.npz")["king_pred"]
z0 = np.load(RUN + "/fold_0_head_scores.npz"); te_rows = z0["te_rows"]; te_days = z0["te_days"]
t0 = time.time(); out = {}


def predict(model, data, split_days, bh=32, K=6):
    model.eval(); o = np.full((data.T, data.N, K), np.nan, np.float32)
    with torch.no_grad():
        for b in data.iter_batches(split_days, batch_hours=bh, rng=None, shuffle=False):
            x = torch.from_numpy(b["Xseq"]).to(DEV); m = torch.from_numpy(b["mask"]).to(DEV)
            sc = model(x, m)["factor_scores"].detach().cpu().numpy(); mm = b["mask"] > 0.5
            o[b["rows"]] = np.where(mm[:, :, None], sc, np.nan)
    return o


def comp(scores, mem, CL, YR):
    T, N, K = scores.shape; C = np.full((T, N), np.nan)
    for t in np.where((mem & CL & np.isfinite(YR)).any(1))[0]:
        base = np.where(mem[t] & CL[t] & np.isfinite(YR[t]))[0]
        if base.size < 5: continue
        c = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores[t, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12: c += (col - col.mean()) / col.std(); nk += 1
        if nk: C[t, base] = c / nk
    return C


model = WideFactorModel(ConformerPanelEncoder(32, d=64, n_blocks=2, kernel_size=15, dropout=0.2), n_factor_heads=6, xattn=True, n_xattn=1, dropout=0.2).to(DEV)
model.load_state_dict(torch.load(RUN + "/fold_0_model.pt", map_location=DEV), strict=True)
for nm in CANDS:
    data = WidePanelData(path=MA + "/exports/" + nm, target_horizon=4, aux_horizons=(1, 24))
    yr = pd.to_datetime(data.ts, unit="ms", utc=True).year.to_numpy()
    day_year = np.array([int(yr[data.day == d][0]) for d in data.uniq_days])
    res_nm = {}
    for norm_tag, emb in (("year_folds_emb8", 8), ("all_prior_days", None)):
        tr_all = data.uniq_days[day_year < 2022]
        tr = tr_all if emb is None else tr_all[:-emb][:-30]
        data.set_fold(tr)
        sc = predict(model, data, te_days)
        C = comp(sc, data.member, data.CL, data.Y)
        both = np.isfinite(C) & np.isfinite(ng)
        res_nm[norm_tag] = {"cells": int(both.sum()), "corr": float(np.corrcoef(C[both], ng[both])[0, 1]), "maxabs": float(np.abs(C[both] - ng[both]).max())}
        print(nm, norm_tag, res_nm[norm_tag], round(time.time() - t0, 1), "s", flush=True)
    out[nm] = res_nm
    del data
json.dump(out, open(f"{PD}/phase_alignment_newgen_provenance_2026-08-22.json", "w"), indent=1)
print(json.dumps(out, indent=1))
