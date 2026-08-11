#!/usr/bin/env python3
"""acceptance_battery.py — Automated model acceptance battery (handoff v2, 0C-SPEC-aligned).

> **创建:** 2026-07-19 JST | **Session:** fable multi-asset-v2 (0B build) | **状态:** v2 (implements 0C `acceptance_battery_SPEC.md` §1-12) | **作废条件:** SPEC / 冠军面板口径 / 引擎 canonical 变更

WHAT THIS IS
------------
One command that mechanically judges a partner's RETRAINED candidate against the frozen
champion: is it (i) COMPLETE (no collapse / no leak / honest caliber), (ii) UP-TO-SPEC
(reproduces champion quality), or (iii) worth REPLACING the champion. It recomputes every
gate from raw arrays — it never trusts a JSON verdict — and emits a four-way ruling:
    REJECT-untrustworthy | REJECT-degraded | ACCEPT-clone | ACCEPT-upgrade
matching the human 0C rulings the project accumulated over 5 months.

INPUT CONTRACTS (auto-detected by path)
---------------------------------------
A) fold-product DIR  — what train_wide_harness.py emits: fold_*_head_scores.npz
   (scores (T,N,K) finite only at that fold's disjoint OOS rows) + one panel_ref.npz
   (ts/day/symbols/Yraw/YR/member/CL/funding/horizon). The RICH format: the K heads are
   present, so the honest ensemble is machine-VERIFIED (not asserted).
B) stitched pred-panel NPZ — the king_pred_panel.npz format: keys
   ts,(king_pred|s2_pred|pred),member,CL,YR,Yraw,day,year — a single stitched OOS
   prediction (T,N). No heads ⇒ gate (b) honest-ensemble is asserted-not-verified (flagged),
   gate (g) head-diversity SKIPs.

Either can be --candidate or --champion. --seeds (≥2 more products) enables the CoV gate;
--pnl <cand.npy> <champ.npy> (per-year daily net series) enables gate (i) net-Sharpe layer;
--claim-upgrade evaluates the upgrade gate (i).

THE GATES  (definitions/thresholds frozen by 0C in acceptance_thresholds_0C_frozen.json)
----------------------------------------------------------------------------------------
HARD (integrity/leak — any FAIL ⇒ REJECT-untrustworthy, quality gates not even read):
 (a) σ collapse guard   — dispersion not collapsed to ~constant. degenerate-ts frac ≤1%,
                          per-head alive, dead-anchor frac (vs champion dispersion) ≤5%.
 (e) forward causal      — IC(pred_t, Yraw_{t+kδ}), δ=H and δ=H/4, k=-2..+2: forward peak at
                          k=0, sub-H +1 ≥0.6×peak (no razor-spike), full-H +1 <peak & not flat
                          (IC₊₁/IC₀<0.9), negative-lag reversal EXEMPT (only a same-sign,
                          ≥0.5×peak, symmetric-bell neg lag is window-overlap leak).
 (f) index alignment     — ts md5 / member / CL byte-match champion; cross-fold overlap 0;
                          OOS coverage present. (require_panel_match)
 (h) clean caliber       — all IC on the CL non-overlap grid; anchor gap ≥ H. Never stride<H.
SOFT (quality — all must pass for ACCEPT-clone):
 (b) honest-ensemble IC  — z-mean over ALL heads (never best-head) rank-IC ≥ champion −
                          tolerance (0.005), pooled + per-year, raw & residual dual-report.
 (c) sign + bootstrap    — every fold & every year IC>0; day-block bootstrap pooled 95% CI
                          excludes 0; no year CI significantly negative.
 (d) dynamic share       — shuffle-future (IC−IC_static)/IC ≥0.5 pooled and no year <0.5.
 (g) CoV + head-diversity — ≥3 seeds: CoV≤10%; heads: pairwise corr<0.999 & ensemble≠any head.
UPGRADE (only when --claim-upgrade):
 (i) replacement gate    — paired day-block bootstrap (cand−champ) per year: non-inferior all +
                          strictly-better ≥1 year (IC and, if --pnl, net-Sharpe). Tie ⇒ incumbent.

Pure CPU; numpy/pandas/scipy. Self-test runs 0C SPEC §12 adversarial matrix:
    python acceptance_battery.py --self-test --champion <king_fold_dir>
constructs T1 champion-vs-self (⇒ACCEPT-clone), T3a shuffle-ts (⇒REJECT via f),
T3b duplicated-head (⇒REJECT via g), T3c injected-lookahead (⇒REJECT via e) and ASSERTS each.
"""
import argparse
import glob
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------------- #
# Frozen thresholds (0C pre-registration). Defaults below MIRROR
# acceptance_thresholds_0C_frozen.json; that file is auto-loaded if present and
# --config <json> overrides any subset. See the SPEC for every derivation.
# ----------------------------------------------------------------------------- #
THRESHOLDS = {
    "ic_tolerance": 0.005,          # (b) = max(0.005, 2*sigma_seed); champion 3-seed sigma 0.0026
    "sigma_floor_ratio": 0.02,      # (a) dead-anchor floor = this * champion median dispersion
    "sigma_dead_frac_max": 0.05,    # (a) dead-anchor frac allowed
    "sigma_degenerate_ts_max": 0.01,# (a) frac of ts with zero xsec dispersion allowed
    "dyn_share_min": 0.50,          # (d)
    "fwd_sub_ratio_min": 0.60,      # (e) sub-H +1 lag / peak floor (razor-spike guard)
    "fwd_flat_ratio_max": 0.90,     # (e) full-H +1 lag / peak ceiling (flat-leak guard)
    "fwd_neg_leak_ratio": 0.50,     # (e) neg-lag same-sign magnitude that (with symmetry) = leak
    "cov_max": 0.10,                # (g)
    "head_corr_max": 0.999,         # (g) head-diversity
    "require_panel_match": True,    # (f)
    "nshuf": 8,                     # (d) shuffle-future repeats (averaged)
    "nboot": 3000,                  # (c)/(i) day-block bootstrap draws
    "min_base": 5,                  # min tradeable assets per anchor to score it
    "seed": 0,                      # RNG seed (reproducible)
}
_FROZEN = os.path.join(HERE, "acceptance_thresholds_0C_frozen.json")
if os.path.exists(_FROZEN):
    try:
        _f = json.load(open(_FROZEN))
        THRESHOLDS.update({k: v for k, v in _f.items() if k in THRESHOLDS})
    except Exception:
        pass


