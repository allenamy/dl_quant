"""PRODUCTION-FOLD inference — the serving path a production fold does not otherwise have. (#31)

> created 2026-08-04 12:3x UTC | Session: B4-retrain

★ WHY A SEPARATE SCRIPT. `vs_infer5.py` drives scoring off each fold's `te_days`. A production fold
  has `te = []` BY CONSTRUCTION, so that path scores **nothing** for it (measured: `te_rows=(0,)`,
  zero finite scores, a 161 MB all-NaN file). A production fold must instead be scored over the
  WHOLE anchor grid with its own single checkpoint.

★★ THE NORMALISATION COMES FROM THE CERTIFIED EXPORT, NOT RE-DERIVED HERE.
  `NORM_PRODFOLD.npz` was written from the run's own train window and the EXPORT PROCEDURE is
  certified (against a witness-bearing 5-fold run: max|d| 0 with rulers 1329x / 343x apart).
  Re-deriving it here would be a second implementation with nothing comparing them — tonight's most
  expensive defect shape. This script LOADS it and asserts it matches the provenance's train window.

★★★ AND THE THING THIS MUST NOT DO: bridge by renaming `fold_0_model.pt` to `fold_4_model.pt`.
  Live's `build_live_preds` looks for `fold_4_model.pt` AND derives its norm from `year_folds[4]`.
  Renaming past the loud failure would silently install a normalisation from a window ~190 days
  shorter than the model trained on. Loud failure is the protection; renaming disarms it.
  (That silent half was separately priced at ~0.05% cross-sectional disagreement — small, but the
  point is that the mechanism is wrong, and small today is not small after the next retrain.)

★ ARM: SERVE — what production actually receives (trailing-13 via the live panel's edge truncation).
"""
import argparse
import json
import sys

import numpy as np
import torch

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
from multi_asset.data.wide_panel_dataset import WidePanelData          # noqa: E402
from multi_asset.model.wide_harness import WideFactorModel             # noqa: E402
import multi_asset.train.train_wide_harness as TH                      # noqa: E402

REG = {
    "pf_king": dict(dir=MA + "/exports/train/wideA_lamorth0_xattn_5yr_PRODFOLD_corrfund_v1",
                    H=4, leg="king", densify=False, xattn=True),
    "pf_s2": dict(dir=MA + "/exports/train/wideA_s2_y24_PRODFOLD_corrfund_v1_val30",
                  H=24, leg="s2", densify=True, xattn=True),
}
PANEL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
K = 6

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True, choices=sorted(REG))
ap.add_argument("--arm", default="SERVE", choices=["TRAIN", "SERVE", "CAUSAL"])
ap.add_argument("--eval-batch-hours", type=int, default=32, dest="ebh")
a = ap.parse_args()
cfg = REG[a.run]

prov = json.load(open(cfg["dir"] + "/PRODUCTION_FOLD_PROVENANCE.json"))
norm = np.load(cfg["dir"] + "/NORM_PRODFOLD.npz", allow_pickle=True)
assert int(norm["train_day_first"]) == int(prov["train_days"][0]) and \
       int(norm["train_day_last"]) == int(prov["train_days"][1]), \
    "NORM_PRODFOLD train window != PROVENANCE train window — the export is not this run's"
mu = norm["%s_mu" % cfg["leg"]].astype(np.float32)
sd = norm["%s_sd" % cfg["leg"]].astype(np.float32)
print("[%s] norm loaded from certified export; train days %d..%d (matches provenance)"
      % (a.run, int(norm["train_day_first"]), int(norm["train_day_last"])), flush=True)

AUX = tuple(x for x in (1, 24) if x != cfg["H"])
d = WidePanelData(path=PANEL, target_horizon=cfg["H"], aux_horizons=AUX)
z = np.load(PANEL, allow_pickle=True)
CL4, member, ts = z["CL4"], z["MEMBER110"], z["ts"].astype(np.int64)
T, N = member.shape
i_b = [str(c) for c in z["ch_names"]].index("betaadj_ret24")
arms = np.load("/tmp/vs_ch31_arms.npz")
assert np.array_equal(arms["CAUSAL"], d.CH[:, :, i_b]), "panel ch31 != CAUSAL arm"
d.CH = d.CH.copy()
d.CH[:, :, i_b] = arms[a.arm]

# the whole anchor grid, and the dense mask for s2 (the mask production actually uses)
ok = np.arange(T) >= (d.W - 1)
d.valid_hour = np.zeros(T, bool)
d.valid_hour[ok] = CL4[ok].any(1)
if cfg["densify"]:
    d.CL = member.copy()
# ★ mu/sd/resid_sigma ALL come from the certified export. `resid_sigma` is not optional decoration:
#   `iter_batches` divides the label by it, so leaving it unset raises — which is the friendly
#   failure. The dangerous version would have been a default that silently rescales.
d.mu, d.sd = mu, sd
d.resid_sigma = np.float32(norm["resid_sigma"])

enc = TH.build_encoder("conformer", 32, TH.D_MODEL, TH.N_BLOCKS, TH.KERNEL, TH.DROPOUT)
m = WideFactorModel(enc, n_factor_heads=K, xattn=cfg["xattn"], n_xattn=1,
                    dropout=TH.DROPOUT, aux_horizons=()).to(TH.DEV)
m.load_state_dict(torch.load(cfg["dir"] + "/fold_0_model.pt", map_location=TH.DEV))
m.eval()

all_days = d.uniq_days
sc = TH.predict_scores_wide(m, d, all_days, a.ebh, K)

base_mask = member & CL4 & np.isfinite(z["YR4"])
OUT = np.full((T, N), np.nan, np.float32)
rows = np.where(d.valid_hour)[0]
for t in rows:
    base = np.where(base_mask[t])[0]
    if base.size < 5:
        continue
    acc = np.zeros(base.size); nk = 0
    for j in range(K):
        col = sc[t, base, j]
        if np.isfinite(col).all() and col.std() > 1e-12:
            acc += (col - col.mean()) / col.std(); nk += 1
    if nk:
        OUT[t, base] = (acc / nk).astype(np.float32)

out = "/tmp/vs_pf_%s_%s.npz" % (a.run, a.arm)
np.savez(out, pred=OUT, ts=ts)
print("[%s/%s] DONE rows=%d finite=%d -> %s"
      % (a.run, a.arm, int(np.isfinite(OUT).any(1).sum()), int(np.isfinite(OUT).sum()), out),
      flush=True)
