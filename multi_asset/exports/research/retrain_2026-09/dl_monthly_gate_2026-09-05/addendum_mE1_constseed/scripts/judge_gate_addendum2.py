"""judge_gate_addendum2.py — addendum §11 frozen reading (lead 09-05, stated before numbers):
Arms (same device, health-check main arm, d30_n2_c42, prod caliber): yearly s42 / s2027 (dl_monthly_gate BASE_*), R0(mE1, s42) (dl_monthly_gate G_mE1_R0),
R0(mE1, s2027) (trackB spl27), CONST = monthly folds with constant seed 42 (mE1c; pre-2025 rows from yearly s42 = spl42 [primary]; spl27 variant).
Pairs (frozen 2025-03→08-10 and full 2025-01→08-10 windows; UTC-day-block bootstrap 2000 seed 20260905):
  CONST − yearly s42 [primary]; CONST(spl27) − yearly s2027; CONST − R0(mE1,s42); CONST − R0(mE1,s2027); R0(mE1,s42) − yearly s42 [reference]; R0(mE1,s2027) − yearly s2027 [reference].
Reading: (a) constant-seed − yearly within ±0.05 with CI ∋ 0 (both yearly seeds) while mE1(seed-per-fold) − yearly stays CI<0 ⇒ deficit = init/seed churn;
(b) constant-seed − yearly CI upper < 0 (both yearly seeds) ⇒ deficit = refit form; (c) otherwise UNDECIDED. Evaluated on the frozen window (primary) and reported on the full window.
usage: judge_gate_addendum2.py → mE1_constseed/results/judge_gate_addendum2.json + addendum2_tables.md"""
import os, json, time, calendar, hashlib
import numpy as np
from scipy.stats import spearmanr
B = "/workspace/review_scratch/allweather_trackB"; M = f"{B}/mE1_constseed"; G = "/workspace/review_scratch/dl_monthly_gate"; NB = 2000; SEED = 20260905; ARM = "d30_n2_c42"
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); T2503 = calendar.timegm((2025, 3, 1, 0, 0, 0)); T26 = calendar.timegm((2026, 1, 1, 0, 0, 0))
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
EXPECT = {"LEGS": "101", "CAL": "log", "LOOK": 900, "WRULE": "msharpe", "MEMBERS_TOPN": 829, "TRADE_TOPN": 0, "FTRIM": "zero", "UMASK_SCOPE": "m1", "W3FIX": None, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
JG = json.load(open(f"{G}/results/judge_gate.json"))
ARMS = {"yearly_s42": (f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_BASE_s42.npz", "(default f10_V2MAIN_s{FSEED})", "42", JG["arms"]["BASE_s42"]["sha256"]),
        "yearly_s2027": (f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_BASE_s2027.npz", "(default f10_V2MAIN_s{FSEED})", "2027", JG["arms"]["BASE_s2027"]["sha256"]),
        "R0_s42": (f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_G_mE1_R0.npz", "f10_gate_mE1_R0_s42.npy", "42", JG["arms"]["G_mE1_R0"]["sha256"]),
        "R0_s2027": (f"{B}/replay/dev_alt/probe_artifacts/w10_ablation_series_G_mE1s2027_R0_spl27.npz", "f10_gate_mE1s2027_R0_spl27.npy", "2027", None),
        "CONST42": (f"{B}/replay/dev_alt/probe_artifacts/w10_ablation_series_G_mE1c_R0_spl42.npz", "f10_gate_mE1c_R0_spl42.npy", "42", None),
        "CONST42_spl27": (f"{B}/replay/dev_alt/probe_artifacts/w10_ablation_series_G_mE1c_R0_spl27.npz", "f10_gate_mE1c_R0_spl27.npy", "2027", None)}
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
OUT = {"arm": ARM, "n_anchors": int(len(ts0)), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "arms": META, "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "levels": {}, "deltas": {}, "reading": {}, "ic": {}}
p(f"<!-- judge_gate_addendum2.py: n={len(ts0)} {iso(ts0[0])}→{iso(ts0[-1])}; windows {OUT['windows']}; bootstrap UTC-day 2000 seed {SEED} -->")
p("## AD2-1 · Levels per gross (bps/anchor); VERIFIED judge_gate_addendum2.json levels")
p("| arm | FPRED | seed | FROZEN [CI95] | S | maxDD | turn/gross | FULL [CI95] | S | 2025-01/02 | 2025 full | 2026≤cut |"); p("|---|---|---|---|---|---|---|---|---|---|---|---|")
for k in keys:
    row = {}
    for w, m in WIN.items():
        x = G_[k][m]; row[w] = {"n": int(m.sum()), "mean": float(x.mean()), "sharpe": sharpe(x), "maxDD_bps": maxdd(x), "turn_per_gross": float(TPG[k][m].mean())}
        if w in (PW, FW): row[w]["boot"] = boot(G_[k], m)
    OUT["levels"][k] = row; a, b = row[PW], row[FW]
    p(f"| {k} | {META[k]['FPRED']} | {META[k]['FSEED']} | **{a['mean']:+.3f}** [{a['boot']['lo']:+.3f}, {a['boot']['hi']:+.3f}] | {a['sharpe']:+.2f} | {a['maxDD_bps']:.0f} | {a['turn_per_gross']:.5f} | **{b['mean']:+.3f}** [{b['boot']['lo']:+.3f}, {b['boot']['hi']:+.3f}] | {b['sharpe']:+.2f} | {row['2025-01/02']['mean']:+.3f} | {row['2025 full']['mean']:+.3f} | {row['2026<=cut']['mean']:+.3f} |")
PAIRS = [("CONST42", "yearly_s42", "CONST(seed 42 every fold) − yearly s42 [primary]"), ("CONST42_spl27", "yearly_s2027", "CONST(pre-2025 = yearly s2027) − yearly s2027"), ("CONST42", "yearly_s2027", "CONST − yearly s2027"),
         ("CONST42", "R0_s42", "CONST − R0(mE1, s42; seed per fold)"), ("CONST42", "R0_s2027", "CONST − R0(mE1, s2027)"), ("R0_s42", "yearly_s42", "R0(mE1,s42) − yearly s42 [reference, §0.4]"), ("R0_s2027", "yearly_s2027", "R0(mE1,s2027) − yearly s2027 [reference, §10]")]
DW = ("pre-2025", "2025-01/02", "2025 full", "2026<=cut", PW, FW)
p("\n## AD2-2 · Paired Δ per gross (Δg = g_x − g_ref by anchor; UTC-day-block bootstrap; Δ [CI95] P(Δ>0)); VERIFIED judge_gate_addendum2.json deltas")
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
# ── frozen reading (a)/(b)/(c) ──
def cell(name, w): return OUT["deltas"][name]["windows"][w]
R = {}
for w in (PW, FW):
    c42 = cell("CONST(seed 42 every fold) − yearly s42 [primary]", w); c27 = cell("CONST(pre-2025 = yearly s2027) − yearly s2027", w)
    m42 = cell("R0(mE1,s42) − yearly s42 [reference, §0.4]", w); m27 = cell("R0(mE1,s2027) − yearly s2027 [reference, §10]", w)
    within = lambda c: (abs(c["mean"]) <= 0.05) and (c["lo"] <= 0 <= c["hi"]); upper_neg = lambda c: c["hi"] < 0
    a_ = within(c42) and within(c27) and upper_neg(m42) and upper_neg(m27); b_ = upper_neg(c42) and upper_neg(c27)
    R[w] = {"const_vs_yearly_s42": [c42["mean"], c42["lo"], c42["hi"]], "const_vs_yearly_s2027": [c27["mean"], c27["lo"], c27["hi"]], "mE1_vs_yearly_s42": [m42["mean"], m42["lo"], m42["hi"]], "mE1_vs_yearly_s2027": [m27["mean"], m27["lo"], m27["hi"]],
            "a_seed_churn": bool(a_), "b_refit_form": bool(b_), "verdict": "(a) init/seed churn ⇒ candidate = monthly refit with fixed init seed (or freeze)" if a_ else ("(b) refit form itself ⇒ freeze-to-yearly stands" if b_ else "(c) UNDECIDED ⇒ both candidates stay open")}
OUT["reading"] = R
p("\n## AD2-3 · Frozen reading (lead 09-05): (a) |CONST − yearly| ≤ 0.05 with CI ∋ 0 (both yearly seeds) while mE1 − yearly CI upper < 0 (both seeds) ⇒ seed churn; (b) CONST − yearly CI upper < 0 (both) ⇒ refit form; (c) otherwise UNDECIDED")
p("| window | CONST − yearly s42 | CONST − yearly s2027 | mE1 s42 − yearly s42 | mE1 s2027 − yearly s2027 | (a) | (b) | verdict |"); p("|---|---|---|---|---|---|---|---|")
for w, r in R.items():
    g = lambda v: f"{v[0]:+.3f} [{v[1]:+.3f},{v[2]:+.3f}]"
    p(f"| {w} | {g(r['const_vs_yearly_s42'])} | {g(r['const_vs_yearly_s2027'])} | {g(r['mE1_vs_yearly_s42'])} | {g(r['mE1_vs_yearly_s2027'])} | {r['a_seed_churn']} | {r['b_refit_form']} | **{r['verdict']}** |")
# ── score level ──
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; Y4 = A["y4s"]; nA = len(E); nB = len(np.load("/workspace/data/dlw_targets.npz", allow_pickle=True)["E_ts"])
def ics(P):
    ic = np.full(nA, np.nan)
    for i in range(int(np.searchsorted(E, T25)), nA):
        if not np.isfinite(P[i]).any(): continue
        mm = MEM[i]; a = P[i, mm]; b = Y4[i, mm]; ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() >= 30: ic[i] = spearmanr(a[ok], b[ok]).correlation
    return ic
def to_ext(p): Q = np.full((nA, 829), np.nan, np.float32); X = np.load(p); Q[:len(X)] = X; return Q
S = {"CONST42": np.load(f"{M}/preds/f10_V2MAIN_mE1c_s42.npy"), "R0_s42": np.load(f"{G}/series/mE1_R0.npy"), "R0_s2027": np.load(f"{B}/mwf_s2027/preds/f10_V2MAIN_mE1_s2027.npy"), "yearly_s42": to_ext("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"), "yearly_s2027": to_ext("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy")}
IC = {k: ics(v) for k, v in S.items()}; Ed = E // 86400
def bootE(x, m):
    v = x[m]; d = Ed[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud); s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "mean": float(v.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5))}
p("\n## AD2-4 · Score level: per-anchor rank IC (same anchor set); ΔIC with UTC-day-block bootstrap")
p("| window | IC CONST | IC R0 s42 | IC R0 s2027 | IC yearly s42 | IC yearly s2027 | ΔIC CONST−yearly s42 | ΔIC CONST−R0 s42 |"); p("|---|---|---|---|---|---|---|---|")
for w, m in {PW: (E >= T2503) & (E <= CUT), FW: (E >= T25) & (E <= CUT)}.items():
    mm = m.copy()
    for k in IC: mm &= np.isfinite(IC[k])
    d1 = bootE(IC["CONST42"] - IC["yearly_s42"], mm); d2 = bootE(IC["CONST42"] - IC["R0_s42"], mm)
    OUT["ic"][w] = {"n": int(mm.sum()), "levels": {k: float(IC[k][mm].mean()) for k in IC}, "dIC_CONST_vs_yearly_s42": d1, "dIC_CONST_vs_R0_s42": d2}
    p(f"| {w} (n={mm.sum()}) | {IC['CONST42'][mm].mean():+.4f} | {IC['R0_s42'][mm].mean():+.4f} | {IC['R0_s2027'][mm].mean():+.4f} | {IC['yearly_s42'][mm].mean():+.4f} | {IC['yearly_s2027'][mm].mean():+.4f} | {d1['mean']:+.4f} [{d1['lo']:+.4f},{d1['hi']:+.4f}] | {d2['mean']:+.4f} [{d2['lo']:+.4f},{d2['hi']:+.4f}] |")
os.makedirs(f"{M}/results", exist_ok=True); json.dump(OUT, open(f"{M}/results/judge_gate_addendum2.json", "w"), indent=1, default=float); open(f"{M}/results/addendum2_tables.md", "w").write("\n".join(T) + "\n")
for w, r in R.items(): print(f"===== §11 READING [{w}]: CONST−yearly s42 {r['const_vs_yearly_s42'][0]:+.4f} [{r['const_vs_yearly_s42'][1]:+.4f},{r['const_vs_yearly_s42'][2]:+.4f}] | CONST−yearly s2027 {r['const_vs_yearly_s2027'][0]:+.4f} [{r['const_vs_yearly_s2027'][1]:+.4f},{r['const_vs_yearly_s2027'][2]:+.4f}] ⇒ {r['verdict']}")
print("ADDENDUM2_JUDGE_DONE", flush=True)
