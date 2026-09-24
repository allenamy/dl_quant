"""fa_b8read.py — B8's frozen readout list (PREREG_fresh_rootcause_B8_2026-09-24.md, 38f4c0fbd §4). Read-only, no engine.
Derived from fa_bread.py; the readout list and its arithmetic are unchanged. Two additions:
  1. the variant->combo-dir map gains B8L180 / B8L360 (an explicit map: a default that quietly resolves to another
     variant is what made B2 report B4's hold/gross);
  2. PREREG §4's extra readout -- FRESH's variant against NEW_S's ORIGINAL look=900 book, i.e. how much of the gap
     is left -- computed with the same daily pairing and the same bootstrap.

One thing to keep straight when reading the output: the high-seat tercile uses FRESH's look=900 seat (the fixed Q33/Q67
below), NOT the variant's recomputed seat. It is deliberately a FIXED conditioning variable, so "high seat" names the
same population of anchors in every arm and the buckets do not move underneath the comparison. It therefore does not
mean "high seat under the short window"."""
import os, sys, json, time, hashlib, calendar
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x
OUT = sys.argv[2]
R = "/dev/shm/fanom_2026-09-24/receipts"; F = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"
PRE = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"); Q33, Q67 = 0.5725596881282329, 0.7810047984528542
B = 10000; RNG = (20260923, 1); BLOCK = 30; DAY = 86400
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def q(v, m):
    vv = v[m]; vv = vv[np.isfinite(vv)]
    return {"median": float(np.median(vv)), "q25": float(np.percentile(vv, 25)), "q75": float(np.percentile(vv, 75))} if len(vv) else None
def daily(r, A, m):
    d = A // DAY; out = {}
    for dd in np.unique(d[m]):
        s = m & (d == dd); out[int(dd)] = float(np.prod(1.0 + r[s]) - 1.0)
    return out
def boot_mean(x, days, rs):
    ud = np.unique(days); st = np.arange(max(1, len(ud) - BLOCK + 1)); nb = int(np.ceil(len(ud) / BLOCK)); o = []
    for _ in range(B):
        sel = np.concatenate([ud[s:s + BLOCK] for s in rs.choice(st, size=nb, replace=True)])
        v = x[np.isin(days, sel)]
        if len(v) >= 5: o.append(float(np.nanmean(v)))
    o = np.array(o)
    return [float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))] if len(o) > 100 else [None, None]
def hold_age(pub):
    age = np.zeros(len(pub), np.int64); last = -1
    for i in range(len(pub)):
        if pub[i]: last = i; age[i] = 0
        else: age[i] = (i - last) if last >= 0 else -1
    return age

rec = {"device": "fa_b8read.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "variant": sys.argv[3] if len(sys.argv)>3 else "B4",
       "prereg": {"path": "docs/PREREG_fresh_rootcause_B8_2026-09-24.md", "commit": "38f4c0fbd"},
       "seat_tercile_note": "terciles use FRESH look=900 seat (fixed conditioning variable), not the variant seat",
       "arms": {}, "gap_remaining": {}}