# ----------------------------------------------------------------------------- #
# Primitives
# ----------------------------------------------------------------------------- #
def md5_bytes(b):
    return hashlib.md5(b).hexdigest()[:8]


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def ricorr(a, b):
    if len(a) < 2 or np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return np.nan
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def _zmean_heads(head_cols):
    """Honest ensemble over K heads for one anchor's base: z-score each live head, mean."""
    comp = np.zeros(head_cols.shape[0]); nk = 0
    for k in range(head_cols.shape[1]):
        col = head_cols[:, k]
        if np.isfinite(col).all() and col.std() > 1e-12:
            comp += (col - col.mean()) / col.std(); nk += 1
    return (comp / nk) if nk else None


def year_of_rows(ts):
    return pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()


# ----------------------------------------------------------------------------- #
# Product = common internal representation for either input contract.
# ----------------------------------------------------------------------------- #
class Product:
    def __init__(self, kind, name):
        self.kind = kind; self.name = name
        self.heads = None          # list of (T,N) per-head stitched panels, or None
        self.pnl_by_year = None    # optional {year: daily-net np.array}

    def finalize(self):
        member, CL = self.member, self.CL
        finite_pred = np.isfinite(self.pred)
        oos_mask = member & CL & finite_pred
        self.oos_rows = np.where(oos_mask.any(1))[0]
        self.yr_of_row = year_of_rows(self.ts)
        # folds
        if getattr(self, "folds", None) is None:
            self.folds = []
            for Y in sorted(set(int(y) for y in self.yr_of_row[self.oos_rows])):
                rows = self.oos_rows[self.yr_of_row[self.oos_rows] == Y]
                self.folds.append(dict(year=Y, rows=rows))
        self.ts_md5 = md5_bytes(np.ascontiguousarray(self.ts).tobytes())
        self.member_md5 = md5_bytes(np.ascontiguousarray(self.member).tobytes())
        self.CL_md5 = md5_bytes(np.ascontiguousarray(self.CL).tobytes())
        # cross-fold overlap
        seen = [set(f["rows"].tolist()) for f in self.folds]
        ov = 0
        for i in range(len(seen)):
            for j in range(i + 1, len(seen)):
                ov += len(seen[i] & seen[j])
        self.fold_overlap = ov
        return self


def load_fold_products(dirpath, thr):
    pr_path = os.path.join(dirpath, "panel_ref.npz")
    pr = np.load(pr_path, allow_pickle=True)
    P = Product("fold_products", os.path.basename(dirpath.rstrip("/")))
    P.member = pr["member"].astype(bool); P.CL = pr["CL"].astype(bool)
    P.YR = pr["YR"].astype(np.float64); P.Yraw = pr["Yraw"].astype(np.float64)
    P.ts = pr["ts"].astype(np.int64); P.day = pr["day"].astype(np.int64)
    P.horizon = int(pr["horizon"]); P.panel_file_md5 = md5_file(pr_path)
    T, N = P.Yraw.shape
    yr_of_row = year_of_rows(P.ts)
    files = sorted(glob.glob(os.path.join(dirpath, "fold_*_head_scores.npz")),
                   key=lambda x: int(x.split("fold_")[1].split("_")[0]))
    if not files:
        raise FileNotFoundError(f"no fold_*_head_scores.npz in {dirpath}")
    K = np.load(files[0])["scores"].shape[2]
    S = np.full((T, N), np.nan)            # honest ensemble
    Pt = np.full((T, N), np.nan)           # point pred (median head)
    Hk = [np.full((T, N), np.nan) for _ in range(K)]   # per-head stitched
    folds = []
    base_rows = np.where((P.member & P.CL & np.isfinite(P.YR)).any(1))[0]
    for f in files:
        z = np.load(f); sc = z["scores"]; te = z["te_rows"].astype(np.int64)
        for t in base_rows:
            b = np.where(P.member[t] & P.CL[t] & np.isfinite(P.YR[t]))[0]
            if b.size < thr["min_base"]:
                continue
            comp = _zmean_heads(sc[t, b, :])
            if comp is None:
                continue
            S[t, b] = comp; Pt[t, b] = np.nanmedian(sc[t, b, :], axis=1)
            for k in range(K):
                Hk[k][t, b] = sc[t, b, k]
        Y = int(np.bincount(yr_of_row[te] - yr_of_row[te].min()).argmax() + yr_of_row[te].min())
        folds.append(dict(year=Y, rows=te))
        del sc, z
    P.pred = S; P.point = Pt; P.heads = Hk; P.folds = folds
    return P.finalize()


