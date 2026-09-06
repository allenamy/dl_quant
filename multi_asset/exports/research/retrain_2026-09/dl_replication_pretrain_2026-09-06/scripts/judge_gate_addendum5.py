"""judge_gate_addendum5.py — frozen judge for the incremental-retrain family arms (PREREG_incremental_retrain_2026-09-06: §1.1 W1F5 c63a216; §3.1 P1 (+P1F) 2086c82;
§3.3 P0 doses 513ebf4), written before any of their numbers were seen. Same device (health-check main arm, d30_n2_c42, prod caliber), g = net_ex/gross_total,
UTC-day-block bootstrap 2000 seed 20260905, frozen window 2025-03→2026-08-10 (primary) + full window. Arms present are detected from the artifacts.
Extra columns (lead 09-06): same-month score agreement with CONST42 (per-anchor Spearman of raw scores, 2025-01→cut) and Δturnover vs the reference.
Readings (verbatim):
  §1.1 W1F5: (A-组合) W1F5 − FLOOR5 CI lower > 0 ∧ (W1F5 − yearly_s42 CI ∋ 0 or lower > 0); (A-单项够用) W1F5 − FLOOR5 CI ∋ 0; (B) W1F5 − FLOOR5 CI upper < 0; else UNDECIDED.
  §3.1 P1: (A) P1 − yearly_s42 CI ∋ 0 ∧ Δ ≥ −0.05 ∧ P1 − CONST42 lower > 0; 近期加权项 = P1 − W2 (lower > 0 加分 / upper < 0 丢信息); (B) P1 − yearly upper < 0; (C) else. P1F: P1F − P1, P1F − W1F5 reported (§1.1-form reading vs P1).
  §3.3 P0eE: (A) some E: P0eE − yearly_s42 CI ∋ 0 ∧ Δ ≥ −0.05 ∧ P0eE − CONST42 lower > 0 ∧ adjacent dose same sign (Δ vs yearly); (B) all three doses P0eE − yearly upper < 0; (C) else. Dose curve reported.
usage: judge_gate_addendum5.py → pretrain/results/judge_gate_addendum5.json + addendum5_tables.md"""
import os, json, time, calendar, hashlib
import numpy as np
from scipy.stats import spearmanr
B = "/workspace/review_scratch/allweather_trackB"; G = "/workspace/review_scratch/dl_monthly_gate"; PA = f"{B}/replay/dev_alt/probe_artifacts"; NB = 2000; SEED = 20260905; ARM = "d30_n2_c42"
CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); T25 = calendar.timegm((2025, 1, 1, 0, 0, 0)); T2503 = calendar.timegm((2025, 3, 1, 0, 0, 0)); T26 = calendar.timegm((2026, 1, 1, 0, 0, 0))
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
EXPECT = {"LEGS": "101", "CAL": "log", "LOOK": 900, "WRULE": "msharpe", "MEMBERS_TOPN": 829, "TRADE_TOPN": 0, "FTRIM": "zero", "UMASK_SCOPE": "m1", "W3FIX": None, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy"}
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
JG = json.load(open(f"{G}/results/judge_gate.json"))
ARMS = {"yearly_s42": (f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_BASE_s42.npz", "(default f10_V2MAIN_s{FSEED})", "42", JG["arms"]["BASE_s42"]["sha256"]), "yearly_s2027": (f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_BASE_s2027.npz", "(default f10_V2MAIN_s{FSEED})", "2027", JG["arms"]["BASE_s2027"]["sha256"]),
        "R0_s42": (f"{G}/replay/dev_alt/probe_artifacts/w10_ablation_series_G_mE1_R0.npz", "f10_gate_mE1_R0_s42.npy", "42", JG["arms"]["G_mE1_R0"]["sha256"]), "CONST42": (f"{PA}/w10_ablation_series_G_mE1c_R0_spl42.npz", "f10_gate_mE1c_R0_spl42.npy", "42", None),
        "FLOOR5": (f"{PA}/w10_ablation_series_G_mE1cF5_R0_spl42.npz", "f10_gate_mE1cF5_R0_spl42.npy", "42", None), "W1": (f"{PA}/w10_ablation_series_G_mE1w1_R0_spl42.npz", "f10_gate_mE1w1_R0_spl42.npy", "42", None), "W2": (f"{PA}/w10_ablation_series_G_mE1w2_R0_spl42.npz", "f10_gate_mE1w2_R0_spl42.npy", "42", None)}
OPT = {"W1F5": "mE1w1F5", "P1": "mE1p1", "P1F": "mE1p1F5", "P0e0": "mE1p0e0", "P0e1": "mE1p0e1", "P0e3": "mE1p0e3", "P0e10": "mE1p0e10"}
STITCH = {"W1F5": f"{B}/warmstart/W1F5/preds/f10_V2MAIN_mE1w1F5_s42.npy", "P1": f"{B}/pretrain/P1/preds/f10_V2MAIN_mE1p1_s42.npy", "P1F": f"{B}/pretrain/P1F/preds/f10_V2MAIN_mE1p1F5_s42.npy", "P0e0": f"{B}/pretrain/P0e0/preds/f10_V2MAIN_mE1p0e0_s42.npy", "P0e1": f"{B}/pretrain/P0e1/preds/f10_V2MAIN_mE1p0e1_s42.npy", "P0e3": f"{B}/pretrain/P0e3/preds/f10_V2MAIN_mE1p0e3_s42.npy", "P0e10": f"{B}/pretrain/P0e10/preds/f10_V2MAIN_mE1p0e10_s42.npy",
          "CONST42": f"{B}/mE1_constseed/preds/f10_V2MAIN_mE1c_s42.npy", "FLOOR5": f"{B}/earlystop/FLOOR5/preds/f10_V2MAIN_mE1cF5_s42.npy", "W1": f"{B}/warmstart/W1/preds/f10_V2MAIN_mE1w1_s42.npy", "W2": f"{B}/warmstart/W2/preds/f10_V2MAIN_mE1w2_s42.npy"}
for k, t in OPT.items():
    p = f"{PA}/w10_ablation_series_G_{t}_R0_spl42.npz"
    if os.path.exists(p): ARMS[k] = (p, f"f10_gate_{t}_R0_spl42.npy", "42", None)
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
# ── score-level: IC and same-month agreement with CONST (ext grid) ──
A = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True); E = A["E_ts"].astype(np.int64); MEM = A["members"]; Y4 = A["y4s"]; nA = len(E); Ed = E // 86400
def to_ext(p): Q = np.full((nA, 829), np.nan, np.float32); X = np.load(p); Q[:len(X)] = X; return Q
S = {k: np.load(v) for k, v in STITCH.items() if k in D or k == "CONST42"}; S["yearly_s42"] = to_ext("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy")
def ic_and_agree(P, Q):
    ic = np.full(nA, np.nan); ag = np.full(nA, np.nan)
    for i in range(int(np.searchsorted(E, T25)), nA):
        if not np.isfinite(P[i]).any(): continue
        mm = MEM[i]; a = P[i, mm]; y = Y4[i, mm]; q = Q[i, mm]; ok = np.isfinite(a) & np.isfinite(y)
        if ok.sum() >= 30: ic[i] = spearmanr(a[ok], y[ok]).correlation
        ok2 = np.isfinite(a) & np.isfinite(q)
        if ok2.sum() >= 30: ag[i] = spearmanr(a[ok2], q[ok2]).correlation
    return ic, ag
