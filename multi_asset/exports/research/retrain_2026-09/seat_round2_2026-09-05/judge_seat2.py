"""judge_seat2.py — frozen judge for seat round 2 (PREREG_seat_round2_dl_seat_and_net_2026-09-05 §2). Adapted from cadence_seats/axisB/judge_axisB.py.
Inputs (read-only): seat_round2/{dev,dev_alt}/probe_artifacts/w10_ablation_series_{arm}_{cal}_s{seed}.npz, arm ∈ B0..B6; writes judge.json + REPORT_tables.md in seat_round2/.
Arm d30_n2_c42, column net_ex (bps/anchor per unit gross, executor caliber); anchors paired by ts (identical sets asserted across ALL artifacts).
Δ = B_k − B0 per (cal, seed). Windows: 2024 | 2024-H2->26 (ts >= 2024-07-01 00:00Z) | 2025 | 2026<=08-10 (ts <= 2026-08-10 20:00Z, last finite F10 row) | 2024->26 | 2025->26 (PRIMARY).
Bootstrap: UTC-calendar-day blocks, 2000 resamples with replacement over days, seed 20260905, CI95 = 2.5/97.5 pct of resampled means, P = P(mean>0).
Sharpe = mean/std(ddof=1)*sqrt(2190); maxDD = max(cummax(cumsum(net_ex)) - cumsum) in bps per unit gross; "2× maxDD" = maxDD at gross 2.0×NAV = 2·maxDD/100 in % NAV;
  turnover = mean of column 'turnover'; Δturn% = (turn_k/turn_B0 - 1)*100 over 2025->26 (decision) and 2024->26 (printed).
Seat trajectories (frozen before any number): yearly mean w3_king (king-book seat, rec col), yearly mean w3f_f10 (F10-book seat, seat2 col), yearly mean phi_t;
  'switches' = anchors where sign(x-0.5) differs from the previous anchor; 'jumps' = |Δx| >= 0.05; phi_state counts (0 warm/const, 1 dynamic, 2 both-shp-zero fallback, 3 clipped).
σ_fund terciles of Δ: exactly axisB/judge_axisB.py (std over META members of f_fund_now*8/ivf bps/8h; trailing 30-anchor mean; terciles over 2024->26 anchors, descriptive).
Yearly tables (E-0904-B style): per arm × cell × year: mean bps/anchor, annualised %/gross (mean·2190/100), Sharpe, maxDD bps, 2× maxDD %NAV, worst calendar month (bps), n; negative years flagged ⚠.
Frozen decision (PREREG §2; four cells = {prod, log} × {42, 2027}; window 2025->26):
  REJECT iff any cell CI95 upper < 0 OR any cell Δturn% > +25;
  else ADMIT-candidate iff all four cells CI95 lower > 0 AND all four Δturn% <= +15;
  else 不变差 (not-worse) iff all four cells CI95 upper > 0 AND (#cells with point estimate >= 0) >= 3 AND all four cells maxDD(2025->26) <= 1.10 × maxDD_B0(2025->26);
  else UNDECIDED.
Best plan = ADMIT-candidate with the highest 2025->26 point estimate (four-cell mean; every cell printed); if none, 不变差 arms are listed (mechanism order B1 < B2 < B3 < B4 < B5 < B6 = PREREG table order) but NOT recommended.
"""
import os, sys, json, time, calendar, hashlib
import numpy as np
ROOT = "/workspace/review_scratch/seat_round2"; ARM = "d30_n2_c42"; NB = 2000; SEED = 20260905
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); H2 = calendar.timegm((2024, 7, 1, 0, 0, 0))
CALS = {"prod": "dev_alt", "log": "dev"}
CAL_DESC = {"log": "raw Σ-simple y4 (meta), CAL=log = no transform", "prod": "compounded Π(1+r5)-1 over [E+1,E+48] (meta_newprod swap), CAL=log"}
ARMS = ["B0", "B1", "B2", "B3", "B4", "B5", "B6"]; SEEDS = ["s42", "s2027"]
ARM_EXPECT = {"B0": {"SEATF10": 0, "SEATNET": 0, "SEATCOST_BPS": 0.0, "PHIDYN": 0}, "B1": {"SEATF10": 1, "SEATNET": 0, "SEATCOST_BPS": 0.0, "PHIDYN": 0},
              "B2": {"SEATF10": 0, "SEATNET": 1, "SEATCOST_BPS": 0.0, "PHIDYN": 0}, "B3": {"SEATF10": 0, "SEATNET": 1, "SEATCOST_BPS": 2.035, "PHIDYN": 0},
              "B4": {"SEATF10": 0, "SEATNET": 0, "SEATCOST_BPS": 0.0, "PHIDYN": 1}, "B5": {"SEATF10": 1, "SEATNET": 0, "SEATCOST_BPS": 0.0, "PHIDYN": 1},
              "B6": {"SEATF10": 1, "SEATNET": 1, "SEATCOST_BPS": 2.035, "PHIDYN": 1}}
ARM_DESC = {"B0": "in-service: gross-price seat, shared by both books, φ 0.45", "B1": "SEATF10: F10 book gets its own msharpe seat (4-leg leg returns)", "B2": "SEATNET: seat input = leg return − 4h carry of the leg's unit-gross book",
            "B3": "SEATNET + SEATCOST 2.035 bps × leg rank-book turnover", "B4": "PHIDYN: φ_t = shp_F10book/(shp_kingbook+shp_F10book) over prev 900 anchors, clip [0.2,0.8]", "B5": "B1 + B4", "B6": "B3 + B5 (all switches on)"}
