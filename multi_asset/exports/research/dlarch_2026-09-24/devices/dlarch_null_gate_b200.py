#!/usr/bin/env python3
"""dlarch_null_gate_b200.py — AMENDMENT 1 to docs/PREREG_dl_layer_ladder_2026-09-24.md (06f571a41).

The ORIGINAL N1 gate ("|mean of ONE within-anchor permutation| < 0.30 bps") was set below the
instrument's own resolution (se 0.18-0.36 bps) and is therefore impossible to pass; the original
verdict VOID_NULL_CONTROL_FAILED STANDS and is not rewritten. lead ruled the repaired gate
(docs/AMENDMENT_1_dl_layer_ladder_null_gate_2026-09-24.md): B=200 within-anchor permutations per
cell, gate = |mean_b(m_b)| <= 3 * se(mean_b), se from the permutation distribution itself.
Neither B nor the factor 3 was chosen by dlarch.

Recomputes ONLY N1'. L3/L5 identities, N4 and N5 are NOT recomputed — they are independent of N1
and already passed in receipt a0eb1a9f.

READ-ONLY. No GPU, no venue calls, no writes under /dev/shm, no writes to live trees.

usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_null_gate_b200.py \
         PATH,HOME,LC_CTYPE <outdir> [B]
"""
import os, sys, json, time, hashlib, calendar

import numpy as np

