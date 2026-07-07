"""GATE 0 — Does the corrected BTC PERP deep-book carry INCREMENTAL cross-sectional
alpha for the 14 alts? Cheap Ridge walk-forward to decide GO/NO-GO on building an
end-to-end BTC-perp fusion model BEFORE spending GPU.

Reuses the validated cross-sectional Ridge harness `target_study.py` (T) EXACTLY:
  - load_panel(): 44-feature alt panel + Y/CL + capw, ts-aligned
  - xsec_zscore(): per-ts cross-sectional z across the 14 assets (>=5 finite)
  - market_means / causal_beta / build_target("T0"): the T0 residual target
    (equal-demean -> per-asset MAD-z -> clip +/-5), train-fold sigma
  - fold layout FOLDS (tr 230 / val 20 / test 40, embargo 1)
  - ridge_fit_gram / ridge_solve (Gram reused across alpha grid)
  - xsec_spearman(pred, RAW y, vmask, rows): per-snapshot xsec rank-IC vs RAW y

Eval metric (FIXED, identical rows/folds): per-timestamp cross-sectional Spearman
rank-IC of Ridge predictions vs RAW y_600. Headline = pooled mean across all test ts.

BTC perp deep-state: exports/btc25_raw_perp/<yyyymmdd>.npz, R25 (85800,104) float16,
ts int64 ns. Channels: 0-24 bid_off_bps, 25-49 ask_off_bps, 50-74 bid_ntl_log,
75-99 ask_ntl_log, 100-103 summary [spread_bps, microprice_dev_bps, deep_imb_l1_25,
total_depth_ntl_log]. SAME vector for all 14 assets at a given t (joined by ts).

VARIANTS (all on identical rows/folds/eval, alpha tuned on val same as BASE):
  BASE          : Ridge(44 alt feats, cs-z)                      -> reproduce ~0.044
  +BTC_SUMMARY  : + 4 BTC summary scalars, broadcast to all assets, cs-z'd
                  (caveat: constant-across-assets => cancels under cs-demean; naive
                   control, expected ~null)
  +BTC_LADDER_PCA: + 8 PCA comps of the 100 ladder channels, broadcast, cs-z'd
                  (same caveat)
  +BTC_INTERACT : *** THE REAL TEST *** alt's own contemporaneous return/flow feats
                  x BTC deep-state scalars (state-dependent beta). These DO have
                  cross-asset spread (alt feat varies across assets) so they can
                  move xsec rank-IC. ~12-18 interaction terms, cs-z'd.

PCA is fit on TRAIN rows only per fold (no leak). Interaction states are causal
contemporaneous BTC book scalars at t (<= t); BTC vector is identical across assets
so it is leak-safe wrt the cross-section.

GATE: pooled Delta xsec-rank-IC >= +0.005 AND sign-consistent across 3 folds => GO.
All within +/-0.003 => NO-GO (bank clean negative). Per-asset raw-Pearson reported
aside, FLAGGED unreliable (corrupted caliber).

CPU only. Writes /tmp/gate0.json.
"""
from __future__ import annotations
import glob
import json
import os
import os.path as p
import sys

import numpy as np

sys.path.insert(0, "/tmp")
import target_study as T  # noqa: E402

PERP_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
            "multi_asset/exports/btc25_raw_perp")

# alpha grid identical to harness
ALPHAS = T.ALPHAS  # [1,3,10,30,100,300]

N_PCA = 8

# --- the 44 alt-feature column order (from features_ma.py build order) -------- #
# 0-4 ret_{30,60,120,300,600}s ; 5-8 vwap/twap press ; 9-23 flow(5x3) ;
# 24-25 rv ; 26-30 obi ; 31-35 depth_ratio ; 36-38 slope ; 39-40 spread ;
# 41-42 vpin ; 43 ofi
FEAT_NAMES = (
    ["ret_30s", "ret_60s", "ret_120s", "ret_300s", "ret_600s",
     "vwap_press_bps", "twap_press_bps", "vwap_press_60s", "twap_press_60s"]
    + [f"{nm}_{w}s" for nm in ("tradeflow", "dollarflow", "cntflow", "bookflow",
                               "midchg") for w in (30, 60, 300)]
    + ["rv_60s", "rv_300s"]
    + ["obi_L1", "obi_L2", "obi_L3", "obi_L4", "obi_L5"]
    + [f"depth_ratio_{dx}bps" for dx in ("1.0", "3.0", "10.0", "30.0", "100.0")]
    + ["book_slope_bid", "book_slope_ask", "book_slope_asym"]
    + ["spread_bps", "spread_bps_60s", "vpin_60s", "vpin_300s", "ofi_60s"]
)
assert len(FEAT_NAMES) == 44, len(FEAT_NAMES)
FIDX = {n: i for i, n in enumerate(FEAT_NAMES)}

