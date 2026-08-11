"""ISOLATION: the first gate was CONFOUNDED — it could not answer the question it was built for.

Gate 1 compared a live-sourced DL panel against causal_v1 and found `size_dvol` (and hence `YR*`)
differing. But the live source differs from the frozen one in THREE keys — `DVOL30`, `Y`, `MEMBER` —
and `size_dvol` is derived from `DVOL30`. So the failure is fully explained by the DVOL30 float
rounding, and says NOTHING about `Y`/`MEMBER`, which were the keys under test.

  A test whose result is explained by a variable it did not intend to vary has not tested anything.

THIS TEST varies ONLY `Y` and `MEMBER`: frozen panel, with those two keys replaced by the live
panel's truncated versions, DVOL30 and all raw arrays left at frozen values. Rebuild, compare 32
channels to causal_v1.

  identical  ⇒ `build_factors`' reads of z["Y"]/z["MEMBER"] provably do not reach the panel.
               The only live-vs-frozen effect is float rounding in DVOL30, which is separately
               quantified (max rel 1.19e-07 = float32 eps).
  different  ⇒ there IS an untraced lineage path through those keys. Genuine stop.
"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/"
S = "/mnt/storage/private/work_hsy/b4_causal_scratch/"

F = np.load(E + "wide_panel_full.npz", allow_pickle=True)
L = np.load(E + "live/wide_panel_live.npz", allow_pickle=True)
n = len(F["ts"])

hyb = {k: F[k] for k in F.keys()}          # start from the FROZEN panel entirely
for k in ("Y", "MEMBER"):                  # swap in ONLY these two, truncated
    hyb[k] = L[k][:n]
# equal_nan=True is REQUIRED here: DVOL30 contains NaN, and np.array_equal without it returns False
# for an array compared against ITSELF. Without the flag this guard goes red for a reason that has
# nothing to do with what it guards — which is exactly the failure mode it exists to catch.
assert np.array_equal(hyb["DVOL30"], F["DVOL30"], equal_nan=True), \
    "DVOL30 must stay frozen — it is the confounder"
assert not np.array_equal(hyb["MEMBER"], F["MEMBER"]), "MEMBER should differ, else nothing varied"
np.savez(S + "wide_panel_hybridYM.npz", **hyb)
print("[hybrid] frozen panel + live Y/MEMBER only; DVOL30 held frozen", flush=True)

from multi_asset.data import build_wide_dl_causal as BC  # noqa: E402

BC.build_causal(S + "wide_panel_hybridYM.npz", S + "wide_dl_hybridYM_causal.npz")

A = np.load(E + "wide_dl_full_causal_v1.npz", allow_pickle=True)
B = np.load(S + "wide_dl_hybridYM_causal.npz", allow_pickle=True)
chn = [str(x) for x in A["ch_names"]]
bad = []
for j, nm in enumerate(chn):
    if not np.array_equal(A["CH"][:, :, j], B["CH"][:, :, j], equal_nan=True):
        bad.append((j, nm, int((A["CH"][:, :, j] != B["CH"][:, :, j]).sum())))
        print("   [ISO] CH[:,:,%2d] %-14s DIFFERS (%d cells)" % bad[-1], flush=True)
for k in ["MEMBER110", "CL1", "CL4", "CL24", "Y1", "Y4", "Y24", "YR1", "YR4", "YR24"]:
    a, b = A[k], B[k]
    same = np.array_equal(a, b, equal_nan=True) if a.dtype.kind == "f" else np.array_equal(a, b)
    print("   %-10s %s" % (k, "identical" if same else "DIFFERS"), flush=True)
    if not same:
        bad.append((None, k, -1))

print("\n[ISO] VERDICT: %s" % (
    "PASS — z[Y]/z[MEMBER] provably do NOT reach the DL panel; gate-1's failure was DVOL30 float "
    "rounding alone" if not bad else "FAIL — a real lineage path runs through z[Y]/z[MEMBER]"),
    flush=True)
sys.exit(1 if bad else 0)
