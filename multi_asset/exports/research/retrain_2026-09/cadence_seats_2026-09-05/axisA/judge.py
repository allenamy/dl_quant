"""judge.py — axis A frozen judge (PREREG_retrain_cadence_and_seat_rule_2026-09-05 §1). Copied and adapted from rolling_king/judge.py.
Read-only inputs; writes judge.json here.
Arm d30_n2_c42, column net_ex (bps/anchor per unit NAV, executor caliber), L-fix arm only (M829/T400/FTRIM zero, W3FIX 0.21,0,0.79, LEGS=101, LOOK=900,
WRULE=msharpe, CAL=log, FSEED=42); anchors paired by ts (asserted identical sets). Kings: pinned (K0), rollm (K1), rollm1 (K2), rollw1 (K3, if present).
Δ vs K0 for K1/K2/K3; K2−K1 = embargo cost (reported separately, not for selection); K3−K2 = cadence effect at equal embargo (auxiliary).
Windows: 2024 | 2025 | 2026<=08-10 (ts <= 2026-08-10 20:00Z, last finite F10 row) | 2026->08-30 | 2024->26 (auxiliary) | 2025->26 (PRIMARY).
Bootstrap: UTC-calendar-day blocks, 2000 resamples with replacement over days, seed 20260905, CI95 = 2.5/97.5 pct of resampled means, P = P(mean>0).
Sharpe = mean/std(ddof=1)*sqrt(2190); maxDD = max(cummax(cumsum(net_ex)) - cumsum) in bps; turnover = mean of column 'turnover';
Δturn% = (turn_x/turn_ref - 1)*100 over the PRIMARY window 2025->26 (2024->26 also printed).
Units chain (printed, not hand-computed): %/gross/yr = mean bps/anchor * 2190 anchors/yr / 100.
Frozen decision (PREREG §1): per candidate king, per caliber, primary window 2025->26: ADMIT-candidate iff BOTH calibers CI95 lower > 0 AND Δturn% <= +15;
REJECT iff EITHER caliber CI95 upper < 0 OR Δturn% > +25; else UNDECIDED. 2024->26 printed as the auxiliary read (not part of the verdict).
"""
import os, sys, json, time, calendar, hashlib
import numpy as np
ROOT = "/workspace/review_scratch/cadence_seats/axisA"; ARM = "d30_n2_c42"; NB = 2000; SEED = 20260905
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0))
CALS = {"log": "dev", "prod": "dev_alt"}
CAL_DESC = {"log": "raw Σ-simple y4 (meta), CAL=log = no transform", "prod": "compounded Π(1+r5)-1 over [E+1,E+48] (meta_newprod swap), CAL=log"}
KING_NPY = {"pinned": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "rollm": "/workspace/review_scratch/rolling_king/slow_pred_rollm.npy",
            "rollm1": f"{ROOT}/slow_pred_rollm1.npy", "rollw1": f"{ROOT}/slow_pred_rollw1.npy", "k1rep": f"{ROOT}/slow_pred_d1_testfold.npy"}
KLABEL = {"pinned": "K0 pinned (year folds)", "rollm": "K1 rollm60 (monthly, embargo 60)", "rollm1": "K2 rollm1 (monthly, embargo 1)", "rollw1": "K3 rollw1 (weekly, embargo 1)", "k1rep": "K1 replicate (D1 retrain; noise floor, not a candidate)"}
KINGS = [k for k in ("pinned", "rollm", "rollm1", "rollw1", "k1rep") if os.path.exists(f"{ROOT}/dev/probe_artifacts/w10_ablation_series_Lfix_{k}_log_s42.npz") and os.path.exists(f"{ROOT}/dev_alt/probe_artifacts/w10_ablation_series_Lfix_{k}_prod_s42.npz")]
EXPECT = {"MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "W3FIX": "0.21,0,0.79"}
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def path(king, cal): return f"{ROOT}/{CALS[cal]}/probe_artifacts/w10_ablation_series_Lfix_{king}_{cal}_s42.npz"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
D = {}; CFG = {}; SHAS = {}
for cal in CALS:
    for king in KINGS:
        p = path(king, cal)
        z = np.load(p, allow_pickle=True); cols = [str(c) for c in z["cols"]]; cfg = json.loads(str(z["config_json"])); R = z[f"{ARM}_rec"]
        assert cfg["LEGS"] == "101" and cfg["LOOK"] == 900 and cfg["WRULE"] == "msharpe" and cfg["CAL"] == "log" and abs(cfg["PHI"] - 0.45) < 1e-12, (p, cfg)
        assert cfg["FSEED"] == "42", (p, cfg["FSEED"]); assert cfg["SLOW_NPY"] == KING_NPY[king], (p, cfg["SLOW_NPY"])
        for kk, vv in EXPECT.items(): assert cfg[kk] == vv, (p, kk, cfg[kk], vv)
        D[(cal, king)] = {c: R[:, i] for i, c in enumerate(cols)}; CFG[(cal, king)] = cfg; SHAS[f"{cal}/{king}"] = {"artifact": sha(p)[:16], "slow_npy": sha(KING_NPY[king])[:16]}
keys = list(D.keys()); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), ("ts mismatch", k)
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts0]); days = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in ts0])
print(f"LOADED {len(D)} artifacts; arm {ARM}; all share identical anchor set n={len(ts0)} first {iso(ts0[0])} last {iso(ts0[-1])}; kings {KINGS}")
print("SHAS " + json.dumps(SHAS))
WIN = {"2024": yrs == 2024, "2025": yrs == 2025, "2026<=08-10": (yrs == 2026) & (ts0 <= CUT), "2026->08-30": yrs == 2026,
       "2024->26": yrs >= 2024, "2025->26": yrs >= 2025, "2024->26<=cut": (yrs >= 2024) & (ts0 <= CUT), "2025->26<=cut": (yrs >= 2025) & (ts0 <= CUT)}