EXPECT = {"MEMBERS_TOPN": 829, "TRADE_TOPN": 0, "FTRIM": "zero", "W3FIX": None, "LEGS": "101", "CAL": "log", "UMASK_SCOPE": "m1", "LOOK": 900, "WRULE": "msharpe", "KTAIL": 0, "KMOD": 0.0, "KMOD_F10": 0.0, "KMOD_AGREE": 0.0, "FUNDSCALE": 0, "FEMAT_NPZ": None, "REF_SKIP": 0,
          "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "UMASK_NPZ": "/workspace/review_scratch/health_check/masks/umask_UPIT.npz", "COSTB_JSON": "/workspace/review_scratch/health_check/calib/costb_fee_steady.json",
          "COST_B": [[1.8001, 4.5001, 0.8511], [1.799, 4.4988, 0.9246], [1.7998, 4.5002, 0.921]], "PHIDYN_LOOK": 900, "PHIDYN_CLIP": [0.2, 0.8]}
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def path(arm, cal, seed): return f"{ROOT}/{CALS[cal]}/probe_artifacts/w10_ablation_series_{arm}_{cal}_{seed}.npz"
D = {}; CFG = {}; S2 = {}; TURN = {}; LEGTS = {}; DEVSHA = set(); FILESHA = {}
for arm in ARMS:
    for cal in CALS:
        for seed in SEEDS:
            p = path(arm, cal, seed)
            if not os.path.exists(p): print(f"MISSING {p}"); continue
            z = np.load(p, allow_pickle=True); cols = [str(c) for c in z["cols"]]; cfg = json.loads(str(z["config_json"])); R = z[f"{ARM}_rec"]
            for kk, vv in EXPECT.items(): assert cfg[kk] == vv, (p, kk, cfg[kk], vv)
            assert abs(cfg["PHI"] - 0.45) < 1e-12 and cfg["FSEED"] == seed[1:], (p, cfg["PHI"], cfg["FSEED"])
            for kk, vv in ARM_EXPECT[arm].items(): assert cfg[kk] == vv, (p, arm, kk, cfg[kk], vv)
            assert cfg["SEAT2"]["PHIDYN_FALLBACK"] == 0.45 and cfg["SEAT2"]["SEATCOST_BPS"] == cfg["SEATCOST_BPS"] and cfg["SEAT2"]["PHIDYN"] == cfg["PHIDYN"], (p, cfg["SEAT2"])
            DEVSHA.add(cfg["SEAT2"]["device_sha256"])
            k = (arm, cal, seed); D[k] = {c: R[:, i] for i, c in enumerate(cols)}; CFG[k] = cfg
            s2c = [str(c) for c in z["seat2_cols"]]; S2[k] = {c: z[f"{ARM}_seat2"][:, i] for i, c in enumerate(s2c)}
            assert len(S2[k]["phi_t"]) == len(R), (p, "seat2 rows != rec rows")
            TURN[k] = z["seat2_turn"]; LEGTS[k] = z["legs_ts"].astype(np.int64); FILESHA[k] = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
assert len(DEVSHA) == 1, ("device sha differs across artifacts", DEVSHA)
keys = list(D.keys()); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), ("ts mismatch", k)
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts0]); days = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in ts0]); months = np.array([time.strftime("%Y-%m", time.gmtime(int(t))) for t in ts0])
print(f"LOADED {len(D)} artifacts; device sha256 {list(DEVSHA)[0]}; arm {ARM}; identical anchor set n={len(ts0)} first {iso(ts0[0])} last {iso(ts0[-1])}")
# B0 consistency across arms: phi_t must be exactly PHI in non-PHIDYN arms; B0/B2/B3 must have NaN F10-book seat? no — w3f is the shared seat there; check B0 phi_t == 0.45 everywhere
for k in keys:
    if CFG[k]["PHIDYN"] == 0: assert np.all(S2[k]["phi_t"] == 0.45), (k, "phi_t != PHI in a non-PHIDYN arm")
WIN = {"2024": yrs == 2024, "2024-H2->26": (ts0 >= H2), "2025": yrs == 2025, "2026<=08-10": (yrs == 2026) & (ts0 <= CUT), "2024->26": yrs >= 2024, "2025->26": yrs >= 2025}
DW6 = ["2024", "2024-H2->26", "2025", "2026<=08-10", "2024->26", "2025->26"]
print("window sizes: " + ", ".join(f"{w}={int(m.sum())}" for w, m in WIN.items()))
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
rng = np.random.default_rng(SEED)
def boot(delta, m):
    x = delta[m]; dd = days[m]; ud, inv = np.unique(dd, return_inverse=True); nd = len(ud)
    sums = np.bincount(inv, weights=x, minlength=nd); cnts = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(NB, nd)); means = sums[idx].sum(1) / cnts[idx].sum(1)
    return float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), float((means > 0).mean()), int(nd)
def traj_stats(w, m):
    w = w[m]; w = w[np.isfinite(w)]
    if len(w) < 2: return {"mean": float("nan"), "switches": 0, "jumps": 0, "turn": float("nan"), "min": float("nan"), "max": float("nan")}
    dw = np.diff(w); s = np.sign(w - 0.5)
    return {"mean": round(float(w.mean()), 4), "switches": int((s[1:] != s[:-1]).sum()), "jumps": int((np.abs(dw) >= 0.05).sum()), "turn": round(float(np.abs(dw).mean()), 5), "min": round(float(w.min()), 4), "max": round(float(w.max()), 4)}
