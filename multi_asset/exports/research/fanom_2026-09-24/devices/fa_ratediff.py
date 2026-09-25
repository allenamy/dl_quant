"""fa_ratediff.py — lead ruling 2026-09-24: stop reporting SHARES, report (a) absolute bucket contributions and
(b) the between-bucket difference in per-anchor loss rate, with 30-day block CIs. Read-only, no engine, no GPU.

Why: the frozen 3-SE denominator rule stands, and shares whose denominator sits 1.1-1.7 SE from zero are shares of
noise. But "the loss is concentrated on high-seat anchors" has a form that needs no denominator at all: the
per-anchor loss RATE on high-seat anchors vs the rest. That is testable and is what this device reports.

Gates, both asserted before any number is produced:
  G-A  the tercile variable is arm- and variant-independent: seat_king_FRESH must be bitwise identical across every
       SER file that carries it. If it is not, the buckets are not the buckets I think they are.
  G-B  reproduce the frozen tercile edges Q33/Q67 from that variable on the pre-2026 population. This is the
       "make a new readout reproduce a known number first" detector that caught correction W-1.
       RESULT: they are NOT reproducible to 1e-9. The closest surviving population (pre-2026 AND ready, n=5495 --
       identical whether taken on the SER axis, the combo axis or the legs axis) gives Q33 off by 2.49e-06 and Q67
       off by 5.09e-07. Tried and rejected: percentile arguments 33/67 and 33.33/66.67, methods lower/higher/
       midpoint/nearest, np.quantile(1/3, 2/3) -- all are FURTHER away. So the frozen constants came from a
       population that differs from the surviving one by a few anchors, and that population is not recoverable.
       The tolerance is NOT loosened to make this pass. Instead every table is computed TWICE, once with the frozen
       edges (what every earlier device used) and once with the recomputed edges, and both are reported with the
       count of anchors that change tercile. If a conclusion differs between the two, it is not a conclusion.

Mandatory new reported item (lead: 必报项, not a gate): the cancellation ratio |total| / sum(|bucket totals|).

usage: ... fa_ratediff.py WL <out.json>
"""
import os, sys, json, time, hashlib, calendar, glob
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
R = "/dev/shm/fanom_2026-09-24/receipts"
PRE = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")
Q33, Q67 = 0.5725596881282329, 0.7810047984528542       # frozen edges, as used by fa_bread.py / fa_b8read.py
B = 10000; RNG = (20260923, 1); BLOCK = 30; DAY = 86400


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def block_ci_diff(val, days, m1, m2):
    """30-day moving-block bootstrap CI for mean(val[m1]) - mean(val[m2]); blocks are days, common resample."""
    rs = np.random.default_rng(RNG)
    ud = np.unique(days); st = np.arange(max(1, len(ud) - BLOCK + 1)); nb = int(np.ceil(len(ud) / BLOCK))
    o = []
    for _ in range(B):
        sel = np.concatenate([ud[s:s + BLOCK] for s in rs.choice(st, size=nb, replace=True)])
        k = np.isin(days, sel)
        a, b_ = val[k & m1], val[k & m2]
        if len(a) >= 5 and len(b_) >= 5:
            o.append(float(np.nanmean(a) - np.nanmean(b_)))
    o = np.array(o)
    return [float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))] if len(o) > 100 else [None, None]


def bucket_report(name, dval, anchors, seat, rec, edges):
    """absolute contributions per tercile + high-vs-rest per-anchor rate difference + cancellation ratio"""
    pre = (anchors >= ts(PRE[0])) & (anchors <= ts(PRE[1]))
    fin = np.isfinite(dval)
    pop = pre & fin
    e33, e67 = edges
    terc = np.where(seat <= e33, 0, np.where(seat <= e67, 1, 2))
    days = anchors // DAY
    rows = {}
    parts = []
    for t, lab in ((0, "seat_low"), (1, "seat_mid"), (2, "seat_high")):
        m = pop & (terc == t)
        tot = float(np.nansum(dval[m])); parts.append(tot)
        rows[lab] = {"n": int(m.sum()), "absolute_bps_total": tot,
                     "bps_per_anchor": float(np.nanmean(dval[m])) if m.any() else None}
    hi = pop & (terc == 2); rest = pop & (terc != 2)
    diff = float(np.nanmean(dval[hi]) - np.nanmean(dval[rest]))
    ci = block_ci_diff(dval, days, hi, rest)
    tot_all = float(np.nansum(dval[pop])); gross = float(sum(abs(p) for p in parts))
    rec[name] = {"tercile_edges": [float(e33), float(e67)], "population_anchors": int(pop.sum()), "window": "pre2026 (%s .. %s)" % PRE,
                 "buckets": rows,
                 "high_vs_rest_bps_per_anchor": {"difference": diff, "ci95_30day_block": ci,
                                                 "n_high": int(hi.sum()), "n_rest": int(rest.sum()),
                                                 "excludes_zero": bool(ci[0] is not None and (ci[0] > 0 or ci[1] < 0))},
                 "total_bps": tot_all,
                 "cancellation_ratio": (abs(tot_all) / gross if gross else None),
                 "note": "shares deliberately NOT reported (frozen 3-SE denominator rule, lead ruling 2026-09-24)"}
    return rec[name]


