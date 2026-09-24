"""fa_b4read.py — B4's frozen readout list (PREREG 56c0177aa §3). Read-only, no engine.
dbar is computed against each arm's OWN original from the saved complete series."""
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

rec = {"device": "fa_b4read.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "variant": "B4",
       "prereg": {"path": "docs/PREREG_fresh_rootcause_B_2026-09-24.md", "commit": "56c0177aa"}, "arms": {}}
for arm in ("FRESH", "NEWS"):
    for seed in ("42", "2027"):
        key = f"B4_{arm}_s{seed}"
        V = np.load(f"{R}/SER_{key}.npz"); O = np.load(f"{R}/SER_ORIG_{arm}_s{seed}.npz")
        ax = V["anchors"].astype(np.int64); assert np.array_equal(ax, O["anchors"].astype(np.int64))
        pre = V["in_pre2026"].astype(bool); seat = V["seat_king_FRESH"]
        # 1. dbar vs own original, bps/day, paired on full UTC days
        dv = daily(V["daily_r_variant"], ax, pre); do = daily(O["daily_r"], ax, pre)
        days = sorted(set(dv) & set(do))
        dd = np.array([1e4 * (dv[k] - do[k]) for k in days]); da = np.array(days)
        dbar = {"mean_bps_per_day": float(dd.mean()), "n_days": int(len(dd)),
                "ci95": boot_mean(dd, da, np.random.default_rng(RNG))}
        # price-channel difference vs own original, bps/anchor
        dprice = V["price_vs_own_original_bps"]
        # 2-5 need the variant's own publication state
        root = F if arm == "FRESH" else N
        vdir = f"/dev/shm/fanom_2026-09-24/bvar/B4_{'fresh' if arm=='FRESH' else 'news'}_2026-09-23_s{seed}"
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
json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
print("FA_B4READ", flush=True)
for k, v in rec["arms"].items():
    print("  %-16s dbar=%+8.4f bps/d ci=%s | price=%+7.4f bps/anc | hold %.3f->%.3f | gross med %.4f (<0.4 %.3f) | hi_seat_share=%+.3f | age1-2=%s"
          % (k, v["dbar_vs_own_original"]["mean_bps_per_day"],
             [round(c, 3) if c is not None else None for c in v["dbar_vs_own_original"]["ci95"]],
             v["price_vs_own_original_bps_per_anchor"], v["hold_fraction_original"], v["hold_fraction_variant"],
             v["gross_vs_floor"]["median"], v["gross_vs_floor"]["frac_below_0.4"], v["high_seat_share"],
             ("%+.4f" % v["hold_age_1_2"]["bps_per_anchor"]) if v["hold_age_1_2"]["bps_per_anchor"] is not None else "n/a"), flush=True)