def worst_month(x, m):
    xm = x[m]; mm = months[m]; um, inv = np.unique(mm, return_inverse=True); s = np.bincount(inv, weights=xm, minlength=len(um)); i = int(np.argmin(s)); return float(s[i]), str(um[i])
OUT = {"arm": ARM, "n_anchors": int(len(ts0)), "cut": iso(CUT), "h2_start": iso(H2), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "device_sha256": list(DEVSHA)[0], "artifact_sha16": {"/".join(k): v for k, v in FILESHA.items()},
       "arms": ARM_DESC, "levels": {}, "deltas": {}, "seats": {}, "books": {}, "turn": {}, "yearly": {}, "sigma_fund": {}, "decision": {}, "best": None}
MD = []
def md(s=""): MD.append(s)
YALL = sorted(set(yrs.tolist()))
# ───────── level tables ─────────
md("### Levels — arm d30_n2_c42, net_ex (bps/anchor per unit gross); cell = mean S=Sharpe DD=maxDD(bps); then 2025->26 gross / w3_king / w3f_f10 / phi / turnover")
for cal in CALS:
    print(f"\n===== LEVELS caliber={cal} [{CAL_DESC[cal]}] arm={ARM} col=net_ex (bps/anchor); per window: mean S=Sharpe DD=maxDD(bps); then 2025->26 gross / w3_king / w3f_f10 / phi_t / turnover")
    print(f"{'arm':4s}{'seed':6s}| " + " | ".join(f"{w:>20s}" for w in DW6) + " | gross w_king w3f_f10 phi turn")
    md(f"\n#### caliber **{cal}** = {CAL_DESC[cal]}\n"); md("| arm | seed | " + " | ".join(DW6) + " | gross | w_king | w3f_f10 | phi_t | turnover |"); md("|" + "---|" * (2 + len(DW6) + 5))
    for seed in SEEDS:
        for arm in ARMS:
            k = (arm, cal, seed)
            if k not in D: continue
            d = D[k]; s2 = S2[k]; row = {}
            for w, m in WIN.items():
                x = d["net_ex"][m]
                row[w] = {"n": int(m.sum()), "mean": round(float(x.mean()), 4), "sharpe": round(sharpe(x), 3), "maxDD": round(maxdd(x), 1), "maxDD_2x_pctNAV": round(2 * maxdd(x) / 100, 2),
                          "gross": round(float(d["gross_total"][m].mean()), 4), "w_king": round(float(d["w3_king"][m].mean()), 4), "w_fund": round(float(d["w3_fund"][m].mean()), 4),
                          "w3f_f10": round(float(np.nanmean(s2["w3f_f10"][m])), 4), "phi": round(float(s2["phi_t"][m].mean()), 4),
                          "turn": round(float(d["turnover"][m].mean()), 5), "carry": round(float(d["carry_ex"][m].mean()), 4), "cost": round(float(d["cost_ex"][m].mean()), 4)}
            OUT["levels"][f"{cal}/{seed}/{arm}"] = row; r25 = row["2025->26"]
            cells = [f"{row[w]['mean']:+.3f} S{row[w]['sharpe']:+.2f} DD{row[w]['maxDD']:.0f}" for w in DW6]
            print(f"{arm:4s}{seed:6s}| " + " | ".join(c.rjust(20) for c in cells) + f" | {r25['gross']:.3f} {r25['w_king']:.3f} {r25['w3f_f10']:.3f} {r25['phi']:.3f} {r25['turn']:.5f}")
            md(f"| {arm} | {seed} | " + " | ".join(cells) + f" | {r25['gross']:.3f} | {r25['w_king']:.3f} | {r25['w3f_f10']:.3f} | {r25['phi']:.3f} | {r25['turn']:.5f} |")
