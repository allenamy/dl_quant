"""Does the HARNESS's own inference function reproduce the frozen s2 scores? (mine does not)

If yes, the defect is in the hand-rolled forward loop that vs_infer{,2,3,4}.py all share, and the
fix is to stop reimplementing `predict_scores_wide` rather than to keep tuning a copy of it.
"""
import sys
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
import torch
from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.model.wide_harness import WideFactorModel
import multi_asset.train.train_wide_harness as TH

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
FULL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
for tag, RUN, H, AUX in (("s2c", MA + "/exports/train/wideA_s2_y24_5yr_corrfund_v1", 24, (1,)),
                         ("s1f", MA + "/exports/train/wideA_lamorth0_xattn_5yr_corrfund_v1", 4, (1, 24))):
    d = WidePanelData(path=FULL, target_horizon=H, aux_horizons=AUX)
    folds = TH.year_folds(d, embargo_days=8, val_days=30, year_from=None)
    print("\n=== %s ===" % tag, flush=True)
    for k in (0, 1):
        fold = folds[k]
        d.set_fold(fold["tr"])
        enc = TH.build_encoder("conformer", 32, TH.D_MODEL, TH.N_BLOCKS, TH.KERNEL, TH.DROPOUT)
        m = WideFactorModel(enc, n_factor_heads=6, xattn=True, n_xattn=1,
                            dropout=TH.DROPOUT, aux_horizons=()).to(TH.DEV)
        m.load_state_dict(torch.load(RUN + "/fold_%d_model.pt" % k, map_location=TH.DEV))
        m.eval()
        saved = np.load(RUN + "/fold_%d_head_scores.npz" % k)
        te_days = saved["te_days"]
        got = TH.predict_scores_wide(m, d, te_days, 32, 6)
        want = saved["scores"]
        rows = saved["te_rows"][:600]
        b = np.isfinite(got[rows]) & np.isfinite(want[rows])
        dmax = float(np.abs(got[rows][b] - want[rows][b]).max()) if b.any() else float("nan")
        print("  fold%d te=%s  max|d|=%.3e  nan-pattern-equal=%s  -> %s"
              % (k, fold["year"], dmax,
                 np.array_equal(np.isfinite(got[rows]), np.isfinite(want[rows])),
                 "REPRODUCES" if dmax < 1e-5 else "still differs"), flush=True)
        del m