# Alt features used as the per-asset loading that interacts with BTC state.
# These have cross-asset spread (vary across the 14 assets) and are the strongest
# univariate signals (returns + flow + L1 imbalance per features_ma.py docstrings).
INTERACT_ALT_FEATS = ["ret_300s", "ret_60s", "ret_30s",
                      "tradeflow_60s", "dollarflow_60s", "bookflow_60s",
                      "obi_L1", "ofi_60s"]
# BTC deep-book state scalars that modulate the alt<->BTC relationship.
# deep_imb (directional), spread (regime/cost), microprice_dev (lead pressure).
# (summary indices into R25: 100 spread, 101 microprice_dev, 102 deep_imb, 103 totdepth)
INTERACT_BTC_STATES = ["deep_imb_l1_25", "spread_bps", "microprice_dev_bps"]
SUMMARY_NAMES = ["spread_bps", "microprice_dev_bps", "deep_imb_l1_25",
                 "total_depth_ntl_log"]
SUMMARY_OFF = {"spread_bps": 100, "microprice_dev_bps": 101,
               "deep_imb_l1_25": 102, "total_depth_ntl_log": 103}


# --------------------------------------------------------------------------- #
# load BTC perp deep-state, aligned to the panel ts (join on ts value)
# --------------------------------------------------------------------------- #
def load_btc_perp(ts):
    """Return Rperp (T,104) float64 aligned row-for-row to panel ts. NaN where the
    panel ts has no matching perp row."""
    files = sorted(glob.glob(p.join(PERP_DIR, "*.npz")))
    files = [f for f in files if os.path.basename(f)[0].isdigit()]
    # global ts->R lookup built incrementally; panel ts are unique & sorted
    R = np.full((len(ts), 104), np.nan, np.float64)
    found = 0
    # build a dict only over panel ts we need, scanning each day file once
    need = {int(t): i for i, t in enumerate(ts)}
    for f in files:
        d = np.load(f)
        pts = d["ts"]
        pr = d["R25"].astype(np.float64)
        # vectorized: which of this day's ts are needed?
        # use searchsorted on sorted panel ts
        idx = np.searchsorted(ts, pts)
        idx = np.clip(idx, 0, len(ts) - 1)
        hit = ts[idx] == pts
        rows_panel = idx[hit]
        rows_day = np.where(hit)[0]
        R[rows_panel] = pr[rows_day]
        found += hit.sum()
    cov = float(np.isfinite(R).all(1).mean())
    print(f"BTC perp join: matched {found} panel rows, coverage={cov:.4f}",
          flush=True)
    return R, cov


# --------------------------------------------------------------------------- #
# feature-set builders -> Xz_aug (T,S,F') cross-sectionally z-scored per ts
# --------------------------------------------------------------------------- #
def _cs_zscore_block(B, vx):
    """cross-sectional z of an extra (T,S,k) block across assets per ts, masked to
    valid rows. Mirrors xsec_zscore semantics (>=5 valid handled by vx upstream)."""
    Bm = np.where(vx[:, :, None], B, np.nan)
    with np.errstate(all="ignore"):
        mu = np.nanmean(Bm, axis=1, keepdims=True)
        sd = np.nanstd(Bm, axis=1, keepdims=True)
    sd = np.where(sd > 1e-9, sd, 1.0)
    Z = (Bm - mu) / sd
    return Z.astype(np.float32)


def build_base(Xz):
    return Xz  # (T,S,44) already cs-z'd by harness


def build_btc_summary(Xz, Rperp, vx):
    T_, S, _ = Xz.shape
    summ = np.stack([Rperp[:, SUMMARY_OFF[n]] for n in SUMMARY_NAMES], axis=1)  # (T,4)
    blk = np.broadcast_to(summ[:, None, :], (T_, S, 4)).copy()                  # broadcast
    Z = _cs_zscore_block(blk, vx)
    return np.concatenate([Xz, Z], axis=2)


