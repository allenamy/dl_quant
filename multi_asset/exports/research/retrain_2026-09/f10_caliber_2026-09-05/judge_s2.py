#!/usr/bin/env python
"""judge_s2.py — PREREG_f10_caliber_sensitivity_2026-09-05 §2 judge (frozen before numbers).
Inputs (read-only): f10_caliber/{dev,dev_alt,dev_alt2}/probe_artifacts/w10_ablation_series_{cal}_phi{0,045}_s{42,2027}.npz (12 artifacts, arm d30_n2_c42).
V2MAIN contribution Δ = g(PHI 0.45) − g(PHI 0), g = net_ex / gross_total = bps/anchor per unit gross (health_metrics.py units chain, E-0904-G), paired by anchor ts.
Secondary (device scale): Δ_raw = net_ex(0.45) − net_ex(0) in bps/anchor of the unit replay book.
Calibers: log = label (i) Σ-simple [E,E+47] (meta y4) · prod = label (iii) Π(1+r5)−1 [E+1,E+48] (meta_newprod) · sum1 = label (ii) Σ-simple [E+1,E+48] (meta_newsum_f10cal).
Windows: 2024 | 2025 | 2026<=08-10 (ts ≤ 2026-08-10 20:00Z, last finite F10 row) | 2024->26 | 2025->26. Seeds 42 / 2027.
Bootstrap: UTC-day blocks, 2000 resamples, seed 20260905 (fresh generator per cell), CI95 = 2.5/97.5 pct, P = P(mean>0), s.e. = std of resampled means.
Frozen reading (§2, per window 2024->26 and 2025->26): if under (i) the CI95 of Δ includes 0 for both seeds while under (ii) AND (iii) the CI95 lower bound > 0 for both seeds
⇒ record "the 08-26/09-04 'V2MAIN net ≈ 0' conclusion is affected by the one-bar window". Numbers only; no in-service verdict is changed here.
"""
import numpy as np, json, time, hashlib, calendar, os
ROOT = "/workspace/review_scratch/f10_caliber"; NB = 2000; SEED = 20260905
DIRS = {"log": "dev", "prod": "dev_alt", "sum1": "dev_alt2"}; LABEL = {"log": "(i) Σ-simple [E,E+47] = meta y4", "prod": "(iii) Π(1+r)−1 [E+1,E+48] = dlw y4s", "sum1": "(ii) Σ-simple [E+1,E+48]"}
CALS = ["log", "sum1", "prod"]; SEEDS = ["42", "2027"]; PHIS = ["0", "045"]
T_START = calendar.timegm((2024, 1, 1, 0, 0, 0)); T_END = calendar.timegm((2026, 8, 10, 20, 0, 0))
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
D = {}; CFG = {}; FSHA = {}; DEVSHA = set()
for cal in CALS:
    for phi in PHIS:
        for s in SEEDS:
            p = f"{ROOT}/{DIRS[cal]}/probe_artifacts/w10_ablation_series_{cal}_phi{phi}_s{s}.npz"
            z = np.load(p, allow_pickle=True); cfg = json.loads(str(z["config_json"])); cols = [str(c) for c in z["cols"]]; R = z["d30_n2_c42_rec"]
            exp_phi = 0.0 if phi == "0" else 0.45
            assert cfg["CAL"] == "log" and cfg["LEGS"] == "101" and cfg["MEMBERS_TOPN"] == 829 and cfg["UMASK_SCOPE"] == "m1" and cfg["FTRIM"] == "zero" and cfg["LOOK"] == 900 and cfg["WRULE"] == "msharpe" and cfg["TRADE_TOPN"] == 0 and cfg["W3FIX"] is None, (p, cfg)
            assert abs(cfg["PHI"] - exp_phi) < 1e-12 and cfg["FSEED"] == s and cfg["COSTB_JSON"].endswith("costb_fee_steady.json") and cfg["UMASK_NPZ"].endswith("umask_UPIT.npz"), (p, cfg["PHI"], cfg["FSEED"], cfg["COSTB_JSON"], cfg["UMASK_NPZ"])
            assert cfg["SLOW_NPY"] == "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", cfg["SLOW_NPY"]
            k = (cal, phi, s); D[k] = {c: R[:, i] for i, c in enumerate(cols)}; CFG[k] = cfg; FSHA[k] = sha(p)[:16]; DEVSHA.add(cfg["HEALTH"]["device_sha256"])
