"""judge_dyn.py — AMENDMENT 2 (L-dyn addendum) judge for axis A. Copied from axisA/judge.py; arm = L-dyn (live dynamic msharpe seat, NO W3FIX,
M829/T400/FTRIM zero, LEGS=101, LOOK=900, CAL=log), seeds s42 and s2027, kings K0 pinned / K1 rollm / K2 rollm1 / K3 rollw1.
Read-only inputs; writes judge_dyn.json + ADDENDUM_tables.md here.
Arm d30_n2_c42, column net_ex (bps/anchor per unit NAV, executor caliber); anchors paired by ts (identical sets asserted). Δ = x − ref per (caliber, seed).
Pairs: K1−K0, K2−K0, K3−K0 (candidates), K2−K1 (embargo cost, separate), K3−K2 (cadence at equal embargo, auxiliary).
Windows: 2024 | 2025 | 2026<=08-10 | 2026->08-30 | 2024->26 (aux) | 2025->26 (PRIMARY). Bootstrap: UTC-day blocks, 2000 resamples, seed 20260905.
Sharpe = mean/std(ddof=1)*sqrt(2190); maxDD on cumsum (bps); Δturn% over 2025->26 (and 2024->26); %/gross/yr = bps/anchor*2190/100 (printed by script).
Seat trajectory (axisB definitions, frozen there before numbers): yearly mean w3_king; 2025->26 mean; value at 2026-08-10 20:00Z; switches = anchors where
sign(w3_king-0.5) differs from the previous anchor; jumps = |Δw3_king| >= 0.05; seat_turn = mean |Δw3_king| per anchor.
Frozen decision (AMENDMENT 2 = PREREG §1 thresholds on L-dyn): per candidate, ADMIT-candidate iff ALL FOUR cells (2 calibers × 2 seeds) have 2025->26 CI95 lower > 0
AND Δturn%(2025->26) <= +15 in all four; REJECT iff ANY cell has CI95 upper < 0 (or Δturn% > +25); else UNDECIDED.
"""
import os, sys, json, time, calendar, hashlib
import numpy as np
ROOT = "/workspace/review_scratch/cadence_seats/axisA"; ARM = "d30_n2_c42"; NB = 2000; SEED = 20260905
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0))
CALS = {"log": "dev", "prod": "dev_alt"}; SEEDS = ["s42", "s2027"]
CAL_DESC = {"log": "raw Σ-simple y4 (meta), CAL=log = no transform", "prod": "compounded Π(1+r5)-1 over [E+1,E+48] (meta_newprod swap), CAL=log"}
KING_NPY = {"pinned": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "rollm": "/workspace/review_scratch/rolling_king/slow_pred_rollm.npy",
            "rollm1": f"{ROOT}/slow_pred_rollm1.npy", "rollw1": f"{ROOT}/slow_pred_rollw1.npy"}
KLABEL = {"pinned": "K0 pinned", "rollm": "K1 rollm60", "rollm1": "K2 rollm1", "rollw1": "K3 rollw1"}
KINGS = [k for k in ("pinned", "rollm", "rollm1", "rollw1") if all(os.path.exists(f"{ROOT}/{d}/probe_artifacts/w10_ablation_series_Ldyn_{k}_{c}_{s}.npz") for c, d in CALS.items() for s in SEEDS)]
EXPECT = {"MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "W3FIX": None}
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def path(king, cal, seed): return f"{ROOT}/{CALS[cal]}/probe_artifacts/w10_ablation_series_Ldyn_{king}_{cal}_{seed}.npz"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
D = {}; SHAS = {}
for cal in CALS:
    for seed in SEEDS:
        for king in KINGS:
            p = path(king, cal, seed); z = np.load(p, allow_pickle=True); cols = [str(c) for c in z["cols"]]; cfg = json.loads(str(z["config_json"])); R = z[f"{ARM}_rec"]
            assert cfg["LEGS"] == "101" and cfg["LOOK"] == 900 and cfg["WRULE"] == "msharpe" and cfg["CAL"] == "log" and abs(cfg["PHI"] - 0.45) < 1e-12, (p, cfg)
            assert cfg["FSEED"] == seed[1:], (p, cfg["FSEED"]); assert cfg["SLOW_NPY"] == KING_NPY[king], (p, cfg["SLOW_NPY"])
            for kk, vv in EXPECT.items(): assert cfg[kk] == vv, (p, kk, cfg[kk], vv)
            D[(cal, seed, king)] = {c: R[:, i] for i, c in enumerate(cols)}; SHAS[f"{cal}/{seed}/{king}"] = sha(p)[:16]
keys = list(D.keys()); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), ("ts mismatch", k)
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts0]); days = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in ts0])
ym = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in ts0])
print(f"LOADED {len(D)} L-dyn artifacts; arm {ARM}; identical anchor set n={len(ts0)} first {iso(ts0[0])} last {iso(ts0[-1])}; kings {KINGS}; seeds {SEEDS}")
print("SHAS " + json.dumps(SHAS))
WIN = {"2024": yrs == 2024, "2025": yrs == 2025, "2026<=08-10": (yrs == 2026) & (ts0 <= CUT), "2026->08-30": yrs == 2026, "2024->26": yrs >= 2024, "2025->26": yrs >= 2025,
       "2024->26<=cut": (yrs >= 2024) & (ts0 <= CUT), "2025->26<=cut": (yrs >= 2025) & (ts0 <= CUT)}