def build_btc_ladder_pca(Xz, Rperp, vx, train_rows):
    """PCA the 100 ladder channels (offsets+notionals), fit on TRAIN rows only,
    project all rows to N_PCA comps, broadcast to assets, cs-z."""
    T_, S, _ = Xz.shape
    L = Rperp[:, 0:100]                       # (T,100)
    finite = np.isfinite(L).all(1)
    tr = train_rows[finite[train_rows]]
    Ltr = L[tr]
    mu = Ltr.mean(0)
    sd = Ltr.std(0)
    sd = np.where(sd > 1e-9, sd, 1.0)
    Ltr_s = (Ltr - mu) / sd
    # SVD on standardized train ladder
    U, Sg, Vt = np.linalg.svd(Ltr_s, full_matrices=False)
    comps = Vt[:N_PCA]                         # (N_PCA,100)
    Lall_s = np.where(finite[:, None], (L - mu) / sd, 0.0)
    proj = Lall_s @ comps.T                    # (T,N_PCA)
    proj[~finite] = np.nan
    blk = np.broadcast_to(proj[:, None, :], (T_, S, N_PCA)).copy()
    Z = _cs_zscore_block(blk, vx)
    return np.concatenate([Xz, Z], axis=2), float(Sg[:N_PCA].sum() ** 2 /
                                                   (Sg ** 2).sum())


def build_btc_interact(X_raw, Xz, Rperp, vx, train_rows):
    """State-dependent beta: (alt own contemporaneous feat) x (BTC deep-state).
    We multiply the RAW alt feature (per-asset, varies across assets) by the BTC
    state scalar (constant across assets at t), then cross-sectionally z the
    resulting (T,S,k) block. k = len(alt_feats) x len(btc_states)."""
    T_, S, _ = Xz.shape
    states = {n: Rperp[:, SUMMARY_OFF[n]] for n in INTERACT_BTC_STATES}  # (T,)
    # standardize each BTC state on train rows (so the product magnitude is sane)
    for n in states:
        s = states[n]
        tr = train_rows[np.isfinite(s[train_rows])]
        m, sd = s[tr].mean(), s[tr].std()
        sd = sd if sd > 1e-9 else 1.0
        states[n] = (s - m) / sd
    blocks = []
    names = []
    for af in INTERACT_ALT_FEATS:
        fcol = X_raw[:, :, FIDX[af]]           # (T,S) raw alt feature (per-asset)
        for bn in INTERACT_BTC_STATES:
            inter = fcol * states[bn][:, None]  # (T,S)
            blocks.append(inter)
            names.append(f"{af}__x__{bn}")
    blk = np.stack(blocks, axis=2)             # (T,S,k)
    Z = _cs_zscore_block(blk, vx)
    return np.concatenate([Xz, Z], axis=2), names


