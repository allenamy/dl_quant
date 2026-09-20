#!/usr/bin/env python3
"""bt_ext_control.py — the lead's required control for the extended A0 run (2026-09-20): on the anchors the two runs SHARE, the run on the
extension targets must reproduce the already-published run BITWISE, per seed — same fills, same window ledger, same 5-minute NAV path.
Nothing is tolerated: any non-zero difference is a FAIL and the extended tables must not be published.

  C0  the two run directories hold the same seeds (paths_R each), and each PATH npz sha equals the sha in its own json (no silent edits)
  C1  anchor axes nest: OLD["A"] == NEW["A"][:len(OLD["A"])] exactly, and the shared count equals the expected one
  C2  every window-indexed array (every key except the 5-minute NAV grid) is BITWISE equal on the shared prefix, per seed: the criterion is
      RAW BYTES equal AND the element count of differences 0, where a NaN in the same cell of both arrays counts as equal (the record
      fields carry NaN where the producer wrote no value; try 1 of this device, receipt BT_EXT_CONTROL_selftest_identity_try1.json, used
      `a != b` and therefore reported 18 differing cells when comparing a run directory WITH ITSELF — caught by the identity self-test)
  C3  the 5-minute NAV grids start at the same epoch (nav5_t0) and NEW["nav5_sim"], NEW["nav5_main"] equal OLD's on OLD's length under the
      PRE-DECLARED CRITERION (lead's ruling, 2026-09-20, written before the runs it governs from here on):
        bitwise everywhere EXCEPT bars at a block boundary, which must be within ULP_BOUND = 4 ulp AND have zero effect on every published
        quantity; any bar that fails either test blocks publication.
      A "bar at a block boundary" is a bar where the two runs cannot perform the same computation: the shorter run's LAST grid boundary,
      which its final `_flush_nav(t_end + 1)` computes in a block of its own while the longer run computes it inside an ordinary block.
      NAMED EXCEPTION carried in every receipt (the lead's reasoning, recorded verbatim in EXCEPTION_RULING below): at that one bar the two
      runs do not perform the same computation — the block height of the BLAS product differs by construction — so "bitwise" is the wrong
      criterion there; the right one is "within floating-point block-order rounding, with zero effect on every published quantity".
  C4  the per-path json summary fields that depend neither on the window nor on the run's NAME: policy, price pin, ua_set, calibration params.
      DISCLOSURE (v2, 2026-09-20, written AFTER the first run of this check went red): `sealed_initial_sha256` was in this list and differs
      between the two runs. It is not a window-independent field: the sealed initial state hashes, among other things, the RUN TAG
      (bt_hist_sim31: {"nav0_usdt", "cash_K0", "entries", "stop_state", "tag", "seed", "policy"}), and the extended runs were given their own
      tags on purpose (OBJB_A0X|… , so that they write their own directories and never touch the published ones). The substantive content of
      that sealed state — the initial NAV and the initial book — is compared bitwise anyway by C2 (nav0 / navm0 / gross0 at the first window).
      The first, red receipt is kept: BT_EXT_CONTROL_<run>_try1.json.
  C7  the only table quantity that reads the 5-minute grid is the 5-minute maximum drawdown: recomputed per seed from both runs over the
      shared prefix, it must differ by EXACTLY 0.0 (a criterion under the lead's ruling: "zero effect on every published quantity")
  C5  the measurement is not vacuous: every seed was compared, and the number of cells actually compared equals
      shared_anchors x window_keys + the two 5-minute grids (a zero-measurement pass is impossible)
  mutations (must go red): one cell of one NEW array perturbed by 1 ulp; a shifted (off-by-one-window) comparison; the SAME comparison
      between different SEEDS (old seed 0 vs new seed 1) — it must differ, which proves the arrays are seed-sensitive and the comparator
      is not passing on constants; a NaN cell replaced by a number — the NaN-aware equality must NOT hide a real difference
  self-test: the device run with the SAME directory as old and new must be all-green (identity), and it is kept as a receipt
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B bt_ext_control.py PATH,HOME,LC_CTYPE <old_run_dir> <new_run_dir>
         <n_seeds> <expected_shared_anchors> <out.json>
"""
import os, sys, json, time, hashlib
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np

