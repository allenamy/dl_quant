"""judge_axisB.py — frozen judge for axis B (PREREG_retrain_cadence_and_seat_rule_2026-09-05 §2: seat rules R1..R5 vs R0). Adapted from rolling_king/judge.py.
Inputs (read-only): axisB/{dev,dev_alt}/probe_artifacts/w10_ablation_series_{rule}_{king}_{cal}_{seed}.npz; writes judge.json + REPORT_tables.md in axisB/.
Arm d30_n2_c42, column net_ex (bps/anchor per unit NAV, executor caliber); anchors paired by ts (identical sets asserted across ALL artifacts).
Δ = R_k − R0 per (king, seed, caliber). Windows: 2024 | 2025 | 2026<=08-10 (ts <= 2026-08-10 20:00Z, last finite F10 row) | 2026->08-30 | 2024->26 | 2025->26 (PRIMARY);
  the "<=cut" variants of the pooled windows are printed too.
Bootstrap: UTC-calendar-day blocks, 2000 resamples with replacement over days, seed 20260905, CI95 = 2.5/97.5 pct of resampled means, P = P(mean>0).
Sharpe = mean/std(ddof=1)*sqrt(2190); maxDD = max(cummax(cumsum(net_ex)) - cumsum) in bps; turnover = mean of column 'turnover';
  Δturn% = (turn_k/turn_R0 - 1)*100 over the PRIMARY window 2025->26 (decision) and over 2024->26 (printed).
Seat trajectory (definitions frozen before any number): yearly mean w3_king; 'switches' = anchors where sign(w3_king-0.5) differs from the previous anchor (dominant-leg switch);
  'jumps' = anchors with |Δw3_king| >= 0.05; 'seat_turn' = mean |Δw3_king| per anchor (seat turnover).
σ_fund terciles of Δ: exactly rolling_king/judge.py — per anchor std over META members with finite f_fund_now of f_fund_now*8/ivf *1e4 (bps/8h), trailing 30-anchor mean over the
  replayed rec sequence (>=15 valid); terciles = 33.33/66.67 pct over the 2024->26 anchors (descriptive; the R5 device uses causal expanding cuts — the max |diff| between the
  device's σ_fund series and this one on common anchors is printed as a receipt).
Frozen decision (PREREG §2; PRIMARY = K1 rollm, window 2025->26): per rule, ADMIT-candidate iff for BOTH calibers and BOTH seeds CI95 lower > 0 AND Δturn%(2025->26) <= +15;
  REJECT iff for ANY caliber (either seed) CI95 upper < 0; else UNDECIDED. The same evaluation for K0 pinned is printed as SECONDARY (not for selection).
"""
import os, sys, json, time, calendar, hashlib
import numpy as np
ROOT = "/workspace/review_scratch/cadence_seats/axisB"; ARM = "d30_n2_c42"; NB = 2000; SEED = 20260905
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0))
CALS = {"log": "dev", "prod": "dev_alt"}
CAL_DESC = {"log": "raw Σ-simple y4 (meta), CAL=log = no transform", "prod": "compounded Π(1+r5)-1 over [E+1,E+48] (meta_newprod swap), CAL=log"}
RULES = ["R0", "R1", "R2", "R3", "R4", "R5"]
RULE_EXPECT = {"R0": {"WRULE": "msharpe", "LOOK": 900}, "R1": {"WRULE": "msharpe", "LOOK": 300}, "R2": {"WRULE": "msharpe_net", "LOOK": 900},
               "R3": {"WRULE": "shrink", "LOOK": 900}, "R4": {"WRULE": "meanvar", "LOOK": 900}, "R5": {"WRULE": "regime", "LOOK": 900}}
RULE_DESC = {"R0": "msharpe LOOK 900 (production)", "R1": "msharpe LOOK 300", "R2": "msharpe_net: r − 3.52·turn, LOOK 900", "R3": "shrink 0.5·[0.5,0,0.5] + 0.5·msharpe900",
             "R4": "meanvar (2-leg, ridge 1e-3·mean var), LOOK 900", "R5": "regime: msharpe over last 900 same-σ_fund-tercile anchors (causal cuts; <300 ⇒ msharpe900)"}