def main():
    t0 = time.time()
    rec = {"device": "fa_ratediff.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "ruling": "lead 2026-09-24: 3-SE rule stands; report absolute contributions + per-anchor rate difference",
           "frozen_tercile_edges": {"Q33": Q33, "Q67": Q67}, "gates": {}, "tables": {}, "unavailable": []}

    # ---- G-A: the tercile variable is arm- and variant-independent ----
    seats = {}
    for p in sorted(glob.glob(f"{R}/SER_*.npz")):
        z = np.load(p)
        if "seat_king_FRESH" in z.files:
            seats[os.path.basename(p)] = np.asarray(z["seat_king_FRESH"])
    assert seats, "no SER carries seat_king_FRESH"
    ref_name = sorted(seats)[0]; ref = seats[ref_name]
    ident = {k: bool(v.shape == ref.shape and v.tobytes() == ref.tobytes()) for k, v in seats.items()}
    rec["gates"]["G_A_seat_variable_identical_across_files"] = {
        "files_checked": len(seats), "reference": ref_name, "all_identical": bool(all(ident.values())),
        "per_file": ident}
    assert all(ident.values()), f"seat_king_FRESH differs across SER files: {[k for k,v in ident.items() if not v]}"

    A0 = np.load(f"{R}/SER_ORIG_FRESH_s42.npz")["anchors"].astype(np.int64)
    zz = np.load(f"{R}/{ref_name}")
    ax_ref = zz["anchors"].astype(np.int64)
    assert np.array_equal(ax_ref, A0), "seat axis != ORIG axis"
    pre = (ax_ref >= ts(PRE[0])) & (ax_ref <= ts(PRE[1]))

    # ---- G-B: reproduce the frozen tercile edges ----
    s_pre = ref[pre]; s_pre = s_pre[np.isfinite(s_pre)]
    q33, q67 = float(np.percentile(s_pre, 100 / 3)), float(np.percentile(s_pre, 200 / 3))
    t_froz = np.where(ref <= Q33, 0, np.where(ref <= Q67, 1, 2))
    t_recp = np.where(ref <= q33, 0, np.where(ref <= q67, 1, 2))
    moved = int(((t_froz != t_recp) & pre & np.isfinite(ref)).sum())
    rec["gates"]["G_B_reproduce_frozen_edges"] = {
        "Q33_frozen": Q33, "Q33_recomputed": q33, "Q33_abs_diff": abs(q33 - Q33),
        "Q67_frozen": Q67, "Q67_recomputed": q67, "Q67_abs_diff": abs(q67 - Q67),
        "n_pre2026": int(len(s_pre)), "EXACT_TO_1e-9": bool(abs(q33 - Q33) < 1e-9 and abs(q67 - Q67) < 1e-9),
        "anchors_changing_tercile": moved,
        "anchors_changing_tercile_fraction": moved / max(1, int((pre & np.isfinite(ref)).sum())),
        "resolution": ("NOT exactly reproducible; tolerance deliberately NOT loosened. Every table is reported under "
                       "BOTH edge sets so the residual's effect is measured rather than assumed."),
        "rejected_alternatives": "percentile 33/67 and 33.33/66.67; methods lower/higher/midpoint/nearest; "
                                 "np.quantile(1/3,2/3) -- all further from the frozen constants than 100/3,200/3"}
    EDGES = {"frozen": (Q33, Q67), "recomputed": (q33, q67)}

    # ---- table 1: the section-2 headline, FRESH vs NEW_S price channel ----
    for sd in ("42", "2027"):
        F = np.load(f"{R}/SER_ORIG_FRESH_s{sd}.npz"); N = np.load(f"{R}/SER_ORIG_NEWS_s{sd}.npz")
        ax = F["anchors"].astype(np.int64); assert np.array_equal(ax, N["anchors"].astype(np.int64))
        assert np.array_equal(ax, ax_ref), "ORIG axis != seat axis"
        dv = np.asarray(F["price_bps"], float) - np.asarray(N["price_bps"], float)
        for ename, ed in EDGES.items():
            bucket_report(f"SECTION2_FRESH_minus_NEWS_price_s{sd}__edges_{ename}", dv, ax, ref, rec["tables"], ed)

    # ---- table 2: every variant arm, variant vs its own original ----
    for VAR in ("B4", "B2", "B5", "B8L180", "B8L360"):
        for arm in ("FRESH", "NEWS"):
            for sd in ("42", "2027"):
                p = f"{R}/SER_{VAR}_{arm}_s{sd}.npz"
                if not os.path.exists(p):
                    rec["unavailable"].append({"item": f"{VAR}_{arm}_s{sd}", "why": "SER file absent"}); continue
                V = np.load(p)
                ax = V["anchors"].astype(np.int64)
                assert np.array_equal(ax, ax_ref), f"{VAR} {arm} s{sd}: axis != seat axis"
                dv = np.asarray(V["price_vs_own_original_bps"], float)
                for ename, ed in EDGES.items():
                    bucket_report(f"{VAR}_{arm}_s{sd}_vs_own_original_price__edges_{ename}", dv, ax, ref, rec["tables"], ed)

    # ---- state-group absolutes: recoverable from the existing receipts only; masks are gone ----
    st = {}
    for f, var in (("FA_B4_READ.json", "B4"), ("FA_B2_READ.json", "B2"), ("FA_B5_READ.json", "B5"),
                   ("FA_B8_READ_180.json", "B8L180"), ("FA_B8_READ_360.json", "B8L360")):
        fp = f"{R}/{f}"
        if not os.path.exists(fp):
            rec["unavailable"].append({"item": f"state_groups_{var}", "why": f"{f} absent"}); continue
        d = json.load(open(fp))
        for k, a in d.get("arms", {}).items():
            rows = a.get("state_groups", {}).get("rows", {})
            st[k] = {g: {"n": r["n"],
                         "absolute_bps_total": (r.get("absolute_bps_total")
                                                if r.get("absolute_bps_total") is not None
                                                else (r["bps_per_anchor"] * r["n"] if r.get("bps_per_anchor") is not None else None)),
                         "bps_per_anchor": r.get("bps_per_anchor")}
                     for g, r in rows.items()}
    rec["state_group_absolutes_from_receipts"] = st
    rec["unavailable"].append({"item": "state-group per-anchor rate differences with CI",
                              "why": "the publish/hold masks come from the variant combo npz, which were freed after "
                                     "their receipts were saved. Absolute contributions are recovered arithmetically "
                                     "from the receipts (n x bps_per_anchor); the CI is NOT recoverable without the "
                                     "masks and is therefore reported as UNAVAILABLE rather than re-run (lead 2026-09-24)."})
    rec["seconds"] = round(time.time() - t0, 1)
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    assert os.path.exists(OUT), "receipt not written"

    gb = rec["gates"]["G_B_reproduce_frozen_edges"]
    print("FA_RATEDIFF G_A=%s | G_B exact_to_1e-9=%s (Q33 d=%.2e, Q67 d=%.2e, %d/%d anchors change tercile) | tables=%d"
          % (rec["gates"]["G_A_seat_variable_identical_across_files"]["all_identical"], gb["EXACT_TO_1e-9"],
             gb["Q33_abs_diff"], gb["Q67_abs_diff"], gb["anchors_changing_tercile"], gb["n_pre2026"],
             len(rec["tables"])), flush=True)
    for k, v in rec["tables"].items():
        h = v["high_vs_rest_bps_per_anchor"]
        print("  %-42s high-rest=%+8.4f bps/anc ci=%s %s | low/mid/high abs bps = %+8.1f / %+8.1f / %+8.1f | cancel=%.3f"
              % (k, h["difference"], [round(c, 3) if c is not None else None for c in h["ci95_30day_block"]],
                 "EXCLUDES_ZERO" if h["excludes_zero"] else "crosses_zero",
                 v["buckets"]["seat_low"]["absolute_bps_total"], v["buckets"]["seat_mid"]["absolute_bps_total"],
                 v["buckets"]["seat_high"]["absolute_bps_total"], v["cancellation_ratio"] or 0.0), flush=True)


if __name__ == "__main__":
    main()