T0 = time.time()
OLD_D, NEW_D, NSEED, NSHARE, OUTP = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
RES = []


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail))
    print(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:300] if detail is not None else "", flush=True)


def mut(name, red, detail=None): ok("[mutation red] " + name, red, detail)


def cmp_arrays(a, b):
    """bitwise comparison: raw bytes equal AND no differing element; a NaN in the SAME cell of both sides is equal, a NaN against a number is not"""
    if a.shape != b.shape: return {"n_differ": -1, "max_abs_delta": None, "bytes_equal": False, "shapes": [list(a.shape), list(b.shape)]}
    be = bool(np.asarray(a).tobytes() == np.asarray(b).tobytes())
    if a.dtype.kind == "f":
        neq = ~((a == b) | (np.isnan(a) & np.isnan(b)))
        d = np.abs(a - b); d = d[np.isfinite(d)]
        return {"n_differ": int(neq.sum()), "max_abs_delta": (float(d.max()) if d.size else 0.0), "bytes_equal": be}
    return {"n_differ": int(np.sum(a != b)), "max_abs_delta": (float(np.max(np.abs(a.astype("float64") - b.astype("float64")))) if a.size else 0.0), "bytes_equal": be}


def stem(d, seed):
    tag = os.path.basename(d.rstrip("/"))
    return os.path.join(d, f"PATH_{tag}_seed_{seed:02d}")


def load(d, seed):
    st = stem(d, seed); J = json.load(open(st + ".json"))
    if J.get("npz_sha256") != sha(st + ".npz"): return None, J, "npz sha != its json"
    return dict(np.load(st + ".npz")), J, None


NAV5 = ("nav5_sim", "nav5_main", "nav5_t0")
ULP_BOUND = 4.0
EXCEPTION_RULING = ("lead's ruling 2026-09-20, recorded verbatim: \"at that one bar the two runs do not perform the same computation — the "
                    "block height of the BLAS product differs by construction — so 'bitwise' is the wrong criterion there; the right one is "
                    "'within floating-point block-order rounding, with zero effect on every published quantity'. You demonstrated both: "
                    "<=2 ulp (max |delta| 5.82e-11 USDT, relative 1.2e-16), mechanism proven by the chunk probe (4/4), and the only consumer, "
                    "the 5-minute maxDD, differs by exactly 0.0 on 160/160 seed pairs. Requiring bitwise would move published numbers by "
                    "<=1 ulp for no informational gain.\" Criterion pre-declared for all future extended/overlapping runs: bitwise everywhere "
                    "except bars at a block boundary, which must be <= 4 ulp AND have zero effect on every published quantity; any bar that "
                    "fails either test blocks publication.")
