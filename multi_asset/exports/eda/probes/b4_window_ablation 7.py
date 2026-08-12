"""探针A — how much of its 168-hour window does the clean king actually use? (ledger #25)

> created 2026-08-04 11:3x UTC | Session: B4-retrain | CPU only, no training

★ THE QUESTION, and why it is the cheapest way to settle the "temporal depth" axis:
  a frozen model, scored with progressively less history. If resid rank-IC saturates by half the
  window, "the clean signal is shallow" stops being an inference from `best_epoch` and becomes
  direct evidence — and the whole deepen/long-context family is downgraded. If it is still climbing
  at full window, the model has not finished eating history and long-window/multi-scale is a real
  proposal. (Single-asset `phase_d` multiscale failed, but that does NOT extrapolate: pooling has
  reversed single-asset conclusions before.)

★★ HOW THE WINDOW IS TRUNCATED, and why not the obvious way.
  NOT by feeding a shorter sequence: that changes the input SHAPE the model was trained on, which is
  a second variable (and conv/attention edge effects would be attributed to "depth").
  INSTEAD: normalise exactly as usual, then **zero the first (W − W') timesteps**. After
  standardisation, zero IS the training mean — so this removes the information while staying in
  distribution and keeping the shape identical.

★ NOT A REIMPLEMENTATION. `predict_scores_wide` is called unmodified; a thin wrapper around the
  dataset's `iter_batches` blanks the head of each batch's `Xseq`. Four scripts hand-rolled that
  forward loop tonight and one of them was wrong by 3.5e-2 — this one does not join them.

★★★ RESULT (2026-08-04, clean king S1F, folds 2/3/4, GPU):

      keep  frac   resid rank-IC   vs full    per-fold
        1   0.01     +0.02973      -37.1%   [0.02666, 0.03429, 0.02823]
       42   0.25     +0.04281       -9.4%   [0.04359, 0.04128, 0.04356]
       84   0.50     +0.04565       -3.4%   [0.04599, 0.04345, 0.04751]
      126   0.75     +0.04773       +1.0%   [0.04780, 0.04521, 0.05018]
      168   1.00     +0.04727        0.0%   [0.04754, 0.04613, 0.04815]

   Controls: NO-OP max|d| = 0.000e+00 on all three folds (bitwise); keep=1 is -37.1%.

   ⇒ The curve SATURATES at ~0.75 of the window (126h ~ 5.25 days) and then goes FLAT. keep=126
     reads +1.0% above full, but the per-fold signs disagree (+0.5 / -2.0 / +4.2) — that is noise,
     not "shorter is better", and it is written here so nobody quotes the +1.0%.
   ⇒ **#30's unlock condition was "still climbing at full window". It is not. #30 stays locked.**
   ⇒ But this is NOT "the signal is shallow": 42h -> 126h buys +11.5%. There is real temporal
     structure between a quarter and three quarters of the window.
   ⇒ The accurate phrasing for the temporal-depth axis is **not "closed" but "already saturated"**:
     the existing 168h window already covers everything the model can use (~126h), so lengthening
     it has nothing left to eat — while halving it costs -3.4%.

★ TWO BUILT-IN CONTROLS (§8-e — a criterion with no partner can be satisfied by doing nothing):
    W' = 168 (full)  -> a NO-OP. Must reproduce the frozen scores BITWISE. If it does not, the
                        wrapper is perturbing something it should not and no other row is readable.
    W' = 1           -> the opposite-side ruler. One timestep of history must be clearly worst;
                        if it is not, the ablation is not reaching the model at all.
"""
import sys

import numpy as np
import torch
from scipy.stats import rankdata

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
from multi_asset.data.wide_panel_dataset import WidePanelData          # noqa: E402
from multi_asset.model.wide_harness import WideFactorModel             # noqa: E402
import multi_asset.train.train_wide_harness as TH                      # noqa: E402

torch.backends.mkldnn.enabled = False
# Device: GPU when free. The CPU run was abandoned after 25 min with 0/3 folds done — 15 scoring
# passes (5 windows x 3 folds) is not a CPU workload. On GPU the NO-OP control is also bitwise (1e-7
# on CPU vs 0 on GPU, measured earlier today), so the control gets stricter, not looser.
TH.DEV = "cuda" if torch.cuda.is_available() else "cpu"
PANEL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"
RUN = MA + "/exports/train/wideA_lamorth0_xattn_5yr_corrfund_v1"     # clean king (S1F), certified
H, EMB = 4, 8
FOLDS_TO_RUN = (2, 3, 4)          # later folds = most training data; 3 folds keeps this ~free


class HeadBlanked:
    """Delegates everything to the real dataset; blanks the first (W-keep) steps of each Xseq."""

    def __init__(self, d, keep):
        self._d, self.keep = d, keep

    def __getattr__(self, k):
        return getattr(self._d, k)

    def iter_batches(self, *a, **kw):
        cut = self._d.W - self.keep
        for b in self._d.iter_batches(*a, **kw):
            if cut > 0:
                b["Xseq"][:, :, :cut, :] = 0.0      # 0 in z-space == the training mean
            yield b