print("window sizes: " + ", ".join(f"{w}={int(m.sum())}" for w, m in WIN.items()))
LW = ("2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26")
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
def pct_yr(b): return b * 2190 / 100.0
rng = np.random.default_rng(SEED)
def boot(delta, m):
    x = delta[m]; dd = days[m]; ud, inv = np.unique(dd, return_inverse=True); nd = len(ud)
    sums = np.bincount(inv, weights=x, minlength=nd); cnts = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(NB, nd)); means = sums[idx].sum(1) / cnts[idx].sum(1)
    return float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), float((means > 0).mean()), int(nd)
def seat_stats(w, m):
    w = w[m]; dw = np.diff(w); s = np.sign(w - 0.5)
    return {"mean_w_king": round(float(w.mean()), 4), "switches": int((s[1:] != s[:-1]).sum()), "jumps": int((np.abs(dw) >= 0.05).sum()), "seat_turn": round(float(np.abs(dw).mean()), 5) if len(dw) else float("nan"),
            "min_w_king": round(float(w.min()), 4), "max_w_king": round(float(w.max()), 4)}
OUT = {"arm": ARM, "form": "L-dyn (dynamic msharpe seat, no W3FIX; M829/T400/FTRIM zero; LEGS=101 LOOK=900; CAL=log)", "n_anchors": int(len(ts0)), "cut": iso(CUT), "windows": {w: int(m.sum()) for w, m in WIN.items()},
       "kings": KINGS, "seeds": SEEDS, "shas": SHAS, "units": "net_ex bps/anchor per unit NAV; %/gross/yr = bps/anchor*2190/100", "levels": {}, "deltas": {}, "seats": {}, "decision": {}}
MD = []
def md(s=""): MD.append(s)
# ───────── levels ─────────
md("### ADDENDUM Levels — arm d30_n2_c42, L-dyn (live dynamic msharpe seat), net_ex bps/anchor per unit NAV; cells: mean (Sharpe; maxDD bps); %/gross/yr = mean × 2190 / 100; worst calendar month (sum of net_ex, bps) over 2024→26")
for cal in CALS:
    print(f"\n===== LEVELS caliber={cal} [{CAL_DESC[cal]}] L-dyn; per window: mean S=Sharpe DD=maxDD(bps) | %/gross/yr 24/25/26 | worst month | 2025->26 gross w_king w_fund turn")
    md(f"\n**caliber {cal} = {CAL_DESC[cal]}**\n"); md("| king | seed | " + " | ".join(LW) + " | %/gross/yr 2024 / 2025 / 2026(8m ann.) | worst month (bps) | gross 25on | w_king 25on | w_fund 25on | turnover 25on |"); md("|" + "---|" * (2 + len(LW) + 5))
    for king in KINGS:
        for seed in SEEDS:
            d = D[(cal, seed, king)]; row = {}
            for w, m in WIN.items():
                x = d["net_ex"][m]
                row[w] = {"n": int(m.sum()), "mean": round(float(x.mean()), 4), "pct_gross_yr": round(pct_yr(float(x.mean())), 2), "sharpe": round(sharpe(x), 3), "maxDD": round(maxdd(x), 1),
                          "gross": round(float(d["gross_total"][m].mean()), 4), "w_king": round(float(d["w3_king"][m].mean()), 4), "w_fund": round(float(d["w3_fund"][m].mean()), 4),
                          "turn": round(float(d["turnover"][m].mean()), 5), "carry": round(float(d["carry_ex"][m].mean()), 4), "cost": round(float(d["cost_ex"][m].mean()), 4)}
            msum = {int(k): float(d["net_ex"][(ym == k) & WIN["2024->26"]].sum()) for k in sorted(set(ym[WIN["2024->26"]].tolist()))}; wm = min(msum, key=msum.get)
            row["worst_month"] = {"ym": wm, "sum_bps": round(msum[wm], 1)}; OUT["levels"][f"{cal}/{seed}/{king}"] = row; r25 = row["2025->26"]
            print(f"{king:7s}{seed:6s}| " + " | ".join(f"{row[w]['mean']:+.3f} S{row[w]['sharpe']:+.2f} DD{row[w]['maxDD']:.0f}".rjust(20) for w in LW)
                  + f" | {row['2024']['pct_gross_yr']:+.1f}/{row['2025']['pct_gross_yr']:+.1f}/{row['2026->08-30']['pct_gross_yr']:+.1f} | {wm} {msum[wm]:+.0f} | {r25['gross']:.3f} {r25['w_king']:.3f} {r25['w_fund']:.3f} {r25['turn']:.5f}")
            md(f"| {KLABEL[king]} | {seed} | " + " | ".join(f"{row[w]['mean']:+.3f} (S {row[w]['sharpe']:+.2f}; DD {row[w]['maxDD']:.0f})" for w in LW)
               + f" | {row['2024']['pct_gross_yr']:+.1f} / {row['2025']['pct_gross_yr']:+.1f} / {row['2026->08-30']['pct_gross_yr']:+.1f} | {wm} {msum[wm]:+.0f} | {r25['gross']:.3f} | {r25['w_king']:.3f} | {r25['w_fund']:.3f} | {r25['turn']:.5f} |")