print("window sizes: " + ", ".join(f"{w}={int(m.sum())}" for w, m in WIN.items()))
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
def pct_yr(mean_bps): return mean_bps * 2190 / 100.0   # bps/anchor -> %/gross/yr
rng = np.random.default_rng(SEED)
def boot(delta, m):
    x = delta[m]; dd = days[m]; ud, inv = np.unique(dd, return_inverse=True); nd = len(ud)
    sums = np.bincount(inv, weights=x, minlength=nd); cnts = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(NB, nd)); means = sums[idx].sum(1) / cnts[idx].sum(1)
    return float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), float((means > 0).mean()), int(nd)
OUT = {"arm": ARM, "n_anchors": int(len(ts0)), "cut": iso(CUT), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "kings": KINGS, "king_labels": KLABEL, "shas": SHAS,
       "units": "net_ex bps/anchor per unit NAV (executor caliber); %/gross/yr = bps/anchor*2190/100", "levels": {}, "deltas": {}, "sigma_fund": {}, "decision": {}}
LW = ("2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26")
# ───────── level tables ─────────
for cal in CALS:
    print(f"\n===== LEVELS caliber={cal} [{CAL_DESC[cal]}] arm={ARM} L-fix col=net_ex (bps/anchor); per window: mean S=Sharpe DD=maxDD(bps) | %/gross/yr by year; then 2025->26 gross / turnover / carry / cost")
    print(f"{'king':7s}| " + " | ".join(f"{w:>20s}" for w in LW) + " | %/gr/yr 24/25/26 | gross turn carry cost (25on)")
    for king in KINGS:
        d = D[(cal, king)]; row = {}
        for w, m in WIN.items():
            x = d["net_ex"][m]
            row[w] = {"n": int(m.sum()), "mean": round(float(x.mean()), 4), "pct_gross_yr": round(pct_yr(float(x.mean())), 2), "sharpe": round(sharpe(x), 3), "maxDD": round(maxdd(x), 1),
                      "worst_month_bps": None, "gross": round(float(d["gross_total"][m].mean()), 4), "w_king": round(float(d["w3_king"][m].mean()), 4), "w_fund": round(float(d["w3_fund"][m].mean()), 4),
                      "turn": round(float(d["turnover"][m].mean()), 5), "carry": round(float(d["carry_ex"][m].mean()), 4), "cost": round(float(d["cost_ex"][m].mean()), 4)}
        # worst calendar month (sum of net_ex within month, bps gross) over 2024->26
        ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in ts0]); msum = {int(k): float(d["net_ex"][(ym == k) & WIN["2024->26"]].sum()) for k in sorted(set(ym[WIN["2024->26"]].tolist()))}
        wm = min(msum, key=msum.get); row["worst_month"] = {"ym": wm, "sum_bps": round(msum[wm], 1)}
        OUT["levels"][f"{cal}/{king}"] = row; r25 = row["2025->26"]
        print(f"{king:7s}| " + " | ".join(f"{row[w]['mean']:+.3f} S{row[w]['sharpe']:+.2f} DD{row[w]['maxDD']:.0f}".rjust(20) for w in LW)
              + f" | {row['2024']['pct_gross_yr']:+.1f}/{row['2025']['pct_gross_yr']:+.1f}/{row['2026->08-30']['pct_gross_yr']:+.1f} | {r25['gross']:.3f} {r25['turn']:.5f} {r25['carry']:+.3f} {r25['cost']:.3f} worst_month {wm} {msum[wm]:+.0f}bps")
