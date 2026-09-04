"""judge.py — STEP 4 frozen judge (PREREG_rolling_king_monthly_2026-09-05 §3). Read-only inputs; writes judge.json here.
Arm d30_n2_c42, column net_ex (bps/anchor per unit NAV, executor caliber), anchors paired by ts (asserted identical sets).
Δ = king_source − pinned. Windows: 2024 | 2025 | 2026<=08-10 (ts <= 2026-08-10 20:00Z, last finite F10 row) | 2026->08-30 (all 2026) |
2024->26 (2024-01-01 .. 2026-08-30 20:00Z, PRIMARY for the frozen criteria) | 2025->26; the "<=cut" variants of the pooled windows are printed too.
Bootstrap: UTC-calendar-day blocks, 2000 resamples with replacement over days, seed 20260905, CI95 = 2.5/97.5 pct of resampled means, P = P(mean>0).
Sharpe = mean/std(ddof=1)*sqrt(2190); maxDD = max(cummax(cumsum(net_ex)) - cumsum) in bps; turnover = mean of column 'turnover'; Δturn% = (turn_x/turn_pinned - 1)*100.
σ_fund (stated definition): per anchor, over META members m with finite f_fund_now: std( f_fund_now*8/ivf ) *1e4 (bps per 8h), ivf = f_fund_iv if finite&>0 else 8;
  then trailing 30-anchor mean over the replayed anchor sequence (>=15 valid); terciles = 33.33/66.67 percentiles over the 2024->26 anchors.
Frozen decision (per §3): ADMIT iff for BOTH calibers: L-fix 2024->26 CI95 lower > 0 AND L-fix 2025->26 Δ >= 0 AND min over {2024, 2025, 2026->08-30} of L-fix Δ >= -0.05
  AND L-fix Δturn% (2024->26) <= +15 AND L-dyn 2024->26 Δ >= 0 for both seeds (same sign, non-negative).
  REJECT iff for EITHER caliber: L-fix 2024->26 CI95 upper < 0 OR L-fix Δturn% > +25. Else UNDECIDED.
"""
import os, sys, json, time, calendar, hashlib
import numpy as np
ROOT = "/workspace/review_scratch/rolling_king"; ARM = "d30_n2_c42"; NB = 2000; SEED = 20260905
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0))
CALS = {"log": "dev", "prod": "dev_alt"}
CAL_DESC = {"log": "raw Σ-simple y4 (meta), CAL=log = no transform", "prod": "compounded Π(1+r5)-1 over [E+1,E+48] (meta_newprod swap), CAL=log"}
ARMS = {"Lfix": ["s42"], "Ldyn": ["s42", "s2027"], "Cdyn": ["s42"]}
KINGS = [k for k in ("pinned", "rollm", "rollq") if os.path.exists(f"{ROOT}/dev/probe_artifacts/w10_ablation_series_Lfix_{k}_log_s42.npz")]
KING_NPY = {"pinned": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "rollm": f"{ROOT}/slow_pred_rollm.npy", "rollq": f"{ROOT}/slow_pred_rollq.npy"}
EXPECT = {"Lfix": {"MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "W3FIX": "0.21,0,0.79"},
          "Ldyn": {"MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "W3FIX": None},
          "Cdyn": {"MEMBERS_TOPN": 0, "TRADE_TOPN": 0, "FTRIM": "off", "W3FIX": None}}
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def path(arm, king, cal, seed): return f"{ROOT}/{CALS[cal]}/probe_artifacts/w10_ablation_series_{arm}_{king}_{cal}_{seed}.npz"
D = {}; CFG = {}
for arm, seeds in ARMS.items():
    for seed in seeds:
        for cal in CALS:
            for king in KINGS:
                p = path(arm, king, cal, seed)
                if not os.path.exists(p): print(f"MISSING {p}"); continue
                z = np.load(p, allow_pickle=True); cols = [str(c) for c in z["cols"]]; cfg = json.loads(str(z["config_json"])); R = z[f"{ARM}_rec"]
                assert cfg["LEGS"] == "101" and cfg["LOOK"] == 900 and cfg["WRULE"] == "msharpe" and cfg["CAL"] == "log" and abs(cfg["PHI"] - 0.45) < 1e-12, (p, cfg)
                assert cfg["FSEED"] == seed[1:], (p, cfg["FSEED"]); assert cfg["SLOW_NPY"] == KING_NPY[king], (p, cfg["SLOW_NPY"])
                for kk, vv in EXPECT[arm].items(): assert cfg[kk] == vv, (p, kk, cfg[kk], vv)
                D[(arm, seed, cal, king)] = {c: R[:, i] for i, c in enumerate(cols)}; CFG[(arm, seed, cal, king)] = cfg
keys = list(D.keys()); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), ("ts mismatch", k)
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts0]); days = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in ts0])
print(f"LOADED {len(D)} artifacts; arm {ARM}; all share identical anchor set n={len(ts0)} first {iso(ts0[0])} last {iso(ts0[-1])}; kings {KINGS}")
WIN = {"2024": yrs == 2024, "2025": yrs == 2025, "2026<=08-10": (yrs == 2026) & (ts0 <= CUT), "2026->08-30": yrs == 2026,
       "2024->26": yrs >= 2024, "2025->26": yrs >= 2025, "2024->26<=cut": (yrs >= 2024) & (ts0 <= CUT), "2025->26<=cut": (yrs >= 2025) & (ts0 <= CUT)}
