#!/usr/bin/env python3
"""t7nc_judge_control.py — end-to-end positive / negative control of t7nc_judge.py (ae5031ce3), ordered by the lead 10:1xZ before any real reading.
Committed before it is run. It exec's the judge source with a fixed list of substitutions (each asserted to hit exactly once), so the control runs the
judge's own code path; the real judge file is not modified.
Synthetic world (no real candidate x return association can be read):
  * y: META y4 rows permuted ACROSS anchors within each calendar year (default_rng([20260927, 10, year])): each anchor gets another anchor's cross-section,
    destroying every real relation between anchor-N features and anchor-N returns.
  * candidates K1, K2, K3krw replaced on their own finiteness pattern (so U_K / year counts keep their real structure):
      POS: raw = -(coef * g + e),  g = centred within-anchor rank of the shuffled y on the finite cells, e ~ N(0,1) default_rng([20260927, 11, k, anchor]);
           the minus sign matches the frozen candidate sign (-1), so sign * c̃ is positively related to y.
      NEG: raw = e (independent noise).
    K3's Binance-volume subtraction is bypassed in the control (it would add a real, y-unrelated feature to the plant); K4 is derived by the judge from
    the planted K1 and the real RN8 indicator (about one third of names), so it carries a weaker plant and has no pass expectation.
  * G3b is not run yet (order: controls -> G3b -> real judge), so the G3b gate is bypassed in the control only.
  * receipt -> /dev/shm/alloc_2026-09-26/t7nc/T7NC_JUDGE_CONTROL_{POS,NEG}.json; the judge's stdout is captured to a file and NOT displayed.
Calibration (POS, before the judge runs): coef chosen by bisection on a replica of the O2 ΔIC formula over every 20th evaluation anchor so that the
replica's mean ΔIC(K1) = 0.010 (the lead's example strength, above the 0.003 gate).
Pre-set expectations (written before running):
  POS: judge reaches stage 5; K1, K2, K3 PASS; each of their O2 mean-of-years ΔIC within 0.010 ± 0.004.
  NEG: judge reaches stage 5 (leak (a), eval years and placebo all pass); none of K1-K4 PASS.
Only the control verdict lines are printed.
usage (pod2): /workspace/venv/bin/python -B t7nc_judge_control.py POS|NEG
"""
import sys, io, json, contextlib, hashlib
import numpy as np
from scipy.stats import rankdata
MODE = sys.argv[1]; assert MODE in ("POS", "NEG")
D = "/dev/shm/alloc_2026-09-26/t7nc"; JUDGE = f"{D}/t7nc_judge.py"; JUDGE_SHA = "d915b4c3274f09cd6bc033797081a82ad8ef4bbcd2ded0f275cff62d653b1401"   # t7nc_judge.py as committed in ae5031ce3
src = open(JUDGE).read(); assert hashlib.sha256(src.encode()).hexdigest() == JUDGE_SHA, "judge file is not the reviewed one"
SUBS = [
    ('"g3b": (f"{D}/T7NC_G3B.json", None),', '"g3b": (f"{D}/S1_GUARDS_a3.json", None),'),
    ('if not G3B.get("PASS"): stop("guards", "G3b not PASS")', 'pass   # CONTROL: G3b not yet run'),
    ('Y4 = M["y4"]; QVK = M["qvk"]; REV = P["f_rev_24h"]', 'Y4 = _CTL_Y(M["y4"], im, EV); QVK = M["qvk"]; REV = P["f_rev_24h"]'),
    ('       "K2_bt": C["K2_bt"], "K2B": C["K2B"], "K3krw_up": C["K3krw_up"], "K3krw_bt": C["K3krw_bt"]}',
     '       "K2_bt": C["K2_bt"], "K2B": C["K2B"], "K3krw_up": C["K3krw_up"], "K3krw_bt": C["K3krw_bt"]}\nRAW = _CTL_RAW(RAW, Y4, im, ic, EV)'),
    ('        with np.errstate(divide="ignore", invalid="ignore"): return np.where(b24 > 0, x - np.log(b24), np.nan)',
     '        return x   # CONTROL: plant used as is'),
    ('b = json.dumps(rec, indent=1, default=float).encode(); p = f"{D}/T7NC_JUDGE.json"',
     'b = json.dumps(rec, indent=1, default=float).encode(); p = f"{D}/T7NC_JUDGE_CONTROL_" + _CTL_MODE + ".json"'),
]
for a, b in SUBS:
    assert src.count(a) == 1, (a[:60], src.count(a)); src = src.replace(a, b)


def ctl_y(Y4, im, EV):
    import time
    EVY = np.array([time.gmtime(int(t)).tm_year for t in EV]); Y = np.array(Y4, dtype=np.float32); out = Y.copy()
    for yv in np.unique(EVY):
        rows = im[EVY == yv]; perm = np.random.default_rng([20260927, 10, int(yv)]).permutation(rows.size); out[rows] = Y[rows[perm]]
    return out


COEF = {"v": None}


def plant(real_row, ys_row, k, a, coef):
    fin = np.isfinite(real_row); g = np.zeros(real_row.size); ok = fin & np.isfinite(ys_row)
    if ok.sum() > 1: g[ok] = rankdata(ys_row[ok]) / ok.sum() - 0.5
    e = np.random.default_rng([20260927, 11, k, int(a)]).standard_normal(real_row.size)
    v = -(coef * g + e) if MODE == "POS" else e
    return np.where(fin, v, np.nan)


