"""S2 partial — the FIRST panel whose YR is residualised against CORRECTED funding.

Tonight's buildable subset of v8 §S2: item (c) (corrected funding caliber into the DL input AND the
residualisation baseline) + the causal ch31 fix. Items (a) span-extension and (b) coin-set refresh
are NOT here — both need CDN acquisition that is not on disk (see report).

★ WHY THIS IS WORTH BUILDING ON ITS OWN, not a consolation prize:
  `apply_funding_fix.py` patched ch0/ch28 of the shipped panel but explicitly did NOT recompute YR —
  its docstring: "YR residual targets were residualised against the un-normalised funding column --
  a recorded caveat ... deferred to THE NEXT RETRAIN CYCLE." This IS that cycle. Every panel to date
  has trained against a baseline containing the un-normalised funding column.

★ AND IT IS A BETTER CONTROLLED EXPERIMENT THAN THE FULL S2 WOULD HAVE BEEN:
  the span is unchanged, so the folds are bit-identical to S1's. S1 vs this differs in EXACTLY ONE
  thing — the funding caliber. Extending the span at the same time would have confounded the two.

Corrected funding comes from 0C's `funding_ema_normfix.npz::FN` (the declared source of truth that
`apply_funding_fix.py` consumes rather than reimplementing), asserted here to be on this panel's
exact (ts, symbols) grid before use.
"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/"
S = "/mnt/storage/private/work_hsy/b4_causal_scratch/"
OUT_SRC = S + "wide_panel_full_corrfund.npz"
OUT_DL = E + "wide_dl_full_corrfund_causal_v1.npz"

F = np.load(E + "wide_panel_full.npz", allow_pickle=True)
FN = np.load(E + "eda/funding_ema_normfix.npz", allow_pickle=True)

assert np.array_equal(F["ts"], FN["ts"]), "FN is not on this panel's ts grid"
assert [str(s) for s in F["symbols"]] == [str(s) for s in FN["symbols"]], "symbol order differs"
corr = FN["FN"].astype(F["FUND_EMA"].dtype)
assert corr.shape == F["FUND_EMA"].shape
old = F["FUND_EMA"]
fin = np.isfinite(old) & np.isfinite(corr)
print("[src] FN on-grid asserted. corrected vs as-trained FUND_EMA: %d/%d finite cells differ, "
      "median |rel| = %.4f" % (int((old[fin] != corr[fin]).sum()), int(fin.sum()),
                               float(np.median(np.abs((corr[fin] - old[fin]) /
                                                      np.maximum(np.abs(old[fin]), 1e-12))))),
      flush=True)
assert not np.array_equal(old, corr, equal_nan=True), "corrected == as-trained: nothing would change"

src = {k: F[k] for k in F.keys()}
src["FUND_EMA"] = corr
np.savez(OUT_SRC, **src)
print("[src] wrote %s (ONLY FUND_EMA swapped; every other key frozen)" % OUT_SRC, flush=True)

from multi_asset.data import build_wide_dl_causal as BC  # noqa: E402

BC.build_causal(OUT_SRC, OUT_DL)

# ---- assertions: exactly the funding-derived surface may move, nothing else ----
A = np.load(E + "wide_dl_full_causal_v1.npz", allow_pickle=True)   # S1 panel: causal + as-trained fund
B = np.load(OUT_DL, allow_pickle=True)                             # this:     causal + corrected fund
chn = [str(x) for x in A["ch_names"]]
MUST_DIFFER = {"funding_ema", "xsr_fund"}
bad = []
print("\n[assert] vs S1 panel (causal_v1) — only the funding-derived surface may move")
for j, nm in enumerate(chn):
    same = np.array_equal(A["CH"][:, :, j], B["CH"][:, :, j], equal_nan=True)
    want_same = nm not in MUST_DIFFER
    ok = (same == want_same)
    if not ok:
        bad.append(nm)
    print("   CH[:,:,%2d] %-14s %-9s %s" % (j, nm, "identical" if same else "DIFFERS",
                                            "OK" if ok else "*** UNEXPECTED ***"), flush=True)
for k in ["ts", "symbols", "ch_names", "baseline_cols", "MEMBER110", "CL1", "CL4", "CL24",
          "Y1", "Y4", "Y24"]:
    a, b = A[k], B[k]
    same = np.array_equal(a, b, equal_nan=True) if a.dtype.kind == "f" else np.array_equal(a, b)
    print("   %-14s %s %s" % (k, "identical" if same else "DIFFERS", "OK" if same else "*** ***"))
    if not same:
        bad.append(k)
# YR MUST differ — that is the whole point of doing this at a retrain cycle
for k in ["YR1", "YR4", "YR24"]:
    diff = not np.array_equal(A[k], B[k], equal_nan=True)
    print("   %-14s %s %s" % (k, "DIFFERS" if diff else "identical",
                              "OK (residualised on corrected funding)" if diff
                              else "*** UNEXPECTED: baseline did not move ***"))
    if not diff:
        bad.append(k)

print("\n[assert] VERDICT: %s" % ("PASS" if not bad else "FAIL %s" % bad), flush=True)
sys.exit(1 if bad else 0)