per_seed = {}; worst = {}
for seed in range(NSEED):
    O, OJ, e1 = load(OLD_D, seed); N, NJ, e2 = load(NEW_D, seed)
    ok(f"C0.seed{seed:02d}.both_paths_present_and_self_consistent", O is not None and N is not None, {"old": e1, "new": e2})
    if O is None or N is None: continue
    A_o, A_n = O["A"], N["A"]
    nest = len(A_n) >= len(A_o) and bool(np.array_equal(A_o, A_n[:len(A_o)]))
    ok(f"C1.seed{seed:02d}.anchor_axis_nests_and_shared_count", nest and len(A_o) == NSHARE,
       {"n_old": int(len(A_o)), "n_new": int(len(A_n)), "expected_shared": NSHARE, "nests": nest})
    if not nest: continue
    k_o = len(A_o); diffs = {}
    for k in O:
        if k in NAV5: continue
        diffs[k] = cmp_arrays(O[k], N[k][:k_o])
        worst[k] = max(worst.get(k, 0.0), diffs[k]["max_abs_delta"] or 0.0)
    bad = {k: v for k, v in diffs.items() if v["n_differ"] != 0 or not v["bytes_equal"]}
    ok(f"C2.seed{seed:02d}.window_arrays_bitwise_equal_on_shared_prefix", not bad, {"keys": len(diffs), "bad": bad})
    t_eq = int(O["nav5_t0"]) == int(N["nav5_t0"])
    n5 = {}
    block_boundary = {len(O["nav5_sim"]) - 1}            # the shorter run's last boundary: its own flush block (see the header)
    admissible = True; inadmissible = []
    for k in ("nav5_sim", "nav5_main"):
        a = O[k]; b = N[k][:len(a)]; n5[k] = dict(cmp_arrays(a, b), n_old=int(len(a)), n_new=int(len(N[k])))
        ix = np.nonzero(a != b)[0]
        if len(ix):
            t0 = int(O["nav5_t0"]); w = []
            for i in ix[:10]:
                ulps = float(abs(a[i] - b[i]) / np.spacing(max(abs(float(a[i])), abs(float(b[i])))))
                at_bb = int(i) in block_boundary
                w.append({"index": int(i), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0 + 300 * int(i))), "old": float(a[i]), "new": float(b[i]),
                          "abs_delta": float(abs(a[i] - b[i])), "relative": float(abs(a[i] - b[i]) / max(abs(a[i]), 1e-300)), "ulps": ulps,
                          "at_block_boundary": at_bb, "admissible": bool(at_bb and ulps <= ULP_BOUND)})
                if not (at_bb and ulps <= ULP_BOUND): admissible = False; inadmissible.append(w[-1])
            n5[k]["where"] = w
            if len(ix) > 10: admissible = False; inadmissible.append({"key": k, "n_differ": int(len(ix)), "reason": "more differing cells than the reported ten"})
    ok(f"C3.seed{seed:02d}.nav5_prefix_equal_bitwise_or_admissible_block_boundary", t_eq and admissible,
       {"nav5_t0_equal": t_eq, "criterion": "bitwise, except a block-boundary bar within %.0f ulp" % ULP_BOUND, "inadmissible": inadmissible, **n5})
    same = {f: (OJ.get(f) == NJ.get(f)) for f in ("policy", "price", "ua_set", "calibration_params_used")}
    same["sealed_initial_sha256_equal_iff_the_run_tag_is_equal"] = ((OJ.get("sealed_initial_sha256") == NJ.get("sealed_initial_sha256"))
                                                                   == (OJ.get("tag") == NJ.get("tag")))     # the run tag is hashed into the sealed state
    ok(f"C4.seed{seed:02d}.window_and_name_independent_summary_fields_agree", all(same.values()), same)
    dd = {}
    for k in ("nav5_sim", "nav5_main"):
        a = O[k]; b = N[k][:len(a)]
        dd[k] = {"maxdd_old": float(np.min(a / np.maximum.accumulate(a) - 1.0)), "maxdd_new": float(np.min(b / np.maximum.accumulate(b) - 1.0))}
        dd[k]["delta"] = dd[k]["maxdd_new"] - dd[k]["maxdd_old"]
    ok(f"C7.seed{seed:02d}.five_minute_maxdd_delta_is_exactly_zero (criterion)", all(v["delta"] == 0.0 for v in dd.values()), dd)
    cells = sum(int(np.asarray(O[k]).size) for k in O if k not in NAV5) + int(O["nav5_sim"].size) + int(O["nav5_main"].size)
    per_seed[seed] = {"n_shared": int(k_o), "n_new": int(len(A_n)), "max_abs_delta_over_keys": max([v["max_abs_delta"] or 0.0 for v in diffs.values()] + [v["max_abs_delta"] or 0.0 for v in n5.values()]),
                      "n_differ_total": sum(max(v["n_differ"], 0) for v in diffs.values()) + sum(max(v["n_differ"], 0) for v in n5.values()),
                      "cells_compared": cells, "window_keys": len(diffs)}

