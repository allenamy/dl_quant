#!/usr/bin/env python3
"""at_supp.py — 冻结后追加, 探索性 (ADDED AFTER THE FREEZE, EXPLORATORY).

Everything this device computes is labelled that way in its output and must be read that way: it was written
AFTER the frozen blocks A–G of at_attrib had been computed and read, to answer follow-up questions the
prereg's own cuts raised. It introduces NO new data, NO new book and NO new statistic — only new cuts of the
same frozen L2 panel and the same frozen L1 series, with the same bin rules.

S1  characteristic × DIRECTION cross-tab (the prereg lists direction as a grouping of its own, not as a cross;
    a root-cause question about 2023 needs the cross, so it is added here and marked).
S2  per-UTC-month series: realised g / price / funding / fee / turnover, A1 king & fund, market & selection,
    the seat, the written-file kind, member count, DISP.
S3  name concentration per period: the 15 best and 15 worst names by total net contribution, the effective
    number of contributing names (Σ|c|)²/Σc², and the share carried by the worst / best 10.
S4  the seat counterfactual: A1_leg ≈ effective_share_leg × raw_leg_return; the effective shares of one
    period applied to another period's raw leg returns. Arithmetic on the reported quantities, NOT a re-run
    of any model and NOT a backtest of an alternative book.
S5  the numerical degeneracy of the prereg's A2 share split: the distribution of |s_i| and how much of
    A2_king − A1_king is carried by names with |s_i| above a threshold.

usage: python at_supp.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import at_lib as L

T0 = time.time()
ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
chk = L.Checks(T0)
rec = L.rec_head("at_supp.py", sys.argv)
rec["status"] = "冻结后追加, 探索性 — ADDED AFTER THE FREEZE, EXPLORATORY; not part of the preregistered deliverable"
chk("env.whitelist", not sorted(set(rec["env"]) - ENV_OK), {"extra": sorted(set(rec["env"]) - ENV_OK)})
PANP = f"{L.ROOT}/work/AT_PANEL.npz"
L1P = f"{L.ROOT}/work/AT_L1_mean.npz"
rec["upstream"] = {"panel": {"path": PANP, "sha256": L.sha(PANP)}, "L1_mean": {"path": L1P, "sha256": L.sha(L1P)},
                   "frozen_config": {"path": f"{L.ROOT}/RUN_CONFIG_attrib_2026-09-20.json", "sha256": L.sha(f"{L.ROOT}/RUN_CONFIG_attrib_2026-09-20.json")},
                   "frozen_result": {"path": f"{OUT}/AT_ATTRIB.json", "sha256": L.sha(f"{OUT}/AT_ATTRIB.json")}}

Z = np.load(PANP, allow_pickle=True)
L1 = np.load(L1P)
in_run = Z["in_run"]
A = Z["A"].astype(np.int64)[in_run]
SY = [str(s) for s in Z["symbols"]]
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
AGE = np.asarray(Z["AGE"], np.float64)[in_run]
RN8 = np.asarray(Z["RN8"], np.float64)[in_run]
MOM30 = np.asarray(Z["MOM30"], np.float64)[in_run]
LIQ = np.asarray(Z["LIQ"], np.float64)[in_run]
TBF = np.asarray(Z["TBF"], np.float64)[in_run]
COND = Z["COND"][in_run]
CONDN = [str(s) for s in Z["COND_NAMES"]]

PRICE = 1e4 * W * RET
FPAID = 1e4 * W * FUND
dW = np.vstack([W[:1], np.diff(W, axis=0)])
tot_dw = np.abs(dW).sum(1)
FEE = np.where(tot_dw[:, None] > 0, np.abs(dW) * (L1["fee"] / np.maximum(tot_dw, 1e-300))[:, None], 0.0)
NET = PRICE - FPAID - FEE
yb0 = np.where(np.isfinite(YBAR), YBAR, 0.0)
MKT = 1e4 * W * INLIFE * yb0[:, None]
SEL = 1e4 * W * INLIFE * (RET - yb0[:, None])
with np.errstate(all="ignore"):
    A1K = 1e4 * (AK * RET).sum(1) / LMIX
    A1F = 1e4 * (BF * RET).sum(1) / LMIX
    gk = np.abs(AK).sum(1)
    gf = np.abs(BF).sum(1)
    RAWK = np.where(gk > 0, 1e4 * (AK * RET).sum(1) / np.maximum(gk, 1e-300), np.nan)
    RAWF = np.where(gf > 0, 1e4 * (BF * RET).sum(1) / np.maximum(gf, 1e-300), np.nan)
A2K = (SHARE * PRICE).sum(1)
LONG = W > 0
SHORT = W < 0


def tercile_labels(X, memb):
    out = np.full(X.shape, -1, np.int8)
    for i in range(X.shape[0]):
        v = X[i][memb[i] & np.isfinite(X[i])]
        if v.size < 10:
            continue
        q1, q2 = np.quantile(v, [1 / 3, 2 / 3])
        row = X[i]
        out[i] = np.where(np.isfinite(row), np.where(row < q1, 0, np.where(row > q2, 2, 1)), -1)
    return out


LAB = {}
age_bin = np.full(AGE.shape, -1, np.int8)
edges = [0, 90, 180, 365, 730, np.inf]
for b in range(5):
    age_bin = np.where(np.isfinite(AGE) & (AGE >= edges[b]) & (AGE < edges[b + 1]), b, age_bin)
LAB["AGE"] = age_bin
rn_bp = RN8 * 1e4
fund_bin = np.full(RN8.shape, -1, np.int8)
for b, c in enumerate([(rn_bp <= -10), (rn_bp > -10) & (rn_bp < 0), (rn_bp >= 0) & (rn_bp < 0.999),
                       (rn_bp >= 0.999) & (rn_bp <= 1.001), (rn_bp > 1.001) & (rn_bp <= 5), (rn_bp > 5)]):
    fund_bin = np.where(np.isfinite(RN8) & c, b, fund_bin)
LAB["FUND"] = fund_bin
LAB["MOM30"] = tercile_labels(MOM30, MEMB)
LAB["LIQ"] = tercile_labels(LIQ, MEMB)
LAB["TBF"] = tercile_labels(TBF, MEMB)
BINS = {"AGE": L.AGE_BINS, "FUND": L.FUND_BINS, "MOM30": L.TER_BINS, "LIQ": L.TER_BINS, "TBF": L.TER_BINS}
PERMASK = {n: L.period_mask(A, lo, hi) for n, lo, hi, _ in L.PERIODS}
PERMASK = {k: v for k, v in PERMASK.items() if v.any()}
O = {"status": rec["status"]}

# ── S1: characteristic × direction ──
S1 = {}
for gname, bins in BINS.items():
    lab = LAB[gname]
    t = {}
    for b, bn in enumerate(bins):
        for dn, dm in (("long", LONG), ("short", SHORT)):
            sel = (lab == b) & dm
            key = f"{bn}|{dn}"
            t[key] = {}
            for pk, pm in PERMASK.items():
                t[key][pk] = {"net": float(np.where(sel, NET, 0.0)[pm].sum(1).mean()),
                              "price": float(np.where(sel, PRICE, 0.0)[pm].sum(1).mean()),
                              "selection": float(np.where(sel, SEL, 0.0)[pm].sum(1).mean()),
                              "funding_paid": float(np.where(sel, FPAID, 0.0)[pm].sum(1).mean()),
                              "gross_share": float(np.where(sel, np.abs(W), 0.0)[pm].sum(1).mean())}
    S1[gname] = t
O["S1_characteristic_x_direction"] = S1

# ── S2: monthly series ──
mon = np.array([time.strftime("%Y-%m", time.gmtime(int(t))) for t in A])
S2 = {}
for m_ in sorted(set(mon.tolist())):
    k = mon == m_
    S2[m_] = {"n_anchors": int(k.sum()),
              "g": float(L1["g"][k].mean()), "price": float(L1["price"][k].mean()),
              "funding_paid": float(L1["funding_paid"][k].mean()), "fee": float(L1["fee"][k].mean()),
              "turnover": float(L1["turnover"][k].mean()),
              "nav_return_2x": float(np.prod(1 + L1["r"][k]) - 1),
              "A1_king": float(A1K[k].mean()), "A1_fund": float(A1F[k].mean()),
              "raw_king": float(np.nanmean(RAWK[k])) if np.isfinite(RAWK[k]).any() else None,
              "raw_fund": float(np.nanmean(RAWF[k])) if np.isfinite(RAWF[k]).any() else None,
              "market": float(MKT[k].sum(1).mean()), "selection": float(SEL[k].sum(1).mean()),
              "phi_fund": float(PHI[k, 1].mean()), "combo_share": float((KIND[k] == 2).mean()),
              "n_members": float(MEMB[k].sum(1).mean()), "n_held": float((W[k] != 0).sum(1).mean()),
              "DISP": float(np.nanmean(COND[k, CONDN.index("DISP")])),
              "FDISP": float(np.nanmean(COND[k, CONDN.index("FDISP")])),
              "ubar_bps": float(np.nanmean(YBAR[k]) * 1e4),
              "stops": float(L1["nstop"][k].sum()), "flattens": float(L1["dstop"][k].sum()), "halts": float(L1["halt"][k].sum())}
O["S2_monthly"] = S2

# ── S3: name concentration ──
S3 = {}
for pk, pm in PERMASK.items():
    c = NET[pm].sum(0) / max(int(pm.sum()), 1)        # bps per anchor of the period, per name
    o = np.argsort(c)
    eff = float((np.abs(c).sum() ** 2) / max(float((c ** 2).sum()), 1e-300))
    S3[pk] = {"total_net": float(c.sum()), "effective_n_names": eff,
              "n_names_touched": int((np.abs(NET[pm]).sum(0) > 0).sum()),
              "worst15": [[SY[j], float(c[j])] for j in o[:15]],
              "best15": [[SY[j], float(c[j])] for j in o[::-1][:15]],
              "worst10_sum": float(c[o[:10]].sum()), "best10_sum": float(c[o[::-1][:10]].sum())}
O["S3_name_concentration"] = S3

# ── S4: seat counterfactual (arithmetic on reported quantities only) ──
S4 = {}
for pk, pm in PERMASK.items():
    rk = float(np.nanmean(RAWK[pm])) if np.isfinite(RAWK[pm]).any() else None
    rf = float(np.nanmean(RAWF[pm])) if np.isfinite(RAWF[pm]).any() else None
    ak, af = float(A1K[pm].mean()), float(A1F[pm].mean())
    S4[pk] = {"raw_king": rk, "raw_fund": rf, "A1_king": ak, "A1_fund": af,
              "effective_share_king": (ak / rk if rk not in (None, 0) and abs(rk) > 1e-9 else None),
              "effective_share_fund": (af / rf if rf not in (None, 0) and abs(rf) > 1e-9 else None)}
for src, dst in (("HIST", "2026"), ("2026", "HIST"), ("HIST", "2023full")):
    s, d = S4[src], S4[dst]
    if None in (s["effective_share_king"], s["effective_share_fund"], d["raw_king"], d["raw_fund"]):
        continue
    O.setdefault("S4_seat_counterfactual", {})[f"{dst}_raw_with_{src}_shares"] = {
        "price_bps": s["effective_share_king"] * d["raw_king"] + s["effective_share_fund"] * d["raw_fund"],
        "actual_price_bps": d["A1_king"] + d["A1_fund"],
        "caveat": "arithmetic identity A1_leg = effective_share × raw_leg applied across periods; NOT a re-run, NOT a backtest of an alternative seat rule"}
O["S4_leg_shares_and_raw"] = S4

# ── S5: the A2 share degeneracy ──
held = W != 0
s_abs = np.abs(SHARE[held])
S5 = {"share_abs_quantiles": {q: float(np.quantile(s_abs, q / 100.0)) for q in (50, 90, 99, 99.9, 100)},
      "share_share_outside_0_1": float(((SHARE[held] < 0) | (SHARE[held] > 1)).mean()), "periods": {}}
for pk, pm in PERMASK.items():
    big = np.abs(SHARE) > 3.0
    contrib_big = float(np.where(big, SHARE * PRICE, 0.0)[pm].sum(1).mean())
    S5["periods"][pk] = {"A2_king": float(A2K[pm].mean()), "A1_king": float(A1K[pm].mean()),
                         "A2_minus_A1_king": float((A2K - A1K)[pm].mean()),
                         "of_which_from_names_with_abs_share_gt_3": contrib_big,
                         "share_abs_p99": float(np.percentile(np.abs(SHARE[pm][W[pm] != 0]), 99)),
                         "share_abs_max": float(np.abs(SHARE[pm][W[pm] != 0]).max())}
O["S5_A2_share_degeneracy"] = S5

# ── S6 / S7: the contemporaneity defect in the prereg's condition list ──
# UBAR as frozen is ȳ(E) = the member universe's return over the SAME (E, E+4h] window the book is paid on.
# It is therefore NOT a state known at the decision; every "g by UBAR bucket" number is a same-window
# accounting relation, not a regime read, and it cannot be used for persistence. Reported as computed (the
# frozen definition), plus here: S6 = the joint over the five conditions that ARE causal and are labelled to
# the axis end; S7 = the causal counterpart ȳ(E−4h), terciled by the same expanding-window rule.
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


ZF = np.load(PANP, allow_pickle=True)
A_full = ZF["A"].astype(np.int64)
G0L_full = ZF["G0L"]
GV = [str(s) for s in ZF["G0_VARS"]]
CAUSAL5 = ["DISP", "FDISP", "FLEVEL", "BREADTH", "VOL"]
LAB5 = np.stack([G0L_full[:, GV.index(L.COND_FROM_G0[c])] for c in CAUSAL5], 1)
ok5 = (LAB5 >= 0).all(1)
key5 = np.where(ok5, (LAB5 * (3 ** np.arange(5))[None, :]).sum(1), -1)
li5 = int(np.nonzero(ok5)[0][-1])
BUCK = ("low", "mid", "high")
mfull_full = L.period_mask(A_full, "2023-06-30T04:00:00Z", "2026-08-31T00:00:00Z")
inr = ZF["in_run"]


def runs_of(m):
    d = np.diff(np.concatenate([[0], m.astype(np.int8), [0]]))
    return np.nonzero(d == -1)[0] - np.nonzero(d == 1)[0]


def gstat(mask_full):
    mr = mask_full[inr] & mfull_full[inr]
    if mr.sum() < 2:
        return {"n_anchors": int(mr.sum())}
    _, s, c = L.day_aggregate(A, L1["g"], mr)
    return {"n_anchors": int(mr.sum()), "g": float(s.sum() / c.sum())}


mc5 = np.where(ok5, (LAB5 == LAB5[li5][None, :]).sum(1), -1)
S6 = {"conditions": CAUSAL5, "at_anchor": L.utc(A_full[li5]), "is_axis_end": bool(li5 == len(A_full) - 1),
      "buckets": {c: BUCK[int(LAB5[li5, i])] for i, c in enumerate(CAUSAL5)},
      "joint": {"n_anchors": int((key5 == key5[li5]).sum()), "n_episodes": int(len(runs_of(key5 == key5[li5]))),
                **gstat(key5 == key5[li5])},
      "runs_of_this_combination_days": ([float(x) / 6.0 for x in np.percentile(runs_of(key5 == key5[li5]), [50, 90])]
                                        if len(runs_of(key5 == key5[li5])) else None),
      "match_profile": {str(k): {"n_anchors": int((mc5 == k).sum()), **gstat(mc5 == k)} for k in range(6)},
      "persistence_of_this_exact_combination": {}}
for hd, ha in ((7, 42), (30, 180), (90, 540)):
    src = np.nonzero(key5 == key5[li5])[0]
    src = src[src + ha < len(A_full)]
    src = src[ok5[src + ha]]
    S6["persistence_of_this_exact_combination"][f"+{hd}d"] = (
        {"n": int(len(src)), "share_same": float((key5[src + ha] == key5[li5]).mean())} if len(src) else {"n": 0})
S6["per_condition_persistence_note"] = "see the frozen AT_REGIME.json block for each condition on its own"
O["S6_joint_over_the_five_causal_states"] = S6

YB_full = ZF["YBAR"]
ubar_prev = np.concatenate([[np.nan], YB_full[:-1]])
lab_prev = expanding_terciles(ubar_prev)
S7 = {"definition": "UBAR_prev = ȳ(E − 4h), the member universe's PREVIOUS 4h return — causal, unlike the frozen UBAR = ȳ(E)",
      "cells_FULL_RECIPE": {}}
for b, bn in enumerate(BUCK):
    m = (lab_prev == b)
    S7["cells_FULL_RECIPE"][bn] = gstat(m)
    mr = m[inr] & mfull_full[inr]
    if mr.sum() >= 2:
        S7["cells_FULL_RECIPE"][bn]["selection"] = float(SEL[mr].sum(1).mean())
        S7["cells_FULL_RECIPE"][bn]["price"] = float(L1["price"][mr].mean())
        S7["cells_FULL_RECIPE"][bn]["funding_paid"] = float(L1["funding_paid"][mr].mean())
r_ = runs_of(lab_prev == 2)
S7["run_lengths_high_days"] = ({"n_runs": int(len(r_)), "median": float(np.median(r_)) / 6.0,
                                "p90": float(np.percentile(r_, 90)) / 6.0} if len(r_) else None)
S7["current_bucket_2026-09-18T20Z"] = (BUCK[int(lab_prev[-1])] if lab_prev[-1] >= 0 else "unlabelled")
O["S7_causal_ubar"] = S7

chk("supp.identity_group_sums", float(np.abs(sum(np.where((LAB["AGE"] == b), NET, 0.0).sum(1) for b in range(5))
                                              + np.where(LAB["AGE"] < 0, NET, 0.0).sum(1) - NET.sum(1)).max()) < 1e-9, {})
chk("supp.causal5_labelled_to_axis_end", bool(ok5[-1]), {"last": L.utc(A_full[li5])})
p = f"{OUT}/AT_SUPP.json"
with open(p + ".tmp", "w") as f:
    json.dump(O, f, indent=1, default=str)
os.replace(p + ".tmp", p)
rec["outputs"] = {"supp": {"path": p, "sha256": L.sha(p)}}
v = L.write_receipt(rec, chk, f"{OUT}/AT_SUPP_RECEIPT.json", {"peak_rss_gb": L.rss_gb(), "runtime_s": round(time.time() - T0, 1)})
print("AT_SUPP VERDICT=%s (冻结后追加, 探索性) checks=%d failed=%s" % (v, len(chk.rows), chk.fails), flush=True)
sys.exit(0 if v == "PASS" else 3)