# ───────── deltas ─────────
md("\n### Deltas — Δ = B_k − B0 (net_ex, bps/anchor), paired anchors; UTC-day-block bootstrap 2000×, seed 20260905; cell = Δ [CI95] P(Δ>0); **2025->26 = PRIMARY**")
for cal in CALS:
    print(f"\n===== DELTAS caliber={cal}: Δ = arm − B0, net_ex bps/anchor, paired by anchor; day-block bootstrap NB={NB} seed={SEED}; cells: Δ [CI95] P(Δ>0)")
    print(f"{'arm':4s}{'seed':6s}| " + " | ".join(f"{w:>28s}" for w in DW6) + " | ΔSharpe(25on/24on) Δturn%(25on/24on) maxDD B0/Bk(25on) DD ratio")
    md(f"\n#### caliber **{cal}**\n"); md("| arm | seed | " + " | ".join(DW6) + " | ΔSharpe 25on/24on | Δturn% 25on/24on | maxDD B0/Bk 25on (bps) | DD ratio |"); md("|" + "---|" * (2 + len(DW6) + 4))
    for seed in SEEDS:
        for arm in ARMS[1:]:
            kx = (arm, cal, seed); ky = ("B0", cal, seed)
            if kx not in D or ky not in D: continue
            delta = D[kx]["net_ex"] - D[ky]["net_ex"]; res = {}
            for w in DW6:
                mu, lo, hi, p, nd = boot(delta, WIN[w]); res[w] = {"mean": round(mu, 4), "lo": round(lo, 4), "hi": round(hi, 4), "P>0": round(p, 4), "n_days": nd, "n": int(WIN[w].sum())}
            dsh = {w: round(sharpe(D[kx]["net_ex"][WIN[w]]) - sharpe(D[ky]["net_ex"][WIN[w]]), 3) for w in ("2024->26", "2025->26")}
            dturn = {}
            for w in ("2024->26", "2025->26"):
                tx = float(D[kx]["turnover"][WIN[w]].mean()); ty = float(D[ky]["turnover"][WIN[w]].mean()); dturn[w] = {"turn_B0": round(ty, 5), "turn_arm": round(tx, 5), "pct": round((tx / ty - 1) * 100, 2)}
            ddx = maxdd(D[kx]["net_ex"][WIN["2025->26"]]); ddy = maxdd(D[ky]["net_ex"][WIN["2025->26"]])
            ddx24 = maxdd(D[kx]["net_ex"][WIN["2024->26"]]); ddy24 = maxdd(D[ky]["net_ex"][WIN["2024->26"]])
            OUT["deltas"][f"{cal}/{seed}/{arm}-B0"] = {"windows": res, "dSharpe": dsh, "dturn": dturn, "dturn_pct_2025on": dturn["2025->26"]["pct"], "dturn_pct_2024on": dturn["2024->26"]["pct"],
                                                        "maxDD_B0_2025on": round(ddy, 1), "maxDD_arm_2025on": round(ddx, 1), "maxDD_ratio_2025on": round(ddx / ddy, 4) if ddy > 0 else float("nan"),
                                                        "maxDD_B0_2024on": round(ddy24, 1), "maxDD_arm_2024on": round(ddx24, 1)}
            f = lambda w: f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] {res[w]['P>0']:.3f}"
            print(f"{arm:4s}{seed:6s}| " + " | ".join(f"{f(w):>28s}" for w in DW6) + f" | {dsh['2025->26']:+.2f}/{dsh['2024->26']:+.2f} {dturn['2025->26']['pct']:+.1f}%/{dturn['2024->26']['pct']:+.1f}% {ddy:.0f}/{ddx:.0f} {ddx / ddy:.3f}")
            md(f"| {arm} | {seed} | " + " | ".join((f"**{f(w)}**" if w == "2025->26" else f(w)) for w in DW6) + f" | {dsh['2025->26']:+.2f}/{dsh['2024->26']:+.2f} | {dturn['2025->26']['pct']:+.1f}%/{dturn['2024->26']['pct']:+.1f}% | {ddy:.0f}/{ddx:.0f} | {ddx / ddy:.3f} |")
# ───────── seat / φ trajectories ─────────
md("\n### Seat trajectories — yearly means of w3_king (king-book seat), w3f_f10 (F10-book seat: = w3_king when the seat is shared, own seat under SEATF10) and φ_t; switches = sign(x−0.5) flips, jumps = |Δx|≥0.05 (2024->26 / 2025->26)")
md("\n| arm | cal | seed | series | 2022 | 2023 | 2024 | 2025 | 2026 | 25on mean | min/max | switches 24on/25on | jumps 24on/25on | φ states warm/dyn/fallback/clipped |"); md("|" + "---|" * 14)
print("\n===== SEAT / φ TRAJECTORIES: yearly mean | switches (sign(x-0.5) flips) | jumps (|Δx|>=0.05) 24on/25on | φ state counts warm/dyn/fallback/clipped")
for arm in ARMS:
    for cal in CALS:
        for seed in SEEDS:
            k = (arm, cal, seed)
            if k not in D: continue
            rec = {}
            for nm, w in (("w3_king", D[k]["w3_king"]), ("w3f_f10", S2[k]["w3f_f10"]), ("phi_t", S2[k]["phi_t"])):
                ym = {int(y): round(float(np.nanmean(w[yrs == y])), 4) for y in YALL}; s24 = traj_stats(w, WIN["2024->26"]); s25 = traj_stats(w, WIN["2025->26"])
                st = S2[k]["phi_state"]; stc = [int((st == s).sum()) for s in (0, 1, 2, 3)] if nm == "phi_t" else None
                rec[nm] = {"yearly_mean": ym, "2024->26": s24, "2025->26": s25, "phi_state_counts": stc}
                print(f"  {arm} {cal:5s}{seed:6s}{nm:8s}: " + " ".join(f"{y}={v:.3f}" for y, v in ym.items()) + f" | 25on mean {s25['mean']:.3f} [{s25['min']:.3f},{s25['max']:.3f}] switches {s24['switches']}/{s25['switches']} jumps {s24['jumps']}/{s25['jumps']}" + (f" | φ states {stc}" if stc else ""))
                md(f"| {arm} | {cal} | {seed} | {nm} | " + " | ".join(f"{ym.get(y, float('nan')):.3f}" for y in (2022, 2023, 2024, 2025, 2026)) + f" | {s25['mean']:.3f} | {s25['min']:.3f}/{s25['max']:.3f} | {s24['switches']}/{s25['switches']} | {s24['jumps']}/{s25['jumps']} | {stc if stc else '—'} |")
            OUT["seats"][f"{cal}/{seed}/{arm}"] = rec