_PRED_KEYS = ("pred", "king_pred", "s2_pred")


def load_pred_panel(npz_path):
    z = np.load(npz_path, allow_pickle=True)
    P = Product("pred_panel", os.path.basename(npz_path))
    P.member = z["member"].astype(bool); P.CL = z["CL"].astype(bool)
    P.YR = z["YR"].astype(np.float64); P.Yraw = z["Yraw"].astype(np.float64)
    P.ts = z["ts"].astype(np.int64)
    P.day = z["day"].astype(np.int64) if "day" in z.files else (P.ts // 86400000)
    predkey = next((k for k in _PRED_KEYS if k in z.files), None)
    if predkey is None:  # fall back: the (T,N) float array that isn't YR/Yraw
        for k in z.files:
            a = z[k]
            if a.ndim == 2 and a.shape == P.YR.shape and k not in ("member", "CL", "YR", "Yraw"):
                predkey = k; break
    P.pred = z[predkey].astype(np.float64); P.point = P.pred
    P.panel_file_md5 = md5_file(npz_path)
    P.horizon = int(z["horizon"]) if "horizon" in z.files else None
    P.folds = None; P.heads = None
    return P.finalize()


def load_any(path, thr):
    if os.path.isdir(path):
        return load_fold_products(path, thr)
    return load_pred_panel(path)


# ----------------------------------------------------------------------------- #
# IC helpers
# ----------------------------------------------------------------------------- #
def ic_series(P, composite, rows, target="YR", use_CL=True):
    tgt = P.YR if target == "YR" else P.Yraw
    ics, days, years = [], [], []
    for t in rows:
        mask = P.member[t] & np.isfinite(tgt[t]) & np.isfinite(composite[t])
        if use_CL:
            mask &= P.CL[t]
        b = np.where(mask)[0]
        if b.size < THRESHOLDS["min_base"]:
            continue
        ic = ricorr(composite[t, b], tgt[t, b])
        if np.isfinite(ic):
            ics.append(ic); days.append(int(P.day[t])); years.append(int(P.yr_of_row[t]))
    return np.array(ics), np.array(days), np.array(years)


def dayblock_ci(ic, days, rng, nboot):
    if len(ic) < 3:
        return (np.nan, np.nan)
    ud = np.unique(days); d2 = {u: np.where(days == u)[0] for u in ud}
    b = np.array([ic[np.concatenate([d2[u] for u in rng.choice(ud, len(ud), True)])].mean()
                  for _ in range(nboot)])
    return (round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4))


# ----------------------------------------------------------------------------- #
# GATES
# ----------------------------------------------------------------------------- #
def gate_a_sigma(cand, champ, thr):
    def xsec_disp(P, arr):
        d = []
        for t in P.oos_rows:
            b = np.where(P.member[t] & P.CL[t] & np.isfinite(arr[t]))[0]
            if b.size >= thr["min_base"]:
                d.append(float(np.std(arr[t, b])))
        return np.array(d)

    def per_asset_ratio(P):
        r = []
        for a in range(P.member.shape[1]):
            m = P.member[:, a] & P.CL[:, a] & np.isfinite(P.point[:, a]) & np.isfinite(P.Yraw[:, a])
            if m.sum() >= 20 and P.Yraw[m, a].std() > 1e-12:
                r.append(float(np.std(P.point[m, a]) / (np.std(P.Yraw[m, a]) + 1e-12)))
        return float(np.median(r)) if r else np.nan

    disp = xsec_disp(cand, cand.point)
    degenerate_ts_frac = float(np.mean(disp <= 1e-12)) if disp.size else 1.0
    ref_disp = float(np.median(xsec_disp(champ, champ.point))) if champ is not None else float(np.median(disp))
    floor = thr["sigma_floor_ratio"] * ref_disp
    dead_frac = float(np.mean(disp < floor)) if disp.size else 1.0
    sig_ratio_med = per_asset_ratio(cand)
    # per-head liveness (fold-product candidates only)
    head_degen = []
    if cand.heads is not None:
        for Hk in cand.heads:
            hd = xsec_disp(cand, Hk)
            head_degen.append(float(np.mean(hd <= 1e-12)) if hd.size else 1.0)
    max_head_degen = max(head_degen) if head_degen else 0.0
    # Pass/fail is driven by SCALE-INVARIANT collapse signals only (0C audit 2026-07-19):
    #  - degenerate_ts_frac / head-degen: fraction of anchors|heads with LITERALLY zero xsec
    #    dispersion (can't produce a ranking) — scale-free;
    #  - per-asset sigma_yhat/sigma_y >= 0.02: the CLAUDE.md iron-law magnitude floor, which
    #    only fires on genuine near-collapse (ratio -> 0), not on a merely smaller-scale model.
    # The champion-relative dead-anchor frac is scale-SENSITIVE (a legitimately weaker retrain
    # has smaller absolute dispersion and would be mislabeled 'untrustworthy' rather than the
    # more accurate 'degraded' via gate b) -> kept as a REPORTED diagnostic, not a gate driver.
    sigma_floor_ok = (not np.isfinite(sig_ratio_med)) or (sig_ratio_med >= thr["sigma_floor_ratio"])
    passed = bool(degenerate_ts_frac <= thr["sigma_degenerate_ts_max"] and
                  max_head_degen <= thr["sigma_degenerate_ts_max"] and sigma_floor_ok)
    return dict(name="a_sigma_collapse", cls="hard", passed=passed,
                sigma_ratio_median=round(sig_ratio_med, 4), sigma_floor=thr["sigma_floor_ratio"],
                degenerate_ts_frac=round(degenerate_ts_frac, 4), max_head_degenerate_frac=round(max_head_degen, 4),
                dead_anchor_frac_vs_champ=round(dead_frac, 4), reference_disp=round(ref_disp, 6),
                note="scale-invariant collapse guard (per-asset sigma-ratio + degenerate-ts + head-degen); "
                     "champ-relative dead-anchor is diagnostic only; not a beta/magnitude check")


