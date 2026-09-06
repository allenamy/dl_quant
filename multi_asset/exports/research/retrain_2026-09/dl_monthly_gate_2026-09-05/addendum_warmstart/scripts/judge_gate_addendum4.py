"""judge_gate_addendum4.py — PREREG_incremental_retrain_2026-09-06 §1 (sha 1463d724…) frozen judge for the warm-start arms W1 (LR 3e-4) / W2 (LR 1e-4), written before any arm number was seen.
Same device (health-check main arm, d30_n2_c42, prod caliber), g = net_ex/gross_total (bps per anchor per unit gross), UTC-day-block bootstrap 2000 seed 20260905,
frozen window 2025-03-01→2026-08-10 20Z (primary) and full window 2025-01-01→2026-08-10 (parallel).
Arms: yearly_s42 / yearly_s2027 (dl_monthly_gate BASE_*, sha asserted), R0_s42 (mE1 seed-per-fold, dl_monthly_gate), CONST42 (mE1c, trackB spl42),
W1 (mE1cF5, spl42; spl27 variant), W2 (mE1cX7, spl42; spl27 variant).
Primary pairs (same seed 42): ARM − yearly_s42; ARM − CONST42. Secondary: ARM(spl27) − yearly_s2027; ARM − R0_s42; W1 − W2.
Frozen reading (§3): (A) at least one arm with ARM − yearly_s42 CI ∋ 0 AND Δ ≥ −0.05 AND the same arm's ARM − CONST42 CI lower > 0;
(B) both arms ARM − yearly_s42 CI upper < 0; (C) otherwise UNDECIDED. Evaluated on the frozen window (primary); full window reported.
usage: judge_gate_addendum3.py → earlystop/results/judge_gate_addendum4.json + addendum4_tables.md"""
import os, json, time, calendar, hashlib
import numpy as np
from scipy.stats import spearmanr
B = "/workspace/review_scratch/allweather_trackB"; M = f"{B}/warmstart"; G = "/workspace/review_scratch/dl_monthly_gate"; NB = 2000; SEED = 20260905; ARM = "d30_n2_c42"
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); T2503 = calendar.timegm((2025, 3, 1, 0, 0, 0)); T26 = calendar.timegm((2026, 1, 1, 0, 0, 0))
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
EXPECT = {"LEGS": "101", "CAL": "log", "LOOK": 900, "WRULE": "msharpe", "MEMBERS_TOPN": 829, "TRADE_TOPN": 0, "FTRIM": "zero", "UMASK_SCOPE": "m1", "W3FIX": None, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
JG = json.load(open(f"{G}/results/judge_gate.json")); PA = f"{B}/replay/dev_alt/probe_artifacts"
ARMS = {"yearly_s42": (f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_BASE_s42.npz", "(default f10_V2MAIN_s{FSEED})", "42", JG["arms"]["BASE_s42"]["sha256"]),
        "yearly_s2027": (f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_BASE_s2027.npz", "(default f10_V2MAIN_s{FSEED})", "2027", JG["arms"]["BASE_s2027"]["sha256"]),
        "R0_s42": (f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_G_mE1_R0.npz", "f10_gate_mE1_R0_s42.npy", "42", JG["arms"]["G_mE1_R0"]["sha256"]),
        "CONST42": (f"{PA}/w10_ablation_series_G_mE1c_R0_spl42.npz", "f10_gate_mE1c_R0_spl42.npy", "42", None),
        "W1": (f"{PA}/w10_ablation_series_G_mE1w1_R0_spl42.npz", "f10_gate_mE1w1_R0_spl42.npy", "42", None), "W1_spl27": (f"{PA}/w10_ablation_series_G_mE1w1_R0_spl27.npz", "f10_gate_mE1w1_R0_spl27.npy", "2027", None),
        "W2": (f"{PA}/w10_ablation_series_G_mE1w2_R0_spl42.npz", "f10_gate_mE1w2_R0_spl42.npy", "42", None), "W2_spl27": (f"{PA}/w10_ablation_series_G_mE1w2_R0_spl27.npz", "f10_gate_mE1w2_R0_spl27.npy", "2027", None)}
if os.path.exists(f"{PA}/w10_ablation_series_G_mE1w1F5_R0_spl42.npz"):   # optional combination arm (PREREG_incremental_retrain §1 末句), added only when present
    ARMS["W1F5"] = (f"{PA}/w10_ablation_series_G_mE1w1F5_R0_spl42.npz", "f10_gate_mE1w1F5_R0_spl42.npy", "42", None)
    ARMS["FLOOR5"] = (f"{PA}/w10_ablation_series_G_mE1cF5_R0_spl42.npz", "f10_gate_mE1cF5_R0_spl42.npy", "42", None)
D = {}; META = {}
for key, (p, fpred, fseed, sha16) in ARMS.items():
    z = np.load(p, allow_pickle=True); cfg = json.loads(str(z["config_json"])); assert [str(c) for c in z["cols"]] == COLS
    for k, v in EXPECT.items(): assert cfg.get(k) == v, (key, k, cfg.get(k), v)
    assert cfg["FPRED"] == fpred and cfg["FSEED"] == fseed and abs(cfg["PHI"] - 0.45) < 1e-12 and cfg.get("PHIDYN", 0) == 0, (key, cfg["FPRED"], cfg["FSEED"])
    s16 = sha(p)[:16]; assert sha16 is None or s16 == sha16, (key, s16, sha16)
    Rr = z[f"{ARM}_rec"]; D[key] = {c: Rr[:, i] for i, c in enumerate(COLS)}; META[key] = {"artifact": p, "sha256_16": s16, "FPRED": fpred, "FSEED": fseed, "n": int(len(Rr))}
keys = list(D); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), k
days = ts0 // 86400; months = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in ts0])
WIN = {"pre-2025": ts0 < T25, "2025-01/02": (ts0 >= T25) & (ts0 < T2503), "FROZEN 2025-03->26<=cut": (ts0 >= T2503) & (ts0 <= CUT), "FULL 2025-01->26<=cut": (ts0 >= T25) & (ts0 <= CUT), "2025 full": (ts0 >= T25) & (ts0 < T26), "2026<=cut": (ts0 >= T26) & (ts0 <= CUT)}
PW = "FROZEN 2025-03->26<=cut"; FW = "FULL 2025-01->26<=cut"
G_ = {k: D[k]["net_ex"] / D[k]["gross_total"] for k in keys}; TPG = {k: D[k]["turnover"] / D[k]["gross_total"] for k in keys}
rng = np.random.default_rng(SEED)
def boot(x, m):
    v = x[m]; d = days[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud); s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "mean": float(v.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5)), "P>0": float((means > 0).mean()), "nav_pct_yr_2x": float(v.mean() * 43.8)}
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
T = []
def p(s=""): T.append(s); print(s)
OUT = {"arm": ARM, "n_anchors": int(len(ts0)), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "arms": META, "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "units": "g = net_ex/gross_total bps per anchor per unit gross; NAV %/yr @2x = mean*43.8; 2xDD %NAV = maxDD_bps*2/100", "levels": {}, "deltas": {}, "reading": {}, "ic": {}}
p(f"<!-- judge_gate_addendum3.py: n={len(ts0)} {iso(ts0[0])}→{iso(ts0[-1])}; windows {OUT['windows']}; bootstrap UTC-day 2000 seed {SEED} -->")
p("## AD4-1 · Levels per gross (bps/anchor); VERIFIED judge_gate_addendum4.json levels; NAV %/yr @2× = mean × 43.8; 2×DD %NAV = maxDD × 2/100")
p("| arm | FPRED | seed | FROZEN [CI95] | S | maxDD (2×DD %NAV) | turn/gross | NAV %/yr @2× | FULL [CI95] | S | 2025-01/02 | 2025 full | 2026≤cut |"); p("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k in keys:
    row = {}
    for w, m in WIN.items():
        x = G_[k][m]; row[w] = {"n": int(m.sum()), "mean": float(x.mean()), "sharpe": sharpe(x), "maxDD_bps": maxdd(x), "turn_per_gross": float(TPG[k][m].mean()), "nav_pct_yr_2x": float(x.mean() * 43.8)}
        if w in (PW, FW): row[w]["boot"] = boot(G_[k], m)
    OUT["levels"][k] = row; a, b = row[PW], row[FW]
    p(f"| {k} | {META[k]['FPRED']} | {META[k]['FSEED']} | **{a['mean']:+.3f}** [{a['boot']['lo']:+.3f}, {a['boot']['hi']:+.3f}] | {a['sharpe']:+.2f} | {a['maxDD_bps']:.0f} ({a['maxDD_bps']*2/100:.1f}%) | {a['turn_per_gross']:.5f} | {a['nav_pct_yr_2x']:+.1f}% | **{b['mean']:+.3f}** [{b['boot']['lo']:+.3f}, {b['boot']['hi']:+.3f}] | {b['sharpe']:+.2f} | {row['2025-01/02']['mean']:+.3f} | {row['2025 full']['mean']:+.3f} | {row['2026<=cut']['mean']:+.3f} |")
PAIRS = [("W1", "yearly_s42", "W1 − yearly_s42 [primary]"), ("W1", "CONST42", "W1 − CONST42 [primary]"), ("W2", "yearly_s42", "W2 − yearly_s42 [primary]"), ("W2", "CONST42", "W2 − CONST42 [primary]"),
         ("W1_spl27", "yearly_s2027", "W1(spl27) − yearly_s2027"), ("W2_spl27", "yearly_s2027", "W2(spl27) − yearly_s2027"), ("W1", "R0_s42", "W1 − R0(mE1,s42)"), ("W2", "R0_s42", "W2 − R0(mE1,s42)"), ("W1", "W2", "W1 − W2"),
         ("CONST42", "yearly_s42", "CONST42 − yearly_s42 [§11 reference]")]
if "W1F5" in D: PAIRS += [("W1F5", "yearly_s42", "W1F5 − yearly_s42 [combo primary]"), ("W1F5", "CONST42", "W1F5 − CONST42 [combo primary]"), ("W1F5", "FLOOR5", "W1F5 − FLOOR5 [combo vs §12 arm]"), ("W1F5", "W1", "W1F5 − W1 [combo vs warm arm]"), ("FLOOR5", "yearly_s42", "FLOOR5 − yearly_s42 [§12 reference]")]
DW = ("pre-2025", "2025-01/02", "2025 full", "2026<=cut", PW, FW)
p("\n## AD4-2 · Paired Δ per gross (Δg = g_x − g_ref by anchor; UTC-day-block bootstrap; Δ [CI95] P(Δ>0)); VERIFIED judge_gate_addendum4.json deltas")
p("| pair | pre-2025 | 2025-01/02 | 2025 full | 2026≤cut | **FROZEN 2025-03→26≤cut** | **FULL 2025-01→26≤cut** | ΔSharpe frozen/full | Δturn% | maxDD ref→x | Δ w/o best month (frozen) |"); p("|---|---|---|---|---|---|---|---|---|---|---|")
for kx, ky, name in PAIRS:
    dg = G_[kx] - G_[ky]; res = {}
    for w in DW:
        m = WIN[w]; b = boot(dg, m); b["exact_zero"] = bool(np.all(dg[m] == 0)); res[w] = b
    tx = float(TPG[kx][WIN[PW]].mean()); ty = float(TPG[ky][WIN[PW]].mean()); dturn = (tx / ty - 1) * 100
    mc = {str(mo): float(dg[(months == mo) & WIN[PW]].sum()) for mo in sorted(set(months[WIN[PW]].tolist()))}; best = max(mc, key=mc.get); drop = boot(dg, WIN[PW] & (months != int(best)))
    OUT["deltas"][name] = {"x": kx, "ref": ky, "windows": res, "dturn_pct_frozen": dturn, "dSharpe": {PW: sharpe(G_[kx][WIN[PW]]) - sharpe(G_[ky][WIN[PW]]), FW: sharpe(G_[kx][WIN[FW]]) - sharpe(G_[ky][WIN[FW]])}, "maxDD_ref": maxdd(G_[ky][WIN[PW]]), "maxDD_x": maxdd(G_[kx][WIN[PW]]), "monthly_contrib_bps": mc, "best_month": best, "drop_best_month": drop}
    f = lambda w: f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] P{res[w]['P>0']:.2f}" + (" (=0)" if res[w]["exact_zero"] else "")
    p(f"| {name} | {f('pre-2025')} | {f('2025-01/02')} | {f('2025 full')} | {f('2026<=cut')} | **{f(PW)}** | **{f(FW)}** | {OUT['deltas'][name]['dSharpe'][PW]:+.3f} / {OUT['deltas'][name]['dSharpe'][FW]:+.3f} | {dturn:+.1f}% | {maxdd(G_[ky][WIN[PW]]):.0f}→{maxdd(G_[kx][WIN[PW]]):.0f} | {drop['mean']:+.3f} [{drop['lo']:+.3f},{drop['hi']:+.3f}] (best {best} {mc[best]:+.0f}) |")
# ── frozen reading §3 ──
R = {}
for w in (PW, FW):
    per = {}
    for arm in ("W1", "W2"):
        y = OUT["deltas"][f"{arm} − yearly_s42 [primary]"]["windows"][w]; c = OUT["deltas"][f"{arm} − CONST42 [primary]"]["windows"][w]
        per[arm] = {"vs_yearly": [y["mean"], y["lo"], y["hi"]], "vs_const": [c["mean"], c["lo"], c["hi"]], "A_cond_yearly_CI_contains0_and_delta_ge_-0.05": bool(y["lo"] <= 0 <= y["hi"] and y["mean"] >= -0.05), "A_cond_const_CI_lower_gt0": bool(c["lo"] > 0), "yearly_CI_upper_lt0": bool(y["hi"] < 0)}
        per[arm]["A_arm"] = per[arm]["A_cond_yearly_CI_contains0_and_delta_ge_-0.05"] and per[arm]["A_cond_const_CI_lower_gt0"]
    A_ = any(per[a]["A_arm"] for a in per); B_ = all(per[a]["yearly_CI_upper_lt0"] for a in per)
    if "W1F5" in D:
        y = OUT["deltas"]["W1F5 − yearly_s42 [combo primary]"]["windows"][w]; c = OUT["deltas"]["W1F5 − CONST42 [combo primary]"]["windows"][w]; f5 = OUT["deltas"]["W1F5 − FLOOR5 [combo vs §12 arm]"]["windows"][w]
        per["W1F5 (combo, reported separately)"] = {"vs_yearly": [y["mean"], y["lo"], y["hi"]], "vs_const": [c["mean"], c["lo"], c["hi"]], "vs_floor5": [f5["mean"], f5["lo"], f5["hi"]], "A_cond_yearly_CI_contains0_and_delta_ge_-0.05": bool(y["lo"] <= 0 <= y["hi"] and y["mean"] >= -0.05), "A_cond_const_CI_lower_gt0": bool(c["lo"] > 0), "yearly_CI_upper_lt0": bool(y["hi"] < 0), "A_arm": bool(y["lo"] <= 0 <= y["hi"] and y["mean"] >= -0.05 and c["lo"] > 0)}
    R[w] = {"arms": per, "A": bool(A_), "B": bool(B_), "verdict": "(A) 热启动候选 ⇒ 与早停臂结果合并成月度重训配方候选(RUNBOOK 改动 + 用户字; 影子/第二仪器再验)" if A_ else ("(B) 热启动不救" if B_ else "(C) UNDECIDED ⇒ 两候选都留")}
OUT["reading"] = R
p("\n## AD4-3 · Frozen reading (PREREG_incremental_retrain §1): (A) some arm: ARM − yearly_s42 CI ∋ 0 ∧ Δ ≥ −0.05 ∧ ARM − CONST42 CI lower > 0; (B) both arms ARM − yearly_s42 CI upper < 0; (C) otherwise")
p("| window | W1 − yearly | W1 − CONST | W1 (A)? | W2 − yearly | W2 − CONST | W2 (A)? | (A) | (B) | verdict |"); p("|---|---|---|---|---|---|---|---|---|---|")
for w, r in R.items():
    g = lambda v: f"{v[0]:+.3f} [{v[1]:+.3f},{v[2]:+.3f}]"; a5, a7 = r["arms"]["W1"], r["arms"]["W2"]
    if "W1F5 (combo, reported separately)" in r["arms"]: cc = r["arms"]["W1F5 (combo, reported separately)"]; p(f"| {w} · W1F5 combo (separate) | {g(cc['vs_yearly'])} | {g(cc['vs_const'])} | A-conditions {cc['A_arm']} | vs FLOOR5 {g(cc['vs_floor5'])} | | | | | reported, not in the two-arm reading |")
    p(f"| {w} | {g(a5['vs_yearly'])} | {g(a5['vs_const'])} | {a5['A_arm']} | {g(a7['vs_yearly'])} | {g(a7['vs_const'])} | {a7['A_arm']} | {r['A']} | {r['B']} | **{r['verdict']}** |")
# ── score level ──
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; Y4 = A["y4s"]; nA = len(E)
def ics(P):
    ic = np.full(nA, np.nan)
    for i in range(int(np.searchsorted(E, T25)), nA):
        if not np.isfinite(P[i]).any(): continue
        mm = MEM[i]; a = P[i, mm]; b = Y4[i, mm]; ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() >= 30: ic[i] = spearmanr(a[ok], b[ok]).correlation
    return ic
def to_ext(p): Q = np.full((nA, 829), np.nan, np.float32); X = np.load(p); Q[:len(X)] = X; return Q
S = {"W1": np.load(f"{M}/W1/preds/f10_V2MAIN_mE1w1_s42.npy"), "W2": np.load(f"{M}/W2/preds/f10_V2MAIN_mE1w2_s42.npy"), "CONST42": np.load(f"{B}/mE1_constseed/preds/f10_V2MAIN_mE1c_s42.npy"), "R0_s42": np.load(f"{G}/series/mE1_R0.npy"), "yearly_s42": to_ext("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy")}
IC = {k: ics(v) for k, v in S.items()}; Ed = E // 86400
def bootE(x, m):
    v = x[m]; d = Ed[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud); s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "mean": float(v.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5))}