# ───────── per-book own net returns (PHIDYN inputs) ─────────
md("\n### Per-book own OOS net return per unit gross (bps/anchor; price − carry − cost of that book's own weights): yearly mean and Sharpe, king book vs F10 book — the PHIDYN inputs (recorded in every arm)")
md("\n| arm | cal | seed | book | 2022 | 2023 | 2024 | 2025 | 2026 | 2024->26 mean / S | 2025->26 mean / S |"); md("|" + "---|" * 11)
print("\n===== PER-BOOK own net/ug (bps/anchor): yearly mean; 2024->26 and 2025->26 mean/Sharpe")
for arm in ARMS:
    for cal in CALS:
        for seed in SEEDS:
            k = (arm, cal, seed)
            if k not in D: continue
            rec = {}
            for nm, x in (("king_book", S2[k]["netk_ug"]), ("f10_book", S2[k]["netf_ug"])):
                ym = {int(y): round(float(x[yrs == y].mean()), 4) for y in YALL}
                rec[nm] = {"yearly_mean": ym, "2024->26": {"mean": round(float(x[WIN['2024->26']].mean()), 4), "sharpe": round(sharpe(x[WIN['2024->26']]), 3)}, "2025->26": {"mean": round(float(x[WIN['2025->26']].mean()), 4), "sharpe": round(sharpe(x[WIN['2025->26']]), 3)}}
                print(f"  {arm} {cal:5s}{seed:6s}{nm:10s}: " + " ".join(f"{y}={v:+.3f}" for y, v in ym.items()) + f" | 24on {rec[nm]['2024->26']['mean']:+.3f}/S{rec[nm]['2024->26']['sharpe']:+.2f} | 25on {rec[nm]['2025->26']['mean']:+.3f}/S{rec[nm]['2025->26']['sharpe']:+.2f}")
                md(f"| {arm} | {cal} | {seed} | {nm} | " + " | ".join(f"{ym.get(y, float('nan')):+.3f}" for y in (2022, 2023, 2024, 2025, 2026)) + f" | {rec[nm]['2024->26']['mean']:+.3f} / {rec[nm]['2024->26']['sharpe']:+.2f} | {rec[nm]['2025->26']['mean']:+.3f} / {rec[nm]['2025->26']['sharpe']:+.2f} |")
            OUT["books"][f"{cal}/{seed}/{arm}"] = rec
# ───────── per-leg rank-book turnover & SEATCOST deduction ─────────
md("\n### Per-leg unit-gross rank-book turnover (unit gross per anchor, legs() sequence) and the B3 deduction 2.035·turn (bps/anchor), yearly means; leg r = seat input (B0 gross-price / B2 net-of-carry) 2025->26 → net of deduction")
md("\n| cal | seed | leg | 2022 | 2023 | 2024 | 2025 | 2026 | all | deduction 2024 / 2025 / 2026 (bps) | leg r (B0) 25on → −carry (B2) → −carry−fee (B3) |"); md("|" + "---|" * 11)
print("\n===== TURNOVER per leg (unit gross/anchor) and deduction 2.035·turn (bps/anchor), yearly means (from the B3 artifacts, legs() sequence); leg r 2025->26 B0 / B2 / B3 seat inputs")
for cal in CALS:
    for seed in SEEDS:
        k3 = ("B3", cal, seed); k0 = ("B0", cal, seed); k2 = ("B2", cal, seed)
        if k3 not in TURN: continue
        lts = LEGTS[k3]; ly = np.array([time.gmtime(int(t)).tm_year for t in lts]); T = TURN[k3]
        z0 = np.load(path("B0", cal, seed), allow_pickle=True); z2 = np.load(path("B2", cal, seed), allow_pickle=True); z3 = np.load(path("B3", cal, seed), allow_pickle=True)
        for li, leg in enumerate(("king", "rev24", "fund", "f10")):
            ym = {int(y): round(float(T[li][ly == y].mean()), 4) for y in YALL}; ded = {y: round(2.035 * ym[y], 4) for y in ym}; m25 = ly >= 2025
            if leg == "f10":
                r0 = float(z0["legs_f10"][m25].mean()); r2 = float(z2["legs_f10"][m25].mean()); r3 = float((z3["legs_f10"] - 2.035 * T[li])[m25].mean())
            else:
                r0 = float(z0[f"legs_{leg}"][m25].mean()); r2 = float(z2[f"legs_{leg}"][m25].mean()); r3 = float((z3[f"legs_{leg}"] - 2.035 * T[li])[m25].mean())
            OUT["turn"][f"{cal}/{seed}/{leg}"] = {"turn_yearly": ym, "turn_all": round(float(T[li].mean()), 4), "deduction_yearly_bps": ded, "leg_r_B0_2025on": round(r0, 4), "leg_r_B2_2025on": round(r2, 4), "leg_r_B3_2025on": round(r3, 4)}
            print(f"  {cal:5s}{seed:6s}{leg:6s}: turn " + " ".join(f"{y}={v:.4f}" for y, v in ym.items()) + f" all={T[li].mean():.4f} | deduction " + " ".join(f"{y}={v:.3f}" for y, v in ded.items()) + f" | r 25on B0 {r0:+.3f} → B2 {r2:+.3f} → B3 {r3:+.3f}" + (" (f10 leg return recorded only under SEATF10=1; B0/B2/B3 have SEATF10=0 ⇒ 0)" if leg == "f10" else ""))
            md(f"| {cal} | {seed} | {leg} | " + " | ".join(f"{ym.get(y, float('nan')):.4f}" for y in (2022, 2023, 2024, 2025, 2026)) + f" | {T[li].mean():.4f} | {ded.get(2024, float('nan')):.3f} / {ded.get(2025, float('nan')):.3f} / {ded.get(2026, float('nan')):.3f} | {r0:+.3f} → {r2:+.3f} → {r3:+.3f} |")
