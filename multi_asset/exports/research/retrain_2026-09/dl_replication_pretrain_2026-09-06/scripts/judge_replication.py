"""judge_replication.py — PREREG_dl_monthly_earlystop §5 (c63a216) seed-2027 replication judge, written before any replication number was seen.
Arms (same device, health-check main arm, d30_n2_c42, prod caliber; pre-2025 rows spliced from yearly s2027 = spl27, the s2027 family convention):
  yearly_s2027 (dl_monthly_gate BASE_s2027), R0_s2027 (mE1 seed-per-fold 2027; trackB G_mE1s2027_R0_spl27), FLOOR5_s2027 (mE1cF5s27 spl27), FIX7_s2027 (mE1cX7s27 spl27);
  seed-42 references FLOOR5 / FIX7 / CONST42 / yearly_s42 for the seed-consistency table.
Reading (§5, frozen): arm replicates ⇔ ARM_s2027 − R0_s2027 CI95 lower > 0 AND ARM_s2027 − yearly_s2027 Δ ≥ −0.05 (CI ∋ 0 or lower > 0); ARM_s2027 − yearly_s2027 CI upper < 0 ⇒ arm fails;
otherwise UNDECIDED. Evaluated on the frozen window 2025-03→2026-08-10 (primary) and the full window. Secondary: best_ep changes, adjacent-month agreement, ΔIC, turnover, maxDD, per-year, drop-best-month.
usage: judge_replication.py → earlystop/results/judge_replication.json + replication_tables.md"""
import os, json, time, calendar, hashlib, glob
import numpy as np
from scipy.stats import spearmanr
B = "/workspace/review_scratch/allweather_trackB"; M = f"{B}/earlystop"; G = "/workspace/review_scratch/dl_monthly_gate"; PA = f"{B}/replay/dev_alt/probe_artifacts"; NB = 2000; SEED = 20260905; ARM = "d30_n2_c42"
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); T2503 = calendar.timegm((2025, 3, 1, 0, 0, 0)); T26 = calendar.timegm((2026, 1, 1, 0, 0, 0))
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
EXPECT = {"LEGS": "101", "CAL": "log", "LOOK": 900, "WRULE": "msharpe", "MEMBERS_TOPN": 829, "TRADE_TOPN": 0, "FTRIM": "zero", "UMASK_SCOPE": "m1", "W3FIX": None, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
JG = json.load(open(f"{G}/results/judge_gate.json"))
ARMS = {"yearly_s2027": (f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_BASE_s2027.npz", "(default f10_V2MAIN_s{FSEED})", "2027", JG["arms"]["BASE_s2027"]["sha256"]), "yearly_s42": (f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_BASE_s42.npz", "(default f10_V2MAIN_s{FSEED})", "42", JG["arms"]["BASE_s42"]["sha256"]),
        "R0_s2027": (f"{PA}/w10_ablation_series_G_mE1s2027_R0_spl27.npz", "f10_gate_mE1s2027_R0_spl27.npy", "2027", None), "FLOOR5_s2027": (f"{PA}/w10_ablation_series_G_mE1cF5s27_R0_spl27.npz", "f10_gate_mE1cF5s27_R0_spl27.npy", "2027", None), "FIX7_s2027": (f"{PA}/w10_ablation_series_G_mE1cX7s27_R0_spl27.npz", "f10_gate_mE1cX7s27_R0_spl27.npy", "2027", None),
        "CONST42": (f"{PA}/w10_ablation_series_G_mE1c_R0_spl42.npz", "f10_gate_mE1c_R0_spl42.npy", "42", None), "FLOOR5": (f"{PA}/w10_ablation_series_G_mE1cF5_R0_spl42.npz", "f10_gate_mE1cF5_R0_spl42.npy", "42", None), "FIX7": (f"{PA}/w10_ablation_series_G_mE1cX7_R0_spl42.npz", "f10_gate_mE1cX7_R0_spl42.npy", "42", None)}
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
p(f"<!-- judge_replication.py: n={len(ts0)} {iso(ts0[0])}→{iso(ts0[-1])}; windows {OUT['windows']}; bootstrap UTC-day 2000 seed {SEED} -->")
p("## AD5-1 · Levels per gross (bps/anchor); VERIFIED judge_replication.json levels")
p("| arm | FPRED | seed | FROZEN [CI95] | S | maxDD | turn/gross | FULL [CI95] | S | 2025-01/02 | 2025 full | 2026≤cut |"); p("|---|---|---|---|---|---|---|---|---|---|---|---|")
for k in keys:
    row = {}
    for w, m in WIN.items():
        x = G_[k][m]; row[w] = {"n": int(m.sum()), "mean": float(x.mean()), "sharpe": sharpe(x), "maxDD_bps": maxdd(x), "turn_per_gross": float(TPG[k][m].mean()), "nav_pct_yr_2x": float(x.mean() * 43.8)}
        if w in (PW, FW): row[w]["boot"] = boot(G_[k], m)
    OUT["levels"][k] = row; a, b = row[PW], row[FW]
    p(f"| {k} | {META[k]['FPRED']} | {META[k]['FSEED']} | **{a['mean']:+.3f}** [{a['boot']['lo']:+.3f}, {a['boot']['hi']:+.3f}] | {a['sharpe']:+.2f} | {a['maxDD_bps']:.0f} | {a['turn_per_gross']:.5f} | **{b['mean']:+.3f}** [{b['boot']['lo']:+.3f}, {b['boot']['hi']:+.3f}] | {b['sharpe']:+.2f} | {row['2025-01/02']['mean']:+.3f} | {row['2025 full']['mean']:+.3f} | {row['2026<=cut']['mean']:+.3f} |")
PAIRS = [("FLOOR5_s2027", "R0_s2027", "FLOOR5_s2027 − R0_s2027 [§5 primary]"), ("FLOOR5_s2027", "yearly_s2027", "FLOOR5_s2027 − yearly_s2027 [§5 primary]"), ("FIX7_s2027", "R0_s2027", "FIX7_s2027 − R0_s2027 [§5 primary]"), ("FIX7_s2027", "yearly_s2027", "FIX7_s2027 − yearly_s2027 [§5 primary]"),
         ("FLOOR5_s2027", "FIX7_s2027", "FLOOR5_s2027 − FIX7_s2027"), ("FLOOR5", "R0_s2027", "FLOOR5(s42) − R0_s2027 [cross-seed info]"), ("R0_s2027", "yearly_s2027", "R0_s2027 − yearly_s2027 [§10 reference]"), ("FLOOR5", "yearly_s42", "FLOOR5(s42) − yearly_s42 [§12 reference]"), ("FIX7", "yearly_s42", "FIX7(s42) − yearly_s42 [§12 reference]")]
DW = ("pre-2025", "2025-01/02", "2025 full", "2026<=cut", PW, FW)
p("\n## AD5-2 · Paired Δ per gross (Δg = g_x − g_ref by anchor; UTC-day-block bootstrap; Δ [CI95] P(Δ>0)); VERIFIED judge_replication.json deltas")
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
R = {}
for w in (PW, FW):
    per = {}
    for arm in ("FLOOR5_s2027", "FIX7_s2027"):
        r0 = OUT["deltas"][f"{arm} − R0_s2027 [§5 primary]"]["windows"][w]; y = OUT["deltas"][f"{arm} − yearly_s2027 [§5 primary]"]["windows"][w]
        rep_ok = (r0["lo"] > 0) and (y["mean"] >= -0.05) and ((y["lo"] <= 0 <= y["hi"]) or y["lo"] > 0); fail = y["hi"] < 0
        per[arm] = {"vs_R0_s2027": [r0["mean"], r0["lo"], r0["hi"]], "vs_yearly_s2027": [y["mean"], y["lo"], y["hi"]], "R0_CI_lower_gt0": bool(r0["lo"] > 0), "yearly_delta_ge_-0.05_and_CI_ok": bool((y["mean"] >= -0.05) and ((y["lo"] <= 0 <= y["hi"]) or y["lo"] > 0)), "yearly_CI_upper_lt0": bool(fail), "verdict": "复验成立" if rep_ok else ("复验失败" if fail else "UNDECIDED")}
    R[w] = per
OUT["reading"] = R
p("\n## AD5-3 · Frozen replication reading (PREREG_dl_monthly_earlystop §5): arm replicates ⇔ ARM_s2027 − R0_s2027 CI lower > 0 ∧ ARM_s2027 − yearly_s2027 Δ ≥ −0.05 (CI ∋ 0 or lower > 0); ARM − yearly_s2027 CI upper < 0 ⇒ fails; else UNDECIDED")
p("| window | arm | − R0_s2027 | lower>0 | − yearly_s2027 | Δ≥−0.05 ∧ CI ok | upper<0 | verdict |"); p("|---|---|---|---|---|---|---|---|")
for w, per in R.items():
    for arm, r in per.items():
        g = lambda v: f"{v[0]:+.3f} [{v[1]:+.3f},{v[2]:+.3f}]"; p(f"| {w} | {arm} | {g(r['vs_R0_s2027'])} | {r['R0_CI_lower_gt0']} | {g(r['vs_yearly_s2027'])} | {r['yearly_delta_ge_-0.05_and_CI_ok']} | {r['yearly_CI_upper_lt0']} | **{r['verdict']}** |")
# score level
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; Y4 = A["y4s"]; nA = len(E)
def ics(P):
    ic = np.full(nA, np.nan)
    for i in range(int(np.searchsorted(E, T25)), nA):
        if not np.isfinite(P[i]).any(): continue
        mm = MEM[i]; a = P[i, mm]; b = Y4[i, mm]; ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() >= 30: ic[i] = spearmanr(a[ok], b[ok]).correlation
    return ic
def to_ext(p): Q = np.full((nA, 829), np.nan, np.float32); X = np.load(p); Q[:len(X)] = X; return Q
S = {"FLOOR5_s2027": np.load(f"{M}/FLOOR5_s2027/preds/f10_V2MAIN_mE1cF5s27_s2027.npy"), "FIX7_s2027": np.load(f"{M}/FIX7_s2027/preds/f10_V2MAIN_mE1cX7s27_s2027.npy"), "R0_s2027": np.load(f"{B}/mwf_s2027/preds/f10_V2MAIN_mE1_s2027.npy"), "yearly_s2027": to_ext("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy")}
IC = {k: ics(v) for k, v in S.items()}; Ed = E // 86400
def bootE(x, m):
    v = x[m]; d = Ed[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud); s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "mean": float(v.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5))}
