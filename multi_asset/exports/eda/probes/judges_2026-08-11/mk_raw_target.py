"""raw-Y4 target file for the §7.1-C arm — masked to the RESIDUAL arm's label pattern.

★ WHY THE MASK. Y4 has 5,149,962 finite cells; YR4 has 4,516,485 — 633,477 more (+14.0%). Handing
  the raw arm the unmasked Y4 would change TWO things at once: the target VALUES and WHICH CELLS ARE
  LABELLED AT ALL. The prereg says "唯一改动 = 目标", and a 14% larger training population is not
  that. It would also break the paired 5-fold SE, since the two arms would not see the same cells.
  ⇒ raw values, residual arm's finite pattern. One variable.
"""
import numpy as np
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
z = np.load(MA + "/exports/wide_dl_full_corrfund_causal_v1.npz", allow_pickle=True)
ts, y4, yr4 = z["ts"], z["Y4"].astype(np.float32), z["YR4"].astype(np.float32)
assert not np.array_equal(np.nan_to_num(y4), np.nan_to_num(yr4)), "Y4 == YR4?! the swap would be a no-op"
masked = np.where(np.isfinite(yr4), y4, np.nan).astype(np.float32)
# KMASK is intersected into CL (`wide_panel_dataset.py:41`). The interface exists for substitute
# targets valid only on a SUBSET of cells; this one is valid exactly where YR4 is (that is what the
# mask above enforces), so CL must be left ALONE -> all-True. Anything else would silently shrink
# the evaluation grid and make the two arms incomparable.
KMASK = np.ones_like(np.isfinite(yr4), dtype=bool)
np.savez("/tmp/raw_target_Y4.npz", ts=ts, YR4K=masked, KMASK=KMASK)
f_m, f_r = np.isfinite(masked), np.isfinite(yr4)
print("wrote /tmp/raw_target_Y4.npz   YR4K <- Y4 masked to YR4's finite pattern")
print("  finite: raw(unmasked)=%d  YR4=%d  raw(masked)=%d   nan-pattern equal to YR4 = %s"
      % (np.isfinite(y4).sum(), f_r.sum(), f_m.sum(), np.array_equal(f_m, f_r)))
b = f_m
print("  std: raw=%.6f  YR4=%.6f  ratio=%.3f   corr(raw,resid)=%.4f"
      % (masked[b].std(), yr4[b].std(), masked[b].std() / yr4[b].std(),
         np.corrcoef(masked[b], yr4[b])[0, 1]))