# ───────── deltas ─────────
PAIRS = [(k, "pinned", f"{k}-pinned") for k in KINGS if k != "pinned"]
if "rollm1" in KINGS and "rollm" in KINGS: PAIRS.append(("rollm1", "rollm", "rollm1-rollm (embargo cost K2-K1)"))
if "rollw1" in KINGS and "rollm1" in KINGS: PAIRS.append(("rollw1", "rollm1", "rollw1-rollm1 (cadence at equal embargo K3-K2, aux)"))
DW = ["2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26", "2024->26<=cut", "2025->26<=cut"]
md("\n### ADDENDUM Deltas — paired by anchor, UTC-day-block bootstrap (2000, seed 20260905); cells: Δ bps/anchor [CI95] P(Δ>0)")
for cal in CALS:
    print(f"\n===== DELTAS caliber={cal}: Δ = x − ref, net_ex bps/anchor, paired; cells Δ [CI95] P(Δ>0)")
    md(f"\n**caliber {cal}**\n"); md("| pair | seed | " + " | ".join(LW) + " | ΔSharpe 24on / 25on | Δturnover % 25on / 24on | Δw_king 25on | maxDD ref / x (25on) |"); md("|" + "---|" * (2 + len(LW) + 4))
    for kx, ky, name in PAIRS:
        for seed in SEEDS:
            delta = D[(cal, seed, kx)]["net_ex"] - D[(cal, seed, ky)]["net_ex"]; res = {}
            for w in DW:
                mu, lo, hi, p, nd = boot(delta, WIN[w]); res[w] = {"mean": round(mu, 4), "lo": round(lo, 4), "hi": round(hi, 4), "P>0": round(p, 4), "n_days": nd, "n": int(WIN[w].sum()), "pct_gross_yr": round(pct_yr(mu), 2)}
            dsh = {w: round(sharpe(D[(cal, seed, kx)]["net_ex"][WIN[w]]) - sharpe(D[(cal, seed, ky)]["net_ex"][WIN[w]]), 3) for w in ("2024->26", "2025->26")}
            dturn = {}
            for w in ("2025->26", "2024->26"):
                tx = float(D[(cal, seed, kx)]["turnover"][WIN[w]].mean()); ty = float(D[(cal, seed, ky)]["turnover"][WIN[w]].mean()); dturn[w] = {"turn_ref": round(ty, 5), "turn_x": round(tx, 5), "dturn_pct": round((tx / ty - 1) * 100, 2)}
            dwk = float((D[(cal, seed, kx)]["w3_king"] - D[(cal, seed, ky)]["w3_king"])[WIN["2025->26"]].mean())
            ddx = maxdd(D[(cal, seed, kx)]["net_ex"][WIN["2025->26"]]); ddy = maxdd(D[(cal, seed, ky)]["net_ex"][WIN["2025->26"]])
            OUT["deltas"][f"{cal}/{seed}/{name}"] = {"x": kx, "ref": ky, "windows": res, "dSharpe": dsh, "dturn": dturn, "dw_king_25on": round(dwk, 4), "maxDD_ref_25on": round(ddy, 1), "maxDD_x_25on": round(ddx, 1)}
            f = lambda w: f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] {res[w]['P>0']:.3f}"
            print(f"{name:42s}{seed:6s}| " + " | ".join(f"{f(w):>28s}" for w in LW) + f" | {dsh['2024->26']:+.2f}/{dsh['2025->26']:+.2f} {dturn['2025->26']['dturn_pct']:+.1f}%/{dturn['2024->26']['dturn_pct']:+.1f}% Δw {dwk:+.3f} {ddy:.0f}/{ddx:.0f}")
            print(f"{'':48s}| <=cut: 2024->26<=cut {f('2024->26<=cut')} | 2025->26<=cut {f('2025->26<=cut')}")
            md(f"| {name} | {seed} | " + " | ".join(f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f}, {res[w]['hi']:+.3f}] {res[w]['P>0']:.2f}" for w in LW) + f" | {dsh['2024->26']:+.2f} / {dsh['2025->26']:+.2f} | {dturn['2025->26']['dturn_pct']:+.1f} / {dturn['2024->26']['dturn_pct']:+.1f} | {dwk:+.3f} | {ddy:.0f} / {ddx:.0f} |")
