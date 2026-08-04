"""CERTIFY the mu/sd re-export — and say plainly what CAN and CANNOT be certified for a prod fold.

> created 2026-08-04 08:xx UTC | Session: B4-retrain | ledger #15, certification step

★ WHY THIS EXISTS: "不认证的重导出就是又一份手抄" (team-lead). Calling `set_fold` again produces
  numbers that look right and have no witness — the exact shape that cost four scripts tonight.

★★★ AND THE FIRST THING IT FOUND IS THAT THE OBVIOUS CERTIFICATION IS IMPOSSIBLE HERE.
   The witness would be the run's own frozen `fold_0_head_scores.npz`. Measured:

       wideA_lamorth0_xattn_5yr_PRODFOLD_corrfund_v1   te_rows=(0,)  finite scores = 0
       wideA_s2_y24_PRODFOLD_corrfund_v1_val30         te_rows=(0,)  finite scores = 0
       wideA_lamorth0_xattn_5yr_corrfund_v1  (5-fold)  te_rows=(2190,) finite = 1,066,068

   **A production fold has `te = []` BY CONSTRUCTION, so it scores nothing and its head_scores file
   is a 161 MB array of all-NaN.** There is no artifact against which its normalisation can be
   witnessed — not "we did not check", but "there is nothing to check against".

   ⇒ So the certification available is **PROCEDURAL, not artifact-level**: certify the export code
     path on a run that DOES have a witness (the 5-fold), then use the identical path for the
     production folds. The claim this supports is **"the procedure is faithful"** — it is NOT
     "this particular export was witnessed". Those are different claims and only the first is
     available; saying the second would be the thing this file exists to prevent.

★★ NON-VACUITY. Initialising the dataset with the very `set_fold` call the export came from and then
   overriding mu/sd with the exported values compares a thing to itself. So the dataset is
   initialised from a DIFFERENT fold's window — leaving mu/sd wrong — and the exported values must
   do all the work. If the frozen scores come back, the export produced them.

★ OPPOSITE-SIDE RULERS (§8-b): `sd x1.5`, and the wrong init window left in place. Both must land
  far from the exported arm, else the comparison is insensitive to the norm and certifies nothing.

★ DEVICE: CPU (the GPU is on the #5/#14 chain). Correct rebuilds read ~3.5e-4 on CPU vs 1.2e-7 on
  GPU from float32 backend arithmetic alone, while wrong-weights controls stay at 6.5e-1 on both —
  so the DISCRIMINATION is device-independent and only the THRESHOLD is. Threshold used: 1e-3.
"""
import sys

import numpy as np
import torch

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
from multi_asset.data.wide_panel_dataset import WidePanelData          # noqa: E402
from multi_asset.model.wide_harness import WideFactorModel             # noqa: E402
import multi_asset.train.train_wide_harness as TH                      # noqa: E402

torch.backends.mkldnn.enabled = False    # oneDNN raises 'could not create a primitive' on this box
TH.DEV = "cpu"
CPU_FLOOR = 1e-3
PANEL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
# The witness-bearing run: 5-fold, fold 4 has 2190 scored test rows.
WITNESS = ("wideA_lamorth0_xattn_5yr_corrfund_v1", 4, 8, 4)     # tag, H, embargo, fold index

tag, H, EMB, FI = WITNESS
p = MA + "/exports/train/%s" % tag
AUX = tuple(x for x in (1, 24) if x != H)
d = WidePanelData(path=PANEL, target_horizon=H, aux_horizons=AUX)
folds = TH.year_folds(d, embargo_days=EMB, val_days=30, year_from=None)

# --- step 1: EXPORT via the same code path the production-fold export uses
d.set_fold(folds[FI]["tr"])
mu_x, sd_x = d.mu.copy().astype(np.float64), d.sd.copy().astype(np.float64)

# --- step 2: poison the state with a DIFFERENT fold's window, so the export must do the work
d.set_fold(folds[0]["tr"])
mu_wrong, sd_wrong = d.mu.copy().astype(np.float64), d.sd.copy().astype(np.float64)

saved = np.load(p + "/fold_%d_head_scores.npz" % FI)
enc = TH.build_encoder("conformer", 32, TH.D_MODEL, TH.N_BLOCKS, TH.KERNEL, TH.DROPOUT)
m = WideFactorModel(enc, n_factor_heads=6, xattn=True, n_xattn=1,
                    dropout=TH.DROPOUT, aux_horizons=()).to("cpu")
m.load_state_dict(torch.load(p + "/fold_%d_model.pt" % FI, map_location="cpu"))
m.eval()

print("=== PROCEDURAL certification on %s fold %d (witness: %d scored rows) ==="
      % (tag, FI, len(saved["te_rows"])))
res = {}
for arm, (mu, sd) in (("exported norm", (mu_x, sd_x)),
                      ("RULER wrong-window", (mu_wrong, sd_wrong)),
                      ("RULER sd x1.5", (mu_x, sd_x * 1.5))):
    d.mu, d.sd = mu.astype(np.float32), sd.astype(np.float32)
    got = TH.predict_scores_wide(m, d, saved["te_days"], 32, 6)
    rows = saved["te_rows"][:400]
    w, g = saved["scores"][rows], got[rows]
    b = np.isfinite(g) & np.isfinite(w)
    res[arm] = float(np.abs(g[b] - w[b]).max()) if b.any() else np.inf
    print("  %-20s max|d| vs frozen = %.3e   (n=%d cells)" % (arm, res[arm], int(b.sum())))

ok = res["exported norm"] < CPU_FLOOR
r1 = res["RULER wrong-window"] / max(res["exported norm"], 1e-12)
r2 = res["RULER sd x1.5"] / max(res["exported norm"], 1e-12)
print("\n  ⇒ export procedure: %s   (CPU floor %.0e)"
      % ("CERTIFIED" if ok else "*** NOT CERTIFIED ***", CPU_FLOOR))
print("  ⇒ rulers: wrong-window %.0fx   sd-x1.5 %.0fx   -> %s"
      % (r1, r2, "sighted" if min(r1, r2) > 100 else "*** INSENSITIVE — certifies nothing ***"))
print("\n★ SCOPE: this certifies the PROCEDURE (set_fold on the run's own train window -> mu/sd).")
print("  The production folds' own exports inherit it because they use the identical call. They")
print("  CANNOT be witnessed individually: te=[] by construction, so they score nothing.")