# f10 leg turnover/returns from the SEATF10 arms (B1) where the f10 leg is populated
for cal in CALS:
    for seed in SEEDS:
        k1 = ("B1", cal, seed); k6 = ("B6", cal, seed)
        if k1 not in TURN: continue
        lts = LEGTS[k1]; ly = np.array([time.gmtime(int(t)).tm_year for t in lts]); T = TURN[k1][3]; z1 = np.load(path("B1", cal, seed), allow_pickle=True); z6 = np.load(path("B6", cal, seed), allow_pickle=True) if k6 in TURN else None
        ym = {int(y): round(float(T[ly == y].mean()), 4) for y in YALL}; m25 = ly >= 2025
        r1 = float(z1["legs_f10"][m25].mean()); r6 = float(z6["legs_f10"][m25].mean()) if z6 is not None else float("nan"); r6n = float((z6["legs_f10"] - 2.035 * TURN[k6][3])[m25].mean()) if z6 is not None else float("nan")
        rk1 = float(z1["legs_king"][m25].mean()); rf1 = float(z1["legs_fund"][m25].mean())
        OUT["turn"][f"{cal}/{seed}/f10_from_B1"] = {"turn_yearly": ym, "turn_all": round(float(T.mean()), 4), "leg_r_f10_B1_2025on": round(r1, 4), "leg_r_f10_B6_netcarry_2025on": round(r6, 4), "leg_r_f10_B6_netcarry_netfee_2025on": round(r6n, 4), "leg_r_king_B1_2025on": round(rk1, 4), "leg_r_fund_B1_2025on": round(rf1, 4)}
        print(f"  {cal:5s}{seed:6s}f10 (from B1/B6): turn " + " ".join(f"{y}={v:.4f}" for y, v in ym.items()) + f" all={T.mean():.4f} | r 25on B1 gross {r1:+.3f} (king {rk1:+.3f}, fund {rf1:+.3f}) → B6 −carry {r6:+.3f} → −carry−fee {r6n:+.3f}")
        md(f"| {cal} | {seed} | f10 (B1/B6) | " + " | ".join(f"{ym.get(y, float('nan')):.4f}" for y in (2022, 2023, 2024, 2025, 2026)) + f" | {T.mean():.4f} | {2.035 * ym.get(2024, float('nan')):.3f} / {2.035 * ym.get(2025, float('nan')):.3f} / {2.035 * ym.get(2026, float('nan')):.3f} | B1 {r1:+.3f} (king {rk1:+.3f}, fund {rf1:+.3f}) → B6 {r6:+.3f} → {r6n:+.3f} |")
# ───────── yearly tables (E-0904-B style) ─────────
md("\n### Yearly tables (E-0904-B style) — net_ex per unit gross; ann% = mean·2190/100; maxDD in bps of gross; 2×DD = maxDD at gross 2.0×NAV in % NAV; worst calendar month (bps); ⚠ = negative year. 2022 = warm-up year (seat = 1/3 each incl. rev24 for the first 900 anchors; F10 book φ 0.45 from the first anchor); 2026 = ≤ 08-10 20Z (last finite F10 row)")
print("\n===== YEARLY TABLES (net_ex per unit gross): year | mean bps/anchor | ann %/gross | Sharpe | maxDD bps | 2×DD %NAV | worst month | n")
YW = {2022: yrs == 2022, 2023: yrs == 2023, 2024: yrs == 2024, 2025: yrs == 2025, 2026: (yrs == 2026) & (ts0 <= CUT)}
for cal in CALS:
    for seed in SEEDS:
        md(f"\n#### caliber **{cal}** seed **{seed}**\n"); md("| arm | year | mean bps/anchor | ann %/gross | Sharpe | maxDD bps | 2×DD %NAV | worst month (bps) | n |"); md("|---|---|---|---|---|---|---|---|---|")
        for arm in ARMS:
            k = (arm, cal, seed)
            if k not in D: continue
            x = D[k]["net_ex"]; rows = {}
            for y, m in YW.items():
                if not m.any(): continue
                xm = x[m]; wm, wmn = worst_month(x, m)
                rows[y] = {"mean": round(float(xm.mean()), 4), "ann_pct_gross": round(float(xm.mean() * 2190 / 100), 2), "sharpe": round(sharpe(xm), 3), "maxDD_bps": round(maxdd(xm), 1), "maxDD_2x_pctNAV": round(2 * maxdd(xm) / 100, 2), "worst_month_bps": round(wm, 1), "worst_month": wmn, "n": int(m.sum()), "negative": bool(xm.mean() < 0)}
                flag = " ⚠" if xm.mean() < 0 else ""
                print(f"  {arm} {cal:5s}{seed:6s} {y}{'≤08-10' if y == 2026 else '      '}: {xm.mean():+.3f} bps | {xm.mean() * 2190 / 100:+.1f}%/gross{flag} | S {sharpe(xm):+.2f} | DD {maxdd(xm):.0f} bps | 2×DD {2 * maxdd(xm) / 100:.1f}% NAV | worst {wm:+.0f} ({wmn}) | n {int(m.sum())}")
                md(f"| {arm} | {y}{' (≤08-10)' if y == 2026 else ''} | {xm.mean():+.3f} | {xm.mean() * 2190 / 100:+.1f}%{flag} | {sharpe(xm):+.2f} | {maxdd(xm):.0f} | {2 * maxdd(xm) / 100:.1f}% | {wm:+.0f} ({wmn}) | {int(m.sum())} |")
            for w in ("2024->26", "2025->26"):
                xm = x[WIN[w]]; wm, wmn = worst_month(x, WIN[w])
                rows[w] = {"mean": round(float(xm.mean()), 4), "ann_pct_gross": round(float(xm.mean() * 2190 / 100), 2), "sharpe": round(sharpe(xm), 3), "maxDD_bps": round(maxdd(xm), 1), "maxDD_2x_pctNAV": round(2 * maxdd(xm) / 100, 2), "worst_month_bps": round(wm, 1), "worst_month": wmn, "n": int(WIN[w].sum())}
                md(f"| {arm} | **{w}** | {xm.mean():+.3f} | {xm.mean() * 2190 / 100:+.1f}% | {sharpe(xm):+.2f} | {maxdd(xm):.0f} | {2 * maxdd(xm) / 100:.1f}% | {wm:+.0f} ({wmn}) | {int(WIN[w].sum())} |")
            OUT["yearly"][f"{cal}/{seed}/{arm}"] = rows
