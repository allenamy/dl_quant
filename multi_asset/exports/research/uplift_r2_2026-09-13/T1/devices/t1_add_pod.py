#!/usr/bin/env python3
"""t1_add_pod.py — pod2, ADDENDUM 1 (spec `ADDENDUM_1_SPEC_T1_2026-09-13.md`, sha asserted). Post-result readings requested by the lead;
T1's frozen verdicts are not touched. Sections: X1.2/X1.3 (units), X2 (separate carry / price state-conditional percentiles),
X3 (30-anchor overlap vs T2), X4 (H4 bridge S0..S5 vs T2 kappa*), X5 (H5 low-dispersion mechanism check).
T2's estimator functions are loaded from T2's own source file by AST (sha asserted), not retyped.
Launch: env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t1_add_pod.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, calendar, ast
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
R = "/workspace/uplift_r2_2026-09-13/T1"; T2D = "/workspace/uplift_r2_2026-09-13/T2"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    import subprocess
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
SPEC_SHA = "79b7c067aaddd63691111809e27f35564fc32c231f7b618b9cedc59ac47f0c4f"; T2K_SHA = "23b5af6b05f6ebb382599cc3b0f4fa54f0fcd42726fca643706c795c514c48fd"
assert sha(R + "/ADDENDUM_1_SPEC_T1_2026-09-13.md") == SPEC_SHA, "spec sha"
assert sha(T2D + "/devices/t2_kappa.py") == T2K_SHA, "t2_kappa sha"
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
assert GPU0.replace(" ", "") == "0%,2MiB", GPU0
t0 = time.time()
B = 2000
utc = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
# ------------------------------------------------------------------ T2 estimator functions, verbatim from T2's source
src = open(T2D + "/devices/t2_kappa.py").read(); tree = ast.parse(src)
want = {"xz", "load_tree", "sigma_rows", "aggregates", "mom", "inv_small", "cluster_fit", "estimate"}
mod = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in want], type_ignores=[])
NS = dict(np=np, rankdata=rankdata, time=time, calendar=calendar, UMASK="/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", NMIN=80, WINS=0.20, EMB=8 * 3600, MIN_BIN=180)
exec(compile(mod, "t2_kappa_functions", "exec"), NS)
assert want <= set(NS), sorted(want - set(NS))
META = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"; PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
X_META = "/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"; X_PANEL = "/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"
KR = json.load(open(T2D + "/receipts/RECEIPT_T2_kappa_main.json")); REF = {e["T_iso"]: e for e in KR["refits"]}
tr = NS["load_tree"](META, PANEL); E = tr["E"]; nA = len(E)
A = NS["aggregates"](tr)
day_m = (E // 86400).astype(np.int64); week_m = ((E // 86400 + 3) // 7).astype(np.int64); valid = np.nonzero(A["valid"])[0]
T0801 = calendar.timegm((2026, 8, 1, 0, 0, 0))
w = valid[E[valid] <= T0801 - 8 * 3600]; g_ref = NS["estimate"](A, E, w, day_m, week_m)
tx = NS["load_tree"](X_META, X_PANEL, carry_forward_umask=True)
LIVE_LO = calendar.timegm((2026, 8, 26, 0, 0, 0)); LIVE_HI = calendar.timegm((2026, 9, 10, 0, 0, 0))
live = [i for i in range(len(tx["E"])) if LIVE_LO <= int(tx["E"][i]) <= LIVE_HI and int(tx["E"][i]) in tx["prow"]]
Ax = NS["aggregates"](tx, anchors=live); li = np.array([i for i in live if Ax["valid"][i]], np.int64)
dayx = (tx["E"] // 86400).astype(np.int64); weekx = ((tx["E"] // 86400 + 3) // 7).astype(np.int64)
g_d4 = NS["estimate"](Ax, tx["E"], li, dayx, weekx)
GT2 = dict(refit_0801_b=g_ref["b"], receipt_b=REF["2026-08-01"]["b"], d4_b=g_d4["b"], receipt_d4_b=KR["d4_live_window"]["estimate"]["b"])
GT2["PASS"] = bool(abs(GT2["refit_0801_b"] - GT2["receipt_b"]) <= 1e-6 and abs(GT2["d4_b"] - GT2["receipt_d4_b"]) <= 1e-6)
print("GATE_G_T2", json.dumps(GT2), round(time.time() - t0, 1), flush=True)
assert GT2["PASS"], "G-T2 failed: X4 not reported"
q1, q2 = REF["2026-08-01"]["sigma"]["q1"], REF["2026-08-01"]["sigma"]["q2"]
sig_row = NS["sigma_rows"](tr["FN"], tr["IV"])
sig_m = np.array([sig_row[A["j"][i]] if A["j"][i] >= 0 else np.nan for i in range(nA)])
def t2bin(s): return np.where(~np.isfinite(s), -1, np.where(s <= q1, 0, np.where(s <= q2, 1, 2)))
# ------------------------------------------------------------------ T1 inputs
ARMS = ["C0_s42", "C0_s2027", "NW_s42", "NW_s2027"]
ST = np.load(R + "/receipts/T1_states.npz", allow_pickle=True); SC = [str(c) for c in ST["cols"]]; SV = ST["S"]; smap = {int(t): i for i, t in enumerate(SV[:, 0].astype(np.int64))}
PRIM = ["DISP24", "BREADTH72", "BTC72", "SIGF", "MUF", "PUMP72"]
def st_on(ts_, s): c = SC.index(s); return np.array([SV[smap[int(t)], c] if int(t) in smap else np.nan for t in ts_])
DZ = np.load(R + "/receipts/T1_d2.npz", allow_pickle=True); DC = [str(c) for c in DZ["cols"]]; DD = DZ["D"]; dci = {c: i for i, c in enumerate(DC)}; SYM = [str(s) for s in DZ["symbols"]]; sidx = {s: i for i, s in enumerate(SYM)}
RZ = np.load(R + "/receipts/T1_real_names.npz", allow_pickle=True); RA = RZ["anchors"]; RAC = [str(c) for c in RZ["anchor_cols"]]; rai = {c: i for i, c in enumerate(RAC)}
RX = RZ["rows"]; RXC = [str(c) for c in RZ["cols"]]; rxi = {c: i for i, c in enumerate(RXC)}
LIVE0 = 1787716800; LIVE1 = 1789156800; TS_WA0 = 1656547200; TS_WA1 = 1788120000; A30_LO = 1787702400; A30_HI = 1788120000
# REAL per anchor (all anchors in the ledger copy): price, carry(+paid), cost, held gross abs, short-cohort
REAL = {}
for r in RA:
    a = int(r[rai["A"]]); gsum = r[rai["gross"]]
    REAL[a] = dict(price=r[rai["price"]] / gsum * 1e4, carry=-r[rai["fund"]] / gsum * 1e4, cost=-(r[rai["fee"]] + r[rai["timing"]]) / gsum * 1e4, gross=gsum, held_abs=0.0)
for x in RX:
    a = int(x[rxi["A"]])
    if a in REAL and x[rxi["held"]] > 0 and np.isfinite(x[rxi["notional_at_mid"]]): REAL[a]["held_abs"] += abs(x[rxi["notional_at_mid"]])
for a in REAL: REAL[a]["g"] = REAL[a]["price"] - REAL[a]["carry"] - REAL[a]["cost"]
D2 = {int(r[dci["A"]]): dict(price=r[dci["price"]], carry=r[dci["carry"]], k=int(r[dci["k_meta"]])) for r in DD}
# D2 row for 2026-08-26 00Z (same formulas as t1_d2.py)
MX = tx["MT"]; PXz = tx["PW"]; Yx = MX["y4"].astype(np.float64); Ex = tx["E"]; emx = {int(t): i for i, t in enumerate(Ex)}; FNx = PXz["f_fund_now"].astype(np.float64); IVx = PXz["f_fund_iv"].astype(np.float64)
IVfx = np.where(np.isfinite(IVx) & (IVx > 0), IVx, 8.0); C4x = np.nan_to_num(FNx, nan=0.0) * (4.0 / IVfx)
dtl = json.load(open(R + "/private/target_live/%d.json" % A30_LO)); wv = np.zeros(829)
for s, v in dtl["weights"].items():
    if s in sidx: wv[sidx[s]] += float(v)
kk = emx[A30_LO]; jj = tx["prow"][A30_LO]; rr_ = Yx[kk]; fin = np.isfinite(rr_); gw = np.abs(wv).sum()
D2[A30_LO] = dict(price=float((wv[fin] * rr_[fin]).sum() / gw * 1e4), carry=float((wv * C4x[jj]).sum() / gw * 1e4), k=kk, producer=str(dtl.get("producer")))
OUT = dict(spec_sha256=SPEC_SHA, gate_G_T2=GT2, t2_sigma_cut_points_20260801=dict(q1=q1, q2=q2))
# ------------------------------------------------------------------ helpers
def day_boot_ratio(days, num, den, k_gen, draws_cache={}):
    """ratio of sums with UTC-day block bootstrap; returns point, ci95"""
    u, inv = np.unique(days, return_inverse=True); nd = len(u)
    sn = np.bincount(inv, weights=num, minlength=nd); sd = np.bincount(inv, weights=den, minlength=nd)
    key = (k_gen, nd, tuple(u[:3]), tuple(u[-3:]))
    if key not in draws_cache:
        rng = np.random.default_rng([20260905, k_gen]); draws_cache[key] = rng.integers(0, nd, size=(B, nd))
    d = draws_cache[key]; rep = sn[d].sum(1) / sd[d].sum(1)
    return float(sn.sum() / sd.sum()), [float(np.nanpercentile(rep, 2.5)), float(np.nanpercentile(rep, 97.5))]
def day_boot_mean(days, v, k_gen):
    return day_boot_ratio(days, v, np.ones(len(v)), k_gen)
def ols_boot(idx, Sxx, Sxy, days, k_gen, col=1, single=False):
    u, inv = np.unique(days[idx], return_inverse=True); nd = len(u)
    if single:
        sx = np.bincount(inv, weights=Sxx[idx], minlength=nd); sy = np.bincount(inv, weights=Sxy[idx], minlength=nd)
        rng = np.random.default_rng([20260905, k_gen]); d = rng.integers(0, nd, size=(B, nd))
        rep = sy[d].sum(1) / sx[d].sum(1); return float(sy.sum() / sx.sum()), [float(np.percentile(rep, 2.5)), float(np.percentile(rep, 97.5))]
    Dxx = np.zeros((nd, 2, 2)); Dxy = np.zeros((nd, 2)); np.add.at(Dxx, inv, Sxx[idx]); np.add.at(Dxy, inv, Sxy[idx])
    pt = np.linalg.solve(Dxx.sum(0), Dxy.sum(0))[col]
    rng = np.random.default_rng([20260905, k_gen]); d = rng.integers(0, nd, size=(B, nd)); rep = np.empty(B)
    for b in range(B): rep[b] = np.linalg.solve(Dxx[d[b]].sum(0), Dxy[d[b]].sum(0))[col]
    return float(pt), [float(np.percentile(rep, 2.5)), float(np.percentile(rep, 97.5))]
YM_m = np.array([time.gmtime(int(t))[:2] for t in E])
def mperiod(name, ts_arr, ym):
    wa = (ts_arr >= TS_WA0) & (ts_arr <= TS_WA1)
    if name == "W_ALPHA": return wa
    if name == "Y2022H2": return wa & (ym[:, 0] == 2022)
    if name in ("Y2023", "Y2024", "Y2025"): return wa & (ym[:, 0] == int(name[1:]))
    if name == "H1_2026": return wa & (ym[:, 0] == 2026) & (ym[:, 1] <= 6)
    if name == "M2026_07": return wa & (ym[:, 0] == 2026) & (ym[:, 1] == 7)
    if name == "M2026_08": return wa & (ym[:, 0] == 2026) & (ym[:, 1] == 8)
    if name == "A30": return (ts_arr >= A30_LO) & (ts_arr <= A30_HI)
    if name == "Y2022H2_2023": return wa & ((ym[:, 0] == 2022) | (ym[:, 0] == 2023))
    if name == "Y2024_H1_2026": return wa & ((ym[:, 0] == 2024) | (ym[:, 0] == 2025) | ((ym[:, 0] == 2026) & (ym[:, 1] <= 6)))
    raise KeyError(name)
PERIODS = ["Y2022H2", "Y2023", "Y2024", "Y2025", "H1_2026", "M2026_07", "M2026_08", "A30", "W_ALPHA"]
# ------------------------------------------------------------------ X4 S0..S2 on the main tree (+ live on x0910)
X4 = dict(S0_S2={}, S3_S5={}, live={}, path=[])
binm = t2bin(sig_m)
for p in PERIODS:
    pm = mperiod(p, E, YM_m) & A["valid"]
    for bname, bsel in (("all", np.ones(nA, bool)), ("low", binm == 0), ("mid", binm == 1), ("high", binm == 2)):
        idx = np.nonzero(pm & bsel)[0]
        if len(idx) < 30: X4["S0_S2"]["%s|%s" % (p, bname)] = dict(n=int(len(idx))); continue
        s0 = ols_boot(idx, A["Sxx"], A["Sxy"], day_m, 21); s1 = ols_boot(idx, A["Sxx"], A["Sxy_raw"], day_m, 21)
        s2 = ols_boot(idx, A["Sxx"][:, 1, 1], A["Sxy_raw"][:, 1], day_m, 21, single=True)
        X4["S0_S2"]["%s|%s" % (p, bname)] = dict(n=int(len(idx)), S0_b=s0, S1_b=s1, S2_b=s2)
Sxx_live = Ax["Sxx"]; X4["live"]["x0910_0826_0910"] = dict(n=int(len(li)), S0_b=ols_boot(li, Ax["Sxx"], Ax["Sxy"], dayx, 21), S1_b=ols_boot(li, Ax["Sxx"], Ax["Sxy_raw"], dayx, 21), S2_b=ols_boot(li, Ax["Sxx"][:, 1, 1], Ax["Sxy_raw"][:, 1], dayx, 21, single=True))
print("X4 S0-S2 done", round(time.time() - t0, 1), flush=True)
# ------------------------------------------------------------------ per-arm book quantities
F15 = {sd: np.load(R + "/private/r15_arms_rec/F_s%s.npz" % sd, allow_pickle=True)["rec"] for sd in ("42", "2027")}
X2 = {}; X3 = {}; X5 = {}; X1 = {}
for arm in ARMS:
    Z = np.load(R + "/arms/%s.npz" % arm, allow_pickle=True); rec = Z["d30_n2_c42_rec"]; ts = rec[:, 0].astype(np.int64); gt = rec[:, 5]
    price = rec[:, 19] / gt; carry = rec[:, 20] / gt; cost = rec[:, 21] / gt; g = rec[:, 18] / gt; w3f = rec[:, 16]
    SMR = Z["d30_n2_c42_T1SMR"]; YV = Z["d30_n2_c42_T1YV"].astype(np.float64); C4 = Z["d30_n2_c42_T1C4"].astype(np.float64); RN8 = Z["d30_n2_c42_T1RN"].astype(np.float64)
    smr = SMR.astype(np.float64).sum(1); fund = SMR[:, 2, :].astype(np.float64); del SMR
    YVw = np.clip(YV, -0.20, 0.20)
    num3 = (fund * YV).sum(1); den3 = (fund * C4).sum(1); num3w = (fund * YVw).sum(1)
    Lm = smr > 0; Sm = smr < 0
    num3L = np.where(Lm, fund * YV, 0).sum(1); den3L = np.where(Lm, fund * C4, 0).sum(1); num3S = np.where(Sm, fund * YV, 0).sum(1); den3S = np.where(Sm, fund * C4, 0).sum(1)
    coh = Sm & (np.nan_to_num(RN8, nan=1.0) <= -0.0010); num4 = np.where(coh, smr * YV, 0).sum(1); den4 = np.where(coh, smr * C4, 0).sum(1)
    fshare = (np.sign(smr) * fund).sum(1) / np.maximum(np.abs(smr).sum(1), 1e-18)
    fcarry = den3 * 1e4 / gt
    day_r = ts // 86400; ym_r = np.array([time.gmtime(int(t))[:2] for t in ts])
    emap_m = {int(t): i for i, t in enumerate(E)}; sig_r = np.array([sig_m[emap_m[int(t)]] for t in ts]); bin_r = t2bin(sig_r)
    sigf_r = st_on(ts, "SIGF")
    if arm.startswith("C0"):
        fr = F15[arm.split("_s")[1]]; assert np.array_equal(fr[:, 0].astype(np.int64), ts)
        dP = fr[:, 19] / fr[:, 5] - price; dC = fr[:, 20] / fr[:, 5] - carry
    # ---- X4 S3..S5 by period and T2 sigma bin
    S35 = {}
    for p in PERIODS:
        pm = mperiod(p, ts, ym_r)
        for bname, bsel in (("all", np.ones(len(ts), bool)), ("low", bin_r == 0), ("mid", bin_r == 1), ("high", bin_r == 2)):
            idx = pm & bsel
            if idx.sum() < 30: S35["%s|%s" % (p, bname)] = dict(n=int(idx.sum())); continue
            o = dict(n=int(idx.sum()), S3_b=day_boot_ratio(day_r[idx], num3[idx], den3[idx], 21), S3w_b=day_boot_ratio(day_r[idx], num3w[idx], den3[idx], 21),
                     S3_long_b=day_boot_ratio(day_r[idx], num3L[idx], den3L[idx], 21), S3_short_b=day_boot_ratio(day_r[idx], num3S[idx], den3S[idx], 21),
                     S4_rho=day_boot_ratio(day_r[idx], num4[idx], den4[idx], 21), fund_carry_bps=day_boot_mean(day_r[idx], fcarry[idx], 21))
            if arm.startswith("C0"): o["S5_b_arm"] = day_boot_ratio(day_r[idx], dP[idx], dC[idx], 21)
            S35["%s|%s" % (p, bname)] = o
    X4["S3_S5"][arm] = S35
    # expanding path at T2 refit dates (all rec rows with E <= T - 8h)
    if arm == "C0_s42":
        for e in KR["refits"]:
            m_ = ts <= e["T"] - 8 * 3600
            if m_.sum() < 100: continue
            X4["path"].append(dict(T_iso=e["T_iso"], T2_b=e.get("b"), T2_kappa_raw=e.get("kappa_raw"), T1_S3_b_cum=float(num3[m_].sum() / den3[m_].sum()), T1_S4_rho_cum=float(num4[m_].sum() / den4[m_].sum()),
                                   T1_S5_b_arm_cum=float(dP[m_].sum() / dC[m_].sum()), n_rec=int(m_.sum())))
    # ---- X5 mechanism check
    X5a = {}
    for p in ("Y2022H2", "Y2023", "Y2022H2_2023", "Y2024_H1_2026"):
        pm = mperiod(p, ts, ym_r); o = dict(n=int(pm.sum()))
        o["M1_share_low_T2sigma"] = float(np.mean(bin_r[pm] == 0)); o["M1_share_SIGF_lt_4p75"] = float(np.mean(sigf_r[pm][np.isfinite(sigf_r[pm])] < 4.75))
        for bname, bsel in (("low", bin_r == 0), ("high", bin_r == 2), ("mid", bin_r == 1)):
            idx = pm & bsel
            if idx.sum() < 30: o[bname] = dict(n=int(idx.sum())); continue
            o[bname] = dict(n=int(idx.sum()), fund_carry_bps=day_boot_mean(day_r[idx], fcarry[idx], 22), S3_b=day_boot_ratio(day_r[idx], num3[idx], den3[idx], 22),
                            fund_eff_gross_share=day_boot_mean(day_r[idx], fshare[idx], 22), w3_fund_nominal=float(w3f[idx].mean()), g=day_boot_mean(day_r[idx], g[idx], 22),
                            price=float(price[idx].mean()), carry=float(carry[idx].mean()))
        if o.get("low", {}).get("n", 0) >= 30 and o.get("high", {}).get("n", 0) >= 30:
            il = pm & (bin_r == 0); ih = pm & (bin_r == 2)
            # difference low - high of the effective fund share, stratified day bootstrap (k=22)
            ul, invl = np.unique(day_r[il], return_inverse=True); uh, invh = np.unique(day_r[ih], return_inverse=True)
            sl = np.bincount(invl, weights=fshare[il]); cl = np.bincount(invl); sh_ = np.bincount(invh, weights=fshare[ih]); ch = np.bincount(invh)
            rng = np.random.default_rng([20260905, 22]); rep = np.empty(B)
            for b in range(B):
                dl = rng.integers(0, len(ul), len(ul)); dh = rng.integers(0, len(uh), len(uh)); rep[b] = sl[dl].sum() / cl[dl].sum() - sh_[dh].sum() / ch[dh].sum()
            o["M3_diff_low_minus_high"] = [float(fshare[il].mean() - fshare[ih].mean()), [float(np.percentile(rep, 2.5)), float(np.percentile(rep, 97.5))]]
            lo_ = o["low"]; hi_ = o["high"]
            o["M2"] = bool(lo_["fund_carry_bps"][1][0] > 0 and lo_["S3_b"][0] <= 0.5)
            o["M3"] = bool(o["M3_diff_low_minus_high"][0] > 0)
            o["M4"] = bool(lo_["g"][0] < 0 and lo_["g"][0] < hi_["g"][0])
            o["fits"] = ("FITS" if (o["M1_share_low_T2sigma"] >= 0.5 and o["M2"] and o["M3"] and o["M4"]) else ("DOES NOT FIT" if (not o["M2"] or not o["M4"]) else "PARTIAL"))
        X5a[p] = o
    X5[arm] = X5a
    # ---- X2 separate carry / price percentiles; X3 overlap
    PRE = (ts >= TS_WA0) & (ts <= TS_WA1) & (ts < LIVE0)
    SREC = {s: st_on(ts, s) for s in PRIM}; srt = {s: np.sort(SREC[s][PRE][np.isfinite(SREC[s][PRE])]) for s in PRIM}
    ecdf = lambda s, x: np.where(np.isfinite(x), np.searchsorted(srt[s], x, side="right") / len(srt[s]), np.nan)
    idxPRE = np.where(PRE)[0]
    def windows(nL):
        st_ = [idxPRE[q] for q in range(0, len(idxPRE) - nL + 1, 6) if idxPRE[q + nL - 1] - idxPRE[q] == nL - 1]
        WM = np.column_stack([ecdf(s, np.array([np.nanmean(SREC[s][a:a + nL]) for a in st_])) for s in PRIM])
        return st_, WM, np.array([carry[a:a + nL].mean() for a in st_]), np.array([price[a:a + nL].mean() for a in st_])
    def live_vec(anchors):
        return np.array([float(ecdf(s, np.array(np.nanmean(st_on(np.array(anchors), s))))) for s in PRIM])
    def pct_block(nL, anchors_state, stats):
        st_, WM, cw, pw = windows(nL); lv = live_vec(anchors_state)
        ok = np.all(np.isfinite(WM), 1); dist = np.sqrt(((WM - lv) ** 2).sum(1)); near = np.where(ok)[0][np.argsort(dist[ok], kind="stable")[:int(round(0.1 * ok.sum()))]]
        res = dict(n_windows=len(st_), n_cond=int(len(near)), live_state_pct=[round(float(x), 3) for x in lv], cond_years={int(y): int(c) for y, c in zip(*np.unique([time.gmtime(int(ts[st_[q]])).tm_year for q in near], return_counts=True))},
                   cond_carry_q=[float(x) for x in np.percentile(cw[near], [2.5, 10, 50, 90, 97.5])], cond_price_q=[float(x) for x in np.percentile(pw[near], [2.5, 10, 50, 90, 97.5])], stats={})
        for nm, (kind, val) in stats.items():
            arr = cw if kind == "carry" else pw
            res["stats"][nm] = dict(value=float(val), uncond_pct=float(np.mean(arr <= val)), cond_pct=float(np.mean(arr[near] <= val)))
        cps = [v["cond_pct"] for k2, v in res["stats"].items() if k2.startswith("carry")]; pps = [v["cond_pct"] for k2, v in res["stats"].items() if k2.startswith("price")]
        res["carry_reading"] = "ANOMALOUS-HIGH" if all(x > 0.975 for x in cps) else ("WITHIN RANGE" if all(x <= 0.90 for x in cps) else "INTERMEDIATE")
        res["price_reading"] = "ANOMALOUS-LOW" if all(x < 0.025 for x in pps) else ("WITHIN RANGE" if all(x >= 0.10 for x in pps) else "INTERMEDIATE")
        return res
    reg_real = [a for a in sorted(REAL) if LIVE0 <= a <= LIVE1]; reg_d2 = [a for a in sorted(D2) if LIVE0 <= a <= 1789056000 - 57600]
    com = sorted(set(reg_real) & set(reg_d2))
    a30 = [a for a in range(A30_LO, A30_HI + 1, 14400)]; a30_real = [a for a in a30 if a in REAL]; a30_d2 = [a for a in a30 if a in D2]
    mean_ = lambda dct, keys, f: float(np.mean([f(dct[k]) for k in keys]))
    rpos = {int(t): i for i, t in enumerate(ts)}; a30_rec = [rpos[a] for a in a30]
    X2[arm] = dict(
        W_reg=pct_block(len(reg_d2), reg_d2, {"carry_REAL": ("carry", mean_(REAL, reg_real, lambda x: x["carry"])), "carry_REAL_modeleq": ("carry", mean_(REAL, reg_real, lambda x: x["carry"]) / 0.733), "carry_D2": ("carry", mean_(D2, reg_d2, lambda x: x["carry"])),
                                              "price_REAL": ("price", mean_(REAL, reg_real, lambda x: x["price"])), "price_REAL_scaled": ("price", mean_(REAL, reg_real, lambda x: x["price"]) / 0.835), "price_D2": ("price", mean_(D2, reg_d2, lambda x: x["price"]))}),
        W_com=pct_block(len(com), com, {"carry_REAL": ("carry", mean_(REAL, com, lambda x: x["carry"])), "carry_REAL_modeleq": ("carry", mean_(REAL, com, lambda x: x["carry"]) / 0.733), "carry_D2": ("carry", mean_(D2, com, lambda x: x["carry"])),
                                        "price_REAL": ("price", mean_(REAL, com, lambda x: x["price"])), "price_REAL_scaled": ("price", mean_(REAL, com, lambda x: x["price"]) / 0.835), "price_D2": ("price", mean_(D2, com, lambda x: x["price"]))}),
        W_30=pct_block(30, a30, {"carry_replay": ("carry", float(carry[a30_rec].mean())), "carry_D2": ("carry", mean_(D2, a30_d2, lambda x: x["carry"])), "carry_REAL": ("carry", mean_(REAL, a30_real, lambda x: x["carry"])), "carry_REAL_modeleq": ("carry", mean_(REAL, a30_real, lambda x: x["carry"]) / 0.733),
                                 "price_replay": ("price", float(price[a30_rec].mean())), "price_D2": ("price", mean_(D2, a30_d2, lambda x: x["price"])), "price_REAL": ("price", mean_(REAL, a30_real, lambda x: x["price"])), "price_REAL_scaled": ("price", mean_(REAL, a30_real, lambda x: x["price"]) / 0.835)}))
    X2[arm]["counts"] = dict(reg_real=len(reg_real), reg_d2=len(reg_d2), common=len(com), a30=len(a30), a30_real=len(a30_real), a30_d2=len(a30_d2))
    # X3 per-anchor rows (replay for this arm)
    X3[arm] = dict(price_A30=float(price[a30_rec].mean()), carry_A30=float(carry[a30_rec].mean()), g_A30=float(g[a30_rec].mean()), carry_WALPHA=float(carry[(ts >= TS_WA0) & (ts <= TS_WA1)].mean()),
                   carry_H1_2026=float(carry[mperiod("H1_2026", ts, ym_r)].mean()), carry_M2026_07=float(carry[mperiod("M2026_07", ts, ym_r)].mean()),
                   per_anchor={utc(a): dict(price=float(price[rpos[a]]), carry=float(carry[rpos[a]]), g=float(g[rpos[a]])) for a in a30})
    ca = [a for a in a30_real]; cr = [rpos[a] for a in ca]
    X3[arm]["paired_on_A30_REAL"] = dict(n=len(ca), mean_REAL_minus_replay=float(np.mean([REAL[a]["price"] for a in ca]) - price[cr].mean()),
                                         mean_D2_minus_replay=float(np.mean([D2[a]["price"] for a in ca if a in D2]) - np.mean([price[rpos[a]] for a in ca if a in D2])),
                                         mean_REAL_minus_D2=float(np.mean([REAL[a]["price"] - D2[a]["price"] for a in ca if a in D2])), n_with_D2=int(sum(1 for a in ca if a in D2)),
                                         replay_price_on_REAL_subset=float(price[cr].mean()), REAL_price=float(np.mean([REAL[a]["price"] for a in ca])))
    del YV, C4, RN8, smr, fund, YVw
    print("arm", arm, "done", round(time.time() - t0, 1), flush=True)
# ------------------------------------------------------------------ arm-independent X3 / X1 / live book quantities
G30 = dict(C0_s42_price=X3["C0_s42"]["price_A30"], C0_s2027_price=X3["C0_s2027"]["price_A30"], C0_s42_carry=X3["C0_s42"]["carry_A30"], C0_s2027_carry=X3["C0_s2027"]["carry_A30"], T2_price=[5.76, 5.66], T2_carry=[1.013, 1.019])
G30["PASS"] = bool(abs(G30["C0_s42_price"] - 5.76) <= 0.01 and abs(G30["C0_s2027_price"] - 5.66) <= 0.01 and abs(G30["C0_s42_carry"] - 1.013) <= 0.01 and abs(G30["C0_s2027_carry"] - 1.019) <= 0.01)
a30 = [a for a in range(A30_LO, A30_HI + 1, 14400)]
E1r = [a for a in sorted(REAL) if LIVE0 <= a <= A30_HI]; E2r = [a for a in sorted(REAL) if A30_HI < a <= LIVE1]
E1d = [a for a in sorted(D2) if LIVE0 <= a <= A30_HI]; E2d = [a for a in sorted(D2) if A30_HI < a <= 1788998400]
allr = E1r + E2r; alld = E1d + E2d
def seg(dct, keys, f="price"): return dict(n=len(keys), mean=float(np.mean([dct[k][f] for k in keys])) if keys else None, contribution_to_window_mean=None)
X3c = dict(gate_G30=G30, A30_anchor_rows={utc(a): dict(REAL=({k: float(REAL[a][k]) for k in ("price", "carry", "cost")} if a in REAL else None), D2=({k: float(D2[a][k]) for k in ("price", "carry")} if a in D2 else None)) for a in a30},
           A30_means=dict(REAL_n=int(sum(1 for a in a30 if a in REAL)), REAL_price=float(np.mean([REAL[a]["price"] for a in a30 if a in REAL])), REAL_carry=float(np.mean([REAL[a]["carry"] for a in a30 if a in REAL])),
                          D2_n=int(sum(1 for a in a30 if a in D2)), D2_price=float(np.mean([D2[a]["price"] for a in a30 if a in D2])), D2_carry=float(np.mean([D2[a]["carry"] for a in a30 if a in D2]))),
           split=dict(REAL=dict(E1=seg(REAL, E1r), E2=seg(REAL, E2r), window=seg(REAL, allr)), D2=dict(E1=seg(D2, E1d), E2=seg(D2, E2d), window=seg(D2, alld))))
for inst, dct, e1, e2 in (("REAL", REAL, E1r, E2r), ("D2", D2, E1d, E2d)):
    N = len(e1) + len(e2)
    X3c["split"][inst]["E1"]["contribution_to_window_mean"] = float(np.sum([dct[a]["price"] for a in e1]) / N)
    X3c["split"][inst]["E2"]["contribution_to_window_mean"] = float(np.sum([dct[a]["price"] for a in e2]) / N)
def daily(dct, keys):
    dd = {}
    for a in keys: dd.setdefault(time.strftime("%Y-%m-%d", time.gmtime(a)), []).append(dct[a]["price"])
    return {d: dict(n=len(v), mean=float(np.mean(v)), sum=float(np.sum(v))) for d, v in sorted(dd.items())}
X3c["daily_REAL"] = daily(REAL, allr); X3c["daily_D2"] = daily(D2, alld)
srt_days = sorted(X3c["daily_REAL"].items(), key=lambda kv: kv[1]["mean"])
X3c["REAL_most_negative_days"] = srt_days[:5]; X3c["REAL_most_positive_days"] = srt_days[-5:][::-1]
m1 = X3c["split"]["REAL"]["E1"]["mean"]; m2 = X3c["split"]["REAL"]["E2"]["mean"]; d1 = X3c["split"]["D2"]["E1"]["mean"]
pr = X3["C0_s42"]["paired_on_A30_REAL"]
X3c["reading_a"] = bool(m1 > 0 and d1 > 0 and m2 < 0); X3c["reading_b"] = bool(abs(pr["mean_REAL_minus_replay"]) >= 2.5)
# X1 units
gn = np.array([REAL[a]["held_abs"] / REAL[a]["gross"] for a in sorted(REAL) if LIVE0 <= a <= LIVE1 and REAL[a]["gross"] > 0])
com = sorted(set([a for a in REAL if LIVE0 <= a <= LIVE1]) & set([a for a in D2 if a >= LIVE0]))
xc = np.array([D2[a]["carry"] for a in com]); yc = np.array([REAL[a]["carry"] for a in com]); bb = np.polyfit(xc, yc, 1)
X1 = dict(gross_norm_held_abs_over_realized_gross=dict(mean=float(gn.mean()), p10=float(np.percentile(gn, 10)), p90=float(np.percentile(gn, 90)), n=int(len(gn))),
          common_carry_REAL_over_D2=dict(n=len(com), mean_REAL=float(yc.mean()), mean_D2=float(xc.mean()), ratio_of_means=float(yc.mean() / xc.mean()), slope=float(bb[0]), intercept=float(bb[1])),
          A30_carry_replay_over_D2={arm: float(X3[arm]["carry_A30"] / X3c["A30_means"]["D2_carry"]) for arm in ARMS})
X1["unit_same"] = bool(0.95 <= X1["gross_norm_held_abs_over_realized_gross"]["mean"] <= 1.05)
nums = dict(P1_quoted=1.371, REAL_reg89=float(np.mean([REAL[a]["carry"] for a in sorted(REAL) if LIVE0 <= a <= LIVE1])), REAL_common78=float(yc.mean()),
            D2_reg89=float(np.mean([D2[a]["carry"] for a in D2 if a >= LIVE0])), D2_common78=float(xc.mean()), C0_s42_replay_A30=X3["C0_s42"]["carry_A30"])
dens = dict(W_ALPHA=X3["C0_s42"]["carry_WALPHA"], H1_2026=X3["C0_s42"]["carry_H1_2026"], M2026_07=X3["C0_s42"]["carry_M2026_07"], analog_T1_s9=0.798)
X1["ratio_table"] = {n: {d: float(v / dv) for d, dv in dens.items()} for n, v in nums.items()}; X1["numerators"] = nums; X1["denominators_C0_s42"] = dens
# live-window book compensation analogs for X5/X4
lv = [a for a in sorted(D2) if a >= A30_LO]
X4["live"]["D2_book_price_over_carry"] = float(np.sum([D2[a]["price"] for a in lv]) / np.sum([D2[a]["carry"] for a in lv]))
X4["live"]["REAL_book_price_over_carry"] = float(np.sum([REAL[a]["price"] for a in sorted(REAL) if LIVE0 <= a <= LIVE1]) / np.sum([REAL[a]["carry"] for a in sorted(REAL) if LIVE0 <= a <= LIVE1]))
X5["live_window"] = dict(n=len(lv), note="T2 sigma computed on the x0910 panel rows with the same 829-base definition; cut points of the 2026-08-01 refit")
sig_rowx = NS["sigma_rows"](tx["FN"], tx["IV"]); live_sigx = np.array([sig_rowx[tx["prow"][a]] for a in lv])
X5["live_window"].update(share_low_T2sigma=float(np.mean(t2bin(live_sigx) == 0)), share_mid=float(np.mean(t2bin(live_sigx) == 1)), share_high=float(np.mean(t2bin(live_sigx) == 2)), mean_T2sigma=float(np.nanmean(live_sigx)))
X5["live_window"]["reading"] = ("MECHANISM CANNOT OPERATE (state absent)" if X5["live_window"]["share_low_T2sigma"] < 0.2 else "state present")
OUT.update(X1=X1, X2=X2, X3=X3c, X3_per_arm=X3, X4=X4, X5=X5)
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD1 = open("/proc/loadavg").read().split()[:3]
RC = dict(self_sha256=sha(os.path.abspath(__file__)), label="ADDENDUM 1 (post-result readings requested by lead; not preregistered falsifiers)", result=OUT,
          inputs={p: sha(p) for p in (META, PANEL, X_META, X_PANEL, R + "/receipts/T1_states.npz", R + "/receipts/T1_d2.npz", R + "/receipts/T1_real_names.npz", T2D + "/receipts/RECEIPT_T2_kappa_main.json")},
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1, load_before=LOAD0, load_after=LOAD1,
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T1_addendum1.json", "w"), indent=1, default=lambda o: (o.tolist() if isinstance(o, np.ndarray) else float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else bool(o) if isinstance(o, np.bool_) else str(o)))
print("G30", json.dumps(G30)); print("DONE_t1_add_pod", RC["wall_s"])
