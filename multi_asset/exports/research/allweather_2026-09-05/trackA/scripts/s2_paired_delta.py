"""s2_paired_delta.py — Track A S2 (PREREG_allweather_programme_2026-09-05 §3 Track A): paired per-gross Δ between two w10_health.py artifacts
(same device, same env, only SLOW_NPY differs: BASE king vs new-column king), window 2024→26 (2024-01-01 .. CUT 2026-08-10 20:00Z, the
health_metrics.py window) and by year. Units chain (E-0904-G, health_metrics.py): g = net_ex / gross_total [bps/anchor per unit gross].
Δ_i = g_new(i) - g_base(i) on common anchors; UTC-day-block bootstrap (2000 resamples, seed 20260905) of mean Δ -> CI95; turnover change =
mean(turnover/gross_total)_new / mean(turnover/gross_total)_base - 1. Gate: CI lower bound > 0 AND turnover change <= +25%.
usage: s2_paired_delta.py <base_artifact.npz> <new_artifact.npz> <out.json>
"""
import os, sys, json, time, calendar, hashlib
import numpy as np
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; NB = 2000; SEED = 20260905; APY = 2190
WIN = {"2023": (T("2023-01-01"), T("2024-01-01")), "2024": (T("2024-01-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")), "2026->cut": (T("2026-01-01"), CUT + 1),
       "2023->26": (T("2023-01-01"), CUT + 1), "2024->26": (T("2024-01-01"), CUT + 1)}
RULE = os.environ.get("RULE", "s2")   # s2: 2024->26 Δ CI lower > 0 AND turnover <= +25% | rider: 2024->26 Δ CI lower > 0 AND every year Δ >= -0.05 AND turnover <= +15%
def load(p):
    z = np.load(p, allow_pickle=True); k = "d30_n2_c42_rec"   # main arm (stop layer d30_n2_c42), same as health_metrics.py
    assert k in z.files, (p, z.files); assert [str(c) for c in z["cols"]] == COLS, (p, list(z["cols"]))
    R = np.asarray(z[k], float); assert R.shape[1] == len(COLS), (p, R.shape)
    return R
def boot(d, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    s1 = np.bincount(inv, d); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(SEED); idx = rng.integers(0, nd, size=(NB, nd))
    m = s1[idx].sum(1) / c[idx].sum(1)
    return {"n_days": int(nd), "ci95": [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)], "p_gt0": round(float((m > 0).mean()), 4)}
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
base_p, new_p, out_p = sys.argv[1:4]
B = load(base_p); N = load(new_p)
tb = B[:, C["ts"]].astype(np.int64); tn = N[:, C["ts"]].astype(np.int64)
common, ib, i_n = np.intersect1d(tb, tn, return_indices=True)
gb = B[ib, C["net_ex"]] / B[ib, C["gross_total"]]; gn = N[i_n, C["net_ex"]] / N[i_n, C["gross_total"]]
tob = B[ib, C["turnover"]] / B[ib, C["gross_total"]]; ton = N[i_n, C["turnover"]] / N[i_n, C["gross_total"]]
ok = np.isfinite(gb) & np.isfinite(gn)
days = common // 86400
res = {"base": base_p, "new": new_p, "sha256": {"base": hashlib.sha256(open(base_p, "rb").read()).hexdigest()[:16], "new": hashlib.sha256(open(new_p, "rb").read()).hexdigest()[:16]},
       "n_common_anchors": int(len(common)), "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "windows": {}}
for w, (lo, hi) in WIN.items():
    m = ok & (common >= lo) & (common < hi)
    if m.sum() < 10: continue
    d = gn[m] - gb[m]
    to_chg = float(ton[m].mean() / tob[m].mean() - 1) if tob[m].mean() > 0 else float("nan")
    b = boot(d, days[m])
    res["windows"][w] = {"n": int(m.sum()), "base_mean_bps_anchor_per_gross": round(float(gb[m].mean()), 4), "new_mean": round(float(gn[m].mean()), 4),
                         "delta_mean": round(float(d.mean()), 4), "delta_ci95": b["ci95"], "p_delta_gt0": b["p_gt0"], "n_days": b["n_days"],
                         "base_sharpe": round(sharpe(gb[m]), 3), "new_sharpe": round(sharpe(gn[m]), 3),
                         "turnover_base": round(float(tob[m].mean()), 5), "turnover_new": round(float(ton[m].mean()), 5), "turnover_change": round(to_chg, 4)}
    print(f"[{w}] n {m.sum()} base {gb[m].mean():+.4f} new {gn[m].mean():+.4f} Δ {d.mean():+.4f} CI95 {b['ci95']} p>0 {b['p_gt0']} Sharpe {sharpe(gb[m]):.2f}->{sharpe(gn[m]):.2f} turnover {to_chg:+.1%}", flush=True)
w = res["windows"].get("2024->26", {}); res["rule"] = RULE
if RULE == "rider":
    yrs_ok = all(res["windows"][y]["delta_mean"] >= -0.05 for y in ("2023", "2024", "2025", "2026->cut") if y in res["windows"])
    res["verdict"] = "PASS" if (w and w["delta_ci95"][0] > 0 and yrs_ok and w["turnover_change"] <= 0.15) else "KILLED"
else:
    res["verdict"] = "PASS" if (w and w["delta_ci95"][0] > 0 and w["turnover_change"] <= 0.25) else "KILLED"
json.dump(res, open(out_p, "w"), indent=1); print(f"PAIRED_DONE rule {RULE} verdict {res['verdict']}", flush=True)
