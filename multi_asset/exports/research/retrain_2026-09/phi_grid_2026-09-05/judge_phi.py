#!/usr/bin/env python
"""judge_phi.py — PREREG_dl_monthly_gate_and_phi_grid_2026-09-05 §B (frozen before numbers): F10 weight φ grid under the accounting caliber (iii).
Arms: φ ∈ {0.25, 0.35, 0.45 (in service), 0.55, 0.65} × seeds {42, 2027}; φ = 0 shown as context (no F10 book). Everything else = health_check main arm
(U-PIT, UMASK_SCOPE=m1, LEGS=101, LOOK=900, msharpe, FTRIM=zero, fee-only COSTB_JSON, d30_n2_c42, label (iii) = meta_newprod = dlw y4s).
φ = 0.45 and φ = 0 artifacts are the f10_caliber prod runs (sha256 asserted against the archived MANIFEST values; not rerun).
PRIMARY caliber: g = net_ex / gross_total = bps/anchor per unit gross (E-0904-G units chain). SECONDARY: device scale net_ex (bps/anchor, unit replay book).
2× leverage annualised NAV (arithmetic) = mean g [bps/anchor per gross] × 6 anchors/day × 365 days × L(=2) ÷ 1e4 ⇒ %/yr  (= mean g × 43.8 %/yr per bps).
Windows: 2024 | 2025 | 2026<=08-10 (ts ≤ 2026-08-10 20:00Z, last finite F10 row) | 2024->26 | 2025->26; negative-mean cells flagged ⚠.
Paired Δ(φ − 0.45) per window: UTC-day-block bootstrap 2000, seed 20260905 (fresh generator per cell), CI95 = 2.5/97.5 pct, P = P(Δ>0), s.e. = std of resampled means.
FROZEN JUDGE (§B): a candidate φ exists ⇔ Δ(φ − 0.45) 2024->26 CI95 lower bound > 0 AND 2025->26 point estimate ≥ 0 AND turnover/gross increase ≤ +20%
(turnover window = 2024->26, the same window as the CI condition; 2025->26 also printed), for BOTH seeds, and both seeds' Δ point estimates have the same sign
(2024->26 and 2025->26). Otherwise "φ 0.45 保持". Candidates go to a prereg only; nothing is deployed here. Forbidden: choosing φ on 2026 alone; label (i) as primary.
"""
import numpy as np, json, time, hashlib, calendar, os
ROOT = "/workspace/review_scratch/phi_grid"; FC = "/workspace/review_scratch/f10_caliber"; NB = 2000; SEED = 20260905; L = 2.0; APY = 2190
PHIS = ["0", "025", "035", "045", "055", "065"]; PHIV = {"0": 0.0, "025": 0.25, "035": 0.35, "045": 0.45, "055": 0.55, "065": 0.65}; GRID = ["025", "035", "055", "065"]; SEEDS = ["42", "2027"]
EXPECTED = {("0", "42"): "93b927b71ba9c6a61dba39186b4423d733441aa58ffa3870b7bba26fd13793f9", ("0", "2027"): "d7e66b9607ef2412af360dde3ccaf9ef4fd8157a937adb4e1f8b29a905c58152",
            ("045", "42"): "53cd2d7fa7be3e00cbca3dffa15dec1d5f64085d4bb375cadd7953792cf2ae24", ("045", "2027"): "4710b1bb4d5fb5b763820d9e7d1890ff37d1e1c055b1e2bfaee0d7c4f035e79b"}   # f10_caliber MANIFEST.md (commit 7ceb754)
