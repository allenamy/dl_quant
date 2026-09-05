"""judge_dl.py — dl_monthly_wf frozen judge (lead's spec, 2026-09-05, numbers unseen when written).
Artifacts: replay/dev_alt/probe_artifacts/w10_ablation_series_<TAG>.npz (device w10_health.py, arm d30_n2_c42), primary form = U-PIT, UMASK_SCOPE=m1, prod caliber
(meta_newprod: y4 = Π(1+r5)−1), fee-only live cost tiers, LEGS=101, LOOK=900, msharpe, PHI 0.45, FTRIM zero, FSEED 42, pinned king.
Arms: BASE (FPRED = yearly-fold file; must be bitwise = health_check M1_UPIT_prod_s42_ccal, checked by check_equiv) | M1_<TAG>spl (spliced: yearly < 2025-01, monthly ≥;
PRIMARY) | M1_<TAG>pure (NaN before 2025-01; lead's literal spec, sensitivity) | PHI1_* (PHI=1.0: the F10 book alone in the live form, auxiliary).
Quantity: g = net_ex / gross_total (bps per anchor per unit gross; health_metrics units chain) — paired Δ = g_x − g_ref per anchor (net_ex per NAV Δ also printed).
Windows: 2025 | 2026<=cut (08-10 20Z) | 2025->26<=cut (PRIMARY) | pre-2025 (must be exactly 0 for spliced arms) | 2026-postcut (F10 leg absent in both ⇒ Δ must be 0).
Bootstrap: UTC-day blocks, 2000 resamples, seed 20260905; CI95 = 2.5/97.5 pct; P = P(mean>0). Sharpe = mean/std(ddof=1)·√2190; maxDD on cumsum(g) in bps gross.
Frozen comparison (lead): "monthly not worse than yearly" ⇔ 2025->26 CI95 upper of Δg > 0 AND ΔIC (2025->26<=cut, ic_monthly.py) ≥ 0. No admission decision.
usage: judge_dl.py <TAG> [<TAG>...]   → replay/results/judge_dl.json + stdout"""
import os, sys, json, time, calendar, hashlib
import numpy as np
R = "/workspace/review_scratch/dl_monthly_wf"; PA = f"{R}/replay/dev_alt/probe_artifacts"; NB = 2000; SEED = 20260905; ARM = "d30_n2_c42"
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); T26 = calendar.timegm((2026, 1, 1, 0, 0, 0))
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
TAGS = sys.argv[1:]; assert TAGS
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
EXPECT = {"LEGS": "101", "CAL": "log", "LOOK": 900, "WRULE": "msharpe", "FSEED": "42", "MEMBERS_TOPN": 829, "TRADE_TOPN": 0, "FTRIM": "zero", "UMASK_SCOPE": "m1", "W3FIX": None, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy"}
ARMS = {"BASE": ("BASE_M1_UPIT_prod_s42_ccal", 0.45, "(default f10_V2MAIN_s{FSEED})"), "PHI1_BASE": ("PHI1_BASE_prod_s42_ccal", 1.0, "(default f10_V2MAIN_s{FSEED})")}
for T in TAGS:
    ARMS[f"{T}spl"] = (f"M1_{T}spl_prod_s42_ccal", 0.45, f"f10_V2MAIN_{T}spl_s42.npy"); ARMS[f"{T}pure"] = (f"M1_{T}pure_prod_s42_ccal", 0.45, f"f10_V2MAIN_{T}_s42.npy")
    ARMS[f"PHI1_{T}spl"] = (f"PHI1_{T}spl_prod_s42_ccal", 1.0, f"f10_V2MAIN_{T}spl_s42.npy")
D = {}; META = {}
for key, (tag, phi, fpred) in ARMS.items():
    p = f"{PA}/w10_ablation_series_{tag}.npz"
    if not os.path.exists(p): print(f"MISSING {key}: {p}"); continue
    z = np.load(p, allow_pickle=True); cfg = json.loads(str(z["config_json"])); assert [str(c) for c in z["cols"]] == COLS
    for k, v in EXPECT.items(): assert cfg.get(k) == v, (key, k, cfg.get(k), v)
    assert abs(cfg["PHI"] - phi) < 1e-12 and cfg["FPRED"] == fpred and cfg["COSTB_JSON"] and cfg["UMASK_NPZ"], (key, cfg["PHI"], cfg["FPRED"], cfg["COSTB_JSON"], cfg["UMASK_NPZ"])
    Rr = z[f"{ARM}_rec"]; D[key] = {c: Rr[:, i] for i, c in enumerate(COLS)}; META[key] = {"artifact": p, "sha256": sha(p)[:16], "FPRED": fpred, "PHI": phi, "n": int(len(Rr))}
keys = list(D); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), ("ts mismatch", k)
days = ts0 // 86400; yrs = np.array([time.gmtime(int(t)).tm_year for t in ts0])
WIN = {"pre-2025": ts0 < T25, "2025": (ts0 >= T25) & (ts0 < T26), "2026<=cut": (ts0 >= T26) & (ts0 <= CUT), "2025->26<=cut": (ts0 >= T25) & (ts0 <= CUT), "2026-postcut": ts0 > CUT, "2024->26<=cut": (ts0 >= calendar.timegm((2024, 1, 1, 0, 0, 0))) & (ts0 <= CUT)}
G = {k: D[k]["net_ex"] / D[k]["gross_total"] for k in keys}; NAVX = {k: D[k]["net_ex"] for k in keys}
rng = np.random.default_rng(SEED)
def boot(x, m):
    v = x[m]; d = days[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud)
    s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "n_days": int(nd), "mean": float(v.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5)), "P>0": float((means > 0).mean()), "pct_gross_yr": float(v.mean() * 2190 / 100)}
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
OUT = {"arm": ARM, "n_anchors": int(len(ts0)), "first": iso(ts0[0]), "last": iso(ts0[-1]), "cut": iso(CUT), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "arms": META,
       "units": "g = net_ex/gross_total, bps per anchor per unit gross (primary); net_ex per unit NAV also given; %/gross/yr = mean*2190/100", "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "levels": {}, "deltas": {}, "frozen_comparison": {}}
print(f"LOADED {len(D)} arms n={len(ts0)} {iso(ts0[0])}→{iso(ts0[-1])}; windows " + ", ".join(f"{w}={int(m.sum())}" for w, m in WIN.items()))
print("ARMS " + json.dumps(META))
LW = ("2025", "2026<=cut", "2025->26<=cut", "2024->26<=cut")
print(f"\n===== LEVELS (per gross, bps/anchor): mean S=Sharpe DD=maxDD(bps gross) %/gross/yr | gross w_king turn/gross cost/gross carry/gross (2025->26<=cut)")
for k in keys:
    row = {}
    for w, m in WIN.items():
        if m.sum() < 12: continue
        x = G[k][m]; d = D[k]
        row[w] = {"n": int(m.sum()), "mean": float(x.mean()), "sharpe": sharpe(x), "maxDD_bps": maxdd(x), "pct_gross_yr": float(x.mean() * 2190 / 100), "net_ex_nav_mean": float(NAVX[k][m].mean()),
                  "gross": float(d["gross_total"][m].mean()), "w_king": float(d["w3_king"][m].mean()), "w_fund": float(d["w3_fund"][m].mean()), "turn_per_gross": float((d["turnover"][m] / d["gross_total"][m]).mean()),
                  "cost_per_gross": float((d["cost_ex"][m] / d["gross_total"][m]).mean()), "carry_per_gross": float((d["carry_ex"][m] / d["gross_total"][m]).mean()), "fires": int(d["fires"][m].sum())}
        if w in ("2025", "2026<=cut", "2025->26<=cut"): row[w]["boot"] = boot(G[k], m)
    OUT["levels"][k] = row; r = row.get("2025->26<=cut", {})
    print(f"{k:14s}| " + " | ".join(f"{w} {row[w]['mean']:+.3f} S{row[w]['sharpe']:+.2f} DD{row[w]['maxDD_bps']:.0f} {row[w]['pct_gross_yr']:+.1f}%" for w in LW if w in row)
          + (f" | {r.get('gross', 0):.3f} {r.get('w_king', 0):.3f} {r.get('turn_per_gross', 0):.5f} {r.get('cost_per_gross', 0):.3f} {r.get('carry_per_gross', 0):+.3f}" if r else ""))
PAIRS = []
for T in TAGS:
    PAIRS += [(f"{T}spl", "BASE", f"{T}spl-BASE (PRIMARY: spliced, identical state entering 2025-01)"), (f"{T}pure", "BASE", f"{T}pure-BASE (sensitivity: NaN before 2025-01)"), (f"PHI1_{T}spl", "PHI1_BASE", f"PHI1 {T}spl-BASE (F10 book alone, auxiliary)")]
if len(TAGS) == 2: PAIRS.append((f"{TAGS[1]}spl", f"{TAGS[0]}spl", f"{TAGS[1]}spl-{TAGS[0]}spl (embargo effect at monthly cadence)"))
DW = ("pre-2025", "2025", "2026<=cut", "2025->26<=cut", "2026-postcut")
print(f"\n===== DELTAS per gross: Δg = g_x − g_ref (bps/anchor per gross), paired by anchor; day-block bootstrap NB={NB} seed={SEED}; cells Δ [CI95] P(Δ>0)")
for kx, ky, name in PAIRS:
    if kx not in D or ky not in D: print(f"skip {name}: missing"); continue
    dg = G[kx] - G[ky]; dn = NAVX[kx] - NAVX[ky]; res = {}
    for w in DW:
        m = WIN[w]
        if m.sum() < 12: continue
        b = boot(dg, m); b["exact_zero"] = bool(np.all(dg[m] == 0)); b["maxabs"] = float(np.max(np.abs(dg[m]))); b["nav_delta_mean"] = float(dn[m].mean()); res[w] = b
    dsh = {w: sharpe(G[kx][WIN[w]]) - sharpe(G[ky][WIN[w]]) for w in ("2025->26<=cut", "2025", "2026<=cut")}
    tx = float((D[kx]["turnover"] / D[kx]["gross_total"])[WIN["2025->26<=cut"]].mean()); ty = float((D[ky]["turnover"] / D[ky]["gross_total"])[WIN["2025->26<=cut"]].mean())
    ddx = maxdd(G[kx][WIN["2025->26<=cut"]]); ddy = maxdd(G[ky][WIN["2025->26<=cut"]])
    OUT["deltas"][name] = {"x": kx, "ref": ky, "windows": res, "dSharpe": dsh, "turn_per_gross_ref": ty, "turn_per_gross_x": tx, "dturn_pct": (tx / ty - 1) * 100 if ty > 0 else None, "maxDD_ref_25on": ddy, "maxDD_x_25on": ddx}
    f = lambda w: (f"{res[w]['mean']:+.4f} [{res[w]['lo']:+.4f},{res[w]['hi']:+.4f}] P{res[w]['P>0']:.3f}" + (" (exact 0)" if res[w]["exact_zero"] else "")) if w in res else "n/a"
    print(f"{name}\n    " + " | ".join(f"{w}: {f(w)}" for w in DW) + f"\n    ΔSharpe 25on {dsh['2025->26<=cut']:+.3f} (2025 {dsh['2025']:+.3f}, 2026 {dsh['2026<=cut']:+.3f}); turn/gross ref {ty:.5f} x {tx:.5f} ({(tx / ty - 1) * 100:+.1f}%); maxDD 25on ref {ddy:.0f} x {ddx:.0f} bps gross; NAV-caliber Δnet_ex 25on {res.get('2025->26<=cut', {}).get('nav_delta_mean', float('nan')):+.4f}")
# frozen comparison
icj = None
for cand in (f"{R}/logs/ic_{'_'.join(TAGS)}.json", f"{R}/logs/ic_mE60_mE1.json", f"{R}/logs/ic_mE60.json"):
    if os.path.exists(cand): icj = json.load(open(cand)); break
for T in TAGS:
    d = OUT["deltas"].get(f"{T}spl-BASE (PRIMARY: spliced, identical state entering 2025-01)", {}).get("windows", {}).get("2025->26<=cut")
    dp = OUT["deltas"].get(f"{T}pure-BASE (sensitivity: NaN before 2025-01)", {}).get("windows", {}).get("2025->26<=cut")
    ic = icj["ic_delta_vs_yearly"].get(f"2025->26<=cut/{T}") if icj else None
    c = {"book_delta_per_gross_2025->26": d, "book_CI95_upper>0": (d["hi"] > 0) if d else None, "book_delta_pure_sensitivity": dp, "ic_delta_2025->26": ic, "ic_delta>=0": (ic["mean"] >= 0) if ic else None}
    c["monthly_not_worse_than_yearly"] = bool(c["book_CI95_upper>0"] and c["ic_delta>=0"]) if (d and ic) else None
    OUT["frozen_comparison"][T] = c
    print(f"\n===== FROZEN COMPARISON [{T}] 'monthly not worse than yearly' = 2025->26 CI95 upper > 0 AND ΔIC >= 0: " + (f"book Δg {d['mean']:+.4f} [{d['lo']:+.4f},{d['hi']:+.4f}] upper>0={c['book_CI95_upper>0']}; " if d else "book n/a; ")
          + (f"ΔIC {ic['mean']:+.4f} ± {ic['se_anchor']:.4f} CI [{ic['ci95_dayblock'][0]:+.4f},{ic['ci95_dayblock'][1]:+.4f}] >=0={c['ic_delta>=0']}; " if ic else "IC n/a; ") + f"⇒ {c['monthly_not_worse_than_yearly']}")
os.makedirs(f"{R}/replay/results", exist_ok=True); json.dump(OUT, open(f"{R}/replay/results/judge_dl.json", "w"), indent=1, default=float)
print(f"\nwrote {R}/replay/results/judge_dl.json"); print("JUDGE_DONE", flush=True)