z = np.load(PANEL, allow_pickle=True)
MEM, YR4, CL4 = z["MEMBER110"], z["YR4"], z["CL4"]
AUX = tuple(x for x in (1, 24) if x != H)
d = WidePanelData(path=PANEL, target_horizon=H, aux_horizons=AUX)
folds = TH.year_folds(d, embargo_days=EMB, val_days=30, year_from=None)
W = d.W
KEEPS = [1, W // 4, W // 2, 3 * W // 4, W]
print("window W=%d ; keeps=%s (=%s of window)"
      % (W, KEEPS, [round(k / W, 2) for k in KEEPS]), flush=True)


def composite_ic(sc, te):
    ics = []
    for t in te:
        base = np.where(MEM[t] & CL4[t])[0]
        if base.size < 5:
            continue
        acc = np.zeros(base.size); nk = 0
        for j in range(sc.shape[2]):
            col = sc[t, base, j].astype(np.float64)
            if np.isfinite(col).all() and col.std() > 1e-12:
                acc += (col - col.mean()) / col.std(); nk += 1
        if nk == 0:
            continue
        p = acc / nk
        v = np.isfinite(p) & np.isfinite(YR4[t, base])
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(p[v]), rankdata(YR4[t, base][v]))[0, 1])
    return float(np.nanmean(ics)) if ics else np.nan


res = {k: [] for k in KEEPS}
fidelity = []
for fi in FOLDS_TO_RUN:
    d.set_fold(folds[fi]["tr"])
    saved = np.load(RUN + "/fold_%d_head_scores.npz" % fi)
    enc = TH.build_encoder("conformer", 32, TH.D_MODEL, TH.N_BLOCKS, TH.KERNEL, TH.DROPOUT)
    m = WideFactorModel(enc, n_factor_heads=6, xattn=True, n_xattn=1,
                        dropout=TH.DROPOUT, aux_horizons=()).to(TH.DEV)
    m.load_state_dict(torch.load(RUN + "/fold_%d_model.pt" % fi, map_location=TH.DEV))
    m.eval()
    for keep in KEEPS:
        sc = TH.predict_scores_wide(m, HeadBlanked(d, keep), saved["te_days"], 32, 6)
        res[keep].append(composite_ic(sc, saved["te_rows"]))
        if keep == W:                                   # the NO-OP control
            rows = saved["te_rows"][:300]
            g, w_ = sc[rows], saved["scores"][rows]
            b = np.isfinite(g) & np.isfinite(w_)
            fidelity.append(float(np.abs(g[b] - w_[b]).max()) if b.any() else np.inf)
    print("  fold %d done: %s" % (fi, {k: round(res[k][-1], 5) for k in KEEPS}), flush=True)
    del m

print("\n=== CONTROLS FIRST (nothing below is readable unless both pass) ===")
worst_fid = max(fidelity)
print("  NO-OP (keep=W) vs frozen scores: max|d| = %.3e per fold %s  -> %s"
      % (worst_fid, [("%.1e" % f) for f in fidelity],
         "PASS" if worst_fid < 1e-5 else "*** FAIL — wrapper perturbs the input ***"))
full, one = np.mean(res[W]), np.mean(res[1])
print("  RULER (keep=1) %.5f vs full %.5f  -> %s"
      % (one, full, "clearly worst, ablation reaches the model"
         if one < 0.7 * full else "*** NOT clearly worst — the ablation may not be reaching it ***"))

print("\n%-10s %-8s %10s   %s" % ("keep", "frac", "resid rank-IC", "vs full"))
for k in KEEPS:
    mu = np.mean(res[k])
    print("  %-8d %-8.2f %+10.5f   %+6.1f%%   per-fold %s"
          % (k, k / W, mu, 100 * (mu / full - 1), np.round(res[k], 5).tolist()))

half = np.mean(res[W // 2])
print("\n=== PRE-REGISTERED READING (ledger #25) ===")
print("  half-window %+.5f vs full %+.5f  -> %+.1f%%" % (half, full, 100 * (half / full - 1)))
if half >= 0.98 * full:
    print("  ⇒ SATURATED BY HALF WINDOW: the clean signal is SHALLOW — direct evidence, not a")
    print("    best_epoch proxy. Temporal-depth axis CLOSED (deepen / long-context family down).")
elif np.mean(res[3 * W // 4]) < 0.98 * full:
    print("  ⇒ STILL CLIMBING AT FULL WINDOW: the model has not finished eating history.")
    print("    Temporal depth is a real lever ⇒ open a long-window/multi-scale proposal.")
    print("    ★ single-asset phase_d multiscale FAILED, but that does not extrapolate — pooling")
    print("      has reversed single-asset conclusions before. New proposal, new prereg.")
else:
    print("  ⇒ IN BETWEEN: saturates somewhere in (0.5, 1.0] of the window. Report the curve; the")
    print("    lever is neither closed nor clearly open on this evidence alone.")