# --------------------------------------------------------------------------- #
# generic fold runner (mirrors target_study T0 variant exactly, alpha-tuned)
# --------------------------------------------------------------------------- #
def run_variant_folds(Xaug_per_fold, Yh, m_eq, m_cw, B, day, uniq, vmask):
    """Xaug_per_fold: callable(fold) -> Xz_aug (T,S,F') (allows per-fold PCA refit).
    Returns dict with pooled, per_fold, alpha, ir, per-fold raw-pearson."""
    pf_ic, pf_alpha, all_ics = [], [], []
    pf_pear, all_pear = [], []
    for fi, fold in enumerate(T.FOLDS):
        Xz_aug = Xaug_per_fold(fi)
        F = Xz_aug.shape[2]
        trd, vad, ted = T.fold_day_lists(uniq, fold)
        trm = np.isin(day, trd)
        vam = np.isin(day, vad)
        tem = np.isin(day, ted)
        trva = trm | vam
        # T0 residual target (train+val sigma) — identical to harness
        r = T.build_target("T0", Yh, m_eq, m_cw, B, np.where(trva)[0], 5.0)
        # flatten respecting NaN in augmented X (uses Xz_aug, finite all-feat)
        def flat(rows):
            sx = Xz_aug[rows]
            sr = r[rows]
            ok = np.isfinite(sx).all(-1) & np.isfinite(sr)
            return sx[ok], sr[ok]
        # tune alpha on val (fit train-only)
        Xf, yf = flat(np.where(trm)[0])
        G, b, xm, ym = T.ridge_fit_gram(Xf, yf)
        va_rows = np.where(vam)[0]
        Xva = np.nan_to_num(Xz_aug[va_rows])
        vaok = np.isfinite(Xz_aug[va_rows]).all(-1)
        best_a, best_ic = ALPHAS[0], -9
        for a in ALPHAS:
            w, b0 = T.ridge_solve(G, b, xm, ym, a)
            pred = np.einsum("tsf,f->ts", Xva, w) + b0
            predf = np.full_like(Yh, np.nan)
            predf[va_rows] = np.where(vaok, pred, np.nan)
            ic = T.xsec_spearman(predf, Yh, vmask, va_rows)
            icm = ic.mean() if len(ic) else -9
            if icm > best_ic:
                best_ic, best_a = icm, a
        # refit on train+val with best alpha, eval on test
        Xf, yf = flat(np.where(trva)[0])
        G, b, xm, ym = T.ridge_fit_gram(Xf, yf)
        w, b0 = T.ridge_solve(G, b, xm, ym, best_a)
        te_rows = np.where(tem)[0]
        Xte = np.nan_to_num(Xz_aug[te_rows])
        teok = np.isfinite(Xz_aug[te_rows]).all(-1)
        pred = np.einsum("tsf,f->ts", Xte, w) + b0
        predf = np.full_like(Yh, np.nan)
        predf[te_rows] = np.where(teok, pred, np.nan)
        ics = T.xsec_spearman(predf, Yh, vmask, te_rows)
        all_ics.append(ics)
        pf_ic.append(round(float(ics.mean()), 4))
        pf_alpha.append(best_a)
        # ---- per-asset RAW Pearson caliber (UNRELIABLE — corrupted metric) ----
        ppa = []
        for si in range(Yh.shape[1]):
            m = vmask[te_rows, si] & teok[:, si]
            if m.sum() < 50:
                continue
            pv = predf[te_rows[m], si]
            yv = Yh[te_rows[m], si]
            if pv.std() > 1e-12 and yv.std() > 1e-12:
                ppa.append(float(np.corrcoef(pv, yv)[0, 1]))
        all_pear.append(ppa)
        pf_pear.append(round(float(np.mean(ppa)) if ppa else float("nan"), 4))
    cat = np.concatenate(all_ics)
    pooled = float(cat.mean())
    flat_pear = [x for sub in all_pear for x in sub]
    return dict(
        pooled_rank_ic=round(pooled, 4),
        per_fold=pf_ic,
        alpha=pf_alpha,
        ir=round(float(cat.mean() / cat.std() * np.sqrt(len(cat))), 2),
        n_ts=int(len(cat)),
        per_fold_raw_pearson=pf_pear,
        pooled_raw_pearson=round(float(np.mean(flat_pear)), 4),
    )


