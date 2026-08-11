"""Settle the s2 embargo from the ARTIFACTS, for both s2 runs, using the certified inference.

The fidelity gate here is discriminating BECAUSE embargo moves fold["tr"] -> set_fold -> mu/sd.
If a run reproduces bitwise at one embargo and not the other, that identifies it.
"""
import sys
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
import torch
from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.model.wide_harness import WideFactorModel
import multi_asset.train.train_wide_harness as TH

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
RUNS = [
    ("DIRTY s2 (deployed)", MA + "/exports/train/wideA_s2_y24_5yr",
     MA + "/exports/wide_dl_full.npz", 24),
    ("CLEAN s2 (my retrain)", MA + "/exports/train/wideA_s2_y24_5yr_corrfund_v1",
     MA + "/exports/wide_dl_full_corrfund_causal_v1.npz", 24),
    ("KING (deployed)", MA + "/exports/train/wideA_lamorth0_xattn_5yr",
     MA + "/exports/wide_dl_full.npz", 4),
]
for name, RUN, PANEL, H in RUNS:
    AUX = tuple(x for x in (1, 24) if x != H)
    print("\n=== %s ===" % name, flush=True)
    for emb in (8, 10):
        d = WidePanelData(path=PANEL, target_horizon=H, aux_horizons=AUX)
        folds = TH.year_folds(d, embargo_days=emb, val_days=30, year_from=None)
        d.set_fold(folds[0]["tr"])
        tr = np.asarray(folds[0]["tr"])
        enc = TH.build_encoder("conformer", 32, TH.D_MODEL, TH.N_BLOCKS, TH.KERNEL, TH.DROPOUT)
        m = WideFactorModel(enc, n_factor_heads=6, xattn=True, n_xattn=1,
                            dropout=TH.DROPOUT, aux_horizons=()).to(TH.DEV)
        m.load_state_dict(torch.load(RUN + "/fold_0_model.pt", map_location=TH.DEV))
        m.eval()
        saved = np.load(RUN + "/fold_0_head_scores.npz")
        got = TH.predict_scores_wide(m, d, saved["te_days"], 32, 6)
        rows = saved["te_rows"][:400]
        w, g = saved["scores"][rows], got[rows]
        b = np.isfinite(g) & np.isfinite(w)
        dmax = float(np.abs(g[b] - w[b]).max()) if b.any() else float("nan")
        print("  embargo=%2d | tr %d..%d (n=%d) | max|d|=%.3e -> %s"
              % (emb, tr.min(), tr.max(), len(tr), dmax,
                 "*** THIS IS THE RECIPE ***" if dmax < 1e-6 else "no"), flush=True)
        del m
