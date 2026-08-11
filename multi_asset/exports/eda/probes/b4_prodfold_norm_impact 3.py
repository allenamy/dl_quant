"""Does the 0.08-sigma normalisation shift matter at the SCORE level? Measure, do not assume.

Third time tonight that an input/score-level magnitude must not be read as an output-level one
(norm window: max|d| 6e-2 -> 0.7% book; forward loop: max|d| 5.7e-1 -> 0.3% BE). So this converts
the shift into the quantity a book consumes: per-anchor cross-sectional agreement.
Scored on the production fold's OWN val window — an input-sensitivity test, NOT an OOS claim.
"""
import sys
import numpy as np, torch
from scipy.stats import rankdata, spearmanr
REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"; MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.model.wide_harness import WideFactorModel
import multi_asset.train.train_wide_harness as TH
PANEL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
for tag, H, EMB, VAL, XA in (("wideA_lamorth0_xattn_5yr_PRODFOLD_corrfund_v1", 4, 8, 30, True),
                             ("wideA_s2_y24_PRODFOLD_corrfund_v1", 24, 10, 90, True)):
    AUX = tuple(x for x in (1, 24) if x != H)
    d = WidePanelData(path=PANEL, target_horizon=H, aux_horizons=AUX)
    u = d.uniq_days; va = u[-VAL:]
    enc = TH.build_encoder("conformer", 32, TH.D_MODEL, TH.N_BLOCKS, TH.KERNEL, TH.DROPOUT)
    m = WideFactorModel(enc, n_factor_heads=6, xattn=XA, n_xattn=1,
                        dropout=TH.DROPOUT, aux_horizons=()).to(TH.DEV)
    m.load_state_dict(torch.load(MA + "/exports/train/%s/fold_0_model.pt" % tag, map_location=TH.DEV))
    m.eval()
    out = {}
    for nm, tr in (("prodfold-own", u[:-VAL]),
                   ("live-derived", TH.year_folds(d, embargo_days=EMB, val_days=30,
                                                  year_from=None)[4]["tr"])):
        d.set_fold(tr)
        out[nm] = TH.predict_scores_wide(m, d, va, 32, 6)
    a, b = out["prodfold-own"], out["live-derived"]
    ok = np.isfinite(a) & np.isfinite(b)
    rows = np.where(np.isin(d.day, va) & d.valid_hour)[0]
    pa = []
    for t in rows:
        va_ = np.isfinite(a[t, :, 0]) & np.isfinite(b[t, :, 0])
        if va_.sum() >= 5:
            ca = a[t, va_].mean(1); cb = b[t, va_].mean(1)
            pa.append(spearmanr(ca, cb).statistic)
    pa = np.array(pa, float)
    print("\n=== %s ===" % tag)
    print("  score max|d|=%.4e  mean|d|=%.4e" % (np.abs(a[ok] - b[ok]).max(), np.abs(a[ok] - b[ok]).mean()))
    print("  ★ per-anchor xsec spearman(own-norm, live-norm): mean=%.6f p05=%.6f min=%.6f n=%d"
          % (np.nanmean(pa), np.nanpercentile(pa, 5), np.nanmin(pa), len(pa)))
    del m
