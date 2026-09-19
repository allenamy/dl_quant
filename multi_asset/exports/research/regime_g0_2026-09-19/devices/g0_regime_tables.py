#!/usr/bin/env python3
"""g0_regime_tables.py — stream G0 of docs/PROGRAM_credible_replay_regime_optimization_2026-09-19.md §4 (FROZEN): regime labels and every
table §4 asks for, on the real-cost replay arms (A0 = in-role form, A1 = v4-retrained form; dyn seat; s42 and s2027). pod2, CPU, read-only.

Labels (written into this docstring BEFORE any regime-conditional performance number was computed):
  expanding-window terciles per variable: at anchor E, q = np.quantile(finite values at anchors <= E, [1/3, 2/3]) (numpy default, linear);
  label 0 (low) if x < q1/3, 2 (high) if x > q2/3, 1 (mid) otherwise — the middle tercile is the CLOSED interval [q1/3, q2/3].
  Why closed: RG-FLEVEL's cross-sectional median is exactly the exchange base rate 1.0 bp/8h on ~70% of anchors, so q1/3 == q2/3 == 1.0 bp;
  "x <= q1 -> low" would empty the middle bucket, "x >= q2 -> high" would empty the low bucket. For continuous variables the rule is identical
  to any other tie rule (ties have measure zero). Warm-up: the first 1,080 finite values of each variable are unlabelled.
  Primary variant = EXCL (holefix-filled bars excluded, see g0_state_build.py); INCL (filled bars used) is a sensitivity.
Performance = the judge's definitions, IMPORTED from fp2_per_year_table.py (230e3c79), not re-implemented: g = net_ex/gross_total per anchor,
  window g = mean; CI95 = UTC-day block bootstrap, NB=2000, rng default_rng([20260905, k]); daily Sharpe = UTC-day compounded at L=1 × √365;
  W_ALPHA = ts <= 2026-08-30T20Z minus the first 900 anchors (start pinned 2022-06-30T00Z). Components pnl/carry/cost per unit gross (g = pnl −
  carry − cost). Legs = the record's leg_king/leg_rev24/leg_fund (seat-weighted target-leg returns, bps per unit leg gross, NOT divided by
  gross_total) and seats w3_*. Bonferroni K = 21: CI at two-sided α = 0.05/21 from the same bootstrap draws (percentiles 0.119 / 99.881).
  Δ vs rest = cell mean g − mean g of the other labelled W_ALPHA anchors of the same variable, same day-block draws over their union of days.
First check (refuses otherwise): the published W_ALPHA g/CI of all four arms (PER_YEAR_TABLE_REALCOST.json dc06ec36) reproduced exactly.
v2 (added AFTER reading the v1 output ad2f1ba5, disclosed): §8 cell × year cross-tab with within-year high−low Δg and sign counts, and §6b the
  kNN realized check on August 2026 queries — because v1 showed the kNN neighbours and the DISP/FDISP cells clustered in time. Descriptive only;
  no variable, cut point, label or cell definition changed, every v1 number is recomputed identically.
usage: python g0_regime_tables.py <STATE_DIR> <OUT_DIR>
"""
import calendar, hashlib, importlib.util, json, os, sys, time
import numpy as np

T0 = time.time()
STATE_DIR, OUT_DIR = sys.argv[1], sys.argv[2]
os.makedirs(OUT_DIR, exist_ok=True)
W = "/workspace"
JUDGE = (f"{W}/fp2_2026-09/devices_v4chain/fp2_per_year_table.py", "230e3c793cd92ddf78abf76198e39c8cdb3657696920f0290324ff4a9e7a882f")
PUBLISHED = (f"{W}/fp2_2026-09/realcost/PER_YEAR_TABLE_REALCOST.json", "dc06ec3695dc4c4fe9ff7af72ac405696c85c3d13abbaf65ef46cfe17662fa28")
AD = f"{W}/fp2_2026-09/realcost/arms"
ARMS = {"A0/s42": (f"{AD}/w10_ablation_series_V4_A0_dyn_s42.npz", "634f7c55ba730520371aab64b64b3b2b5c211422af6ab7b8bacb78e4d706060b", "42"),
        "A0/s2027": (f"{AD}/w10_ablation_series_V4_A0_dyn_s2027.npz", "c1f92ec24bb45c990427840831033e6cc136cc7ba02a86b00375a6dcf1f74081", "2027"),
        "A1/s42": (f"{AD}/w10_ablation_series_V4_A1_dyn_s42.npz", "a077ed6b8f7136edb637770d3d886190046475a0b50cbd8eacf1c0edd33bdae7", "42"),
        "A1/s2027": (f"{AD}/w10_ablation_series_V4_A1_dyn_s2027.npz", "d9f69a059a2f6a612c93ece19b922714f5204378bae059bd2aeca85de69852df", "2027")}
LEV = 2.0; UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); WA_START = calendar.timegm((2022, 6, 30, 0, 0, 0))
WARM = 1080; KB = 21; ALPHA_B = 0.05 / KB; LAB = ["low", "mid", "high"]
CUR0 = calendar.timegm((2026, 8, 1, 0, 0, 0)); PRE_END = calendar.timegm((2026, 7, 31, 20, 0, 0)); KNN = 500


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)


CHECKS = []; FAILS = []
def check(name, ok, detail=None):
    CHECKS.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail is not None else {})})
    if not ok: FAILS.append(name)
    log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300] if detail is not None else "")
    return ok


