#!/usr/bin/env python3
"""at_beta.py — replaces the withdrawn "market β = 0" reading of §2-C with an EX-ANTE RISK decomposition.

WHY THE OLD SECTION WAS WRONG. It computed market_i = W_i·ȳ(E) and, because the executor's reshape makes
ΣW = 0, concluded that "the market contribution is 0.000 in every period" and that "none of 2026 came from
the market". That is a statement about DOLLAR neutrality only. Dollar neutrality does not imply beta
neutrality: a book can be exactly dollar-neutral and still carry net market exposure whenever the names it
is long have systematically different betas from the names it is short. This device measures that.

════════ DEFINITIONS, FROZEN HERE BEFORE ANY NUMBER OF THIS DEVICE ════════
MARKET PROXY. m(E) = ȳ(E), the equal-weight mean 4h return over the anchor's producer member list ∩ in-life
  names — the same universe the book is normalised against. SENSITIVITY: m_btc(E) = BTCUSDT's 4h return.
  Both are reported; ȳ is primary because it is the cross-sectional centre the book itself is demeaned
  against, so a non-zero loading on it is exactly the exposure the old section claimed was absent.

EX-ANTE BETA. β_i(E) = Cov(r_i, m) / Var(m) over the W = 180 anchors (30 days) ENDING AT E, i.e. over the
  returns RET[j] with A[j] + 4h ≤ E — strictly realised by the decision instant, nothing from (E, E+4h].
  A pair (j, i) enters only if name i is in life over that whole window row. Requires ≥ 120 usable pairs
  and Var(m) > 0, else β_i(E) is UNDEFINED. No winsorisation, no shrinkage, no cap — the raw OLS slope;
  its distribution is reported so the reader can see the tails rather than have them hidden.

THE SPLIT (per anchor, in bps per unit target gross, the document's unit):
    price     = 1e4 · Σ_i W_i · RET_i
              = m(E) · 1e4 · Σ_{β defined} W_i β_i          ← COMMON (market) part = net-beta × market move
              + 1e4 · Σ_{β defined} W_i · (RET_i − β_i m(E)) ← RESIDUAL part
              + 1e4 · Σ_{β UNDEFINED} W_i · RET_i            ← UNATTRIBUTED, never dropped
  Reported long-side and short-side separately, and with the book's ex-ante NET BETA
    B(E) = Σ_{β defined} W_i β_i        (per unit gross; B = 0 would be beta-neutral)
  and its long/short halves, so "dollar-neutral but not beta-neutral" is a number, not an adjective.

NAMES WITHOUT AN ESTIMABLE BETA ARE BOUNDED, NOT DROPPED. For each anchor the device reports their gross
  share and the bound |Σ_{undef} W_i| · |m(E)| · β99(E), where β99(E) is the 99th percentile of |β| among
  the names that DO have one at that anchor. If the bound is small relative to the common part, the
  unattributed names cannot overturn the reading; if it is not, the device says so.

STYLE / CLUSTER STEP. At each anchor, a cross-sectional OLS of RET_i on
    [1, β_i, MOM30 dummies (2), LIQ (2), TBF (2), FUND (5), AGE (4)]
  over the in-life member names that have a β (the frozen C0 bucket rules of at_lib; one bucket per family
  dropped as the reference level). fitted f_i = common risk + style, residual e_i = name-specific.
    price = 1e4·Σ W_i f_i (COMMON RISK + STYLE) + 1e4·Σ W_i e_i (SELECTION) + unattributed.
  This is the honest version of "market vs selection": the old §2-C put everything except a ΣW·ȳ term
  (which is 0 by construction) into "selection".

usage: python at_beta.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import at_lib as L

T0 = time.time()
ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
chk = L.Checks(T0)
rec = L.rec_head("at_beta.py", sys.argv)
rec["replaces"] = "at_attrib.py block_C_market_vs_selection — the 'market β = 0' reading, withdrawn"
chk("env.whitelist", not sorted(set(rec["env"]) - ENV_OK), {"extra": sorted(set(rec["env"]) - ENV_OK)})
PANP = f"{L.ROOT}/work/AT_PANEL.npz"
L1P = f"{L.ROOT}/work/AT_L1_mean.npz"
rec["upstream"] = {"panel": {"path": PANP, "sha256": L.sha(PANP)}, "L1_mean": {"path": L1P, "sha256": L.sha(L1P)}}

WIN, MINOBS = 180, 120
Z = np.load(PANP, allow_pickle=True)
L1 = np.load(L1P)
in_run = Z["in_run"]
A_full = Z["A"].astype(np.int64)
SY = [str(s) for s in Z["symbols"]]
NW = len(SY)
RET_f = np.asarray(Z["RET"], np.float64)
INL_f = Z["INLIFE"]
MEMB_f = Z["MEMB"]
YB_f = np.asarray(Z["YBAR"], np.float64)
NAf = len(A_full)

# ── rolling ex-ante beta on the FULL axis (so the run window has a full warm-up where the grid allows) ──
m_f = np.where(np.isfinite(YB_f), YB_f, 0.0)
val = INL_f & np.isfinite(RET_f)
x = np.where(val, RET_f, 0.0)
mm = np.where(val, m_f[:, None], 0.0)
def cs(a):
    return np.vstack([np.zeros((1, NW)), np.cumsum(a, 0)])
c_n, c_x, c_m, c_xm, c_mm = cs(val.astype(np.float64)), cs(x), cs(mm), cs(x * mm), cs(mm * mm)
BETA = np.full((NAf, NW), np.nan)
for t in range(WIN, NAf):
    lo, hi = t - WIN, t                     # rows t-WIN .. t-1  ⇒ every RET realised by A[t]
    n = c_n[hi] - c_n[lo]
    ok = n >= MINOBS
    if not ok.any():
        continue
    sx = c_x[hi] - c_x[lo]; sm = c_m[hi] - c_m[lo]
    sxm = c_xm[hi] - c_xm[lo]; smm = c_mm[hi] - c_mm[lo]
    nn = np.maximum(n, 1.0)
    cov = sxm / nn - (sx / nn) * (sm / nn)
    var = smm / nn - (sm / nn) ** 2
    good = ok & (var > 1e-18)
    BETA[t, good] = cov[good] / var[good]
del c_n, c_x, c_m, c_xm, c_mm, x, mm, val
chk("beta.causal_window", True, {"window_anchors": WIN, "min_obs": MINOBS,
                                 "note": "rows t-180..t-1 only; every return realised by A[t]"})

A = A_full[in_run]
NA = len(A)
W = np.asarray(Z["W"], np.float64)[in_run]
RET = RET_f[in_run]
INL = INL_f[in_run]
MEMB = MEMB_f[in_run]
B = BETA[in_run]
m = m_f[in_run]
AGE = np.asarray(Z["AGE"], np.float64)[in_run]
RN8 = np.asarray(Z["RN8"], np.float64)[in_run]
MOM30 = np.asarray(Z["MOM30"], np.float64)[in_run]
LIQ = np.asarray(Z["LIQ"], np.float64)[in_run]
TBF = np.asarray(Z["TBF"], np.float64)[in_run]

held = W != 0
hasb = np.isfinite(B)
chk("beta.coverage_of_held_names", float((hasb & held).sum() / max(held.sum(), 1)) > 0.90,
    {"share_of_held_name_anchors_with_a_beta": float((hasb & held).sum() / max(held.sum(), 1))})
bq = np.nanpercentile(B[hasb & held], [1, 25, 50, 75, 99])
rec["beta_distribution_held"] = {"p01": float(bq[0]), "p25": float(bq[1]), "p50": float(bq[2]),
                                 "p75": float(bq[3]), "p99": float(bq[4])}

Bw = np.where(hasb, B, 0.0)
Wd = np.where(hasb, W, 0.0)          # weight on names that HAVE a beta
Wu = np.where(hasb, 0.0, W)          # weight on names that do not
netb = (Wd * Bw).sum(1)                                   # book ex-ante net beta, per unit gross
common = 1e4 * m * netb
resid = 1e4 * (Wd * (RET - Bw * m[:, None])).sum(1)
unatt = 1e4 * (Wu * RET).sum(1)
price = 1e4 * (W * RET).sum(1)
chk("split.additive", float(np.abs(common + resid + unatt - price).max()) <= 1e-9,
    {"max_abs_bps": float(np.abs(common + resid + unatt - price).max())})
b99 = np.array([np.nanpercentile(np.abs(B[t][hasb[t] & held[t]]), 99) if (hasb[t] & held[t]).any() else 0.0 for t in range(NA)])
bound = 1e4 * np.abs(Wu).sum(1) * np.abs(m) * b99

LONG, SHORT = W > 0, W < 0
def side(mask_side, arr_w):
    return 1e4 * m * (np.where(mask_side, arr_w, 0.0) * Bw).sum(1)


OUTJ = {"status": "CORRECTED §2-C: ex-ante risk decomposition; replaces the withdrawn 'market β = 0' reading",
        "definitions": {"market": "ȳ(E) = equal-weight member ∩ in-life 4h return (primary); BTCUSDT 4h return (sensitivity)",
                        "beta": "OLS Cov(r_i,m)/Var(m) over the 180 anchors ending at E (all realised by E); ≥120 usable pairs; no winsorisation",
                        "split": "price = m·Σ W β (COMMON) + Σ W (RET − β m) (RESIDUAL) + Σ_{no β} W RET (UNATTRIBUTED)"},
        "beta_distribution_held_names": rec["beta_distribution_held"], "per_period": {}}
PERMASK = {n: L.period_mask(A, lo, hi) for n, lo, hi, _ in L.PERIODS}
PERMASK = {k: v for k, v in PERMASK.items() if v.any()}
for k, msk in PERMASK.items():
    OUTJ["per_period"][k] = {
        "n_anchors": int(msk.sum()),
        "price": float(price[msk].mean()),
        "common_market": float(common[msk].mean()),
        "residual_selection": float(resid[msk].mean()),
        "unattributed_no_beta": float(unatt[msk].mean()),
        "unattributed_bound_abs": float(bound[msk].mean()),
        "gross_share_without_beta": float(np.abs(Wu)[msk].sum() / np.abs(W)[msk].sum()),
        "book_ex_ante_net_beta_mean": float(netb[msk].mean()),
        "book_ex_ante_net_beta_absmean": float(np.abs(netb[msk]).mean()),
        "book_ex_ante_net_beta_p05_p95": [float(np.percentile(netb[msk], 5)), float(np.percentile(netb[msk], 95))],
        "net_beta_long_side": float((np.where(LONG, Wd, 0.0) * Bw)[msk].sum(1).mean()),
        "net_beta_short_side": float((np.where(SHORT, Wd, 0.0) * Bw)[msk].sum(1).mean()),
        "common_long": float(side(LONG, Wd)[msk].mean()), "common_short": float(side(SHORT, Wd)[msk].mean()),
        "residual_long": float((1e4 * (np.where(LONG, Wd, 0.0) * (RET - Bw * m[:, None])).sum(1))[msk].mean()),
        "residual_short": float((1e4 * (np.where(SHORT, Wd, 0.0) * (RET - Bw * m[:, None])).sum(1))[msk].mean()),
        "dollar_net_over_gross": float((W * INL)[msk].sum(1).mean()),
        "mean_market_bps": float(m[msk].mean() * 1e4)}

# ── style / cluster regression ──
def terc(X):
    o = np.full(X.shape, -1, np.int8)
    for i in range(X.shape[0]):
        v = X[i][MEMB[i] & np.isfinite(X[i])]
        if v.size < 10:
            continue
        q1, q2 = np.quantile(v, [1 / 3, 2 / 3])
        o[i] = np.where(np.isfinite(X[i]), np.where(X[i] < q1, 0, np.where(X[i] > q2, 2, 1)), -1)
    return o


LABS = {"MOM30": terc(MOM30), "LIQ": terc(LIQ), "TBF": terc(TBF)}
age_bin = np.full(AGE.shape, -1, np.int8)
ed = [0, 90, 180, 365, 730, np.inf]
for b in range(5):
    age_bin = np.where(np.isfinite(AGE) & (AGE >= ed[b]) & (AGE < ed[b + 1]), b, age_bin)
rn = RN8 * 1e4
fb = np.full(RN8.shape, -1, np.int8)
for b, c in enumerate([(rn <= -10), (rn > -10) & (rn < 0), (rn >= 0) & (rn < 0.999),
                       (rn >= 0.999) & (rn <= 1.001), (rn > 1.001) & (rn <= 5), (rn > 5)]):
    fb = np.where(np.isfinite(RN8) & c, b, fb)
LABS["FUND"] = fb
LABS["AGE"] = age_bin
NB = {"MOM30": 3, "LIQ": 3, "TBF": 3, "FUND": 6, "AGE": 5}
sty_c = np.zeros(NA)
sty_r = np.zeros(NA)
sty_cl = np.zeros(NA); sty_cs = np.zeros(NA); sty_rl = np.zeros(NA); sty_rs = np.zeros(NA)
nfit = np.zeros(NA)
for t in range(NA):
    u = MEMB[t] & INL[t] & hasb[t] & np.isfinite(RET[t])
    for f_, lab in LABS.items():
        u &= lab[t] >= 0
    n = int(u.sum())
    nfit[t] = n
    if n < 60:
        sty_r[t] = 1e4 * (W[t] * RET[t]).sum()
        continue
    cols = [np.ones(n), B[t][u]]
    for f_, lab in LABS.items():
        for b in range(1, NB[f_]):            # drop bucket 0 as the reference level
            cols.append((lab[t][u] == b).astype(float))
    X = np.stack(cols, 1)
    y = RET[t][u]
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    f_all = np.zeros(NW)
    f_all[u] = X @ coef
    e_all = np.zeros(NW)
    e_all[u] = y - f_all[u]
    off = ~u                                   # held names outside the fit population
    sty_c[t] = 1e4 * (W[t] * f_all).sum()
    sty_r[t] = 1e4 * (W[t] * e_all).sum() + 1e4 * (W[t] * np.where(off, RET[t], 0.0)).sum()
    sty_cl[t] = 1e4 * (np.where(LONG[t], W[t], 0.0) * f_all).sum()
    sty_cs[t] = 1e4 * (np.where(SHORT[t], W[t], 0.0) * f_all).sum()
    sty_rl[t] = 1e4 * (np.where(LONG[t], W[t], 0.0) * e_all).sum() + 1e4 * (np.where(LONG[t] & off, W[t] * RET[t], 0.0)).sum()
    sty_rs[t] = 1e4 * (np.where(SHORT[t], W[t], 0.0) * e_all).sum() + 1e4 * (np.where(SHORT[t] & off, W[t] * RET[t], 0.0)).sum()
    if t % 1500 == 0:
        chk.log("style", t, "/", NA, "n_fit", n)
chk("style.additive", float(np.abs(sty_c + sty_r - price).max()) <= 1e-8,
    {"max_abs_bps": float(np.abs(sty_c + sty_r - price).max())})
chk("style.fit_population", float(nfit.mean()) > 100, {"mean_names_in_fit": float(nfit.mean()),
                                                       "anchors_below_60": int((nfit < 60).sum())})
for k, msk in PERMASK.items():
    OUTJ["per_period"][k].update({
        "style_common_risk_and_style": float(sty_c[msk].mean()),
        "style_residual_selection": float(sty_r[msk].mean()),
        "style_common_long": float(sty_cl[msk].mean()), "style_common_short": float(sty_cs[msk].mean()),
        "style_residual_long": float(sty_rl[msk].mean()), "style_residual_short": float(sty_rs[msk].mean()),
        "style_mean_names_in_fit": float(nfit[msk].mean())})

# BTC sensitivity on the net beta only (cheap, and it answers "is this an artefact of the ȳ proxy")
jb = SY.index("BTCUSDT") if "BTCUSDT" in SY else None
if jb is not None:
    mb_f = np.where(INL_f[:, jb], RET_f[:, jb], 0.0)
    valb = INL_f & np.isfinite(RET_f)
    xb = np.where(valb, RET_f, 0.0)
    mb = np.where(valb, mb_f[:, None], 0.0)
    c_n, c_x, c_m, c_xm, c_mm = cs(valb.astype(np.float64)), cs(xb), cs(mb), cs(xb * mb), cs(mb * mb)
    BB = np.full((NAf, NW), np.nan)
    for t in range(WIN, NAf):
        lo, hi = t - WIN, t
        n = c_n[hi] - c_n[lo]
        okk = n >= MINOBS
        if not okk.any():
            continue
        sx = c_x[hi] - c_x[lo]; sm = c_m[hi] - c_m[lo]
        sxm = c_xm[hi] - c_xm[lo]; smm = c_mm[hi] - c_mm[lo]
        nn = np.maximum(n, 1.0)
        cov = sxm / nn - (sx / nn) * (sm / nn)
        var = smm / nn - (sm / nn) ** 2
        g = okk & (var > 1e-18)
        BB[t, g] = cov[g] / var[g]
    del c_n, c_x, c_m, c_xm, c_mm, xb, mb, valb
    Bb = BB[in_run]
    hb = np.isfinite(Bb)
    netbb = (np.where(hb, W, 0.0) * np.where(hb, Bb, 0.0)).sum(1)
    cb = 1e4 * mb_f[in_run] * netbb
    for k, msk in PERMASK.items():
        OUTJ["per_period"][k].update({"btc_net_beta_mean": float(netbb[msk].mean()),
                                      "btc_common_market": float(cb[msk].mean()),
                                      "btc_mean_market_bps": float(mb_f[in_run][msk].mean() * 1e4)})

# ── CI on the contrasts that carry the conclusions ──
SER = {"price": price, "common_market": common, "residual_selection": resid,
       "style_common": sty_c, "style_residual": sty_r, "net_beta": netb, "market_bps": m * 1e4}
def ci_of(x, msk, k):
    _, s_, c_ = L.day_aggregate(A, x, msk)
    return L.ci_p(float(s_.sum() / c_.sum()), L.boot_mean_ratio(s_, c_, seed_k=k))
m23 = PERMASK["2023full"]; mref = PERMASK["2024"] | PERMASK["2025"] | PERMASK["2026"]
m26 = PERMASK["2026"]; mh = PERMASK["HIST"]
OUTJ["ci_2023H2_vs_reference"] = {nm: {"2023H2": ci_of(x, m23, 800 + j), "2024_2026_reference": ci_of(x, mref, 830 + j)}
                                  for j, (nm, x) in enumerate(sorted(SER.items()))}
OUTJ["ci_2026_vs_HIST"] = {}
for j, (nm, x) in enumerate(sorted(SER.items())):
    _, sA, cA = L.day_aggregate(A, x, m26)
    _, sB, cB = L.day_aggregate(A, x, mh)
    hat, dr = L.boot_two_window(sA, cA, sB, cB, seed_k=860 + j)
    r_ = L.ci_p(hat, dr); r_.update({"mean_2026": float(sA.sum() / cA.sum()), "mean_hist": float(sB.sum() / cB.sum())})
    OUTJ["ci_2026_vs_HIST"][nm] = r_

# ── cross-check requested by the coordinator: does the DISP-bucket SHIFT explain the 2026 improvement? ──
# Δg = Σ_b (p26_b − ph_b)·gh_b   [BETWEEN: the book spent more time in better buckets]
#    + Σ_b p26_b·(g26_b − gh_b)  [WITHIN : the book behaved differently inside the same bucket]
G0L = Z["G0L"][in_run]
GV = [str(s_) for s_ in Z["G0_VARS"]]
DIS = {}
for cn in ("DISP", "FDISP", "VOL", "ALT", "BREADTH", "FLEVEL"):
    lab = G0L[:, GV.index(L.COND_FROM_G0[cn])]
    okh = mh & (lab >= 0); ok6 = m26 & (lab >= 0)
    ph = np.array([float((okh & (lab == b)).sum()) for b in range(3)]); ph /= max(ph.sum(), 1)
    p6 = np.array([float((ok6 & (lab == b)).sum()) for b in range(3)]); p6 /= max(p6.sum(), 1)
    gh = np.array([float(L1["g"][okh & (lab == b)].mean()) if (okh & (lab == b)).sum() else 0.0 for b in range(3)])
    g6 = np.array([float(L1["g"][ok6 & (lab == b)].mean()) if (ok6 & (lab == b)).sum() else 0.0 for b in range(3)])
    DIS[cn] = {"share_hist": ph.tolist(), "share_2026": p6.tolist(),
               "g_hist_by_bucket": gh.tolist(), "g_2026_by_bucket": g6.tolist(),
               "total_delta": float((p6 * g6).sum() - (ph * gh).sum()),
               "between_bucket_shift": float(((p6 - ph) * gh).sum()),
               "within_bucket_change": float((p6 * (g6 - gh)).sum())}
OUTJ["bucket_shift_vs_within_2026_minus_HIST"] = DIS

p = f"{OUT}/AT_BETA.json"
with open(p + ".tmp", "w") as f:
    json.dump(OUTJ, f, indent=1, default=str)
os.replace(p + ".tmp", p)
rec["outputs"] = {"beta": {"path": p, "sha256": L.sha(p)}}
v = L.write_receipt(rec, chk, f"{OUT}/AT_BETA_RECEIPT.json", {"peak_rss_gb": L.rss_gb(), "runtime_s": round(time.time() - T0, 1)})
print("AT_BETA VERDICT=%s checks=%d failed=%s" % (v, len(chk.rows), chk.fails), flush=True)
sys.exit(0 if v == "PASS" else 3)
