"""S2 MUST-PASS GATE (team-lead ruling 3): are the live-source `Y`/`MEMBER` differences irrelevant?

`wide_panel_live.npz` reproduces the frozen panel bit-for-bit on the 8 raw arrays, but `Y`,
`MEMBER` and `DVOL30` differ across history. `DVOL30` was shown to differ only at float-rounding
scale (MEMBER110 derived from either is bit-identical). `Y` and `MEMBER` are read by
`wide_factory.build_factors` (line 95) and I never traced what for — so "irrelevant" was an
inference, not a measurement.

THE TEST: truncate the live-sourced raw panel to the frozen panel's exact 48,168 rows, build the DL
panel from it with the SAME causal builder, and compare all 32 channels to `causal_v1` (built from
the CSV source) bit-for-bit.

  identical  ⇒ whatever build_factors does with those two keys provably does not reach the panel,
               and the live source is a drop-in for S2.
  different  ⇒ there is a lineage difference on the factor path that nobody has traced. STOP.
"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/"
S = "/mnt/storage/private/work_hsy/b4_causal_scratch/"

F = np.load(E + "wide_panel_full.npz", allow_pickle=True)
L = np.load(E + "live/wide_panel_live.npz", allow_pickle=True)
n = len(F["ts"])
out = {}
for k in L.keys():
    a = L[k]
    out[k] = a[:n] if (a.ndim >= 1 and a.shape[0] == len(L["ts"])) else a
assert np.array_equal(out["ts"], F["ts"]), "ts mismatch after truncation"
np.savez(S + "wide_panel_liveTRUNC.npz", **out)
print("[trunc] wrote liveTRUNC T=%d" % len(out["ts"]), flush=True)

for k in ["Y", "MEMBER", "DVOL30"]:
    a, b = F[k], out[k]
    same = np.array_equal(a, b, equal_nan=True) if a.dtype.kind == "f" else np.array_equal(a, b)
    print("   source-level %-8s identical to frozen: %s   <-- the keys under test" % (k, same),
          flush=True)

from multi_asset.data import build_wide_dl_causal as BC  # noqa: E402

BC.build_causal(S + "wide_panel_liveTRUNC.npz", S + "wide_dl_liveTRUNC_causal.npz")

A = np.load(E + "wide_dl_full_causal_v1.npz", allow_pickle=True)
B = np.load(S + "wide_dl_liveTRUNC_causal.npz", allow_pickle=True)
chn = [str(x) for x in A["ch_names"]]
bad = []
for j, nm in enumerate(chn):
    if not np.array_equal(A["CH"][:, :, j], B["CH"][:, :, j], equal_nan=True):
        d = int((A["CH"][:, :, j] != B["CH"][:, :, j]).sum())
        bad.append((j, nm, d))
        print("   [GATE] CH[:,:,%2d] %-14s DIFFERS (%d cells)" % (j, nm, d), flush=True)
print("\n[GATE] 32-channel bitwise  CSV-source vs LIVE-source: %s"
      % ("ALL 32 IDENTICAL" if not bad else "DIFFER"), flush=True)

for k in ["ts", "symbols", "ch_names", "baseline_cols", "MEMBER110",
          "CL1", "CL4", "CL24", "Y1", "Y4", "Y24", "YR1", "YR4", "YR24"]:
    a, b = A[k], B[k]
    same = np.array_equal(a, b, equal_nan=True) if a.dtype.kind == "f" else np.array_equal(a, b)
    print("   %-14s %s" % (k, "identical" if same else "DIFFERS"), flush=True)
    if not same:
        bad.append((None, k, -1))

print("\n[GATE] VERDICT: %s" % ("PASS — z[Y]/z[MEMBER] differences provably do NOT reach the DL "
                                "panel; live source is a drop-in for S2"
                                if not bad else "FAIL — STOP AND REPORT"), flush=True)
sys.exit(1 if bad else 0)