p("\n## AD4-4 · Score level: per-anchor rank IC (same anchor set); ΔIC with UTC-day-block bootstrap")
p("| window | IC W1 | IC W2 | IC CONST | IC R0 s42 | IC yearly s42 | ΔIC W1−yearly | ΔIC W2−yearly | ΔIC W1−CONST | ΔIC W2−CONST |"); p("|---|---|---|---|---|---|---|---|---|---|")
for w, m in {PW: (E >= T2503) & (E <= CUT), FW: (E >= T25) & (E <= CUT)}.items():
    mm = m.copy()
    for k in IC: mm &= np.isfinite(IC[k])
    d = {nm: bootE(IC[a] - IC[b], mm) for nm, a, b in (("F5_y", "W1", "yearly_s42"), ("X7_y", "W2", "yearly_s42"), ("F5_c", "W1", "CONST42"), ("X7_c", "W2", "CONST42"))}
    OUT["ic"][w] = {"n": int(mm.sum()), "levels": {k: float(IC[k][mm].mean()) for k in IC}, "deltas": d}; g = lambda q: f"{q['mean']:+.4f} [{q['lo']:+.4f},{q['hi']:+.4f}]"
    p(f"| {w} (n={mm.sum()}) | {IC['W1'][mm].mean():+.4f} | {IC['W2'][mm].mean():+.4f} | {IC['CONST42'][mm].mean():+.4f} | {IC['R0_s42'][mm].mean():+.4f} | {IC['yearly_s42'][mm].mean():+.4f} | {g(d['F5_y'])} | {g(d['X7_y'])} | {g(d['F5_c'])} | {g(d['X7_c'])} |")
