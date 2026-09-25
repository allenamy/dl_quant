#!/usr/bin/env python3
"""dlarch_leg_readout.py — the leg-layer readout for docs/PREREG_dlarch_T3_leg_gate_2026-09-25.md.

Takes an arm's F10_OOF.npz, runs the PRODUCTION combo path on it (continuous_combo.evolve +
combo_target.step, imported UNCHANGED -- S3 already proved that harness reproduces the archived book
array-for-array), and reports the pre-registered leg-layer quantity:

    L4fc = u(fc)/|fc|_1 * 1e4      bps per anchor per unit gross, y4s caliber

per segment (2023H2 / 2024 / 2025 / pre2026 + 2026 reported separately), per seed, plus:
  * Delta = L4fc(T3) - L4fc(T0), same seed, same folds, same caliber  (the pre-registered measurand);
  * zero control, SCHEME A (population-preserving, lead's ruling): permute y only among the positions
    where y is finite, so the finite-y mask is invariant; gate |mean| <= 3*se, and the population
    invariance count must be exactly 0;
  * random-rank control: replace the F10 scores by within-anchor random ranks (3 seeds) -> L4fc ~ 0;
  * sd_leg_L4fc_across_seeds -- reported, and explicitly NOT sigma_F10 (different layer, unit, caliber);
  * per-year cross-sectional Spearman between this arm's F10 scores and the IN-SERVICE NC s42 scores
    (lead 2026-09-25: a family member's distance from the in-service model is a must-report fact);
  * the leg->book projection table recomputed with the MEASURED Delta.

SELFTEST (run it before trusting any new number): pass `SELFTEST` instead of the arm list. The device then
runs its own pipeline on the IN-SERVICE NC s42 F10 scores and asserts that L4fc(pre2026) reproduces the
already-published ladder value +0.9015 (docs/RESULT_dl_layer_ladder_2026-09-24.md L4fc, s42). A new readout
that cannot reproduce a known number is not yet a readout -- 受据 imported_denominator_has_no_closure_assertion.

READ-ONLY inputs; all writes under /workspace. No GPU.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_leg_readout.py \
         PATH,HOME,LC_CTYPE <outdir> <arm>:<seed>[,<arm>:<seed>...]
"""
import os, sys, json, time, hashlib, calendar

import numpy as np

W = "/dev/shm/news2_2026-09-23"
T3ROOT = "/workspace/dlarch_2026-09-24/T3"
LAB = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
LAB_SHA = "ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62"
MASK_PATH = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"
INSERVICE = f"{W}/work/f10_s42/F10_OOF.npz"          # the deployed NC s42 F10 scores
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"),
       "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"),
       "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"),
       "2026_reported_not_gated": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z")}
MAIN = "pre2026"
NULL_DRAWS = 20
K_SE = 3.0                  # lead's gate form
RNG = 20260925
# projection coefficients, all taken from the ladder receipt (see prereg revision 2 R2.2)
PROJ = {"t_fc_to_raw": 0.4797 / 0.9015, "t_paper_to_real": 0.5416 / 0.8175, "anchors_per_day": 6.0, "gm": 2.0}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def anchor_value(row, yrow):
    """THE R25-02 rule, in one place. Returns (value_in_bps or None, unknown_mask).

    A non-zero weight whose label is not finite is UNKNOWN: dropped from the numerator AND from the
    gross denominator, never zero-filled. Extracted as a function so the synthetic positive control
    calls the SAME code the readout calls -- a control that re-implements the rule proves only that two
    of my implementations agree.
    """
    unk = (row != 0) & ~np.isfinite(yrow)
    if unk.any():
        row = row.copy()
        row[unk] = 0.0
    g = float(np.abs(row).sum())
    if g <= 1e-9:
        return None, unk
    return 1e4 * float((row * np.nan_to_num(yrow)).sum()) / g, unk