IC = {}; AG = {}
for k, P in S.items(): IC[k], AG[k] = ic_and_agree(P, S["CONST42"])
def bootE(x, m):
    v = x[m]; d = Ed[m]; ud, inv = np.unique(d, return_inverse=True); nd = len(ud); s = np.bincount(inv, weights=v, minlength=nd); c = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(NB, nd)); means = s[idx].sum(1) / c[idx].sum(1)
    return {"n": int(m.sum()), "mean": float(v.mean()), "lo": float(np.percentile(means, 2.5)), "hi": float(np.percentile(means, 97.5))}
T = []
def p(s=""): T.append(s); print(s)
OUT = {"arm": ARM, "n_anchors": int(len(ts0)), "arms_present": keys, "windows": {w: int(m.sum()) for w, m in WIN.items()}, "arms": META, "bootstrap": {"blocks": "UTC day", "n": NB, "seed": SEED}, "levels": {}, "deltas": {}, "reading": {}, "ic": {}, "agreement_with_CONST": {}}
p(f"<!-- judge_gate_addendum5.py: arms {keys}; n={len(ts0)}; windows {OUT['windows']}; bootstrap UTC-day 2000 seed {SEED} -->")
mE = (E >= T25) & (E <= CUT)
p("## AD6-1 · Levels per gross (bps/anchor) + score level + same-month agreement with CONST (2025-01→cut); VERIFIED judge_gate_addendum5.json")
p("| arm | seed | FROZEN [CI95] | S | maxDD (2×DD %NAV) | turn/gross | Δturn vs yearly | FULL [CI95] | S | 2025 full | 2026≤cut | IC frozen | agree w/ CONST (mean / p10) |"); p("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k in keys:
    row = {}
    for w, m in WIN.items():
        x = G_[k][m]; row[w] = {"n": int(m.sum()), "mean": float(x.mean()), "sharpe": sharpe(x), "maxDD_bps": maxdd(x), "turn_per_gross": float(TPG[k][m].mean()), "nav_pct_yr_2x": float(x.mean() * 43.8)}
        if w in (PW, FW): row[w]["boot"] = boot(G_[k], m)
    OUT["levels"][k] = row; a, b = row[PW], row[FW]; dt = (a["turn_per_gross"] / OUT["levels"]["yearly_s42"][PW]["turn_per_gross"] - 1) * 100 if "yearly_s42" in OUT["levels"] else float("nan")
    icf = float(np.nanmean(IC[k][(E >= T2503) & (E <= CUT)])) if k in IC else float("nan"); ag = AG.get(k); agm = (float(np.nanmean(ag[mE])), float(np.nanpercentile(ag[mE], 10))) if ag is not None else (float("nan"), float("nan"))
    OUT["agreement_with_CONST"][k] = {"mean": agm[0], "p10": agm[1]}; OUT["levels"][k]["ic_frozen"] = icf; OUT["levels"][k]["dturn_vs_yearly_pct"] = dt
    p(f"| {k} | {META[k]['FSEED']} | **{a['mean']:+.3f}** [{a['boot']['lo']:+.3f}, {a['boot']['hi']:+.3f}] | {a['sharpe']:+.2f} | {a['maxDD_bps']:.0f} ({a['maxDD_bps']*2/100:.1f}%) | {a['turn_per_gross']:.5f} | {dt:+.1f}% | **{b['mean']:+.3f}** [{b['boot']['lo']:+.3f}, {b['boot']['hi']:+.3f}] | {b['sharpe']:+.2f} | {row['2025 full']['mean']:+.3f} | {row['2026<=cut']['mean']:+.3f} | {icf:+.4f} | {agm[0]:+.3f} / {agm[1]:+.3f} |")
PAIRS = []
if "W1F5" in D: PAIRS += [("W1F5", "yearly_s42", "W1F5 − yearly_s42 [§1.1]"), ("W1F5", "CONST42", "W1F5 − CONST42 [§1.1]"), ("W1F5", "FLOOR5", "W1F5 − FLOOR5 [§1.1 key]"), ("W1F5", "W1", "W1F5 − W1 [§1.1]")]
if "P1" in D: PAIRS += [("P1", "yearly_s42", "P1 − yearly_s42 [§3.1]"), ("P1", "CONST42", "P1 − CONST42 [§3.1]"), ("P1", "W2", "P1 − W2 [§3.1 近期加权项]")]
if "P1F" in D: PAIRS += [("P1F", "P1", "P1F − P1 [§3.1 P1F]"), ("P1F", "W1F5", "P1F − W1F5 [§3.1 P1F]"), ("P1F", "yearly_s42", "P1F − yearly_s42")]
for e in ("1", "3", "10"):
    if f"P0e{e}" in D: PAIRS += [(f"P0e{e}", "yearly_s42", f"P0e{e} − yearly_s42 [§3.3]"), (f"P0e{e}", "CONST42", f"P0e{e} − CONST42 [§3.3]"), (f"P0e{e}", "W2", f"P0e{e} − W2 [§3.3]"), (f"P0e{e}", "P0e0", f"P0e{e} − P0e0 [§3.3 更新有无改动书]")]
if "P0e0" in D: PAIRS += [("P0e0", "yearly_s42", "P0e0 − yearly_s42 [never-update reference]"), ("P0e0", "CONST42", "P0e0 − CONST42 [reference]")]
DW = ("2025-01/02", "2025 full", "2026<=cut", PW, FW)
p("\n## AD6-2 · Paired Δ per gross (Δg = g_x − g_ref by anchor; UTC-day-block bootstrap; Δ [CI95] P(Δ>0)); VERIFIED judge_gate_addendum5.json deltas")
p("| pair | 2025-01/02 | 2025 full | 2026≤cut | **FROZEN** | **FULL** | ΔSharpe frozen | Δturn% | maxDD ref→x | Δ w/o best month (frozen) |"); p("|---|---|---|---|---|---|---|---|---|---|")
for kx, ky, name in PAIRS:
    dg = G_[kx] - G_[ky]; res = {}
    for w in DW:
        m = WIN[w]; b = boot(dg, m); b["exact_zero"] = bool(np.all(dg[m] == 0)); res[w] = b
    tx = float(TPG[kx][WIN[PW]].mean()); ty = float(TPG[ky][WIN[PW]].mean()); dturn = (tx / ty - 1) * 100
    mc = {str(mo): float(dg[(months == mo) & WIN[PW]].sum()) for mo in sorted(set(months[WIN[PW]].tolist()))}; best = max(mc, key=mc.get); drop = boot(dg, WIN[PW] & (months != int(best)))
    OUT["deltas"][name] = {"x": kx, "ref": ky, "windows": res, "dturn_pct_frozen": dturn, "dSharpe_frozen": sharpe(G_[kx][WIN[PW]]) - sharpe(G_[ky][WIN[PW]]), "maxDD_ref": maxdd(G_[ky][WIN[PW]]), "maxDD_x": maxdd(G_[kx][WIN[PW]]), "monthly_contrib_bps": mc, "best_month": best, "drop_best_month": drop}
    f = lambda w: f"{res[w]['mean']:+.3f} [{res[w]['lo']:+.3f},{res[w]['hi']:+.3f}] P{res[w]['P>0']:.2f}" + (" (=0)" if res[w]["exact_zero"] else "")
    p(f"| {name} | {f('2025-01/02')} | {f('2025 full')} | {f('2026<=cut')} | **{f(PW)}** | **{f(FW)}** | {OUT['deltas'][name]['dSharpe_frozen']:+.3f} | {dturn:+.1f}% | {maxdd(G_[ky][WIN[PW]]):.0f}→{maxdd(G_[kx][WIN[PW]]):.0f} | {drop['mean']:+.3f} [{drop['lo']:+.3f},{drop['hi']:+.3f}] (best {best} {mc[best]:+.0f}) |")
def cell(name, w): return OUT["deltas"][name]["windows"][w]
inside = lambda c: c["lo"] <= 0 <= c["hi"]
R = {}
for w in (PW, FW):
    r = {}
    if "W1F5" in D:
        f5 = cell("W1F5 − FLOOR5 [§1.1 key]", w); y = cell("W1F5 − yearly_s42 [§1.1]", w); w1 = cell("W1F5 − W1 [§1.1]", w)
        v = "(A-组合) 组合候选优先于单项" if (f5["lo"] > 0 and (inside(y) or y["lo"] > 0)) else ("(B) 热启动与早停修正相冲" if f5["hi"] < 0 else ("(A-单项够用) 以 FLOOR5/FIX7 单项为候选" if inside(f5) else "UNDECIDED"))
        r["W1F5"] = {"vs_FLOOR5": [f5["mean"], f5["lo"], f5["hi"]], "vs_yearly": [y["mean"], y["lo"], y["hi"]], "vs_W1": [w1["mean"], w1["lo"], w1["hi"]], "verdict": v}
    if "P1" in D:
        y = cell("P1 − yearly_s42 [§3.1]", w); c = cell("P1 − CONST42 [§3.1]", w); w2 = cell("P1 − W2 [§3.1 近期加权项]", w)
        v = "(A) 候选" if (inside(y) and y["mean"] >= -0.05 and c["lo"] > 0) else ("(B) 近期微调判负" if y["hi"] < 0 else "(C) UNDECIDED"); rw = "加分(下界>0)" if w2["lo"] > 0 else ("丢信息(上界<0)" if w2["hi"] < 0 else "含 0")
        r["P1"] = {"vs_yearly": [y["mean"], y["lo"], y["hi"]], "vs_CONST": [c["mean"], c["lo"], c["hi"]], "vs_W2": [w2["mean"], w2["lo"], w2["hi"]], "recent_weighting_term": rw, "verdict": v}
    if "P1F" in D:
        a = cell("P1F − P1 [§3.1 P1F]", w); b = cell("P1F − W1F5 [§3.1 P1F]", w); y = cell("P1F − yearly_s42", w)
        r["P1F"] = {"vs_P1": [a["mean"], a["lo"], a["hi"]], "vs_W1F5": [b["mean"], b["lo"], b["hi"]], "vs_yearly": [y["mean"], y["lo"], y["hi"]], "verdict": "(A-组合) floor 在近期微调之上再加" if (a["lo"] > 0 and (inside(y) or y["lo"] > 0)) else ("(B) 相冲" if a["hi"] < 0 else ("(A-单项够用)" if inside(a) else "UNDECIDED"))}
    doses = [e for e in ("1", "3", "10") if f"P0e{e}" in D]
    if doses:
        per = {}
        for e in doses:
            y = cell(f"P0e{e} − yearly_s42 [§3.3]", w); c = cell(f"P0e{e} − CONST42 [§3.3]", w); z0 = cell(f"P0e{e} − P0e0 [§3.3 更新有无改动书]", w); w2 = cell(f"P0e{e} − W2 [§3.3]", w)
            per[e] = {"vs_yearly": [y["mean"], y["lo"], y["hi"]], "vs_CONST": [c["mean"], c["lo"], c["hi"]], "vs_W2": [w2["mean"], w2["lo"], w2["hi"]], "vs_P0e0": [z0["mean"], z0["lo"], z0["hi"]], "A_single": bool(inside(y) and y["mean"] >= -0.05 and c["lo"] > 0), "yearly_upper_lt0": bool(y["hi"] < 0)}
        order = [e for e in ("1", "3", "10") if e in per]; sgn = {e: np.sign(per[e]["vs_yearly"][0]) for e in order}
        def adj_same(e):
            i = order.index(e); nb = [order[j] for j in (i - 1, i + 1) if 0 <= j < len(order)]; return any(sgn[n] == sgn[e] for n in nb)
        A_ = any(per[e]["A_single"] and adj_same(e) for e in order); B_ = len(order) == 3 and all(per[e]["yearly_upper_lt0"] for e in order)
        curve = [per[e]["vs_yearly"][0] for e in order]; mono = "单调下降(支持 epoch 多则过拟合近月)" if all(curve[i] > curve[i + 1] for i in range(len(curve) - 1)) else ("单调上升(一月数据仍在教东西)" if all(curve[i] < curve[i + 1] for i in range(len(curve) - 1)) else "非单调/平")
        r["P0"] = {"doses": per, "dose_curve_vs_yearly": dict(zip(order, curve)), "dose_curve_reading": mono, "verdict": "(A) 一月微调候选" if A_ else ("(B) 一月微调判负" if B_ else "(C) UNDECIDED")}
    R[w] = r
OUT["reading"] = R
p("\n## AD6-3 · Frozen readings (verbatim prereg sections); VERIFIED judge_gate_addendum5.json reading")
p("```json"); p(json.dumps(R, indent=1, ensure_ascii=False, default=float)); p("```")
p("\n## AD6-4 · Score level: per-anchor rank IC (frozen / full) and ΔIC vs yearly_s42 and vs CONST42 (UTC-day-block bootstrap)")
p("| arm | IC frozen | IC full | ΔIC vs yearly frozen | ΔIC vs CONST frozen | agree w/ CONST mean / p10 |"); p("|---|---|---|---|---|---|")
for k in keys:
    if k not in IC: continue
    mmF = (E >= T2503) & (E <= CUT) & np.isfinite(IC[k]) & np.isfinite(IC["yearly_s42"]) & np.isfinite(IC["CONST42"]); mmA = mE & np.isfinite(IC[k]) & np.isfinite(IC["yearly_s42"]) & np.isfinite(IC["CONST42"])
    d1 = bootE(IC[k] - IC["yearly_s42"], mmF); d2 = bootE(IC[k] - IC["CONST42"], mmF); OUT["ic"][k] = {"ic_frozen": float(IC[k][mmF].mean()), "ic_full": float(IC[k][mmA].mean()), "dIC_vs_yearly_frozen": d1, "dIC_vs_CONST_frozen": d2}
    ag = OUT["agreement_with_CONST"][k]; p(f"| {k} | {IC[k][mmF].mean():+.4f} | {IC[k][mmA].mean():+.4f} | {d1['mean']:+.4f} [{d1['lo']:+.4f},{d1['hi']:+.4f}] | {d2['mean']:+.4f} [{d2['lo']:+.4f},{d2['hi']:+.4f}] | {ag['mean']:+.3f} / {ag['p10']:+.3f} |")
os.makedirs(f"{B}/pretrain/results", exist_ok=True); json.dump(OUT, open(f"{B}/pretrain/results/judge_gate_addendum5.json", "w"), indent=1, default=float); open(f"{B}/pretrain/results/addendum5_tables.md", "w").write("\n".join(T) + "\n")
for w, r in R.items():
    for arm, v in r.items(): print(f"===== §14 READING [{w}] {arm}: {v.get('verdict')}")
print("ADDENDUM5_JUDGE_DONE", flush=True)