KINGS = ["rollm", "pinned"]; SEEDS = ["s42", "s2027"]
KING_NPY = {"pinned": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "rollm": "/workspace/review_scratch/rolling_king/slow_pred_rollm.npy"}
EXPECT = {"MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "W3FIX": None, "LEGS": "101", "CAL": "log"}
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
def path(rule, king, cal, seed): return f"{ROOT}/{CALS[cal]}/probe_artifacts/w10_ablation_series_{rule}_{king}_{cal}_{seed}.npz"
D = {}; CFG = {}; AX = {}; DEVSHA = set(); FILESHA = {}
for rule in RULES:
    for king in KINGS:
        for cal in CALS:
            for seed in SEEDS:
                p = path(rule, king, cal, seed)
                if not os.path.exists(p): print(f"MISSING {p}"); continue
                z = np.load(p, allow_pickle=True); cols = [str(c) for c in z["cols"]]; cfg = json.loads(str(z["config_json"])); R = z[f"{ARM}_rec"]
                for kk, vv in EXPECT.items(): assert cfg[kk] == vv, (p, kk, cfg[kk], vv)
                assert abs(cfg["PHI"] - 0.45) < 1e-12 and cfg["FSEED"] == seed[1:] and cfg["SLOW_NPY"] == KING_NPY[king], (p, cfg["PHI"], cfg["FSEED"], cfg["SLOW_NPY"])
                for kk, vv in RULE_EXPECT[rule].items(): assert cfg[kk] == vv, (p, kk, cfg[kk], vv)
                ax = cfg["AXISB"]; DEVSHA.add(ax["device_sha256"])
                assert ax["kappa_turn_bps"] == 3.52 and ax["shrink_lambda"] == 0.5 and ax["mv_ridge_frac"] == 1e-3 and ax["mv_mask_order"] == "first" and ax["regime_look"] == 900 and ax["regime_min"] == 300, (p, ax)
                k = (rule, king, cal, seed); D[k] = {c: R[:, i] for i, c in enumerate(cols)}; CFG[k] = cfg
                AX[k] = {kk: z[kk] for kk in z.files if kk.startswith("axisb_")}; FILESHA[k] = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
assert len(DEVSHA) == 1, ("device sha differs across artifacts", DEVSHA)
keys = list(D.keys()); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), ("ts mismatch", k)
yrs = np.array([time.gmtime(int(t)).tm_year for t in ts0]); days = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in ts0])
print(f"LOADED {len(D)} artifacts; device sha256 {list(DEVSHA)[0]}; arm {ARM}; identical anchor set n={len(ts0)} first {iso(ts0[0])} last {iso(ts0[-1])}")
WIN = {"2024": yrs == 2024, "2025": yrs == 2025, "2026<=08-10": (yrs == 2026) & (ts0 <= CUT), "2026->08-30": yrs == 2026,
       "2024->26": yrs >= 2024, "2025->26": yrs >= 2025, "2024->26<=cut": (yrs >= 2024) & (ts0 <= CUT), "2025->26<=cut": (yrs >= 2025) & (ts0 <= CUT)}
DW6 = ["2024", "2025", "2026<=08-10", "2026->08-30", "2024->26", "2025->26"]
print("window sizes: " + ", ".join(f"{w}={int(m.sum())}" for w, m in WIN.items()))
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
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
OUT = {"arm": ARM, "n_anchors": int(len(ts0)), "cut": iso(CUT), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "device_sha256": list(DEVSHA)[0], "artifact_sha16": {"/".join(k): v for k, v in FILESHA.items()},
       "rules": RULE_DESC, "levels": {}, "deltas": {}, "seats": {}, "sigma_fund": {}, "r2_turn": {}, "r5_fallback": {}, "decision": {}}