def selftest_r25_02():
    """The reviewer's synthetic case (lead's control (i)): book [.5, -.5] against labels [.01, NaN].
    The -.5 leg is held and unlabelled, so it must be reported UNKNOWN, and the anchor's value must come
    from the .5 leg alone -- gross .5, not 1.0. The old code returned 1e4*(.5*.01 + -.5*0)/1.0 = +50.0,
    a fabricated 'this position returned zero'. Correct answer: +100.0 with one UNKNOWN cell."""
    row = np.array([0.5, -0.5]); yrow = np.array([0.01, np.nan])
    v, unk = anchor_value(row, yrow)
    assert unk.tolist() == [False, True], f"UNKNOWN mask wrong: {unk.tolist()}"
    assert v is not None and abs(v - 100.0) < 1e-9, f"value should be +100.0 (gross .5), got {v}"
    old = 1e4 * float((row * np.nan_to_num(yrow)).sum()) / float(np.abs(row).sum())
    assert abs(old - 50.0) < 1e-9, f"the pre-fix arithmetic should give +50.0, got {old}"
    # and a book that is ENTIRELY unknown must yield no reading rather than 0.0
    v2, unk2 = anchor_value(np.array([0.5, -0.5]), np.array([np.nan, np.nan]))
    assert v2 is None and unk2.all(), f"all-unknown book must give None, got {v2}"
    return {"synthetic_book": [0.5, -0.5], "synthetic_labels": [0.01, None],
            "unknown_mask": unk.tolist(), "value_after_fix_bps": v, "value_before_fix_bps": old,
            "all_unknown_book_returns": None, "PASS": True,
            "why": ("the pre-fix path reported +50.0 by treating an unlabelled HELD leg as a zero-return "
                    "holding; after the fix that leg is UNKNOWN, excluded from numerator and gross, and "
                    "the anchor reads +100.0 from the labelled leg alone")}

def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def log(*a): print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def stats1(v):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if not len(v): return {"NO_MEASUREMENT": "0 finite anchors"}
    se = float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else float("nan")
    return {"n": int(len(v)), "mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else None,
            "se": se, "t": float(v.mean() / se) if se and np.isfinite(se) and se > 0 else None,
            "median": float(np.median(v))}


