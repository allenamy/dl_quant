#!/usr/bin/env python3
"""judge_streamT.py — PREREG_retrain_reeval_corrected_pipeline_2026-09-19 (sha256 9b403aad…, commit 4a96358ec) §3, transcribed; written BEFORE any arm number.

Formulas are NOT re-implemented: load / level / delta / boot / maxdd_anchor / sharpe_daily are imported from the table device
fp2_per_year_table.py (sha256 230e3c79…, the device that published PER_YEAR_TABLE_REALCOST_2026-09-17), so
  g   = net_ex / gross_total per anchor (bps per unit gross), variant d30_n2_c42
  CI  = paired UTC-day block bootstrap, NB = 2000, default_rng([20260905, k])
  Sharpe = daily (UTC-day compounded at L=1, √365);  maxDD = NAV compounded PER ANCHOR at L = 2.0 (day-end sampled reported too);  turnover = tau_raw mean.
Order (frozen): (0) reproduce A1's published W_ALPHA g (0.6166582… / 0.6313477…) from THIS stream's replay tree — the reproduced arm file must equal
the published arm file's d30_n2_c42_rec bitwise and its g must equal the published value — else REFUSE (rc 3) before any Δ is computed.
(1) Δg = g_X − g_B per anchor, B = A1 (reproduced), on W_T = 2025-01-01T00Z .. 2026-08-30T20Z inclusive (main), and the 2025 / 2026 splits (report).
(2) Reading (W_T only): (A) CANDIDATE ⇔ both seeds' CI95 lower > 0; (B) REJECT ⇔ both seeds' CI95 upper < 0; else (C) UNDECIDED.
    EQUIVALENT (reported alongside) ⇔ both seeds' CI95 ⊂ [−0.05, +0.05] (δ = 0.05). K = 3 attempts (T1, T2, T3) counted toward DSR.
env: ARMS_DIR PUB_DIR PUB_JSON TABLE_DEV OUT_JSON OUT_MD [ARMS=T1,T2,T3] [SEEDS=42,2027] [EXPECT_JSON=per-arm expected SLOW/FPRED]"""
import calendar, hashlib, importlib.util, json, os, sys, time
import numpy as np
E = {k: os.environ.get(k, "") for k in ("ARMS_DIR", "PUB_DIR", "PUB_JSON", "TABLE_DEV", "OUT_JSON", "OUT_MD", "ARMS", "SEEDS", "EXPECT_JSON")}
ARMS = (E["ARMS"] or "T1,T2,T3").split(","); SEEDS = (E["SEEDS"] or "42,2027").split(","); LEV = 2.0; DELTA_EQ = 0.05
spec = importlib.util.spec_from_file_location("tbl", E["TABLE_DEV"]); T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
def sha(p): return T.sha(p)
rec = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%FT%TZ", time.gmtime()), "env": E,
       "table_device": E["TABLE_DEV"], "table_device_sha256": sha(E["TABLE_DEV"]), "prereg": "docs/PREREG_retrain_reeval_corrected_pipeline_2026-09-19.md sha256 9b403aad…",
       "reading": {"A": "both seeds CI95 lower > 0 (W_T)", "B": "both seeds CI95 upper < 0 (W_T)", "C": "otherwise", "EQUIVALENT": f"both seeds CI95 within [-{DELTA_EQ}, +{DELTA_EQ}]", "K": 3},
       "windows": {"W_T": "2025-01-01T00:00:00Z .. 2026-08-30T20:00:00Z inclusive", "2025": "W_T & UTC year 2025", "2026": "W_T & UTC year 2026"}, "repro": {}, "arms": {}, "verdict": {}}
def refuse(msg):
    rec["REFUSED"] = msg; json.dump(rec, open(E["OUT_JSON"], "w"), indent=1, default=str); print("JUDGE_REFUSED", msg, flush=True); sys.exit(3)