print("window sizes: " + ", ".join(f"{w}={int(m.sum())}" for w, m in WIN.items()))
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
rng = np.random.default_rng(SEED)
def boot(delta, m):
    x = delta[m]; dd = days[m]; ud, inv = np.unique(dd, return_inverse=True); nd = len(ud)
    sums = np.bincount(inv, weights=x, minlength=nd); cnts = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(NB, nd)); means = sums[idx].sum(1) / cnts[idx].sum(1)
    return float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), float((means > 0).mean()), int(nd)
OUT = {"arm": ARM, "n_anchors": int(len(ts0)), "cut": iso(CUT), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "kings": KINGS, "levels": {}, "deltas": {}, "sigma_fund": {}, "decision": {}}
# ───────── level tables ─────────
for cal in CALS:
    print(f"\n===== LEVELS caliber={cal} [{CAL_DESC[cal]}] arm={ARM} col=net_ex (bps/anchor); per window: mean S=Sharpe DD=maxDD(bps); then 2024->26 gross / w3_king / w3_fund / turnover")
    print(f"{'arm':6s}{'seed':6s}{'king':7s}| " + " | ".join(f"{w:>20s}" for w in ("2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26")) + " | gross w_king w_fund turn")
    for arm, seeds in ARMS.items():
        for seed in seeds:
            for king in KINGS:
                k = (arm, seed, cal, king)
                if k not in D: continue
                d = D[k]; row = {}
                for w, m in WIN.items():
                    x = d["net_ex"][m]
                    row[w] = {"n": int(m.sum()), "mean": round(float(x.mean()), 4), "sharpe": round(sharpe(x), 3), "maxDD": round(maxdd(x), 1),
                              "gross": round(float(d["gross_total"][m].mean()), 4), "w_king": round(float(d["w3_king"][m].mean()), 4), "w_fund": round(float(d["w3_fund"][m].mean()), 4),
                              "turn": round(float(d["turnover"][m].mean()), 5), "carry": round(float(d["carry_ex"][m].mean()), 4), "cost": round(float(d["cost_ex"][m].mean()), 4)}
                OUT["levels"][f"{cal}/{arm}/{seed}/{king}"] = row; r24 = row["2024->26"]
                print(f"{arm:6s}{seed:6s}{king:7s}| " + " | ".join(f"{row[w]['mean']:+.3f} S{row[w]['sharpe']:+.2f} DD{row[w]['maxDD']:.0f}".rjust(20) for w in ("2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26")) + f" | {r24['gross']:.3f} {r24['w_king']:.3f} {r24['w_fund']:.3f} {r24['turn']:.5f}")
