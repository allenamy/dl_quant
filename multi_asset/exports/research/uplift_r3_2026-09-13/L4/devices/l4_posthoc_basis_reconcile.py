#!/usr/bin/env python3
"""l4_posthoc_basis_reconcile.py -- L4 POST-HOC diagnostic (written after reading TABLES_L4.md T8; NOT in the PREREG; changes no reading and no verdict).
Question: the frozen run marks basis with the premium index (B2) and, as a descriptive cross-check, with Binance perp/spot closes (B1). On the same
positions the two markings disagree in sign and size (A01 S2426 net +0.266 vs -0.696 bps/anchor). Where does the B1-minus-B2 basis P&L come from?
Method: re-run the frozen state machine by exec-ing the constants/core section of the committed l4_run.py (sha asserted), assert the per-anchor base
net series equal L4_SERIES.npz bitwise for all 12 arms, then decompose basis P&L per hold (completed and open): telescoped B1 and B2, entry/exit
levels, the in-hold maximum |ln(1 + spot/perp - 1)| (price-identity guard value, T7 threshold ln 1.25 applied at entry only in the frozen spec),
and concentration of the B1-B2 difference. Writes <work>/POSTHOC_L4_basis_reconcile.json; prints one SUMMARY line.
Usage: python3 l4_posthoc_basis_reconcile.py <env_whitelist_csv> <work_dir> <path_to_l4_run.py>
"""
import os, sys, json, time, math, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
WORK = os.path.abspath(sys.argv[2]); RUNDEV = os.path.abspath(sys.argv[3])
import numpy as np
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def ut(y, m, d, h=0): return calendar.timegm((y, m, d, h, 0, 0))
RUN_SHA = "cfa2517120979a46881eae42e4968a34a8d529e8fc817a0a54e16e45a0fc8a22"; INP_SHA = "3d9d3466ce0078730c3630876d3767ba69da0135cfad9edf42fbfe59bfce05dd"
SER_SHA = "8ba4ba1fa6220d9763443a920ea37a9abcba0536f55954a6d5d7fa05c2bb4473"
assert sha(RUNDEV) == RUN_SHA and sha(os.path.join(WORK, "l4_inputs.npz")) == INP_SHA and sha(os.path.join(WORK, "L4_SERIES.npz")) == SER_SHA
REC = dict(device="l4_posthoc_basis_reconcile.py", label="POST-HOC", device_sha256=sha(os.path.abspath(__file__)), run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           run_device_sha256=RUN_SHA, inputs_sha256=INP_SHA, series_sha256=SER_SHA, python=sys.version.split()[0], numpy=np.__version__, affinity=sorted(os.sched_getaffinity(0)))
assert len(REC["affinity"]) <= 8
src = open(RUNDEV).read()
a = src.index("# ---------------------------------------------------------------- constants"); b = src.index("# ---------------------------------------------------------------- G-SYN")
NS_ = {"np": np, "math": math, "REC": {"gates": {}}}
exec(compile(src[a:b], "l4_run_core", "exec"), NS_)
ARMS = NS_["ARMS"]; prepare = NS_["prepare"]; simulate = NS_["simulate"]; account = NS_["account"]; CS_BASE = NS_["CS_BASE"]
Z = np.load(os.path.join(WORK, "l4_inputs.npz"), allow_pickle=True); SER = np.load(os.path.join(WORK, "L4_SERIES.npz"))
EG = Z["EG"].astype(np.int64); SYM = [str(s) for s in Z["SYM"]]; iW0 = int(Z["iW0"]); iW1 = int(Z["iW1"])
B2 = Z["B2"].astype(np.float64); B1 = Z["B1"].astype(np.float64)
D = prepare(Z["A"].astype(np.float64), Z["NEV"].astype(np.int16), Z["ELIG"].astype(bool), Z["TRAD"].astype(bool), Z["SPOT_OK"].astype(bool), B2, B1)
TSW = EG[iW0:iW1 + 1]; S2426 = TSW >= ut(2024, 1, 1)
with np.errstate(invalid="ignore", divide="ignore"):
    GV = np.abs(np.log1p(1.0 / (1.0 + B1) - 1.0))          # |ln(spot*mult/perp)| from B1 = perp/spot - 1