assert len(DEVSHA) == 1, DEVSHA
assert list(DEVSHA)[0] == sha(f"{ROOT}/w10_health.py"), "device sha in artifacts != f10_caliber/w10_health.py"
keys = list(D); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), ("ts mismatch", k)
SEEDIND = {cal: bool(all(np.array_equal(D[(cal, "0", "42")][c], D[(cal, "0", "2027")][c]) for c in D[(cal, "0", "42")])) for cal in CALS}
print(f"LOADED 12 artifacts; device sha256 {list(DEVSHA)[0]}; identical anchor set n={len(ts0)} first {iso(ts0[0])} last {iso(ts0[-1])}; PHI=0 seed-independence (s42 == s2027 bitwise, all rec columns): {SEEDIND}", flush=True)
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts0]); days = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in ts0])
inw = (ts0 >= T_START) & (ts0 <= T_END)
WIN = {"2024": inw & (yrs == 2024), "2025": inw & (yrs == 2025), "2026<=08-10": inw & (yrs == 2026), "2024->26": inw, "2025->26": inw & (yrs >= 2025)}
print("window sizes: " + ", ".join(f"{w}={int(m.sum())}" for w, m in WIN.items()), flush=True)
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
def boot(x, m):
    x = x[m]; dd = days[m]; ud, inv = np.unique(dd, return_inverse=True); nd = len(ud)
    sums = np.bincount(inv, weights=x, minlength=nd); cnts = np.bincount(inv, minlength=nd)
    rng = np.random.default_rng(SEED); idx = rng.integers(0, nd, size=(NB, nd)); means = sums[idx].sum(1) / cnts[idx].sum(1)
    return {"mean": float(x.mean()), "se": float(means.std(ddof=1)), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5)), "p_gt0": float((means > 0).mean()), "n": int(len(x)), "n_days": int(nd)}
G = {k: D[k]["net_ex"] / D[k]["gross_total"] for k in keys}
OUT = {"device_sha256": list(DEVSHA)[0], "n_anchors": int(len(ts0)), "first": iso(ts0[0]), "last": iso(ts0[-1]), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "artifact_sha16": {"/".join(k): v for k, v in FSHA.items()},
       "phi0_seed_independent": SEEDIND, "units": "g = net_ex/gross_total [bps/anchor per unit gross]; raw = net_ex [bps/anchor, unit replay book]", "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED, "rng": "fresh default_rng(seed) per cell"},
       "levels": {}, "delta_pergross": {}, "delta_raw": {}, "reading": {}}
md = []; P = md.append
P("### §2.1 Levels — arm d30_n2_c42, g = net_ex/gross_total (bps/anchor per unit gross); cell = mean · Sharpe(anchor) · maxDD(bps of g); then 2024->26 mean gross_total / w3_king / turnover per gross")
P(""); P("| caliber | PHI | seed | " + " | ".join(WIN) + " | gross | w3_king | turn/gross |"); P("|" + "---|" * (3 + len(WIN) + 3))
for cal in CALS:
    for phi in PHIS:
        for s in SEEDS:
            k = (cal, phi, s); g = G[k]; row = {}
            for w, m in WIN.items(): row[w] = {"mean": round(float(g[m].mean()), 4), "sharpe": round(sharpe(g[m]), 3), "maxDD": round(maxdd(g[m]), 1), "n": int(m.sum())}
            m = WIN["2024->26"]; row["form_2024->26"] = {"gross_total": round(float(D[k]["gross_total"][m].mean()), 4), "w3_king": round(float(D[k]["w3_king"][m].mean()), 4), "w3_fund": round(float(D[k]["w3_fund"][m].mean()), 4), "turn_per_gross": round(float((D[k]["turnover"][m] / D[k]["gross_total"][m]).mean()), 5), "netlong": round(float(D[k]["netlong"][m].mean()), 4)}
            OUT["levels"][f"{cal}/phi{phi}/s{s}"] = row; f = row["form_2024->26"]
            P(f"| {cal} | {'0.45' if phi == '045' else '0'} | s{s} | " + " | ".join(f"{row[w]['mean']:+.3f} · S{row[w]['sharpe']:+.2f} · DD{row[w]['maxDD']:.0f}" for w in WIN) + f" | {f['gross_total']:.3f} | {f['w3_king']:.3f} | {f['turn_per_gross']:.4f} |")