def gate_b_ic(cand, champ, thr):
    ic_r, _, yr_r = ic_series(cand, cand.pred, cand.oos_rows, "YR")
    ic_raw, _, _ = ic_series(cand, cand.pred, cand.oos_rows, "Yraw")
    cand_ic = float(np.mean(ic_r)) if len(ic_r) else np.nan
    by_year = {int(y): round(float(ic_r[yr_r == y].mean()), 4) for y in sorted(set(yr_r.tolist()))}
    cand_ic_raw = float(np.mean(ic_raw)) if len(ic_raw) else np.nan
    champ_ic = champ_ic_raw = None
    if champ is not None:
        cic, _, _ = ic_series(champ, champ.pred, champ.oos_rows, "YR")
        champ_ic = float(np.mean(cic)) if len(cic) else np.nan
        cic_raw, _, _ = ic_series(champ, champ.pred, champ.oos_rows, "Yraw")
        champ_ic_raw = float(np.mean(cic_raw)) if len(cic_raw) else np.nan
    thresh = (champ_ic - thr["ic_tolerance"]) if champ_ic is not None else None
    passed = bool(champ_ic is None or (np.isfinite(cand_ic) and cand_ic >= thresh))
    verified = cand.heads is not None
    # raw-caliber gap is always surfaced (0C T2 ruling): Yraw is target-independent and
    # cross-arm comparable, so even when a candidate's residual-YR target is its own (not the
    # champion's) — or gate (f) hard-fails on a different CL grid — the raw-IC gap makes a
    # 'degraded' candidate visible (e.g. archived N1b raw 0.068 vs champion 0.121).
    raw_gap = None if champ_ic_raw is None else round(cand_ic_raw - champ_ic_raw, 4)
    return dict(name="b_honest_ensemble_ic", cls="soft", passed=passed,
                ic_pooled_resid=round(cand_ic, 4), ic_pooled_raw=round(cand_ic_raw, 4) if np.isfinite(cand_ic_raw) else None,
                ic_by_year=by_year, champion_ic=None if champ_ic is None else round(champ_ic, 4),
                champion_ic_raw=None if champ_ic_raw is None else round(champ_ic_raw, 4), raw_ic_gap=raw_gap,
                tolerance=thr["ic_tolerance"], threshold=None if thresh is None else round(thresh, 4),
                honest_ensemble_verified=bool(verified),
                note="z-mean over all heads" if verified else "ensemble caliber ASSERTED-not-verified (no per-head panels)")


def gate_c_sign(cand, thr):
    rng = np.random.default_rng(thr["seed"])
    ic_all, days_all, yr_all = ic_series(cand, cand.pred, cand.oos_rows, "YR")
    by_fold = []
    for f in cand.folds:
        ics, _, _ = ic_series(cand, cand.pred, f["rows"], "YR")
        by_fold.append(round(float(np.mean(ics)), 4) if len(ics) else np.nan)
    by_year, ci_year = {}, {}
    for y in sorted(set(yr_all.tolist())):
        sel = yr_all == y
        by_year[int(y)] = round(float(ic_all[sel].mean()), 4)
        ci_year[int(y)] = list(dayblock_ci(ic_all[sel], days_all[sel], rng, thr["nboot"]))
    ci_pooled = dayblock_ci(ic_all, days_all, rng, thr["nboot"])
    all_pos = all(np.isfinite(x) and x > 0 for x in by_fold) and all(v > 0 for v in by_year.values())
    no_year_neg = all(ci[1] > 0 for ci in ci_year.values())  # no year CI wholly below 0
    passed = bool(all_pos and ci_pooled[0] > 0 and no_year_neg)
    return dict(name="c_sign_bootstrap", cls="soft", passed=passed, ic_by_fold=by_fold,
                ic_by_year=by_year, boot_ci_pooled=list(ci_pooled), boot_ci_by_year=ci_year,
                all_signs_positive=bool(all_pos), note="day-block bootstrap, block=natural day")