MD = []
def md(s=""): MD.append(s)
# ───────── level tables ─────────
md("### Levels — arm d30_n2_c42, net_ex (bps/anchor per unit NAV); cell = mean S=Sharpe DD=maxDD(bps); gross / w_king / w_fund / turnover over 2025->26")
for cal in CALS:
    print(f"\n===== LEVELS caliber={cal} [{CAL_DESC[cal]}] arm={ARM} col=net_ex (bps/anchor); per window: mean S=Sharpe DD=maxDD(bps); then 2025->26 gross / w3_king / w3_fund / turnover")
    print(f"{'rule':5s}{'king':7s}{'seed':6s}| " + " | ".join(f"{w:>20s}" for w in DW6) + " | gross w_king w_fund turn")
    md(f"\n#### caliber **{cal}** = {CAL_DESC[cal]}\n"); md("| rule | king | seed | " + " | ".join(DW6) + " | gross | w_king | w_fund | turnover |"); md("|" + "---|" * (3 + len(DW6) + 4))
    for king in KINGS:
        for seed in SEEDS:
            for rule in RULES:
                k = (rule, king, cal, seed)
                if k not in D: continue
                d = D[k]; row = {}
                for w, m in WIN.items():
                    x = d["net_ex"][m]
                    row[w] = {"n": int(m.sum()), "mean": round(float(x.mean()), 4), "sharpe": round(sharpe(x), 3), "maxDD": round(maxdd(x), 1),
                              "gross": round(float(d["gross_total"][m].mean()), 4), "w_king": round(float(d["w3_king"][m].mean()), 4), "w_fund": round(float(d["w3_fund"][m].mean()), 4),
                              "turn": round(float(d["turnover"][m].mean()), 5), "carry": round(float(d["carry_ex"][m].mean()), 4), "cost": round(float(d["cost_ex"][m].mean()), 4)}
                OUT["levels"][f"{cal}/{king}/{seed}/{rule}"] = row; r25 = row["2025->26"]
                cells = [f"{row[w]['mean']:+.3f} S{row[w]['sharpe']:+.2f} DD{row[w]['maxDD']:.0f}" for w in DW6]
                print(f"{rule:5s}{king:7s}{seed:6s}| " + " | ".join(c.rjust(20) for c in cells) + f" | {r25['gross']:.3f} {r25['w_king']:.3f} {r25['w_fund']:.3f} {r25['turn']:.5f}")
                md(f"| {rule} | {king} | {seed} | " + " | ".join(cells) + f" | {r25['gross']:.3f} | {r25['w_king']:.3f} | {r25['w_fund']:.3f} | {r25['turn']:.5f} |")
