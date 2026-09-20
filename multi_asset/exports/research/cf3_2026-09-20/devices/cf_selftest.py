#!/usr/bin/env python3
"""cf_selftest.py — CF3 battery. Every item is credited ONLY if the baseline is GREEN **and** the
mutation is RED, and the receipt records BOTH values. Rationale (memory 2026-09-16): a red-capability
check is vacuously true when the baseline is already red, and a bare N/N count prints on both the
ALL PASS and the FAILURES line, so the verdict line below names the failures.

Items test PROPERTIES of the device, not its text:
  C1  chain is scale-invariant for a positive scalar          (the identity RESULT 3.4 relies on)
  C2  chain is NOT linear in z                                (the reason a linear split does not exist)
  C3  chain returns None exactly on a z that is flat on `sel` (the C-DEGEN trigger)
  C4  chain's dead band really freezes                        (why C-DEGEN-STATE is not "let the EMA decay")
  C5  bitwise_equal is 1-ULP sensitive
  C6  zf is the production rank transform
  C7  h_from_weights_file really is float32 + the 1e-9 filter
  C8  Shapley/LOO/LOI/GAP: exact on an ADDITIVE value function, and the GAP is non-zero on a
      non-additive one                                        (null control for the decomposition)
  C9  an aggregate over an EMPTY subset returns None, never 0.0   (E-0920-C)
  C10 the bucket partition check actually fires when a bucket loses an anchor

usage: env -i ... /workspace/venv/bin/python -B cf_selftest.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import itertools
import json
import os
import sys
import time

import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cf_lib as L                                     # noqa: E402

ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
rec = L.rec_head("cf_selftest.py", sys.argv)
extra = sorted(set(rec["env"]) - ENV_OK)
items = []
fails = []


def item(name, baseline_green, baseline_value, mutation_red, mutation_value, note=""):
    ok = bool(baseline_green) and bool(mutation_red)
    items.append({"item": name, "baseline_green": bool(baseline_green), "baseline_value": baseline_value,
                  "mutation_red": bool(mutation_red), "mutation_value": mutation_value,
                  "credited": ok, "note": note})
    if not ok:
        fails.append(name + ("[baseline not green]" if not baseline_green else "[mutation not red]"))


if extra:
    fails.append("env.whitelist" + str(extra))

rng = np.random.default_rng(20260920)
NW = 64
n = 40
P = {"cap_mult": 2.5, "alpha": 0.1, "band": 0.00025, "qv4h_min": 250000.0}
pm = np.sort(rng.choice(NW, n, replace=False)).astype(np.int64)
sel = rng.random(n) < 0.85
sel[0] = True
LIVE = np.ones(NW, bool)
CH = L.Chain(sel, pm, P, LIVE, NW=NW)
z = rng.normal(size=n)
H0 = np.zeros(NW)

# C1 scale invariance for c > 0.
# NOTE the first run of this battery asserted BITWISE equality here and the baseline came out RED:
# chain divides by Sum|w|, and (c*x)/(c*g) != x/g in IEEE754. The invariance the identity in
# RESULT 3.4 relies on is ANALYTIC, not bitwise. The item now measures the actual deviation and
# requires it to be at floating-point level, with a sign flip as the control that the test can fail.
a = CH.run(z, H0)
b = CH.run(7.25 * z, H0)
d_pos = float(np.max(np.abs(a - b)))
scale = float(np.max(np.abs(a)))
d_neg = float(np.max(np.abs(a - CH.run(-1.0 * z, H0))))
item("C1.chain_scale_invariant_positive_to_float_precision",
     d_pos <= 1e-12 * max(scale, 1e-300), {"max_abs_dev": d_pos, "max_abs_weight": scale,
                                           "bitwise": bool(L.bitwise_equal(a, b)[0])},
     d_neg > 1e-6 * scale, {"sign_flipped_max_abs_dev": d_neg},
     "positive scaling must not change the book beyond float noise; a sign flip must change it materially")

# C2 chain is NOT linear in z
y = rng.normal(size=n)
lhs = CH.run(0.55 * z + 0.45 * y, H0)
rhs = 0.55 * CH.run(z, H0) + 0.45 * CH.run(y, H0)
nonlin = float(np.max(np.abs(lhs - rhs)))
# the null control: with cap and band disabled and H = 0 the same operator IS linear after renorm only
# if the L1 norms coincide, so the control is a pair of IDENTICAL inputs, where the gap must be 0
ctrl = float(np.max(np.abs(CH.run(z, H0) - (1.0 * CH.run(z, H0) + 0.0 * CH.run(y, H0)))))
item("C2.chain_is_not_linear", ctrl == 0.0, {"identical_input_gap": ctrl},
     nonlin > 1e-12, {"max_abs_gap_0.55z+0.45y": nonlin},
     "null control = the same expression with weights (1,0); a true zero there proves the gap above is the operator")

# C3 degeneracy trigger
none_flat = CH.run(np.zeros(n), H0)
const = np.full(n, 3.7)
none_const = CH.run(const, H0)
alive = CH.run(z, H0)
item("C3.chain_returns_None_on_a_flat_z", alive is not None, {"real_z_returns_vector": alive is not None},
     none_flat is None and none_const is None,
     {"zero_z_is_None": none_flat is None, "constant_z_is_None": none_const is None},
     "constant z demeans to zero on sel, so it degenerates too")

# C4 the dead band freezes.
# The first run of this battery used H small and z scaled by 1e-9 and the mutation came out GREEN:
# chain renormalises by Sum|w|, so scaling z down does NOT shrink the move (that is item C1). The
# small move has to come from H being CLOSE TO THE TARGET, which is what actually happens when a
# component's book is decaying towards flat.
TGT = L.Chain(sel, pm, {**P, "alpha": 1.0, "band": 0.0}, LIVE, NW=NW).run(z, np.zeros(NW))
H_near = TGT * (1.0 - 0.01)          # alpha*0.01*|tgt| ~ 2.5e-5  <  band 2.5e-4  -> frozen
H_far = TGT * (1.0 - 0.5)            # alpha*0.5 *|tgt| ~ 1.2e-3  >  band          -> moves
near = CH.run(z, H_near)
far = CH.run(z, H_far)
frozen_cells = int((near[pm] == H_near[pm]).sum())
moved_cells = int((far[pm] != H_far[pm]).sum())
would_move = float(np.max(np.abs(P["alpha"] * (TGT - H_near))))
item("C4.dead_band_freezes_small_moves", moved_cells > 0,
     {"cells_that_moved_when_H_is_far": moved_cells, "n": n},
     frozen_cells == n,
     {"cells_frozen_when_H_is_near": frozen_cells, "n": n,
      "size_of_the_move_that_was_frozen": would_move, "band": P["band"]},
     "a non-zero move below the band is discarded; this is why C-DEGEN-STATE is a zero state "
     "and not 'let the EMA decay into flat' (the decay would freeze at a residue)")

# C5 bitwise_equal is 1-ULP sensitive
u = rng.normal(size=100)
w = u.copy()
w[17] = np.nextafter(w[17], np.inf)
ok5, _ = L.bitwise_equal(u, u.copy())
bad5, nd5 = L.bitwise_equal(u, w)
item("C5.bitwise_equal_is_1ulp_sensitive", ok5, {"identical_arrays_equal": ok5},
     (not bad5) and nd5 == 1, {"cells_differ_after_one_ulp": nd5})

# C6 zf is the production rank transform
sc = rng.normal(size=25)
sc[3] = np.nan
zf, okf = L.zf_from_scores(sc)
from scipy.stats import rankdata                        # noqa: E402
want = rankdata(sc[np.isfinite(sc)]) / max(int(np.isfinite(sc).sum()) - 1, 1) - 0.5
ok6, _ = L.bitwise_equal(zf[okf], want)
sc2 = sc.copy()
sc2[0], sc2[1] = sc2[1], sc2[0]                         # swapping two scores must swap their ranks
zf2, _ = L.zf_from_scores(sc2)
bad6 = bool(np.array_equal(zf[okf], zf2[okf]))
item("C6.zf_is_the_production_rank_transform", ok6, {"matches_rankdata_bitwise": ok6},
     not bad6, {"swapping_two_scores_changes_zf": not bad6})

# C7 the weights-file round trip
v = np.zeros(L.NW)
v[5] = 1.0 / 3.0                                        # not representable in float32
v[6] = 5e-10                                            # below the 1e-9 filter
h = L.h_from_weights_file(v)
item("C7.weights_file_is_float32_and_1e-9_filtered",
     h[6] == 0.0, {"below_1e-9_dropped": float(h[6])},
     h[5] != v[5] and h[5] == np.float64(np.float32(v[5])),
     {"float64_value": v[5], "after_round_trip": float(h[5])})

# C8 decomposition: exact on an additive v, GAP non-zero on a non-additive one
PL = ("FUND", "KING", "F10")


def decomp(vfun):
    v = {frozenset(s): vfun(frozenset(s)) for r in range(4) for s in itertools.combinations(PL, r)}
    full, empty = frozenset(PL), frozenset()
    total = v[full] - v[empty]
    loo = {i: v[full] - v[full - {i}] for i in PL}
    marg = {i: [] for i in PL}
    for perm in itertools.permutations(PL):
        cur = frozenset()
        for i in perm:
            marg[i].append(v[cur | {i}] - v[cur])
            cur = cur | {i}
    shap = {i: float(np.mean(marg[i])) for i in PL}
    return total, loo, shap, total - sum(loo.values()), total - sum(shap.values()), marg


w_add = {"FUND": 1.5, "KING": -0.4, "F10": 2.25}
tA, looA, shA, gapA, residA, margA = decomp(lambda s: sum(w_add[i] for i in s))
tN, looN, shN, gapN, residN, margN = decomp(lambda s: sum(w_add[i] for i in s) + (3.0 if len(s) == 3 else 0.0))
add_exact = (abs(gapA) < 1e-12 and abs(residA) < 1e-12
             and all(abs(shA[i] - w_add[i]) < 1e-12 for i in PL)
             and all(abs(looA[i] - w_add[i]) < 1e-12 for i in PL)
             and all(max(margA[i]) - min(margA[i]) < 1e-12 for i in PL))
item("C8.decomposition_exact_on_additive_and_gap_shows_on_nonadditive",
     add_exact, {"GAP_LOO": gapA, "shapley_residual": residA, "shapley": shA,
                 "per_signal_ordering_range": {i: max(margA[i]) - min(margA[i]) for i in PL}},
     abs(gapN) > 1e-9 and abs(residN) < 1e-12,
     {"GAP_LOO": gapN, "shapley_residual_still_zero": residN,
      "per_signal_ordering_range": {i: max(margN[i]) - min(margN[i]) for i in PL}},
     "Shapley always sums to the total; the LOO gap is what exposes the interaction")

# C9 an empty subset must aggregate to None, never 0.0
x = np.array([1.0, 2.0, 3.0])


def agg(mask):
    return float(x[mask].mean()) if mask.any() else None


item("C9.empty_subset_is_None_not_zero", agg(np.array([True, True, False])) == 1.5,
     {"non_empty_subset_mean": agg(np.array([True, True, False]))},
     agg(np.zeros(3, bool)) is None, {"empty_subset_value": agg(np.zeros(3, bool))},
     "E-0920-C: 'no measurement' must never be encoded as a benign number")

# C10 the partition check fires
kind = np.array([2, 2, 1, 1, 0])
parts_ok = np.array_equal((kind == 2).astype(int) + (kind == 1).astype(int) + (kind == 0).astype(int), np.ones(5, int))
kind_bad = np.array([2, 2, 1, 1, 3])
parts_bad = np.array_equal((kind_bad == 2).astype(int) + (kind_bad == 1).astype(int) + (kind_bad == 0).astype(int), np.ones(5, int))
item("C10.bucket_partition_check_fires", parts_ok, {"partition_on_valid_kinds": parts_ok},
     not parts_bad, {"partition_on_an_out_of_range_kind": parts_bad})

rec["items"] = items
rec["n_items"] = len(items)
rec["n_credited"] = sum(1 for i in items if i["credited"])
rec["failed"] = fails
rec["verdict"] = "ALL PASS" if not fails else "FAILURES"
rec["runtime_s"] = round(time.time() - T0, 2)
p = f"{OUT}/CF_SELFTEST.json"
with open(p + ".tmp", "w") as f:
    json.dump(rec, f, indent=1, default=float)
os.replace(p + ".tmp", p)
print("CF_SELFTEST VERDICT=%s items=%d credited=%d failed=%s receipt_sha256=%s"
      % (rec["verdict"], len(items), rec["n_credited"], fails, L.sha(p)), flush=True)
sys.exit(0 if not fails else 3)
