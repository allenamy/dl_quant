#!/usr/bin/env python3
"""at_attrib.py — PREREG §2-A…§2-F on the L2 paper panel built by at_build.py, reconciled to the L1 realised
layer of the certified run at every period. Definitions are the frozen ones (at_lib header +
RUN_CONFIG_attrib_2026-09-20.json); this device only aggregates and tests.

Per-name contributions at anchor E (bps per unit target gross; the paper book W has Σ|W| = 1):
  price_i   = 1e4 · W_i · RET_i
  fundpd_i  = 1e4 · W_i · FUNDPAID_i                      (positive = the book pays)
  fee_i     = L1_fee(E) · |ΔW_i| / Σ_j|ΔW_j|              (the REALISED anchor fee, allocated by the paper
                                                           book's own per-name turnover; ΔW against the
                                                           previous anchor of the axis, ΔW = W at the first)
  net_i     = price_i − fundpd_i − fee_i
  Σ_i net_i = paper price − paper funding − realised fee. It is NOT the realised g: the difference
  RESID = realised g − Σ_i net_i is the execution residual (fill timing at N+24 min, partial fills, per-name
  stops, day-stop flattens, halts, holds, dust, venue clamps and pops) and is reported per period in block R,
  never absorbed into a leg or a group.

Blocks: R reconciliation · A legs (A1 / A2 / A2b + raw leg returns) · B groups · C market vs selection ·
D anchor conditions · E extreme anchors · F the 2023 fall. Family: 22 group tests + 8 condition tests, Holm.

usage: python at_attrib.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import at_lib as L

T0 = time.time()
ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
os.makedirs(OUT, exist_ok=True)
chk = L.Checks(T0)
rec = L.rec_head("at_attrib.py", sys.argv)
chk("env.whitelist", not sorted(set(rec["env"]) - ENV_OK), {"extra": sorted(set(rec["env"]) - ENV_OK)})
CFGP = f"{L.ROOT}/RUN_CONFIG_attrib_2026-09-20.json"
rec["frozen_config"] = {"path": CFGP, "sha256": L.sha(CFGP)}
PANP = f"{L.ROOT}/work/AT_PANEL.npz"
L1P = f"{L.ROOT}/work/AT_L1_mean.npz"
rec["upstream"] = {"panel": {"path": PANP, "sha256": L.sha(PANP)}, "L1_mean": {"path": L1P, "sha256": L.sha(L1P)}}

Z = np.load(PANP, allow_pickle=True)
L1 = np.load(L1P)
A_full = Z["A"].astype(np.int64)
in_run = Z["in_run"]
A = A_full[in_run]
NA = len(A)
chk("axis.matches_L1", np.array_equal(A, L1["A"].astype(np.int64)), {"n": int(NA)})
SY = [str(s) for s in Z["symbols"]]
NW = len(SY)

W = np.asarray(Z["W"], np.float64)[in_run]
AK = np.asarray(Z["AK"], np.float64)[in_run]
BF = np.asarray(Z["BF"], np.float64)[in_run]
SHARE = np.asarray(Z["SHARE"], np.float64)[in_run]
LMIX = Z["LMIX"][in_run]
RET = np.asarray(Z["RET"], np.float64)[in_run]
FUND = np.asarray(Z["FUND"], np.float64)[in_run]
MEMB = Z["MEMB"][in_run]
INLIFE = Z["INLIFE"][in_run]
KIND = Z["KIND"][in_run]
PHI = Z["PHI"][in_run]
YBAR = Z["YBAR"][in_run]
NETQ = Z["NETQ"][in_run]
AGE = np.asarray(Z["AGE"], np.float64)[in_run]
RN8 = np.asarray(Z["RN8"], np.float64)[in_run]
MOM30 = np.asarray(Z["MOM30"], np.float64)[in_run]
LIQ = np.asarray(Z["LIQ"], np.float64)[in_run]
TBF = np.asarray(Z["TBF"], np.float64)[in_run]
COND = Z["COND"][in_run]
CONDN = [str(s) for s in Z["COND_NAMES"]]
G0L = Z["G0L"][in_run]
G0V = Z["G0V"][in_run]
GVARS = [str(s) for s in Z["G0_VARS"]]

# ─────────────────────────── per-name contributions ───────────────────────────
PRICE = 1e4 * W * RET
FPAID = 1e4 * W * FUND
dW = np.vstack([W[:1], np.diff(W, axis=0)])
tot_dw = np.abs(dW).sum(1)
FEE = np.where(tot_dw[:, None] > 0, np.abs(dW) * (L1["fee"] / np.maximum(tot_dw, 1e-300))[:, None], 0.0)
NET = PRICE - FPAID - FEE
chk("fee.allocation_sums_to_realised", float(np.abs(FEE.sum(1) - L1["fee"]).max()) < 1e-9,
    {"max_abs_bps": float(np.abs(FEE.sum(1) - L1["fee"]).max())})
px_paper = PRICE.sum(1)
fd_paper = FPAID.sum(1)
net_paper = NET.sum(1)
RESID = L1["g"] - net_paper

yb0 = np.where(np.isfinite(YBAR), YBAR, 0.0)
MKT = 1e4 * W * INLIFE * yb0[:, None]
SEL = 1e4 * W * INLIFE * (RET - yb0[:, None])
chk("C.market_plus_selection_per_name", float(np.abs(MKT + SEL - PRICE).max()) < 1e-9,
    {"max_abs_bps": float(np.abs(MKT + SEL - PRICE).max())})

with np.errstate(all="ignore"):
    A1K = 1e4 * (AK * RET).sum(1) / LMIX
    A1F = 1e4 * (BF * RET).sum(1) / LMIX
    A1K_f = 1e4 * (AK * FUND).sum(1) / LMIX
    A1F_f = 1e4 * (BF * FUND).sum(1) / LMIX
SHP = px_paper - A1K - A1F
SHP_f = fd_paper - A1K_f - A1F_f
A2K = (SHARE * PRICE).sum(1)
A2F = PRICE.sum(1) - A2K
A2K_f = (SHARE * FPAID).sum(1)
A2F_f = FPAID.sum(1) - A2K_f
# raw (un-seated) leg returns, per unit of the leg's OWN gross
with np.errstate(all="ignore"):
    gk = np.abs(AK).sum(1)
    gf = np.abs(BF).sum(1)
    RAWK = np.where(gk > 0, 1e4 * (AK * RET).sum(1) / np.maximum(gk, 1e-300), np.nan)
    RAWF = np.where(gf > 0, 1e4 * (BF * RET).sum(1) / np.maximum(gf, 1e-300), np.nan)

GROSS = np.abs(W).sum(1)
LONG = W > 0
SHORT = W < 0


# ─────────────────────────── grouping ───────────────────────────
def tercile_labels(X, memb):
    """per-anchor terciles inside the member set over finite values (c0 §1.4 / G0 §2 rule)."""
    out = np.full(X.shape, -1, np.int8)
    for i in range(X.shape[0]):
        v = X[i][memb[i] & np.isfinite(X[i])]
        if v.size < 10:
            continue
        q1, q2 = np.quantile(v, [1 / 3, 2 / 3])
        row = X[i]
        ok = np.isfinite(row)
        lab = np.where(row < q1, 0, np.where(row > q2, 2, 1))
        out[i] = np.where(ok, lab, -1)
    return out


LAB = {}
age_bin = np.full(AGE.shape, -1, np.int8)
edges = [0, 90, 180, 365, 730, np.inf]
for b in range(5):
    age_bin = np.where(np.isfinite(AGE) & (AGE >= edges[b]) & (AGE < edges[b + 1]), b, age_bin)
LAB["AGE"] = age_bin
rn_bp = RN8 * 1e4
fund_bin = np.full(RN8.shape, -1, np.int8)
conds = [(rn_bp <= -10), (rn_bp > -10) & (rn_bp < 0), (rn_bp >= 0) & (rn_bp < 0.999),
         (rn_bp >= 0.999) & (rn_bp <= 1.001), (rn_bp > 1.001) & (rn_bp <= 5), (rn_bp > 5)]
for b, c in enumerate(conds):
    fund_bin = np.where(np.isfinite(RN8) & c, b, fund_bin)
LAB["FUND"] = fund_bin
LAB["MOM30"] = tercile_labels(MOM30, MEMB)
LAB["LIQ"] = tercile_labels(LIQ, MEMB)
LAB["TBF"] = tercile_labels(TBF, MEMB)
dir_bin = np.where(LONG, 0, np.where(SHORT, 1, -1)).astype(np.int8)
LAB["DIR"] = dir_bin
for k, spec in L.GROUP_SPECS:
    nb = len(spec)
    chk(f"group.labels_in_range.{k}", int(LAB[k].max()) < nb and int(LAB[k].min()) >= -1,
        {"min": int(LAB[k].min()), "max": int(LAB[k].max())})
held = W != 0
for k, spec in L.GROUP_SPECS:
    cov = float((LAB[k][held] >= 0).mean())
    chk(f"group.coverage_of_held_names.{k}", cov > 0.90, {"share_labelled": cov})


def group_sums(lab, nb, X):
    """(NA, nb) per-anchor sum of X inside each bin, plus the NA-row (unlabelled)."""
    out = np.zeros((X.shape[0], nb + 1))
    for b in range(nb):
        out[:, b] = np.where(lab == b, X, 0.0).sum(1)
    out[:, nb] = np.where(lab < 0, X, 0.0).sum(1)
    return out


# ─────────────────────────── period aggregation ───────────────────────────
def per_period(mask, extra=None):
    d = {"n_anchors": int(mask.sum()), "first": L.utc(A[mask][0]), "last": L.utc(A[mask][-1])}
    d["L1"] = {k: float(L1[k][mask].mean()) for k in ("g", "price", "funding_paid", "fee", "turnover")}
    d["L1"]["stops_total"] = float(L1["nstop"][mask].sum())
    d["L1"]["flattens_total"] = float(L1["dstop"][mask].sum())
    d["L1"]["halt_anchors"] = float(L1["halt"][mask].sum())
    d["L2"] = {"price": float(px_paper[mask].mean()), "funding_paid": float(fd_paper[mask].mean()),
               "fee": float(L1["fee"][mask].mean()), "net": float(net_paper[mask].mean())}
    d["resid_L1_minus_L2"] = float(RESID[mask].mean())
    d["resid_share_of_L1_g"] = (float(RESID[mask].mean() / L1["g"][mask].mean()) if abs(L1["g"][mask].mean()) > 1e-9 else None)
    return d


PERMASK = {}
for name, lo, hi, _ in L.PERIODS:
    m = L.period_mask(A, lo, hi)
    if m.any():
        PERMASK[name] = m

OUTJ = {"block_R_reconciliation": {k: per_period(m) for k, m in PERMASK.items()}}

# ── A: legs ──
blockA = {}
for k, m in PERMASK.items():
    a1k, a1f, shp = float(A1K[m].mean()), float(A1F[m].mean()), float(SHP[m].mean())
    a2k, a2f = float(A2K[m].mean()), float(A2F[m].mean())
    tot1, tot2 = a1k + a1f + shp, a2k + a2f
    sc = max(abs(tot1), abs(tot2), 1e-12)
    blockA[k] = {
        "A1_price": {"king": a1k, "fund": a1f, "shape_residual": shp, "total": tot1},
        "A2_price": {"king": a2k, "fund": a2f, "total": tot2},
        "A1_funding_paid": {"king": float(A1K_f[m].mean()), "fund": float(A1F_f[m].mean()), "shape_residual": float(SHP_f[m].mean())},
        "A2_funding_paid": {"king": float(A2K_f[m].mean()), "fund": float(A2F_f[m].mean())},
        "raw_leg_price_per_own_gross": {"king": float(np.nanmean(RAWK[m])), "fund": float(np.nanmean(RAWF[m]))},
        "seats": {"phi_king_mean": float(PHI[m, 0].mean()), "phi_fund_mean": float(PHI[m, 1].mean()),
                  "share_anchors_king_file_only": float((KIND[m] == 1).mean())},
        "A1_vs_A2_gap": {"king": a1k - a2k, "fund": a1f - a2f,
                         "king_exceeds_5pct": bool(abs(a1k - a2k) > 0.05 * sc),
                         "fund_exceeds_5pct": bool(abs(a1f - a2f) > 0.05 * sc),
                         "scale_used": sc},
    }
OUTJ["block_A_legs"] = blockA

# ── B: groups ──
blockB = {}
GS_CACHE = {}
for gname, bins in L.GROUP_SPECS:
    nb = len(bins)
    lab = LAB[gname]
    GS_CACHE[gname] = {"net": group_sums(lab, nb, NET), "price": group_sums(lab, nb, PRICE),
                       "fund": group_sums(lab, nb, FPAID), "fee": group_sums(lab, nb, FEE),
                       "gross": group_sums(lab, nb, np.abs(W)), "sel": group_sums(lab, nb, SEL),
                       "mkt": group_sums(lab, nb, MKT)}
    chk(f"group.sums_add_up.{gname}",
        float(np.abs(GS_CACHE[gname]["net"].sum(1) - NET.sum(1)).max()) < 1e-9,
        {"max_abs_bps": float(np.abs(GS_CACHE[gname]["net"].sum(1) - NET.sum(1)).max())})
    tab = {}
    for k, m in PERMASK.items():
        rows = {}
        for b, bn in enumerate(list(bins) + ["NA"]):
            gsh = float(GS_CACHE[gname]["gross"][m, b].mean())
            rows[bn] = {"gross_share": gsh,
                        "price": float(GS_CACHE[gname]["price"][m, b].mean()),
                        "funding_paid": float(GS_CACHE[gname]["fund"][m, b].mean()),
                        "fee": float(GS_CACHE[gname]["fee"][m, b].mean()),
                        "net": float(GS_CACHE[gname]["net"][m, b].mean()),
                        "market": float(GS_CACHE[gname]["mkt"][m, b].mean()),
                        "selection": float(GS_CACHE[gname]["sel"][m, b].mean()),
                        "price_over_own_gross": (float(GS_CACHE[gname]["price"][m, b].mean() / gsh) if gsh > 1e-9 else None)}
        tab[k] = rows
    blockB[gname] = tab
OUTJ["block_B_groups"] = blockB

# ── C: market vs selection, basket returns ──
blockC = {}
for k, m in PERMASK.items():
    wl = np.where(LONG, W, 0.0)
    ws = np.where(SHORT, -W, 0.0)
    with np.errstate(all="ignore"):
        rl = np.where(wl[m].sum(1) > 0, (wl[m] * RET[m]).sum(1) / np.maximum(wl[m].sum(1), 1e-300), np.nan)
        rs = np.where(ws[m].sum(1) > 0, (ws[m] * RET[m]).sum(1) / np.maximum(ws[m].sum(1), 1e-300), np.nan)
    blockC[k] = {"price": float(px_paper[m].mean()), "market": float(MKT[m].sum(1).mean()),
                 "selection": float(SEL[m].sum(1).mean()),
                 "market_long": float(np.where(LONG, MKT, 0.0)[m].sum(1).mean()),
                 "market_short": float(np.where(SHORT, MKT, 0.0)[m].sum(1).mean()),
                 "selection_long": float(np.where(LONG, SEL, 0.0)[m].sum(1).mean()),
                 "selection_short": float(np.where(SHORT, SEL, 0.0)[m].sum(1).mean()),
                 "ubar_bps": float(np.nanmean(YBAR[m]) * 1e4),
                 "long_basket_minus_ubar_bps": float(np.nanmean(rl - yb0[m]) * 1e4),
                 "short_basket_minus_ubar_bps": float(np.nanmean(rs - yb0[m]) * 1e4),
                 "net_priced_exposure_share_of_gross": float(NETQ[m].mean()),
                 "gross_out_of_life_share": float(np.abs(W[m])[~INLIFE[m]].sum() / np.abs(W[m]).sum()),
                 "gross_outside_member_set_share": float(np.abs(W[m])[~MEMB[m]].sum() / np.abs(W[m]).sum())}
OUTJ["block_C_market_vs_selection"] = blockC

# ── D: anchor conditions ──
def expanding_terciles(x, warm=1080):
    lab = np.full(len(x), -1, np.int8)
    for i in range(warm, len(x)):
        h = x[:i + 1]
        h = h[np.isfinite(h)]
        if h.size < warm:
            continue
        q1, q2 = np.quantile(h, [1 / 3, 2 / 3])
        if np.isfinite(x[i]):
            lab[i] = 0 if x[i] < q1 else (2 if x[i] > q2 else 1)
    return lab


CLAB = {}
for ci, cn in enumerate(CONDN):
    if cn in L.COND_FROM_G0:
        CLAB[cn] = G0L[:, GVARS.index(L.COND_FROM_G0[cn])]
    else:
        CLAB[cn] = expanding_terciles(COND[:, ci])
blockD = {}
for k, m in PERMASK.items():
    blockD[k] = {cn: {"mean": (float(np.nanmean(COND[m, ci])) if np.isfinite(COND[m, ci]).any() else None),
                      "median": (float(np.nanmedian(COND[m, ci])) if np.isfinite(COND[m, ci]).any() else None)}
                 for ci, cn in enumerate(CONDN)}
OUTJ["block_D_conditions_levels"] = blockD

mfull = PERMASK["FULL_RECIPE"]
dcells = {}
for cn in CONDN:
    lab = CLAB[cn]
    cell = {}
    for b, bn in ((0, "low"), (1, "mid"), (2, "high")):
        mm = mfull & (lab == b)
        if mm.sum() < 2:
            cell[bn] = {"n_anchors": int(mm.sum())}
            continue
        ud, s, c = L.day_aggregate(A, L1["g"], mm)
        cell[bn] = {"n_anchors": int(mm.sum()), "n_days": int(len(ud)), "g": float(s.sum() / c.sum()),
                    "price": float(L1["price"][mm].mean()), "funding_paid": float(L1["funding_paid"][mm].mean()),
                    "fee": float(L1["fee"][mm].mean()),
                    "A1_fund_price": float(A1F[mm].mean()), "A1_king_price": float(A1K[mm].mean()),
                    "selection": float(SEL[mm].sum(1).mean()), "market": float(MKT[mm].sum(1).mean())}
    dcells[cn] = cell
OUTJ["block_D_conditions_cells_FULL_RECIPE"] = dcells

# ── the frozen family: 22 group tests + 8 condition tests, Holm ──
m2026 = PERMASK["2026"]
mhist = PERMASK["HIST"]
fam = []
kk = 0
for gname, bins in L.GROUP_SPECS:
    for b, bn in enumerate(bins):
        x = GS_CACHE[gname]["net"][:, b]
        _, sA, cA = L.day_aggregate(A, x, m2026)
        _, sB, cB = L.day_aggregate(A, x, mhist)
        hat, dr = L.boot_two_window(sA, cA, sB, cB, seed_k=kk)
        r_ = L.ci_p(hat, dr)
        r_.update({"test": f"B:{gname}:{bn}", "kind": "group net 2026 − HIST", "k": kk,
                   "mean_2026": float(sA.sum() / cA.sum()), "mean_hist": float(sB.sum() / cB.sum())})
        for bl in L.BLOCK_SENS:
            _, dr2 = L.boot_two_window(sA, cA, sB, cB, b=bl, seed_k=kk)
            r_[f"ci95_block{bl}"] = L.ci_p(hat, dr2)["ci95"]
        fam.append(r_)
        kk += 1
for cn in CONDN[:len(L.COND_NAMES)]:
    lab = CLAB[cn]
    mh = mfull & (lab == 2)
    ml = mfull & (lab == 0)
    if mh.sum() < 2 or ml.sum() < 2:
        fam.append({"test": f"D:{cn}:high−low", "kind": "g high tercile − low tercile (FULL_RECIPE)", "k": kk,
                    "point": None, "ci95": [None, None], "p": None, "note": "fewer than 2 days in a tercile"})
        kk += 1
        continue
    _, sA, cA = L.day_aggregate(A, L1["g"], mh)
    _, sB, cB = L.day_aggregate(A, L1["g"], ml)
    hat, dr = L.boot_two_window(sA, cA, sB, cB, seed_k=kk)
    r_ = L.ci_p(hat, dr)
    r_.update({"test": f"D:{cn}:high−low", "kind": "g high tercile − low tercile (FULL_RECIPE)", "k": kk,
               "g_high": float(sA.sum() / cA.sum()), "g_low": float(sB.sum() / cB.sum()),
               "n_anchors_high": int(mh.sum()), "n_anchors_low": int(ml.sum())})
    for bl in L.BLOCK_SENS:
        _, dr2 = L.boot_two_window(sA, cA, sB, cB, b=bl, seed_k=kk)
        r_[f"ci95_block{bl}"] = L.ci_p(hat, dr2)["ci95"]
    fam.append(r_)
    kk += 1
chk("family.size_matches_frozen_config", kk == L.N_GROUP_TESTS + len(L.COND_NAMES),
    {"k": kk, "expected": L.N_GROUP_TESTS + len(L.COND_NAMES)})
rej, thr = L.holm([f.get("p") for f in fam])
for f, r_, t_ in zip(fam, rej, thr):
    f["holm_reject_at_0.05"] = bool(r_)
    f["holm_threshold"] = t_
OUTJ["family_holm"] = {"m": len(fam), "alpha": 0.05, "tests": fam,
                       "n_rejected": int(sum(rej))}

# ── E: extreme anchors ──
gr = L1["g"]
idx_full = np.nonzero(mfull)[0]
gg = gr[idx_full]
n1 = max(1, int(round(0.01 * len(idx_full))))
ord_ = np.argsort(gg)
bot = idx_full[ord_[:n1]]
top = idx_full[ord_[-n1:]][::-1]


def anchor_detail(i):
    nm = NET[i]
    o = np.argsort(-np.abs(nm))[:10]
    names = [{"name": SY[j], "w": float(W[i, j]), "ret": float(RET[i, j]), "price": float(PRICE[i, j]),
              "funding_paid": float(FPAID[i, j]), "net": float(nm[j]),
              "in_member_set": bool(MEMB[i, j]), "in_life": bool(INLIFE[i, j]),
              "rn8_bp": (float(RN8[i, j] * 1e4) if np.isfinite(RN8[i, j]) else None),
              "mom30": (float(MOM30[i, j]) if np.isfinite(MOM30[i, j]) else None),
              "age_d": (float(AGE[i, j]) if np.isfinite(AGE[i, j]) else None),
              "king_share": float(SHARE[i, j])} for j in o]
    return {"anchor": L.utc(A[i]), "kind": ("combo" if KIND[i] == 2 else "king_file"),
            "phi": [float(PHI[i, 0]), float(PHI[i, 1])],
            "L1": {k: float(L1[k][i]) for k in ("g", "price", "funding_paid", "fee", "turnover")},
            "L1_events": {"stops": float(L1["nstop"][i]), "flattens": float(L1["dstop"][i]),
                          "halt": float(L1["halt"][i]), "hold": float(L1["hold"][i])},
            "L2": {"price": float(px_paper[i]), "funding_paid": float(fd_paper[i]), "net": float(net_paper[i]),
                   "market": float(MKT[i].sum()), "selection": float(SEL[i].sum()),
                   "A1_king": float(A1K[i]), "A1_fund": float(A1F[i]), "shape": float(SHP[i]),
                   "A2_king": float(A2K[i]), "A2_fund": float(A2F[i])},
            "resid": float(RESID[i]),
            "conditions": {cn: (float(COND[i, ci]) if np.isfinite(COND[i, ci]) else None) for ci, cn in enumerate(CONDN)},
            "condition_labels": {cn: int(CLAB[cn][i]) for cn in CONDN},
            "ubar_bps": (float(YBAR[i] * 1e4) if np.isfinite(YBAR[i]) else None),
            "n_members": int(MEMB[i].sum()), "n_held": int((W[i] != 0).sum()),
            "top10_names_by_abs_net": names}


def seg_extremes(width):
    c = np.convolve(np.where(mfull, gr, 0.0), np.ones(width), "valid")
    ok = np.convolve(mfull.astype(float), np.ones(width), "valid") == width
    c = np.where(ok, c, np.nan)
    if not np.isfinite(c).any():
        return {}
    b = int(np.nanargmin(c))
    t = int(np.nanargmax(c))
    return {"worst": {"from": L.utc(A[b]), "to": L.utc(A[b + width - 1]), "sum_g_bps": float(c[b]),
                      "nav_return_2x": float(np.prod(1 + L1["r"][b:b + width]) - 1)},
            "best": {"from": L.utc(A[t]), "to": L.utc(A[t + width - 1]), "sum_g_bps": float(c[t]),
                     "nav_return_2x": float(np.prod(1 + L1["r"][t:t + width]) - 1)}}


ydigit = np.array([time.strftime("%Y", time.gmtime(int(t))) for t in A])
OUTJ["block_E_extremes"] = {
    "definition": "top / bottom 1 % of FULL_RECIPE anchors by realised per-anchor g (path mean)",
    "n_each": int(n1),
    "year_counts_top": {y: int((ydigit[top] == y).sum()) for y in sorted(set(ydigit[top].tolist()))},
    "year_counts_bottom": {y: int((ydigit[bot] == y).sum()) for y in sorted(set(ydigit[bot].tolist()))},
    "top": [anchor_detail(int(i)) for i in top],
    "bottom": [anchor_detail(int(i)) for i in bot],
    "segments_3_anchors": seg_extremes(3),
    "segments_24h_6_anchors": seg_extremes(6),
}
# per-fill-path spread on the extreme anchors (path dispersion, prereg §3)
ppg = L1["per_path_g"]
OUTJ["block_E_extremes"]["path_spread"] = {
    "top": {"p05": float(np.percentile(ppg[:, top].mean(1), 5)), "p95": float(np.percentile(ppg[:, top].mean(1), 95)),
            "mean": float(ppg[:, top].mean())},
    "bottom": {"p05": float(np.percentile(ppg[:, bot].mean(1), 5)), "p95": float(np.percentile(ppg[:, bot].mean(1), 95)),
               "mean": float(ppg[:, bot].mean())}}

# ── F: 2023, with CI on every item ──
m23 = PERMASK["2023full"]
mref = PERMASK["2024"] | PERMASK["2025"] | PERMASK["2026"]


def ci_of(x, m, k):
    _, s, c = L.day_aggregate(A, x, m)
    dr = L.boot_mean_ratio(s, c, seed_k=k)
    return L.ci_p(float(s.sum() / c.sum()), dr)


items = {"g_realised": L1["g"], "price_realised": L1["price"], "funding_paid_realised": L1["funding_paid"],
         "fee_realised": L1["fee"], "price_paper": px_paper, "funding_paid_paper": fd_paper,
         "market": MKT.sum(1), "selection": SEL.sum(1), "selection_long": np.where(LONG, SEL, 0.0).sum(1),
         "selection_short": np.where(SHORT, SEL, 0.0).sum(1), "A1_king": A1K, "A1_fund": A1F,
         "A2_king": A2K, "A2_fund": A2F, "shape_residual": SHP, "exec_residual": RESID,
         "ubar_bps": YBAR * 1e4}
blockF = {"window": ["2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"], "n_anchors": int(m23.sum()), "items": {}}
for j, (nm, x) in enumerate(sorted(items.items())):
    blockF["items"][nm] = {"2023H2": ci_of(np.nan_to_num(x), m23, 100 + j),
                           "2024_2026_reference": ci_of(np.nan_to_num(x), mref, 200 + j)}
blockF["groups_2023_vs_reference"] = {}
for gname, bins in L.GROUP_SPECS:
    blockF["groups_2023_vs_reference"][gname] = {
        bn: {"net_2023H2": float(GS_CACHE[gname]["net"][m23, b].mean()),
             "net_reference": float(GS_CACHE[gname]["net"][mref, b].mean()),
             "gross_share_2023H2": float(GS_CACHE[gname]["gross"][m23, b].mean()),
             "gross_share_reference": float(GS_CACHE[gname]["gross"][mref, b].mean()),
             "price_2023H2": float(GS_CACHE[gname]["price"][m23, b].mean()),
             "funding_2023H2": float(GS_CACHE[gname]["fund"][m23, b].mean()),
             "selection_2023H2": float(GS_CACHE[gname]["sel"][m23, b].mean())}
        for b, bn in enumerate(bins)}
blockF["legs_2023H2"] = blockA["2023full"]
blockF["seat_history"] = {k: {"phi_fund_mean": float(PHI[m, 1].mean()), "share_king_file_anchors": float((KIND[m] == 1).mean())}
                          for k, m in PERMASK.items()}
OUTJ["block_F_2023"] = blockF

OUTJ["book_shape_by_period"] = {
    k: {"n_anchors": int(m.sum()), "kind_combo_share": float((KIND[m] == 2).mean()),
        "phi_fund_mean": float(PHI[m, 1].mean()), "n_held_mean": float((W[m] != 0).sum(1).mean()),
        "n_members_mean": float(MEMB[m].sum(1).mean()),
        "gross_out_of_life_share": float(np.abs(W[m])[~INLIFE[m]].sum() / np.abs(W[m]).sum()),
        "share_abs_p99": float(np.percentile(np.abs(SHARE[m][W[m] != 0]), 99))}
    for k, m in PERMASK.items()}

p = f"{OUT}/AT_ATTRIB.json"
tmp = p + ".tmp"
with open(tmp, "w") as f:
    json.dump(OUTJ, f, indent=1, default=str)
os.replace(tmp, p)
rec["outputs"] = {"attrib": {"path": p, "sha256": L.sha(p), "bytes": os.path.getsize(p)}}
v = L.write_receipt(rec, chk, f"{OUT}/AT_ATTRIB_RECEIPT.json", {"peak_rss_gb": L.rss_gb(), "runtime_s": round(time.time() - T0, 1)})
print("AT_ATTRIB VERDICT=%s checks=%d failed=%s" % (v, len(chk.rows), chk.fails), flush=True)
sys.exit(0 if v == "PASS" else 3)