# ───────── deltas ─────────
PAIRS = [(k, "pinned", f"{k}-pinned") for k in KINGS if k not in ("pinned", "k1rep")]
if "k1rep" in KINGS and "rollm" in KINGS: PAIRS.append(("k1rep", "rollm", "k1rep-rollm (K1 replicate: LGBM-bits noise floor, auxiliary)"))
if "rollm1" in KINGS and "rollm" in KINGS: PAIRS.append(("rollm1", "rollm", "rollm1-rollm (embargo cost K2-K1)"))
if "rollw1" in KINGS and "rollm1" in KINGS: PAIRS.append(("rollw1", "rollm1", "rollw1-rollm1 (cadence at equal embargo K3-K2, auxiliary)"))
DW = ["2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26", "2024->26<=cut", "2025->26<=cut"]
for cal in CALS:
    print(f"\n===== DELTAS caliber={cal}: Δ = x − ref, net_ex bps/anchor, paired by anchor; day-block bootstrap NB={NB} seed={SEED}; cells: Δ [CI95] P(Δ>0)")
    print(f"{'pair':38s}| " + " | ".join(f"{w:>28s}" for w in DW[:6]) + " | ΔSharpe(24on/25on) Δturn%(25on/24on) maxDD ref/x(25on)")
    for kx, ky, name in PAIRS:
        delta = D[(cal, kx)]["net_ex"] - D[(cal, ky)]["net_ex"]; res = {}
        for w in DW:
            mu, lo, hi, p, nd = boot(delta, WIN[w]); res[w] = {"mean": round(mu, 4), "lo": round(lo, 4), "hi": round(hi, 4), "P>0": round(p, 4), "n_days": nd, "n": int(WIN[w].sum()), "pct_gross_yr": round(pct_yr(mu), 2)}
        dsh = {w: round(sharpe(D[(cal, kx)]["net_ex"][WIN[w]]) - sharpe(D[(cal, ky)]["net_ex"][WIN[w]]), 3) for w in ("2024->26", "2025->26")}
        dturn = {}
        for w in ("2025->26", "2024->26"):
            tx = float(D[(cal, kx)]["turnover"][WIN[w]].mean()); ty = float(D[(cal, ky)]["turnover"][WIN[w]].mean()); dturn[w] = {"turn_ref": round(ty, 5), "turn_x": round(tx, 5), "dturn_pct": round((tx / ty - 1) * 100, 2)}
        ddx = maxdd(D[(cal, kx)]["net_ex"][WIN["2025->26"]]); ddy = maxdd(D[(cal, ky)]["net_ex"][WIN["2025->26"]])
        OUT["deltas"][f"{cal}/{name}"] = {"x": kx, "ref": ky, "windows": res, "dSharpe": dsh, "dturn": dturn, "maxDD_ref_25on": round(ddy, 1), "maxDD_x_25on": round(ddx, 1)}
        f = lambda w: f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] {res[w]['P>0']:.3f}"
        print(f"{name:38s}| " + " | ".join(f"{f(w):>28s}" for w in DW[:6]) + f" | {dsh['2024->26']:+.2f}/{dsh['2025->26']:+.2f} {dturn['2025->26']['dturn_pct']:+.1f}%/{dturn['2024->26']['dturn_pct']:+.1f}% {ddy:.0f}/{ddx:.0f}")
        print(f"{'':38s}| <=cut variants: 2024->26<=cut {f('2024->26<=cut')} | 2025->26<=cut {f('2025->26<=cut')}")
# ───────── σ_fund terciles (auxiliary) ─────────
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}; FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
sig_map = {}
for i in range(len(E_ts)):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]; f = FN[j, m]; iv = IV[j, m]; ivf = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0); ok = np.isfinite(f)
    sig_map[int(E_ts[i])] = float(np.std(f[ok] * 8.0 / ivf[ok]) * 1e4) if ok.sum() >= 50 else np.nan
sig = np.array([sig_map.get(int(t), np.nan) for t in ts0])
roll = np.full(len(ts0), np.nan)
for i in range(len(ts0)):
    w = sig[max(0, i - 29):i + 1]; v = w[np.isfinite(w)]
    if len(v) >= 15: roll[i] = v.mean()
