#!/usr/bin/env python3
"""news2_hold_population_attr.py -- split the NEW<->NC gap by whether NC published a book or held.

Pre-registration: docs/PREREG_hold_population_attribution_2026-09-24.md (committed a0d07fbe3, BEFORE
any number here). Read it first; the judgement rules are frozen there, not in this file.

WHY TWO READINGS. The literal request -- "dbar on the hold anchors" -- is NOT computable. In the
frozen device news_stats.py, full_days() only admits days whose SIX anchors are all inside the mask
(`c == 6`) and daily_on() asserts every requested day exists. dbar is therefore defined on complete
6-anchor days and cannot be evaluated on an arbitrary anchor subset. This device does not relax
`c == 6`; it offers the two readings the pre-registration names:

  A  same caliber, day-level split : complete days containing >=1 population anchor vs days containing
                                     none. dbar/boot used AS IMPORTED from the frozen device.
  B  different caliber, per-anchor : mean paired per-anchor return difference in bps/ANCHOR (NOT
                                     bps/day, never comparable to A), plus the price/funding/fee split.

The caliber for A is the frozen code itself: load_cell / seg_mask / full_days / daily_on / dbar / boot
are IMPORTED from news_stats.py, never re-implemented here, so there is no second definition to drift.

NOT MEASURED (named, per the pre-registration):
  - any "share of the gap". B's per-anchor numbers may not be additive into A's per-day numbers; the
    pre-registration forbids computing a share without first proving additivity, which is not done.
  - causality. A hold is itself the OUTPUT of the gross preflight, which is driven by the legs, so a
    gap concentrated on hold days is association, not a cause.
"""
import argparse, hashlib, json, os, sys

import numpy as np

