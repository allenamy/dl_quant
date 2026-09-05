"""judge_gate_addendum.py — dl_monthly_gate addendum (lead 09-05): is "monthly (R0, mE1) worse than yearly on the frozen main window" a seed-42 artefact?
Same device (health-check main arm, d30_n2_c42, prod caliber), same g = net_ex/gross_total, same UTC-day-block bootstrap (2000, seed 20260905),
same frozen window 2025-03-01→2026-08-10 20Z (PREREG §A primary) AND the full window 2025-01-01→2026-08-10 20Z (f311321's 2025→26).
Arms: yearly s42 / s2027 (BASE_*, dl_monthly_gate artifacts, sha asserted vs judge_gate.json), R0(mE1, s42) (G_mE1_R0, dl_monthly_gate), R0(mE1, s2027)
spliced with yearly s2027 before 2025-01 (spl27, same-seed primary) and with yearly s42 (spl42). Pairs: R0s2027 − yearly s2027 [primary]; R0s2027(spl42) − yearly s42;
R0s2027 − yearly s42; R0s42 − yearly s42 / s2027 (Part 0 reproduction); R0s2027 − R0s42 (seed-to-seed); seed-mean R0 − seed-mean yearly.
Frozen reading (PREREG §A4): keepable ⇔ R0 − yearly CI95 upper > 0 on the frozen window. Reported both windows, both seeds, no new criterion.
usage: judge_gate_addendum.py → mwf_s2027/results/judge_gate_addendum.json + addendum_tables.md"""
import os, json, time, calendar, hashlib
import numpy as np
from scipy.stats import spearmanr
B = "/workspace/review_scratch/allweather_trackB"; M = f"{B}/mwf_s2027"; G = "/workspace/review_scratch/dl_monthly_gate"; NB = 2000; SEED = 20260905; ARM = "d30_n2_c42"
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
        "R0_s2027_spl42": (f"{B}/replay/dev_alt/probe_artifacts/w10_ablation_series_G_mE1s2027_R0_spl42.npz", "f10_gate_mE1s2027_R0_spl42.npy", "42", None)}
D = {}; META = {}
for key, (p, fpred, fseed, sha16) in ARMS.items():
    z = np.load(p, allow_pickle=True); cfg = json.loads(str(z["config_json"])); assert [str(c) for c in z["cols"]] == COLS
    for k, v in EXPECT.items(): assert cfg.get(k) == v, (key, k, cfg.get(k), v)
    assert cfg["FPRED"] == fpred and cfg["FSEED"] == fseed and abs(cfg["PHI"] - 0.45) < 1e-12 and cfg.get("PHIDYN", 0) == 0, (key, cfg["FPRED"], cfg["FSEED"])
    s16 = sha(p)[:16]; assert sha16 is None or s16 == sha16, (key, s16, sha16)
    Rr = z[f"{ARM}_rec"]; D[key] = {c: Rr[:, i] for i, c in enumerate(COLS)}; META[key] = {"artifact": p, "sha256_16": s16, "FPRED": fpred, "FSEED": fseed, "n": int(len(Rr)), "device": cfg.get("HEALTH", {}).get("device_sha256", "")[:16]}