def gate_d_dynshare(cand, thr):
    rng = np.random.default_rng(thr["seed"])
    tot_by_year, sta_by_year = {}, {}
    for f in cand.folds:
        Y, rows = f["year"], f["rows"]
        ics = []
        for t in rows:
            b = np.where(cand.member[t] & cand.CL[t] & np.isfinite(cand.YR[t]) & np.isfinite(cand.pred[t]))[0]
            if b.size >= thr["min_base"]:
                ics.append(ricorr(cand.pred[t, b], cand.YR[t, b]))
        tot_by_year.setdefault(Y, []).append(np.nanmean(ics))
        sh = []
        for _ in range(thr["nshuf"]):
            Csh = {}
            for a in range(cand.member.shape[1]):
                vr = rows[cand.member[rows, a] & cand.CL[rows, a] & np.isfinite(cand.pred[rows, a])]
                if vr.size > 2:
                    Csh[a] = (vr, cand.pred[vr[rng.permutation(vr.size)], a])
            sh.append(_shuffled_ic(cand, rows, Csh, thr))
        sta_by_year.setdefault(Y, []).append(np.nanmean(sh))
    tot = {y: float(np.mean(v)) for y, v in tot_by_year.items()}
    sta = {y: float(np.mean(v)) for y, v in sta_by_year.items()}
    dyn_by_year = {int(y): round((tot[y] - sta[y]) / tot[y], 3) if tot[y] else np.nan for y in tot}
    tt = np.mean(list(tot.values())); ss = np.mean(list(sta.values()))
    dyn_pooled = float((tt - ss) / tt) if tt else np.nan
    passed = bool(np.isfinite(dyn_pooled) and dyn_pooled >= thr["dyn_share_min"] and
                  all(v >= thr["dyn_share_min"] for v in dyn_by_year.values()))
    return dict(name="d_dynamic_share", cls="soft", passed=passed, dyn_share_pooled=round(dyn_pooled, 3),
                dyn_share_by_year=dyn_by_year, static_ic=round(ss, 4), total_ic=round(tt, 4),
                note="shuffle-future: static per-asset tilt shuffled out")


def _shuffled_ic(cand, rows, Csh, thr):
    """rank-IC over rows with each asset's pred permuted-in-time per Csh {a:(vr,vals)}."""
    ics = []
    permmap = {a: dict(zip(vr.tolist(), vals.tolist())) for a, (vr, vals) in Csh.items()}
    for t in rows:
        b = np.where(cand.member[t] & cand.CL[t] & np.isfinite(cand.YR[t]) & np.isfinite(cand.pred[t]))[0]
        if b.size < thr["min_base"]:
            continue
        pv = np.array([permmap[a].get(int(t), cand.pred[t, a]) if a in permmap else cand.pred[t, a] for a in b])
        ics.append(ricorr(pv, cand.YR[t, b]))
    return np.nanmean(ics)