rec = {"device": "g0_regime_tables.py", "self_sha256": sha(os.path.abspath(__file__)), "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)}, "utc_start": utc(time.time()), "inputs": {}}
def refuse(why):
    rec.update({"checks": CHECKS, "failed": FAILS, "VERDICT": "REFUSED", "why": why}); json.dump(rec, open(f"{OUT_DIR}/RECEIPT_g0_regime_tables.json", "w"), indent=1, default=str)
    log("REFUSED", why); sys.exit(3)


# ---------------- inputs ----------------
for nm, (p, s) in [("JUDGE", JUDGE), ("PUBLISHED", PUBLISHED)] + [(f"ARM_{k}", (v[0], v[1])) for k, v in ARMS.items()]:
    got = sha(p); rec["inputs"][nm] = {"path": p, "sha256": got}; check(f"input_sha.{nm}", got == s, {"expected": s[:12], "got": got[:12]})
SR = json.load(open(f"{STATE_DIR}/RECEIPT_g0_state_build.json"))
SNPZ = f"{STATE_DIR}/g0_state_vars.npz"; snpz_sha = sha(SNPZ)
rec["inputs"]["STATE_RECEIPT"] = {"path": f"{STATE_DIR}/RECEIPT_g0_state_build.json", "sha256": sha(f"{STATE_DIR}/RECEIPT_g0_state_build.json"), "state_device_sha256": SR.get("self_sha256")}
rec["inputs"]["STATE_NPZ"] = {"path": SNPZ, "sha256": snpz_sha}
check("state.receipt_PASS_and_npz_sha", SR.get("VERDICT") == "PASS" and SR["outputs"]["state_vars"]["sha256"] == snpz_sha, {"verdict": SR.get("VERDICT")})
if FAILS: refuse("input gate")
spec = importlib.util.spec_from_file_location("fp2_judge", JUDGE[0]); J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)

# ---------------- arms (judge loader + its config assertions) ----------------
X = {}; RAW = {}
for k, (p, s, seed) in ARMS.items():
    x = J.load(p, "dyn", seed=seed)
    check(f"arm.judge_load.{k}", not x["why"], x["why"]); X[k] = x
    Z = np.load(p, allow_pickle=True); C = [str(c) for c in Z["cols"]]; R = np.asarray(Z["d30_n2_c42_rec"], float)
    RAW[k] = {c: R[:, C.index(c)] for c in ("leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "nmember")}
ts = X["A0/s42"]["ts"]
for k in X: check(f"arm.same_ts.{k}", np.array_equal(X[k]["ts"], ts))
if FAILS: refuse("arm gate")
NA = len(ts)
DAY = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in ts]); DAYS = (ts // 86400) * 86400
WA = ts <= UB; WA[:900] = False
check("wa.start_pinned", int(ts[900]) == WA_START, utc(ts[900]))

# ---------------- reproduction check (first, refuses) ----------------
PUB = json.load(open(PUBLISHED[0]))
rec["reproduction"] = {}
for k in X:
    lv = J.level(X[k], WA, DAY, DAYS, LEV); pub = PUB["arms"][k.replace("/", "/dyn/")]["W_ALPHA"]
    same = (lv["g"] == pub["g"]) and (lv["ci95"] == pub["ci95"]) and (lv["n"] == pub["n"])
    rec["reproduction"][k] = {"g": lv["g"], "ci95": lv["ci95"], "n": lv["n"], "published_g": pub["g"], "published_ci95": pub["ci95"], "exact": bool(same)}
    check(f"repro.W_ALPHA.{k}", same, rec["reproduction"][k])
if FAILS: refuse("reproduction of the published W_ALPHA numbers failed")

# ---------------- state + labels ----------------
S = np.load(SNPZ, allow_pickle=True); AX = S["ts"].astype(np.int64); VARS = [str(v) for v in S["vars"]]; NAX = len(AX)
check("state.axis_prefix_equals_arm_ts", bool(np.array_equal(AX[:NA], ts)), {"state_anchors": NAX, "last": utc(AX[-1])})
if FAILS: refuse("axis")
VAL = {v: np.asarray(S[v], float) for v in ("EXCL", "INCL")}


def expanding_labels(x):
    lab = np.full(len(x), -1, np.int8); q = np.full((len(x), 2), np.nan); pr = np.full(len(x), np.nan)
    fin = np.isfinite(x); cnt = np.cumsum(fin)
    for t in range(len(x)):
        if not fin[t] or cnt[t] <= WARM: continue
        h = x[:t + 1][fin[:t + 1]]; q1, q2 = np.quantile(h, [1 / 3, 2 / 3]); q[t] = (q1, q2)
        lab[t] = 0 if x[t] < q1 else (2 if x[t] > q2 else 1); pr[t] = float(np.mean(h <= x[t]))
    return lab, q, pr


LB = {}; QQ = {}; PR = {}
for v in VAL:
    LB[v] = np.full((NAX, 7), -1, np.int8); QQ[v] = np.full((NAX, 7, 2), np.nan); PR[v] = np.full((NAX, 7), np.nan)
    for j in range(7):
        LB[v][:, j], QQ[v][:, j], PR[v][:, j] = expanding_labels(VAL[v][:, j])
    log("labels", v)
rec["label_census"] = {v: {VARS[j]: {"labelled": int((LB[v][:, j] >= 0).sum()), "first_labelled": (utc(AX[np.argmax(LB[v][:, j] >= 0)]) if (LB[v][:, j] >= 0).any() else None),
                                     "share_low_mid_high_all": [float(np.mean(LB[v][LB[v][:, j] >= 0, j] == l)) for l in range(3)],
                                     "WA_anchors_low_mid_high": [int((WA & (LB[v][:NA, j] == l)).sum()) for l in range(3)],
                                     "q_last": QQ[v][-1, j].tolist()} for j in range(7)} for v in VAL}
rec["label_agreement_EXCL_vs_INCL"] = {VARS[j]: {"both_labelled": int(((LB["EXCL"][:, j] >= 0) & (LB["INCL"][:, j] >= 0)).sum()),
                                                "equal": int(((LB["EXCL"][:, j] >= 0) & (LB["EXCL"][:, j] == LB["INCL"][:, j])).sum()),
                                                "equal_share_arm_WA": float(np.mean((LB["EXCL"][:NA, j] == LB["INCL"][:NA, j])[WA & (LB["EXCL"][:NA, j] >= 0) & (LB["INCL"][:NA, j] >= 0)]))} for j in range(7)}


# ---------------- statistics helpers (judge draws) ----------------
def boot_dist(d, mask):
    """the judge's boot() line by line (same day grouping, same per-day summation order, same draws) but returning the whole distribution"""
    idx = np.nonzero(mask)[0]
    if len(idx) == 0: return None
    dd = {}
    for k in idx: dd.setdefault(DAY[k], []).append(k)
    keys = sorted(dd); tot = np.array([d[dd[k]].sum() for k in keys]); cnt = np.array([len(dd[k]) for k in keys], float)
    r = J.draws(len(keys)); return tot[r].sum(1) / cnt[r].sum(1)


def delta_dist(d, m_in, m_out):
    idx = np.nonzero(m_in | m_out)[0]
    keys, inv = np.unique(DAY[idx], return_inverse=True); nd = len(keys)
    si = np.bincount(inv, weights=np.where(m_in[idx], d[idx], 0.0), minlength=nd); ci = np.bincount(inv, weights=m_in[idx].astype(float), minlength=nd)
    so = np.bincount(inv, weights=np.where(m_out[idx], d[idx], 0.0), minlength=nd); co = np.bincount(inv, weights=m_out[idx].astype(float), minlength=nd)
    r = J.draws(nd)
    with np.errstate(all="ignore"): return si[r].sum(1) / ci[r].sum(1) - so[r].sum(1) / co[r].sum(1)


PB = [100 * ALPHA_B / 2, 100 * (1 - ALPHA_B / 2)]
ci_consistency_bad = []


def cell(k, mask, rest=None):
    x = X[k]; n = int(mask.sum())
    if n == 0: return {"n": 0}
    lv = J.level(x, mask, DAY, DAYS, LEV); ms = boot_dist(x["g"], mask)
    ci = [float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))]
    if ci != lv["ci95"]: ci_consistency_bad.append((k, n))
    o = {kk: lv[kk] for kk in ("n", "g", "ci95", "se_boot", "n_days", "sharpe_anchor", "sharpe_daily", "pnl", "carry", "cost", "tau_raw", "gross_total", "netlong", "maxdd_L")}
    o["ci_bonf"] = [float(np.percentile(ms, PB[0])), float(np.percentile(ms, PB[1]))]
    o["excl0_95"] = bool(o["ci95"][0] > 0 or o["ci95"][1] < 0); o["excl0_bonf"] = bool(o["ci_bonf"][0] > 0 or o["ci_bonf"][1] < 0)
    for c in ("leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund"): o[c] = float(RAW[k][c][mask].mean())
    if rest is not None and rest.any():
        dd = delta_dist(x["g"], mask, rest); o["d_vs_rest"] = float(x["g"][mask].mean() - x["g"][rest].mean())
        o["d_ci95"] = [float(np.nanpercentile(dd, 2.5)), float(np.nanpercentile(dd, 97.5))]; o["d_ci_bonf"] = [float(np.nanpercentile(dd, PB[0])), float(np.nanpercentile(dd, PB[1]))]
        o["d_excl0_95"] = bool(o["d_ci95"][0] > 0 or o["d_ci95"][1] < 0); o["d_excl0_bonf"] = bool(o["d_ci_bonf"][0] > 0 or o["d_ci_bonf"][1] < 0)
    return o


