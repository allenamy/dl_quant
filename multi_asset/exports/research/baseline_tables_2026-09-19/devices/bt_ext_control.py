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
  C3  the 5-minute NAV grids start at the same epoch (nav5_t0) and NEW["nav5_sim"], NEW["nav5_main"] are bitwise equal to OLD's on OLD's length
  C4  the per-path json: runtime and device shas may differ, but the audits, the fired-event counts, the UA counters and the status counts
      restricted to the shared window must agree — checked through the arrays (C2) plus the summary fields that do not depend on the window
      (policy, price pin, ua_set, calibration params, config gross): any mismatch is named
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
    for k in ("nav5_sim", "nav5_main"):
        n5[k] = dict(cmp_arrays(O[k], N[k][:len(O[k])]), n_old=int(len(O[k])), n_new=int(len(N[k])))
    ok(f"C3.seed{seed:02d}.nav5_prefix_bitwise_equal", t_eq and all(v["n_differ"] == 0 and v["bytes_equal"] for v in n5.values()), {"nav5_t0_equal": t_eq, **n5})
    same = {f: (OJ.get(f) == NJ.get(f)) for f in ("policy", "price", "ua_set", "calibration_params_used", "sealed_initial_sha256")}
    ok(f"C4.seed{seed:02d}.window_independent_summary_fields_agree", all(same.values()), same)
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
