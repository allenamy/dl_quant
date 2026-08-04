"""Export each PRODUCTION_FOLD's own normalisation, and price the defect of not using it.

> created 2026-08-04 10:xx UTC | Session: B4-retrain | status: final | ledger #15 (first half)

★ THE DEFECT THIS ADDRESSES. `engine/live/signal_loop.py::build_live_preds` derives the serving
  normalisation itself:
        folds = th.year_folds(data, embargo_days=emb, val_days=30)
        data.set_fold(folds[4]["tr"])            <- fold 4's TRAIN window
        model = _model(f"{Ddir}/fold_4_model.pt")
  A production fold trains on `u[:-val_days]` — everything to the panel end — and saves
  `fold_0_model.pt`. So serving a production fold through that path would (i) not find the
  checkpoint, and (ii) if someone "fixed" (i) by renaming, silently normalise it with a window
  ~190 days shorter than the one it was trained on. **(i) fails loudly; renaming past it arms (ii)
  silently** — the obvious fix arms the deep defect.

★ WHAT THIS SCRIPT DOES, AND DELIBERATELY DOES NOT DO.
  DOES: recompute each production fold's OWN mu/sd from its OWN train window, write them into that
        run's directory in the `norm_stats.npz` key layout live already uses (king_mu/king_sd/
        s2_mu/s2_sd, (32,) float32), and MEASURE how far they sit from what live would have derived.
  DOES NOT: touch `~/dl_quant_live`. `checkpoints/norm_stats.npz` there is a PINNED frozen input
        (`live/frozen_inputs.py`) and that tree is 落盘即上线 — swapping it is a deployment action
        and belongs to the deployment batch, by hand, not to a research probe.

★ THE COMPARISON IS THE POINT, NOT THE EXPORT. An export nobody can size is just another file. The
  measured z-shift below says how much a wrongly-normalised production fold would actually be off:
  a channel whose mu moves by d and whose sd is s shifts that channel's z by d/s, and the model
  clips at +-10, so |dz| is directly readable as "how many sigma the input moved".
"""
import sys

import numpy as np

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
from multi_asset.data.wide_panel_dataset import WidePanelData          # noqa: E402
import multi_asset.train.train_wide_harness as TH                      # noqa: E402

PANEL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
RUNS = {
    # tag                                         horizon, embargo, val_days used by the prod fold
    "wideA_lamorth0_xattn_5yr_PRODFOLD_corrfund_v1": (4, 8, 30, "king"),
    "wideA_lamorth0_5yr_PRODFOLD_corrfund_v1": (4, 8, 30, "king"),
    "wideA_s2_y24_PRODFOLD_corrfund_v1": (24, 10, 90, "s2"),          # val=90 variant, NOT the candidate
    "wideA_s2_y24_PRODFOLD_corrfund_v1_val30": (24, 10, 30, "s2"),    # the deployment candidate
}

for tag, (H, EMB, VAL, leg) in RUNS.items():
    AUX = tuple(x for x in (1, 24) if x != H)
    d = WidePanelData(path=PANEL, target_horizon=H, aux_horizons=AUX)
    u = d.uniq_days

    # (a) the production fold's OWN window — u[:-val_days], exactly train_production_fold.py
    d.set_fold(u[:-VAL])
    mu_p, sd_p, rs_p = d.mu.copy(), d.sd.copy(), float(d.resid_sigma)
    tr_p = (int(u[0]), int(u[-VAL - 1]))

    # (b) what live WOULD derive for it — year_folds fold 4's train window
    folds = TH.year_folds(d, embargo_days=EMB, val_days=30, year_from=None)
    d.set_fold(folds[4]["tr"])
    mu_l, sd_l = d.mu.copy(), d.sd.copy()
    tr_l = (int(np.asarray(folds[4]["tr"]).min()), int(np.asarray(folds[4]["tr"]).max()))

    dz = np.abs(mu_p - mu_l) / np.maximum(sd_p, 1e-12)          # per-channel z shift
    sr = sd_l / np.maximum(sd_p, 1e-12)
    print("\n=== %s ===" % tag)
    print("  prod-fold train days %d..%d (%d) | live would use %d..%d (%d)  -> %d days shorter"
          % (tr_p[0], tr_p[1], tr_p[1] - tr_p[0] + 1, tr_l[0], tr_l[1], tr_l[1] - tr_l[0] + 1,
             (tr_p[1] - tr_p[0]) - (tr_l[1] - tr_l[0])))
    print("  ★ |z shift| across 32 channels: max=%.4f  mean=%.4f  p95=%.4f   (model clips at +-10)"
          % (dz.max(), dz.mean(), np.percentile(dz, 95)))
    print("  ★ sd ratio (live/prod):        min=%.4f  max=%.4f" % (sr.min(), sr.max()))
    print("  worst channel: idx %d  |dz|=%.4f" % (int(dz.argmax()), dz.max()))

    out = MA + "/exports/train/%s/NORM_PRODFOLD.npz" % tag
    np.savez(out, **{"%s_mu" % leg: mu_p.astype(np.float32),
                     "%s_sd" % leg: sd_p.astype(np.float32)},
             resid_sigma=np.float32(rs_p), train_day_first=tr_p[0], train_day_last=tr_p[1],
             val_days=VAL, target_horizon=H, embargo_days=EMB, panel=PANEL)
    print("  wrote %s  (keys %s_mu/%s_sd, live's norm_stats layout)" % (out, leg, leg))

print("\n★ These are SOURCE artifacts for the deployment batch, not a deployment. Building the live")
print("  checkpoints/norm_stats.npz from them is a pinned-frozen-input swap and is done by hand.")