T_START = calendar.timegm((2024, 1, 1, 0, 0, 0)); T_END = calendar.timegm((2026, 8, 10, 20, 0, 0))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def path(phi, s): return (f"{FC}/dev_alt/probe_artifacts/w10_ablation_series_prod_phi{phi}_s{s}.npz" if phi in ("0", "045") else f"{ROOT}/dev_alt/probe_artifacts/w10_ablation_series_prod_phi{phi}_s{s}.npz")
D = {}; CFG = {}; FSHA = {}; DEVSHA = set()
for phi in PHIS:
    for s in SEEDS:
        p = path(phi, s); h = sha(p)
        if (phi, s) in EXPECTED: assert h == EXPECTED[(phi, s)], (p, h, EXPECTED[(phi, s)])
        z = np.load(p, allow_pickle=True); cfg = json.loads(str(z["config_json"])); cols = [str(c) for c in z["cols"]]; R = z["d30_n2_c42_rec"]
        assert cfg["CAL"] == "log" and cfg["LEGS"] == "101" and cfg["MEMBERS_TOPN"] == 829 and cfg["UMASK_SCOPE"] == "m1" and cfg["FTRIM"] == "zero" and cfg["LOOK"] == 900 and cfg["WRULE"] == "msharpe" and cfg["TRADE_TOPN"] == 0 and cfg["W3FIX"] is None, (p, cfg)
        assert abs(cfg["PHI"] - PHIV[phi]) < 1e-12 and cfg["FSEED"] == s and cfg["COSTB_JSON"].endswith("costb_fee_steady.json") and cfg["UMASK_NPZ"].endswith("umask_UPIT.npz") and cfg["SLOW_NPY"] == "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", (p, cfg["PHI"], cfg["FSEED"], cfg["COSTB_JSON"], cfg["UMASK_NPZ"], cfg["SLOW_NPY"])
        assert os.path.basename(os.path.realpath(os.path.join(os.path.dirname(os.path.dirname(p)), "pod_backup_2026-08-21", "wide_fea_hist_meta.npz"))) == "meta_newprod.npz", ("layout meta is not meta_newprod", p)
        k = (phi, s); D[k] = {c: R[:, i] for i, c in enumerate(cols)}; CFG[k] = cfg; FSHA[k] = h; DEVSHA.add(cfg["HEALTH"]["device_sha256"])
assert len(DEVSHA) == 1 and list(DEVSHA)[0] == sha(f"{ROOT}/w10_health.py") == sha(f"{FC}/w10_health.py"), DEVSHA
keys = list(D); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), ("ts mismatch", k)
print(f"LOADED {len(D)} artifacts (4 anchors from f10_caliber, sha-asserted; 8 new); device sha256 {list(DEVSHA)[0]}; identical anchor set n={len(ts0)} first {iso(ts0[0])} last {iso(ts0[-1])}", flush=True)
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts0]); days = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in ts0])
inw = (ts0 >= T_START) & (ts0 <= T_END)
WIN = {"2024": inw & (yrs == 2024), "2025": inw & (yrs == 2025), "2026<=08-10": inw & (yrs == 2026), "2024->26": inw, "2025->26": inw & (yrs >= 2025)}
print("window sizes: " + ", ".join(f"{w}={int(m.sum())}" for w, m in WIN.items()), flush=True)
NAVF = APY * L / 1e4 * 100   # %/yr per (bps/anchor per gross)
print(f"UNITS: g = net_ex/gross_total [bps/anchor per unit gross]; NAV %/yr at L={L:.0f} (arithmetic) = mean g × 6 anchors/day × 365 days × {L:.0f} ÷ 1e4 × 100 = mean g × {NAVF:.1f}; 2×DD %NAV = maxDD(bps of g) × {L:.0f} / 100", flush=True)
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
def boot(x, m):
    x = x[m]; dd = days[m]; ud, inv = np.unique(dd, return_inverse=True); nd = len(ud)
    sums = np.bincount(inv, weights=x, minlength=nd); cnts = np.bincount(inv, minlength=nd)
    rng = np.random.default_rng(SEED); idx = rng.integers(0, nd, size=(NB, nd)); means = sums[idx].sum(1) / cnts[idx].sum(1)
    return {"mean": float(x.mean()), "se": float(means.std(ddof=1)), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5)), "p_gt0": float((means > 0).mean()), "n": int(len(x)), "n_days": int(nd)}