# ───────── deltas ─────────
DW = ["2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26", "2024->26<=cut", "2025->26<=cut"]
for cal in CALS:
    print(f"\n===== DELTAS caliber={cal}: Δ = king − pinned, net_ex bps/anchor, paired by anchor; day-block bootstrap NB={NB} seed={SEED}; cells: Δ [CI95] P(Δ>0)")
    print(f"{'arm':6s}{'seed':6s}{'king':7s}| " + " | ".join(f"{w:>28s}" for w in DW[:6]) + " | ΔSharpe(24on/25on) Δturn%(24on) Δw_king(24on) maxDD pin/king(24on)")
    for arm, seeds in ARMS.items():
        for seed in seeds:
            for king in KINGS:
                if king == "pinned": continue
                kx = (arm, seed, cal, king); ky = (arm, seed, cal, "pinned")
                if kx not in D or ky not in D: continue
                delta = D[kx]["net_ex"] - D[ky]["net_ex"]; res = {}
                for w in DW:
                    mu, lo, hi, p, nd = boot(delta, WIN[w]); res[w] = {"mean": round(mu, 4), "lo": round(lo, 4), "hi": round(hi, 4), "P>0": round(p, 4), "n_days": nd, "n": int(WIN[w].sum())}
                dsh = {w: round(sharpe(D[kx]["net_ex"][WIN[w]]) - sharpe(D[ky]["net_ex"][WIN[w]]), 3) for w in ("2024->26", "2025->26")}
                tx = float(D[kx]["turnover"][WIN["2024->26"]].mean()); ty = float(D[ky]["turnover"][WIN["2024->26"]].mean()); dturn = (tx / ty - 1) * 100
                dwk = float((D[kx]["w3_king"] - D[ky]["w3_king"])[WIN["2024->26"]].mean())
                ddx = maxdd(D[kx]["net_ex"][WIN["2024->26"]]); ddy = maxdd(D[ky]["net_ex"][WIN["2024->26"]])
                OUT["deltas"][f"{cal}/{arm}/{seed}/{king}-pinned"] = {"windows": res, "dSharpe": dsh, "turn_pinned": round(ty, 5), "turn_king": round(tx, 5), "dturn_pct": round(dturn, 2), "dw_king": round(dwk, 4), "maxDD_pinned": round(ddy, 1), "maxDD_king": round(ddx, 1)}
                f = lambda w: f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] {res[w]['P>0']:.3f}"
                print(f"{arm:6s}{seed:6s}{king:7s}| " + " | ".join(f"{f(w):>28s}" for w in DW[:6]) + f" | {dsh['2024->26']:+.2f}/{dsh['2025->26']:+.2f} {dturn:+.1f}% {dwk:+.3f} {ddy:.0f}/{ddx:.0f}")
                print(f"{'':19s}| <=cut variants: 2024->26<=cut {f('2024->26<=cut')} | 2025->26<=cut {f('2025->26<=cut')}")
# ───────── σ_fund terciles ─────────
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
OUT["sigma_fund"]["mean_sigma_by_tercile"] = [round(float(roll[ter == t].mean()), 3) for t in range(3)]
print(f"\n===== σ_fund TERCILES of Δ (2024->26): σ_fund = {OUT['sigma_fund']['definition']}; cuts {q1:.2f}/{q2:.2f} bps; n per tercile {OUT['sigma_fund']['n']}; mean σ per tercile {OUT['sigma_fund']['mean_sigma_by_tercile']}")
for cal in CALS:
    for arm, seeds in ARMS.items():
        for seed in seeds:
            for king in KINGS:
                if king == "pinned": continue
                kx = (arm, seed, cal, king); ky = (arm, seed, cal, "pinned")
                if kx not in D or ky not in D: continue
                delta = D[kx]["net_ex"] - D[ky]["net_ex"]; cells = []; rec = {}
                for t, nm in enumerate(("low", "mid", "high")):
                    mu, lo, hi, p, nd = boot(delta, ter == t); rec[nm] = {"mean": round(mu, 4), "lo": round(lo, 4), "hi": round(hi, 4), "P>0": round(p, 4), "n": int((ter == t).sum()),
                                                                          "pinned_mean": round(float(D[ky]["net_ex"][ter == t].mean()), 4), "king_mean": round(float(D[kx]["net_ex"][ter == t].mean()), 4)}
                    cells.append(f"{nm} Δ{mu:+.3f} [{lo:+.3f},{hi:+.3f}] P{p:.2f} (pin {rec[nm]['pinned_mean']:+.3f} → {rec[nm]['king_mean']:+.3f})")
                OUT["sigma_fund"][f"{cal}/{arm}/{seed}/{king}-pinned"] = rec
                print(f"  {cal:4s} {arm:5s} {seed:6s} {king:6s}: " + " | ".join(cells))
