#!/usr/bin/env python3
"""dlarch_null_gate_schemeA.py — AMENDMENT 2 (docs/AMENDMENT_2_dlarch_null_population_preserving_2026-09-24.md).

lead ruled: a null control's randomisation must NOT change the population of the statistic. It may only
permute the pairing WITHIN the population where the statistic is defined ("scheme A"). The gate form
|mean_null| <= 3*se stays as it was; the gate was right, the null hypothesis construction was wrong.
Neither the gate form, B=200, the factor 3, nor the scheme-A contract was chosen by dlarch.

What changes vs dlarch_null_gate_b200.py (scheme B):
  * L2 leg cells: permute y ONLY among positions where y is finite, so `okl` (and hence the de-meaning
    population and the gross g) is invariant across draws. Scheme B shuffled the whole member vector,
    moving the NaNs and therefore the population.
  * L1 IC cells: UNCHANGED — news2_diag1_score_ic.ic_series already computes the mask before shuffling
    and permutes only inside it, i.e. it was already scheme A. The 20 IC cells must therefore come out
    BITWISE IDENTICAL to the scheme-B run; that identity is asserted, and at least one LEG cell must
    differ. Together those two exclude "switch not wired" and "switch wired to the wrong half".

Also reports, per lead: |mean_null| / |truth| (report-only, never a gate; flagged n/a when |truth| ~ 0),
and the population-invariance counts for BOTH schemes side by side (scheme B on a 5-draw demonstration,
not a 200-draw rerun — labelled as such).

The original verdict VOID_NULL_CONTROL_FAILED and the scheme-B verdict NULL_GATE PASS both STAND.

READ-ONLY. No GPU, no venue calls, no writes under /dev/shm.

usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_null_gate_schemeA.py \
         PATH,HOME,LC_CTYPE <outdir> <nullgate_b200.json> [B]
"""
import os, sys, json, time, hashlib, calendar

import numpy as np

W = "/dev/shm/news2_2026-09-23"
LAB = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
LAB_SHA = "ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62"
LADDER = "/workspace/dlarch_2026-09-24/news2_layer_ladder.py"
LADDER_SHA = "9eec18a078917ccb143367ecf7339e5ce51d60c9e1fe94e93e8bd101da241da5"
B_DEFAULT = 200          # lead
K_SE = 3.0               # lead
S1_DRAWS = 20            # prereg S1 §3
DEMO_B_DRAWS = 5         # scheme-B population-mismatch demonstration only
RNG_BASE = 20260924
TRUTH_NEAR_ZERO = 0.05   # |truth| below this bps/IC-unit -> the |mean|/|truth| column is printed n/a
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"),
       "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"),
       "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")}