# ---------------- 21 cells ----------------
rec["cells"] = {}
for v in ("EXCL", "INCL"):
    rec["cells"][v] = {}
    for k in X:
        rec["cells"][v][k] = {}
        for j, nm in enumerate(VARS):
            labd = WA & (LB[v][:NA, j] >= 0)
            rec["cells"][v][k][nm] = {LAB[l]: cell(k, labd & (LB[v][:NA, j] == l), labd & (LB[v][:NA, j] != l)) for l in range(3)}
            rec["cells"][v][k][nm]["_labelled_WA"] = cell(k, labd)
    log("cells", v)
check("stats.own_bootstrap_equals_judge_ci95", not ci_consistency_bad, ci_consistency_bad[:5])

# ---------------- period tables ----------------
YR = np.array([time.gmtime(int(t)).tm_year for t in ts]); MO = np.array([time.gmtime(int(t)).tm_mon for t in ts])
QTAG = np.array([f"{y}Q{(m - 1) // 3 + 1}" for y, m in zip(YR, MO)]); MTAG = np.array([f"{y}-{m:02d}" for y, m in zip(YR, MO)]); YTAG = YR.astype(str)
rec["periods"] = {}
for k in X:
    rec["periods"][k] = {"W_ALPHA": cell(k, WA)}
    for nm, TG in (("year", YTAG), ("quarter", QTAG), ("month", MTAG)):
        rec["periods"][k][nm] = {p: cell(k, WA & (TG == p)) for p in sorted(set(TG[WA].tolist()))}
log("periods")

# ---------------- persistence ----------------
rec["persistence"] = {}
for v in VAL:
    rec["persistence"][v] = {}
    for j, nm in enumerate(VARS):
        lab = LB[v][:, j]; o = {}
        for hn, h in (("1d", 6), ("30d", 180)):
            a, b = lab[:-h], lab[h:]; ok = (a >= 0) & (b >= 0)
            M = np.zeros((3, 3), int); np.add.at(M, (a[ok], b[ok]), 1)
            P = M / np.maximum(M.sum(1, keepdims=True), 1)
            pa = M.sum(1) / M.sum(); pb = M.sum(0) / M.sum()
            o[hn] = {"counts": M.tolist(), "P": P.round(4).tolist(), "p_same": float(np.trace(M) / M.sum()), "p_same_if_independent": float((pa * pb).sum()), "pairs": int(ok.sum())}
        runs = []; cur = None; ln = 0
        for l in lab:
            if l < 0:
                if cur is not None: runs.append((cur, ln))
                cur, ln = None, 0; continue
            if l == cur: ln += 1
            else:
                if cur is not None: runs.append((cur, ln))
                cur, ln = int(l), 1
        if cur is not None: runs.append((cur, ln))
        o["mean_spell_days"] = {LAB[l]: float(np.mean([r[1] for r in runs if r[0] == l]) / 6) if any(r[0] == l for r in runs) else None for l in range(3)}
        o["median_spell_days"] = {LAB[l]: float(np.median([r[1] for r in runs if r[0] == l]) / 6) if any(r[0] == l for r in runs) else None for l in range(3)}
        rec["persistence"][v][nm] = o
