"""judge_gate.py — dl_monthly_gate frozen judge (PREREG_dl_monthly_gate_and_phi_grid §A2/§A4, numbers unseen when written).
Artifacts: replay/dev_alt/probe_artifacts/w10_ablation_series_<TAG>.npz, arm d30_n2_c42, prod caliber, U-PIT m1 FTRIM msharpe-900 PHI 0.45 live fee tiers.
Arms: BASE_s42 / BASE_s2027 (R-yearly), G_{mE1,mE60}_{R0,R1,R2,R3,R4}, G_mE1_R1_phidyn (w10_seat2g PHIDYN=1 clip [0.3,0.6]), G_mE1_R0_phidyn (auxiliary), G_mE1_R1_seat2def (equivalence only).
g = net_ex / gross_total (bps per anchor per unit gross). Windows: PRIMARY 2025-03-01 → 2026-08-10 20Z (first two months dropped: no gate comparison; same anchor
set for all arms) | 2026≤cut | 2025-03→12 | pre-2025 (exact 0 expected: all spliced from the same yearly rows) | 2025-01/02 (identical across gate arms, differs for R0).
Paired Δ vs R0 (= G_mE1_R0, the live form) and vs R-yearly (BASE_s42 primary, BASE_s2027 secondary); mE60 arms additionally vs G_mE60_R0. UTC-day blocks, 2000, seed 20260905.
Frozen judge §A4: "门有价值" ⇔ gate arm vs R0: primary-window CI95 lower > 0 AND 2026≤cut point ≥ 0 AND turnover/gross increase ≤ +10 %;
"现行月度换装可保持" ⇔ R0 − R-yearly CI95 upper > 0; else UNDECIDED. Single-month check (operationalised here, before numbers): for a qualifying arm, the Δ with its best
calendar month removed must still have CI95 lower > 0, else UNDECIDED. Per-month contribution table printed for every arm.
usage: judge_gate.py  → results/judge_gate.json + stdout"""
import os, sys, json, time, calendar, hashlib
import numpy as np
G = "/workspace/review_scratch/dl_monthly_gate"; PA = f"{G}/replay/dev_alt/probe_artifacts"; NB = 2000; SEED = 20260905; ARM = "d30_n2_c42"
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); T2503 = calendar.timegm((2025, 3, 1, 0, 0, 0)); T26 = calendar.timegm((2026, 1, 1, 0, 0, 0))
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
EXPECT = {"LEGS": "101", "CAL": "log", "LOOK": 900, "WRULE": "msharpe", "MEMBERS_TOPN": 829, "TRADE_TOPN": 0, "FTRIM": "zero", "UMASK_SCOPE": "m1", "W3FIX": None, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
ARMS = {"BASE_s42": ("(default f10_V2MAIN_s{FSEED})", "42", None), "BASE_s2027": ("(default f10_V2MAIN_s{FSEED})", "2027", None)}
for T in ("mE1", "mE60"):
    for r in ("R0", "R1", "R2", "R3", "R4"): ARMS[f"G_{T}_{r}"] = (f"f10_gate_{T}_{r}_s42.npy", "42", None)
ARMS["G_mE1_R1_phidyn"] = ("f10_gate_mE1_R1_s42.npy", "42", [0.3, 0.6]); ARMS["G_mE1_R0_phidyn"] = ("f10_gate_mE1_R0_s42.npy", "42", [0.3, 0.6])
D = {}; META = {}; PHIT = {}
for key, (fpred, fseed, clip) in ARMS.items():
    p = f"{PA}/w10_ablation_series_{key}.npz"
    if not os.path.exists(p): print(f"MISSING {key}: {p}"); continue
    z = np.load(p, allow_pickle=True); cfg = json.loads(str(z["config_json"])); assert [str(c) for c in z["cols"]] == COLS
    for k, v in EXPECT.items(): assert cfg.get(k) == v, (key, k, cfg.get(k), v)
    assert cfg["FPRED"] == fpred and cfg["FSEED"] == fseed and abs(cfg["PHI"] - 0.45) < 1e-12 and cfg["COSTB_JSON"] and cfg["UMASK_NPZ"], (key, cfg["FPRED"], cfg["FSEED"], cfg["PHI"])
    if clip is not None:
        assert cfg["PHIDYN"] == 1 and cfg["PHIDYN_CLIP"] == clip and cfg["PHIDYN_LOOK"] == 900 and cfg.get("SEATCOST_BPS", 0.0) == 0.0 and cfg.get("SEATF10", 0) == 0, (key, cfg.get("PHIDYN"), cfg.get("PHIDYN_CLIP"))
        s2c = [str(c) for c in z["seat2_cols"]]; PHIT[key] = z[f"{ARM}_seat2"][:, s2c.index("phi_t")]
    else: assert cfg.get("PHIDYN", 0) == 0, (key, cfg.get("PHIDYN"))
    Rr = z[f"{ARM}_rec"]; D[key] = {c: Rr[:, i] for i, c in enumerate(COLS)}; META[key] = {"artifact": p, "sha256": sha(p)[:16], "FPRED": fpred, "FSEED": fseed, "PHIDYN_CLIP": clip, "n": int(len(Rr)), "device": cfg.get("SEAT2", cfg.get("HEALTH", {})).get("device_sha256", "")[:16]}
keys = list(D); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), ("ts mismatch", k)
days = ts0 // 86400; months = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in ts0])
WIN = {"pre-2025": ts0 < T25, "2025-01/02": (ts0 >= T25) & (ts0 < T2503), "2025-03->26<=cut": (ts0 >= T2503) & (ts0 <= CUT), "2026<=cut": (ts0 >= T26) & (ts0 <= CUT), "2025-03->12": (ts0 >= T2503) & (ts0 < T26), "2026-postcut": ts0 > CUT}
G_ = {k: D[k]["net_ex"] / D[k]["gross_total"] for k in keys}; TPG = {k: D[k]["turnover"] / D[k]["gross_total"] for k in keys}
rng = np.random.default_rng(SEED)
def boot(x, m):
    v = x[m]; d = days[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud)
    s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "n_days": int(nd), "mean": float(v.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5)), "P>0": float((means > 0).mean()), "pct_gross_yr": float(v.mean() * 2190 / 100)}
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
SC = {T: json.load(open(f"{G}/results/score_{T}.json")) if os.path.exists(f"{G}/results/score_{T}.json") else None for T in ("mE1", "mE60")}
OUT = {"arm": ARM, "n_anchors": int(len(ts0)), "first": iso(ts0[0]), "last": iso(ts0[-1]), "cut": iso(CUT), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "arms": META, "units": "g = net_ex/gross_total bps per anchor per unit gross; %/gross/yr = mean*2190/100",
       "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "levels": {}, "deltas": {}, "monthly_contrib": {}, "phidyn": {}, "judge": {}}
print(f"LOADED {len(D)} arms n={len(ts0)} {iso(ts0[0])}→{iso(ts0[-1])}; windows " + ", ".join(f"{w}={int(m.sum())}" for w, m in WIN.items())); print("ARMS " + json.dumps(META))
PW = "2025-03->26<=cut"
print(f"\n===== LEVELS per gross (bps/anchor): mean S=Sharpe DD=maxDD(bps gross) %/gross/yr | gross w_king turn/gross cost/gross carry/gross ({PW}) | swaps / mean age / IC")
for k in keys:
    row = {}
    for w, m in WIN.items():
        if m.sum() < 12: continue
        x = G_[k][m]; d = D[k]
        row[w] = {"n": int(m.sum()), "mean": float(x.mean()), "sharpe": sharpe(x), "maxDD_bps": maxdd(x), "pct_gross_yr": float(x.mean() * 2190 / 100), "gross": float(d["gross_total"][m].mean()), "w_king": float(d["w3_king"][m].mean()),
                  "turn_per_gross": float(TPG[k][m].mean()), "cost_per_gross": float((d["cost_ex"][m] / d["gross_total"][m]).mean()), "carry_per_gross": float((d["carry_ex"][m] / d["gross_total"][m]).mean()), "net_ex_nav_mean": float(d["net_ex"][m].mean())}
        if w in (PW, "2026<=cut", "2025-03->12"): row[w]["boot"] = boot(G_[k], m)
    T = "mE1" if "_mE1_" in k else ("mE60" if "_mE60_" in k else None); r = k.split("_")[2] if T else None
    arm_sc = SC[T]["arms"].get(r) if (T and SC[T]) else None; ic = SC[T]["ic_levels"].get(f"{PW}/{r}") if (T and SC[T]) else None
    if k.startswith("BASE") and SC["mE1"]: ic = SC["mE1"]["ic_levels"].get(f"{PW}/yearly")
    row["swaps"] = arm_sc["swaps"] if arm_sc else None; row["mean_age"] = arm_sc["mean_age_from_2025-03"] if arm_sc else (1.0 if k.startswith("BASE") is False else None); row["max_age"] = arm_sc["max_age"] if arm_sc else None; row["ic_primary"] = ic
    OUT["levels"][k] = row; p = row[PW]
    print(f"{k:18s}| {PW} {p['mean']:+.3f} S{p['sharpe']:+.2f} DD{p['maxDD_bps']:.0f} {p['pct_gross_yr']:+.1f}% | 2026 {row['2026<=cut']['mean']:+.3f} S{row['2026<=cut']['sharpe']:+.2f} | 2025-03->12 {row['2025-03->12']['mean']:+.3f} | {p['gross']:.3f} {p['w_king']:.3f} {p['turn_per_gross']:.5f} {p['cost_per_gross']:.3f} {p['carry_per_gross']:+.3f} | "
          + (f"swaps {row['swaps']} age {row['mean_age']:.2f} max {row['max_age']}" if arm_sc else "-") + (f" IC {ic['mean']:+.4f}±{ic['se_anchor']:.4f}" if ic else ""))
PAIRS = []
for k in keys:
    if k.startswith("G_mE1_") and k != "G_mE1_R0": PAIRS += [(k, "G_mE1_R0", f"{k} − R0(mE1)"), (k, "BASE_s42", f"{k} − yearly s42"), (k, "BASE_s2027", f"{k} − yearly s2027")]
    if k.startswith("G_mE60_"): PAIRS += [(k, "G_mE1_R0", f"{k} − R0(mE1)"), (k, "BASE_s42", f"{k} − yearly s42")] + ([(k, "G_mE60_R0", f"{k} − R0(mE60)")] if k != "G_mE60_R0" else [])
PAIRS += [("G_mE1_R0", "BASE_s42", "R0(mE1) − yearly s42 [§A4 keepable]"), ("G_mE1_R0", "BASE_s2027", "R0(mE1) − yearly s2027"), ("G_mE1_R1_phidyn", "G_mE1_R1", "R1+φdyn − R1 (fixed φ) [§A3]"), ("G_mE1_R0_phidyn", "G_mE1_R0", "R0+φdyn − R0 (aux)")]
DW = ("pre-2025", "2025-01/02", "2025-03->12", "2026<=cut", PW, "2026-postcut")
print(f"\n===== DELTAS per gross: Δg = g_x − g_ref, paired by anchor; day-block bootstrap NB={NB} seed={SEED}; cells Δ [CI95] P(Δ>0)")
for kx, ky, name in PAIRS:
    if kx not in D or ky not in D: print(f"skip {name}"); continue
    dg = G_[kx] - G_[ky]; res = {}
    for w in DW:
        m = WIN[w]
        if m.sum() < 12: continue
        b = boot(dg, m); b["exact_zero"] = bool(np.all(dg[m] == 0)); b["maxabs"] = float(np.max(np.abs(dg[m]))); res[w] = b
    tx = float(TPG[kx][WIN[PW]].mean()); ty = float(TPG[ky][WIN[PW]].mean()); dturn = (tx / ty - 1) * 100 if ty > 0 else float("nan")
    dsh = {w: sharpe(G_[kx][WIN[w]]) - sharpe(G_[ky][WIN[w]]) for w in (PW, "2026<=cut", "2025-03->12")}
    # per-month contribution (sum of Δg over the calendar month, bps gross) within the primary window
    mc = {}
    for mo in sorted(set(months[WIN[PW]].tolist())):
        mm = (months == mo) & WIN[PW]; mc[str(mo)] = {"n": int(mm.sum()), "sum_bps": float(dg[mm].sum()), "mean": float(dg[mm].mean())}
    tot = sum(v["sum_bps"] for v in mc.values()); best = max(mc, key=lambda q: mc[q]["sum_bps"]); worst = min(mc, key=lambda q: mc[q]["sum_bps"])
    drop = boot(dg, WIN[PW] & (months != int(best)))
    OUT["deltas"][name] = {"x": kx, "ref": ky, "windows": res, "dturn_pct_primary": dturn, "turn_ref": ty, "turn_x": tx, "dSharpe": dsh, "maxDD_ref": maxdd(G_[ky][WIN[PW]]), "maxDD_x": maxdd(G_[kx][WIN[PW]]),
                         "monthly_contrib": mc, "total_bps": tot, "best_month": best, "best_month_share": (mc[best]["sum_bps"] / tot if abs(tot) > 1e-9 else None), "worst_month": worst, "n_months_pos": int(sum(1 for v in mc.values() if v["sum_bps"] > 0)), "n_months": len(mc), "drop_best_month": drop}
    f = lambda w: (f"{res[w]['mean']:+.4f} [{res[w]['lo']:+.4f},{res[w]['hi']:+.4f}] P{res[w]['P>0']:.2f}" + (" (=0)" if res[w]["exact_zero"] else "")) if w in res else "n/a"
    print(f"{name}\n    " + " | ".join(f"{w}: {f(w)}" for w in DW) + f"\n    ΔSharpe {PW} {dsh[PW]:+.3f}; turn/gross ref {ty:.5f} x {tx:.5f} ({dturn:+.1f}%); maxDD ref {maxdd(G_[ky][WIN[PW]]):.0f} x {maxdd(G_[kx][WIN[PW]]):.0f}; months +{OUT['deltas'][name]['n_months_pos']}/{len(mc)}; best {best} {mc[best]['sum_bps']:+.0f} bps ({(mc[best]['sum_bps']/tot*100 if abs(tot)>1e-9 else float('nan')):+.0f}% of total {tot:+.0f}); worst {worst} {mc[worst]['sum_bps']:+.0f}; Δ without best month {drop['mean']:+.4f} [{drop['lo']:+.4f},{drop['hi']:+.4f}]")
# φdyn stats
for k, ph in PHIT.items():
    m = WIN[PW]; x = ph[m]; OUT["phidyn"][k] = {"phi_mean": float(x.mean()), "phi_min": float(x.min()), "phi_max": float(x.max()), "share_at_lower_clip": float((x <= 0.3 + 1e-12).mean()), "share_at_upper_clip": float((x >= 0.6 - 1e-12).mean()), "share_eq_0.45": float((np.abs(x - 0.45) < 1e-12).mean()),
                                                 "n_cross_0.45": int((np.diff(np.sign(x - 0.45)) != 0).sum()), "n_jumps_ge_0.05": int((np.abs(np.diff(x)) >= 0.05).sum()), "phi_by_year": {str(y): float(ph[m & (months // 100 == y)].mean()) for y in (2025, 2026)}}
    print(f"PHIDYN {k}: " + json.dumps(OUT["phidyn"][k]))
# ── frozen judge §A4 ──
def cell(name, w): return OUT["deltas"].get(name, {}).get("windows", {}).get(w)
J = {}
for T in ("mE1", "mE60"):
    for r in ("R1", "R2", "R3", "R4"):
        k = f"G_{T}_{r}"; nm = f"{k} − R0(mE1)"
        if nm not in OUT["deltas"]: continue
        d = OUT["deltas"][nm]; p = d["windows"].get(PW); q = d["windows"].get("2026<=cut")
        c = {"primary_delta": p["mean"], "primary_CI": [p["lo"], p["hi"]], "CI_lower>0": p["lo"] > 0, "2026_point>=0": q["mean"] >= 0, "dturn_pct": d["dturn_pct_primary"], "turn<=+10%": d["dturn_pct_primary"] <= 10.0,
             "single_month_check_drop_best_CI_lower>0": d["drop_best_month"]["lo"] > 0, "best_month_share": d["best_month_share"]}
        ok = c["CI_lower>0"] and c["2026_point>=0"] and c["turn<=+10%"]; c["verdict"] = ("GATE VALUABLE" if (ok and c["single_month_check_drop_best_CI_lower>0"]) else ("UNDECIDED (single-month driven)" if ok else "UNDECIDED")); J[k] = c
        print(f"\n===== JUDGE §A4 [{k} vs R0(mE1)]: Δ {p['mean']:+.4f} [{p['lo']:+.4f},{p['hi']:+.4f}] lower>0={c['CI_lower>0']}; 2026 point {q['mean']:+.4f} >=0={c['2026_point>=0']}; Δturn {d['dturn_pct_primary']:+.1f}% <=10={c['turn<=+10%']}; drop-best-month lower>0={c['single_month_check_drop_best_CI_lower>0']} ⇒ {c['verdict']}")
for nm, lab in (("R0(mE1) − yearly s42 [§A4 keepable]", "keepable_s42"), ("R0(mE1) − yearly s2027", "keepable_s2027")):
    p = cell(nm, PW)
    if p: J[lab] = {"delta": p["mean"], "CI": [p["lo"], p["hi"]], "CI_upper>0": p["hi"] > 0, "verdict": "现行月度换装可保持 (CI upper > 0)" if p["hi"] > 0 else "NOT keepable by §A4 (CI upper <= 0)"}; print(f"===== JUDGE §A4 [{nm}]: {p['mean']:+.4f} [{p['lo']:+.4f},{p['hi']:+.4f}] ⇒ {J[lab]['verdict']}")
p = cell("R1+φdyn − R1 (fixed φ) [§A3]", PW)
if p: J["R1_phidyn_vs_R1"] = {"delta": p["mean"], "CI": [p["lo"], p["hi"]], "dturn_pct": OUT["deltas"]["R1+φdyn − R1 (fixed φ) [§A3]"]["dturn_pct_primary"]}; print(f"===== §A3 [R1+φdyn − R1]: {p['mean']:+.4f} [{p['lo']:+.4f},{p['hi']:+.4f}], Δturn {J['R1_phidyn_vs_R1']['dturn_pct']:+.1f}%")
OUT["judge"] = J; json.dump(OUT, open(f"{G}/results/judge_gate.json", "w"), indent=1, default=float); print(f"\nwrote {G}/results/judge_gate.json"); print("JUDGE_DONE", flush=True)
