#!/usr/bin/env python3
"""t7nc_judge.py — T7 S1 judge on the in-service NC book (pod2). Committed before it is run; NOT run until the lead has reviewed it line by line.
Governing texts (every decision line below carries its source tag):
  [P]  PREREG_T7_S1.md, FROZEN, sha256 62c6da52 (freeze commit 3f764ab51); §n = its section
  [A1] AMENDMENT_T7_NC_2026-09-27.md, frozen 21ecc60f5
  [A2] AMENDMENT_2_T7_NC_universe_2026-09-27.md, frozen 435559a61 (+ appended correction fbe2ce5a5, definition unchanged)
  [A3] AMENDMENT_3_T7_G2_denominator_2026-09-27.md, frozen 70edf17ed
  [I]  an interpretation fixed HERE, before any reading, where the frozen text leaves a detail open; each one is listed in INTERPRETATIONS and in the
       receipt, for the lead's review.
Stage order [P §4 "泄漏守卫(先于读门)", A1 §4 read-out order]: guards receipts (G1-G5 A3 run, G3b) -> leakage (a)(b)(c) -> expected-eval-year assertion
-> placebo noise floor -> main ΔIC table and verdicts. Any stage failing => STOP before the next stage is computed; the main ΔIC is computed only in stage 5.
usage (pod2): /workspace/venv/bin/python -B t7nc_judge.py <candidates_sha> > /dev/shm/alloc_2026-09-26/t7nc/judge.log  (receipt T7NC_JUDGE.json beside)
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
from scipy.stats import rankdata

D = "/dev/shm/alloc_2026-09-26/t7nc"
# ---- inputs, all sha-pinned ----------------------------------------------------------------------------------------------------------------
PIN = {
    "candidates": (f"{D}/T7_S1_CANDIDATES.npz", "405765ccf023c99fc9628222cf13cb92171f9ceefbde1b259098701b46aa2e71"),  # frozen t7_s1_build.py output (fb0938466)
    "U_NC": (f"{D}/U_NC.npz", "19b9dc35ab86b232f52199ad0d3642bc48dfca78e75d2640a829316da4564625"),                    # [A2 §1] universe LIVE, B_finite
    "legs": ("/dev/shm/news2_2026-09-23/work/legs.npz", "9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65"),  # [A1 row 2] WL/KZ/ZFD; RN8
    "META": ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3"),  # [A1 row 4, 9]
    "PANEL": ("/workspace/data/wide_panel_4h_v2ext.npz", "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116"),  # [A1 row 8] f_rev_24h
    "guards_a3": (f"{D}/S1_GUARDS_a3.json", None),          # [A3] G1-G5 rerun; STOP must be false; sha recorded
    "build_receipt": (f"{D}/T7_S1_BUILD_RECEIPT.json", None),  # [P §4 leak (b)(c)] self-report of the frozen build
    "g3b": (f"{D}/T7NC_G3B.json", None),                    # [P §2.4 G3b] must be PASS
}
EXPECTED_EVAL_YEARS = (2023, 2024, 2025, 2026)   # [A1 §2] literal
MIN_SUBSET = 30          # [P §4] "|U_K(N)| < 30 的锚剔除", [P §11.4]; counted on the O1 set [A2 §2]
MIN_ANCHORS = 100        # [P §4] "每个评估年(≥ 100 有效锚)", [P §11.7]
W_B, W_C = 0.7, 0.3      # [P §4] ΔIC = IC(0.7·z(B) + 0.3·z(sign·c̃)) − IC(z(B))
TH = 0.003               # [P §4] "ΔIC 均值 ≥ +0.003 且每年 ≥ 0" (read as in its source F7 §P0 L28: mean of the yearly means >= +0.003 and every year >= 0)
SIGN = {"K1": -1, "K2": -1, "K3": -1, "K4": -1}   # [P §3] signs fixed ex ante; the reverse sign is diagnostic only, never a pass [P §3]
PLACEBO_SEEDS = (0, 1, 2, 3, 4)                  # [P §4] "5 个固定种子(0–4)的锚内 c̃ 置换安慰剂"
R1_YEARS = (2025, 2026)                           # [P §5 R1] "2025–2026 子期单独报, S1 过必须 R1 同号"
T0, T1 = calendar.timegm((2023, 1, 1, 0, 0, 0)), calendar.timegm((2026, 8, 30, 20, 0, 0))   # [A1 row 5], [A1 §2]
INTERPRETATIONS = {
    "I1_K3_binance_24h": "[P §2.3, §11.6; A1 row 9] K3 = ln(KRW turnover in USDT over 24h) − ln(Binance 24h quote volume). META qvk is NOT a 4h volume: it is "
                         "the 7-day trailing mean of log1p(5m quote volume) (pod_dlw_targets_raw.py L100-108). The frozen A0 device's 4h convention is "
                         "qv4h = expm1(clip(qvk, 0, 30))·48 (w10_sleeve_t1.py L255-256, cited in RESULT_T7_feasibility L105). Implemented: Binance 24h = "
                         "sum of qv4h over the 6 META rows ending at N (rows k−5..k; qvk row k is causal: window [E−2016, E−1]). The per-anchor median "
                         "subtraction of [P §2.3] is a constant per anchor and cannot change any rank, so it is omitted.",
    "I2_K4_fund_rate": "[P §3 K4] 'fund 8h 当量现费率秩 ≥ 2/3' on NC = legs.RN8 (in-service as-of 8h-equivalent rate), percentile rank within the anchor's "
                       "eligible set Ω (ties averaged), indicator rank/|Ω| ≥ 2/3; K4 = z(K1 over U_K1) × indicator; K4 is valid exactly where K1 is valid.",
    "I3_O2_blend_scale": "[P §5 O2] c̃ is z-scored on U_K (P §4 '再 z'), set to 0 on Ω \\ U_K (neutral), and enters the blend as is (no second z over Ω); "
                         "z(B) is taken over Ω. O1: both z(B) and c̃ over U_K.",
    "I4_Omega": "Ω(N) = U_NC(N) ∩ B finite [A2 §2] ∩ y4 finite; U_K(N) = Ω ∩ {raw candidate finite} ∩ {f_rev_24h finite} (the residualisation needs rev24).",
    "I5_placebo_rule": "[P §4] 'its ΔIC mean must be < 0': the mean over the 5 seeds of each seed's all-anchor O2 ΔIC mean must be < 0 (each seed also reported); "
                       "placebo permutes c̃ within U_K with default_rng([seed, N]).",
    "I6_shuffle_future_t": "[P §4 leak (a)] y permuted within Ω per anchor (default_rng([20260927, 7, N])); ΔIC(O2) with the true c̃; t = mean/(sd/sqrt(n)) over "
                           "valid anchors pooled across the eval years; |t| < 2 required, per candidate.",
    "I7_R1": "[P §5 R1] 'S1 过必须 R1 同号': the mean O2 ΔIC over the 2025–2026 valid anchors must be > 0 (same sign as the required positive pass).",
    "I8_y": "[A1 row 4] y = META y4 (RAW Π(1+r) − 1 over [N, N+4h]) at the META row with E_ts == N; META columns are the 829 legs/PANEL symbols in order "
            "(asserted via PANEL symbols == legs symbols and META qvk width 829).",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def z(v):
    s = v.std(); return (v - v.mean()) / s if s > 0 else np.zeros_like(v)


def sp(a, b):   # Spearman = Pearson of ranks
    ra, rb = rankdata(a), rankdata(b); sa, sb = ra.std(), rb.std()
    return float(((ra - ra.mean()) * (rb - rb.mean())).mean() / (sa * sb)) if sa > 0 and sb > 0 else np.nan


def resid(y, X):   # OLS residual of y on [1, X]
    A = np.column_stack([np.ones(y.size), X]); beta, *_ = np.linalg.lstsq(A, y, rcond=None); return y - A @ beta


rec = {"device": "t7nc_judge.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "governing": {"P": "62c6da52", "A1": "21ecc60f5", "A2": "435559a61", "A3": "70edf17ed"}, "interpretations": INTERPRETATIONS, "stages": {}}


def stop(stage, why):
    rec["STOP"] = f"{stage}: {why}"; write(); print("T7NC_JUDGE STOP", rec["STOP"], flush=True); sys.exit(2)


def write():
    b = json.dumps(rec, indent=1, default=float).encode(); p = f"{D}/T7NC_JUDGE.json"
    with open(p + ".tmp", "wb") as f: f.write(b); f.flush(); os.fsync(f.fileno())
    os.replace(p + ".tmp", p); assert sha(p) == hashlib.sha256(b).hexdigest(); rec["_receipt_sha"] = hashlib.sha256(b).hexdigest()


# ---- stage 1: inputs and guard receipts -----------------------------------------------------------------------------------------------------
rec["inputs"] = {}
for k, (p, s) in PIN.items():
    h = sha(p); rec["inputs"][k] = h
    if s is not None and h != s: stop("inputs", f"{k} sha {h} != pin {s}")
G = json.load(open(PIN["guards_a3"][0]))
if G.get("STOP") is not False or G.get("amendment_3_commit", "")[:9] != "70edf17ed": stop("guards", "A3 guard receipt not green")   # [P §2.4, A3]
B_ = json.load(open(PIN["build_receipt"][0]))
if B_["candidates_sha256"] != PIN["candidates"][1]: stop("guards", "build receipt candidates sha")
leak_b = all(B_["leak_b"][f"{v}_leaky_cells"] == B_["leak_b"][f"{v}_leaky_cells_violating_G1"] > 0 for v in ("upbit", "bithumb"))   # [P §4 leak (b)]
leak_c = all(v <= -3600 for v in B_["leak_c_max_bar_open_minus_N_s"].values())                                                    # [P §4 leak (c)]
G3B = json.load(open(PIN["g3b"][0]))
if not G3B.get("PASS"): stop("guards", "G3b not PASS")                                                                              # [P §2.4 G3b]
rec["stages"]["1_guards"] = {"guards_a3_STOP": G["STOP"], "g3b_PASS": G3B["PASS"], "leak_b": leak_b, "leak_c": leak_c}
if not (leak_b and leak_c): stop("leak_b_c", "build self-report")

# ---- data -------------------------------------------------------------------------------------------------------------------------------------
L = np.load(PIN["legs"][0]); la = L["E_ts"].astype(np.int64); sym = [str(s) for s in L["symbols"]]
UN = np.load(PIN["U_NC"][0]); ua = UN["E_ts"].astype(np.int64); assert [str(s) for s in UN["symbols"]] == sym
C = np.load(PIN["candidates"][0]); cta = C["E_ts"].astype(np.int64); assert [str(s) for s in C["symbols"]] == sym
M = np.load(PIN["META"][0], allow_pickle=False); ma = M["E_ts"].astype(np.int64); assert M["qvk"].shape[1] == len(sym)
P = np.load(PIN["PANEL"][0], allow_pickle=True); pa = P["ts"].astype(np.int64); assert [str(s) for s in P["symbols"]] == sym   # I8
EV = ua[(ua >= T0) & (ua <= T1)]                                                                                                     # [A1 row 5]
def rows(axis, t, name):
    r = np.searchsorted(axis, t); assert (r < axis.size).all() and np.array_equal(axis[r], t), f"{name} axis misses NC anchors"; return r
iu, il, ic, im, ip = rows(ua, EV, "U_NC"), rows(la, EV, "legs"), rows(cta, EV, "candidates"), rows(ma, EV, "META"), rows(pa, EV, "PANEL")
Y4 = M["y4"]; QVK = M["qvk"]; REV = P["f_rev_24h"]
U = UN["U"].astype(bool); BF = UN["B_finite"].astype(bool)
WL = L["WL"].astype(np.float64); KZ = L["KZ"]; ZFD = L["ZFD"]; RN8 = L["RN8"]
EVY = np.array([time.gmtime(int(t)).tm_year for t in EV])
qv4h = np.expm1(np.clip(QVK.astype(np.float64), 0, 30)) * 48.0                                                                      # I1
RAW = {"K1": C["K1"], "K2": C["K2"], "K3krw": C["K3krw"], "K1_up": C["K1_up"], "K1_bt": C["K1_bt"], "K1B": C["K1B"], "K2_up": C["K2_up"],
       "K2_bt": C["K2_bt"], "K2B": C["K2B"], "K3krw_up": C["K3krw_up"], "K3krw_bt": C["K3krw_bt"]}


def anchor(t):
    """per-anchor arrays on Ω (I4)."""
    a = t; om = U[iu[a]] & BF[iu[a]]                                                                                             # [A2 §1-§2]
    y = Y4[im[a]].astype(np.float64); om &= np.isfinite(y)
    den = WL[il[a], 0] + WL[il[a], 2]; wk, wf = (WL[il[a], 0] / den, WL[il[a], 2] / den) if den > 1e-12 else (0.5, 0.5)            # [A1 row 2]
    Bv = wk * KZ[il[a]].astype(np.float64) + wf * ZFD[il[a]].astype(np.float64)
    b24 = qv4h[max(im[a] - 5, 0): im[a] + 1].sum(0)                                                                                 # I1
    return om, y, Bv, b24, (wk, wf)


def cand_raw(name, a, om, b24):
    if name in ("K3", "K3_up", "K3_bt"):
        k = {"K3": "K3krw", "K3_up": "K3krw_up", "K3_bt": "K3krw_bt"}[name]; x = RAW[k][ic[a]].astype(np.float64)
        with np.errstate(divide="ignore", invalid="ignore"): return np.where(b24 > 0, x - np.log(b24), np.nan)                     # [P §2.3] I1
    return RAW[name][ic[a]].astype(np.float64)


def build(name, a, om, y, Bv, b24, rng_perm=None, y_perm=None):
    """returns dict with ΔIC O2 / O1 for one anchor, or None if |U_K| < MIN_SUBSET."""
    rev = REV[ip[a]].astype(np.float64)
    if name == "K4":                                                                                                                   # [P §3 K4] I2
        raw1 = RAW["K1"][ic[a]].astype(np.float64); uk = om & np.isfinite(raw1) & np.isfinite(rev)
        if uk.sum() < MIN_SUBSET: return None
        r8 = RN8[il[a]].astype(np.float64); fin = om & np.isfinite(r8); ind = np.zeros(om.size)
        if fin.sum(): pr = np.zeros(om.size); pr[fin] = rankdata(r8[fin]) / fin.sum(); ind = (pr >= 2 / 3).astype(float)
        raw = np.full(om.size, np.nan); raw[uk] = z(raw1[uk]) * ind[uk]
    else:
        raw = cand_raw(name, a, om, b24); uk = om & np.isfinite(raw) & np.isfinite(rev)
        if uk.sum() < MIN_SUBSET: return None                                                                                          # [P §4]
    ct = z(resid(rankdata(raw[uk]), rankdata(-rev[uk])))                                                                               # [P §4] c̃
    if rng_perm is not None: ct = ct[rng_perm(uk.sum())]                                                                               # placebo [P §4]
    yy = y if y_perm is None else y_perm
    s = SIGN[name[:2]]
    full = np.zeros(om.size); full[uk] = ct                                                                                           # [P §5 O2] I3
    zb = np.zeros(om.size); zb[om] = z(Bv[om])
    d2 = sp(W_B * zb[om] + W_C * s * full[om], yy[om]) - sp(zb[om], yy[om])                                                           # O2 main
    zb1 = z(Bv[uk]); d1 = sp(W_B * zb1 + W_C * s * ct, yy[uk]) - sp(zb1, yy[uk])                                                      # O1
    return {"d2": d2, "d1": d1, "nK": int(uk.sum()), "nO": int(om.sum()), "uk": uk, "raw": raw, "ct": ct}


FAM = ("K1", "K2", "K3", "K4")                                                                                                        # [P §3, §7] N = 4

# ---- stage 2: leakage (a) shuffle-future --------------------------------------------------------------------------------------------------
sf = {k: [] for k in FAM}
for a, t in enumerate(EV):
    om, y, Bv, b24, _ = anchor(a)
    if om.sum() < MIN_SUBSET: continue
    yp = y.copy(); idx = np.flatnonzero(om); yp[idx] = y[idx][np.random.default_rng([20260927, 7, int(t)]).permutation(idx.size)]    # I6
    for k in FAM:
        r = build(k, a, om, y, Bv, b24, y_perm=yp)
        if r is not None: sf[k].append(r["d2"])
leak_a = {}
for k in FAM:
    v = np.array(sf[k]); tt = float(v.mean() / (v.std(ddof=1) / np.sqrt(v.size))) if v.size > 2 else float("nan")
    leak_a[k] = {"n": int(v.size), "mean": float(v.mean()) if v.size else None, "t": tt, "ok": bool(np.isfinite(tt) and abs(tt) < 2)}   # NaN anchors would make t NaN => not ok (fail-closed)
rec["stages"]["2_leak_a_shuffle_future"] = leak_a
if not all(v["ok"] for v in leak_a.values()): stop("leak_a", json.dumps({k: v["t"] for k, v in leak_a.items()}))              # [P §4 (a)]

# ---- stage 3: expected evaluation years ---------------------------------------------------------------------------------------------------
valid = {k: {} for k in FAM}
for a, t in enumerate(EV):
    om, y, Bv, b24, _ = anchor(a)
    for k in FAM:
        if om.sum() >= MIN_SUBSET and build(k, a, om, y, Bv, b24) is not None: valid[k][int(EVY[a])] = valid[k].get(int(EVY[a]), 0) + 1
ya = {}
for k in FAM:
    got = tuple(sorted(y for y, n in valid[k].items() if n >= MIN_ANCHORS)); ya[k] = {"valid_anchors": valid[k], "years": got, "ok": got == EXPECTED_EVAL_YEARS}
rec["stages"]["3_eval_years"] = ya
if not all(v["ok"] for v in ya.values()): stop("eval_years", json.dumps({k: v["years"] for k, v in ya.items()}))                # [A1 §2]

# ---- stage 4: placebo noise floor ---------------------------------------------------------------------------------------------------------
pl = {k: {s: [] for s in PLACEBO_SEEDS} for k in FAM}
for a, t in enumerate(EV):
    om, y, Bv, b24, _ = anchor(a)
    if om.sum() < MIN_SUBSET: continue
    for k in FAM:
        for s in PLACEBO_SEEDS:
            r = build(k, a, om, y, Bv, b24, rng_perm=np.random.default_rng([s, int(t)]).permutation)
            if r is not None: pl[k][s].append(r["d2"])
floor = {k: {"per_seed": {s: float(np.mean(v)) for s, v in pl[k].items()}, "mean": float(np.mean([np.mean(v) for v in pl[k].values()]))} for k in FAM}
for k in FAM: floor[k]["ok"] = floor[k]["mean"] < 0                                                                                    # I5
rec["stages"]["4_placebo_floor"] = floor
if not all(v["ok"] for v in floor.values()): stop("placebo", json.dumps({k: v["mean"] for k, v in floor.items()}))              # [P §4]

# ---- stage 5: main table ------------------------------------------------------------------------------------------------------------------
EXTRA = ("K1_up", "K1_bt", "K1B", "K2_up", "K2_bt", "K2B", "K3_up", "K3_bt")                                                       # [P §4 同表附报] per venue, def B
per = {k: {"d2": [], "d1": [], "yr": [], "alone": [], "resid_joint": [], "kz": [], "zfd": [], "d2_half": []} for k in FAM}
per_x = {k: {"d2": [], "yr": []} for k in EXTRA}
for a, t in enumerate(EV):
    om, y, Bv, b24, _ = anchor(a)
    if om.sum() < MIN_SUBSET: continue
    yr = int(EVY[a])
    for k in FAM:
        r = build(k, a, om, y, Bv, b24)
        if r is None: continue
        uk = r["uk"]; s = SIGN[k]; rev = REV[ip[a]].astype(np.float64)
        per[k]["d2"].append(r["d2"]); per[k]["d1"].append(r["d1"]); per[k]["yr"].append(yr)
        per[k]["alone"].append(sp(s * r["raw"][uk], y[uk]))                                                                          # 候选单独 IC
        kz = KZ[il[a]].astype(np.float64)[uk]; zf = ZFD[il[a]].astype(np.float64)[uk]
        per[k]["resid_joint"].append(sp(s * resid(rankdata(r["raw"][uk]), np.column_stack([rankdata(kz), rankdata(zf), rankdata(-rev[uk])])), y[uk]))
        per[k]["kz"].append(sp(kz, y[uk])); per[k]["zfd"].append(sp(zf, y[uk]))                                                    # 同子集 KZ / ZFD IC
        B5 = 0.5 * KZ[il[a]].astype(np.float64) + 0.5 * ZFD[il[a]].astype(np.float64)                                               # [A1 row 3] 0.5/0.5 column
        full = np.zeros(om.size); full[uk] = r["ct"]; zb = np.zeros(om.size); zb[om] = z(B5[om])
        per[k]["d2_half"].append(sp(W_B * zb[om] + W_C * s * full[om], y[om]) - sp(zb[om], y[om]))
    for k in EXTRA:
        r = build(k, a, om, y, Bv, b24)                                                                                                # cand_raw maps K3_up/K3_bt to K3krw_*
        if r is not None: per_x[k]["d2"].append(r["d2"]); per_x[k]["yr"].append(yr)


def yearly(vals, yrs):   # anchor-equal mean per year; NaN anchors (constant ranks) are skipped and counted
    v = np.array(vals, float); y_ = np.array(yrs)
    return {int(y): {"mean": float(np.nanmean(v[y_ == y])), "n": int(np.isfinite(v[y_ == y]).sum()), "nan": int((~np.isfinite(v[y_ == y])).sum())}
            for y in EXPECTED_EVAL_YEARS if (y_ == y).sum()}


table = {}
for k in FAM:
    yv = yearly(per[k]["d2"], per[k]["yr"]); mean_of_years = float(np.mean([v["mean"] for v in yv.values()]))
    r1 = np.nanmean(np.array(per[k]["d2"], float)[np.isin(per[k]["yr"], R1_YEARS)])
    passed = mean_of_years >= TH and all(v["mean"] >= 0 for v in yv.values()) and r1 > 0                                                     # [P §4] + [P §5 R1] I7
    table[k] = {"O2_dIC_by_year": yv, "O2_mean_of_years": mean_of_years, "R1_2025_26_mean": float(r1), "PASS": bool(passed),
                "dIC_minus_placebo": mean_of_years - floor[k]["mean"],                                                                 # [P §4] 报「ΔIC − 安慰剂」
                "O1_dIC_by_year": yearly(per[k]["d1"], per[k]["yr"]), "segments_O2": {"2023-24": float(np.nanmean(np.array(per[k]["d2"], float)[np.isin(per[k]["yr"], (2023, 2024))])),
                "2025-26": float(r1)}, "alone_IC_by_year": yearly(per[k]["alone"], per[k]["yr"]), "resid_joint_IC_by_year": yearly(per[k]["resid_joint"], per[k]["yr"]),
                "KZ_IC_same_subset": yearly(per[k]["kz"], per[k]["yr"]), "ZFD_IC_same_subset": yearly(per[k]["zfd"], per[k]["yr"]),
                "O2_dIC_baseline_half_half_by_year": yearly(per[k]["d2_half"], per[k]["yr"]), "anchors": len(per[k]["d2"])}
rec["stages"]["5_main"] = {"table": table, "extra_O2_dIC_by_year": {k: yearly(v["d2"], v["yr"]) for k, v in per_x.items() if v["d2"]},
                           "passing": [k for k in FAM if table[k]["PASS"]],
                           "scope": "4h RAW · NC LIVE universe ∩ B finite · two venues merged · 2023–2026 · survivor subset [P §5 R2, A1 §4]"}
rec["VERDICT"] = ("S1 PASS for " + ",".join(rec["stages"]["5_main"]["passing"]) + " -> S2 needs its own AMENDMENT first [A1 row 10]") if rec["stages"]["5_main"]["passing"] \
    else "S1 FAIL for all four -> T7 closed on this caliber [P §8]"
write(); print("T7NC_JUDGE DONE", rec["VERDICT"], rec["_receipt_sha"][:16], flush=True)