# ───────── seat trajectories ─────────
i_cut = int(np.where(ts0 == CUT)[0][0])
md("\n### ADDENDUM Seat trajectories — w3_king (production msharpe, LOOK=900): yearly mean; 2025→26 mean [min/max]; value at 2026-08-10 20:00Z; switches = sign(w_king−0.5) flips; jumps = |Δw_king| ≥ 0.05; seat_turn = mean |Δw_king| per anchor (axisB definitions)")
md("\n| king | seed | cal | 2022 | 2023 | 2024 | 2025 | 2026 | 2025→26 mean [min/max] | w_king @2026-08-10 20:00Z | switches 24on / 25on | jumps 24on / 25on | seat_turn 24on / 25on |"); md("|" + "---|" * 13)
print("\n===== SEAT TRAJECTORIES (w3_king)")
for king in KINGS:
    for seed in SEEDS:
        for cal in CALS:
            w = D[(cal, seed, king)]["w3_king"]; ymean = {int(y): round(float(w[yrs == y].mean()), 4) for y in sorted(set(yrs.tolist()))}
            s24 = seat_stats(w, WIN["2024->26"]); s25 = seat_stats(w, WIN["2025->26"]); wcut = float(w[i_cut])
            OUT["seats"][f"{cal}/{seed}/{king}"] = {"yearly_mean": ymean, "2024->26": s24, "2025->26": s25, "w_at_cut": round(wcut, 4)}
            print(f"  {king:7s}{seed:6s}{cal:5s}: " + " ".join(f"{y}={v:.3f}" for y, v in ymean.items()) + f" | 25on {s25['mean_w_king']:.3f} [{s25['min_w_king']:.3f},{s25['max_w_king']:.3f}] @cut {wcut:.3f} | switches {s24['switches']}/{s25['switches']} jumps {s24['jumps']}/{s25['jumps']} seat_turn {s24['seat_turn']:.4f}/{s25['seat_turn']:.4f}")
            md(f"| {KLABEL[king]} | {seed} | {cal} | " + " | ".join(f"{ymean.get(y, float('nan')):.3f}" for y in (2022, 2023, 2024, 2025, 2026)) + f" | {s25['mean_w_king']:.3f} [{s25['min_w_king']:.3f}/{s25['max_w_king']:.3f}] | {wcut:.3f} | {s24['switches']} / {s25['switches']} | {s24['jumps']} / {s25['jumps']} | {s24['seat_turn']:.4f} / {s25['seat_turn']:.4f} |")