keys = list(D); ts0 = D[keys[0]]["ts"].astype(np.int64)
for k in keys: assert np.array_equal(D[k]["ts"].astype(np.int64), ts0), k
days = ts0 // 86400; months = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in ts0])
WIN = {"pre-2025": ts0 < T25, "2025-01/02": (ts0 >= T25) & (ts0 < T2503), "FROZEN 2025-03->26<=cut": (ts0 >= T2503) & (ts0 <= CUT), "FULL 2025-01->26<=cut": (ts0 >= T25) & (ts0 <= CUT), "2025-03->12": (ts0 >= T2503) & (ts0 < T26), "2025 full": (ts0 >= T25) & (ts0 < T26), "2026<=cut": (ts0 >= T26) & (ts0 <= CUT), "2026-postcut": ts0 > CUT}
PW = "FROZEN 2025-03->26<=cut"; FW = "FULL 2025-01->26<=cut"
G_ = {k: D[k]["net_ex"] / D[k]["gross_total"] for k in keys}; TPG = {k: D[k]["turnover"] / D[k]["gross_total"] for k in keys}
G_["R0_seedmean"] = (G_["R0_s42"] + G_["R0_s2027"]) / 2; G_["yearly_seedmean"] = (G_["yearly_s42"] + G_["yearly_s2027"]) / 2; TPG["R0_seedmean"] = (TPG["R0_s42"] + TPG["R0_s2027"]) / 2; TPG["yearly_seedmean"] = (TPG["yearly_s42"] + TPG["yearly_s2027"]) / 2
rng = np.random.default_rng(SEED)
def boot(x, m):
    v = x[m]; d = days[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud); s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "n_days": int(nd), "mean": float(v.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5)), "P>0": float((means > 0).mean()), "nav_pct_yr_2x": float(v.mean() * 43.8)}
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(2190)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def maxdd(x): c = np.cumsum(x); return float(np.max(np.maximum.accumulate(c) - c)) if len(x) else float("nan")
T = []
def p(s=""): T.append(s); print(s)
OUT = {"arm": ARM, "n_anchors": int(len(ts0)), "windows": {w: int(m.sum()) for w, m in WIN.items()}, "arms": META, "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "levels": {}, "deltas": {}, "judge": {}, "ic": {}}
p(f"<!-- judge_gate_addendum.py: n={len(ts0)} {iso(ts0[0])}→{iso(ts0[-1])}; windows {OUT['windows']}; bootstrap UTC-day 2000 seed {SEED} -->")
p("## AD-1 · Levels per gross (bps/anchor); VERIFIED judge_gate_addendum.json levels")
p("| arm | FPRED | seed | FROZEN 2025-03→26≤cut [CI95] | S | maxDD | turn/gross | FULL 2025-01→26≤cut [CI95] | S | 2025-01/02 | 2025-03→12 | 2026≤cut | 2025 full |"); p("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k in list(keys) + ["R0_seedmean", "yearly_seedmean"]:
    row = {}
    for w, m in WIN.items():
        if m.sum() < 12: continue
        x = G_[k][m]; row[w] = {"n": int(m.sum()), "mean": float(x.mean()), "sharpe": sharpe(x), "maxDD_bps": maxdd(x), "turn_per_gross": float(TPG[k][m].mean()), "nav_pct_yr_2x": float(x.mean() * 43.8)}
        if w in (PW, FW): row[w]["boot"] = boot(G_[k], m)
    OUT["levels"][k] = row; a, b = row[PW], row[FW]; meta = META.get(k, {"FPRED": "(seed mean)", "FSEED": "42+2027"})
    p(f"| {k} | {meta['FPRED']} | {meta['FSEED']} | **{a['mean']:+.3f}** [{a['boot']['lo']:+.3f}, {a['boot']['hi']:+.3f}] | {a['sharpe']:+.2f} | {a['maxDD_bps']:.0f} | {a['turn_per_gross']:.5f} | **{b['mean']:+.3f}** [{b['boot']['lo']:+.3f}, {b['boot']['hi']:+.3f}] | {b['sharpe']:+.2f} | {row['2025-01/02']['mean']:+.3f} | {row['2025-03->12']['mean']:+.3f} | {row['2026<=cut']['mean']:+.3f} | {row['2025 full']['mean']:+.3f} |")
PAIRS = [("R0_s2027", "yearly_s2027", "R0(mE1,s2027) − yearly s2027 [same-seed, primary]"), ("R0_s2027_spl42", "yearly_s42", "R0(mE1,s2027; pre-2025 = yearly s42) − yearly s42"), ("R0_s2027", "yearly_s42", "R0(mE1,s2027) − yearly s42"),
         ("R0_s42", "yearly_s42", "R0(mE1,s42) − yearly s42 [Part 0 keepable_s42]"), ("R0_s42", "yearly_s2027", "R0(mE1,s42) − yearly s2027 [Part 0 keepable_s2027]"), ("R0_s2027", "R0_s42", "R0(mE1,s2027) − R0(mE1,s42) [seed-to-seed]"), ("yearly_s2027", "yearly_s42", "yearly s2027 − yearly s42 [seed-to-seed]"),
         ("R0_seedmean", "yearly_seedmean", "seed-mean R0(mE1) − seed-mean yearly")]
DW = ("pre-2025", "2025-01/02", "2025-03->12", "2025 full", "2026<=cut", PW, FW, "2026-postcut")
p("\n## AD-2 · Paired Δ per gross (Δg = g_x − g_ref by anchor; UTC-day-block bootstrap; Δ [CI95] P(Δ>0)); VERIFIED judge_gate_addendum.json deltas")
p("| pair | pre-2025 | 2025-01/02 | 2025-03→12 | 2025 full | 2026≤cut | **FROZEN 2025-03→26≤cut** | **FULL 2025-01→26≤cut** | ΔSharpe frozen/full | Δturn% frozen | maxDD ref→x (frozen) | Δ w/o best month (frozen) |"); p("|---|---|---|---|---|---|---|---|---|---|---|---|")
for kx, ky, name in PAIRS:
    dg = G_[kx] - G_[ky]; res = {}
    for w in DW:
        m = WIN[w]
        if m.sum() < 12: continue
        b = boot(dg, m); b["exact_zero"] = bool(np.all(dg[m] == 0)); b["maxabs"] = float(np.max(np.abs(dg[m]))); res[w] = b
    tx = float(TPG[kx][WIN[PW]].mean()); ty = float(TPG[ky][WIN[PW]].mean()); dturn = (tx / ty - 1) * 100
    mc = {}
    for mo in sorted(set(months[WIN[PW]].tolist())):
        mm = (months == mo) & WIN[PW]; mc[str(mo)] = float(dg[mm].sum())
    best = max(mc, key=mc.get); drop = boot(dg, WIN[PW] & (months != int(best)))
    OUT["deltas"][name] = {"x": kx, "ref": ky, "windows": res, "dturn_pct_frozen": dturn, "dSharpe": {PW: sharpe(G_[kx][WIN[PW]]) - sharpe(G_[ky][WIN[PW]]), FW: sharpe(G_[kx][WIN[FW]]) - sharpe(G_[ky][WIN[FW]])}, "maxDD_ref": maxdd(G_[ky][WIN[PW]]), "maxDD_x": maxdd(G_[kx][WIN[PW]]), "monthly_contrib_bps": mc, "best_month": best, "drop_best_month": drop}
    f = lambda w: (f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] P{res[w]['P>0']:.2f}" + (" (=0)" if res[w]["exact_zero"] else "")) if w in res else "n/a"
    p(f"| {name} | {f('pre-2025')} | {f('2025-01/02')} | {f('2025-03->12')} | {f('2025 full')} | {f('2026<=cut')} | **{f(PW)}** | **{f(FW)}** | {OUT['deltas'][name]['dSharpe'][PW]:+.3f} / {OUT['deltas'][name]['dSharpe'][FW]:+.3f} | {dturn:+.1f}% | {maxdd(G_[ky][WIN[PW]]):.0f}→{maxdd(G_[kx][WIN[PW]]):.0f} | {drop['mean']:+.3f} [{drop['lo']:+.3f},{drop['hi']:+.3f}] (best {best} {mc[best]:+.0f} bps) |")
# ── §A4 keepable reading, both windows ──
p("\n## AD-3 · §A4 'keepable' reading (keepable ⇔ R0 − yearly CI95 upper > 0), frozen window (as preregistered) and full window (f311321 convention)")
p("| pair | frozen Δ [CI95] | frozen upper>0 | full Δ [CI95] | full upper>0 | NAV %/yr @2× (frozen / full) |"); p("|---|---|---|---|---|---|")
for kx, ky, name in PAIRS:
    if not (kx.startswith("R0") and ky.startswith("yearly")): continue
    r = OUT["deltas"][name]["windows"]; a, b = r[PW], r[FW]
    OUT["judge"][name] = {"frozen": {"delta": a["mean"], "CI": [a["lo"], a["hi"]], "keepable_CI_upper>0": a["hi"] > 0}, "full": {"delta": b["mean"], "CI": [b["lo"], b["hi"]], "keepable_CI_upper>0": b["hi"] > 0}}
    p(f"| {name} | {a['mean']:+.3f} [{a['lo']:+.3f},{a['hi']:+.3f}] | {a['hi'] > 0} | {b['mean']:+.3f} [{b['lo']:+.3f},{b['hi']:+.3f}] | {b['hi'] > 0} | {a['nav_pct_yr_2x']:+.1f} / {b['nav_pct_yr_2x']:+.1f} |")
# ── score level: per-anchor rank IC of the s2027 monthly stitched file vs both yearly files (ext grid) ──
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; Y4 = A["y4s"]; nA = len(E); nB = len(np.load("/workspace/data/dlw_targets.npz", allow_pickle=True)["E_ts"])
def ics(P):
    ic = np.full(nA, np.nan)
    for i in range(int(np.searchsorted(E, T25)), nA):
        if not np.isfinite(P[i]).any(): continue
        mm = MEM[i]; a = P[i, mm]; b = Y4[i, mm]; ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() >= 30: ic[i] = spearmanr(a[ok], b[ok]).correlation
    return ic
def to_ext(p): Q = np.full((nA, 829), np.nan, np.float32); X = np.load(p); Q[:len(X)] = X; return Q
S = {"R0_s2027": np.load(f"{M}/preds/f10_V2MAIN_mE1_s2027.npy"), "R0_s42": np.load(f"{G}/series/mE1_R0.npy"), "yearly_s42": to_ext("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"), "yearly_s2027": to_ext("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy")}
IC = {k: ics(v) for k, v in S.items()}; Ed = E // 86400
def bootE(x, m):
    v = x[m]; d = Ed[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud); s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "mean": float(v.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5))}