# ───────── deltas ─────────
DW = DW6 + ["2024->26<=cut", "2025->26<=cut"]
md("\n### Deltas — Δ = R_k − R0 (net_ex, bps/anchor), paired anchors; UTC-day-block bootstrap 2000×, seed 20260905; cell = Δ [CI95] P(Δ>0); **2025->26 = PRIMARY**")
for cal in CALS:
    print(f"\n===== DELTAS caliber={cal}: Δ = rule − R0, net_ex bps/anchor, paired by anchor; day-block bootstrap NB={NB} seed={SEED}; cells: Δ [CI95] P(Δ>0)")
    print(f"{'rule':5s}{'king':7s}{'seed':6s}| " + " | ".join(f"{w:>28s}" for w in DW6) + " | ΔSharpe(25on/24on) Δturn%(25on/24on) Δw_king(25on) maxDD R0/Rk(25on)")
    md(f"\n#### caliber **{cal}**\n"); md("| rule | king | seed | " + " | ".join(DW6) + " | ΔSharpe 25on/24on | Δturn% 25on/24on | Δ mean w_king 25on | maxDD R0/Rk 25on |"); md("|" + "---|" * (3 + len(DW6) + 4))
    for king in KINGS:
        for seed in SEEDS:
            for rule in RULES[1:]:
                kx = (rule, king, cal, seed); ky = ("R0", king, cal, seed)
                if kx not in D or ky not in D: continue
                delta = D[kx]["net_ex"] - D[ky]["net_ex"]; res = {}
                for w in DW:
                    mu, lo, hi, p, nd = boot(delta, WIN[w]); res[w] = {"mean": round(mu, 4), "lo": round(lo, 4), "hi": round(hi, 4), "P>0": round(p, 4), "n_days": nd, "n": int(WIN[w].sum())}
                dsh = {w: round(sharpe(D[kx]["net_ex"][WIN[w]]) - sharpe(D[ky]["net_ex"][WIN[w]]), 3) for w in ("2024->26", "2025->26")}
                dturn = {}
                for w in ("2024->26", "2025->26"):
                    tx = float(D[kx]["turnover"][WIN[w]].mean()); ty = float(D[ky]["turnover"][WIN[w]].mean()); dturn[w] = {"turn_R0": round(ty, 5), "turn_rule": round(tx, 5), "pct": round((tx / ty - 1) * 100, 2)}
                dwk = float((D[kx]["w3_king"] - D[ky]["w3_king"])[WIN["2025->26"]].mean())
                ddx = maxdd(D[kx]["net_ex"][WIN["2025->26"]]); ddy = maxdd(D[ky]["net_ex"][WIN["2025->26"]])
                OUT["deltas"][f"{cal}/{king}/{seed}/{rule}-R0"] = {"windows": res, "dSharpe": dsh, "dturn": dturn, "dturn_pct_2025on": dturn["2025->26"]["pct"], "dturn_pct_2024on": dturn["2024->26"]["pct"],
                                                                     "dw_king_2025on": round(dwk, 4), "maxDD_R0_2025on": round(ddy, 1), "maxDD_rule_2025on": round(ddx, 1)}
                f = lambda w: f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] {res[w]['P>0']:.3f}"
                print(f"{rule:5s}{king:7s}{seed:6s}| " + " | ".join(f"{f(w):>28s}" for w in DW6) + f" | {dsh['2025->26']:+.2f}/{dsh['2024->26']:+.2f} {dturn['2025->26']['pct']:+.1f}%/{dturn['2024->26']['pct']:+.1f}% {dwk:+.3f} {ddy:.0f}/{ddx:.0f}")
                print(f"{'':18s}| <=cut variants: 2024->26<=cut {f('2024->26<=cut')} | 2025->26<=cut {f('2025->26<=cut')}")
                md(f"| {rule} | {king} | {seed} | " + " | ".join((f"**{f(w)}**" if w == "2025->26" else f(w)) for w in DW6) + f" | {dsh['2025->26']:+.2f}/{dsh['2024->26']:+.2f} | {dturn['2025->26']['pct']:+.1f}%/{dturn['2024->26']['pct']:+.1f}% | {dwk:+.3f} | {ddy:.0f}/{ddx:.0f} |")
# ───────── seat trajectories ─────────
md("\n### Seat trajectories — w3_king by year (mean), switches = sign(w_king−0.5) flips, jumps = |Δw_king|≥0.05, seat_turn = mean |Δw_king| per anchor; identical across calibers only if the seat inputs are (they are not: leg returns differ by caliber), so both calibers are listed")
md("\n| rule | king | seed | cal | 2022 | 2023 | 2024 | 2025 | 2026 | 2025->26 mean | min/max w_king | switches 24on / 25on | jumps 24on / 25on | seat_turn 24on / 25on |"); md("|" + "---|" * 15)
print("\n===== SEAT TRAJECTORIES (w3_king): yearly mean | switches (sign(w-0.5) flips) | jumps (|Δw|>=0.05) | seat_turn (mean |Δw|)")
YALL = sorted(set(yrs.tolist()))
for rule in RULES:
    for king in KINGS:
        for seed in SEEDS:
            for cal in CALS:
                k = (rule, king, cal, seed)
                if k not in D: continue
                w = D[k]["w3_king"]; ym = {int(y): round(float(w[yrs == y].mean()), 4) for y in YALL}
                s24 = seat_stats(w, WIN["2024->26"]); s25 = seat_stats(w, WIN["2025->26"])
                OUT["seats"][f"{cal}/{king}/{seed}/{rule}"] = {"yearly_mean_w_king": ym, "2024->26": s24, "2025->26": s25}
                print(f"  {rule} {king:7s}{seed:6s}{cal:5s}: " + " ".join(f"{y}={v:.3f}" for y, v in ym.items()) + f" | 25on mean {s25['mean_w_king']:.3f} [{s25['min_w_king']:.3f},{s25['max_w_king']:.3f}] switches {s24['switches']}/{s25['switches']} jumps {s24['jumps']}/{s25['jumps']} seat_turn {s24['seat_turn']:.5f}/{s25['seat_turn']:.5f}")
                md(f"| {rule} | {king} | {seed} | {cal} | " + " | ".join(f"{ym.get(y, float('nan')):.3f}" for y in (2022, 2023, 2024, 2025, 2026)) + f" | {s25['mean_w_king']:.3f} | {s25['min_w_king']:.3f}/{s25['max_w_king']:.3f} | {s24['switches']} / {s25['switches']} | {s24['jumps']} / {s25['jumps']} | {s24['seat_turn']:.5f} / {s25['seat_turn']:.5f} |")