# ───────── frozen decision (rollm only; rollq = shape check) ─────────
def decide(king):
    checks = {}; admit = True; reject = False
    for cal in CALS:
        dl = OUT["deltas"].get(f"{cal}/Lfix/s42/{king}-pinned"); d1 = OUT["deltas"].get(f"{cal}/Ldyn/s42/{king}-pinned"); d2 = OUT["deltas"].get(f"{cal}/Ldyn/s2027/{king}-pinned")
        if dl is None or d1 is None or d2 is None: return "INCOMPLETE", {"missing": cal}
        w = dl["windows"]; worst = min(w["2024"]["mean"], w["2025"]["mean"], w["2026->08-30"]["mean"])
        c = {"Lfix_2024->26_CI_lower>0": w["2024->26"]["lo"] > 0, "Lfix_2024->26_CI": [w["2024->26"]["lo"], w["2024->26"]["hi"]], "Lfix_2024->26_mean": w["2024->26"]["mean"],
             "Lfix_2025->26_delta>=0": w["2025->26"]["mean"] >= 0, "Lfix_2025->26_mean": w["2025->26"]["mean"],
             "worst_year_delta>=-0.05": worst >= -0.05, "worst_year_delta": worst, "yearly": [w["2024"]["mean"], w["2025"]["mean"], w["2026->08-30"]["mean"]],
             "turn_increase<=15%": dl["dturn_pct"] <= 15.0, "dturn_pct": dl["dturn_pct"],
             "Ldyn_both_seeds_nonneg": (d1["windows"]["2024->26"]["mean"] >= 0) and (d2["windows"]["2024->26"]["mean"] >= 0), "Ldyn_deltas": [d1["windows"]["2024->26"]["mean"], d2["windows"]["2024->26"]["mean"]],
             "REJECT_CI_upper<0": w["2024->26"]["hi"] < 0, "REJECT_turn>25%": dl["dturn_pct"] > 25.0}
        checks[cal] = c
        admit &= c["Lfix_2024->26_CI_lower>0"] and c["Lfix_2025->26_delta>=0"] and c["worst_year_delta>=-0.05"] and c["turn_increase<=15%"] and c["Ldyn_both_seeds_nonneg"]
        reject |= c["REJECT_CI_upper<0"] or c["REJECT_turn>25%"]
    verdict = "REJECT" if reject else ("ADMIT-candidate" if admit else "UNDECIDED")
    return verdict, checks
for king in KINGS:
    if king == "pinned": continue
    v, c = decide(king); OUT["decision"][king] = {"verdict": v, "checks": c, "role": "PRIMARY (frozen criteria)" if king == "rollm" else "shape check only (not for selection)"}
    print(f"\n===== DECISION [{king}] ({OUT['decision'][king]['role']}): {v}")
    for cal, cc in (c.items() if isinstance(c, dict) else []):
        print(f"  {cal}: " + "; ".join(f"{kk}={vv}" for kk, vv in cc.items()))
json.dump(OUT, open(f"{ROOT}/judge.json", "w"), indent=1)
print(f"\nwrote {ROOT}/judge.json")