def ctl_raw(RAW, Y4, im, ic, EV):
    out = dict(RAW)
    for kk, name in enumerate(("K1", "K2", "K3krw")):
        arr = np.array(RAW[name], dtype=np.float64)
        for a in range(EV.size): arr[ic[a]] = plant(arr[ic[a]], Y4[im[a]].astype(np.float64), kk, a, COEF["v"])
        out[name] = arr
    return out


def calibrate(g):
    """replica of the O2 ΔIC for K1 on every 20th anchor; returns coef with replica mean ΔIC ~ 0.010 (POS only)."""
    pass
    D_ = g
    L = np.load(D_["PIN"]["legs"][0]); UN = np.load(D_["PIN"]["U_NC"][0]); C = np.load(D_["PIN"]["candidates"][0])
    M = np.load(D_["PIN"]["META"][0], allow_pickle=False); P = np.load(D_["PIN"]["PANEL"][0], allow_pickle=True)
    ua = UN["E_ts"].astype(np.int64); EV = ua[(ua >= D_["T0"]) & (ua <= D_["T1"])]
    def rows(ax, t): return np.searchsorted(ax, t)
    iu, il, ic, im, ip = rows(ua, EV), rows(L["E_ts"].astype(np.int64), EV), rows(C["E_ts"].astype(np.int64), EV), rows(M["E_ts"].astype(np.int64), EV), rows(P["ts"].astype(np.int64), EV)
    Ysh = ctl_y(M["y4"], im, EV)
    U = UN["U"].astype(bool); BF = UN["B_finite"].astype(bool); WL = L["WL"].astype(np.float64); KZ = L["KZ"]; ZFD = L["ZFD"]; K1 = C["K1"]; REV = P["f_rev_24h"]
    z, sp, resid = D_["z"], D_["sp"], D_["resid"]
    sample = range(0, EV.size, 20)
    def mean_dic(coef):
        v = []
        for a in sample:
            y = Ysh[im[a]].astype(np.float64); om = U[iu[a]] & BF[iu[a]] & np.isfinite(y)
            den = WL[il[a], 0] + WL[il[a], 2]; wk, wf = (WL[il[a], 0] / den, WL[il[a], 2] / den) if den > 1e-12 else (0.5, 0.5)
            Bv = wk * KZ[il[a]].astype(np.float64) + wf * ZFD[il[a]].astype(np.float64)
            raw = plant(K1[ic[a]].astype(np.float64), y, 0, a, coef); rev = REV[ip[a]].astype(np.float64)
            uk = om & np.isfinite(raw) & np.isfinite(rev)
            if uk.sum() < 30: continue
            ct = z(resid(rankdata(raw[uk]), rankdata(-rev[uk]))); full = np.zeros(om.size); full[uk] = ct; zb = np.zeros(om.size); zb[om] = z(Bv[om])
            v.append(sp(0.7 * zb[om] - 0.3 * full[om], y[om]) - sp(zb[om], y[om]))
        return float(np.mean(v))
    lo, hi = 0.0, 2.0
    for _ in range(30):
        c = 0.5 * (lo + hi); m = mean_dic(c)
        if abs(m - 0.010) < 3e-4: break
        lo, hi = (c, hi) if m < 0.010 else (lo, c)
    return c, m


class _Stop(Exception): pass


g = {"__name__": "__main__", "__file__": JUDGE, "_CTL_Y": ctl_y, "_CTL_RAW": ctl_raw, "_CTL_MODE": MODE}
sys.argv = [JUDGE]
# run the judge's definitions up to the data section once, to reuse its helpers and pins for the calibration replica
head = src.split("# ---- stage 1: inputs and guard receipts")[0]
exec(compile(head, JUDGE, "exec"), g)
if MODE == "POS":
    COEF["v"], rep_m = calibrate(g)
else:
    COEF["v"], rep_m = 0.0, None
out = io.StringIO(); rc = 0
with contextlib.redirect_stdout(out):
    try:
        exec(compile(src, JUDGE, "exec"), g)
    except SystemExit as e:
        rc = e.code
open(f"{D}/judge_control_{MODE}.stdout", "w").write(out.getvalue())
R = json.load(open(f"{D}/T7NC_JUDGE_CONTROL_{MODE}.json"))
stage = max(int(k[0]) for k in R["stages"]); main = R["stages"].get("5_main", {}).get("table", {})
res = {k: {"PASS": v["PASS"], "mean_of_years": round(v["O2_mean_of_years"], 5), "years_min": round(min(x["mean"] for x in v["O2_dIC_by_year"].values()), 5)}
       for k, v in main.items()}
if MODE == "POS":
    ok = stage == 5 and all(res[k]["PASS"] and abs(res[k]["mean_of_years"] - 0.010) <= 0.004 for k in ("K1", "K2", "K3"))
else:
    ok = stage == 5 and not any(res[k]["PASS"] for k in res)
line = {"control": MODE, "coef": COEF["v"], "replica_mean_dIC_K1": rep_m, "judge_rc": rc, "stage_reached": stage, "STOP": R.get("STOP"),
        "placebo_mean": {k: round(v["mean"], 5) for k, v in R["stages"].get("4_placebo_floor", {}).items()},
        "leak_a_t": {k: round(v["t"], 3) for k, v in R["stages"].get("2_leak_a_shuffle_future", {}).items()}, "result": res,
        "EXPECTATION_MET": bool(ok)}
json.dump(line, open(f"{D}/T7NC_JUDGE_CONTROL_{MODE}_verdict.json", "w"), indent=1)
print("T7NC_CONTROL", json.dumps(line), flush=True)