# ───────── R2 turnover / deduction and R5 fallback ─────────
print("\n===== R2: per-leg unit-gross rank-book turnover (unit gross/anchor) and deduction κ·turn (bps/anchor), yearly means (from the R2 artifacts' axisb_turn; legs sequence)")
md("\n### R2 — per-leg rank-book turnover (unit gross per anchor) and deduction κ·turn (bps/anchor), yearly mean over the legs() sequence")
md("\n| king | cal | leg | 2022 | 2023 | 2024 | 2025 | 2026 | all | deduction 2024 / 2025 / 2026 (bps) | leg r mean 2025->26 → net |"); md("|" + "---|" * 11)
for king in KINGS:
    for cal in CALS:
        k = ("R2", king, cal, "s42")
        if k not in AX: continue
        lts = AX[k]["axisb_legs_ts"].astype(np.int64); ly = np.array([time.gmtime(int(t)).tm_year for t in lts]); T = AX[k]["axisb_turn"]; LRR = AX[k]["axisb_legs_r"]
        for li, leg in enumerate(("king", "rev24", "fund")):
            ym = {int(y): round(float(T[li][ly == y].mean()), 4) for y in YALL}; ded = {y: round(3.52 * ym[y], 4) for y in ym}
            m25 = ly >= 2025; rm = float(LRR[li][m25].mean()); rn = float((LRR[li] - 3.52 * T[li])[m25].mean())
            OUT["r2_turn"][f"{cal}/{king}/{leg}"] = {"turn_yearly": ym, "turn_all": round(float(T[li].mean()), 4), "deduction_yearly_bps": ded, "leg_r_2025on": round(rm, 4), "leg_r_net_2025on": round(rn, 4)}
            print(f"  {king:7s}{cal:5s}{leg:6s}: turn " + " ".join(f"{y}={v:.4f}" for y, v in ym.items()) + f" all={T[li].mean():.4f} | deduction " + " ".join(f"{y}={v:.3f}" for y, v in ded.items()) + f" | r 25on {rm:+.3f} -> net {rn:+.3f}")
            md(f"| {king} | {cal} | {leg} | " + " | ".join(f"{ym.get(y, float('nan')):.4f}" for y in (2022, 2023, 2024, 2025, 2026)) + f" | {T[li].mean():.4f} | {ded.get(2024, float('nan')):.3f} / {ded.get(2025, float('nan')):.3f} / {ded.get(2026, float('nan')):.3f} | {rm:+.3f} → {rn:+.3f} |")