LEGNAMES = ("king", "rev24", "fund", "f10_s42", "f10_s2027")
ICNAMES = ("king", "f10_s42", "f10_s2027", "fund_z", "rev24_z")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def log(*a): print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def leg_return_pop(z, y, rng=None, scheme="A"):
    """Leg return + the POPULATION MASK used. scheme 'A' permutes only inside the finite-y positions
    (population invariant); scheme 'B' permutes the whole vector (the NaNs move, so the population SET
    moves) — kept only to demonstrate the difference. Arithmetic otherwise verbatim news_legs.py L51-57.

    E-0924-DLARCH-D: the population must be compared as a SET, not as a count. A permutation preserves
    the multiset of values, hence the NUMBER of finite entries, BY CONSTRUCTION — counting them can never
    detect a population change, in either scheme. The first version of this device counted, and its own
    load-bearing assertion ("scheme B must show some population change") fired and stopped the run.
    """
    yy = np.asarray(y, float)
    if scheme == "B":
        if rng is not None:
            yy = yy.copy(); rng.shuffle(yy)
        okl = np.isfinite(yy)
    else:
        okl = np.isfinite(yy)                       # population fixed BEFORE any randomisation
        if rng is not None:
            v = yy[okl].copy(); rng.shuffle(v)
            yy = yy.copy(); yy[okl] = v
    zz = np.where(okl, np.nan_to_num(np.asarray(z, float)), 0.0)
    zz = zz - (zz[okl].mean() if okl.sum() else 0.0)
    g = float(np.abs(zz).sum())
    v = float((zz / g * np.nan_to_num(yy, nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0
    return v, okl


def main():
    assert not sorted(set(os.environ) - set(sys.argv[1].split(","))), "env outside whitelist"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    bpath = sys.argv[3]
    B = int(sys.argv[4]) if len(sys.argv) > 4 else B_DEFAULT
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[k] = "2"
    sys.path.insert(0, f"{W}/devices"); sys.path.insert(0, os.path.dirname(LADDER))
    assert sha(LADDER) == LADDER_SHA, "ladder device sha drifted"
    from news2_diag1_score_ic import ic_series
    from scipy.stats import rankdata

    prev = json.load(open(bpath))
    assert prev["VERDICT"] == "NULL_GATE PASS" and prev["amendment"]["B"] == B, "scheme-B receipt mismatch"

    rec = {"device": "dlarch_null_gate_schemeA.py", "self_sha256": sha(os.path.abspath(__file__)),
           "amendment": {"path": "docs/AMENDMENT_2_dlarch_null_population_preserving_2026-09-24.md",
                         "contract_author": "lead", "scheme": "A (population-preserving)", "B": B, "k_se": K_SE},
           "prior_verdicts_unchanged": {"original_N1": "VOID_NULL_CONTROL_FAILED (a0eb1a9f)",
                                        "schemeB_N1prime": f"NULL_GATE PASS ({sha(bpath)[:16]})"},
           "schemeB_receipt": {"path": bpath, "sha256": sha(bpath)},
           "rng_rule": "np.random.default_rng([20260924, b]); S1 uses [20260924, 1, b]",
           "utc_start": iso(time.time()), "cells": {}, "S1": {}, "inputs": {}}

    log("hashing inputs")
    fpath = f"{W}/work/NEWS_FEATURES.npz"; lpath = f"{W}/work/legs.npz"; kpath = f"{W}/work/king/KING_OOF.npz"
    fsha = sha(fpath); lsha = sha(lpath)
    assert json.load(open(f"{W}/receipts/P2B_FEATURES.json"))["sha256"] == fsha
    assert json.load(open(f"{W}/receipts/P3_LEGS.json"))["sha256"] == lsha
    assert sha(LAB) == LAB_SHA
    rec["inputs"].update({fpath: fsha, lpath: lsha, LAB: LAB_SHA, kpath: sha(kpath)})

    F = np.load(fpath); leg = np.load(lpath); K = np.load(kpath); lab = np.load(LAB, allow_pickle=True)
    a = F["anchors"].astype(np.int64); syms = F["symbols"]
    ya = lab["E_ts"].astype(np.int64); Y = lab["y4s"]
    assert np.array_equal(lab["symbols"], syms)
    off = F["off"]; mm = F["m"].astype(np.int64)
    members = [mm[off[i]:off[i + 1]] for i in range(len(a))]
    ready = leg["ready"]
    iy = np.searchsorted(ya, a); lab_ok = (iy < len(ya)) & (ya[np.minimum(iy, len(ya) - 1)] == a)
    SCORES = {"king": K["P"], "fund_z": leg["ZFD"], "rev24_z": leg["Z24"]}
    LEG_Z = {"king": leg["KZ"], "rev24": leg["Z24"], "fund": leg["ZFD"]}
    f10P = {}
    for sd in (42, 2027):
        p = f"{W}/work/f10_s{sd}/F10_OOF.npz"
        assert json.load(open(f"{W}/work/f10_s{sd}/TRAIN_RECEIPT.json"))["pred_sha256"] == sha(p)
        rec["inputs"][p] = sha(p); f10P[sd] = np.load(p)["P"]; SCORES[f"f10_s{sd}"] = f10P[sd]

    masks = {s: (a >= ts(lo)) & (a <= ts(hi)) for s, (lo, hi) in SEG.items()}
    rows = {s: np.flatnonzero(masks[s] & ready & lab_ok) for s in SEG}
    all_rows = np.unique(np.concatenate([rows[s] for s in SEG]))
    zf_cache = {}
    for i in all_rows:
        m = members[i]
        for sd in (42, 2027):
            p = f10P[sd][i][m]; ok = np.isfinite(p); z = np.full(len(m), np.nan)
            if ok.sum(): z[ok] = rankdata(p[ok]) / max(ok.sum() - 1, 1) - .5
            zf_cache[(i, sd)] = z
    log("caches built; anchors per segment", {s: int(len(rows[s])) for s in SEG})

    def zvec(name, i):
        if name.startswith("f10_s"): return zf_cache[(i, int(name.split("_s")[1]))]
        return LEG_Z[name][i][members[i]]

    def leg_cell(name, rws, rng=None, scheme="A"):
        """-> (window mean, #anchors whose population SET differs from unpermuted, #member cells with non-finite y)"""
        vals = []; mism = 0; nanc = 0
        for i in rws:
            m = members[i]; y = Y[iy[i]][m]
            base_okl = np.isfinite(y)
            nanc += int((~base_okl).sum())
            v, okl = leg_return_pop(zvec(name, i), y, rng=rng, scheme=scheme)
            vals.append(v)
            if not np.array_equal(okl, base_okl): mism += 1
        return float(np.mean(vals)), mism, nanc

    def ic_cell(name, rws, rng=None):
        ics, _, _ = ic_series(SCORES[name], Y, rws, iy[rws], rng=rng)
        return float(ics.mean()) if len(ics) else float("nan")

    truth = {}
    for s in SEG:
        for n in LEGNAMES: truth[("LEG", s, n)] = leg_cell(n, rows[s])[0]
        for n in ICNAMES: truth[("IC", s, n)] = ic_cell(n, rows[s])
    log("unpermuted truth computed")

    # ── scheme-B population-mismatch DEMONSTRATION (5 draws, not a 200-draw rerun) ──
    demo = {}
    for s in ("pre2026",):
        for n in LEGNAMES:
            mA = mB = 0; nanc = None
            for b in range(DEMO_B_DRAWS):
                _, ma, nanc = leg_cell(n, rows[s], rng=np.random.default_rng([RNG_BASE, b]), scheme="A")
                _, mb, _ = leg_cell(n, rows[s], rng=np.random.default_rng([RNG_BASE, b]), scheme="B")
                mA += ma; mB += mb
            demo[f"LEG|{s}|{n}"] = {"schemeA_anchor_population_mismatches": mA,
                                    "schemeB_anchor_population_mismatches": mB,
                                    "member_cells_with_nonfinite_label": nanc,
                                    "draws": DEMO_B_DRAWS, "anchors": int(len(rows[s]))}
            log("popdemo", n, "A", mA, "B", mB, "nonfinite_label_cells", nanc)
    rec["population_invariance_demonstration"] = {
        "note": "counts over draws x anchors of anchors whose finite-label population differs from unpermuted; "
                "scheme B is shown on a 5-draw demonstration, NOT the archived 200-draw run",
        "cells": demo}
    assert all(v["schemeA_anchor_population_mismatches"] == 0 for v in demo.values()), "scheme A did not preserve population"
    nf = max(v["member_cells_with_nonfinite_label"] for v in demo.values())
    anyB = any(v["schemeB_anchor_population_mismatches"] > 0 for v in demo.values())
    rec["population_invariance_demonstration"]["nonfinite_label_member_cells_in_window"] = nf
    if nf == 0:
        # There is nothing for scheme B to move: every member of every judged anchor has a finite label.
        # Then scheme B == scheme A for the LEG cells, and the population defect NEVER EXISTED there.
        rec["population_invariance_demonstration"]["FINDING"] = (
            "no non-finite labels among members on the judged anchors ⇒ scheme B could not move the LEG "
            "population; the population defect found in S1 does NOT apply to the LEG cells")
        log("FINDING: 0 non-finite member labels in window ⇒ scheme B == scheme A for LEG cells")
    else:
        assert anyB, "non-finite labels exist but scheme B moved no population — detector suspect"

    # ── the 200-draw scheme-A run ──
    draws = {k: [] for k in truth}
    popmis = {k: 0 for k in truth if k[0] == "LEG"}
    t0 = time.monotonic()
    for b in range(B):
        for s in SEG:
            for n in LEGNAMES:
                v, mism, _ = leg_cell(n, rows[s], rng=np.random.default_rng([RNG_BASE, b]), scheme="A")
                draws[("LEG", s, n)].append(v); popmis[("LEG", s, n)] += mism
            for n in ICNAMES:
                draws[("IC", s, n)].append(ic_cell(n, rows[s], rng=np.random.default_rng([RNG_BASE, b])))
        if (b + 1) % 10 == 0:
            el = time.monotonic() - t0
            log(f"b={b+1}/{B} elapsed {el/60:.1f} min, eta {(el/(b+1)*(B-b-1))/60:.1f} min")
            open(os.path.join(outdir, "SCHEMEA.progress.json"), "w").write(json.dumps({"b_done": b + 1, "B": B}))

    fails = []; nomeas = []; ic_identical = 0; ic_total = 0; leg_changed = 0; leg_total = 0
    for (kind, s, n), v in draws.items():
        v = np.asarray(v, float)
        mean_null = float(v.mean()); sd = float(v.std(ddof=1)); se = sd / np.sqrt(len(v))
        tr = truth[(kind, s, n)]
        n_eq_truth = int(np.sum(np.abs(v - tr) <= 1e-12))
        key = f"{kind}|{s}|{n}"
        pb = prev["cells"].get(key, {})
        same_as_B = bool(pb and abs(pb["mean_null"] - mean_null) <= 1e-12 and abs(pb["sd_null"] - sd) <= 1e-12)
        cell = {"kind": kind, "segment": s, "name": n, "B": int(len(v)), "scheme": "A",
                "truth_unpermuted": tr, "mean_null": mean_null, "sd_null": sd, "se_null": se,
                "gate_rhs_3se": K_SE * se, "abs_mean_over_se": float(abs(mean_null) / se) if se > 0 else None,
                "abs_mean_over_abs_truth": (float(abs(mean_null) / abs(tr)) if abs(tr) > TRUTH_NEAR_ZERO else None),
                "abs_mean_over_abs_truth_note": None if abs(tr) > TRUTH_NEAR_ZERO else "n/a (|truth| ~ 0)",
                "PASS": bool(abs(mean_null) <= K_SE * se) if se > 0 else False,
                "N1a_distribution_nondegenerate": bool(sd > 0.0),
                "N1b_draws_equal_to_unpermuted_truth": n_eq_truth,
                "bitwise_same_as_schemeB": same_as_B,
                "schemeB_mean_null": pb.get("mean_null"), "n_anchors": int(len(rows[s]))}
        if kind == "LEG":
            cell["population_mismatch_anchor_draws"] = popmis[(kind, s, n)]
            if popmis[(kind, s, n)] != 0:
                cell["PASS"] = False; cell["NO_MEASUREMENT"] = "scheme A did not preserve the population"
                nomeas.append(key)
            leg_total += 1; leg_changed += 0 if same_as_B else 1
        else:
            ic_total += 1; ic_identical += 1 if same_as_B else 0
        if sd == 0.0 or n_eq_truth > 0:
            cell["PASS"] = False; cell["NO_MEASUREMENT"] = "permutation did not act"; nomeas.append(key)
        if not cell["PASS"]: fails.append(f"{key}: |{mean_null:+.5f}| vs 3se {K_SE*se:.5f}")
        rec["cells"][key] = cell

    rec["switch_wiring"] = {"ic_cells": ic_total, "ic_bitwise_identical_to_schemeB": ic_identical,
                            "leg_cells": leg_total, "leg_cells_changed_vs_schemeB": leg_changed,
                            "SWITCH_OK": bool(ic_identical == ic_total and leg_changed > 0)}
    assert rec["switch_wiring"]["SWITCH_OK"], f"SWITCH_MISWIRED: {rec['switch_wiring']}"

    base = rec["cells"]["LEG|pre2026|king"]
    rec["N1c_red_capability"] = {"cell": "LEG|pre2026|king", "baseline_mean_null": base["mean_null"],
                                 "baseline_3se": base["gate_rhs_3se"], "baseline_green": base["PASS"],
                                 "mutation": "identity permutation (no shuffle)",
                                 "mutated_value": truth[("LEG", "pre2026", "king")],
                                 "mutation_goes_red": bool(abs(truth[("LEG", "pre2026", "king")]) > base["gate_rhs_3se"])}
    assert rec["N1c_red_capability"]["mutation_goes_red"], "red-capability check vacuous"

    # ── S1 weight-correlation null under scheme A ──
    log("S1 scheme-A null")
    s1 = {}
    for sd in (42, 2027):
        pol = "scaled_diagnostic"
        cp = f"{W}/work/combo_s{sd}/{pol}.npz"
        assert json.load(open(f"{W}/work/combo_s{sd}/TARGET_RECEIPT.json"))["policies"][pol]["sha"] == sha(cp)
        C = np.load(cp); ca = C["E_ts"].astype(np.int64); kc = C["kc"]; fc = C["fc"]
        ci = np.searchsorted(a, ca); assert np.all(a[ci] == ca)
        sel = np.flatnonzero(masks["pre2026"][ci] & ready[ci] & lab_ok[ci])
        def wcorr(k, f):
            nz = (np.abs(k) > 1e-12) | (np.abs(f) > 1e-12)
            if nz.sum() < 20 or k[nz].std() == 0 or f[nz].std() == 0: return None, nz
            return float(np.corrcoef(k[nz], f[nz])[0, 1]), nz
        tvals = []; tpop = []
        for j in sel:
            v, p = wcorr(kc[j], fc[j])
            if v is not None: tvals.append(v); tpop.append(p)
        tmean = float(np.mean(tvals))
        nulls = []; mism = 0; n_eq = 0
        for b in range(S1_DRAWS):
            rng = np.random.default_rng([RNG_BASE, 1, b]); vals = []
            for q, j in enumerate(sel):
                f = fc[j].copy(); pos = np.flatnonzero(np.abs(f) > 1e-12)
                if len(pos) > 1: f[pos] = rng.permutation(f[pos])       # scheme A: support preserved
                v, p = wcorr(kc[j], f)
                if v is not None:
                    vals.append(v)
                    if q < len(tpop) and not np.array_equal(p, tpop[q]): mism += 1
            m = float(np.mean(vals)); nulls.append(m)
            if abs(m - tmean) <= 1e-12: n_eq += 1
        nv = np.asarray(nulls, float); se = float(nv.std(ddof=1) / np.sqrt(len(nv)))
        s1[f"s{sd}_{pol}"] = {"draws": S1_DRAWS, "truth_unpermuted": tmean, "mean_null": float(nv.mean()),
                              "sd_null": float(nv.std(ddof=1)), "se_null": se, "gate_rhs_3se": K_SE * se,
                              "abs_mean_over_se": float(abs(nv.mean()) / se) if se > 0 else None,
                              "abs_mean_over_abs_truth": float(abs(nv.mean()) / abs(tmean)),
                              "population_mismatch_anchor_draws": mism,
                              "draws_equal_to_unpermuted": n_eq,
                              "PASS": bool(abs(float(nv.mean())) <= K_SE * se and mism == 0 and n_eq == 0)}
        log("S1-A", sd, json.dumps({k: s1[f"s{sd}_{pol}"][k] for k in ("mean_null", "se_null", "abs_mean_over_se", "PASS")}))
    rec["S1"] = s1
    s1_fail = [k for k, v in s1.items() if not v["PASS"]]

    verdict = "PASS" if (not fails and not s1_fail) else "FAIL"
    rec["VERDICT"] = f"NULL_GATE_SCHEME_A {verdict}"
    rec["failing_cells"] = fails; rec["no_measurement_cells"] = nomeas; rec["S1_failing"] = s1_fail
    rec["utc_end"] = iso(time.time())
    op = os.path.join(outdir, "NULLGATE_SCHEMEA.json")
    tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
    print(f"NULLGATE_SCHEMEA VERDICT={verdict} B={B} cells={len(rec['cells'])} failing={len(fails)} "
          f"no_measurement={len(nomeas)} s1_failing={len(s1_fail)} "
          f"ic_identical={ic_identical}/{ic_total} leg_changed={leg_changed}/{leg_total} "
          f"red_pair={rec['N1c_red_capability']['baseline_green']}/{rec['N1c_red_capability']['mutation_goes_red']} "
          f"json={sha(op)[:16]}", flush=True)
    sys.exit(0 if verdict == "PASS" else 5)


if __name__ == "__main__":
    main()