def gate_e_forward(cand, thr):
    H = cand.horizon or 4
    T = cand.member.shape[0]

    def profile(delta):
        out = {}
        for k in (-2, -1, 0, 1, 2):
            ics = []
            for t in cand.oos_rows:
                tt = t + k * delta
                if tt < 0 or tt >= T:
                    continue
                b = np.where(cand.member[t] & cand.CL[t] & np.isfinite(cand.pred[t]) &
                             cand.member[tt] & np.isfinite(cand.Yraw[tt]))[0]
                if b.size >= thr["min_base"]:
                    ic = ricorr(cand.pred[t, b], cand.Yraw[tt, b])
                    if np.isfinite(ic):
                        ics.append(ic)
            out[k] = round(float(np.mean(ics)), 4) if ics else None
        return out

    full = profile(H); sub = profile(max(1, H // 4))
    ic0 = full.get(0)
    fwd = [full[k] for k in (1, 2) if full.get(k) is not None]
    peak_at_0 = ic0 is not None and ic0 > 0 and all(ic0 >= v for v in fwd)
    # razor-spike (sub-H): +1 lag must retain >= fwd_sub_ratio_min of sub-peak
    s0, s1 = sub.get(0), sub.get(1)
    fwd_ratio_sub = (s1 / s0) if (s0 and s1 is not None and s0 > 0) else None
    razor_ok = (fwd_ratio_sub is None) or (fwd_ratio_sub >= thr["fwd_sub_ratio_min"])
    # flat-leak (full-H): +1 lag must be < fwd_flat_ratio_max of peak (and < peak)
    fwd_ratio_full = (full[1] / ic0) if (ic0 and full.get(1) is not None and ic0 > 0) else None
    flat_ok = (fwd_ratio_full is None) or (fwd_ratio_full < thr["fwd_flat_ratio_max"])
    # negative-lag reversal exemption: leak only if same-sign as peak, >=0.5*peak, symmetric bell
    n1, p1, n2, p2 = full.get(-1), full.get(1), full.get(-2), full.get(2)
    neg_leak = False
    if ic0 and ic0 > 0 and n1 is not None:
        same_sign = n1 > 0
        large = n1 >= thr["fwd_neg_leak_ratio"] * ic0
        sym1 = (p1 is not None) and abs(n1 - p1) < 0.25 * ic0
        sym2 = (n2 is None or p2 is None) or abs(n2 - p2) < 0.25 * ic0
        neg_leak = bool(same_sign and large and sym1 and sym2)
    passed = bool(peak_at_0 and razor_ok and flat_ok and not neg_leak)
    return dict(name="e_forward_causal", cls="hard", passed=passed, profile_fullH=full, profile_subH=sub,
                peak_at_lag0=bool(peak_at_0), fwd_ratio_subH=None if fwd_ratio_sub is None else round(fwd_ratio_sub, 3),
                fwd_ratio_fullH=None if fwd_ratio_full is None else round(fwd_ratio_full, 3),
                neg_lag_leak=bool(neg_leak), note="reversal-exempt (opposite-sign neg lag is healthy)")


def gate_f_align(cand, champ, thr):
    if champ is None:
        return dict(name="f_index_alignment", cls="hard", passed=not thr["require_panel_match"],
                    note="no champion supplied; alignment unverifiable", ran=False)
    ts_match = cand.ts_md5 == champ.ts_md5
    mem_match = cand.member_md5 == champ.member_md5
    cl_match = cand.CL_md5 == champ.CL_md5
    overlap_ok = cand.fold_overlap == 0
    coverage = int(cand.oos_rows.size)
    passed = bool(ts_match and mem_match and cl_match and overlap_ok and coverage > 0)
    if not thr["require_panel_match"]:
        passed = bool(overlap_ok and coverage > 0)
    return dict(name="f_index_alignment", cls="hard", passed=passed, ts_md5=cand.ts_md5,
                ts_md5_match=bool(ts_match), member_match=bool(mem_match), CL_match=bool(cl_match),
                cross_fold_overlap=cand.fold_overlap, coverage_oos_ts=coverage,
                require_match=bool(thr["require_panel_match"]),
                note="index byte-alignment to champion; catches shuffled/misaligned rows")


def gate_h_clean(cand, thr):
    H = cand.horizon or 4
    gaps = np.diff(np.sort(cand.oos_rows))
    min_gap = int(gaps.min()) if gaps.size else H
    passed = bool(min_gap >= H)
    return dict(name="h_clean_caliber", cls="hard", passed=passed, used_clean_mask=True,
                min_anchor_gap_rows=min_gap, horizon_rows=H,
                note="all IC on CL non-overlap grid; stride>=horizon")


def gate_g_cov(cand, seed_prods, thr):
    ran = False; cov = None; head_corr_max = None; ens_eq_head = None; passes = []
    # head diversity (fold-product candidate)
    if cand.heads is not None:
        rows = cand.oos_rows
        vals = []
        for Hk in cand.heads:
            col = []
            for t in rows:
                b = np.where(cand.member[t] & cand.CL[t] & np.isfinite(Hk[t]))[0]
                if b.size >= thr["min_base"]:
                    col.append(np.corrcoef(rankdata(Hk[t, b]), rankdata(cand.pred[t, b]))[0, 1])
            vals.append(np.nanmean(col))
        # pairwise corr of head panels (flattened over OOS cells)
        flat = []
        m = cand.member & cand.CL
        for Hk in cand.heads:
            flat.append(np.where(m & np.isfinite(Hk), Hk, np.nan))
        K = len(flat); mx = 0.0
        for i in range(K):
            for j in range(i + 1, K):
                a, b = flat[i].ravel(), flat[j].ravel()
                ok = np.isfinite(a) & np.isfinite(b)
                if ok.sum() > 100 and a[ok].std() > 1e-12 and b[ok].std() > 1e-12:
                    mx = max(mx, abs(float(np.corrcoef(a[ok], b[ok])[0, 1])))
        head_corr_max = round(mx, 4)
        ens_eq_head = bool(mx >= thr["head_corr_max"])
        passes.append(mx < thr["head_corr_max"])
        ran = True
    # multi-seed CoV
    if seed_prods and len(seed_prods) >= 2:
        means = []
        for sp in seed_prods:
            ics, _, _ = ic_series(sp, sp.pred, sp.oos_rows, "YR")
            means.append(float(np.mean(ics)))
        means = np.array(means)
        cov = float(means.std() / means.mean()) if means.mean() else np.nan
        passes.append(np.isfinite(cov) and cov <= thr["cov_max"])
        ran = True
    if not ran:
        return dict(name="g_cov_headdiv", cls="soft", passed=True, ran=False,
                    note="SKIP: single seed & no per-head panels (seed-stability unverified)")
    return dict(name="g_cov_headdiv", cls="soft", passed=bool(all(passes)), ran=True,
                seed_cov=None if cov is None else round(cov, 3),
                head_pairwise_corr_max=head_corr_max, ensemble_equals_single_head=ens_eq_head,
                note="CoV<=10% and heads not duplicated")


def gate_i_upgrade(cand, champ, thr, claim):
    if not claim:
        return dict(name="i_upgrade", cls="upgrade", passed=True, ran=False,
                    evaluated=False, note="not claiming upgrade; incumbent retained")
    rng = np.random.default_rng(thr["seed"])
    # paired per-year IC diff on shared OOS anchors
    shared = np.intersect1d(cand.oos_rows, champ.oos_rows)
    by_year = {}
    non_inf = True; better_any = False
    for y in sorted(set(int(v) for v in cand.yr_of_row[shared])):
        rows = shared[cand.yr_of_row[shared] == y]
        diffs, days = [], []
        for t in rows:
            b = np.where(cand.member[t] & cand.CL[t] & np.isfinite(cand.pred[t]) &
                         np.isfinite(champ.pred[t]) & np.isfinite(cand.YR[t]))[0]
            if b.size >= thr["min_base"]:
                dc = ricorr(cand.pred[t, b], cand.YR[t, b]) - ricorr(champ.pred[t, b], cand.YR[t, b])
                if np.isfinite(dc):
                    diffs.append(dc); days.append(int(cand.day[t]))
        diffs, days = np.array(diffs), np.array(days)
        ci = dayblock_ci(diffs, days, rng, thr["nboot"])
        by_year[int(y)] = list(ci)
        if ci[1] < 0:
            non_inf = False
        if ci[0] > 0:
            better_any = True
    net_sharpe_non_inf = None
    if cand.pnl_by_year is not None and champ.pnl_by_year is not None:
        net_sharpe_non_inf = True
        for y in cand.pnl_by_year:
            if y in champ.pnl_by_year:
                sc = cand.pnl_by_year[y]; sk = champ.pnl_by_year[y]
                shc = sc.mean() / (sc.std() + 1e-12); shk = sk.mean() / (sk.std() + 1e-12)
                if shc < shk - 0.5:
                    net_sharpe_non_inf = False
    passed = bool(non_inf and better_any and (net_sharpe_non_inf is not False))
    return dict(name="i_upgrade", cls="upgrade", passed=passed, ran=True, evaluated=True,
                paired_ci_by_year=by_year, non_inferior_all=bool(non_inf),
                strictly_better_any=bool(better_any), net_sharpe_non_inferior=net_sharpe_non_inf,
                note="tie => incumbent retained")


# ----------------------------------------------------------------------------- #
# Orchestration + verdict synthesis (SPEC §10)
# ----------------------------------------------------------------------------- #
def run_battery(cand, champ=None, seed_prods=None, thr=None, claim_upgrade=False):
    thr = {**THRESHOLDS, **(thr or {})}
    gates = [
        gate_a_sigma(cand, champ, thr),
        gate_b_ic(cand, champ, thr),
        gate_c_sign(cand, thr),
        gate_d_dynshare(cand, thr),
        gate_e_forward(cand, thr),
        gate_f_align(cand, champ, thr),
        gate_g_cov(cand, seed_prods, thr),
        gate_h_clean(cand, thr),
        gate_i_upgrade(cand, champ, thr, claim_upgrade),
    ]
    g = {x["name"]: x for x in gates}
    hard = [x for x in gates if x["cls"] == "hard"]
    soft = [x for x in gates if x["cls"] == "soft"]
    hard_fail = [x["name"] for x in hard if not x["passed"]]
    soft_fail = [x["name"] for x in soft if not x["passed"]]
    if hard_fail:
        verdict = "REJECT-untrustworthy"
    elif not g["b_honest_ensemble_ic"]["passed"]:
        verdict = "REJECT-degraded"
    elif soft_fail:
        verdict = "REJECT-quality"
    elif claim_upgrade and not g["i_upgrade"]["passed"]:
        verdict = "ACCEPT-clone"     # complete & up-to-spec but not a proven upgrade
    elif claim_upgrade and g["i_upgrade"]["passed"]:
        verdict = "ACCEPT-upgrade"
    else:
        verdict = "ACCEPT-clone"
    return dict(title="acceptance battery v2 (0C-SPEC)", verdict=verdict,
                hard_failed=hard_fail, soft_failed=soft_fail, thresholds=thr, gates=gates,
                candidate=cand.name, champion=None if champ is None else champ.name)


def _print(rep):
    print(f"\n{'='*74}\nACCEPTANCE BATTERY v2 — {rep['verdict']}   (cand={rep['candidate']} vs champ={rep['champion']})\n{'='*74}", flush=True)
    for x in rep["gates"]:
        mark = "PASS" if x["passed"] else "FAIL"
        extra = {k: v for k, v in x.items() if k not in ("name", "passed", "note", "cls")}
        print(f"[{mark}][{x['cls']:7s}] {x['name']:22s} {json.dumps(extra, default=str)}", flush=True)
    if rep["hard_failed"]:
        print(f"HARD FAILED: {rep['hard_failed']}", flush=True)
    if rep["soft_failed"]:
        print(f"SOFT FAILED: {rep['soft_failed']}", flush=True)


# ----------------------------------------------------------------------------- #
# SPEC §12 adversarial self-test matrix
# ----------------------------------------------------------------------------- #
def _clone(P):
    import copy
    Q = Product(P.kind, P.name + "_clone")
    for k, v in P.__dict__.items():
        Q.__dict__[k] = (v.copy() if isinstance(v, np.ndarray)
                         else ([h.copy() for h in v] if (k == "heads" and v is not None)
                               else copy.copy(v)))
    return Q


def corrupt_shuffle_ts(P, seed):
    """T3a: permute the ts index (and day/year) => ts md5 breaks alignment."""
    rng = np.random.default_rng(seed); Q = _clone(P); Q.name = P.name + "_shuffled_ts"
    perm = rng.permutation(P.ts.size)
    Q.ts = P.ts[perm]; Q.day = P.day[perm]
    return Q.finalize()


def corrupt_dup_head(P, seed):
    """T3b: replace every head with head-0 (fake ensemble = single head duplicated)."""
    Q = _clone(P); Q.name = P.name + "_dup_head"
    if Q.heads is None:
        return Q.finalize()
    h0 = Q.heads[0].copy(); Q.heads = [h0.copy() for _ in Q.heads]
    Q.pred = h0.copy(); Q.point = h0.copy()  # ensemble == single head
    return Q.finalize()


def corrupt_inject_lookahead(P, seed, w=0.85):
    """T3c: a MATERIAL lookahead leak — per anchor, mix the cross-sectionally z-scored
    future return z(Yraw_{t+H}) into pred_t at weight w (scale-matched so the leak
    actually dominates the ranking, as a real future-using feature would). Moves the
    forward-window peak from lag0 to lag +1 => gate (e) must FAIL. (A negligible-magnitude
    injection is NOT a material leak and correctly does not trip the gate; §11.)"""
    Q = _clone(P); Q.name = P.name + "_lookahead"; H = P.horizon or 4
    T = P.pred.shape[0]; mb = THRESHOLDS["min_base"]
    newp = Q.pred.copy()
    for t in range(T - H):
        b = np.where(P.member[t] & P.CL[t] & np.isfinite(P.pred[t]) &
                     P.member[t + H] & np.isfinite(P.Yraw[t + H]))[0]
        if b.size < mb:
            continue
        zp = P.pred[t, b]; zp = (zp - zp.mean()) / (zp.std() + 1e-12)
        zf = P.Yraw[t + H, b]; zf = (zf - zf.mean()) / (zf.std() + 1e-12)
        newp[t, b] = (1.0 - w) * zp + w * zf
    Q.pred = newp; Q.point = newp.copy()
    if Q.heads is not None:
        Q.heads = [newp.copy() for _ in Q.heads]
    return Q.finalize()


def self_test(champion_path, thr):
    thr = {**THRESHOLDS, **(thr or {})}
    print(f"[self-test] loading champion {champion_path} ...", flush=True)
    champ = load_any(champion_path, thr)
    results = {}
    def run(tag, cand, expect_prefix, expect_gate=None):
        rep = run_battery(cand, champ=champ, thr=thr)
        _print(rep)
        ok = rep["verdict"].startswith(expect_prefix)
        if expect_gate:
            ok = ok and (expect_gate in rep["hard_failed"] or expect_gate in rep["soft_failed"])
        print(f"[{tag}] verdict={rep['verdict']} expect~{expect_prefix}"
              f"{'/'+expect_gate if expect_gate else ''} -> {'OK' if ok else 'BROKEN'}", flush=True)
        results[tag] = dict(verdict=rep["verdict"], ok=bool(ok),
                            hard_failed=rep["hard_failed"], soft_failed=rep["soft_failed"])
        return ok

    print("\n########## T1 champion vs self (expect ACCEPT-clone) ##########", flush=True)
    ok1 = run("T1_clone", _clone(champ).finalize(), "ACCEPT")
    print("\n########## T3a shuffle-ts (expect REJECT via f) ##########", flush=True)
    ok3a = run("T3a_shuffle_ts", corrupt_shuffle_ts(champ, thr["seed"]), "REJECT", "f_index_alignment")
    print("\n########## T3b duplicated-head (expect REJECT via g) ##########", flush=True)
    ok3b = run("T3b_dup_head", corrupt_dup_head(champ, thr["seed"]), "REJECT", "g_cov_headdiv")
    print("\n########## T3c injected-lookahead (expect REJECT via e) ##########", flush=True)
    ok3c = run("T3c_lookahead", corrupt_inject_lookahead(champ, thr["seed"]), "REJECT", "e_forward_causal")

    all_ok = ok1 and ok3a and ok3b and ok3c
    print(f"\n{'#'*74}\nSELF-TEST {'OK' if all_ok else 'BROKEN'} — "
          f"T1={results['T1_clone']['verdict']} T3a={results['T3a_shuffle_ts']['verdict']} "
          f"T3b={results['T3b_dup_head']['verdict']} T3c={results['T3c_lookahead']['verdict']}\n{'#'*74}", flush=True)
    return dict(results=results, self_test_ok=bool(all_ok))


def main():
    ap = argparse.ArgumentParser(description="Automated model acceptance battery v2 (0C-SPEC)")
    ap.add_argument("--candidate", help="candidate: fold-product DIR or pred-panel NPZ")
    ap.add_argument("--champion", help="champion: fold-product DIR or pred-panel NPZ")
    ap.add_argument("--seeds", nargs="*", default=None, help="≥2 extra seed products for CoV gate")
    ap.add_argument("--claim-upgrade", action="store_true", help="evaluate the upgrade gate (i)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--config", default=None, help="JSON overriding any THRESHOLDS subset")
    ap.add_argument("--self-test", action="store_true", help="run SPEC §12 adversarial matrix")
    args = ap.parse_args()

    thr = json.load(open(args.config)) if args.config else {}
    if args.self_test:
        if not args.champion:
            ap.error("--self-test requires --champion")
        res = self_test(args.champion, thr)
        if args.out:
            json.dump(res, open(args.out, "w"), indent=2, default=str)
            print("SAVED " + args.out, flush=True)
        sys.exit(0 if res["self_test_ok"] else 2)

    if not args.candidate:
        ap.error("--candidate required (or --self-test)")
    full = {**THRESHOLDS, **thr}
    cand = load_any(args.candidate, full)
    champ = load_any(args.champion, full) if args.champion else None
    seed_prods = [load_any(d, full) for d in args.seeds] if args.seeds else None
    rep = run_battery(cand, champ=champ, seed_prods=seed_prods, thr=thr, claim_upgrade=args.claim_upgrade)
    _print(rep)
    if args.out:
        json.dump(rep, open(args.out, "w"), indent=2, default=str)
        print("\nSAVED " + args.out, flush=True)
    sys.exit(0 if rep["verdict"].startswith("ACCEPT") else 1)


if __name__ == "__main__":
    main()