print("\n===== R5: fallback share by year (evaluated anchors p>=LOOK) and tercile counts")
md("\n### R5 — fallback (plain msharpe900) share by year over evaluated anchors, and causal-tercile membership counts 2024+")
md("\n| king | cal | seed | 2022 | 2023 | 2024 | 2025 | 2026 | all | tercile counts 2024+ (low/mid/high) |"); md("|" + "---|" * 10)
for king in KINGS:
    for cal in CALS:
        for seed in SEEDS:
            k = ("R5", king, cal, seed)
            if k not in AX: continue
            lts = AX[k]["axisb_legs_ts"].astype(np.int64); ly = np.array([time.gmtime(int(t)).tm_year for t in lts]); FB = AX[k]["axisb_regime_fallback"].astype(int); TER = AX[k]["axisb_regime_tercile"].astype(int); ev = FB >= 0
            ym = {int(y): (round(float(FB[ev & (ly == y)].mean()), 4) if (ev & (ly == y)).any() else None) for y in YALL}; tc = [int(((TER == t) & (ly >= 2024)).sum()) for t in range(3)]
            OUT["r5_fallback"][f"{cal}/{king}/{seed}"] = {"fallback_share_yearly": ym, "fallback_share_all": round(float(FB[ev].mean()), 4), "n_evaluated": int(ev.sum()), "tercile_counts_2024on": tc}
            print(f"  {king:7s}{cal:5s}{seed:6s}: fallback " + " ".join(f"{y}={v}" for y, v in ym.items()) + f" all={FB[ev].mean():.4f} (n_eval {int(ev.sum())}) | tercile counts 2024+ {tc}")
            md(f"| {king} | {cal} | {seed} | " + " | ".join((f"{ym.get(y):.3f}" if ym.get(y) is not None else "—") for y in (2022, 2023, 2024, 2025, 2026)) + f" | {FB[ev].mean():.3f} | {tc} |")
# ───────── σ_fund terciles (judge.py definition, descriptive) ─────────
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
# receipt: device σ_fund series (legs sequence, R5 state) vs this judge's series on common anchors
k5 = next((k for k in AX if k[0] == "R5"), None)
if k5 is not None:
    lts = AX[k5]["axisb_legs_ts"].astype(np.int64); dro = AX[k5]["axisb_sigma_roll"]; dmap = {int(t): float(v) for t, v in zip(lts, dro)}
    dv = np.array([dmap.get(int(t), np.nan) for t in ts0]); both = np.isfinite(dv) & np.isfinite(roll); dd = np.abs(dv[both] - roll[both])
    OUT["sigma_fund"]["device_vs_judge"] = {"n_common_finite": int(both.sum()), "max_abs_diff": float(dd.max()), "n_diff_gt_1e-9": int((dd > 1e-9).sum()), "n_rec_anchors_absent_in_device": int((~np.isfinite(dv) & np.isfinite(roll)).sum())}
    print(f"\nσ_fund receipt: device series (legs sequence) vs judge series (rec sequence) on {int(both.sum())} common finite anchors: max|diff| {dd.max():.3e}, n(diff>1e-9) {int((dd > 1e-9).sum())}")
print(f"\n===== σ_fund TERCILES of Δ (2024->26): cuts {q1:.2f}/{q2:.2f} bps; n per tercile {OUT['sigma_fund']['n']}; mean σ per tercile {OUT['sigma_fund']['mean_sigma_by_tercile']}")
md(f"\n### σ_fund-tercile Δ (2024->26 anchors; cuts {q1:.2f}/{q2:.2f} bps/8h; n per tercile {OUT['sigma_fund']['n']}); cell = Δ [CI95] P (R0 mean → rule mean)")
md("\n| rule | king | seed | cal | low | mid | high |"); md("|---|---|---|---|---|---|---|")
for cal in CALS:
    for king in KINGS:
        for seed in SEEDS:
            for rule in RULES[1:]:
                kx = (rule, king, cal, seed); ky = ("R0", king, cal, seed)
                if kx not in D or ky not in D: continue
                delta = D[kx]["net_ex"] - D[ky]["net_ex"]; cells = []; rec = {}
                for t, nm in enumerate(("low", "mid", "high")):
                    mu, lo, hi, p, nd = boot(delta, ter == t); rec[nm] = {"mean": round(mu, 4), "lo": round(lo, 4), "hi": round(hi, 4), "P>0": round(p, 4), "n": int((ter == t).sum()),
                                                                          "R0_mean": round(float(D[ky]["net_ex"][ter == t].mean()), 4), "rule_mean": round(float(D[kx]["net_ex"][ter == t].mean()), 4)}
                    cells.append(f"{mu:+.3f} [{lo:+.3f},{hi:+.3f}] P{p:.2f} ({rec[nm]['R0_mean']:+.3f}→{rec[nm]['rule_mean']:+.3f})")
                OUT["sigma_fund"][f"{cal}/{king}/{seed}/{rule}-R0"] = rec
                print(f"  {cal:4s} {king:7s}{seed:6s}{rule}: " + " | ".join(f"{nm} {c}" for nm, c in zip(("low", "mid", "high"), cells)))
                md(f"| {rule} | {king} | {seed} | {cal} | " + " | ".join(cells) + " |")