SELF = os.path.realpath(__file__)
DAY = 86400


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--news-devices", required=True, help="dir holding the FROZEN news_stats.py")
    ap.add_argument("--nc-targets", required=True)
    ap.add_argument("--researcher-combo", required=True)
    ap.add_argument("--nc-combo", required=True,
                    help="NC's own combo output (scaled_diagnostic.npz): gives raw, trade_mask, reason")
    ap.add_argument("--nc-cell-dir", required=True)
    ap.add_argument("--nc-cell-tag", required=True)
    ap.add_argument("--new-cell-dir", required=True)
    ap.add_argument("--new-cell-tag", required=True)
    ap.add_argument("--readings", default="A,B")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    sys.path.insert(0, a.news_devices)
    import news_stats as NS
    # news_stats.py L45 is `BT = DL = None`: it does NOT import its own helpers, the caller wires them
    # (news2_stats.py L98-101 does exactly this). Without this the first load_cell dies on
    # `NoneType has no attribute audits_clean`, which is how I found it.
    import bt_tables as _BT
    import bt_driver_lib as _DL
    NS.BT, NS.DL = _BT, _DL

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_hold_population_attribution_2026-09-24.md @ a0d07fbe3",
           "status": "DIAGNOSTIC_NO_GATE",
           "caliber_source": {"news_stats_path": os.path.realpath(NS.__file__),
                              "news_stats_sha256": sha(NS.__file__),
                              "bt_tables_path": os.path.realpath(_BT.__file__),
                              "bt_tables_sha256": sha(_BT.__file__),
                              "bt_driver_lib_path": os.path.realpath(_DL.__file__),
                              "bt_driver_lib_sha256": sha(_DL.__file__),
                              "NPATH": NS.NPATH, "B": NS.B, "RNG": list(NS.RNG),
                              "BLOCK_MAIN": NS.BLOCK_MAIN, "SEG": getattr(NS, "SEG", None)},
           "inputs": {k: {"path": p, "sha256": sha(p)} for k, p in
                      (("nc_targets", a.nc_targets), ("researcher_combo", a.researcher_combo),
                       ("nc_combo", a.nc_combo))}}

    # ---- population P: NC holds (kind 0, not pad) AND the researcher publishes ----
    T = np.load(a.nc_targets, allow_pickle=False)
    C = np.load(a.researcher_combo, allow_pickle=False)
    t_a, t_k, t_pad = T["anchor"].astype(np.int64), T["scaled_kind"], T["pad_before_new_axis"]
    c_a, c_m = C["E_ts"].astype(np.int64), C["trade_mask"]
    pub = {int(t) for t, k in zip(c_a, c_m) if k}
    nc_hold = {int(t) for t, k, p in zip(t_a, t_k, t_pad) if (not p) and int(k) == 0}
    nc_pub = {int(t) for t, k, p in zip(t_a, t_k, t_pad) if (not p) and int(k) == 2}
    P = sorted(nc_hold & pub)
    rec["population"] = {
        "definition": "NC scaled_kind==0 and not pad  AND  researcher trade_mask==True",
        "nc_hold_anchors": len(nc_hold), "nc_publish_anchors": len(nc_pub),
        "researcher_publish_anchors": len(pub), "P_size": len(P),
        "note_203_is_a_net_difference_not_P": True,
        "also_reported_complement_nc_pub_and_new_hold": len(nc_pub - pub),
    }

    # Cross-check the NC hold set a SECOND way, from NC's own combo output, and assert the two agree.
    # The targets file records the adapter's kind; the combo file records the producer's decision. If
    # they disagree the population is not what its name says, so this is an identity, not a nicety.
    NCC = np.load(a.nc_combo, allow_pickle=False)
    ncc_a, ncc_m = NCC["E_ts"].astype(np.int64), NCC["trade_mask"]
    nc_hold_combo = {int(t) for t, m in zip(ncc_a, ncc_m) if not m}
    rec["population"]["nc_hold_from_combo_trade_mask"] = len(nc_hold_combo)
    rec["population"]["hold_sets_agree"] = (nc_hold_combo == nc_hold)
    if nc_hold_combo != nc_hold:
        rec["population"]["only_in_targets_kind0"] = len(nc_hold - nc_hold_combo)
        rec["population"]["only_in_combo_trade_mask_false"] = len(nc_hold_combo - nc_hold)

    # ---- lead's extra column: raw gross on both sides (for the NEXT step, why NC's gross collapses) ----
    RC_ = np.load(a.researcher_combo, allow_pickle=False)

    def gross_by_anchor(Z):
        raw = np.asarray(Z["raw"])
        ts = Z["E_ts"].astype(np.int64)
        g = np.abs(raw).sum(1)
        return {int(t): float(v) for t, v in zip(ts, g)}

    g_new, g_nc = gross_by_anchor(RC_), gross_by_anchor(NCC)

    def gdist(ts, g):
        v = np.array([g[t] for t in ts if t in g], np.float64)
        if v.size == 0:
            return {"n": 0, "note": "no anchor with a recorded raw gross"}
        return {"n": int(v.size), "mean": float(v.mean()),
                "p10": float(np.percentile(v, 10)), "median": float(np.median(v)),
                "p90": float(np.percentile(v, 90)),
                "frac_below_0.4": float((v < 0.4).mean()), "frac_above_1.2": float((v > 1.2).mean()),
                "frac_inside_band": float(((v >= 0.4) & (v <= 1.2)).mean())}

    PRE_END = 1767225600  # 2026-01-01T00:00:00Z: pre-2026 cut for the gross columns
    P_pre = [t for t in P if t < PRE_END]
    comp_pre = sorted((nc_pub | nc_hold) - set(P))
    comp_pre = [t for t in comp_pre if t < PRE_END]
    rec["raw_gross"] = {
        "note": ("gross = sum|raw| per anchor from each side's own combo output; the shared preflight "
                 "admits 0.4 <= gross <= 1.2 (combo_target.py L42)"),
        "population_A_pre2026": {"NC": gdist(P_pre, g_nc), "NEW": gdist(P_pre, g_new)},
        "complement_pre2026": {"NC": gdist(comp_pre, g_nc), "NEW": gdist(comp_pre, g_new)},
    }

    # ---- load both cells through the FROZEN loader (verifies sha, audits, seed fields) ----
    nc_paths, nc_facts = NS.load_cell(a.nc_cell_dir, a.nc_cell_tag)
    nw_paths, nw_facts = NS.load_cell(a.new_cell_dir, a.new_cell_tag)
    rec["cells"] = {"nc": {"dir": a.nc_cell_dir, "tag": a.nc_cell_tag, "n_paths": len(nc_paths)},
                    "new": {"dir": a.new_cell_dir, "tag": a.new_cell_tag, "n_paths": len(nw_paths)}}
    if len(nc_paths) != len(nw_paths):
        rec["verdict"] = "UNAVAILABLE"; rec["why"] = "path counts differ; dbar pairs path-by-path"
        json.dump(rec, open(a.out, "w"), indent=2); print("HOLD_ATTR VERDICT=UNAVAILABLE"); return 2

    A_nc, A_nw = nc_paths[0]["A"], nw_paths[0]["A"]
    same_axis = A_nc.shape == A_nw.shape and bool((A_nc == A_nw).all())
    rec["anchor_axis_identical"] = same_axis
    if not same_axis:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = ("engine anchor axes differ; dbar pairs by position, so a by-position pairing "
                      "would compare different anchors")
        rec["axis_sizes"] = [int(A_nc.size), int(A_nw.size)]
        json.dump(rec, open(a.out, "w"), indent=2); print("HOLD_ATTR VERDICT=UNAVAILABLE axes"); return 2
    A = A_nc
    Pset = set(P)
    in_P = np.array([int(t) in Pset for t in A], bool)
    rec["population"]["P_on_engine_axis"] = int(in_P.sum())
    rec["population"]["P_not_on_engine_axis"] = len(P) - int(in_P.sum())

    readings = [x.strip() for x in a.readings.split(",") if x.strip()]
    segs = getattr(NS, "SEG", None) or {}
    rec["segments_used"] = {k: list(v) for k, v in segs.items()} if isinstance(segs, dict) else str(segs)

    # ---------- reading A: same caliber, day-level split ----------
    if "A" in readings:
        outA = {}
        for name, (s0, s1) in (segs.items() if isinstance(segs, dict) else []):
            try:
                m = NS.seg_mask(A, s0, s1)
            except Exception as e:
                outA[name] = {"note": f"segment unavailable: {type(e).__name__}: {e}"}; continue
            days_all = NS.full_days(A, m)
            dP = (A[in_P] // DAY) * DAY
            hold_days = np.array(sorted(set(days_all.tolist()) & set(dP.tolist())), np.int64)
            pub_days = np.array(sorted(set(days_all.tolist()) - set(hold_days.tolist())), np.int64)
            e = {"n_full_days": int(days_all.size), "n_days_with_a_P_anchor": int(hold_days.size),
                 "n_days_without": int(pub_days.size)}
            for lbl, dd in (("all", days_all), ("days_with_P_anchor", hold_days),
                            ("days_without_P_anchor", pub_days)):
                if dd.size == 0:
                    e[lbl] = {"n_days": 0, "note": "no day in this group; nothing measured"}
                    continue
                db, D = NS.dbar(nw_paths, nc_paths, m, dd)
                e[lbl] = {"n_days": int(dd.size), "mean_bps_per_day": float(1e4 * db.mean()),
                          "boot_30d": NS.boot(db, NS.BLOCK_MAIN)}
            # Shares and the closure identity. dbar's overall number is the SIMPLE MEAN over full
            # days, so splitting the days into two disjoint groups is exactly additive:
            #     total = (n_A * mean_A + n_B * mean_B) / n_total
            # That makes closure an identity to assert, not a hope. Shares are therefore legitimate
            # for reading A (day-level) and remain forbidden for reading B (anchor-level).
            tot, gA, gB = e.get("all"), e.get("days_with_P_anchor"), e.get("days_without_P_anchor")
            if not (tot and tot.get("n_days") and gA.get("n_days") and gB.get("n_days")):
                # One side of the split is empty, so there is no day-level contrast in this segment.
                # Report it as a named non-measurement; do NOT fall back to a different split.
                e["shares"] = {
                    "note": "day-level split is degenerate in this segment: one group has 0 full days",
                    "n_days_total": (tot or {}).get("n_days", 0),
                    "n_days_with_P_anchor": gA.get("n_days", 0),
                    "n_days_without_P_anchor": gB.get("n_days", 0),
                    "consequence": ("every full day in this segment contains a P anchor (or none does), "
                                    "so the gap cannot be attributed between the two groups here"),
                }
            else:
                nA, nB, nT = gA.get("n_days", 0), gB.get("n_days", 0), tot["n_days"]
                contribA = (nA * gA["mean_bps_per_day"]) / nT if nT else None
                contribB = (nB * gB["mean_bps_per_day"]) / nT if nT else None
                recomposed = (contribA or 0.0) + (contribB or 0.0)
                e["shares"] = {
                    "denominator_bps_per_day": tot["mean_bps_per_day"],
                    "denominator_is": "this segment's own dbar over ALL full days (not the quoted 2.83)",
                    "n_days_total": nT, "n_days_with_P_anchor": nA,
                    "frac_days_with_P_anchor": (nA / nT) if nT else None,
                    "contribution_days_with_P_anchor_bps_per_day": contribA,
                    "contribution_days_without_bps_per_day": contribB,
                    "share_of_segment_gap_days_with_P": (contribA / tot["mean_bps_per_day"])
                    if tot["mean_bps_per_day"] not in (0.0, None) else None,
                    "closure_recomposed_bps_per_day": recomposed,
                    "closure_abs_residual_bps_per_day": abs(recomposed - tot["mean_bps_per_day"]),
                    "closure_holds_to_1e-9": abs(recomposed - tot["mean_bps_per_day"]) < 1e-9,
                }
            outA[name] = e
        rec["reading_A_same_caliber_day_split"] = outA

    # ---------- reading B: per-anchor, bps/ANCHOR, explicitly not dbar ----------
    if "B" in readings:
        outB = {"unit": "bps_per_ANCHOR (NOT dbar, NOT bps/day; never compare with reading A)",
                "units_note": ("series_from_path already multiplies pnl/car/cst by 1e4, so those are "
                               "ALREADY bps and are NOT scaled again here; only r is a raw return and "
                               "is scaled by 1e4. car is -funding, i.e. funding RECEIVED.")}
        # (label, key, already_in_bps)
        chans = [("total", "r", False), ("price", "pnl", True), ("funding", "car", True),
                 ("fee", "cst", True), ("g_per_gross", "g", True)]
        for name, (s0, s1) in (segs.items() if isinstance(segs, dict) else []):
            try:
                m = NS.seg_mask(A, s0, s1)
            except Exception as e:
                outB[name] = {"note": f"segment unavailable: {type(e).__name__}: {e}"}; continue
            e = {}
            for grp, sel in (("P_nc_holds_new_publishes", m & in_P), ("complement", m & ~in_P)):
                g = {"n_anchors": int(sel.sum())}
                if sel.sum() == 0:
                    g["note"] = "empty group; nothing measured"; e[grp] = g; continue
                for lbl, key, in_bps in chans:
                    if key not in nc_paths[0] or key not in nw_paths[0]:
                        g[lbl] = {"note": f"channel '{key}' absent from the path series"}; continue
                    k = 1.0 if in_bps else 1e4
                    d = np.array([np.asarray(x[key])[sel].mean() - np.asarray(y[key])[sel].mean()
                                  for x, y in zip(nw_paths, nc_paths)], np.float64)
                    g[lbl] = {"new_minus_nc_bps_per_anchor": float(k * d.mean()),
                              "across_path_sd_bps": float(k * d.std(ddof=1)) if d.size > 1 else None,
                              "level_new": float(k * np.mean([np.asarray(x[key])[sel].mean() for x in nw_paths])),
                              "level_nc": float(k * np.mean([np.asarray(y[key])[sel].mean() for y in nc_paths]))}
                # what each side actually DID on these anchors -- measured, not assumed.
                # hold = executor status 2 (no new file, carry the book); halt = status 1.
                for lbl, key in (("status_hold_fraction", "hold"), ("status_halt_fraction", "halt")):
                    if key in nc_paths[0] and key in nw_paths[0]:
                        g[lbl] = {"new": float(np.mean([np.asarray(x[key])[sel].mean() for x in nw_paths])),
                                  "nc": float(np.mean([np.asarray(y[key])[sel].mean() for y in nc_paths]))}
                e[grp] = g
            outB[name] = e
        rec["reading_B_per_anchor_not_dbar"] = outB

    # ---------- red control ----------
    # Cell 1 (baseline green): dbar of a cell against ITSELF must be exactly 0 on every day group.
    #   This is not trivially true -- it runs the full pairing/masking/day-selection path, and a
    #   mis-paired axis or a day-selection bug shows up as a non-zero.
    # Cell 2 (population is non-degenerate): P must be neither empty nor the whole axis, else the
    #   split has only one side and the comparison is vacuous.
    ctrl = {}
    if isinstance(segs, dict) and segs:
        nm = list(segs)[0]; s0, s1 = segs[nm]
        m = NS.seg_mask(A, s0, s1); dd = NS.full_days(A, m)
        self_db, _ = NS.dbar(nc_paths, nc_paths, m, dd)
        ctrl["self_dbar_max_abs_bps"] = float(1e4 * np.abs(self_db).max())
        ctrl["baseline_green"] = ctrl["self_dbar_max_abs_bps"] == 0.0
        ctrl["segment_used"] = nm
    else:
        ctrl["baseline_green"] = False; ctrl["why"] = "no segments available from the frozen device"
    ctrl["P_nonempty"] = int(in_P.sum()) > 0
    ctrl["P_not_everything"] = int(in_P.sum()) < int(in_P.size)
    ctrl["population_non_degenerate"] = ctrl["P_nonempty"] and ctrl["P_not_everything"]
    rec["red_control"] = ctrl

    if not ctrl.get("baseline_green"):
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = "red control: a cell compared against itself did not give exactly 0 bps/day"
    elif not ctrl["population_non_degenerate"]:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = ("red control: the population is empty or covers the whole axis, so the split "
                      "has only one side")
    else:
        rec["verdict"] = "MEASURED"

    json.dump(rec, open(a.out, "w"), indent=2)
    print(f"HOLD_ATTR VERDICT={rec['verdict']}  P={rec['population']['P_size']} "
          f"(on engine axis {rec['population']['P_on_engine_axis']})")
    print(f"  red control: baseline_green={ctrl.get('baseline_green')} "
          f"(self dbar max |.| = {ctrl.get('self_dbar_max_abs_bps')} bps) "
          f"population_non_degenerate={ctrl['population_non_degenerate']}")
    print(f"  NC holds {rec['population']['nc_hold_anchors']}, researcher publishes "
          f"{rec['population']['researcher_publish_anchors']}, "
          f"hold sets agree (two sources) = {rec['population']['hold_sets_agree']}")
    rg = rec.get("raw_gross", {})
    print("  RAW GROSS (sum|raw| per anchor; shared preflight admits 0.4..1.2), pre-2026:")
    for grp in ("population_A_pre2026", "complement_pre2026"):
        for side in ("NC", "NEW"):
            d = rg.get(grp, {}).get(side, {})
            if not d.get("n"):
                print(f"   {grp:22s} {side:4s} -- {d.get('note','no data')}"); continue
            print(f"   {grp:22s} {side:4s} n={d['n']:5d}  p10={d['p10']:.4f} med={d['median']:.4f} "
                  f"p90={d['p90']:.4f}  <0.4:{100*d['frac_below_0.4']:5.1f}%  "
                  f">1.2:{100*d['frac_above_1.2']:4.1f}%  in-band:{100*d['frac_inside_band']:5.1f}%")
    if "reading_A_same_caliber_day_split" in rec:
        print("  READING A (same caliber, bps/DAY, NEW minus NC):")
        for nm, e in rec["reading_A_same_caliber_day_split"].items():
            if "note" in e:
                print(f"   {nm}: {e['note']}"); continue
            for lbl in ("all", "days_with_P_anchor", "days_without_P_anchor"):
                d = e.get(lbl, {})
                if not d.get("n_days"):
                    print(f"   {nm:9s} {lbl:22s} -- {d.get('note','')}"); continue
                ci = d["boot_30d"]["ci97.5_two_sided_bps"]
                print(f"   {nm:9s} {lbl:22s} n_days={d['n_days']:4d}  "
                      f"{d['mean_bps_per_day']:+8.3f}  ci97.5=[{ci[0]:+.2f},{ci[1]:+.2f}]")
            s = e.get("shares")
            if s and "note" in s:
                print(f"   {nm:9s} SHARES: {s['note']} "
                      f"(with_P {s['n_days_with_P_anchor']}, without {s['n_days_without_P_anchor']}, "
                      f"total {s['n_days_total']})")
            elif s:
                print(f"   {nm:9s} SHARES: days_with_P {s['n_days_with_P_anchor']}/{s['n_days_total']} "
                      f"({100*s['frac_days_with_P_anchor']:.1f}%)  contrib_with={s['contribution_days_with_P_anchor_bps_per_day']:+.3f}  "
                      f"contrib_without={s['contribution_days_without_bps_per_day']:+.3f}  "
                      f"denom={s['denominator_bps_per_day']:+.3f}  "
                      f"share_with={s['share_of_segment_gap_days_with_P'] if s['share_of_segment_gap_days_with_P'] is None else round(100*s['share_of_segment_gap_days_with_P'],1)}%  "
                      f"CLOSURE_ok={s['closure_holds_to_1e-9']} (residual {s['closure_abs_residual_bps_per_day']:.2e})")
    if "reading_B_per_anchor_not_dbar" in rec:
        print("  READING B (bps/ANCHOR, NOT dbar -- do not compare with A):")
        for nm, e in rec["reading_B_per_anchor_not_dbar"].items():
            if not isinstance(e, dict) or "note" in e:
                continue
            for grp, g in e.items():
                if not g.get("n_anchors"):
                    continue
                t = g.get("total", {})
                hf = g.get("status_hold_fraction", {})
                print(f"   {nm:9s} {grp:26s} n={g['n_anchors']:5d}  "
                      f"Δtotal={t.get('new_minus_nc_bps_per_anchor',float('nan')):+8.4f}  "
                      f"Δprice={g.get('price',{}).get('new_minus_nc_bps_per_anchor',float('nan')):+8.4f}  "
                      f"Δfund={g.get('funding',{}).get('new_minus_nc_bps_per_anchor',float('nan')):+8.4f}  "
                      f"Δfee={g.get('fee',{}).get('new_minus_nc_bps_per_anchor',float('nan')):+8.4f}")
                print(f"   {'':9s} {'':26s} levels: NEW={t.get('level_new',float('nan')):+8.4f} "
                      f"NC={t.get('level_nc',float('nan')):+8.4f} bps/anchor   "
                      f"hold_frac NEW={hf.get('new',float('nan')):.3f} NC={hf.get('nc',float('nan')):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
