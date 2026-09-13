#!/usr/bin/env python3
"""t1_judge.py — pod2 (PREREG_T1 §5–§7 + AMENDMENTS 1–3). Every statistic and verdict of T1 from the gated inputs:
  arms/{C0,NW}_s{42,2027}.npz (GATE P/I), receipts/T1_states.npz (GATE X/S), receipts/T1_lags.npz (GATE LAG0), receipts/T1_d2.npz (GATE D2),
  receipts/T1_real_names.npz (GATE L), private/r15_arms_rec/F_s{42,2027}.npz (GATE R, checked here).
Estimator: UTC-day block bootstrap, B=2000, numpy default_rng([20260905, k]) per family, common random numbers within a family, stratified by period.
CI95 = percentile; verdict interval = point ± z_K·SE_boot, z_K = Φ⁻¹(1 − 0.025/K).
"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import norm
R = "/workspace/uplift_r2_2026-09-13/T1"
SH = {"PREREG_T1_edge_diagnosis_2026-09-13.md": "9548214267b5a44900ba90fee6b2fb2bbeb77964d562628b77678b16c56777f6", "PREREG_AMENDMENT_1_T1_2026-09-13.md": "a7628a7268cad50976470e5b6334c9086af9805bf786dac0ed51f496374da373",
      "PREREG_AMENDMENT_2_T1_2026-09-13.md": "12b262fd5b5ec47b7741c10b500baa9bc726cfc873ef7c5b07edf39b897e7207", "PREREG_AMENDMENT_3_T1_2026-09-13.md": "e6afc13879c6332520d7f3876f2adc212468e98594c312baf5fab035483685e8"}
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
for f, h in SH.items(): assert sha(R + "/" + f) == h, f
GATES = {}
for nm, key in (("RECEIPT_T1_drive_gates.json", None), ("RECEIPT_T1_states.json", None), ("RECEIPT_T1_lags.json", None), ("RECEIPT_T1_d2.json", None), ("RECEIPT_T1_realized.json", None)):
    GATES[nm] = json.load(open(R + "/receipts/" + nm))
assert GATES["RECEIPT_T1_drive_gates.json"]["gate"]["P"]["PASS"] and GATES["RECEIPT_T1_drive_gates.json"]["gate"]["I"]["PASS"], "GATE P/I"
assert GATES["RECEIPT_T1_states.json"]["gate_X"]["PASS_strict"] and GATES["RECEIPT_T1_states.json"]["gate_S"]["PASS"], "GATE X/S"
assert GATES["RECEIPT_T1_lags.json"]["gate_LAG0"]["PASS"], "GATE LAG0"
assert GATES["RECEIPT_T1_d2.json"]["gate_D2"]["PASS"], "GATE D2"
assert GATES["RECEIPT_T1_realized.json"]["gate_L"]["PASS"], "GATE L"
INPUT_SHA = {}
t0 = time.time()
B = 2000
def zK(K): return float(norm.ppf(1 - 0.025 / K))
Z = dict(H1=zK(10), H3=zK(8), H4=zK(3), H5=zK(4), MONTH=zK(10))
TS_WA0 = 1656547200; TS_WA1 = 1788120000; LIVE0 = 1787716800; LIVE1_REAL = 1789156800
S_P = 0.835; S_F = 0.733          # P2 slopes (price, funding) — sensitivity only
STALE15 = ["ANKRUSDT", "AXSUSDT", "ENJUSDT", "FLOWUSDT", "GMTUSDT", "IOSTUSDT", "KAVAUSDT", "MASKUSDT", "ONTUSDT", "RVNUSDT", "SKLUSDT", "STGUSDT", "XTZUSDT", "ZILUSDT", "ZRXUSDT"]
def ym(t): g = time.gmtime(int(t)); return g.tm_year, g.tm_mon
def utc(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
def L(x):
    if isinstance(x, np.ndarray): return x.tolist()
    return x
# ------------------------------------------------------------------ bootstrap engine
class Fam:
    def __init__(self, k, plist):
        self.k = k; rng = np.random.default_rng([20260905, k]); self.days = {p: np.asarray(d, np.int64) for p, d in plist}; self.order = [p for p, _ in plist]
        self.draws = {p: np.empty((B, len(self.days[p])), np.int32) for p in self.order}
        for b in range(B):
            for p in self.order:
                nd = len(self.days[p]); self.draws[p][b] = rng.integers(0, nd, nd)
    def mean(self, p, day, V):
        V = np.asarray(V, np.float64)
        if V.ndim == 1: V = V[:, None]
        assert np.all(np.isfinite(V)), ("non-finite stat", p)
        days = self.days[p]; di = np.searchsorted(days, day); assert np.all(days[np.minimum(di, len(days) - 1)] == day), ("day not in period", p)
        nd = len(days); s = V.shape[1]
        ds = np.zeros((nd, s)); np.add.at(ds, di, V); dc = np.bincount(di, minlength=nd).astype(np.float64)
        point = ds.sum(0) / dc.sum(); reps = np.empty((B, s)); dr = self.draws[p]
        for c0 in range(0, B, 100):
            d = dr[c0:c0 + 100]; reps[c0:c0 + 100] = ds[d].sum(1) / dc[d].sum(1)[:, None]
        return point, reps
def summ(point, reps, z=None):
    point = np.asarray(point, float); reps = np.asarray(reps, float)
    nbad = int(np.sum(~np.isfinite(reps)))
    se = np.nanstd(reps, 0, ddof=1); lo, hi = np.nanpercentile(reps, [2.5, 97.5], axis=0)
    o = dict(point=L(point), se=L(se), ci95_lo=L(lo), ci95_hi=L(hi), n_nonfinite_reps=nbad)
    if z is not None: o.update(vci_lo=L(point - z * se), vci_hi=L(point + z * se), z=z)
    return o
# ------------------------------------------------------------------ load states / lags / D2 / REAL
ST = np.load(R + "/receipts/T1_states.npz", allow_pickle=True); SCOL = [str(c) for c in ST["cols"]]; SV = ST["S"]; sts = SV[:, 0].astype(np.int64); smap = {int(t): i for i, t in enumerate(sts)}
PRIM = ["DISP24", "BREADTH72", "BTC72", "SIGF", "MUF", "PUMP72"]; SECD = ["DISP72", "BREADTH24", "BTC24", "PUMPSPR72"]
def state_on(tsarr, name):
    c = SCOL.index(name); out = np.full(len(tsarr), np.nan)
    for q, t in enumerate(tsarr):
        i = smap.get(int(t))
        if i is not None: out[q] = SV[i, c]
    return out
DZ = np.load(R + "/receipts/T1_d2.npz", allow_pickle=True); DCOL = [str(c) for c in DZ["cols"]]; DD = DZ["D"]; dts = DD[:, 0].astype(np.int64); dc_ = {c: i for i, c in enumerate(DCOL)}
def dcol(c): return DD[:, dc_[c]]
RZ = np.load(R + "/receipts/T1_real_names.npz", allow_pickle=True); RN = RZ["names"]; RC_ = [str(c) for c in RZ["cols"]]; RX = RZ["rows"]; rci = {c: i for i, c in enumerate(RC_)}
RA = RZ["anchors"]; RAC = [str(c) for c in RZ["anchor_cols"]]; rai = {c: i for i, c in enumerate(RAC)}
ra_mask = (RA[:, rai["A"]] >= LIVE0) & (RA[:, rai["A"]] <= LIVE1_REAL); RAL = RA[ra_mask]; rts = RAL[:, rai["A"]].astype(np.int64); rgross = RAL[:, rai["gross"]]
ridx = {int(t): q for q, t in enumerate(rts)}
nR = len(rts); REALV = {k: np.zeros(nR) for k in ("price", "funding", "fee", "timing", "price_L", "price_S", "fund_L", "fund_S", "cost_L", "cost_S", "unsided_price", "unsided_fund", "unsided_cost", "gross_S_abs", "gross_L_abs", "cohC_price", "cohC_fund", "st15_price", "st15_fund", "st15_gross")}
rrow_A = RX[:, rci["A"]].astype(np.int64)
for q_row in range(len(RX)):
    q = ridx.get(int(rrow_A[q_row]))
    if q is None: continue
    x = RX[q_row]; s = x[rci["side"]]; pr = x[rci["price_usd"]]; fu = x[rci["funding_usd"]]; co = -(x[rci["fee_usd"]] + x[rci["timing_usd"]])
    REALV["price"][q] += pr; REALV["funding"][q] += fu; REALV["fee"][q] += x[rci["fee_usd"]]; REALV["timing"][q] += x[rci["timing_usd"]]
    if s > 0: REALV["price_L"][q] += pr; REALV["fund_L"][q] += fu; REALV["cost_L"][q] += co
    elif s < 0: REALV["price_S"][q] += pr; REALV["fund_S"][q] += fu; REALV["cost_S"][q] += co
    else: REALV["unsided_price"][q] += pr; REALV["unsided_fund"][q] += fu; REALV["unsided_cost"][q] += co
    held = x[rci["held"]] > 0; notl = x[rci["notional_at_mid"]]
    if held and np.isfinite(notl):
        if s < 0: REALV["gross_S_abs"][q] += abs(notl)
        elif s > 0: REALV["gross_L_abs"][q] += abs(notl)
    rn = x[rci["rn8_producer"]]
    if held and s < 0 and np.isfinite(rn) and rn <= -0.0010: REALV["cohC_price"][q] += pr; REALV["cohC_fund"][q] += fu
    if str(RN[q_row]) in STALE15:
        REALV["st15_price"][q] += pr; REALV["st15_fund"][q] += fu
        if held and np.isfinite(notl): REALV["st15_gross"][q] += abs(notl)
# identity with the anchor totals (GATE L receipts)
assert np.allclose(REALV["price"], RAL[:, rai["price"]], atol=1e-6) and np.allclose(REALV["funding"], RAL[:, rai["fund"]], atol=1e-6) and np.allclose(REALV["fee"], RAL[:, rai["fee"]], atol=1e-6), "REAL name->anchor identity"
bp = 1e4 / rgross
REAL = dict(price=REALV["price"] * bp, carry=-REALV["funding"] * bp, cost=-(REALV["fee"] + REALV["timing"]) * bp)
REAL["g"] = REAL["price"] - REAL["carry"] - REAL["cost"]; REAL["g_r6net"] = (REALV["price"] + REALV["funding"] + REALV["fee"]) * bp
REAL["price_s"] = REAL["price"] / S_P; REAL["carry_s"] = REAL["carry"] / S_F; REAL["g_s"] = REAL["price_s"] - REAL["carry_s"] - REAL["cost"]
for k in ("price_L", "price_S"): REAL[k] = REALV[k] * bp
REAL["carry_L"] = -REALV["fund_L"] * bp; REAL["carry_S"] = -REALV["fund_S"] * bp; REAL["cost_L"] = REALV["cost_L"] * bp; REAL["cost_S"] = REALV["cost_S"] * bp
REAL["unsided_g"] = (REALV["unsided_price"] + REALV["unsided_fund"] - REALV["unsided_cost"]) * bp
REAL["gross_S"] = REALV["gross_S_abs"] / rgross; REAL["gross_L"] = REALV["gross_L_abs"] / rgross
REAL["coh_price"] = REALV["cohC_price"] * bp; REAL["coh_carry"] = -REALV["cohC_fund"] * bp
REAL["st15_price"] = REALV["st15_price"] * bp; REAL["st15_carry"] = -REALV["st15_fund"] * bp; REAL["st15_gross"] = REALV["st15_gross"] / rgross
rday = rts // 86400
D2 = dict(price=dcol("price"), carry=dcol("carry")); D2["g_pre"] = D2["price"] - D2["carry"]
for k in ("price_L", "price_S", "carry_L", "carry_S", "gross_L", "gross_S", "coh_price", "coh_carry", "st15_gross", "st15_price", "st15_carry", "non8h_gross", "non8h_price", "non8h_carry", "fundsig_st15_absz_share", "fundsig_st15_lr0", "fundsig_lr0", "unknown_ret_share", "producer_is_combo"): D2[k] = dcol(k)
dday = dts // 86400
LG = np.load(R + "/receipts/T1_lags.npz", allow_pickle=True); lts = LG["ts"].astype(np.int64)
MX = np.load("/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz", allow_pickle=True); INPUT_SHA["meta_x0910"] = sha("/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz")
row_avail = np.isfinite(MX["y4"]).sum(1) >= 50
assert np.array_equal(MX["E_ts"].astype(np.int64), lts)
complete = np.zeros(len(lts), bool)
for i in range(len(lts) - 23): complete[i] = LG["have"][i] and bool(row_avail[i:i + 24].all())
# ------------------------------------------------------------------ replay axis periods
A0 = np.load(R + "/arms/C0_s42.npz", allow_pickle=True); rec0 = A0["d30_n2_c42_rec"]; ts = rec0[:, 0].astype(np.int64); day = ts // 86400
WA = (ts >= TS_WA0) & (ts <= TS_WA1); YM = np.array([ym(t) for t in ts])
def pmask(name):
    if name == "W_ALPHA": return WA
    if name == "PRE_LIVE": return WA & (ts < LIVE0)
    if name == "LIVE_REPLAY": return WA & (ts >= LIVE0)
    if name == "H1_2026": return WA & (YM[:, 0] == 2026) & (YM[:, 1] <= 6)
    if name == "STATE_FIT": return WA & ((YM[:, 0] == 2024) | (YM[:, 0] == 2025))
    if name == "Y2022H2": return WA & (YM[:, 0] == 2022)
    if name.startswith("Y"): return WA & (YM[:, 0] == int(name[1:]))
    if name.startswith("M"): y, m = int(name[1:5]), int(name[6:8]); return WA & (YM[:, 0] == y) & (YM[:, 1] == m)
    raise KeyError(name)
MONTHS25 = ["M2025_%02d" % m for m in range(1, 13)]; MONTHS26 = ["M2026_%02d" % m for m in range(1, 9)]
def rdays(name): return np.unique(day[pmask(name)])
def plist(names):
    out = []
    for n in names:
        if n == "LIVE_D2": out.append((n, np.unique(dday)))
        elif n == "LIVE_REAL": out.append((n, np.unique(rday)))
        elif n == "LIVE_REAL_ST": out.append((n, np.unique(rday[np.isfinite(state_on(rts, "SIGF"))])))
        elif n in ("LIVE_LAG",): out.append((n, np.unique((lts[(lts >= LIVE0) & complete & (lts <= dts.max())]) // 86400)))
        elif n.startswith("LAG_"): nm = n[4:]; out.append((n, np.unique((lts[complete & lag_period(nm)]) // 86400)))
        elif n == "ANALOG": out.append((n, ANALOG_DAYS))
        else: out.append((n, rdays(n)))
    return out
def lag_period(name):
    YL = np.array([ym(t) for t in lts]); wa = (lts >= TS_WA0) & (lts <= TS_WA1)
    if name == "H1_2026": return wa & (YL[:, 0] == 2026) & (YL[:, 1] <= 6)
    if name == "M2026_08": return wa & (YL[:, 0] == 2026) & (YL[:, 1] == 8)
    raise KeyError(name)
# quintile edges on PRE_LIVE (replay rows) for each state
PRE = pmask("PRE_LIVE"); STATE_REC = {s: state_on(ts, s) for s in PRIM + SECD}
EDGES = {s: np.nanpercentile(STATE_REC[s][PRE], [20, 40, 60, 80]) for s in PRIM}
def qbin(x, s):
    b = np.searchsorted(EDGES[s], x, side="right").astype(float); b[~np.isfinite(x)] = np.nan; return b
STATE_D2 = {s: state_on(dts, s) for s in PRIM + SECD}; STATE_REAL = {s: state_on(rts, s) for s in PRIM + SECD}
# ------------------------------------------------------------------ families
FAM = {}
FAM[1] = Fam(1, plist(["W_ALPHA", "Y2022H2", "Y2023", "Y2024", "Y2025", "H1_2026"] + MONTHS25 + MONTHS26 + ["LIVE_REPLAY", "LIVE_D2", "LIVE_REAL", "PRE_LIVE"]))
FAM[2] = Fam(2, plist(["H1_2026", "M2026_07", "M2026_08", "LIVE_REPLAY", "Y2023", "LIVE_D2", "LIVE_REAL", "LIVE_REAL_ST"]))
FAM[3] = Fam(3, plist(["STATE_FIT", "H1_2026", "M2026_08", "LIVE_D2"]))
FAM[4] = Fam(4, plist(["LAG_H1_2026", "LAG_M2026_08", "LIVE_LAG"]))
FAM[5] = Fam(5, plist(["H1_2026", "LIVE_D2", "LIVE_REAL", "W_ALPHA", "Y2022H2", "Y2023", "Y2024", "Y2025", "M2026_07", "M2026_08", "LIVE_REPLAY"]))
FAM[6] = Fam(6, plist(["Y2023", "LIVE_D2", "LIVE_REAL"]))
FAM[7] = Fam(7, plist(["H1_2026"] + MONTHS26 + ["LIVE_D2", "LIVE_REAL"]))
print("families built", round(time.time() - t0, 1), "s", flush=True)
OUT = dict(z=Z, windows={}, arms={})
for n in ["W_ALPHA", "PRE_LIVE", "STATE_FIT", "Y2022H2", "Y2023", "Y2024", "Y2025", "H1_2026"] + MONTHS25 + MONTHS26 + ["LIVE_REPLAY"]:
    msk = pmask(n); OUT["windows"][n] = dict(n=int(msk.sum()), first=utc(ts[msk][0]), last=utc(ts[msk][-1]), n_days=int(len(np.unique(day[msk]))))
OUT["windows"]["LIVE_D2"] = dict(n=int(len(dts)), first=utc(dts[0]), last=utc(dts[-1]), n_days=int(len(np.unique(dday))), n_combo_producer=int(D2["producer_is_combo"].sum()), max_unknown_ret_share=float(D2["unknown_ret_share"].max()))
OUT["windows"]["LIVE_REAL"] = dict(n=int(nR), first=utc(rts[0]), last=utc(rts[-1]), n_days=int(len(np.unique(rday))), n_with_state=int(np.isfinite(STATE_REAL["SIGF"]).sum()))
OUT["windows"]["LIVE_LAG"] = dict(n=int(((lts >= LIVE0) & complete & (lts <= dts.max())).sum()), first=utc(lts[(lts >= LIVE0) & complete][0]), last=utc(lts[(lts >= LIVE0) & complete & (lts <= dts.max())][-1]))
OUT["quintile_edges_PRE_LIVE"] = {s: L(EDGES[s]) for s in PRIM}
# ------------------------------------------------------------------ per-arm computation
ARMS = ["C0_s42", "C0_s2027", "NW_s42", "NW_s2027"]
for arm in ARMS:
    ta = time.time()
    Z_ = np.load(R + "/arms/%s.npz" % arm, allow_pickle=True); INPUT_SHA["arm_" + arm] = sha(R + "/arms/%s.npz" % arm)
    rec = Z_["d30_n2_c42_rec"]; assert np.array_equal(rec[:, 0].astype(np.int64), ts)
    gt = rec[:, 5]; price = rec[:, 19] / gt; carry = rec[:, 20] / gt; cost = rec[:, 21] / gt; g = rec[:, 18] / gt
    AGG = Z_["d30_n2_c42_T1AGG"] / gt[:, None, None]   # rows pnlL,pnlS,carL,carS,costL,costS ; cols king,rev24,fund,f10
    SMR = Z_["d30_n2_c42_T1SMR"]; smr = SMR.astype(np.float64).sum(1); YV = Z_["d30_n2_c42_T1YV"].astype(np.float64); C4 = Z_["d30_n2_c42_T1C4"].astype(np.float64); RN8 = Z_["d30_n2_c42_T1RN"].astype(np.float64)
    gS = np.where(smr < 0, -smr, 0.0).sum(1) / gt; gL = np.where(smr > 0, smr, 0.0).sum(1) / gt
    coh = (smr < 0) & (np.nan_to_num(RN8, nan=1.0) <= -0.0010)
    pC = (np.where(coh, smr * YV, 0.0)).sum(1) * 1e4 / gt; cC = (np.where(coh, smr * C4, 0.0)).sum(1) * 1e4 / gt
    sym = [str(s) for s in Z_["symbols"]]; st15 = np.isin(np.array(sym), STALE15)
    fund_abs = np.abs(SMR[:, 2, :].astype(np.float64)); f15_share = np.where(fund_abs.sum(1) > 0, fund_abs[:, st15].sum(1) / np.maximum(fund_abs.sum(1), 1e-18), 0.0)
    f15_price = (SMR[:, 2, :][:, st15].astype(np.float64) * YV[:, st15]).sum(1) * 1e4 / gt; f15_carry = (SMR[:, 2, :][:, st15].astype(np.float64) * C4[:, st15]).sum(1) * 1e4 / gt
    b15_share = np.abs(smr[:, st15]).sum(1) / np.maximum(np.abs(smr).sum(1), 1e-18)
    del SMR
    A = dict()
    # ---------------- (k=1) levels
    LEV = {}
    Vr = np.column_stack([price, carry, cost, g, AGG[:, 0:2, :].sum(1), AGG[:, 2:4, :].sum(1), AGG[:, 0, :].sum(1), AGG[:, 1, :].sum(1), AGG[:, 2, :].sum(1), AGG[:, 3, :].sum(1), gS, gL])
    vnames = ["price", "carry", "cost", "g", "price_king", "price_rev24", "price_fund", "price_f10", "carry_king", "carry_rev24", "carry_fund", "carry_f10", "price_L", "price_S", "carry_L", "carry_S", "gross_S", "gross_L"]
    for n in ["W_ALPHA", "Y2022H2", "Y2023", "Y2024", "Y2025", "H1_2026"] + MONTHS25 + MONTHS26 + ["LIVE_REPLAY", "PRE_LIVE"]:
        msk = pmask(n); p, r = FAM[1].mean(n, day[msk], Vr[msk]); LEV[n] = {vn: summ(p[q], r[:, q]) for q, vn in enumerate(vnames)}
    A["levels"] = LEV
    # ---------------- (k=2) ranked cells vs H1_2026
    ROWN = ["price_L", "price_S", "carry_L", "carry_S", "cost_L", "cost_S"]; SGN = np.array([1, 1, -1, -1, -1, -1]); LEGN = ["king", "rev24", "fund", "f10"]
    cellV = AGG.reshape(len(ts), 24)   # row-major: row r, leg l -> r*4+l
    cellN = ["%s|%s" % (ROWN[r], LEGN[l]) for r in range(6) for l in range(4)]; cellS = np.repeat(SGN, 4)
    mH = pmask("H1_2026"); pH, rH = FAM[2].mean("H1_2026", day[mH], cellV[mH])
    CELLS = {}
    for T in ["M2026_07", "M2026_08", "LIVE_REPLAY", "Y2023"]:
        mT = pmask(T); pT, rT = FAM[2].mean(T, day[mT], cellV[mT])
        contrib = cellS * (pT - pH); crep = cellS * (rT - rH)
        dg = g[mT].mean() - g[mH].mean(); assert abs(contrib.sum() - dg) < 1e-9, ("cell identity", arm, T, contrib.sum(), dg)
        order = np.argsort(-np.abs(contrib))
        CELLS[T] = dict(dg=float(dg), sum_cells=float(contrib.sum()), cells=[dict(cell=cellN[q], contrib=float(contrib[q]), ci95=[float(np.percentile(crep[:, q], 2.5)), float(np.percentile(crep[:, q], 97.5))], mean_T=float(pT[q]), mean_H1=float(pH[q])) for q in order])
        # state x cell
        STC = {}
        for s in PRIM:
            bT = qbin(STATE_REC[s][mT], s); bH = qbin(STATE_REC[s][mH], s)
            UT = np.column_stack([(bT == b)[:, None] * cellV[mT] for b in range(5)]); UT = np.nan_to_num(UT)
            UH = np.column_stack([(bH == b)[:, None] * cellV[mH] for b in range(5)]); UH = np.nan_to_num(UH)
            FT = np.column_stack([(bT == b).astype(float) for b in range(5)]); FH = np.column_stack([(bH == b).astype(float) for b in range(5)])
            pUT, rUT = FAM[2].mean(T, day[mT], UT); pUH, rUH = FAM[2].mean("H1_2026", day[mH], UH)
            pFT, _ = FAM[2].mean(T, day[mT], FT); pFH, _ = FAM[2].mean("H1_2026", day[mH], FH)
            sg = np.tile(cellS, 5); cb = sg * (pUT - pUH); cbr = sg * (rUT - rUH)
            names = ["Q%d|%s" % (b + 1, cellN[q]) for b in range(5) for q in range(24)]
            order = np.argsort(-np.abs(cb))[:30]
            # mix / within on g (per bin): m = mean g-cell sum within bin
            gT = np.array([cb[b * 24:(b + 1) * 24].sum() for b in range(5)])
            mTg = np.array([(sg[b * 24:(b + 1) * 24] * pUT[b * 24:(b + 1) * 24]).sum() / pFT[b] if pFT[b] > 0 else 0.0 for b in range(5)])
            mHg = np.array([(sg[b * 24:(b + 1) * 24] * pUH[b * 24:(b + 1) * 24]).sum() / pFH[b] if pFH[b] > 0 else 0.0 for b in range(5)])
            mix = float(((pFT - pFH) * mHg).sum()); within = float((pFT * (mTg - mHg)).sum())
            unst = float(1 - pFT.sum()); unsH = float(1 - pFH.sum())
            STC[s] = dict(sum_contrib=float(cb.sum()), mix=mix, within=within, f_T=L(pFT), f_H1=L(pFH), share_T_state_nan=unst, share_H1_state_nan=unsH,
                          top30=[dict(cell=names[q], contrib=float(cb[q]), ci95=[float(np.percentile(cbr[:, q], 2.5)), float(np.percentile(cbr[:, q], 97.5))]) for q in order])
        CELLS[T]["state_cells"] = STC
    # D2 and REAL cells vs H1 (component x side)
    Hs = np.column_stack([AGG[:, 0, :].sum(1), AGG[:, 1, :].sum(1), AGG[:, 2, :].sum(1), AGG[:, 3, :].sum(1), AGG[:, 4, :].sum(1), AGG[:, 5, :].sum(1)])
    pHs, rHs = FAM[2].mean("H1_2026", day[mH], Hs[mH])
    VD = np.column_stack([D2["price_L"], D2["price_S"], D2["carry_L"], D2["carry_S"]]); pD, rD = FAM[2].mean("LIVE_D2", dday, VD)
    sg4 = np.array([1, 1, -1, -1]); cD = sg4 * (pD - pHs[:4]); cDr = sg4 * (rD - rHs[:, :4])
    CELLS["LIVE_D2"] = dict(note="D2 has no cost cells; sum = delta g_pre", dg_pre=float((D2["price"] - D2["carry"]).mean() - (price[mH] - carry[mH]).mean()), sum_cells=float(cD.sum()),
                            cells=[dict(cell=["price_L", "price_S", "carry_L", "carry_S"][q], contrib=float(cD[q]), ci95=[float(np.percentile(cDr[:, q], 2.5)), float(np.percentile(cDr[:, q], 97.5))], mean_T=float(pD[q]), mean_H1=float(pHs[q])) for q in np.argsort(-np.abs(cD))])
    for tag, scP, scF in (("LIVE_REAL", 1.0, 1.0), ("LIVE_REAL_scaled", S_P, S_F)):
        VR = np.column_stack([REAL["price_L"] / scP, REAL["price_S"] / scP, REAL["carry_L"] / scF, REAL["carry_S"] / scF, REAL["cost_L"], REAL["cost_S"], REAL["unsided_g"]])
        pR, rR = FAM[2].mean("LIVE_REAL", rday, VR)
        sg6 = np.array([1, 1, -1, -1, -1, -1]); cR = sg6 * (pR[:6] - pHs); cRr = sg6 * (rR[:, :6] - rHs)
        gR = (REAL["price"] / scP - REAL["carry"] / scF - REAL["cost"]).mean()
        CELLS[tag] = dict(dg=float(gR - g[mH].mean()), sum_cells=float(cR.sum()), unsided_g_mean=float(pR[6]),
                          cells=[dict(cell=["price_L", "price_S", "carry_L", "carry_S", "cost_L", "cost_S"][q], contrib=float(cR[q]), ci95=[float(np.percentile(cRr[:, q], 2.5)), float(np.percentile(cRr[:, q], 97.5))], mean_T=float(pR[q]), mean_H1=float(pHs[q])) for q in np.argsort(-np.abs(cR))])
    # state x cell for D2 and REAL (component x side)
    for tag, TT, V_, dd, SD in (("LIVE_D2", "LIVE_D2", VD, dday, STATE_D2), ("LIVE_REAL", "LIVE_REAL_ST", np.column_stack([REAL["price_L"], REAL["price_S"], REAL["carry_L"], REAL["carry_S"], REAL["cost_L"], REAL["cost_S"]]), rday, STATE_REAL)):
        ncell = V_.shape[1]; sgn = np.array([1, 1, -1, -1, -1, -1])[:ncell]; keep = np.ones(len(dd), bool) if TT == "LIVE_D2" else np.isfinite(SD["SIGF"])
        STC = {}
        for s in PRIM:
            bT = qbin(SD[s][keep], s); bH = qbin(STATE_REC[s][mH], s)
            UT = np.nan_to_num(np.column_stack([(bT == b)[:, None] * V_[keep] for b in range(5)])); UH = np.nan_to_num(np.column_stack([(bH == b)[:, None] * Hs[mH][:, :ncell] for b in range(5)]))
            FT = np.column_stack([(bT == b).astype(float) for b in range(5)]); FH = np.column_stack([(bH == b).astype(float) for b in range(5)])
            pUT, rUT = FAM[2].mean(TT, dd[keep], UT); pUH, rUH = FAM[2].mean("H1_2026", day[mH], UH); pFT, _ = FAM[2].mean(TT, dd[keep], FT); pFH, _ = FAM[2].mean("H1_2026", day[mH], FH)
            sg = np.tile(sgn, 5); cb = sg * (pUT - pUH); cbr = sg * (rUT - rUH)
            names = ["Q%d|%s" % (b + 1, ["price_L", "price_S", "carry_L", "carry_S", "cost_L", "cost_S"][q]) for b in range(5) for q in range(ncell)]
            order = np.argsort(-np.abs(cb))[:30]
            STC[s] = dict(sum_contrib=float(cb.sum()), f_T=L(pFT), f_H1=L(pFH), top30=[dict(cell=names[q], contrib=float(cb[q]), ci95=[float(np.percentile(cbr[:, q], 2.5)), float(np.percentile(cbr[:, q], 97.5))]) for q in order])
        CELLS[tag]["state_cells"] = STC
    A["cells"] = CELLS
    # ---------------- (k=7) month verdicts — deliverable (2)
    pHm, rHm = FAM[7].mean("H1_2026", day[mH], np.column_stack([price[mH], carry[mH]])); P_ref, C_ref = float(pHm[0]), float(pHm[1])
    MON = {}
    for M in MONTHS26:
        mm = pmask(M); pm, rm = FAM[7].mean(M, day[mm], np.column_stack([price[mm], carry[mm]]))
        sp = summ(pm[0], rm[:, 0], Z["MONTH"]); sc = summ(pm[1], rm[:, 1])
        MON[M] = dict(price=sp, carry=sc, price_gone=bool(pm[0] <= 0.25 * P_ref and sp["vci_hi"] < P_ref), carry_persisted=bool(pm[1] >= 0.75 * C_ref and sc["ci95_lo"] > 0))
    pm, rm = FAM[7].mean("LIVE_D2", dday, np.column_stack([D2["price"], D2["carry"]])); sp = summ(pm[0], rm[:, 0], Z["MONTH"])
    MON["LIVE_D2"] = dict(price=sp, carry=summ(pm[1], rm[:, 1]), price_gone=bool(pm[0] <= 0.25 * P_ref and sp["vci_hi"] < P_ref))
    pm, rm = FAM[7].mean("LIVE_REAL", rday, np.column_stack([REAL["price"], REAL["carry"]])); sp = summ(pm[0], rm[:, 0], Z["MONTH"])
    MON["LIVE_REAL"] = dict(price=sp, carry=summ(pm[1], rm[:, 1]), price_gone_raw=bool(pm[0] <= 0.25 * P_ref and sp["vci_hi"] < P_ref), price_gone_vs_scaled_ref=bool(pm[0] <= 0.25 * S_P * P_ref and sp["vci_hi"] < S_P * P_ref))
    MON["LIVE_REAL"]["price_gone"] = bool(MON["LIVE_REAL"]["price_gone_raw"] and MON["LIVE_REAL"]["price_gone_vs_scaled_ref"])
    vanish = None
    for q, M in enumerate(MONTHS26):
        if MON[M]["price_gone"] and MON[M]["carry_persisted"] and all(MON[M2]["price_gone"] for M2 in MONTHS26[q:]) and MON["LIVE_D2"]["price_gone"] and MON["LIVE_REAL"]["price_gone"]:
            vanish = M; break
    if vanish is None and MON["LIVE_D2"]["price_gone"] and MON["LIVE_REAL"]["price_gone"]: vanish = "LIVE window only"
    A["month"] = dict(P_ref=P_ref, C_ref=C_ref, months=MON, vanish=(vanish or "no such month"))
    # ---------------- (k=3) H1 and H1-fuel
    mS = pmask("STATE_FIT"); mA = pmask("M2026_08")
    H1R = {}
    pPH, rPH = FAM[3].mean("H1_2026", day[mH], price[mH]); pPA, rPA = FAM[3].mean("M2026_08", day[mA], price[mA]); pPL, rPL = FAM[3].mean("LIVE_D2", dday, D2["price"])
    D_TA = (pPA - pPH)[0]; D_TAr = (rPA - rPH)[:, 0]; D_TL = (pPL - pPH)[0]; D_TLr = (rPL - rPH)[:, 0]
    H1R["D_TA"] = summ(D_TA, D_TAr, Z["H1"]); H1R["D_TL"] = summ(D_TL, D_TLr, Z["H1"])
    for s in ["DISP24", "BREADTH72", "SIGF", "MUF"]:
        bF = qbin(STATE_REC[s][mS], s); VF = np.column_stack([np.nan_to_num((bF == b) * price[mS]) for b in range(5)] + [(bF == b).astype(float) for b in range(5)])
        pF, rF = FAM[3].mean("STATE_FIT", day[mS], VF); mu = pF[:5] / pF[5:]; mur = rF[:, :5] / rF[:, 5:]
        def fshares(bins, fam, per, dd_):
            V = np.column_stack([(bins == b).astype(float) for b in range(5)] + [np.isfinite(bins).astype(float)])
            p, r = fam.mean(per, dd_, V); return p[:5] / p[5], r[:, :5] / r[:, 5:6]
        fH, fHr = fshares(qbin(STATE_REC[s][mH], s), FAM[3], "H1_2026", day[mH])
        fA, fAr = fshares(qbin(STATE_REC[s][mA], s), FAM[3], "M2026_08", day[mA])
        fL, fLr = fshares(qbin(STATE_D2[s], s), FAM[3], "LIVE_D2", dday)
        for T, fT, fTr, D, Dr in (("T_A", fA, fAr, D_TA, D_TAr), ("T_L", fL, fLr, D_TL, D_TLr)):
            mix = float(((fT - fH) * mu).sum()); mixr = ((fTr - fHr) * mur).sum(1); sm_ = summ(mix, mixr, Z["H1"]); sd_ = summ(D, Dr, Z["H1"])
            ratio = mix / D if D != 0 else np.nan
            if sd_["vci_hi"] < 0 and sm_["vci_hi"] < 0 and ratio >= 0.5: v = "EXPLAINS"
            elif sd_["vci_hi"] < 0 and (sm_["vci_lo"] <= 0 <= sm_["vci_hi"] or ratio < 0.25): v = "DOES-NOT-EXPLAIN"
            else: v = "UNDECIDED"
            H1R["%s|%s" % (s, T)] = dict(MIX=sm_, mix_over_D=float(ratio), mu_STATE_FIT=L(mu), f_H1=L(fH), f_T=L(fT), cell_verdict=v)
    def agg_h1(vars_):
        cells = [H1R["%s|%s" % (s, T)]["cell_verdict"] for s in vars_ for T in ("T_A", "T_L")]
        if "EXPLAINS" in cells: return "SURVIVES"
        if all(c == "DOES-NOT-EXPLAIN" for c in cells): return "FALSIFIED"
        return "NOT DECIDABLE"
    H1R["H1_verdict"] = agg_h1(["DISP24", "BREADTH72"]); H1R["H1fuel_verdict"] = agg_h1(["SIGF", "MUF"])
    A["H1"] = H1R
    # ---------------- (k=5) H4
    H4 = {}
    pr_, rr_ = FAM[5].mean("H1_2026", day[mH], np.column_stack([pC[mH], cC[mH]])); rhoH = pr_[0] / pr_[1]; rhoHr = rr_[:, 0] / rr_[:, 1]
    H4["rho_H1"] = summ(rhoH, rhoHr, Z["H4"])
    pr_, rr_ = FAM[5].mean("LIVE_D2", dday, np.column_stack([D2["coh_price"], D2["coh_carry"]])); rhoD = pr_[0] / pr_[1]; rhoDr = rr_[:, 0] / rr_[:, 1]
    H4["rho_LIVE_D2"] = summ(rhoD, rhoDr, Z["H4"]); H4["LIVE_D2_coh_price_carry"] = L(pr_)
    pr_, rr_ = FAM[5].mean("LIVE_REAL", rday, np.column_stack([REAL["coh_price"], REAL["coh_carry"]])); rhoR = pr_[0] / pr_[1]; rhoRr = rr_[:, 0] / rr_[:, 1]
    H4["rho_LIVE_REAL"] = summ(rhoR, rhoRr, Z["H4"]); H4["rho_LIVE_REAL_scaled"] = summ(rhoR * S_F / S_P, rhoRr * S_F / S_P, Z["H4"]); H4["LIVE_REAL_coh_price_carry"] = L(pr_)
    half = 0.5 * rhoH
    if H4["rho_H1"]["vci_lo"] > 0 and H4["rho_LIVE_D2"]["vci_hi"] < half and H4["rho_LIVE_REAL"]["vci_hi"] < half and H4["rho_LIVE_REAL_scaled"]["vci_hi"] < half: v = "SURVIVES"
    elif H4["rho_LIVE_D2"]["vci_lo"] >= half and H4["rho_LIVE_REAL"]["vci_lo"] >= half and H4["rho_LIVE_REAL_scaled"]["vci_lo"] >= half: v = "FALSIFIED"
    else: v = "NOT DECIDABLE"
    H4["verdict"] = v
    per = {}
    for n in ["W_ALPHA", "Y2022H2", "Y2023", "Y2024", "Y2025", "H1_2026", "M2026_07", "M2026_08", "LIVE_REPLAY"]:
        msk = pmask(n); p_, r_ = FAM[5].mean(n, day[msk], np.column_stack([pC[msk], cC[msk]])); per[n] = dict(rho=summ(p_[0] / p_[1], r_[:, 0] / r_[:, 1]), coh_price=float(p_[0]), coh_carry=float(p_[1]))
    if arm.startswith("C0"):
        F = np.load(R + "/private/r15_arms_rec/F_%s.npz" % arm.split("_")[1], allow_pickle=True); INPUT_SHA["r15_F_" + arm] = sha(R + "/private/r15_arms_rec/F_%s.npz" % arm.split("_")[1])
        fr = F["rec"]; assert np.array_equal(fr[:, 0].astype(np.int64), ts)
        dP = fr[:, 19] / fr[:, 5] - price; dC = fr[:, 20] / fr[:, 5] - carry; dK = fr[:, 21] / fr[:, 5] - cost
        H4["gate_R_W_ALPHA"] = dict(dpnl=float(dP[WA].mean()), dcarry=float(dC[WA].mean()), dcost=float(dK[WA].mean()), dg=float((dP - dC - dK)[WA].mean()))
        for n in per:
            msk = pmask(n); p_, r_ = FAM[5].mean(n, day[msk], np.column_stack([dP[msk], dC[msk]])); per[n]["kappa"] = summ(p_[0] / p_[1], r_[:, 0] / r_[:, 1]); per[n]["dpnl"] = float(p_[0]); per[n]["dcarry"] = float(p_[1])
    H4["by_period"] = per
    A["H4"] = H4
    # ---------------- (k=6) H5
    H5 = {}
    m23 = pmask("Y2023")
    sig23 = STATE_REC["SIGF"][m23]; sigL = STATE_D2["SIGF"]
    H5["c1_share_SIGF_lt_4p75"] = dict(Y2023=float(np.mean(sig23[np.isfinite(sig23)] < 4.75)), LIVE_D2=float(np.mean(sigL[np.isfinite(sigL)] < 4.75)))
    H5["c1_diff"] = H5["c1_share_SIGF_lt_4p75"]["LIVE_D2"] - H5["c1_share_SIGF_lt_4p75"]["Y2023"]
    p23, r23 = FAM[6].mean("Y2023", day[m23], np.column_stack([price[m23], carry[m23], AGG[m23, 1, :].sum(1), gS[m23]]))
    pi23 = p23[0] / p23[1]; pi23r = r23[:, 0] / r23[:, 1]; ss23 = p23[2] / p23[3]; ss23r = r23[:, 2] / r23[:, 3]
    pD_, rD_ = FAM[6].mean("LIVE_D2", dday, np.column_stack([D2["price"], D2["carry"], D2["price_S"], D2["gross_S"]]))
    pR_, rR_ = FAM[6].mean("LIVE_REAL", rday, np.column_stack([REAL["price"], REAL["carry"], REAL["price_S"], REAL["gross_S"]]))
    H5["pi_2023"] = summ(pi23, pi23r); H5["sigma_short_2023"] = summ(ss23, ss23r)
    H5["pi_LIVE_D2"] = summ(pD_[0] / pD_[1], rD_[:, 0] / rD_[:, 1]); H5["sigma_short_LIVE_D2"] = summ(pD_[2] / pD_[3], rD_[:, 2] / rD_[:, 3])
    H5["pi_LIVE_REAL"] = summ(pR_[0] / pR_[1], rR_[:, 0] / rR_[:, 1]); H5["sigma_short_LIVE_REAL"] = summ(pR_[2] / pR_[3], rR_[:, 2] / rR_[:, 3])
    dpD = summ(pD_[0] / pD_[1] - pi23, rD_[:, 0] / rD_[:, 1] - pi23r, Z["H5"]); dsD = summ(pD_[2] / pD_[3] - ss23, rD_[:, 2] / rD_[:, 3] - ss23r, Z["H5"])
    dpR = summ(pR_[0] / pR_[1] - pi23, rR_[:, 0] / rR_[:, 1] - pi23r, Z["H5"]); dsR = summ(pR_[2] / pR_[3] - ss23, rR_[:, 2] / rR_[:, 3] - ss23r, Z["H5"])
    kP = S_F / S_P
    dpRs = summ(pR_[0] / pR_[1] * kP - pi23, rR_[:, 0] / rR_[:, 1] * kP - pi23r, Z["H5"]); dsRs = summ(pR_[2] / pR_[3] / S_P - ss23, rR_[:, 2] / rR_[:, 3] / S_P - ss23r, Z["H5"])
    H5.update(dpi_D2=dpD, dsig_D2=dsD, dpi_REAL=dpR, dsig_REAL=dsR, dpi_REAL_scaled=dpRs, dsig_REAL_scaled=dsRs)
    excl = lambda s_: s_["vci_lo"] > 0 or s_["vci_hi"] < 0
    c1d = abs(H5["c1_diff"])
    if c1d >= 0.50 and ((excl(dpD) and excl(dpR) and excl(dpRs)) or (excl(dsD) and excl(dsR) and excl(dsRs))): v = "SURVIVES (different mechanisms)"
    elif c1d <= 0.20 and not any(excl(x) for x in (dpD, dsD, dpR, dsR, dpRs, dsRs)) and abs(dpD["point"]) <= 0.25 * abs(pi23) and abs(dpR["point"]) <= 0.25 * abs(pi23) and abs(dsD["point"]) <= 0.25 * abs(ss23) and abs(dsR["point"]) <= 0.25 * abs(ss23): v = "FALSIFIED (same mechanism)"
    else: v = "NOT DECIDABLE"
    H5["verdict"] = v
    A["H5"] = H5
    # ---------------- H2 descriptive shares (replay layer, LIVE_REPLAY and M2026_08)
    H2D = {}
    for n in ["M2026_08", "LIVE_REPLAY", "H1_2026"]:
        msk = pmask(n)
        H2D[n] = dict(fund_leg_gross_share_stale15=float(f15_share[msk].mean()), fund_leg_price_contrib_stale15_bps=float(f15_price[msk].mean()), fund_leg_carry_contrib_stale15_bps=float(f15_carry[msk].mean()),
                      book_gross_share_stale15=float(b15_share[msk].mean()), book_price_bps=float(price[msk].mean()), book_carry_bps=float(carry[msk].mean()))
    A["H2_descriptive_replay"] = H2D
    # ---------------- (5) live position in the state distribution
    POS = {}
    live_state = {s: float(np.nanmean(STATE_D2[s])) for s in PRIM + SECD}
    pre_vals = {s: STATE_REC[s][PRE] for s in PRIM + SECD}
    pre_sorted = {s: np.sort(pre_vals[s][np.isfinite(pre_vals[s])]) for s in PRIM + SECD}
    def ecdf(s, x): return float(np.searchsorted(pre_sorted[s], x, side="right") / len(pre_sorted[s]))
    def ecdf_vec(s, xs): out = np.searchsorted(pre_sorted[s], xs, side="right") / len(pre_sorted[s]); return np.where(np.isfinite(xs), out, np.nan)
    POS["live_mean_state"] = live_state; POS["pct_in_PRE_LIVE_anchors"] = {s: ecdf(s, live_state[s]) for s in PRIM + SECD}
    nL = len(dts); idxPRE = np.where(PRE)[0]
    starts = [idxPRE[q] for q in range(0, len(idxPRE) - nL + 1, 6) if idxPRE[q + nL - 1] - idxPRE[q] == nL - 1]
    WM = {s: np.array([np.nanmean(STATE_REC[s][a:a + nL]) for a in starts]) for s in PRIM + SECD}
    POS["pct_in_window_means"] = {s: float(np.mean(WM[s][np.isfinite(WM[s])] <= live_state[s])) for s in PRIM + SECD}
    POS["n_windows"] = len(starts); POS["window_len"] = nL
    Pmat = np.column_stack([ecdf_vec(s, STATE_REC[s]) for s in PRIM])
    live_vec = np.array([POS["pct_in_PRE_LIVE_anchors"][s] for s in PRIM])
    okA = PRE & np.all(np.isfinite(Pmat), 1); dist = np.sqrt(((Pmat - live_vec) ** 2).sum(1)); cand = np.where(okA)[0]
    near = cand[np.argsort(dist[cand], kind="stable")[:1000]]
    ANALOG_DAYS = np.unique(day[near]); FA = Fam(8, [("ANALOG", ANALOG_DAYS)])
    pa_, ra_ = FA.mean("ANALOG", day[near], np.column_stack([g[near], price[near], carry[near], cost[near]]))
    POS["analog"] = dict(n=int(len(near)), max_dist=float(dist[near].max()), g=summ(pa_[0], ra_[:, 0]), price=summ(pa_[1], ra_[:, 1]), carry=summ(pa_[2], ra_[:, 2]), cost=summ(pa_[3], ra_[:, 3]),
                         years={int(y): int(c) for y, c in zip(*np.unique(YM[near, 0], return_counts=True))})
    gnet_w = np.array([g[a:a + nL].mean() for a in starts]); gpre_w = np.array([(price - carry)[a:a + nL].mean() for a in starts])
    Wvec = np.column_stack([ecdf_vec(s, WM[s]) for s in PRIM])
    okW = np.all(np.isfinite(Wvec), 1); dW = np.sqrt(((Wvec - live_vec) ** 2).sum(1)); nearW = np.where(okW)[0][np.argsort(dW[okW], kind="stable")[:max(1, int(round(0.10 * okW.sum())))]]
    liveR = float(REAL["g"].mean()); liveRs = float(REAL["g_s"].mean()); liveD = float(D2["g_pre"].mean())
    POS["live_stats"] = dict(REAL_g=liveR, REAL_g_scaled=liveRs, D2_g_pre=liveD, REAL_g_r6net=float(REAL["g_r6net"].mean()))
    POS["uncond_pct"] = dict(REAL=float(np.mean(gnet_w <= liveR)), REAL_scaled=float(np.mean(gnet_w <= liveRs)), D2=float(np.mean(gpre_w <= liveD)))
    POS["cond_pct"] = dict(REAL=float(np.mean(gnet_w[nearW] <= liveR)), REAL_scaled=float(np.mean(gnet_w[nearW] <= liveRs)), D2=float(np.mean(gpre_w[nearW] <= liveD)), n_cond_windows=int(len(nearW)),
                           cond_window_years={int(y): int(c) for y, c in zip(*np.unique([ym(ts[starts[q]])[0] for q in nearW], return_counts=True))},
                           cond_gnet_quantiles=L(np.percentile(gnet_w[nearW], [2.5, 10, 50, 90])), cond_gpre_quantiles=L(np.percentile(gpre_w[nearW], [2.5, 10, 50, 90])))
    cp = POS["cond_pct"]
    POS["reading"] = ("ANOMALOUS" if all(cp[k] < 0.025 for k in ("REAL", "REAL_scaled", "D2")) else "WITHIN RANGE GIVEN STATE" if all(cp[k] >= 0.10 for k in ("REAL", "REAL_scaled", "D2")) else "INTERMEDIATE")
    A["position"] = POS
    OUT["arms"][arm] = A
    print("arm", arm, "done", round(time.time() - ta, 1), "s", flush=True)
# ------------------------------------------------------------------ arm-independent: H3 lags, D2/REAL levels, H2b descriptive
H3 = {}
Lf = {l: LG["LR_" + l] for l in ("fund", "king", "f10_s42", "f10_s2027")}
mH_l = complete & lag_period("H1_2026"); mA_l = complete & lag_period("M2026_08"); mL_l = complete & (lts >= LIVE0) & (lts <= dts.max())
lday = lts // 86400
def e01(l, msk): X = Lf[l][msk]; return np.column_stack([X[:, 0], X[:, 1:24].sum(1)])
cells = [("fund", "LAG_M2026_08", mA_l), ("fund", "LIVE_LAG", mL_l), ("king", "LAG_M2026_08", mA_l), ("f10_s42", "LAG_M2026_08", mA_l), ("f10_s2027", "LAG_M2026_08", mA_l)]
for l, per, msk in cells:
    pH_, rH_ = FAM[4].mean("LAG_H1_2026", lday[mH_l], e01(l, mH_l)); pT_, rT_ = FAM[4].mean(per, lday[msk], e01(l, msk))
    dE0 = summ(pT_[0] - pH_[0], rT_[:, 0] - rH_[:, 0], Z["H3"]); dE1 = summ(pT_[1] - pH_[1], rT_[:, 1] - rH_[:, 1], Z["H3"])
    E0H, E1H, E0T, E1T = float(pH_[0]), float(pH_[1]), float(pT_[0]), float(pT_[1])
    if dE1["vci_hi"] < 0 and E0T >= 0.75 * E0H and dE0["vci_lo"] <= 0 <= dE0["vci_hi"]: v = "HALF-LIFE"
    elif dE0["vci_hi"] < 0 and (E0T / E0H if E0H != 0 else np.inf) <= (E1T / E1H if E1H != 0 else np.inf) + 0.25: v = "LEVEL"
    elif dE1["point"] >= -0.25 * abs(E1H): v = "NO-DROP"
    else: v = "UNDECIDED"
    prof_H = Lf[l][mH_l].mean(0); prof_T = Lf[l][msk].mean(0)
    def thalf(pr): c = np.cumsum(pr); tot = c[-1]; return int(np.argmax(c >= 0.5 * tot)) if tot > 0 else None
    H3["%s|%s" % (l, per)] = dict(n_H1=int(mH_l.sum()), n_T=int(msk.sum()), E0_H1=E0H, E1_H1=E1H, E0_T=E0T, E1_T=E1T, dE0=dE0, dE1=dE1, cell_verdict=v, profile_H1=L(prof_H), profile_T=L(prof_T), t_half_H1=thalf(prof_H), t_half_T=thalf(prof_T),
                                    nonzero_share_T=float(np.mean(np.abs(Lf[l][msk][:, 0]) > 0)))
fcells = [H3["fund|LAG_M2026_08"]["cell_verdict"], H3["fund|LIVE_LAG"]["cell_verdict"]]
H3["verdict"] = "SURVIVES" if "HALF-LIFE" in fcells else ("FALSIFIED" if all(c in ("LEVEL", "NO-DROP") for c in fcells) else "NOT DECIDABLE")
OUT["H3"] = H3
OUT["verdict_agreement"] = {k: {a: OUT["arms"][a][sec][fld] for a in ARMS} for k, sec, fld in (("H1", "H1", "H1_verdict"), ("H1fuel", "H1", "H1fuel_verdict"), ("H4", "H4", "verdict"), ("H5", "H5", "verdict"))}
OUT["verdict_agreement"]["month_vanish"] = {a: OUT["arms"][a]["month"]["vanish"] for a in ARMS}
OUT["verdict_agreement"]["position_reading"] = {a: OUT["arms"][a]["position"]["reading"] for a in ARMS}
for k in list(OUT["verdict_agreement"]): OUT["verdict_agreement"][k]["all_agree"] = len(set(OUT["verdict_agreement"][k].values())) == 1
# D2 / REAL levels (k=1)
pDl, rDl = FAM[1].mean("LIVE_D2", dday, np.column_stack([D2[k] for k in ("price", "carry", "g_pre", "price_L", "price_S", "carry_L", "carry_S", "gross_L", "gross_S", "st15_gross", "st15_price", "st15_carry", "non8h_gross", "non8h_price", "non8h_carry", "fundsig_st15_absz_share", "fundsig_st15_lr0", "fundsig_lr0")]))
OUT["LIVE_D2_levels"] = {k: summ(pDl[q], rDl[:, q]) for q, k in enumerate(("price", "carry", "g_pre", "price_L", "price_S", "carry_L", "carry_S", "gross_L", "gross_S", "st15_gross", "st15_price", "st15_carry", "non8h_gross", "non8h_price", "non8h_carry", "fundsig_st15_absz_share", "fundsig_st15_lr0", "fundsig_lr0"))}
rk = ("price", "carry", "cost", "g", "g_r6net", "price_s", "carry_s", "g_s", "price_L", "price_S", "carry_L", "carry_S", "cost_L", "cost_S", "unsided_g", "gross_L", "gross_S", "coh_price", "coh_carry", "st15_price", "st15_carry", "st15_gross")
pRl, rRl = FAM[1].mean("LIVE_REAL", rday, np.column_stack([REAL[k] for k in rk]))
OUT["LIVE_REAL_levels"] = {k: summ(pRl[q], rRl[:, q]) for q, k in enumerate(rk)}
w5 = (rts <= 1789056000)
OUT["LIVE_REAL_W5_R6_reconciliation"] = dict(n=int(w5.sum()), price=float(REAL["price"][w5].mean()), fund=float(-REAL["carry"][w5].mean()), fee_timing_cost=float(REAL["cost"][w5].mean()), g=float(REAL["g"][w5].mean()), g_r6net=float(REAL["g_r6net"][w5].mean()))
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg=SH, input_sha256=INPUT_SHA, gates_used={k: (v.get("gate") or {k2: v[k2] for k2 in v if k2.startswith("gate")}) for k, v in GATES.items()}, result=OUT,
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T1_judge.json", "w"), indent=1, default=lambda o: (o.tolist() if isinstance(o, np.ndarray) else float(o) if isinstance(o, (np.floating,)) else int(o) if isinstance(o, (np.integer,)) else bool(o) if isinstance(o, np.bool_) else str(o)))
print("DONE_t1_judge", RC["wall_s"])