def main():
    ts, day, X, Y, CL, capw = T.load_panel()
    uniq = np.unique(day)
    print(f"panel nT={len(ts)} days={len(uniq)}", flush=True)
    Xz, vx = T.xsec_zscore(X)
    Xraw = np.where(vx[:, :, None], X.astype(np.float64), np.nan)  # keep raw for interact
    del X

    Rperp, cov = load_btc_perp(ts)

    hz = "y600"
    Yh, CLh = Y[hz], CL[hz]
    m_eq, m_cw = T.market_means(Yh, capw)
    B, _ = T.causal_beta(Yh, m_eq, day, uniq)
    vmask = vx & CLh & np.isfinite(Yh)

    out = {"folds": [dict(tr=f["tr"], te=f["te"]) for f in T.FOLDS],
           "alphas": ALPHAS, "btc_perp_coverage": round(cov, 4),
           "interact_alt_feats": INTERACT_ALT_FEATS,
           "interact_btc_states": INTERACT_BTC_STATES,
           "variants": {}}

    # precompute fold train-row lists (for PCA/interact state standardization)
    fold_trva = []
    for fold in T.FOLDS:
        trd, vad, ted = T.fold_day_lists(uniq, fold)
        trva = np.isin(day, trd) | np.isin(day, vad)
        fold_trva.append(np.where(trva)[0])

    # BASE
    print("=== BASE ===", flush=True)
    out["variants"]["BASE"] = run_variant_folds(
        lambda fi: Xz, Yh, m_eq, m_cw, B, day, uniq, vmask)
    print("BASE", out["variants"]["BASE"]["pooled_rank_ic"],
          out["variants"]["BASE"]["per_fold"], flush=True)

    # +BTC_SUMMARY
    print("=== +BTC_SUMMARY ===", flush=True)
    Xz_sum = build_btc_summary(Xz, Rperp, vx)
    out["variants"]["+BTC_SUMMARY"] = run_variant_folds(
        lambda fi: Xz_sum, Yh, m_eq, m_cw, B, day, uniq, vmask)
    print("+BTC_SUMMARY", out["variants"]["+BTC_SUMMARY"]["pooled_rank_ic"],
          out["variants"]["+BTC_SUMMARY"]["per_fold"], flush=True)

    # +BTC_LADDER_PCA (PCA refit per fold on train rows)
    print("=== +BTC_LADDER_PCA ===", flush=True)
    pca_cache = {}
    pca_evr = []
    def pca_builder(fi):
        if fi not in pca_cache:
            Xaug, evr = build_btc_ladder_pca(Xz, Rperp, vx, fold_trva[fi])
            pca_cache[fi] = Xaug
            pca_evr.append(round(evr, 4))
        return pca_cache[fi]
    out["variants"]["+BTC_LADDER_PCA"] = run_variant_folds(
        pca_builder, Yh, m_eq, m_cw, B, day, uniq, vmask)
    out["variants"]["+BTC_LADDER_PCA"]["pca_evr_per_fold"] = pca_evr
    print("+BTC_LADDER_PCA", out["variants"]["+BTC_LADDER_PCA"]["pooled_rank_ic"],
          out["variants"]["+BTC_LADDER_PCA"]["per_fold"], "evr", pca_evr, flush=True)

    # +BTC_INTERACT (state std refit per fold)
    print("=== +BTC_INTERACT ===", flush=True)
    inter_cache = {}
    inter_names = [None]
    def inter_builder(fi):
        if fi not in inter_cache:
            Xaug, names = build_btc_interact(Xraw, Xz, Rperp, vx, fold_trva[fi])
            inter_cache[fi] = Xaug
            inter_names[0] = names
        return inter_cache[fi]
    out["variants"]["+BTC_INTERACT"] = run_variant_folds(
        inter_builder, Yh, m_eq, m_cw, B, day, uniq, vmask)
    out["variants"]["+BTC_INTERACT"]["interaction_terms"] = inter_names[0]
    print("+BTC_INTERACT", out["variants"]["+BTC_INTERACT"]["pooled_rank_ic"],
          out["variants"]["+BTC_INTERACT"]["per_fold"], flush=True)

    # deltas vs BASE + verdict
    base = out["variants"]["BASE"]
    bpf = np.array(base["per_fold"])
    verdict = {}
    for v in ("+BTC_SUMMARY", "+BTC_LADDER_PCA", "+BTC_INTERACT"):
        d = out["variants"][v]
        dpf = np.array(d["per_fold"]) - bpf
        d["delta_vs_BASE_pooled"] = round(
            d["pooled_rank_ic"] - base["pooled_rank_ic"], 4)
        d["delta_vs_BASE_per_fold"] = [round(float(x), 4) for x in dpf]
        d["sign_consistent"] = bool((dpf > 0).all() or (dpf < 0).all())
        passes = (d["delta_vs_BASE_pooled"] >= 0.005) and \
                 bool((dpf > 0).all())
        d["PASS_gate"] = passes
        verdict[v] = dict(delta_pooled=d["delta_vs_BASE_pooled"],
                          sign_consistent_positive=bool((dpf > 0).all()),
                          PASS=passes)
    # overall GO/NO-GO: GO iff +BTC_INTERACT passes (the real test)
    interact_pass = out["variants"]["+BTC_INTERACT"]["PASS_gate"]
    any_pass = any(out["variants"][v]["PASS_gate"]
                   for v in ("+BTC_SUMMARY", "+BTC_LADDER_PCA", "+BTC_INTERACT"))
    out["verdict"] = dict(
        per_variant=verdict,
        interact_PASS=interact_pass,
        any_variant_PASS=any_pass,
        DECISION="GO_build_fusion_model" if interact_pass else "NO_GO_clean_negative",
    )

    with open("/tmp/gate0.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\n=== VERDICT ===", json.dumps(out["verdict"], indent=2), flush=True)
    print("WROTE /tmp/gate0.json", flush=True)


if __name__ == "__main__":
    main()
