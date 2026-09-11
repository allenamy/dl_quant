"""TRACK E judge — judge_v4.py's FROZEN DEFINITION ported verbatim (load/boot/levels/WIN/FROZEN/EXT/COLS/APY
copied line-for-line from judge_v4.py sha-pinned below), applied to arms that judge_v4.py cannot address
(its ARMS/CON and ELIGIBILITY_CONTRACT.json are hard-coded to A0..A3). Therefore every reading produced here is
INFORMATIONAL / NON-CANDIDATE by construction: no arm of Track E can be promoted through this file.

Modes:
  verify  : recompute levels+contrasts for A0..A3 exactly as judge_v4 does and diff against the archived
            JUDGE_v4.json -> the port receipt. Any non-zero difference aborts.
  judge   : read SPEC (json {baseline: tag, arms: {tag: path}}) and report levels + paired contrasts vs baseline.
"""
import numpy as np, json, calendar, time, os, sys
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}; APY = 2190
def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))
FROZEN = (T(2025, 3, 1), T(2026, 8, 10, 20) + 1); EXT = (T(2025, 3, 1), T(2026, 8, 31, 20) + 1)
WIN = {"2022": (T(2022, 1, 1), T(2023, 1, 1)), "2023": (T(2023, 1, 1), T(2024, 1, 1)), "2024": (T(2024, 1, 1), T(2025, 1, 1)), "2025": (T(2025, 1, 1), T(2026, 1, 1)), "2026→08-10 20Z": (T(2026, 1, 1), T(2026, 8, 10, 20) + 1),
       "frozen 2025-03-01→2026-08-10 20Z": FROZEN, "2024-01→2026-08-10 20Z": (T(2024, 1, 1), T(2026, 8, 10, 20) + 1), "ext 08-11→08-30 20Z": (T(2026, 8, 11), T(2026, 8, 30, 20) + 1), "08-31 (6)": (T(2026, 8, 31), T(2026, 9, 1)),
       "2026→08-31 20Z (all)": (T(2026, 1, 1), T(2026, 8, 31, 20) + 1), "EXTENDED 2025-03-01→2026-08-31 20Z": EXT, "2024-01→2026-08-31 20Z": (T(2024, 1, 1), T(2026, 8, 31, 20) + 1)}
def load(path):
    A = np.load(path, allow_pickle=True); R = A["d30_n2_c42_rec"]
    ts = np.round(np.asarray(R[:, 0], dtype=np.float64)).astype(np.int64)
    g = R[:, C["net_ex"]] / R[:, C["gross_total"]]
    assert np.isfinite(g[(ts >= FROZEN[0]) & (ts < FROZEN[1])]).all(), f"non-finite g on frozen window: {path}"
    assert (R[(ts >= FROZEN[0]) & (ts < FROZEN[1]), C["gross_total"]] > 0).all(), f"gross_total<=0 on frozen: {path}"
    return ts, g, R
def boot(v, days, rng):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    if nd < 3: return (float("nan"), float("nan"), float("nan"))
    S = np.bincount(inv, weights=v, minlength=nd); N = np.bincount(inv, minlength=nd); idx = rng.integers(0, nd, size=(2000, nd)); mn = S[idx].sum(1) / N[idx].sum(1)
    return float(np.percentile(mn, 2.5)), float(np.percentile(mn, 97.5)), float((mn > 0).mean())
def levels(ts, g, R):
    out = {}
    for w, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi)
        if not m.any(): continue
        v = g[m]; c = np.concatenate([[0.0], np.cumsum(v)]); dd = float(np.max(np.maximum.accumulate(c) - c))
        days = ts[m] // 86400; ud, inv = np.unique(days, return_inverse=True); dsum = np.bincount(inv, weights=v); mon = np.array([time.gmtime(int(t)).tm_year * 100 + time.gmtime(int(t)).tm_mon for t in ts[m]]); um, im = np.unique(mon, return_inverse=True); msum = np.bincount(im, weights=v)
        out[w] = {"n": int(m.sum()), "mean_bps": float(v.mean()), "sharpe": float(v.mean() / v.std(ddof=1) * np.sqrt(APY)) if m.sum() > 2 and v.std(ddof=1) > 0 else float("nan"), "maxdd_bps": dd,
                  "worst_day_bps": float(dsum.min()), "worst_day": time.strftime("%F", time.gmtime(int(ud[dsum.argmin()]) * 86400)), "worst_month_bps": float(msum.min()), "worst_month": str(um[msum.argmin()]),
                  "n_neg_months": int((msum < 0).sum()), "n_months": int(len(um)), "gross_total_mean": float(R[m, C["gross_total"]].mean()), "nsel_mean": float(R[m, C["nsel"]].mean()), "w3_king_mean": float(R[m, C["w3_king"]].mean()), "turnover_mean": float(R[m, C["turnover"]].mean()),
                  "annual_pct_per_gross": float(v.mean() * APY / 1e4 * 100), "negative_year": bool(v.sum() < 0)}
    return out