for arm in ("FRESH", "NEWS"):
    for seed in ("42", "2027"):
        VAR = sys.argv[3] if len(sys.argv)>3 else "B4"
        key = f"{VAR}_{arm}_s{seed}"
        V = np.load(f"{R}/SER_{key}.npz"); O = np.load(f"{R}/SER_ORIG_{arm}_s{seed}.npz")
        ax = V["anchors"].astype(np.int64); assert np.array_equal(ax, O["anchors"].astype(np.int64))
        pre = V["in_pre2026"].astype(bool); seat = V["seat_king_FRESH"]
        # 1. dbar vs own original, bps/day, paired on full UTC days
        dv = daily(V["daily_r_variant"], ax, pre); do = daily(O["daily_r"], ax, pre)
        days = sorted(set(dv) & set(do))
        dd = np.array([1e4 * (dv[k] - do[k]) for k in days]); da = np.array(days)
        dbar = {"mean_bps_per_day": float(dd.mean()), "n_days": int(len(dd)),
                "window": "pre2026 (%s .. %s)" % PRE,
                "ci95": boot_mean(dd, da, np.random.default_rng(RNG))}
        # price-channel difference vs own original, bps/anchor
        dprice = V["price_vs_own_original_bps"]
        # 2-5 need the variant's own publication state
        root = F if arm == "FRESH" else N
        # explicit variant -> combo-dir map. The previous fallback ("B5T" if B5 else "B4") silently read the
        # B4 combo for B2 and reported B4's hold/gross as if they were B2's. A default that quietly resolves
        # to another variant is the same family as a missing key resolving to some other arm.
        PREF = {"B4": "B4", "B5": "B5", "B2": "B2", "B8L180": "B8L180", "B8L360": "B8L360"}
        assert VAR in PREF, f"no combo prefix mapped for variant {VAR}"
        pref = PREF[VAR]
        vdir = f"/dev/shm/fanom_2026-09-24/bvar/{pref}_{'fresh' if arm=='FRESH' else 'news'}_2026-09-23_s{seed}"
        if VAR == "B5":
            # B5's variant combo lives under the B5_ prefix (the transform used the ORIGINAL targets, but the
            # publication state it represents is the B5 variant combo built by fa_bvariant.py)
            vdir_c = vdir
            CV = np.load(f"{vdir_c}/scaled_diagnostic.npz", allow_pickle=True)
        else:
            CV = np.load(f"{vdir}/scaled_diagnostic.npz", allow_pickle=True)
        CO = np.load(f"{root}/work/combo_s{seed}/scaled_diagnostic.npz", allow_pickle=True)
        ce = CV["E_ts"].astype(np.int64); cp = {int(t): i for i, t in enumerate(ce)}
        ci = np.array([cp.get(int(t), -1) for t in ax]); ok = ci >= 0
        pv = np.zeros(len(ax), bool); po = np.zeros(len(ax), bool)
        pv[ok] = np.asarray(CV["trade_mask"])[ci[ok]].astype(bool); po[ok] = np.asarray(CO["trade_mask"])[ci[ok]].astype(bool)
        gv = np.full(len(ax), np.nan); gv[ok] = np.abs(CV["raw"])[ci[ok]].sum(1)
        terc = np.where(seat <= Q33, 0, np.where(seat <= Q67, 1, 2))
        pop = pre & ok; den = float(np.nansum(dprice[pop]))
        grp = {"G1_both_publish": pop & pv & po, "G2_variant_hold_orig_publish": pop & ~pv & po,
               "G3_variant_publish_orig_hold": pop & pv & ~po, "G4_both_hold": pop & ~pv & ~po}
        rows = {}; tot = 0.0; n = 0
        for g, m in grp.items():
            s = float(np.nansum(dprice[m])); tot += s; n += int(m.sum())
            rows[g] = {"n": int(m.sum()), "bps_per_anchor": float(np.nanmean(dprice[m])) if m.any() else None,
                       "share": (s / den if den else None)}
        closes = abs(tot - den) <= 1e-9 * max(1.0, abs(den)) and n == int(pop.sum())
        age = np.full(len(ax), -1, np.int64); age[ok] = hold_age(np.asarray(CV["trade_mask"]).astype(bool))[ci[ok]]
        m12 = pop & (age >= 1) & (age <= 2)
        hi = pop & (terc == 2)
        rec["arms"][key] = {"dbar_vs_own_original": dbar,
                            "price_vs_own_original_bps_per_anchor": float(np.nanmean(dprice[pop])),
                            "state_groups": {"rows": rows, "sum_shares": float(tot / den) if den else None, "CLOSES": bool(closes)},
                            "hold_age_1_2": {"n": int(m12.sum()), "bps_per_anchor": float(np.nanmean(dprice[m12])) if m12.any() else None},
                            "high_seat_share": (float(np.nansum(dprice[hi])) / den if den else None),
                            "gross_vs_floor": {"median": q(gv, pop)["median"], "q25": q(gv, pop)["q25"], "q75": q(gv, pop)["q75"],
                                               "frac_below_0.4": float(np.nanmean((gv[pop] < 0.4).astype(float)))},
                            "hold_fraction_variant": float((~pv[pop]).mean()), "hold_fraction_original": float((~po[pop]).mean())}
        assert closes, f"{key}: state groups do not close"