m24 = WIN["2024->26"] & np.isfinite(roll); q1, q2 = np.nanpercentile(roll[m24], [100 / 3, 200 / 3])
ter = np.full(len(ts0), -1); ter[m24 & (roll <= q1)] = 0; ter[m24 & (roll > q1) & (roll <= q2)] = 1; ter[m24 & (roll > q2)] = 2
OUT["sigma_fund"]["definition"] = "std over meta members (finite f_fund_now) of f_fund_now*8/ivf, *1e4 bps/8h; trailing 30-anchor mean (>=15 valid); terciles over 2024->26 anchors"
OUT["sigma_fund"]["cuts_bps"] = [round(float(q1), 3), round(float(q2), 3)]; OUT["sigma_fund"]["n"] = [int((ter == t).sum()) for t in range(3)]
print(f"\n===== σ_fund TERCILES of Δ (2024->26, auxiliary): cuts {q1:.2f}/{q2:.2f} bps; n per tercile {OUT['sigma_fund']['n']}")
for cal in CALS:
    for kx, ky, name in PAIRS:
        delta = D[(cal, kx)]["net_ex"] - D[(cal, ky)]["net_ex"]; cells = []; rec = {}
        for t, nm in enumerate(("low", "mid", "high")):
            mu, lo, hi, p, nd = boot(delta, ter == t); rec[nm] = {"mean": round(mu, 4), "lo": round(lo, 4), "hi": round(hi, 4), "P>0": round(p, 4), "n": int((ter == t).sum()),
                                                                  "ref_mean": round(float(D[(cal, ky)]["net_ex"][ter == t].mean()), 4), "x_mean": round(float(D[(cal, kx)]["net_ex"][ter == t].mean()), 4)}
            cells.append(f"{nm} Δ{mu:+.3f} [{lo:+.3f},{hi:+.3f}] P{p:.2f} (ref {rec[nm]['ref_mean']:+.3f} → {rec[nm]['x_mean']:+.3f})")
        OUT["sigma_fund"][f"{cal}/{name}"] = rec
        print(f"  {cal:4s} {name:38s}: " + " | ".join(cells))
# ───────── frozen decision (PREREG §1): candidates K1/K2/K3 vs K0, primary 2025->26 ─────────
def decide(king):
    checks = {}; admit = True; reject = False
    for cal in CALS:
        dl = OUT["deltas"].get(f"{cal}/{king}-pinned")
        if dl is None: return "INCOMPLETE", {"missing": cal}
        w = dl["windows"]["2025->26"]; w24 = dl["windows"]["2024->26"]; dt = dl["dturn"]["2025->26"]["dturn_pct"]
        c = {"primary_2025->26_delta": w["mean"], "primary_CI": [w["lo"], w["hi"]], "CI_lower>0": w["lo"] > 0, "CI_upper<0": w["hi"] < 0,
             "dturn_pct_25on": dt, "turn<=+15%": dt <= 15.0, "turn>+25%": dt > 25.0,
             "aux_2024->26_delta": w24["mean"], "aux_2024->26_CI": [w24["lo"], w24["hi"]], "aux_CI_lower>0": w24["lo"] > 0,
             "yearly": [dl["windows"]["2024"]["mean"], dl["windows"]["2025"]["mean"], dl["windows"]["2026->08-30"]["mean"]]}
        checks[cal] = c
        admit &= c["CI_lower>0"] and c["turn<=+15%"]
        reject |= c["CI_upper<0"] or c["turn>+25%"]
    verdict = "REJECT" if reject else ("ADMIT-candidate" if admit else "UNDECIDED")
    return verdict, checks
for king in KINGS:
    if king in ("pinned", "k1rep"): continue
    v, c = decide(king); OUT["decision"][king] = {"verdict": v, "checks": c, "label": KLABEL[king], "rule": "PREREG §1: primary 2025->26; ADMIT iff both calibers CI95 lower>0 and Δturn<=+15%; REJECT iff either caliber CI95 upper<0 or Δturn>+25%; else UNDECIDED"}
    print(f"\n===== DECISION [{king} = {KLABEL[king]}] vs K0 (primary 2025->26, both calibers): {v}")
    for cal, cc in (c.items() if isinstance(c, dict) else []):
        print(f"  {cal}: " + "; ".join(f"{kk}={vv}" for kk, vv in cc.items()))
if "rollm1" in KINGS and "rollm" in KINGS:
    e = {cal: OUT["deltas"][f"{cal}/rollm1-rollm (embargo cost K2-K1)"]["windows"] for cal in CALS}
    OUT["decision"]["embargo_cost_K2_minus_K1"] = {cal: {w: e[cal][w] for w in ("2024", "2025", "2026->08-30", "2024->26", "2025->26")} for cal in CALS}
    print("\n===== EMBARGO COST (K2 − K1, reported separately, not for selection): " + " | ".join(f"{cal} 2025->26 {e[cal]['2025->26']['mean']:+.3f} [{e[cal]['2025->26']['lo']:+.3f},{e[cal]['2025->26']['hi']:+.3f}], 2024->26 {e[cal]['2024->26']['mean']:+.3f} [{e[cal]['2024->26']['lo']:+.3f},{e[cal]['2024->26']['hi']:+.3f}]" for cal in CALS))
json.dump(OUT, open(f"{ROOT}/judge.json", "w"), indent=1)
print(f"\nwrote {ROOT}/judge.json")