# ───────── σ_fund terciles (judge_axisB definition, descriptive) ─────────
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
OUT["sigma_fund"]["definition"] = "std over meta members (finite f_fund_now) of f_fund_now*8/ivf, *1e4 bps/8h; trailing 30-anchor mean (>=15 valid) over the rec sequence; terciles over 2024->26 anchors (descriptive)"
OUT["sigma_fund"]["cuts_bps"] = [round(float(q1), 3), round(float(q2), 3)]; OUT["sigma_fund"]["n"] = [int((ter == t).sum()) for t in range(3)]
OUT["sigma_fund"]["mean_sigma_by_tercile"] = [round(float(roll[ter == t].mean()), 3) for t in range(3)]
print(f"\n===== σ_fund TERCILES of Δ (2024->26): cuts {q1:.2f}/{q2:.2f} bps; n per tercile {OUT['sigma_fund']['n']}; mean σ per tercile {OUT['sigma_fund']['mean_sigma_by_tercile']}")
md(f"\n### σ_fund-tercile Δ (2024->26 anchors; cuts {q1:.2f}/{q2:.2f} bps/8h; n per tercile {OUT['sigma_fund']['n']}); cell = Δ [CI95] P (B0 mean → arm mean)")
md("\n| arm | cal | seed | low | mid | high |"); md("|---|---|---|---|---|---|")
for cal in CALS:
    for seed in SEEDS:
        for arm in ARMS[1:]:
            kx = (arm, cal, seed); ky = ("B0", cal, seed)
            if kx not in D or ky not in D: continue
            delta = D[kx]["net_ex"] - D[ky]["net_ex"]; cells = []; rec = {}
            for t, nm in enumerate(("low", "mid", "high")):
                mu, lo, hi, p, nd = boot(delta, ter == t); rec[nm] = {"mean": round(mu, 4), "lo": round(lo, 4), "hi": round(hi, 4), "P>0": round(p, 4), "n": int((ter == t).sum()),
                                                                      "B0_mean": round(float(D[ky]["net_ex"][ter == t].mean()), 4), "arm_mean": round(float(D[kx]["net_ex"][ter == t].mean()), 4)}
                cells.append(f"{mu:+.3f} [{lo:+.3f},{hi:+.3f}] P{p:.2f} ({rec[nm]['B0_mean']:+.3f}→{rec[nm]['arm_mean']:+.3f})")
            OUT["sigma_fund"][f"{cal}/{seed}/{arm}-B0"] = rec
            print(f"  {cal:4s} {seed:6s}{arm}: " + " | ".join(f"{nm} {c}" for nm, c in zip(("low", "mid", "high"), cells)))
            md(f"| {arm} | {cal} | {seed} | " + " | ".join(cells) + " |")
# ───────── frozen decision ─────────
def decide(arm):
    checks = {}; missing = []
    for cal in CALS:
        for seed in SEEDS:
            d = OUT["deltas"].get(f"{cal}/{seed}/{arm}-B0")
            if d is None: missing.append(f"{cal}/{seed}"); continue
            w = d["windows"]["2025->26"]
            checks[f"{cal}/{seed}"] = {"CI_lower>0": w["lo"] > 0, "CI_upper>0": w["hi"] > 0, "CI_upper<0": w["hi"] < 0, "point>=0": w["mean"] >= 0, "CI": [w["lo"], w["hi"]], "mean": w["mean"], "P>0": w["P>0"],
                                      "dturn_pct_2025on": d["dturn_pct_2025on"], "turn<=+15%": d["dturn_pct_2025on"] <= 15.0, "turn>+25%": d["dturn_pct_2025on"] > 25.0,
                                      "maxDD_ratio_2025on": d["maxDD_ratio_2025on"], "maxDD<=B0*1.10": d["maxDD_ratio_2025on"] <= 1.10,
                                      "aux_2024->26": d["windows"]["2024->26"]["mean"], "aux_2024->26_CI": [d["windows"]["2024->26"]["lo"], d["windows"]["2024->26"]["hi"]],
                                      "aux_2024-H2->26": d["windows"]["2024-H2->26"]["mean"], "aux_2024-H2->26_CI": [d["windows"]["2024-H2->26"]["lo"], d["windows"]["2024-H2->26"]["hi"]]}
    if missing: return "INCOMPLETE", {"missing": missing, **checks}
    cs = list(checks.values())
    reject = any(c["CI_upper<0"] for c in cs) or any(c["turn>+25%"] for c in cs)
    admit = all(c["CI_lower>0"] for c in cs) and all(c["turn<=+15%"] for c in cs)
    notworse = all(c["CI_upper>0"] for c in cs) and sum(c["point>=0"] for c in cs) >= 3 and all(c["maxDD<=B0*1.10"] for c in cs)
    v = "REJECT" if reject else ("ADMIT-candidate" if admit else ("不变差" if notworse else "UNDECIDED"))
    return v, checks