# PREREG §4 extra: FRESH's variant against NEW_S's ORIGINAL (look=900) book -- how much of the gap is left.
# Same daily pairing, same bootstrap, same judge window as every dbar above.
for seed in ("42", "2027"):
    VAR = sys.argv[3] if len(sys.argv) > 3 else "B4"
    V = np.load(f"{R}/SER_{VAR}_FRESH_s{seed}.npz"); ON = np.load(f"{R}/SER_ORIG_NEWS_s{seed}.npz")
    ax = V["anchors"].astype(np.int64); assert np.array_equal(ax, ON["anchors"].astype(np.int64))
    pre = V["in_pre2026"].astype(bool)
    dv = daily(V["daily_r_variant"], ax, pre); dn = daily(ON["daily_r"], ax, pre)
    days = sorted(set(dv) & set(dn))
    dd = np.array([1e4 * (dv[k] - dn[k]) for k in days]); da = np.array(days)
    # the baseline gap, for reference on the same days: FRESH's OWN original vs NEW_S's original
    OF = np.load(f"{R}/SER_ORIG_FRESH_s{seed}.npz"); df = daily(OF["daily_r"], ax, pre)
    d0 = np.array([1e4 * (df[k] - dn[k]) for k in days])
    rec["gap_remaining"][f"{VAR}_FRESH_vs_ORIG_NEWS_s{seed}"] = {
        "mean_bps_per_day": float(dd.mean()), "n_days": int(len(dd)),
        "window": "pre2026 (%s .. %s)" % PRE,
        "ci95": boot_mean(dd, da, np.random.default_rng(RNG)),
        "baseline_gap_ORIG_FRESH_vs_ORIG_NEWS_same_days": float(d0.mean()),
        "gap_closed_bps_per_day": float(dd.mean() - d0.mean()),
        "window_note": ("the baseline gap is computed HERE, on the same days and with the same arithmetic as the "
                        "numerator. Do NOT divide by the -5.592/-5.208 figure from the FRESH verdict: that is the "
                        "FULL judge window (1157d, includes 2026 where FRESH is better by +0.81/+0.85) and mixing "
                        "windows overstated B4's recovered share as 34-41% when the matched-window value is 26-31% "
                        "(correction W-1 in RESULT_fresh_book_anomaly_2026-09-24.md)")}
json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
print("FA_B8READ %s" % (sys.argv[3] if len(sys.argv)>3 else "B4"), flush=True)
for k, v in rec["arms"].items():
    print("  %-16s dbar=%+8.4f bps/d ci=%s | price=%+7.4f bps/anc | hold %.3f->%.3f | gross med %.4f (<0.4 %.3f) | hi_seat_share=%+.3f | age1-2=%s"
          % (k, v["dbar_vs_own_original"]["mean_bps_per_day"],
             [round(c, 3) if c is not None else None for c in v["dbar_vs_own_original"]["ci95"]],
             v["price_vs_own_original_bps_per_anchor"], v["hold_fraction_original"], v["hold_fraction_variant"],
             v["gross_vs_floor"]["median"], v["gross_vs_floor"]["frac_below_0.4"], v["high_seat_share"],
             ("%+.4f" % v["hold_age_1_2"]["bps_per_anchor"]) if v["hold_age_1_2"]["bps_per_anchor"] is not None else "n/a"), flush=True)
for k, v in rec["gap_remaining"].items():
    print("  GAP %-28s dbar=%+8.4f bps/d ci=%s | baseline gap %+8.4f | closed %+8.4f"
          % (k, v["mean_bps_per_day"], [round(c, 3) if c is not None else None for c in v["ci95"]],
             v["baseline_gap_ORIG_FRESH_vs_ORIG_NEWS_same_days"], v["gap_closed_bps_per_day"]), flush=True)
