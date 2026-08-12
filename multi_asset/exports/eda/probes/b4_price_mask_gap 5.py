"""Price the train/serve MASK gap, using production's own `infer()` rather than a copy of it.

> created 2026-08-04 10:xx UTC | Session: B4-retrain | status: final
> dispatch (team-lead a1e66aff §3): same frozen king, same anchors, ONLY the mask changes.

★ WHY IMPORT AND NOT REIMPLEMENT. Tonight's most expensive defect was four scripts hand-rolling
  `predict_scores_wide`, none comparing against it, wrong by 3.5e-2 on the s2 leg. Pricing the gap
  with a fifth copy of `infer()` would repeat exactly that. So this imports
  `engine.live.signal_loop.infer` — the function production actually runs.

★★ THE GAP IS TWO GATES, NOT ONE. team-lead read the live mask as member-only and the training mask
   as member & CL, and both readings are right, but the difference has a second term:

     training / predict_scores_wide : member & CL & isfinite(Y)     (iter_batches, dense=False)
     research "densify" d.CL=member : member      & isfinite(Y)     (== the dense=True branch)
     LIVE infer()                   : member                        (no CL gate, NO isfinite(Y) gate)

   The live comment says why the Y gate cannot be there: *"no future-Y gate, so live anchors with
   unrealized targets still score"* — at an anchor the forward return does not exist yet. So the
   densified research arm is CLOSER to live than the CL arm, but it is still not live: it keeps a
   gate that live structurally cannot have. "Densify == production" is nearly right, not right.

★ WHAT EACH ARM ANSWERS. Read the three as a ladder, not as right-vs-wrong:
     CL arm     — what the frozen scores contain, the only arm with a bitwise reference
     dense arm  — what every book to date used
     live arm   — what production actually computes
   The distance from the CL arm to the live arm is the quantity that has never been priced.
"""
import sys

import numpy as np
import torch

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")

from multi_asset.data.wide_panel_dataset import WidePanelData          # noqa: E402
from multi_asset.model.wide_harness import WideFactorModel             # noqa: E402
import multi_asset.train.train_wide_harness as TH                      # noqa: E402
import signal_loop as SL                                               # noqa: E402

CASES = [
    ("KING  (deployed, emb 8)", MA + "/exports/train/wideA_lamorth0_xattn_5yr",
     MA + "/exports/wide_dl_full.npz", 4, 8),
    ("s2    (deployed, emb 10)", MA + "/exports/train/wideA_s2_y24_5yr",
     MA + "/exports/wide_dl_full.npz", 24, 10),
]
NROW = 300

for name, RUN, PANEL, H, EMB in CASES:
    print("\n" + "=" * 92)
    print("=== %s ===" % name, flush=True)
    AUX = tuple(x for x in (1, 24) if x != H)
    d = WidePanelData(path=PANEL, target_horizon=H, aux_horizons=AUX)
    folds = TH.year_folds(d, embargo_days=EMB, val_days=30, year_from=None)
    f4 = folds[4]
    d.set_fold(f4["tr"])
    enc = TH.build_encoder("conformer", 32, TH.D_MODEL, TH.N_BLOCKS, TH.KERNEL, TH.DROPOUT)
    m = WideFactorModel(enc, n_factor_heads=6, xattn=True, n_xattn=1,
                        dropout=TH.DROPOUT, aux_horizons=()).to(TH.DEV)
    m.load_state_dict(torch.load(RUN + "/fold_4_model.pt", map_location=TH.DEV))
    m.eval()

    saved = np.load(RUN + "/fold_4_head_scores.npz")
    te_rows = saved["te_rows"]
    rows = np.asarray(te_rows[:NROW])

    # ---- arm 1: the training/scoring mask (member & CL & isfinite(Y)) — has a bitwise reference
    sc_cl = TH.predict_scores_wide(m, d, saved["te_days"], 32, 6)
    ref = saved["scores"][rows]
    b = np.isfinite(sc_cl[rows]) & np.isfinite(ref)
    print("  [CL arm] vs frozen scores: max|d|=%.3e (must be ~0 or nothing below is anchored)"
          % (np.abs(sc_cl[rows][b] - ref[b]).max() if b.any() else np.nan), flush=True)

    # ---- arm 3: production's own infer(), member-only, imported not copied
    mcpu = m.to("cpu")
    comp_live = SL.infer(d, mcpu, rows)

    # composite the CL arm the same way live composites, so only the MASK differs
    comp_cl = np.full_like(comp_live, np.nan)
    for t in rows:
        base = np.where(d.member[t])[0]
        c = SL._composite(sc_cl[t], base)
        if c is not None:
            comp_cl[t, base] = c

    ok = np.isfinite(comp_cl) & np.isfinite(comp_live)
    n_live = int(np.isfinite(comp_live).sum())
    n_cl = int(np.isfinite(comp_cl).sum())
    if ok.sum() > 10:
        from scipy.stats import spearmanr
        rho = float(spearmanr(comp_cl[ok], comp_live[ok]).statistic)
        print("  cells: CL arm %d | live arm %d | overlap %d" % (n_cl, n_live, int(ok.sum())))
        print("  ★ composite  max|d|=%.3e  mean|d|=%.3e  pearson=%.6f  spearman=%.6f"
              % (np.abs(comp_cl[ok] - comp_live[ok]).max(),
                 np.abs(comp_cl[ok] - comp_live[ok]).mean(),
                 np.corrcoef(comp_cl[ok], comp_live[ok])[0, 1], rho), flush=True)
        # per-anchor cross-sectional agreement — the quantity a book actually consumes
        pa = []
        for t in rows:
            v = np.isfinite(comp_cl[t]) & np.isfinite(comp_live[t])
            if v.sum() >= 5:
                pa.append(spearmanr(comp_cl[t, v], comp_live[t, v]).statistic)
        pa = np.array(pa, float)
        print("  ★★ per-anchor xsec spearman(CL, live): mean=%.6f  p05=%.6f  min=%.6f  n=%d"
              % (np.nanmean(pa), np.nanpercentile(pa, 5), np.nanmin(pa), len(pa)), flush=True)
    else:
        print("  insufficient overlap")
    del m, mcpu

print("\n★ read the per-anchor xsec spearman, not max|d|: a book consumes the cross-sectional")
print("  ORDER at each anchor, and tonight twice already a large max|d| was worth <1% at book level.")