SER = {"pergross": {k: D[k]["net_ex"] / D[k]["gross_total"] for k in keys}, "raw": {k: D[k]["net_ex"] for k in keys}}
TURN = {k: D[k]["turnover"] / D[k]["gross_total"] for k in keys}
OUT = {"prereg": "docs/PREREG_dl_monthly_gate_and_phi_grid_2026-09-05.md §B (sha256 05801bb2…, commit dfbe516)", "device_sha256": list(DEVSHA)[0], "n_anchors": int(len(ts0)), "first": iso(ts0[0]), "last": iso(ts0[-1]),
       "windows": {w: int(m.sum()) for w, m in WIN.items()}, "artifact_sha256": {f"phi{phi}/s{s}": FSHA[(phi, s)] for phi in PHIS for s in SEEDS}, "artifact_path": {f"phi{phi}/s{s}": path(phi, s) for phi in PHIS for s in SEEDS},
       "units": {"pergross": "g = net_ex/gross_total [bps/anchor per unit gross]", "raw": "net_ex [bps/anchor, unit replay book]", "nav_formula": f"NAV %/yr at L={L:.0f} = mean g × 6 × 365 × {L:.0f} / 1e4 × 100 = mean g × {NAVF:.1f}", "dd2x": "2×DD %NAV = maxDD(bps of g) × 2 / 100"},
       "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED, "rng": "fresh default_rng(seed) per cell"}, "judge_rule": "candidate φ ⇔ Δ(φ−0.45) 2024->26 CI95 lower > 0 AND 2025->26 point ≥ 0 AND Δturnover/gross (2024->26) ≤ +20%, both seeds, both seeds same sign (2024->26 and 2025->26); else φ 0.45 保持",
       "levels": {}, "delta": {}, "verdict": {}}