def main():
    assert not sorted(set(os.environ) - set(sys.argv[1].split(","))), "env outside whitelist"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    selftest = sys.argv[3].strip().upper() == "SELFTEST"
    spec = [] if selftest else [x.split(":") for x in sys.argv[3].split(",")]
    sys.path.insert(0, f"{W}/devices")
    from continuous_combo import evolve
    from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
    import combo_target
    from scipy.stats import rankdata, spearmanr

    assert sha(f"{W}/vendor_live/fea171/combo_stage.py") == combo_target.EXPECTED
    assert sha(UNIVERSE_PATH) == UNIVERSE_SHA
    assert sha(LAB) == LAB_SHA
    rec = {"device": "dlarch_leg_readout.py", "self_sha256": sha(os.path.abspath(__file__)),
           "prereg": {"path": "docs/PREREG_dlarch_T3_leg_gate_2026-09-25.md"},
           "caliber": {"label": "y4s; LEG layer; NOT the v4 RAW accounting caliber (KB-05)",
                       "unit": "bps per anchor per unit gross"},
           "projection_note": "the paper->realised coefficient crosses a caliber boundary; order of magnitude only",
           "utc_start": iso(time.time()), "inputs": {}, "arms": {}, "controls": {}}

    F = np.load(f"{W}/work/NEWS_FEATURES.npz"); leg = np.load(f"{W}/work/legs.npz")
    lab = np.load(LAB, allow_pickle=True)
    fsha = sha(f"{W}/work/NEWS_FEATURES.npz"); lsha = sha(f"{W}/work/legs.npz")
    assert json.load(open(f"{W}/receipts/P2B_FEATURES.json"))["sha256"] == fsha
    assert json.load(open(f"{W}/receipts/P3_LEGS.json"))["sha256"] == lsha
    rec["inputs"].update({f"{W}/work/NEWS_FEATURES.npz": fsha, f"{W}/work/legs.npz": lsha, LAB: LAB_SHA})
    a = F["anchors"].astype(np.int64); syms = F["symbols"]
    off = F["off"]; mm = F["m"].astype(np.int64)
    members = [mm[off[i]:off[i + 1]] for i in range(len(a))]
    ya = lab["E_ts"].astype(np.int64); Y = lab["y4s"]
    iy = np.searchsorted(ya, a); lab_ok = (iy < len(ya)) & (ya[np.minimum(iy, len(ya) - 1)] == a)
    params = json.loads(open(f"{W}/inputs/bundle_config.json").read())["params"]
    mk = np.load(MASK_PATH); crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
    cand = mk["mask"] & crypto[None, :]
    universe = np.load(UNIVERSE_PATH)
    use = (a >= 1672531200) & (a <= universe["ts"][-1]); au = a[use]
    book_legal = align_universe(au, syms, universe) & cand[use]
    ci = np.searchsorted(a, au); assert np.all(a[ci] == au)
    # R25-02 control (ii), lead: report the candidate DENOMINATOR next to the realisation. This is an
    # UPPER bound -- cells the book MAY hold (legal) whose label is NaN -- so a realised count of 0 is
    # legitimate and is NOT evidence that the detector is broken. That job belongs to selftest_r25_02().
    _cand_cells = 0; _cand_anchors = 0
    for _j in range(len(au)):
        _i = ci[_j]
        if not lab_ok[_i]: continue
        _h = int((book_legal[_j] & ~np.isfinite(Y[iy[_i]])).sum())
        if _h: _cand_cells += _h; _cand_anchors += 1
    CAND = {"cells": _cand_cells, "anchors": _cand_anchors}
    KZu = leg["KZ"][use].astype(np.float64); ZFDu = leg["ZFD"][use].astype(np.float64)
    WLu = leg["WL"][use].astype(np.float64); RN8u = leg["RN8"][use].astype(np.float64)
    QVu = leg["QV"][use].astype(np.float64); RDY = leg["ready"][use]
    mem_u = [members[i] for i in np.flatnonzero(use)]
    INS = np.load(INSERVICE)["P"]; rec["inputs"][INSERVICE] = sha(INSERVICE)
    masks = {s: (au >= ts(lo)) & (au <= ts(hi)) for s, (lo, hi) in SEG.items()}

    UNK = {"pairs": set(), "notional": 0.0, "by_name": set()}

    def book_series(bk, rng_mode=None, rng=None):
        """u(book)/|book|_1*1e4 per anchor, for ANY book array (fc -> L4fc, raw -> L5raw).
        rng_mode 'A' permutes y ONLY among the finite positions, so the population is invariant.

        R25-02 (independent review 7cbe907ba): a NON-ZERO position whose label is missing used to go
        through nan_to_num, i.e. it was recorded as a held name that returned exactly zero. That is a
        fabricated observation. Such a cell is now UNKNOWN: it is removed from the numerator AND from
        the gross denominator (lead: not folded into the denominator), and counted. The pattern is
        copied from the TRAINING layer, which already refuses this case outright
        (dlarch_train_f10.py:289/293 raises 'unknown held return: loss refused').
        nan_to_num is still applied afterwards, but only where the weight is now exactly 0, so a NaN
        label on an unheld name legitimately contributes nothing."""
        vals = np.full(len(au), np.nan); pop_mismatch = 0
        for j in range(len(au)):
            i = ci[j]
            if not lab_ok[i]: continue
            yrow = Y[iy[i]].astype(np.float64)
            base_ok = np.isfinite(yrow)
            if rng_mode == "A":
                v = yrow[base_ok].copy(); rng.shuffle(v); yrow = yrow.copy(); yrow[base_ok] = v
                if not np.array_equal(np.isfinite(yrow), base_ok): pop_mismatch += 1
            v, unk = anchor_value(bk[j], yrow)
            if unk.any():
                # UNIQUE (anchor, name) pairs: book_series is called once per arm, and counting cell
                # VISITS would multiply the same cell by the number of arms and look like more evidence
                for k in np.flatnonzero(unk):
                    UNK["pairs"].add((int(au[j]), int(k)))
                    UNK["by_name"].add(str(syms[k]))
                UNK["notional"] += float(np.abs(bk[j][unk]).sum())
            if v is None: continue
            vals[j] = v
        return vals, pop_mismatch

    def unk_report(u):
        return {"unknown_cells_with_nonzero_book": len(u["pairs"]),
                "unknown_anchors": len({p[0] for p in u["pairs"]}),
                "unknown_abs_notional": u["notional"], "unknown_names": sorted(u["by_name"]),
                "candidate_denominator_legal_and_label_nan": CAND["cells"],
                "candidate_anchors": CAND["anchors"],
                "note": ("the candidate denominator is an UPPER bound (legal cells whose label is NaN); a "
                         "true count of 0 is legitimate, because the book need not hold those names. Both "
                         "numbers are reported so the reader can see the bound and the realisation. The "
                         "detector's own positive control is the synthetic case below, not this ratio.")}

    def run_evolve(P10u):
        out = evolve(anchors=au, king=KZu, f10=P10u, fund=ZFDu, seats=WLu, rn8=RN8u, members=mem_u,
                     qv=QVu, legal=book_legal, ready=RDY, params=params, publication="scaled_diagnostic")
        return out

    LADDER_L4FC_S42 = 0.9015          # docs/RESULT_dl_layer_ladder_2026-09-24.md, L4fc,  s42, pre-2026
    LADDER_L5RAW_S42 = 0.8175         # docs/RESULT_dl_layer_ladder_2026-09-24.md, L5raw, s42, pre-2026
    if selftest:
        t0 = time.monotonic(); out = run_evolve(INS[use].astype(np.float64))
        vals, _ = book_series(out["fc"]); vraw, _ = book_series(out["raw"])
        got = float(np.nanmean(vals[masks[MAIN]])); gotr = float(np.nanmean(vraw[masks[MAIN]]))
        rec["SELFTEST"] = {"source": INSERVICE,
                           "L4fc_pre2026_measured": got, "L4fc_pre2026_published": LADDER_L4FC_S42,
                           "L4fc_abs_diff": abs(got - LADDER_L4FC_S42),
                           "L5raw_pre2026_measured": gotr, "L5raw_pre2026_published": LADDER_L5RAW_S42,
                           "L5raw_abs_diff": abs(gotr - LADDER_L5RAW_S42), "tolerance": 2e-3,
                           "publish_rate_pre2026": float(out["trade_mask"][masks[MAIN]].mean()),
                           "seconds": round(time.monotonic() - t0, 1),
                           "PASS": bool(abs(got - LADDER_L4FC_S42) <= 2e-3 and abs(gotr - LADDER_L5RAW_S42) <= 2e-3)}
        rec["utc_end"] = iso(time.time())
        op = os.path.join(outdir, "LEG_READOUT_SELFTEST.json")
        tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
        print(f"LEG_READOUT_SELFTEST L4fc {got:.4f} vs {LADDER_L4FC_S42:.4f} (d={abs(got-LADDER_L4FC_S42):.2e}) | "
              f"L5raw {gotr:.4f} vs {LADDER_L5RAW_S42:.4f} (d={abs(gotr-LADDER_L5RAW_S42):.2e}) | "
              f"PASS={rec['SELFTEST']['PASS']} json={sha(op)[:16]}", flush=True)
        assert rec["SELFTEST"]["PASS"], f"selftest: L4fc {got:.6f} / L5raw {gotr:.6f} vs published {LADDER_L4FC_S42}/{LADDER_L5RAW_S42}"
        return

    fc_cache = {}; raw_cache = {}
    for arm, seed in spec:
        oof = f"{T3ROOT}/{arm}/f10_s{seed}/F10_OOF.npz"
        tr = f"{T3ROOT}/{arm}/f10_s{seed}/TRAIN_RECEIPT.json"
        if not os.path.exists(oof):
            rec["arms"][f"{arm}:{seed}"] = {"NOT_PRESENT": oof}; log("MISSING", oof); continue
        R = json.load(open(tr)); assert R["pred_sha256"] == sha(oof), "OOF sha != TRAIN_RECEIPT"
        assert R["arm"] == arm and R["seed"] == int(seed)
        rec["inputs"][oof] = sha(oof); rec["inputs"][tr] = sha(tr)
        Z = np.load(oof); assert np.array_equal(Z["E_ts"].astype(np.int64), a) and np.array_equal(Z["symbols"], syms)
        P10 = Z["P"]
        t0 = time.monotonic(); out = run_evolve(P10[use].astype(np.float64)); fc = out["fc"]
        fc_cache[(arm, seed)] = fc; raw_cache[(arm, seed)] = out['raw']
        vals, _ = book_series(fc); vraw, _ = book_series(out["raw"])
        e = {"folds": R["folds"], "status": R["status"], "oof_sha256": sha(oof), "oof_path": oof,
             "receipt_sha256": sha(tr), "evolve_seconds": round(time.monotonic() - t0, 1),
             "publish_rate_pre2026": float(out["trade_mask"][masks[MAIN]].mean()),
             "L4fc": {s: stats1(vals[masks[s]]) for s in SEG},
             "L5raw": {s: stats1(vraw[masks[s]]) for s in SEG}}
        # lead 2026-09-25: distance from the in-service model, per year
        ins = {}
        for s in SEG:
            rr = []
            for j in np.flatnonzero(masks[s] & RDY):
                i = ci[j]; m = members[i]
                p1 = P10[i][m]; p2 = INS[i][m]; ok = np.isfinite(p1) & np.isfinite(p2)
                if ok.sum() < 20: continue
                c = spearmanr(p1[ok], p2[ok]).statistic
                if np.isfinite(c): rr.append(float(c))
            ins[s] = stats1(rr)
        e["spearman_vs_inservice_NC_s42"] = ins
        e["spearman_vs_inservice_note"] = ("1.0 would mean this family member IS the in-service model; "
                                          "for arm T0 seed 42 it is expected HIGH but not 1.0 (masked WL changes training)")
        rec["arms"][f"{arm}:{seed}"] = e
        log(arm, seed, "L4fc pre2026", round(e["L4fc"][MAIN].get("mean", float("nan")), 4),
            "rho_vs_inservice", round(ins[MAIN].get("mean", float("nan")), 4))

    # ── Delta = T3 - T0, same seed ──
    deltas = {}
    for (arm, seed), fc in list(fc_cache.items()):
        if not arm.startswith("T3"): continue
        if ("T0", seed) not in fc_cache: continue
        v3, _ = book_series(fc); v0, _ = book_series(fc_cache[("T0", seed)])
        r3, _ = book_series(raw_cache[(arm, seed)]); r0, _ = book_series(raw_cache[("T0", seed)])
        deltas[f"{arm}:{seed}"] = {
            "L4fc": {s: stats1((v3 - v0)[masks[s]]) for s in SEG},
            "L5raw": {s: stats1((r3 - r0)[masks[s]]) for s in SEG},
            "gate_measurand": "L5raw" if arm.startswith(("T2", "T2T3")) else "L4fc",
            "gate_note": ("T3's gate is L4fc (frozen); T2's and the combined arm's gate is L5raw. The two "
                          "gates are on DIFFERENT objects, so 'T2 passed and T3 did not' does NOT order them.")}
        log("DELTA", arm, seed, "L4fc", round(deltas[f"{arm}:{seed}"]["L4fc"][MAIN].get("mean", float("nan")), 4),
            "L5raw", round(deltas[f"{arm}:{seed}"]["L5raw"][MAIN].get("mean", float("nan")), 4))
    rec["delta_T3_minus_T0"] = deltas

    # ── R25-02: both numbers lead asked for, side by side ──
    # (i) the synthetic positive control, which is what certifies the detector -- it calls anchor_value,
    #     the same function the readout calls, so it cannot pass by agreeing with a second implementation.
    # (ii) the realisation next to its candidate denominator. A realised 0 against a candidate 79 is a
    #     legitimate outcome (the book need not hold those names) and must not be read as a broken
    #     detector; that is precisely what (i) is for.
    rec["controls"]["r25_02_unknown_held_return"] = dict(unk_report(UNK),
                                                         synthetic_positive_control=selftest_r25_02())
    log("R25-02", json.dumps({k: v for k, v in rec["controls"]["r25_02_unknown_held_return"].items()
                              if k != "synthetic_positive_control" and k != "unknown_names"}))

    # ── controls, on the first available arm ──
    if fc_cache:
        key = sorted(fc_cache)[0]; fc = fc_cache[key]
        nulls = []; pop_bad = 0
        for b in range(NULL_DRAWS):
            v, pm_ = book_series(fc, rng_mode="A", rng=np.random.default_rng([RNG, b])); pop_bad += pm_
            nulls.append(float(np.nanmean(v[masks[MAIN]])))
        nv = np.asarray(nulls); se = float(nv.std(ddof=1) / np.sqrt(len(nv)))
        truth = float(np.nanmean(book_series(fc)[0][masks[MAIN]]))
        rec["controls"]["zero_control_schemeA"] = {
            "arm": f"{key[0]}:{key[1]}", "draws": NULL_DRAWS, "truth": truth, "mean_null": float(nv.mean()),
            "se": se, "gate_rhs_3se": K_SE * se, "abs_mean_over_se": abs(float(nv.mean())) / se if se > 0 else None,
            "abs_mean_over_abs_truth": abs(float(nv.mean())) / abs(truth) if abs(truth) > 0.05 else None,
            "population_mismatch_anchor_draws": pop_bad,
            "PASS": bool(abs(float(nv.mean())) <= K_SE * se and pop_bad == 0)}
        log("zero control", json.dumps(rec["controls"]["zero_control_schemeA"]))
        rr = []
        for k in range(3):
            g = np.random.default_rng([RNG, 900 + k])
            Pr = np.full_like(INS, np.nan)
            for j in np.flatnonzero(RDY):
                i = ci[j]; m = members[i]
                Pr[i, m] = g.permutation(len(m)) / max(len(m) - 1, 1) - .5
            v, _ = book_series(run_evolve(Pr[use].astype(np.float64))["fc"])
            rr.append(float(np.nanmean(v[masks[MAIN]])))
        rec["controls"]["random_rank_arms"] = {"seeds": 3, "L4fc_pre2026": rr, "mean": float(np.mean(rr)),
                                              "note": "a random-rank F10 must not produce the arm's L4fc"}
        log("random-rank control", rr)

    # ── sd across T0 seeds (NOT sigma_F10) + projection with the measured Delta ──
    t0s = {s: rec["arms"][f"T0:{s}"]["L4fc"][MAIN]["mean"] for (arm, s) in fc_cache if arm == "T0"
           and "mean" in rec["arms"][f"T0:{s}"]["L4fc"][MAIN]}
    if len(t0s) >= 2:
        vv = np.array(list(t0s.values()), float)
        rec["sd_leg_L4fc_across_seeds"] = {
            "seeds": sorted(t0s), "values": {k: float(v) for k, v in t0s.items()},
            "sd": float(vv.std(ddof=1)), "n": int(len(vv)),
            "IS_NOT_sigma_F10": "different layer (leg vs book), unit (bps/anchor/unit gross vs bps/day) "
                                "and caliber (y4s vs accounting). MUST NOT be substituted into the book "
                                "gate's SE floor (DECISION_RULE ... 038e8e78f revision 1 item 6)."}
    k = PROJ["t_fc_to_raw"] * PROJ["t_paper_to_real"] * PROJ["anchors_per_day"] * PROJ["gm"]
    kub = PROJ["t_fc_to_raw"] * PROJ["anchors_per_day"] * PROJ["gm"]
    rec["projection_from_measured_delta"] = {
        "coefficients": PROJ, "bps_day_per_leg_bps": {"with_weak_link": k, "upper_bound_link_set_to_1": kub},
        "per_arm": {a_: {"gate_measurand": d["gate_measurand"],
                         "delta_pre2026": d[d["gate_measurand"]][MAIN].get("mean"),
                         "projected_book_dbar_bps_day": (d[d["gate_measurand"]][MAIN]["mean"] * k) if "mean" in d[d["gate_measurand"]][MAIN] else None,
                         "projected_upper_bound": (d[d["gate_measurand"]][MAIN]["mean"] * kub) if "mean" in d[d["gate_measurand"]][MAIN] else None}
                    for a_, d in deltas.items()},
        "caveat": "projection, not a measurement; the paper->realised coefficient crosses a caliber boundary"}
    rec["utc_end"] = iso(time.time())
    op = os.path.join(outdir, "LEG_READOUT.json")
    tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
    zc = rec["controls"].get("zero_control_schemeA", {})
    print(f"LEG_READOUT arms={len([k for k in rec['arms'] if 'NOT_PRESENT' not in rec['arms'][k]])} "
          f"deltas={len(deltas)} zero_control_PASS={zc.get('PASS')} json={sha(op)[:16]}", flush=True)


if __name__ == "__main__":
    main()