# ── (0) reproduce A1 ──
PUB = json.load(open(E["PUB_JSON"])); B = {}
for s in SEEDS:
    pub_p = os.path.join(E["PUB_DIR"], f"w10_ablation_series_V4_A1_dyn_s{s}.npz"); rep_p = os.path.join(E["ARMS_DIR"], f"w10_ablation_series_V4_A1R_dyn_s{s}.npz")
    xp = T.load(pub_p, "dyn", seed=s); xr = T.load(rep_p, "dyn", seed=s)
    if xp["why"] or xr["why"]: refuse(f"A1 s{s} load gates: pub {xp['why']} repro {xr['why']}")
    Zp, Zr = np.load(pub_p, allow_pickle=True), np.load(rep_p, allow_pickle=True)
    rec_eq = bool(np.array_equal(np.asarray(Zp["d30_n2_c42_rec"]), np.asarray(Zr["d30_n2_c42_rec"]))); w_eq = bool(np.array_equal(np.asarray(Zp["d30_n2_c42_W"]), np.asarray(Zr["d30_n2_c42_W"])))
    ts = xr["ts"]; UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); DAY = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in ts]); DAYS = (ts // 86400) * 86400
    WA = ts <= UB; WA[:900] = False
    if int(ts[900]) != calendar.timegm((2022, 6, 30, 0, 0, 0)): refuse("W_ALPHA start not on the pinned 2022-06-30T00Z")
    g_rep = T.level(xr, WA, DAY, DAYS, LEV)["g"]; g_pub = PUB["arms"][f"A1/dyn/s{s}"]["W_ALPHA"]["g"]
    ok = rec_eq and w_eq and abs(g_rep - g_pub) <= 1e-12
    rec["repro"][f"s{s}"] = {"published_file": pub_p, "published_sha256": xp["sha"], "reproduced_file": rep_p, "reproduced_sha256": xr["sha"], "rec_bitwise_equal": rec_eq, "W_bitwise_equal": w_eq,
                             "g_W_ALPHA_published": g_pub, "g_W_ALPHA_reproduced": g_rep, "abs_diff": abs(g_rep - g_pub), "PASS": bool(ok), "cfg": xr["cfg"]}
    print(f"A1 repro s{s}: published g {g_pub:.10f} reproduced {g_rep:.10f} rec bitwise {rec_eq} W bitwise {w_eq} -> {'PASS' if ok else 'FAIL'}", flush=True)
    if not ok: refuse(f"A1 s{s} not reproduced")
    B[s] = xr
# ── (1) arms ──
EXP = json.load(open(E["EXPECT_JSON"])) if E["EXPECT_JSON"] else {}
ts = B[SEEDS[0]]["ts"]; DAY = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in ts]); DAYS = (ts // 86400) * 86400; YEAR = np.array([time.gmtime(int(t)).tm_year for t in ts])
T25, UB = calendar.timegm((2025, 1, 1, 0, 0, 0)), calendar.timegm((2026, 8, 30, 20, 0, 0))
WT = (ts >= T25) & (ts <= UB); WIN = {"W_T": WT, "2025": WT & (YEAR == 2025), "2026": WT & (YEAR == 2026)}
rec["window_counts"] = {k: int(v.sum()) for k, v in WIN.items()}
rec["window_bounds"] = {k: [time.strftime("%FT%TZ", time.gmtime(int(ts[v][0]))), time.strftime("%FT%TZ", time.gmtime(int(ts[v][-1])))] for k, v in WIN.items()}
def four(x, m):
    lv = T.level(x, m, DAY, DAYS, LEV)
    return {"g": lv["g"], "g_ci95": lv["ci95"], "sharpe_daily": lv["sharpe_daily"], "maxdd_2x_anchor": lv["maxdd_L"], "maxdd_2x_dayend": lv["maxdd_L_dayend"], "turnover_tau_raw": lv["tau_raw"],
            "gross_total": lv["gross_total"], "pnl": lv["pnl"], "carry": lv["carry"], "cost": lv["cost"], "n": lv["n"]}
rec["baseline_A1"] = {f"s{s}": {w: four(B[s], m) for w, m in WIN.items()} for s in SEEDS}
for a in ARMS:
    rec["arms"][a] = {}
    for s in SEEDS:
        p = os.path.join(E["ARMS_DIR"], f"w10_ablation_series_V4_{a}_dyn_s{s}.npz")
        if not os.path.isfile(p): refuse(f"missing arm artifact {p} — the judge does not read a partial arm set")
        x = T.load(p, "dyn", seed=s)
        why = list(x["why"])
        if not np.array_equal(x["ts"], ts): why.append("ts axis differs from A1")
        if x["symbols"] != B[s]["symbols"]: why.append("symbols differ from A1")
        for k in ("UMASK_NPZ", "COSTB_JSON", "FSEED", "W3FIX", "FEMAT_NPZ"):
            if x["cfg"].get(k) != B[s]["cfg"].get(k): why.append(f"cfg {k} differs from A1: {x['cfg'].get(k)} vs {B[s]['cfg'].get(k)}")
        ex = EXP.get(a, {})
        for k in ("SLOW_NPY", "FPRED"):
            want = ex.get(k, "").replace("{s}", s)
            if want and x["cfg"].get(k) != want: why.append(f"cfg {k}={x['cfg'].get(k)} != expected {want}")
        if why: refuse(f"{a} s{s}: {why}")
        r = {"file": p, "sha256": x["sha"], "cfg": x["cfg"], "delta": {}, "metrics": {}}
        for w, m in WIN.items():
            r["delta"][w] = T.delta(x, B[s], m, DAY); r["metrics"][w] = four(x, m)
        rec["arms"][a][f"s{s}"] = r
        d = r["delta"]["W_T"]; print(f"{a} s{s} W_T Δg {d['dg']:+.4f} CI95 [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}] anchors differ {d['n_anchors_g_differs']}/{d['n']}", flush=True)
    ci = [rec["arms"][a][f"s{s}"]["delta"]["W_T"]["ci95"] for s in SEEDS]
    v = "A" if all(c[0] > 0 for c in ci) else ("B" if all(c[1] < 0 for c in ci) else "C")
    eq = all(c[0] >= -DELTA_EQ and c[1] <= DELTA_EQ for c in ci)
    rec["verdict"][a] = {"reading": {"A": "(A) CANDIDATE", "B": "(B) REJECT", "C": "(C) UNDECIDED"}[v], "EQUIVALENT": bool(eq), "ci95_W_T": {f"s{s}": c for s, c in zip(SEEDS, ci)},
                         "dg_W_T": {f"s{s}": rec["arms"][a][f"s{s}"]["delta"]["W_T"]["dg"] for s in SEEDS}, "K": 3}
    print(f"VERDICT {a}: {rec['verdict'][a]['reading']} | EQUIVALENT(δ={DELTA_EQ}) {eq} | K=3", flush=True)
json.dump(rec, open(E["OUT_JSON"], "w"), indent=1, default=str)
# ── markdown ──
f = lambda v, d=4: ("%+." + str(d) + "f") % v if isinstance(v, (int, float)) and v is not None else "—"
pc = lambda v: ("%.2f%%" % (100 * v)) if v is not None else "—"
L = [f"# stream T judge (judge_streamT.py {rec['self_sha256'][:8]}; table device {rec['table_device_sha256'][:8]}; {rec['utc']})", "",
     f"windows: {json.dumps(rec['window_bounds'])} counts {json.dumps(rec['window_counts'])}", "", "## (0) A1 reproduction", "",
     "| seed | published g W_ALPHA | reproduced | rec bitwise | W bitwise | PASS |", "|---|---|---|---|---|---|"]
for s in SEEDS:
    r = rec["repro"][f"s{s}"]; L.append(f"| {s} | {r['g_W_ALPHA_published']:.10f} | {r['g_W_ALPHA_reproduced']:.10f} | {r['rec_bitwise_equal']} | {r['W_bitwise_equal']} | {r['PASS']} |")
L += ["", "## (1) Δg vs A1 (paired, UTC-day block bootstrap 2000, rng [20260905,k])", "", "| arm | seed | window | n | Δg | CI95 | anchors differ | Δpnl / Δcarry / Δcost | Δτ |", "|---|---|---|---|---|---|---|---|---|"]
for a in ARMS:
    for s in SEEDS:
        for w in WIN:
            d = rec["arms"][a][f"s{s}"]["delta"][w]
            L.append(f"| {a} | {s} | {w} | {d['n']} | {f(d['dg'])} | [{f(d['ci95'][0])}, {f(d['ci95'][1])}] | {d['n_anchors_g_differs']} | {f(d['dpnl'],3)} / {f(d['dcarry'],3)} / {f(d['dcost'],3)} | {d['dtau_raw']:+.5f} |")
L += ["", "## (2) verdicts (W_T; K = 3)", "", "| arm | reading | EQUIVALENT (δ=0.05) | Δg s42 | CI s42 | Δg s2027 | CI s2027 |", "|---|---|---|---|---|---|---|"]
for a in ARMS:
    v = rec["verdict"][a]; c = v["ci95_W_T"]; g = v["dg_W_T"]
    L.append(f"| {a} | {v['reading']} | {v['EQUIVALENT']} | {f(g['s42'])} | [{f(c['s42'][0])}, {f(c['s42'][1])}] | {f(g['s2027'])} | [{f(c['s2027'][0])}, {f(c['s2027'][1])}] |")
L += ["", "## (3) four metrics (level g bps/anchor/gross · daily Sharpe · 2× maxDD per-anchor · turnover τ)", "", "| book | seed | window | g | Sharpe(daily) | maxDD 2× | τ |", "|---|---|---|---|---|---|---|"]
for s in SEEDS:
    for w in WIN:
        m = rec["baseline_A1"][f"s{s}"][w]; L.append(f"| A1 | {s} | {w} | {f(m['g'])} | {f(m['sharpe_daily'],3)} | {pc(m['maxdd_2x_anchor'])} | {m['turnover_tau_raw']:.5f} |")
    for a in ARMS:
        for w in WIN:
            m = rec["arms"][a][f"s{s}"]["metrics"][w]; L.append(f"| {a} | {s} | {w} | {f(m['g'])} | {f(m['sharpe_daily'],3)} | {pc(m['maxdd_2x_anchor'])} | {m['turnover_tau_raw']:.5f} |")
open(E["OUT_MD"], "w").write("\n".join(L) + "\n"); print("JUDGE_STREAMT_DONE", E["OUT_JSON"], flush=True)