# ───────── frozen decision ─────────
def decide(king, rule):
    checks = {}; admit = True; reject = False; missing = []
    for cal in CALS:
        for seed in SEEDS:
            d = OUT["deltas"].get(f"{cal}/{king}/{seed}/{rule}-R0")
            if d is None: missing.append(f"{cal}/{seed}"); continue
            w = d["windows"]["2025->26"]
            c = {"CI_lower>0": w["lo"] > 0, "CI_upper<0": w["hi"] < 0, "CI": [w["lo"], w["hi"]], "mean": w["mean"], "P>0": w["P>0"], "dturn_pct_2025on": d["dturn_pct_2025on"], "turn<=+15%": d["dturn_pct_2025on"] <= 15.0,
                 "aux_2026<=08-10": d["windows"]["2026<=08-10"]["mean"], "aux_2026<=08-10_CI": [d["windows"]["2026<=08-10"]["lo"], d["windows"]["2026<=08-10"]["hi"]]}
            checks[f"{cal}/{seed}"] = c; admit &= c["CI_lower>0"] and c["turn<=+15%"]; reject |= c["CI_upper<0"]
    if missing: return "INCOMPLETE", {"missing": missing, **checks}
    return ("REJECT" if reject else ("ADMIT-candidate" if admit else "UNDECIDED")), checks
md("\n### Decisions (PREREG §2 frozen; PRIMARY = K1 rollm, window 2025->26; ADMIT iff both calibers × both seeds CI95 lower > 0 and Δturn ≤ +15%; REJECT iff any CI95 upper < 0; else UNDECIDED)")
md("\n| rule | king | role | verdict | log/s42 Δ [CI] Δturn% | log/s2027 | prod/s42 | prod/s2027 |"); md("|---|---|---|---|---|---|---|---|")
for king in KINGS:
    for rule in RULES[1:]:
        v, c = decide(king, rule); role = "PRIMARY (frozen criteria)" if king == "rollm" else "SECONDARY (K0 pinned; not for selection)"
        OUT["decision"][f"{king}/{rule}"] = {"verdict": v, "role": role, "checks": c}
        print(f"\n===== DECISION [{king} {rule}] ({role}): {v}")
        for kk, cc in c.items():
            if isinstance(cc, dict): print(f"  {kk}: Δ {cc['mean']:+.4f} CI [{cc['CI'][0]:+.4f},{cc['CI'][1]:+.4f}] P {cc['P>0']:.3f} Δturn {cc['dturn_pct_2025on']:+.2f}% | aux 2026<=08-10 Δ {cc['aux_2026<=08-10']:+.4f} CI [{cc['aux_2026<=08-10_CI'][0]:+.4f},{cc['aux_2026<=08-10_CI'][1]:+.4f}]")
        cell = lambda kk: (f"{c[kk]['mean']:+.3f} [{c[kk]['CI'][0]:+.3f},{c[kk]['CI'][1]:+.3f}] {c[kk]['dturn_pct_2025on']:+.1f}%" if isinstance(c.get(kk), dict) else "—")
        md(f"| {rule} | {king} | {role} | **{v}** | {cell('log/s42')} | {cell('log/s2027')} | {cell('prod/s42')} | {cell('prod/s2027')} |")
json.dump(OUT, open(f"{ROOT}/judge.json", "w"), indent=1)
open(f"{ROOT}/REPORT_tables.md", "w").write("\n".join(MD) + "\n")
print(f"\nwrote {ROOT}/judge.json and {ROOT}/REPORT_tables.md")