def quarters(ts, g, lo, hi):
    m = (ts >= lo) & (ts < hi); q = np.array([time.gmtime(int(t)).tm_year * 10 + (time.gmtime(int(t)).tm_mon - 1) // 3 + 1 for t in ts[m]])
    uq, iq = np.unique(q, return_inverse=True); qs = np.bincount(iq, weights=g[m]); qn = np.bincount(iq)
    return {str(int(a)): {"sum_bps": float(b), "mean_bps": float(b / c), "n": int(c)} for a, b, c in zip(uq, qs, qn)}
HC = os.environ.get("JUDGE_HC", "/workspace/review_scratch/health_check")
MODE = sys.argv[1]
if MODE == "verify":
    ref = json.load(open(os.environ["REF_JSON"]))
    CON = [("A1","A0"),("A2","A0"),("A3","A0"),("A1","A2"),("A1","A3"),("A1s","A0"),("A1s","A1"),("A1e","A1"),("A1e","A0")]
    ARMS = {}
    for arm in ("A0","A0p","A1","A1s","A1e","A2","A3"):
        for seat in ("dyn","fix"):
            for s in ("42","2027"):
                p = f"{HC}/dev_v4/probe_artifacts/w10_ablation_series_V4_{arm}_{seat}_s{s}.npz"
                if os.path.exists(p): ARMS[(arm,seat,s)] = load(p)
    nbad = 0; ncmp = 0
    for k,(ts,g,R) in sorted(ARMS.items()):
        L = levels(ts,g,R); rk = ref["levels"].get("_".join(k))
        if rk is None: continue
        for w,r in L.items():
            for f,v in r.items():
                rv = rk[w][f]
                if isinstance(v,float) and isinstance(rv,float):
                    if not (v==rv or (np.isnan(v) and np.isnan(rv))): nbad+=1; print("LEVEL_DIFF","_".join(k),w,f,v,rv)
                elif v != rv: nbad+=1; print("LEVEL_DIFF","_".join(k),w,f,v,rv)
                ncmp+=1
    for ci,(a,b) in enumerate(CON):
        for seat in ("dyn","fix"):
            for s in ("42","2027"):
                if (a,seat,s) not in ARMS or (b,seat,s) not in ARMS: continue
                ta,ga,_ = ARMS[(a,seat,s)]; tb,gb,_ = ARMS[(b,seat,s)]
                m = (ta>=FROZEN[0])&(ta<FROZEN[1]); d=(ga-gb)[m]
                rng = np.random.default_rng([20260905,ci]); lo,hi,p = boot(d, ta[m]//86400, rng)
                rr = ref["contrasts"].get(f"{a}-{b}|{seat}|s{s}")
                if rr is None: continue
                for f,v in (("delta",float(d.mean())),("p_gt0",p),("n",int(m.sum()))):
                    if v != rr[f]: nbad+=1; print("CON_DIFF",a,b,seat,s,f,v,rr[f])
                    ncmp+=1
                for i,v in enumerate((lo,hi)):
                    if v != rr["ci95"][i]: nbad+=1; print("CON_DIFF",a,b,seat,s,"ci95[%d]"%i,v,rr["ci95"][i])
                    ncmp+=1
    print(f"PORT_RECEIPT compared={ncmp} differences={nbad}")
    print("PORT_PASS" if nbad==0 else "PORT_FAIL"); sys.exit(0 if nbad==0 else 9)
spec = json.load(open(sys.argv[2])); base = spec["baseline"]; arms = spec["arms"]
A = {t: load(p) for t,p in arms.items()}
out = {"spec": spec, "baseline": base, "levels": {}, "contrasts": {}, "contrasts_extended": {}, "quarters": {},
       "standing": "INFORMATIONAL / NON-CANDIDATE: judge_v4.py's ELIGIBILITY_CONTRACT.json registers only A0..A3; no Track E arm can be promoted through this file."}
for t,(ts,g,R) in A.items():
    out["levels"][t] = levels(ts,g,R); out["quarters"][t] = quarters(ts,g,*FROZEN)
tb, gb, _ = A[base]
order = [t for t in arms if t != base]
print("== CONTRASTS vs %s (frozen; UTC-day block bootstrap 2000; rng [20260905, k]) ==" % base)
print("%-22s %9s %22s %6s | %s" % ("arm","d bps","CI95","P>0","base -> arm"))
for ci,t in enumerate(order):
    ta,ga,_ = A[t]
    com = np.intersect1d(ta,tb); ia=np.searchsorted(ta,com); ib=np.searchsorted(tb,com)
    for wn,(lo_,hi_),key,off in (("frozen",FROZEN,"contrasts",0),("extended",EXT,"contrasts_extended",100)):
        m = (com>=lo_)&(com<hi_); d = (ga[ia]-gb[ib])[m]
        rng = np.random.default_rng([20260905, off+ci]); lo,hi,p = boot(d, com[m]//86400, rng)
        out[key][t] = {"delta": float(d.mean()), "ci95":[lo,hi], "p_gt0":p, "n": int(m.sum()),
                       "level_base": float(gb[ib][m].mean()), "level_arm": float(ga[ia][m].mean()), "rng":[20260905,off+ci],
                       "n_common": int(len(com))}
        if wn=="frozen":
            print("%-22s %+9.4f [%+8.4f,%+8.4f] %6.3f | %+7.4f -> %+7.4f (n=%d)" % (t, d.mean(), lo, hi, p, gb[ib][m].mean(), ga[ia][m].mean(), m.sum()))
out["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(out, open(sys.argv[3],"w"), indent=1); print("TRACKE_JUDGE_DONE", sys.argv[3])
