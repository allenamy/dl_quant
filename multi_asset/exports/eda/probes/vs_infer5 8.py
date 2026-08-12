"""B4 — produce prediction panels by CALLING the harness's inference, not by reimplementing it.

> created 2026-08-04 08:xx UTC | Session: B4-retrain | status: final
> supersedes the inference half of vs_infer{,2,3,4}.py for the corrfund runs

★★★ WHY THIS FILE EXISTS — a four-way duplication that nothing compared.
   `vs_infer.py`, `vs_infer2.py`, `vs_infer3.py` and my own `vs_infer4.py` each hand-roll the forward
   loop (batch -> normalise -> clip -> model -> mask -> composite). None of them ever compares its
   output against `train_wide_harness.predict_scores_wide`, which is what actually produced the
   frozen `fold_k_head_scores.npz`. Measured 2026-08-04 on GPU, against the frozen scores:

       hand-rolled loop, king (s1f)   max|d| = 1.2e-07    <- looked perfect
       hand-rolled loop, s2  (s2c)    max|d| = 3.5e-02    <- wrong, and nothing could see it
       harness predict_scores_wide    max|d| = 0.000e+00  <- both runs, bitwise

   The king agreeing to float32 epsilon is exactly why this survived: **the copy was validated by
   the leg where it happened to agree.** The s2 leg carries ~80% of the book at k=0.2, which is the
   configuration tonight's headline rests on.

   ⇒ A second implementation is only correct if something compares it to the first, every run
     ([[duplication-with-equality-assertion]]). Here nothing did, for four scripts.

★★ TWO PRODUCTS, SAID OUT LOUD.
   (a) GATE  — native `valid_hour`, native mask: reproduces training bitwise, and is checked against
       the frozen scores on every run. This certifies the FUNCTION.
   (b) PANEL — `valid_hour` widened to the CL4 anchor grid so the book has hourly coverage (the
       `densify_s2_cl4.py` recipe that `vs_infer.py` introduced). This is a DELIBERATE DEVIATION
       from training and is NOT bitwise-checkable against anything — no frozen artifact exists for
       those rows. The gate certifies the machinery that produces it; it does not certify the
       extrapolation to rows the model never scored during training.

★ ARM. Scored under SERVE by default: the models trained on causal ch31, but production hands them a
  trailing-13 window (live panel ends at the signal row; `convolve(..., "same")` zero-fills the 11
  future taps). Reading the book at its training arm reports a caliber live never sees.

READ-ONLY on panels and run dirs; writes only /tmp.
"""
import argparse
import os
import sys

import numpy as np
import torch

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)

from multi_asset.data.wide_panel_dataset import WidePanelData          # noqa: E402
from multi_asset.model.wide_harness import WideFactorModel             # noqa: E402
import multi_asset.train.train_wide_harness as TH                      # noqa: E402

# ★ EACH RUN CARRIES ITS OWN PANEL. The as-trained panel is a property of the RUN, not of this
#   script — `wideA_*_causal_v1` trained on as_trained funding, `wideA_*_corrfund_v1` on corrected.
#   Reading a run against the wrong generation turns nothing red (PANELS_MANIFEST section 2).
CORRFUND = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
CAUSALV1 = MA + "/exports/wide_dl_full_causal_v1.npz"
REG = {
    "s1f": dict(dir=MA + "/exports/train/wideA_lamorth0_xattn_5yr_corrfund_v1", H=4,
                densify=False, panel=CORRFUND),
    "s2c": dict(dir=MA + "/exports/train/wideA_s2_y24_5yr_corrfund_v1", H=24,
                densify=True, panel=CORRFUND),
    # emb=10 retrain of the clean s2 (ledger #14). Kept ALONGSIDE s2c (emb=8) rather than replacing
    # it: the pair is the embargo-sensitivity measurement (IC within 3%, but persistence −10.7%).
    "s2c10": dict(dir=MA + "/exports/train/wideA_s2_y24_5yr_corrfund_emb10", H=24,
                  densify=True, panel=CORRFUND),
    # C3's clean king — the model behind tonight's BE 4.692 / net +682. Re-derived here through the
    # CERTIFIED inference so the headline can be checked against its own uncertified version.
    "s1x": dict(dir=MA + "/exports/train/wideA_lamorth0_xattn_5yr_causal_v1", H=4,
                densify=False, panel=CAUSALV1),
}
K = 6

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True, choices=sorted(REG))
ap.add_argument("--arm", default="SERVE", choices=["TRAIN", "SERVE", "CAUSAL"])
ap.add_argument("--embargo", type=int, default=8)
ap.add_argument("--eval-batch-hours", type=int, default=32, dest="ebh")
ap.add_argument("--gate-cap", type=int, default=600)
ap.add_argument("--out", default=None)
a = ap.parse_args()
cfg = REG[a.run]
FULL = cfg["panel"]

AUX = tuple(x for x in (1, 24) if x != cfg["H"])
d = WidePanelData(path=FULL, target_horizon=cfg["H"], aux_horizons=AUX)
folds = TH.year_folds(d, embargo_days=a.embargo, val_days=30, year_from=None)
zf = np.load(FULL, allow_pickle=True)
CL4, member, ts = zf["CL4"], zf["MEMBER110"], zf["ts"].astype(np.int64)
T, N = member.shape
NATIVE_VH = d.valid_hour.copy()
i_b = [str(c) for c in zf["ch_names"]].index("betaadj_ret24")
assert i_b == 31, i_b

