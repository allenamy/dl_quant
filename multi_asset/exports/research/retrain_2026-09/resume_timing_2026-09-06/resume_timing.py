#!/usr/bin/env python3
"""resume_timing.py — read-only DIAGNOSTIC: after the day-loss stop trips, how long should the book stay flat?
Question (written before the numbers): the trip itself is a hard operational rule; the free variable is the RESUME DELAY.

Device: health_check main-arm replay artifacts (M1_UPIT_prod_s{42,2027}_ccal.npz, key d30_n2_c42_rec) — the same series the
base-rate doc used. g = net_ex/gross_total [bps/anchor per unit gross]; NAV at 2x: r = 2g/1e4; UTC-day compounding.

Trip model (matches live semantics, watchdog.py [B32]): within each UTC day, walk anchors accumulating the day return;
the FIRST anchor at which the running day return <= THR is the trip anchor. Live behaviour: flatten at that moment,
no opening from the next anchor. So the flat window starts at trip+1.

Resume model: re-enter at anchor trip+1+k (k = anchors waited, k=0 means resume at the very next anchor).
Cost of waiting k = the 2x return over anchors [trip+1, trip+1+k) that the flat book forgoes (sign: positive = waiting cost).
Re-entry cost: one full rebuild from flat = 1.0 unit of gross turnover at COST bps per unit turnover (default 3.52,
the re-audited live turnover cost), i.e. 2*COST/1e4 of NAV at 2x — charged once, independent of k.

Also reported: baseline unconditional per-anchor mean (is the post-trip regime better or worse than normal?),
and the same for the -2.68% investigation tier (larger sample).
NOT a gate; any resume RULE would need its own prereg + user word."""
import json, time, calendar, hashlib, sys
import numpy as np
H = "/workspace/review_scratch/health_check"
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {k: i for i, k in enumerate(COLS)}; L, COST = 2.0, 3.52
THRS = {"-4.0%": -0.040, "-2.68%": -0.0268}
KS = [0, 1, 2, 3, 6, 12, 18, 24, 36, 48, 72]
out = {"device": "health_check M1_UPIT_prod_s{seed}_ccal.npz d30_n2_c42_rec", "units": "2x NAV; UTC-day compounding; COST 3.52 bps per unit turnover",
       "caveat": "DIAGNOSTIC, not a gate. Trip counts are tiny at -4.0%; the -2.68% tier is the usable sample.", "seeds": {}}
for seed in (42, 2027):
    p = f"{H}/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s{seed}_ccal.npz"
    z = np.load(p, allow_pickle=True); assert [str(c) for c in z["cols"]] == COLS
    R = np.asarray(z["d30_n2_c42_rec"], float); ts = R[:, C["ts"]].astype(np.int64)
    g = R[:, C["net_ex"]] / R[:, C["gross_total"]]; r = L * g / 1e4
    sha = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    days = ts // 86400; ud = np.unique(days)
    res = {"artifact": p, "sha16": sha, "n_anchors": int(len(ts)), "baseline_mean_bps_2x": float(r.mean() * 1e4), "tiers": {}}
    for tname, thr in THRS.items():
        trips = []
        for d in ud:
            idx = np.where(days == d)[0]
            cum = np.cumprod(1 + r[idx]) - 1
            hit = np.where(cum <= thr)[0]
            if len(hit): trips.append(int(idx[hit[0]]))
        fwd = {}
        for k in KS:
            # return over the window the flat book forgoes: anchors [trip+1, trip+1+k)
            forgone = [float(np.prod(1 + r[t+1:t+1+k]) - 1) for t in trips if t + 1 + k <= len(r)] if k > 0 else []
            # return of the resumed book over the 30 anchors after re-entry (comparable horizon for every k)
            after = [float(np.prod(1 + r[t+1+k:t+1+k+30]) - 1) for t in trips if t + 1 + k + 30 <= len(r)]
            fwd[str(k)] = {"n": len(after), "forgone_pct_mean": (float(np.mean(forgone)) * 100 if forgone else 0.0),
                           "next30_after_resume_pct_mean": (float(np.mean(after)) * 100 if after else None),
                           "next30_after_resume_pct_median": (float(np.median(after)) * 100 if after else None)}
        # per-anchor mean in horizon buckets after the trip (is the post-trip regime unusual?)
        buckets = {}
        for lo, hi in ((1, 6), (7, 12), (13, 24), (25, 48), (49, 72), (73, 144)):
            vals = [r[t+lo:t+hi+1] for t in trips if t + hi + 1 <= len(r)]
            if vals:
                v = np.concatenate(vals); buckets[f"{lo}-{hi}"] = {"n_anchors": int(len(v)), "mean_bps_2x": float(v.mean() * 1e4), "share_pos": float((v > 0).mean())}
        res["tiers"][tname] = {"n_trips": len(trips), "trip_days": [time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(ts[t]))) for t in trips],
                              "reentry_cost_pct_2x": L * COST / 1e4 * 100, "by_wait_k": fwd, "post_trip_buckets": buckets}
    out["seeds"][f"s{seed}"] = res
json.dump(out, open("/workspace/review_scratch/health_check/resume_timing.json", "w"), indent=1, default=float)
for s, res in out["seeds"].items():
    print(f"\n===== {s}  基线每锚 {res['baseline_mean_bps_2x']:+.2f} bps(2×)  锚数 {res['n_anchors']}  再入场成本 { L*COST/1e4*100:.3f}%")
    for tname, t in res["tiers"].items():
        print(f"-- 触发档 {tname}: {t['n_trips']} 次  {t['trip_days']}")
        print("   等待 k 锚 | 放弃的收益% | 复场后 30 锚收益%(均值/中位) | n")
        for k in KS:
            f = t["by_wait_k"][str(k)]
            a = f["next30_after_resume_pct_mean"]; m = f["next30_after_resume_pct_median"]
            print(f"     k={k:>3} | {f['forgone_pct_mean']:+7.2f}% | {('%+7.2f' % a) if a is not None else '   n/a '} / {('%+7.2f' % m) if m is not None else '   n/a '} | {f['n']}")
        print("   触发后逐段每锚均值(2×): " + ", ".join(f"{kk}: {vv['mean_bps_2x']:+.1f} bps (正占比 {vv['share_pos']:.2f}, n {vv['n_anchors']})" for kk, vv in t["post_trip_buckets"].items()))
print("\nRESUME_TIMING_DONE")