log("persistence")

# ---------------- current-regime location ----------------
cur = np.nonzero(AX >= CUR0)[0]
rec["current"] = {"first": utc(AX[cur[0]]), "last": utc(AX[cur[-1]]), "n_anchors": int(len(cur)), "anchors": []}
for a in cur:
    rec["current"]["anchors"].append({"ts": utc(AX[a]), "in_arm_window": bool(a < NA),
                                      **{v: {"value": [None if not np.isfinite(z) else float(z) for z in VAL[v][a]], "label": [int(z) for z in LB[v][a]],
                                             "pct_rank": [None if not np.isfinite(z) else float(z) for z in PR[v][a]]} for v in VAL}})
PRE = WA & (ts <= PRE_END)
segs = {"2026-08": (AX >= CUR0) & (AX < calendar.timegm((2026, 9, 1, 0, 0, 0))), "2026-09(to last)": AX >= calendar.timegm((2026, 9, 1, 0, 0, 0)), "all_current": AX >= CUR0}
rec["current"]["by_variable"] = {}
for v in VAL:
    rec["current"]["by_variable"][v] = {}
    for j, nm in enumerate(VARS):
        o = {}
        for sg, sm in segs.items():
            lab = LB[v][sm, j]; ok = lab >= 0
            sh = [float(np.mean(lab[ok] == l)) if ok.any() else None for l in range(3)]
            o[sg] = {"labelled": int(ok.sum()), "unlabelled": int((~ok).sum()), "share_low_mid_high": sh, "last_label": (LAB[int(lab[ok][-1])] if ok.any() else None)}
            for k in X:
                full = [rec["cells"][v][k][nm][LAB[l]].get("g") for l in range(3)]
                prec = [(float(X[k]["g"][PRE & (LB[v][:NA, j] == l)].mean()) if (PRE & (LB[v][:NA, j] == l)).any() else None) for l in range(3)]
                o[sg][k] = {"g_full_by_bucket": full, "g_pre_by_bucket": prec,
                            "share_weighted_g_full": (float(sum(s * g for s, g in zip(sh, full))) if ok.any() and None not in full else None),
                            "share_weighted_g_pre": (float(sum(s * g for s, g in zip(sh, prec))) if ok.any() and None not in prec else None)}
        rec["current"]["by_variable"][v][nm] = o
# exact 7-tuple matches (descriptive)
rec["current"]["tuple_match"] = {}
for v in VAL:
    allL = (LB[v] >= 0).all(1); hist = np.nonzero(PRE & allL[:NA])[0]; HT = {}
    for i in hist: HT.setdefault(tuple(int(z) for z in LB[v][i]), []).append(i)
    rows = []
    for a in cur:
        if not allL[a]: rows.append({"ts": utc(AX[a]), "tuple": None}); continue
        tp = tuple(int(z) for z in LB[v][a]); hi = np.array(HT.get(tp, []), int)
        rows.append({"ts": utc(AX[a]), "tuple": "".join("LMH"[z] for z in tp), "n_hist": int(len(hi)), "n_hist_days": int(len(set(DAY[hi].tolist()))) if len(hi) else 0,
                     **({k: float(X[k]["g"][hi].mean()) for k in X} if len(hi) else {})})
    rec["current"]["tuple_match"][v] = rows

# ---------------- kNN analog (EXPLORATORY) ----------------
iUB = int(np.nonzero(ts <= UB)[0][-1])
FWD = {}
for k in X:
    cs = np.concatenate([[0.0], np.cumsum(X[k]["g"])]); f = np.full(NA, np.nan); ii = np.arange(NA); okf = ii + 179 <= iUB
    f[okf] = (cs[ii[okf] + 180] - cs[ii[okf]]) / 180.0; FWD[k] = f
rec["knn"] = {"definition": f"EXPLORATORY. k={KNN} nearest anchors by Euclidean distance on the 7 state variables z-scored with the pool mean/std; pool = W_ALPHA anchors with all 7 "
                             "variables defined, forward 180 anchors inside ts<=UB, and ts <= query − 30 days; reports mean next-4h g (g at the neighbour) and mean next-30-day g "
                             "(mean g over the neighbour's next 180 anchors), with the pool's unconditional means", "rows": {}}
for v in VAL:
    V = VAL[v]; allv = np.isfinite(V).all(1); rows = []
    for a in cur:
        if not allv[a]: rows.append({"ts": utc(AX[a]), "defined": False}); continue
        pool = np.nonzero(WA & allv[:NA] & np.isfinite(FWD["A0/s42"]) & (ts <= AX[a] - 30 * 86400))[0]
        mu = V[pool].mean(0); sd = V[pool].std(0); sd = np.where(sd > 0, sd, 1.0)
        dz = np.sqrt((((V[pool] - mu) / sd - (V[a] - mu) / sd) ** 2).sum(1))
        nb = pool[np.argpartition(dz, KNN - 1)[:KNN]] if len(pool) > KNN else pool
        o = {"ts": utc(AX[a]), "defined": True, "pool": int(len(pool)), "median_dist": float(np.median(np.sort(dz)[:KNN])), "nb_months": int(len(set(MTAG[nb].tolist()))),
             "nb_first": utc(ts[nb].min()), "nb_last": utc(ts[nb].max()), "nb_years": {str(y): int((YR[nb] == y).sum()) for y in sorted(set(YR[nb].tolist()))}}
        for k in X:
            o[k] = {"nb_next4h_g": float(X[k]["g"][nb].mean()), "nb_next30d_g": float(FWD[k][nb].mean()), "pool_next4h_g": float(X[k]["g"][pool].mean()), "pool_next30d_g": float(FWD[k][pool].mean())}
        rows.append(o)
    rec["knn"]["rows"][v] = rows
log("knn")

