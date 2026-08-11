"""#21 pre-check: are the candidates orthogonal to the king FOR THE RIGHT REASON?

★ THE WORRY, stated before measuring: `YR4` — the DL target — is built as
  `_xsec_residualize(Y4, Xbase, MEM)` where Xbase = the panel's `baseline_cols`. If a candidate IS
  one of those columns, then the king was trained on a target with that candidate PROJECTED OUT ⇒
  the king carries (near) zero exposure to it ⇒ **gate 3 (|rho| < 0.3 vs king) passes BY
  CONSTRUCTION.** Passing a criterion for a reason unrelated to the property it claims to establish
  is the §8-e failure mode, and gate 3 is the one that DEFINES breadth.
"""
import numpy as np
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
z = np.load(MA + "/exports/wide_dl_full_corrfund_causal_v1.npz", allow_pickle=True)
base = [str(c) for c in z["baseline_cols"]]
chn = [str(c) for c in z["ch_names"]]
CAND = ["mom_4h", "mom_8h", "mom_24h", "mom_72h", "mom_168h", "rev_1h", "rev_3h",
        "gtja_046", "a101_044", "max_ret_24h", "rvol_24h", "rvol_72h",
        "lturnover_24h", "size_dvol"]
print("baseline_cols (what YR4 is residualised against): %s\n" % base)
inb = [c for c in CAND if c in base]
notb = [c for c in CAND if c not in base]
print("%-16s %-12s %-12s" % ("candidate", "in baseline?", "in wide_dl ch?"))
for c in CAND:
    print("  %-14s %-12s %-12s" % (c, "★ YES" if c in base else "no",
                                   "yes" if c in chn else "not in this panel"))
print("\n⇒ %d of %d candidates ARE baseline columns: %s" % (len(inb), len(CAND), inb))
print("⇒ %d are not: %s" % (len(notb), notb))
print("""
★★★ CONSEQUENCE FOR GATE 3, before any compute is spent:
  For the %d candidates that ARE baseline columns, the king's target had them projected out, so
  low |rho| vs the king is GUARANTEED BY THE TARGET'S CONSTRUCTION. Gate 3 would pass for a reason
  that has nothing to do with those factors supplying breadth — the §8-e shape, landing on the one
  gate that DEFINES breadth.
  ⇒ Gate 3 vs the KING is uninformative for them. It stays informative vs s2 and funding (whose
    targets are not built that way), and the honest reading is per-sleeve, not pooled.
  ⇒ And the mirror worry for the other %d: they were never projected out, so a HIGH |rho| there is
    a real finding rather than an artifact.
""" % (len(inb), len(notb)))