md("\n### Decisions (PREREG §2 frozen; window 2025->26; four cells {prod,log}×{42,2027}; REJECT: any CI95 upper<0 or Δturn>+25% | ADMIT: all CI95 lower>0 and Δturn≤+15% | 不变差: all CI95 upper>0, ≥3/4 point≥0, all maxDD ≤ B0×1.10 | else UNDECIDED)")
md("\n| arm | verdict | prod/s42 Δ [CI] Δturn% DDratio | prod/s2027 | log/s42 | log/s2027 | 4-cell mean Δ | aux 2024->26 (4-cell mean) | aux 2024-H2->26 (4-cell mean) |"); md("|---|---|---|---|---|---|---|---|---|")
BEST = []
for arm in ARMS[1:]:
    v, c = decide(arm); OUT["decision"][arm] = {"verdict": v, "checks": c}
    cells_ok = [cc for cc in c.values() if isinstance(cc, dict)]
    m4 = float(np.mean([cc["mean"] for cc in cells_ok])) if cells_ok else float("nan"); a24 = float(np.mean([cc["aux_2024->26"] for cc in cells_ok])) if cells_ok else float("nan"); ah2 = float(np.mean([cc["aux_2024-H2->26"] for cc in cells_ok])) if cells_ok else float("nan")
    OUT["decision"][arm]["mean4_2025on"] = round(m4, 4); OUT["decision"][arm]["mean4_2024on"] = round(a24, 4); OUT["decision"][arm]["mean4_2024H2on"] = round(ah2, 4)
    if v == "ADMIT-candidate": BEST.append((m4, arm))
    print(f"\n===== DECISION [{arm}] {ARM_DESC[arm]}: {v}  (4-cell mean Δ 2025->26 {m4:+.4f}; aux 2024->26 {a24:+.4f}; 2024-H2->26 {ah2:+.4f})")
    for kk, cc in c.items():
        if isinstance(cc, dict): print(f"  {kk}: Δ {cc['mean']:+.4f} CI [{cc['CI'][0]:+.4f},{cc['CI'][1]:+.4f}] P {cc['P>0']:.3f} Δturn {cc['dturn_pct_2025on']:+.2f}% DDratio {cc['maxDD_ratio_2025on']:.3f} | aux 2024->26 Δ {cc['aux_2024->26']:+.4f} CI [{cc['aux_2024->26_CI'][0]:+.4f},{cc['aux_2024->26_CI'][1]:+.4f}] | 2024-H2->26 Δ {cc['aux_2024-H2->26']:+.4f} CI [{cc['aux_2024-H2->26_CI'][0]:+.4f},{cc['aux_2024-H2->26_CI'][1]:+.4f}]")
    cell = lambda kk: (f"{c[kk]['mean']:+.3f} [{c[kk]['CI'][0]:+.3f},{c[kk]['CI'][1]:+.3f}] {c[kk]['dturn_pct_2025on']:+.1f}% {c[kk]['maxDD_ratio_2025on']:.2f}" if isinstance(c.get(kk), dict) else "—")
    md(f"| {arm} | **{v}** | {cell('prod/s42')} | {cell('prod/s2027')} | {cell('log/s42')} | {cell('log/s2027')} | {m4:+.4f} | {a24:+.4f} | {ah2:+.4f} |")
if BEST:
    BEST.sort(reverse=True); OUT["best"] = {"arm": BEST[0][1], "mean4_2025on": round(BEST[0][0], 4), "rule": "ADMIT-candidate with the highest 2025->26 point estimate (four-cell mean)"}
    print(f"\n===== BEST PLAN: {BEST[0][1]} ({ARM_DESC[BEST[0][1]]}) — highest 2025->26 four-cell mean Δ {BEST[0][0]:+.4f} among ADMIT candidates {[b[1] for b in BEST]}")
    md(f"\n**Best plan (PREREG §2): {BEST[0][1]}** — highest 2025->26 four-cell mean Δ {BEST[0][0]:+.4f} among ADMIT candidates {[b[1] for b in BEST]}.")
else:
    nw = [a for a in ARMS[1:] if OUT["decision"][a]["verdict"] == "不变差"]
    OUT["best"] = {"arm": None, "rule": "no ADMIT candidate; 不变差 arms listed in mechanism (PREREG table) order, NOT recommended for deployment", "notworse_arms": nw}
    print(f"\n===== BEST PLAN: none (no ADMIT candidate). 不变差 arms (mechanism order, not recommended): {nw}")
    md(f"\n**Best plan (PREREG §2): none** — no ADMIT candidate. 不变差 arms in mechanism order (reported, not recommended for deployment): {nw}.")
json.dump(OUT, open(f"{ROOT}/judge.json", "w"), indent=1, ensure_ascii=False)
open(f"{ROOT}/REPORT_tables.md", "w").write("\n".join(MD) + "\n")
print(f"\nwrote {ROOT}/judge.json and {ROOT}/REPORT_tables.md")