WE = {PW: (E >= T2503) & (E <= CUT), FW: (E >= T25) & (E <= CUT), "2026<=cut": (E >= T26) & (E <= CUT)}
p("\n## AD-4 · Score level: per-anchor rank IC (ext grid, same anchor set = anchors where all four files are finite); ΔIC with UTC-day-block bootstrap")
p("| window | IC R0 s42 | IC R0 s2027 | IC yearly s42 | IC yearly s2027 | ΔIC R0s2027−yearly s2027 [CI95] | ΔIC R0s42−yearly s42 [CI95] | ΔIC R0s2027−R0s42 [CI95] |"); p("|---|---|---|---|---|---|---|---|")
for w, m in WE.items():
    mm = m.copy()
    for k in IC: mm &= np.isfinite(IC[k])
    d1 = bootE(IC["R0_s2027"] - IC["yearly_s2027"], mm); d2 = bootE(IC["R0_s42"] - IC["yearly_s42"], mm); d3 = bootE(IC["R0_s2027"] - IC["R0_s42"], mm)
    OUT["ic"][w] = {"n": int(mm.sum()), "levels": {k: float(IC[k][mm].mean()) for k in IC}, "dIC_R0s2027_vs_yearly_s2027": d1, "dIC_R0s42_vs_yearly_s42": d2, "dIC_R0s2027_vs_R0s42": d3}
    p(f"| {w} (n={mm.sum()}) | {IC['R0_s42'][mm].mean():+.4f} | {IC['R0_s2027'][mm].mean():+.4f} | {IC['yearly_s42'][mm].mean():+.4f} | {IC['yearly_s2027'][mm].mean():+.4f} | {d1['mean']:+.4f} [{d1['lo']:+.4f},{d1['hi']:+.4f}] | {d2['mean']:+.4f} [{d2['lo']:+.4f},{d2['hi']:+.4f}] | {d3['mean']:+.4f} [{d3['lo']:+.4f},{d3['hi']:+.4f}] |")
os.makedirs(f"{M}/results", exist_ok=True); json.dump(OUT, open(f"{M}/results/judge_gate_addendum.json", "w"), indent=1, default=float); open(f"{M}/results/addendum_tables.md", "w").write("\n".join(T) + "\n")
for name, v in OUT["judge"].items(): print(f"===== ADDENDUM keepable [{name}]: frozen {v['frozen']['delta']:+.4f} [{v['frozen']['CI'][0]:+.4f},{v['frozen']['CI'][1]:+.4f}] upper>0={v['frozen']['keepable_CI_upper>0']} | full {v['full']['delta']:+.4f} [{v['full']['CI'][0]:+.4f},{v['full']['CI'][1]:+.4f}] upper>0={v['full']['keepable_CI_upper>0']}")
print("ADDENDUM_JUDGE_DONE", flush=True)