arms = np.load("/tmp/vs_ch31_arms.npz")
assert np.array_equal(arms["CAUSAL"], d.CH[:, :, i_b]), \
    "corrfund_causal_v1 ch31 != CAUSAL arm — the panel is not what its name claims"
NATIVE_CH = d.CH.copy()
print("[%s/%s] folds=%s embargo=%d aux=%s" % (a.run, a.arm, [f["year"] for f in folds],
                                              a.embargo, AUX), flush=True)


def model_for(k):
    enc = TH.build_encoder("conformer", 32, TH.D_MODEL, TH.N_BLOCKS, TH.KERNEL, TH.DROPOUT)
    m = WideFactorModel(enc, n_factor_heads=K, xattn=True, n_xattn=1,
                        dropout=TH.DROPOUT, aux_horizons=()).to(TH.DEV)
    m.load_state_dict(torch.load(cfg["dir"] + "/fold_%d_model.pt" % k, map_location=TH.DEV))
    m.eval()
    return m


# ---------------------------------------------------------------- (a) GATE
print("\n=== FIDELITY GATE — native grid, native ch31, vs the frozen scores ===", flush=True)
worst = 0.0
for k in range(len(folds)):
    d.CH, d.valid_hour = NATIVE_CH, NATIVE_VH
    d.set_fold(folds[k]["tr"])
    saved = np.load(cfg["dir"] + "/fold_%d_head_scores.npz" % k)
    m = model_for(k)
    got = TH.predict_scores_wide(m, d, saved["te_days"], a.ebh, K)
    del m
    rows = saved["te_rows"][:a.gate_cap]
    w = saved["scores"][rows]
    g = got[rows]
    b = np.isfinite(g) & np.isfinite(w)
    dmax = float(np.abs(g[b] - w[b]).max()) if b.any() else np.inf
    worst = max(worst, dmax)
    print("  fold%d te=%s n=%d  max|d|=%.3e  nan-pattern-equal=%s"
          % (k, folds[k]["year"], len(rows), dmax,
             np.array_equal(np.isfinite(g), np.isfinite(w))), flush=True)
if worst > 1e-5:
    print("*** GATE FAILED max|d|=%.3e — emitting nothing ***" % worst)
    sys.exit(1)
print("=== GATE PASSED max|d|=%.3e (bitwise for both runs when this was written) ===\n" % worst,
      flush=True)

# ---------------------------------------------------------------- (b) PANEL
CH_ARM = NATIVE_CH.copy()
CH_ARM[:, :, i_b] = arms[a.arm]
wide_vh = np.zeros(T, bool)
ok = np.arange(T) >= (d.W - 1)
wide_vh[ok] = CL4[ok].any(1)
base_mask = member & CL4 & np.isfinite(zf["YR4"])

OUT = np.full((T, N), np.nan, np.float32)
for k in range(len(folds)):
    d.CH, d.valid_hour = NATIVE_CH, NATIVE_VH
    d.set_fold(folds[k]["tr"])                   # norm from the AS-TRAINED panel + native grid
    saved = np.load(cfg["dir"] + "/fold_%d_head_scores.npz" % k)
    d.CH = CH_ARM                                # only ch31 moves
    if cfg["densify"]:
        # ★ THE DENSIFY IS `d.CL = member`, NOT a valid_hour widening. `predict_scores_wide` masks
        #   with `member & CL & isfinite(Y)` inside `iter_batches`; setting CL to member collapses
        #   that to `member & isfinite(Y)` — the dense branch, and the mask production actually uses
        #   (live drops the isfinite(Y) term too, which is the residual 0.6% priced separately).
        #   Widening `valid_hour` alone does NOT densify: the rows get visited and then masked out,
        #   which is why the first attempt produced 1636 anchors instead of 9821.
        #   `set_fold` does not read `d.CL` (verified: removing this mutation left scores bitwise
        #   unchanged), so the fold normalisation is unaffected by doing it here.
        d.CL = member.copy()
        d.valid_hour = wide_vh
    m = model_for(k)
    sc = TH.predict_scores_wide(m, d, saved["te_days"], a.ebh, K)
    del m
    rows = np.where(np.isin(d.day, saved["te_days"]) & d.valid_hour)[0]
    for t in rows:
        base = np.where(base_mask[t])[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size)
        nk = 0
        for j in range(K):
            col = sc[t, base, j]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std()
                nk += 1
        if nk:
            OUT[t, base] = (comp / nk).astype(np.float32)
    print("[%s/%s] fold%d te=%s rows=%d" % (a.run, a.arm, k, folds[k]["year"], len(rows)), flush=True)

out = a.out or "/tmp/vs5_pred_%s_%s.npz" % (a.run, a.arm)
np.savez(out, pred=OUT, ts=ts)
print("[%s/%s] DONE finite=%d -> %s" % (a.run, a.arm, int(np.isfinite(OUT).sum()), out), flush=True)