# ---------------- root-cause readout (descriptive) ----------------
rc = {}
for v in ("EXCL",):
    rc[v] = {}
    for k in X:
        C = rec["cells"][v][k]; cells = [(nm, LAB[l], C[nm][LAB[l]]) for nm in VARS for l in range(3) if C[nm][LAB[l]].get("n", 0) > 0]
        g = np.array([c[2]["g"] for c in cells]); p = np.array([c[2]["pnl"] for c in cells]); ca = np.array([c[2]["carry"] for c in cells]); co = np.array([c[2]["cost"] for c in cells])
        vg = g.var()
        dec = {"var_g_across_cells": float(vg), "share_price": float(np.cov(g, p, bias=True)[0, 1] / vg), "share_carry": float(-np.cov(g, ca, bias=True)[0, 1] / vg), "share_cost": float(-np.cov(g, co, bias=True)[0, 1] / vg)}
        order = np.argsort(g); bad = [cells[i] for i in order[:5]]; good = [cells[i] for i in order[-5:]]
        def avg(cs):
            return {f: float(np.mean([c[2][f] for c in cs])) for f in ("g", "pnl", "carry", "cost", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_fund", "tau_raw", "netlong")}
        hl = {}
        for nm in VARS:
            hi, lo = C[nm]["high"], C[nm]["low"]
            if hi.get("n", 0) and lo.get("n", 0):
                hl[nm] = {f"d_{f}": float(hi[f] - lo[f]) for f in ("g", "pnl", "carry", "cost", "leg_king", "leg_fund", "w3_king", "w3_fund", "tau_raw", "netlong")}
        rc[v][k] = {"variance_decomposition_21_cells": dec, "bottom5": [(c[0], c[1]) for c in bad], "top5": [(c[0], c[1]) for c in good], "bottom5_mean": avg(bad), "top5_mean": avg(good), "high_minus_low": hl}
PER = {"2023": (AX >= calendar.timegm((2023, 1, 1, 0, 0, 0))) & (AX < calendar.timegm((2024, 1, 1, 0, 0, 0))),
       "2026H1": (AX >= calendar.timegm((2026, 1, 1, 0, 0, 0))) & (AX < calendar.timegm((2026, 7, 1, 0, 0, 0))),
       "2026-07": (AX >= calendar.timegm((2026, 7, 1, 0, 0, 0))) & (AX < CUR0),
       "2026-08": segs["2026-08"], "2026-09(to last)": segs["2026-09(to last)"], "W_ALPHA_all": np.concatenate([WA, np.zeros(NAX - NA, bool)])}
rc["periods_state"] = {}
for v in VAL:
    rc["periods_state"][v] = {}
    allfin = {j: VAL[v][np.concatenate([WA, np.zeros(NAX - NA, bool)]) & np.isfinite(VAL[v][:, j]), j] for j in range(7)}
    for pn, pm in PER.items():
        o = {}
        for j, nm in enumerate(VARS):
            x = VAL[v][pm, j]; x = x[np.isfinite(x)]; lab = LB[v][pm, j]; lab = lab[lab >= 0]
            o[nm] = {"n": int(len(x)), "mean": (float(x.mean()) if len(x) else None), "median": (float(np.median(x)) if len(x) else None),
                     "median_pct_in_W_ALPHA": (float(np.mean(allfin[j] <= np.median(x))) if len(x) else None),
                     "label_share_low_mid_high": ([float(np.mean(lab == l)) for l in range(3)] if len(lab) else None)}
        rc["periods_state"][v][pn] = o
rc["periods_perf"] = {k: {pn: cell(k, pm[:NA] & WA) for pn, pm in PER.items() if (pm[:NA] & WA).any()} for k in X}
rec["root_cause"] = rc
log("root cause")

# ---------------- v2: cell x year (descriptive) ----------------
years = sorted(set(YR[WA].tolist()))
rec["cell_by_year"] = {}
for k in X:
    rec["cell_by_year"][k] = {}
    for j, nm in enumerate(VARS):
        o = {}
        for l in range(3):
            o[LAB[l]] = {}
            for y in years:
                m = WA & (LB["EXCL"][:NA, j] == l) & (YR == y)
                o[LAB[l]][str(y)] = {"n": int(m.sum()), "g": (float(X[k]["g"][m].mean()) if m.any() else None), "pnl": (float(X[k]["pnl"][m].mean()) if m.any() else None),
                                    "carry": (float(X[k]["car"][m].mean()) if m.any() else None)}
        wy = {}
        for y in years:
            a, b = o["high"][str(y)], o["low"][str(y)]
            wy[str(y)] = (a["g"] - b["g"]) if (a["n"] >= 30 and b["n"] >= 30) else None
        vals = [v for v in wy.values() if v is not None]
        o["within_year_high_minus_low"] = wy
        o["within_year_sign"] = {"pos": int(sum(v > 0 for v in vals)), "neg": int(sum(v < 0 for v in vals)), "years_with_both_ge30": len(vals),
                                 "mean_of_within_year_deltas": (float(np.mean(vals)) if vals else None)}
        rec["cell_by_year"][k][nm] = o
# ---------------- v2: kNN realized check on August queries (next-4h g realized inside the arm window) ----------------
rec["knn"]["realized_check_aug"] = {}
for v in VAL:
    rows = [r for r in rec["knn"]["rows"][v] if r["defined"]]
    idx = {utc(t): i for i, t in enumerate(ts)}
    rr = [(r, idx[r["ts"]]) for r in rows if r["ts"] in idx and ts[idx[r["ts"]]] <= UB]
    o = {"queries_with_realized_next4h": len(rr)}
    for k in X:
        pred = np.array([r[k]["nb_next4h_g"] for r, _ in rr]); real = np.array([X[k]["g"][i] for _, i in rr])
        o[k] = {"mean_pred_next4h": float(pred.mean()), "mean_realized_next4h": float(real.mean()), "corr_pred_realized": float(np.corrcoef(pred, real)[0, 1]) if len(rr) > 2 else None,
                "mean_pred_next30d": float(np.mean([r[k]["nb_next30d_g"] for r, _ in rr]))}
    rec["knn"]["realized_check_aug"][v] = o
    o["nb_share_2025_2026_mean"] = float(np.mean([(r["nb_years"].get("2025", 0) + r["nb_years"].get("2026", 0)) / KNN for r in rows]))
    o["nb_share_2026_mean"] = float(np.mean([r["nb_years"].get("2026", 0) / KNN for r in rows]))
log("v2 sections")

# ---------------- outputs ----------------
lab_npz = f"{OUT_DIR}/g0_labels.npz"
np.savez_compressed(lab_npz, ts=AX, vars=np.array(VARS), LAB_EXCL=LB["EXCL"], LAB_INCL=LB["INCL"], Q_EXCL=QQ["EXCL"], Q_INCL=QQ["INCL"], PR_EXCL=PR["EXCL"], PR_INCL=PR["INCL"])
out_json = f"{OUT_DIR}/G0_TABLES.json"
rec.update({"checks": CHECKS, "n_checks": len(CHECKS), "failed": FAILS, "VERDICT": "PASS" if not FAILS else "FAIL"})
json.dump(rec, open(out_json, "w"), indent=1, default=str)


# ---------------- markdown rendering ----------------
def f(x, d=3):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else ("%+." + str(d) + "f") % x


def ci(c, key="ci95"):
    return f"[{f(c[key][0], 2)}, {f(c[key][1], 2)}]" if c.get(key) else "—"


def cell_row(name, c, rest=True):
    if not c or c.get("n", 0) == 0: return f"| {name} | 0 |" + " — |" * (13 if rest else 10)
    star = ("**" if c["excl0_bonf"] else ("*" if c["excl0_95"] else ""))
    base = (f"| {name} | {c['n']} | {c['n_days']} | {star}{f(c['g'])}{star} | {ci(c)} | {ci(c, 'ci_bonf')} | {f(c['sharpe_daily'], 2)} | {f(c['pnl'])} / {f(c['carry'])} / {f(c['cost'])} | "
            f"{f(c['leg_king'], 2)} / {f(c['leg_rev24'], 2)} / {f(c['leg_fund'], 2)} | {c['w3_king']:.3f} / {c['w3_rev24']:.3f} / {c['w3_fund']:.3f} | {c['tau_raw']:.4f} | {f(c['netlong'])} |")
    if rest:
        ds = ("**" if c.get("d_excl0_bonf") else ("*" if c.get("d_excl0_95") else ""))
        base += f" {ds}{f(c.get('d_vs_rest'))}{ds} | {ci(c, 'd_ci95')} | {ci(c, 'd_ci_bonf')} |"
    return base


HDR = ("| cell | anchors | days | g | CI95 | CI Bonf(K=21) | Sharpe daily | price / carry / cost | leg king / rev24 / fund | seat king / rev24 / fund | τ raw | netlong | Δg vs rest | ΔCI95 | ΔCI Bonf |",
       "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
PHDR = ("| period | anchors | days | g | CI95 | CI Bonf | Sharpe daily | price / carry / cost | leg king / rev24 / fund | seat king / rev24 / fund | τ raw | netlong |", "|---|---|---|---|---|---|---|---|---|---|---|---|")
M = [f"# G0 regime tables (rendered by g0_regime_tables.py {rec['self_sha256'][:8]}; VERDICT {rec['VERDICT']})", "",
     f"state npz {snpz_sha[:8]} (g0_state_build.py {str(SR.get('self_sha256'))[:8]}); judge fp2_per_year_table.py {JUDGE[1][:8]}; arms " + ", ".join(f"{k} {v[1][:8]}" for k, v in ARMS.items()), "",
     "g = net_ex/gross_total, bps per anchor per unit gross; components: g = price − carry − cost; legs: seat-weighted target-leg returns (bps per unit leg gross); "
     "`*` = CI95 excludes 0, `**` = Bonferroni (K=21) CI excludes 0. Δg vs rest = cell − other labelled W_ALPHA anchors of the same variable.", "",
     "## 0. Reproduction check (published W_ALPHA, PER_YEAR_TABLE_REALCOST.json dc06ec36)", "", "| arm | g reproduced | published | CI95 reproduced | published | exact |", "|---|---|---|---|---|---|"]
for k, r in rec["reproduction"].items(): M.append(f"| {k} | {r['g']:.10f} | {r['published_g']:.10f} | {r['ci95']} | {r['published_ci95']} | {r['exact']} |")
M += ["", "## 1. Label census (EXCL primary; INCL sensitivity)", "", "| variable | variant | labelled anchors | first labelled | share low/mid/high (all labelled) | W_ALPHA anchors low/mid/high | last q⅓, q⅔ | EXCL=INCL share (W_ALPHA) |", "|---|---|---|---|---|---|---|---|"]
for nm in VARS:
    for v in VAL:
        c = rec["label_census"][v][nm]
        M.append(f"| {nm} | {v} | {c['labelled']} | {c['first_labelled']} | {' / '.join('%.3f' % s for s in c['share_low_mid_high_all'])} | {' / '.join(str(s) for s in c['WA_anchors_low_mid_high'])} | "
                 f"{', '.join('%.5g' % q for q in c['q_last'])} | {rec['label_agreement_EXCL_vs_INCL'][nm]['equal_share_arm_WA']:.4f} |")
for v in ("EXCL", "INCL"):
    for k in X:
        if v == "INCL" and k.startswith("A1"): continue
        M += ["", f"## 2{'a' if v == 'EXCL' else 'b'}. 21 cells — {k} — variant {v}{' (primary)' if v == 'EXCL' else ' (sensitivity)'}", "", *HDR]
        for nm in VARS:
            for l in range(3): M.append(cell_row(f"{nm} {LAB[l]}", rec["cells"][v][k][nm][LAB[l]]))
        M.append(cell_row("(all labelled W_ALPHA, TREND)", rec["cells"][v][k]["RG-TREND"]["_labelled_WA"], rest=False) + " | | |")
for nm_p in ("year", "quarter", "month"):
    for k in X:
        M += ["", f"## 3. Period table — {nm_p} — {k}", "", *PHDR, cell_row("W_ALPHA", rec["periods"][k]["W_ALPHA"], rest=False)]
        for p, c in rec["periods"][k][nm_p].items(): M.append(cell_row(p, c, rest=False))
M += ["", "## 4. Persistence (EXCL): transition matrices P(label at t+h | label at t), rows low/mid/high", "", "| variable | h | P row low | P row mid | P row high | P(same) | P(same) if independent | pairs | mean spell days L/M/H |", "|---|---|---|---|---|---|---|---|---|"]
for nm in VARS:
    o = rec["persistence"]["EXCL"][nm]
    for hn in ("1d", "30d"):
        P = o[hn]["P"]; sp = o["mean_spell_days"]
        M.append(f"| {nm} | {hn} | {P[0]} | {P[1]} | {P[2]} | {o[hn]['p_same']:.3f} | {o[hn]['p_same_if_independent']:.3f} | {o[hn]['pairs']} | " + (" / ".join("%.1f" % sp[l] if sp[l] is not None else "—" for l in LAB) if hn == "1d" else "") + " |")
M += ["", f"## 5. Current-regime location {rec['current']['first']} → {rec['current']['last']} ({rec['current']['n_anchors']} anchors)", "",
      "### 5a. Per variable: label shares and the historical g of the buckets (A0/s42 · A0/s2027); g_full = W_ALPHA cells, g_pre = W_ALPHA ∩ ts ≤ 2026-07-31 20Z", "",
      "| variable | variant | segment | labelled/unlab. | share L/M/H | last label | A0/s42 g_full L/M/H | share-weighted | A0/s42 g_pre L/M/H | share-weighted pre | A0/s2027 share-weighted full / pre |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for nm in VARS:
    for v in VAL:
        for sg in segs:
            o = rec["current"]["by_variable"][v][nm][sg]; a, b = o["A0/s42"], o["A0/s2027"]
            M.append(f"| {nm} | {v} | {sg} | {o['labelled']}/{o['unlabelled']} | {' / '.join('%.2f' % s if s is not None else '—' for s in o['share_low_mid_high'])} | {o['last_label']} | "
                     f"{' / '.join(f(g, 2) for g in a['g_full_by_bucket'])} | {f(a['share_weighted_g_full'], 2)} | {' / '.join(f(g, 2) for g in a['g_pre_by_bucket'])} | {f(a['share_weighted_g_pre'], 2)} | "
                     f"{f(b['share_weighted_g_full'], 2)} / {f(b['share_weighted_g_pre'], 2)} |")
M += ["", "### 5b. Every current anchor: labels (EXCL | INCL), order TREND BREADTH DISP FLEVEL FDISP VOL ALT; L/M/H, `.` = unlabelled", "", "| anchor | EXCL | INCL | 7-tuple hist n (EXCL) | A0/s42 g of tuple | kNN(EXCL) next-4h / next-30d g A0/s42 | kNN(INCL) next-4h / next-30d A0/s42 |", "|---|---|---|---|---|---|---|"]
KE = {r["ts"]: r for r in rec["knn"]["rows"]["EXCL"]}; KI = {r["ts"]: r for r in rec["knn"]["rows"]["INCL"]}; TE = {r["ts"]: r for r in rec["current"]["tuple_match"]["EXCL"]}
for r in rec["current"]["anchors"]:
    le = "".join("LMH"[z] if z >= 0 else "." for z in r["EXCL"]["label"]); li = "".join("LMH"[z] if z >= 0 else "." for z in r["INCL"]["label"])
    te = TE[r["ts"]]; ke = KE[r["ts"]]; ki = KI[r["ts"]]
    M.append(f"| {r['ts']} | {le} | {li} | {te.get('n_hist', '—') if te.get('tuple') else '—'} | {f(te.get('A0/s42'), 2) if te.get('n_hist') else '—'} | "
             f"{(f(ke['A0/s42']['nb_next4h_g'], 2) + ' / ' + f(ke['A0/s42']['nb_next30d_g'], 2)) if ke['defined'] else '—'} | {(f(ki['A0/s42']['nb_next4h_g'], 2) + ' / ' + f(ki['A0/s42']['nb_next30d_g'], 2)) if ki['defined'] else '—'} |")
M += ["", "## 6. kNN analog (EXPLORATORY; " + rec["knn"]["definition"] + ")", "", "| variant | segment | queries | arm | mean nb next-4h g | pool next-4h g | mean nb next-30d g | pool next-30d g | nb distinct months (mean) |", "|---|---|---|---|---|---|---|---|---|"]
rec["knn"]["summary"] = {}
for v in VAL:
    for sg, sm in segs.items():
        tsset = set(utc(t) for t in AX[sm]); rows = [r for r in rec["knn"]["rows"][v] if r["defined"] and r["ts"] in tsset]
        if not rows: M.append(f"| {v} | {sg} | 0 | — | — | — | — | — | — |"); continue
        for k in X:
            sm_ = {q: float(np.mean([r[k][q] for r in rows])) for q in ("nb_next4h_g", "pool_next4h_g", "nb_next30d_g", "pool_next30d_g")}
            rec["knn"]["summary"].setdefault(v, {}).setdefault(sg, {})[k] = sm_ | {"queries": len(rows)}
            M.append(f"| {v} | {sg} | {len(rows)} | {k} | {f(sm_['nb_next4h_g'], 2)} | {f(sm_['pool_next4h_g'], 2)} | {f(sm_['nb_next30d_g'], 2)} | {f(sm_['pool_next30d_g'], 2)} | {np.mean([r['nb_months'] for r in rows]):.1f} |")
M += ["", "### 6b. (v2) kNN realized check — August 2026 queries whose next-4h g is inside the arm window (ts ≤ 2026-08-30 20Z)", "",
      "| variant | queries | nb share from 2025–26 / 2026 | arm | mean predicted next-4h | mean realized next-4h | corr(pred, realized) | mean predicted next-30d |", "|---|---|---|---|---|---|---|---|"]
for v in VAL:
    o = rec["knn"]["realized_check_aug"][v]
    for k in X:
        M.append(f"| {v} | {o['queries_with_realized_next4h']} | {o['nb_share_2025_2026_mean']:.2f} / {o['nb_share_2026_mean']:.2f} | {k} | {f(o[k]['mean_pred_next4h'], 2)} | {f(o[k]['mean_realized_next4h'], 2)} | {f(o[k]['corr_pred_realized'], 3)} | {f(o[k]['mean_pred_next30d'], 2)} |")
M += ["", "## 7. Root-cause readout (descriptive; EXCL)", "", "### 7a. Where the spread of g across the 21 cells comes from (cov share; price + carry + cost = 1)", "", "| arm | var(g) across cells | price | carry | cost | bottom-5 cells | top-5 cells |", "|---|---|---|---|---|---|---|"]
for k in X:
    r = rec["root_cause"]["EXCL"][k]; d = r["variance_decomposition_21_cells"]
    M.append(f"| {k} | {d['var_g_across_cells']:.3f} | {d['share_price']:.3f} | {d['share_carry']:.3f} | {d['share_cost']:.3f} | {', '.join(a + ' ' + b for a, b in r['bottom5'])} | {', '.join(a + ' ' + b for a, b in r['top5'])} |")
M += ["", "### 7b. Bottom-5 vs top-5 cells (means)", "", "| arm | set | g | price | carry | cost | leg king | leg rev24 | leg fund | seat king | seat fund | τ raw | netlong |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for k in X:
    for st in ("bottom5_mean", "top5_mean"):
        a = rec["root_cause"]["EXCL"][k][st]
        M.append(f"| {k} | {st[:-5]} | {f(a['g'])} | {f(a['pnl'])} | {f(a['carry'])} | {f(a['cost'])} | {f(a['leg_king'], 2)} | {f(a['leg_rev24'], 2)} | {f(a['leg_fund'], 2)} | {a['w3_king']:.3f} | {a['w3_fund']:.3f} | {a['tau_raw']:.4f} | {f(a['netlong'])} |")
M += ["", "### 7c. High − low tercile per variable", "", "| arm | variable | Δg | Δprice | Δcarry | Δcost | Δleg king | Δleg fund | Δseat king | Δτ | Δnetlong |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for k in X:
    for nm, d in rec["root_cause"]["EXCL"][k]["high_minus_low"].items():
        M.append(f"| {k} | {nm} | {f(d['d_g'])} | {f(d['d_pnl'])} | {f(d['d_carry'])} | {f(d['d_cost'])} | {f(d['d_leg_king'], 2)} | {f(d['d_leg_fund'], 2)} | {f(d['d_w3_king'])} | {f(d['d_tau_raw'], 4)} | {f(d['d_netlong'])} |")
M += ["", "### 7d. State of the market by period (EXCL; median value, its percentile within W_ALPHA, label shares L/M/H)", "", "| variable | " + " | ".join(PER) + " |", "|---|" + "---|" * len(PER)]
for nm in VARS:
    cells_ = []
    for pn in PER:
        o = rec["root_cause"]["periods_state"]["EXCL"][pn][nm]
        cells_.append("—" if not o["n"] else f"{o['median']:.4g} (p{100 * o['median_pct_in_W_ALPHA']:.0f}; {'/'.join('%.2f' % s for s in o['label_share_low_mid_high']) if o['label_share_low_mid_high'] else 'unlab.'})")
    M.append(f"| {nm} | " + " | ".join(cells_) + " |")
M += ["", "### 7e. Performance by period", "", *PHDR]
for k in X:
    for pn, c in rec["root_cause"]["periods_perf"][k].items(): M.append(cell_row(f"{k} {pn}", c, rest=False))
M += ["", "## 8. (v2) Cell × year, EXCL — anchors / g per UTC year inside W_ALPHA; within-year high − low Δg (years where both buckets have ≥ 30 anchors) and its sign count", ""]
for k in X:
    M += [f"### {k}", "", "| cell | " + " | ".join(str(y) for y in years) + " |", "|---|" + "---|" * len(years)]
    for nm in VARS:
        o = rec["cell_by_year"][k][nm]
        for l in range(3):
            M.append(f"| {nm} {LAB[l]} | " + " | ".join((f"{o[LAB[l]][str(y)]['n']} / {f(o[LAB[l]][str(y)]['g'], 2)}" if o[LAB[l]][str(y)]["n"] else "0") for y in years) + " |")
        ws = o["within_year_sign"]
        M.append(f"| {nm} high−low (within year) | " + " | ".join(f(o["within_year_high_minus_low"][str(y)], 2) for y in years) + f" |  ← +{ws['pos']} / −{ws['neg']} of {ws['years_with_both_ge30']}; mean {f(ws['mean_of_within_year_deltas'], 2)}")
    M.append("")
out_md = f"{OUT_DIR}/G0_TABLES.md"; open(out_md, "w").write("\n".join(M) + "\n")
rec["outputs"] = {"json": {"path": out_json}, "md": {"path": out_md, "sha256": sha(out_md)}, "labels": {"path": lab_npz, "sha256": sha(lab_npz)}}
rec.update({"runtime_s": round(time.time() - T0, 1), "utc_end": utc(time.time())})
json.dump(rec, open(out_json, "w"), indent=1, default=str)
rct = {k: rec[k] for k in ("device", "self_sha256", "numpy", "argv", "env", "utc_start", "utc_end", "runtime_s", "inputs", "reproduction", "checks", "n_checks", "failed", "VERDICT")}
rct["outputs"] = rec["outputs"] | {"json": {"path": out_json, "sha256": sha(out_json)}}
json.dump(rct, open(f"{OUT_DIR}/RECEIPT_g0_regime_tables.json", "w"), indent=1, default=str)
log("VERDICT", rec["VERDICT"], FAILS)
sys.exit(0 if not FAILS else 3)