for nm, series, title in (("delta_pergross", G, "PRIMARY: Δ = g(PHI 0.45) − g(PHI 0), g = net_ex/gross_total (bps/anchor per unit gross)"), ("delta_raw", {k: D[k]["net_ex"] for k in keys}, "SECONDARY (device scale): Δ = net_ex(0.45) − net_ex(0) (bps/anchor, unit replay book)")):
    P(""); P(f"### §2.2{'a' if nm == 'delta_pergross' else 'b'} V2MAIN contribution — {title}; paired anchors; UTC-day-block bootstrap 2000 seed 20260905; cell = Δ ± s.e. [CI95] P(Δ>0)")
    P(""); P("| caliber (label) | seed | " + " | ".join(WIN) + " | ΔSharpe 24on / 25on | Δturn% 24on |"); P("|" + "---|" * (2 + len(WIN) + 2))
    for cal in CALS:
        for s in SEEDS:
            k1 = (cal, "045", s); k0 = (cal, "0", s); delta = series[k1] - series[k0]; res = {}
            for w, m in WIN.items(): res[w] = boot(delta, m)
            dsh = {w: round(sharpe(series[k1][WIN[w]]) - sharpe(series[k0][WIN[w]]), 3) for w in ("2024->26", "2025->26")}
            m = WIN["2024->26"]; t1 = (D[k1]["turnover"][m] / D[k1]["gross_total"][m]).mean(); t0_ = (D[k0]["turnover"][m] / D[k0]["gross_total"][m]).mean(); dturn = round(float((t1 / t0_ - 1) * 100), 2)
            OUT[nm][f"{cal}/s{s}"] = {"windows": res, "dSharpe": dsh, "dturn_pct_2024on": dturn}
            P(f"| {cal} {LABEL[cal]} | s{s} | " + " | ".join(f"{res[w]['mean']:+.3f} ± {res[w]['se']:.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] {res[w]['p_gt0']:.2f}" for w in WIN) + f" | {dsh['2024->26']:+.2f} / {dsh['2025->26']:+.2f} | {dturn:+.1f}% |")
# frozen reading
P(""); P("### §2.3 Frozen reading (PREREG §2): per window, (i) ≈ 0 (CI95 includes 0, both seeds) AND (ii),(iii) CI95 lower bound > 0 (both seeds) ⇒ 'the 08-26/09-04 V2MAIN net ≈ 0 conclusion is affected by the one-bar window'")
P(""); P("| window | (i) log: CI includes 0 (s42/s2027) | (ii) sum1: lower>0 (s42/s2027) | (iii) prod: lower>0 (s42/s2027) | verdict |"); P("|---|---|---|---|---|")
for w in WIN:
    st = {}
    for cal in CALS:
        st[cal] = {s: OUT["delta_pergross"][f"{cal}/s{s}"]["windows"][w] for s in SEEDS}
    i_zero = all(st["log"][s]["lo"] <= 0 <= st["log"][s]["hi"] for s in SEEDS)
    ii_pos = all(st["sum1"][s]["lo"] > 0 for s in SEEDS); iii_pos = all(st["prod"][s]["lo"] > 0 for s in SEEDS)
    if i_zero and ii_pos and iii_pos: v = "AFFECTED BY ONE-BAR WINDOW: (i) ≈0, (ii) and (iii) CI>0"
    elif i_zero and not ii_pos and not iii_pos: v = "≈0 under all three calibers (not decided by the window)"
    elif not i_zero: v = "(i) itself not ≈0 (see cells)"
    else: v = "mixed: (ii) CI>0 " + str(ii_pos) + ", (iii) CI>0 " + str(iii_pos) + " (rule not met)"
    OUT["reading"][w] = {"i_includes_zero_both_seeds": i_zero, "ii_lower_gt0_both_seeds": ii_pos, "iii_lower_gt0_both_seeds": iii_pos, "verdict": v, "primary_window": w in ("2024->26", "2025->26")}
    P(f"| {w}{' (PREREG-named)' if w in ('2024->26', '2025->26') else ''} | " + " / ".join(str(st['log'][s]['lo'] <= 0 <= st['log'][s]['hi']) for s in SEEDS) + " | " + " / ".join(str(st['sum1'][s]['lo'] > 0) for s in SEEDS) + " | " + " / ".join(str(st['prod'][s]['lo'] > 0) for s in SEEDS) + f" | {v} |")
P(""); P(f"Receipts: 12 artifacts, one device sha256 {list(DEVSHA)[0][:16]}… (= f10_caliber/w10_health.py), identical anchor set n={len(ts0)} ({iso(ts0[0])} .. {iso(ts0[-1])}); PHI=0 runs seed-independent (s42 ≡ s2027 bitwise, all rec columns): {SEEDIND}")
json.dump(OUT, open(f"{ROOT}/results/s2_judge.json", "w"), indent=1)
open(f"{ROOT}/results/s2_tables.md", "w").write("\n".join(md) + "\n")
print("\n".join(md), flush=True)
print("JUDGE_DONE", flush=True)