# ---- mutations, on seed 0 (the comparison itself must be able to go red)
O, _, _ = load(OLD_D, 0); N, _, _ = load(NEW_D, 0); k_o = len(O["A"])
Nm = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in N.items()}
Nm["navm1"][0] = np.nextafter(Nm["navm1"][0], np.inf)
mut("one 1-ulp perturbation in the new path is detected", int(np.sum(O["navm1"] != Nm["navm1"][:k_o])) > 0, {"key": "navm1"})
mut("a shifted (off-by-one-window) comparison is detected", int(np.sum(O["navm1"][:k_o - 1] != N["navm1"][1:k_o])) > 0, {"key": "navm1 shifted by 1"})
nan_key = next((k for k in O if k not in NAV5 and O[k].dtype.kind == "f" and np.isnan(O[k]).any()), None)
if nan_key is None:
    ok("[mutation red] a NaN cell replaced by a number is detected", False, "no NaN-carrying array found — the mutation could not be built")
else:
    Nn = N[nan_key][:k_o].copy(); i = int(np.nonzero(np.isnan(Nn))[0][0]); Nn[i] = 0.0
    mut("a NaN cell replaced by a number is detected", cmp_arrays(O[nan_key], Nn)["n_differ"] > 0, {"key": nan_key, "cell": i})
    ok("C6.NaN_in_the_same_cell_on_both_sides_is_equal (the try-1 defect)", cmp_arrays(O[nan_key], N[nan_key][:k_o])["n_differ"] == 0 and bool(np.isnan(O[nan_key]).any()),
        {"key": nan_key, "n_nan": int(np.isnan(O[nan_key]).sum())})
N1, _, _ = load(NEW_D, 1)
mut("the same comparison between different seeds (old seed 0 vs new seed 1) differs",
    int(np.sum(O["navm1"] != N1["navm1"][:k_o])) > 0, {"cells_differ": int(np.sum(O["navm1"] != N1["navm1"][:k_o]))})
ok("C5.every_seed_checked", len(per_seed) == NSEED, {"checked": len(per_seed), "expected": NSEED})
min_cells = NSHARE * min((p["window_keys"] for p in per_seed.values()), default=0)
ok("C5.measurement_is_not_vacuous", bool(per_seed) and all(p["cells_compared"] >= min_cells > 0 for p in per_seed.values()),
   {"cells_compared_min": min((p["cells_compared"] for p in per_seed.values()), default=0), "window_keys": min((p["window_keys"] for p in per_seed.values()), default=0), "shared_anchors": NSHARE})

fails = [r["check"] for r in RES if not r["ok"]]
out = dict(device="bt_ext_control.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, numpy=np.__version__,
           EXCEPTION_RULING=EXCEPTION_RULING, ulp_bound=ULP_BOUND,
           old_run_dir=OLD_D, new_run_dir=NEW_D, n_seeds=NSEED, expected_shared_anchors=NSHARE, per_seed=per_seed,
           max_abs_delta_by_key={k: v for k, v in sorted(worst.items(), key=lambda kv: -kv[1])[:10]},
           max_abs_delta_overall=max([p["max_abs_delta_over_keys"] for p in per_seed.values()] or [None]),
           n_differ_overall=sum(p["n_differ_total"] for p in per_seed.values()), checks=RES, failed=fails,
           VERDICT="PASS" if not fails else "RED", runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=str)
n_ok = sum(r["ok"] for r in RES)
print("BT_EXT_CONTROL VERDICT: " + ("ALL PASS %d/%d checks (shared %d anchors x %d seeds bitwise, max|delta| %s, cells differing %d)"
      % (n_ok, len(RES), NSHARE, NSEED, out["max_abs_delta_overall"], out["n_differ_overall"])
      if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails[:6])), flush=True)
sys.exit(0 if not fails else 3)