os.makedirs(f"{M}/results", exist_ok=True); json.dump(OUT, open(f"{M}/results/judge_gate_addendum4.json", "w"), indent=1, default=float); open(f"{M}/results/addendum4_tables.md", "w").write("\n".join(T) + "\n")
for w, r in R.items(): print(f"===== §13 READING [{w}]: W1−yearly {r['arms']['W1']['vs_yearly'][0]:+.4f} [{r['arms']['W1']['vs_yearly'][1]:+.4f},{r['arms']['W1']['vs_yearly'][2]:+.4f}] W1−CONST {r['arms']['W1']['vs_const'][0]:+.4f} [{r['arms']['W1']['vs_const'][1]:+.4f},{r['arms']['W1']['vs_const'][2]:+.4f}] | W2−yearly {r['arms']['W2']['vs_yearly'][0]:+.4f} [{r['arms']['W2']['vs_yearly'][1]:+.4f},{r['arms']['W2']['vs_yearly'][2]:+.4f}] W2−CONST {r['arms']['W2']['vs_const'][0]:+.4f} [{r['arms']['W2']['vs_const'][1]:+.4f},{r['arms']['W2']['vs_const'][2]:+.4f}] ⇒ {r['verdict']}")
print("ADDENDUM4_JUDGE_DONE", flush=True)