LN125 = math.log(1.25)
out = {}; gate_eq = {}
for arm in ARMS:
    POS, holds, openh = simulate(arm, D, iW0, iW1); acc = account(POS, D, iW0, arm["K"], CS_BASE); acc1 = account(POS, D, iW0, arm["K"], CS_BASE, marker="B1")
    gate_eq[arm["id"]] = bool(np.array_equal(acc["net"], SER["%s_net" % arm["id"]]))
    n = acc["n"]; rows = []
    for (k, t0, t1, why) in holds + openh:
        te = t1 if t1 is not None else (iW1 - iW0 + 1)
        i0 = iW0 + t0; i1 = iW0 + te
        b2 = n * 1e4 * (D["B2F"][i0, k] - D["B2F"][i1, k]); b1 = n * 1e4 * (D["B1F"][i0, k] - D["B1F"][i1, k]) if np.isfinite(D["B1F"][i0, k]) and np.isfinite(D["B1F"][i1, k]) else float("nan")
        gv = GV[i0:i1 + 1, k]; gmax = float(np.nanmax(gv)) if np.isfinite(gv).any() else float("nan")
        rows.append(dict(sym=SYM[k], entry=iso(EG[i0]), exit=iso(EG[i1]) if t1 is not None else None, reason=why, anchors=int(te - t0), in_S2426=bool(EG[i0] >= ut(2024, 1, 1)),
                         b2_pnl=float(b2), b1_pnl=float(b1), diff_b1_minus_b2=float(b1 - b2) if math.isfinite(b1) else None,
                         b2_in_bps=float(D["B2F"][i0, k] * 1e4), b2_out_bps=float(D["B2F"][i1, k] * 1e4), b1_in_bps=float(D["B1F"][i0, k] * 1e4) if np.isfinite(D["B1F"][i0, k]) else None,
                         b1_out_bps=float(D["B1F"][i1, k] * 1e4) if np.isfinite(D["B1F"][i1, k]) else None, guard_max_in_hold=gmax, guard_breached_in_hold=bool(math.isfinite(gmax) and gmax > LN125)))
    d = np.array([r["diff_b1_minus_b2"] for r in rows if r["diff_b1_minus_b2"] is not None])
    br = np.array([r["guard_breached_in_hold"] for r in rows if r["diff_b1_minus_b2"] is not None])
    tot_b1 = float(acc1["bas"].sum()); tot_b2 = float(acc["bas"].sum()); nA = len(TSW)
    o = dict(holds=len(rows), total_b1_bps_capital=tot_b1, total_b2_bps_capital=tot_b2, per_anchor_FULL_b1=tot_b1 / nA, per_anchor_FULL_b2=tot_b2 / nA,
             per_anchor_S2426_b1=float(acc1["bas"][S2426].mean()), per_anchor_S2426_b2=float(acc["bas"][S2426].mean()),
             sum_hold_diff=float(d.sum()), median_hold_diff=float(np.median(d)), mean_hold_diff=float(d.mean()),
             holds_guard_breached=int(br.sum()), sum_diff_guard_breached=float(d[br].sum()), sum_diff_not_breached=float(d[~br].sum()),
             per_anchor_FULL_b1_excl_breached_holds=(tot_b1 - float(np.array([r["b1_pnl"] for r in rows if r["diff_b1_minus_b2"] is not None])[br].sum())) / nA,
             per_anchor_FULL_b2_excl_breached_holds=(tot_b2 - float(np.array([r["b2_pnl"] for r in rows if r["diff_b1_minus_b2"] is not None])[br].sum())) / nA,
             share_of_diff_from_top1pct=float(np.sort(np.abs(d))[::-1][:max(1, len(d) // 100)].sum() / max(np.abs(d).sum(), 1e-300)),
             share_of_diff_from_top10_holds=float(np.sort(np.abs(d))[::-1][:10].sum() / max(np.abs(d).sum(), 1e-300)),
             entry_level_b1_minus_b2_bps_mean=float(np.nanmean([r["b1_in_bps"] - r["b2_in_bps"] for r in rows if r["b1_in_bps"] is not None])),
             exit_level_b1_minus_b2_bps_mean=float(np.nanmean([r["b1_out_bps"] - r["b2_out_bps"] for r in rows if r["b1_out_bps"] is not None and r["exit"] is not None])),
             top10_by_abs_diff=sorted([r for r in rows if r["diff_b1_minus_b2"] is not None], key=lambda r: -abs(r["diff_b1_minus_b2"]))[:10])
    q = np.percentile(d, [1, 5, 25, 50, 75, 95, 99]); o["hold_diff_percentiles_1_5_25_50_75_95_99"] = [float(x) for x in q]
    out[arm["id"]] = o
    print("PH %s holds=%d FULL b2 %.4f b1 %.4f | hold diff sum %.1f median %.3f | guard-breached holds %d carry %.1f of diff; excl breached FULL b1 %.4f b2 %.4f | top10 share %.3f | entry lvl b1-b2 %.2f exit %.2f bps" % (
        arm["id"], o["holds"], o["per_anchor_FULL_b2"], o["per_anchor_FULL_b1"], o["sum_hold_diff"], o["median_hold_diff"], o["holds_guard_breached"], o["sum_diff_guard_breached"],
        o["per_anchor_FULL_b1_excl_breached_holds"], o["per_anchor_FULL_b2_excl_breached_holds"], o["share_of_diff_from_top10_holds"], o["entry_level_b1_minus_b2_bps_mean"], o["exit_level_b1_minus_b2_bps_mean"]), flush=True)
REC["gate_net_series_bitwise_equal"] = gate_eq; REC["arms"] = out
json.dump(REC, open(os.path.join(WORK, "POSTHOC_L4_basis_reconcile.json"), "w"), indent=1)
print("SUMMARY l4_posthoc_basis_reconcile (POST-HOC) series_equal=%d/12 A01 FULL b2 %.4f b1 %.4f excl-guard-breached b1 %.4f median hold diff %.3f self_sha256=%s" % (
    sum(gate_eq.values()), out["A01"]["per_anchor_FULL_b2"], out["A01"]["per_anchor_FULL_b1"], out["A01"]["per_anchor_FULL_b1_excl_breached_holds"], out["A01"]["median_hold_diff"], REC["device_sha256"][:16]), flush=True)