md = []; P = md.append
for cal, title in (("pergross", "PRIMARY per-gross caliber (g = net_ex/gross_total, bps/anchor per unit gross)"), ("raw", "SECONDARY device scale (net_ex, bps/anchor, unit replay book)")):
    P(f"### §B.1{'a' if cal == 'pergross' else 'b'} Levels — {title}; arm d30_n2_c42; ⚠ = negative mean; NAV %/yr @2× = mean × {NAVF:.1f} (per-gross only)")
    P(""); P("| φ | seed | window | mean bps/anchor | Sharpe (anchor) | maxDD bps | 2×DD %NAV | turnover/gross | NAV %/yr @2× | gross_total | w3_king | n |"); P("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for phi in PHIS:
        for s in SEEDS:
            k = (phi, s); x = SER[cal][k]
            for w, m in WIN.items():
                xm = x[m]; row = {"mean": round(float(xm.mean()), 4), "negative": bool(xm.mean() < 0), "sharpe": round(sharpe(xm), 3), "maxDD_bps": round(maxdd(xm), 1), "dd2x_pctNAV": round(2 * maxdd(xm) / 100, 2) if cal == "pergross" else None,
                       "turn_per_gross": round(float(TURN[k][m].mean()), 5), "nav_pct_yr_2x": round(float(xm.mean() * NAVF), 2) if cal == "pergross" else None, "gross_total": round(float(D[k]["gross_total"][m].mean()), 4), "w3_king": round(float(D[k]["w3_king"][m].mean()), 4), "n": int(m.sum())}
                OUT["levels"][f"{cal}/phi{phi}/s{s}/{w}"] = row
                P(f"| {PHIV[phi]:.2f}{' (在役)' if phi == '045' else (' (无F10, 对照)' if phi == '0' else '')} | s{s} | {w} | {row['mean']:+.3f}{' ⚠' if row['negative'] else ''} | {row['sharpe']:+.2f} | {row['maxDD_bps']:.0f} | {row['dd2x_pctNAV'] if cal == 'pergross' else '—'} | {row['turn_per_gross']:.4f} | {row['nav_pct_yr_2x'] if cal == 'pergross' else '—'} | {row['gross_total']:.3f} | {row['w3_king']:.3f} | {row['n']} |")
    P("")
    P(f"### §B.2{'a' if cal == 'pergross' else 'b'} Δ(φ − 0.45) — {title}; paired anchors; UTC-day-block bootstrap {NB}, seed {SEED}; cell = Δ ± s.e. [CI95] P(Δ>0)")
    P(""); P("| φ | seed | " + " | ".join(WIN) + " | ΔSharpe 24on / 25on | Δturn/gross % 24on / 25on |"); P("|" + "---|" * (2 + len(WIN) + 2))
    for phi in PHIS:
        if phi == "045": continue
        for s in SEEDS:
            k1 = (phi, s); k0 = ("045", s); delta = SER[cal][k1] - SER[cal][k0]; res = {w: boot(delta, m) for w, m in WIN.items()}
            dsh = {w: round(sharpe(SER[cal][k1][WIN[w]]) - sharpe(SER[cal][k0][WIN[w]]), 3) for w in ("2024->26", "2025->26")}
            dturn = {w: round(float((TURN[k1][WIN[w]].mean() / TURN[k0][WIN[w]].mean() - 1) * 100), 2) for w in ("2024->26", "2025->26")}
            OUT["delta"][f"{cal}/phi{phi}/s{s}"] = {"windows": res, "dSharpe": dsh, "dturn_pct": dturn}
            P(f"| {PHIV[phi]:.2f}{' (对照)' if phi == '0' else ''} | s{s} | " + " | ".join(f"{res[w]['mean']:+.3f} ± {res[w]['se']:.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] {res[w]['p_gt0']:.2f}" for w in WIN) + f" | {dsh['2024->26']:+.2f} / {dsh['2025->26']:+.2f} | {dturn['2024->26']:+.1f}% / {dturn['2025->26']:+.1f}% |")
    P("")
# frozen verdict (primary caliber, grid φ only)
P("### §B.3 Frozen judge (PREREG §B) — per-gross caliber; candidate ⇔ lower95(Δ 2024->26) > 0 AND Δ(2025->26) ≥ 0 AND Δturnover/gross(2024->26) ≤ +20%, for both seeds, both seeds same sign")
P(""); P("| φ | seed | Δ 2024->26 [CI95] | lower>0 | Δ 2025->26 | point≥0 | Δturn% 24on | ≤ +20% | seed passes |"); P("|---|---|---|---|---|---|---|---|---|")
cands = []
for phi in GRID:
    per = {}
    for s in SEEDS:
        dd = OUT["delta"][f"pergross/phi{phi}/s{s}"]; w24 = dd["windows"]["2024->26"]; w25 = dd["windows"]["2025->26"]; dt = dd["dturn_pct"]["2024->26"]
        c1 = w24["lo"] > 0; c2 = w25["mean"] >= 0; c3 = dt <= 20.0; per[s] = {"lower_gt0": c1, "point25_ge0": c2, "turn_le20": c3, "pass": bool(c1 and c2 and c3), "d24": w24["mean"], "d25": w25["mean"], "lo24": w24["lo"], "hi24": w24["hi"], "dturn24": dt}
        P(f"| {PHIV[phi]:.2f} | s{s} | {w24['mean']:+.3f} [{w24['lo']:+.3f},{w24['hi']:+.3f}] | {c1} | {w25['mean']:+.3f} | {c2} | {dt:+.1f}% | {c3} | **{per[s]['pass']}** |")
    same = (np.sign(per["42"]["d24"]) == np.sign(per["2027"]["d24"])) and (np.sign(per["42"]["d25"]) == np.sign(per["2027"]["d25"]))
    ok = bool(per["42"]["pass"] and per["2027"]["pass"] and same); OUT["verdict"][f"phi{phi}"] = {"per_seed": per, "both_seeds_same_sign": bool(same), "candidate": ok}
    if ok: cands.append(PHIV[phi])
OUT["verdict"]["candidates"] = cands; OUT["verdict"]["final"] = ("候选 φ = " + ", ".join(f"{c:.2f}" for c in cands) + "(只进预注册, 不直接换装)") if cands else "φ 0.45 保持(无 φ 同时满足三条件于双种子)"
P(""); P(f"**Verdict (frozen rule, primary caliber): {OUT['verdict']['final']}**")
P(""); P(f"Receipts: 12 artifacts, one device sha256 {list(DEVSHA)[0][:16]}… (= phi_grid/w10_health.py = f10_caliber/w10_health.py = health_check); anchors φ=0 / φ=0.45 reused from f10_caliber with sha256 asserted ({', '.join(f'phi{p}/s{s}={EXPECTED[(p, s)][:8]}…' for (p, s) in EXPECTED)}); identical anchor set n={len(ts0)} ({iso(ts0[0])} .. {iso(ts0[-1])}); label (iii) layout asserted (meta_newprod) for all 12.")
json.dump(OUT, open(f"{ROOT}/results/phi_judge.json", "w"), indent=1)
open(f"{ROOT}/results/phi_tables.md", "w").write("\n".join(md) + "\n")
print("\n".join(md), flush=True)
print("JUDGE_PHI_DONE", flush=True)