# ───────── frozen decision (AMENDMENT 2) ─────────
md("\n### ADDENDUM Frozen decision (AMENDMENT 2 = PREREG §1 thresholds on L-dyn; primary 2025→26; four cells = 2 calibers × 2 seeds; ADMIT iff all four CI95 lower > 0 and Δturnover ≤ +15%; REJECT iff any cell CI95 upper < 0 or Δturnover > +25%; else UNDECIDED)")
md("\n| candidate | cell | Δ 2025→26 [CI95] | P(Δ>0) | CI lower > 0 | CI upper < 0 | Δturnover % 25on | Δw_king 25on | aux Δ 2024→26 [CI95] | yearly Δ 2024 / 2025 / 2026 | verdict |"); md("|" + "---|" * 11)
for king in KINGS:
    if king == "pinned": continue
    cells = {}; admit = True; reject = False
    for cal in CALS:
        for seed in SEEDS:
            dl = OUT["deltas"][f"{cal}/{seed}/{king}-pinned"]; w = dl["windows"]["2025->26"]; w24 = dl["windows"]["2024->26"]; dt = dl["dturn"]["2025->26"]["dturn_pct"]
            c = {"delta": w["mean"], "ci": [w["lo"], w["hi"]], "P>0": w["P>0"], "lower>0": w["lo"] > 0, "upper<0": w["hi"] < 0, "dturn_pct": dt, "turn<=15": dt <= 15.0, "turn>25": dt > 25.0, "dw_king": dl["dw_king_25on"],
                 "aux_2024->26": [w24["mean"], w24["lo"], w24["hi"]], "yearly": [dl["windows"]["2024"]["mean"], dl["windows"]["2025"]["mean"], dl["windows"]["2026->08-30"]["mean"]]}
            cells[f"{cal}/{seed}"] = c; admit &= c["lower>0"] and c["turn<=15"]; reject |= c["upper<0"] or c["turn>25"]
    verdict = "REJECT" if reject else ("ADMIT-candidate" if admit else "UNDECIDED")
    OUT["decision"][king] = {"verdict": verdict, "cells": cells, "label": KLABEL[king]}
    print(f"\n===== DECISION [{king} = {KLABEL[king]}] vs K0 under L-dyn (primary 2025->26, 2 calibers × 2 seeds): {verdict}")
    for cell, c in cells.items():
        print(f"  {cell}: Δ {c['delta']:+.4f} CI [{c['ci'][0]:+.4f},{c['ci'][1]:+.4f}] P {c['P>0']:.3f} lower>0 {c['lower>0']} upper<0 {c['upper<0']} dturn {c['dturn_pct']:+.2f}% dw_king {c['dw_king']:+.3f} aux24 {c['aux_2024->26'][0]:+.4f} [{c['aux_2024->26'][1]:+.4f},{c['aux_2024->26'][2]:+.4f}] yearly {c['yearly']}")
        md(f"| {KLABEL[king]} | {cell} | {c['delta']:+.3f} [{c['ci'][0]:+.3f}, {c['ci'][1]:+.3f}] | {c['P>0']:.2f} | {c['lower>0']} | {c['upper<0']} | {c['dturn_pct']:+.1f} | {c['dw_king']:+.3f} | {c['aux_2024->26'][0]:+.3f} [{c['aux_2024->26'][1]:+.3f}, {c['aux_2024->26'][2]:+.3f}] | {c['yearly'][0]:+.3f} / {c['yearly'][1]:+.3f} / {c['yearly'][2]:+.3f} | **{verdict}** |")
for name, label in (("rollm1-rollm (embargo cost K2-K1)", "Embargo cost K2 − K1 (separate, not for selection)"), ("rollw1-rollm1 (cadence at equal embargo K3-K2, aux)", "Cadence at equal embargo K3 − K2 (auxiliary)")):
    if not any(name in k for k in OUT["deltas"]): continue
    parts = []
    for cal in CALS:
        for seed in SEEDS:
            e = OUT["deltas"][f"{cal}/{seed}/{name}"]["windows"]; parts.append(f"{cal}/{seed}: 2025→26 {e['2025->26']['mean']:+.3f} [{e['2025->26']['lo']:+.3f}, {e['2025->26']['hi']:+.3f}], 2024→26 {e['2024->26']['mean']:+.3f} [{e['2024->26']['lo']:+.3f}, {e['2024->26']['hi']:+.3f}], yearly {e['2024']['mean']:+.3f}/{e['2025']['mean']:+.3f}/{e['2026->08-30']['mean']:+.3f}")
    print(f"\n===== {label}: " + " | ".join(parts)); md(f"\n**{label}:** " + "; ".join(parts))
json.dump(OUT, open(f"{ROOT}/judge_dyn.json", "w"), indent=1); open(f"{ROOT}/ADDENDUM_tables.md", "w").write("\n".join(MD) + "\n")
print(f"\nwrote {ROOT}/judge_dyn.json and {ROOT}/ADDENDUM_tables.md")