p("\n## AD5-4 · Score level (seed 2027 family): per-anchor rank IC; ΔIC with UTC-day-block bootstrap")
p("| window | IC FLOOR5_s2027 | IC FIX7_s2027 | IC R0_s2027 | IC yearly_s2027 | ΔIC FLOOR5−yearly | ΔIC FIX7−yearly | ΔIC FLOOR5−R0 | ΔIC FIX7−R0 |"); p("|---|---|---|---|---|---|---|---|---|")
for w, m in {PW: (E >= T2503) & (E <= CUT), FW: (E >= T25) & (E <= CUT)}.items():
    mm = m.copy()
    for k in IC: mm &= np.isfinite(IC[k])
    d = {nm: bootE(IC[a] - IC[b], mm) for nm, a, b in (("F5_y", "FLOOR5_s2027", "yearly_s2027"), ("X7_y", "FIX7_s2027", "yearly_s2027"), ("F5_r", "FLOOR5_s2027", "R0_s2027"), ("X7_r", "FIX7_s2027", "R0_s2027"))}
    OUT["ic"][w] = {"n": int(mm.sum()), "levels": {k: float(IC[k][mm].mean()) for k in IC}, "deltas": d}; g = lambda q: f"{q['mean']:+.4f} [{q['lo']:+.4f},{q['hi']:+.4f}]"
    p(f"| {w} (n={mm.sum()}) | {IC['FLOOR5_s2027'][mm].mean():+.4f} | {IC['FIX7_s2027'][mm].mean():+.4f} | {IC['R0_s2027'][mm].mean():+.4f} | {IC['yearly_s2027'][mm].mean():+.4f} | {g(d['F5_y'])} | {g(d['X7_y'])} | {g(d['F5_r'])} | {g(d['X7_r'])} |")
os.makedirs(f"{M}/results", exist_ok=True); json.dump(OUT, open(f"{M}/results/judge_replication.json", "w"), indent=1, default=float); open(f"{M}/results/replication_tables.md", "w").write("\n".join(T) + "\n")
for w, per in R.items():
    for arm, r in per.items(): print(f"===== §5 REPLICATION [{w}] {arm}: −R0_s2027 {r['vs_R0_s2027'][0]:+.4f} [{r['vs_R0_s2027'][1]:+.4f},{r['vs_R0_s2027'][2]:+.4f}] | −yearly_s2027 {r['vs_yearly_s2027'][0]:+.4f} [{r['vs_yearly_s2027'][1]:+.4f},{r['vs_yearly_s2027'][2]:+.4f}] ⇒ {r['verdict']}")
print("REPLICATION_JUDGE_DONE", flush=True)