W = "/dev/shm/news2_2026-09-23"
LAB = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
LAB_SHA = "ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62"
LADDER = "/workspace/dlarch_2026-09-24/news2_layer_ladder.py"
LADDER_SHA = "9eec18a078917ccb143367ecf7339e5ce51d60c9e1fe94e93e8bd101da241da5"
B_DEFAULT = 200                       # lead's ruling
K_SE = 3.0                            # lead's ruling
RNG_BASE = 20260924
MIN_NAMES = 20                        # news2_diag1_score_ic.py
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"),
       "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"),
       "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def log(*a): print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def main():
    WLIST = set(sys.argv[1].split(","))
    extra = sorted(set(os.environ) - WLIST)
    assert not extra, f"env outside whitelist: {extra}"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    B = int(sys.argv[3]) if len(sys.argv) > 3 else B_DEFAULT
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[k] = "2"
    sys.path.insert(0, f"{W}/devices"); sys.path.insert(0, os.path.dirname(LADDER))
    assert sha(LADDER) == LADDER_SHA, "ladder device sha drifted; N1' must use its arithmetic"
    from news2_layer_ladder import leg_return                      # the L2 arithmetic, imported
    from news2_diag1_score_ic import ic_series                     # the L1 arithmetic, imported
    from scipy.stats import spearmanr

    rec = {"device": "dlarch_null_gate_b200.py", "self_sha256": sha(os.path.abspath(__file__)),
           "amendment": {"path": "docs/AMENDMENT_1_dl_layer_ladder_null_gate_2026-09-24.md",
                         "gate_author": "lead", "B": B, "k_se": K_SE,
                         "original_verdict_unchanged": "VOID_NULL_CONTROL_FAILED (receipt a0eb1a9f)"},
           "prereg": {"path": "docs/PREREG_dl_layer_ladder_2026-09-24.md", "commit": "06f571a41"},
           "imported": {LADDER: LADDER_SHA, f"{W}/devices/news2_diag1_score_ic.py": sha(f"{W}/devices/news2_diag1_score_ic.py")},
           "rng_rule": "np.random.default_rng([20260924, b]) — one independent stream per b, consumed anchor by anchor",
           "utc_start": iso(time.time()), "cells": {}, "inputs": {}}

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
    LEGZ = {"king": leg["KZ"], "rev24": leg["Z24"], "fund": leg["ZFD"]}
    f10P = {}
    for sd in (42, 2027):
        p = f"{W}/work/f10_s{sd}/F10_OOF.npz"; tr = json.load(open(f"{W}/work/f10_s{sd}/TRAIN_RECEIPT.json"))
        h = sha(p); assert tr["pred_sha256"] == h
        rec["inputs"][p] = h
        f10P[sd] = np.load(p)["P"]; SCORES[f"f10_s{sd}"] = f10P[sd]

    masks = {s: (a >= ts(lo)) & (a <= ts(hi)) for s, (lo, hi) in SEG.items()}
    rows = {s: np.flatnonzero(masks[s] & ready & lab_ok) for s in SEG}
    log("anchors per segment", {s: int(len(rows[s])) for s in SEG})

    # production-caliber F10 rank, cached once per (anchor, seed) — identical to the ladder device
    from scipy.stats import rankdata
    def f10_rank(p):
        n = len(p); ok = np.isfinite(p); z = np.full(n, np.nan)
        if ok.sum(): z[ok] = rankdata(p[ok]) / max(ok.sum() - 1, 1) - .5
        return z
    all_rows = np.unique(np.concatenate([rows[s] for s in SEG]))
    zf_cache = {}
    for i in all_rows:
        m = members[i]
        for sd in (42, 2027): zf_cache[(i, sd)] = f10_rank(f10P[sd][i][m])
    LEG_Z = dict(LEGZ)
    log("f10 rank cache built", len(zf_cache))

    # ── N1'-c red-capability control: identity permutation on king/pre2026 must go RED ──
    def leg_series(name, rws, rng=None, identity=False):
        out = []
        for i in rws:
            m = members[i]; y = Y[iy[i]][m]
            z = (zf_cache[(i, int(name.split("_s")[1]))] if name.startswith("f10_s") else LEG_Z[name][i][m])
            if identity:
                v, _ = leg_return(z, y)                      # no shuffle at all
            else:
                v, _ = leg_return(z, y, rng=rng)
            out.append(v)
        return float(np.mean(out))

    def ic_mean(name, rws, rng=None):
        ics, _, _ = ic_series(SCORES[name], Y, rws, iy[rws], rng=rng)
        return float(ics.mean()) if len(ics) else float("nan")

    LEGNAMES = ("king", "rev24", "fund", "f10_s42", "f10_s2027")
    ICNAMES = ("king", "f10_s42", "f10_s2027", "fund_z", "rev24_z")

    truth = {}
    for s in SEG:
        for n in LEGNAMES: truth[("LEG", s, n)] = leg_series(n, rows[s], identity=True)
        for n in ICNAMES: truth[("IC", s, n)] = ic_mean(n, rows[s])
    log("unpermuted truth computed")

    draws = {k: [] for k in truth}
    t0 = time.monotonic()
    for b in range(B):
        for s in SEG:
            for n in LEGNAMES:
                draws[("LEG", s, n)].append(leg_series(n, rows[s], rng=np.random.default_rng([RNG_BASE, b])))
            for n in ICNAMES:
                draws[("IC", s, n)].append(ic_mean(n, rows[s], rng=np.random.default_rng([RNG_BASE, b])))
        if (b + 1) % 10 == 0:
            el = time.monotonic() - t0
            log(f"b={b+1}/{B} elapsed {el/60:.1f} min, eta {(el/(b+1)*(B-b-1))/60:.1f} min")
            tmp = os.path.join(outdir, "NULLGATE.progress.json")
            open(tmp, "w").write(json.dumps({"b_done": b + 1, "B": B, "elapsed_s": el}))

    fails = []; nomeas = []
    for (kind, s, n), v in draws.items():
        v = np.asarray(v, float)
        mean_null = float(v.mean()); sd = float(v.std(ddof=1)); se = sd / np.sqrt(len(v))
        # N1'-a / N1'-b
        degenerate = bool(sd == 0.0)
        n_equal_truth = int(np.sum(np.abs(v - truth[(kind, s, n)]) <= 1e-12))
        cell = {"kind": kind, "segment": s, "name": n, "B": int(len(v)),
                "truth_unpermuted": truth[(kind, s, n)],
                "mean_null": mean_null, "sd_null": sd, "se_null": se,
                "gate_rhs_3se": K_SE * se, "abs_mean_over_se": float(abs(mean_null) / se) if se > 0 else None,
                "PASS": bool(abs(mean_null) <= K_SE * se) if se > 0 else False,
                "N1a_distribution_nondegenerate": not degenerate,
                "N1b_draws_equal_to_unpermuted_truth": n_equal_truth,
                "n_anchors": int(len(rows[s]))}
        if degenerate or n_equal_truth > 0:
            cell["PASS"] = False; cell["NO_MEASUREMENT"] = "permutation did not act" if degenerate else "some draws equal the unpermuted truth"
            nomeas.append(f"{kind}/{s}/{n}")
        if not cell["PASS"]: fails.append(f"{kind}/{s}/{n}: |{mean_null:+.5f}| vs 3se {K_SE*se:.5f}")
        rec["cells"][f"{kind}|{s}|{n}"] = cell

    # N1'-c red-capability pair on king/pre2026 (printed with BOTH measured values)
    base = rec["cells"]["LEG|pre2026|king"]
    mut_mean = truth[("LEG", "pre2026", "king")]                      # identity permutation = the truth itself
    rec["N1c_red_capability"] = {
        "cell": "LEG|pre2026|king",
        "baseline_mean_null": base["mean_null"], "baseline_3se": base["gate_rhs_3se"],
        "baseline_green": base["PASS"],
        "mutation": "identity permutation (no shuffle)", "mutated_value": mut_mean,
        "mutation_goes_red": bool(abs(mut_mean) > base["gate_rhs_3se"])}
    assert rec["N1c_red_capability"]["mutation_goes_red"], "red-capability check vacuous"

    verdict = "NULL_GATE PASS" if not fails else "NULL_GATE FAIL"
    rec["VERDICT"] = verdict; rec["failing_cells"] = fails; rec["no_measurement_cells"] = nomeas
    rec["utc_end"] = iso(time.time())
    op = os.path.join(outdir, "NULLGATE_B200.json")
    tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
    print(f"NULLGATE VERDICT={'PASS' if not fails else 'FAIL'} B={B} cells={len(rec['cells'])} "
          f"failing={len(fails)} no_measurement={len(nomeas)} "
          f"red_pair={rec['N1c_red_capability']['baseline_green']}/{rec['N1c_red_capability']['mutation_goes_red']} "
          f"json={sha(op)[:16]}", flush=True)
    sys.exit(0 if not fails else 5)


if __name__ == "__main__":
    main()
