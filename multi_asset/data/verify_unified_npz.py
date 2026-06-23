"""Verification gates for the UNIFIED BTC cache (``data/npz_btc_unified``).

> **created:** 2026-06-21 | **状态:** in-progress | **作废条件:** spec change.

Runs the Phase-1 hard-evidence gates on a SMALL day range (gate 4, the training
acceptance test, is run separately via run_pipeline_v3 because it needs a fold):

  GATE 2  feature validity   : new X_spot vs data/npz_spot per-feature corr ≈1.0
                               AND std/scale match (the trade-venue confound).
                               (X_spot here = SPOT book + SPOT trades = npz_spot.)
  GATE 3  targets leak-free  : future-perturbation sentinel on y_*; perp-vs-spot
                               corr ≈0.9985; re-anchor offset 0.
  GATE 5  new-feat leak-free : shuffle-future null on X_cross + X_long.
  GATE 6  finite/bounded     : no NaN/Inf anywhere; X_cross/basis bounded; X_long
                               finite at day edges.

Each gate prints PASS/FAIL with the numeric evidence. Exit 1 if any gate fails.
"""
from __future__ import annotations

import os.path as p
import sys

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

import multi_asset.data.build_unified_npz as B    # noqa: E402
from multi_asset.data.build_unified_npz import (   # noqa: E402
    OUT_DIR, EXPECTED_FEATURES, CROSS_NAMES, LONG_NAMES, US, INPUT_LEN,
    build_one_day, build_day_result, _mids_tuple, _neighbors,
)

NPZ_SPOT_DIR = p.join(_REPO, "data", "npz_spot")    # gate-2 reference (exists)


# ----------------------------------------------------------------- GATE 2
def gate2_feature_validity(date_str, res):
    """new X_spot vs data/npz_spot per-feature corr + std. X_spot = SPOT book +
    SPOT trades, so it must reproduce npz_spot in VALUE and SCALE."""
    ref = p.join(NPZ_SPOT_DIR, f"{date_str}.npz")
    if not p.exists(ref):
        print(f"  [GATE2 {date_str}] SKIP: no npz_spot reference", flush=True)
        return None
    with np.load(ref, allow_pickle=True) as z:
        ts_ref = z["timestamps"].astype(np.int64)
        Xref = z["X"].astype(np.float32)
        names_ref = [str(s) for s in z["features"]]
    ts_new = res["timestamps"].astype(np.int64)
    Xnew = res["X_spot"].astype(np.float32)
    common, in_new, in_ref = np.intersect1d(ts_new, ts_ref, return_indices=True)
    if common.size < 20:
        print(f"  [GATE2 {date_str}] SKIP: {common.size} common windows", flush=True)
        return None
    Xn = Xnew[in_new]; Xr = Xref[in_ref]
    if names_ref != EXPECTED_FEATURES:
        print(f"  [GATE2 {date_str}] WARN feature-name order differs from new", flush=True)

    print(f"  [GATE2 {date_str}] X_spot vs npz_spot ({common.size} common windows)",
          flush=True)
    print(f"    {'#':>3} {'feature':<26}{'corr':>9}{'std_new':>11}{'std_ref':>11}"
          f"{'std_ratio':>11}", flush=True)
    corrs = []
    std_ratios = []
    worst = []
    for j, nm in enumerate(EXPECTED_FEATURES):
        a = Xn[:, -1, j].astype(np.float64)
        b = Xr[:, -1, j].astype(np.float64)
        g = np.isfinite(a) & np.isfinite(b)
        if g.sum() < 10 or a[g].std() == 0 or b[g].std() == 0:
            c = float("nan")
        else:
            c = float(np.corrcoef(a[g], b[g])[0, 1])
        sn = float(np.nanstd(Xn[:, :, j])); sr = float(np.nanstd(Xr[:, :, j]))
        ratio = sn / sr if sr > 1e-12 else float("nan")
        corrs.append(c); std_ratios.append(ratio)
        flag = ""
        if np.isfinite(c) and c < 0.99:
            flag = "  <corr"
        if np.isfinite(ratio) and (ratio > 1.05 or ratio < 0.95):
            flag += "  <std"
        if flag:
            worst.append((nm, c, ratio))
        # print only flagged + first/last few to keep output readable
        if flag or j < 4 or j > 60:
            print(f"    {j:>3} {nm:<26}{c:>9.4f}{sn:>11.4g}{sr:>11.4g}{ratio:>11.4f}{flag}",
                  flush=True)
    corrs = np.array(corrs); std_ratios = np.array(std_ratios)
    med_corr = float(np.nanmedian(corrs)); min_corr = float(np.nanmin(corrs))
    n_lowcorr = int(np.sum(corrs < 0.99))
    overall_std_new = float(np.nanstd(Xn.reshape(-1, 64)))
    overall_std_ref = float(np.nanstd(Xr.reshape(-1, 64)))
    n_badstd = int(np.sum((std_ratios > 1.05) | (std_ratios < 0.95)))
    # PASS: every feature corr >= 0.99 AND overall std within 1% AND no per-feat
    # std off by >5%.
    ok = (min_corr >= 0.99 and abs(overall_std_new / overall_std_ref - 1.0) < 0.01
          and n_badstd == 0)
    print(f"    SUMMARY median_corr={med_corr:.5f} min_corr={min_corr:.5f} "
          f"#corr<0.99={n_lowcorr}/64  overall_std new={overall_std_new:.4f} "
          f"ref={overall_std_ref:.4f} (ratio {overall_std_new/overall_std_ref:.4f}) "
          f"#per-feat std off>5%={n_badstd}/64", flush=True)
    if worst:
        print(f"    flagged feats: {[(w[0], round(w[1],3), round(w[2],3)) for w in worst]}",
              flush=True)
    print(f"    -> GATE2 {'PASS' if ok else 'FAIL'}", flush=True)
    return ok


# ----------------------------------------------------------------- GATE 3
def gate3_targets_leakfree(date_str, res):
    """(a) re-anchor offset 0: y_perp_600[t] uses perp_mid[t] & perp_mid[t+600].
       (b) perp-vs-spot 600 corr ≈ 0.9985.
       (c) future-perturbation sentinel: corrupt the per-second mids STRICTLY
           AFTER t+0 leaves y at t unchanged ONLY for the part <= t; corrupting
           the FORWARD window must CHANGE y (proves the target reads the future);
           corrupting strictly BEFORE t must NOT change y (no past leak in label).
       We verify the label is a pure forward return by reconstructing it from the
       mid grid and confirming offset 0 + future-sensitivity + past-insensitivity.
    """
    ok = True
    # (b) perp vs spot 600 corr
    mp = res["y_mask_perp_600"].astype(bool) & res["y_mask_spot_600"].astype(bool)
    yp = res["y_perp_600"][mp].astype(np.float64)
    ysp = res["y_spot_600"][mp].astype(np.float64)
    corr = float(np.corrcoef(yp, ysp)[0, 1]) if mp.sum() > 10 else float("nan")
    ok_corr = 0.995 <= corr <= 0.9999
    print(f"  [GATE3 {date_str}] perp-vs-spot y_600 corr={corr:.5f} "
          f"(expect ~0.9985)  N={int(mp.sum())} -> {'ok' if ok_corr else 'FAIL'}",
          flush=True)
    ok &= ok_corr

    # (a)+(c) reconstruct from the mid grid and run the future-perturbation sentinel
    d_prev, d_next = _neighbors(date_str)
    next_mids = _mids_tuple(d_next)
    ss, smid, sspr = B._mid_1s(date_str, B.SPOT_VENUE)
    ps, pmid, pspr = B._mid_1s(date_str, B.PERP_VENUE)
    sec_c, smid_c, sspr_c, pmid_c, pspr_c = B._common_grid(ss, smid, sspr, ps, pmid, pspr)
    fwd_sec, fwd_smid, fwd_pmid = B._stitch_forward(sec_c, smid_c, pmid_c, next_mids)
    ts = res["timestamps"].astype(np.int64)

    # offset-0 check: y_perp_600 should equal log(perp_mid[t+600]/perp_mid[t]) EXACTLY
    ys0, _ = B._targets(ts, sec_c, smid_c, pmid_c, (fwd_sec, fwd_smid, fwd_pmid))
    off0 = float(np.nanmax(np.abs(ys0["y_perp_600"][res["y_mask_perp_600"].astype(bool)]
                                  - res["y_perp_600"][res["y_mask_perp_600"].astype(bool)])))
    ok_off = off0 < 1e-6
    print(f"    offset-0 reconstruction max|Δ|={off0:.2e} -> {'ok' if ok_off else 'FAIL'}",
          flush=True)
    ok &= ok_off

    # future-perturbation sentinel: corrupt fwd mids STRICTLY BEFORE each cut and
    # confirm y is INVARIANT (label uses no second < t); then corrupt STRICTLY
    # AFTER t and confirm y CHANGES (label reads the future, as a target must).
    s = (ts // US)
    cut = int(np.median(s))
    rng = np.random.default_rng(20260621)
    # perturb seconds < cut  (the label window starts at >= t, so labels with t>=cut
    # must be byte-identical)
    pmid_pastpert = pmid_c.copy()
    before = fwd_sec < cut
    fwd_pmid_b = fwd_pmid.copy(); fwd_pmid_b[before] *= (1.0 + rng.uniform(-0.3, 0.3, int(before.sum())))
    pmid_c_b = pmid_c.copy()
    mb = sec_c < cut
    pmid_c_b[mb] *= (1.0 + rng.uniform(-0.3, 0.3, int(mb.sum())))
    ys_b, _ = B._targets(ts, sec_c, pmid_c_b * 0 + smid_c, pmid_c_b,
                         (fwd_sec, fwd_smid, fwd_pmid_b))
    # compare only labels whose t >= cut (their window [t,t+600] is all >= cut)
    later = (s >= cut) & res["y_mask_perp_600"].astype(bool)
    dpast = float(np.nanmax(np.abs(ys_b["y_perp_600"][later] - res["y_perp_600"][later]))) \
        if later.any() else 0.0
    ok_past = dpast < 1e-6
    print(f"    past-perturb (t>=cut labels invariant) max|Δ|={dpast:.2e} "
          f"-> {'ok (no past leak)' if ok_past else 'FAIL'}", flush=True)
    ok &= ok_past

    # forward-sensitivity: perturb fwd mids strictly AFTER cut, labels with t<cut
    # whose window reaches past cut MUST move (proves it is a forward return)
    after = fwd_sec > cut
    fwd_pmid_a = fwd_pmid.copy(); fwd_pmid_a[after] *= 1.05
    ys_a, _ = B._targets(ts, sec_c, smid_c, pmid_c, (fwd_sec, fwd_pmid_a * 0 + fwd_smid, fwd_pmid_a))
    earlier = (s < cut) & (s + 600 > cut) & res["y_mask_perp_600"].astype(bool)
    dfut = float(np.nanmax(np.abs(ys_a["y_perp_600"][earlier] - res["y_perp_600"][earlier]))) \
        if earlier.any() else 0.0
    ok_fut = dfut > 1e-6
    print(f"    forward-sensitivity (labels reading t+600>cut move) max|Δ|={dfut:.2e} "
          f"-> {'ok (reads future)' if ok_fut else 'FAIL'}", flush=True)
    ok &= ok_fut

    print(f"    -> GATE3 {'PASS' if ok else 'FAIL'}", flush=True)
    return ok


# ----------------------------------------------------------------- GATE 5
def gate5_newfeat_leakfree(date_str):
    """Shuffle-future null on X_cross + X_long: rebuild the day with the per-second
    mids corrupted STRICTLY AFTER a cut second, and confirm every window whose
    pred-second <= cut has byte-identical X_cross & X_long (a causal feature cannot
    move when only its future changes).
    """
    d_prev, d_next = _neighbors(date_str)
    prev_mids = _mids_tuple(d_prev)
    next_mids = _mids_tuple(d_next)
    res0 = build_day_result(date_str, prev_mids=prev_mids, next_mids=next_mids)

    # monkeypatch _mids_tuple is overkill; instead corrupt INSIDE build by wrapping
    # the per-second readers. Simplest robust approach: rebuild with a corrupted
    # source by temporarily patching B._mid_1s to perturb seconds > cut.
    ts = res0["timestamps"].astype(np.int64)
    s = ts // US
    cut = int(np.percentile(s, 70))

    orig_mid_1s = B._mid_1s
    rng = np.random.default_rng(7)

    def _corrupt_mid_1s(date, venue):
        sec, mid, spr = orig_mid_1s(date, venue)
        fut = sec > cut
        if fut.any():
            mid = mid.copy(); spr = spr.copy()
            mid[fut] *= (1.0 + rng.uniform(-0.5, 0.5, int(fut.sum())))
            spr[fut] = rng.uniform(1.0, 50.0, int(fut.sum()))
        return sec, mid, spr

    B._mid_1s = _corrupt_mid_1s
    try:
        # rebuild neighbor tuples under the corruption too (next day is future)
        prev_c = _mids_tuple(d_prev)        # prior day fully <= cut -> unaffected mostly
        next_c = _mids_tuple(d_next)        # next day all > cut -> corrupted
        res1 = build_day_result(date_str, prev_mids=prev_c, next_mids=next_c)
    finally:
        B._mid_1s = orig_mid_1s

    le = s <= cut
    dC = np.abs(res0["X_cross"][le].astype(np.float64) - res1["X_cross"][le].astype(np.float64))
    dL = np.abs(res0["X_long"][le].astype(np.float64) - res1["X_long"][le].astype(np.float64))
    mC = float(np.nanmax(dC)) if dC.size else 0.0
    mL = float(np.nanmax(dL)) if dL.size else 0.0
    ok = mC < 1e-5 and mL < 1e-5
    print(f"  [GATE5 {date_str}] shuffle-future (cut sec={cut}, {int(le.sum())} "
          f"causal windows): max|ΔX_cross|={mC:.3e} max|ΔX_long|={mL:.3e} "
          f"-> {'PASS (causal)' if ok else 'FAIL'}", flush=True)
    return ok


# ----------------------------------------------------------------- GATE 6
def gate6_finite_bounded(date_str, res):
    """No NaN/Inf anywhere; X_cross basis bounded; X_long finite at day edges."""
    keys = ["X_spot", "X_perp", "Xraw_spot", "Xraw_perp", "X_cross", "X_long",
            "regime_prior", "X_rg", "X_bs", "y_spot_600", "y_perp_600",
            "y_180", "y_1800"]
    n_bad = {}
    for k in keys:
        a = res[k].astype(np.float64)
        # targets carry NaN where masked-invalid by design -> check only the mask
        if k.startswith("y_"):
            m = res["y_mask_" + k[2:]].astype(bool)
            n_bad[k] = int((~np.isfinite(a[m])).sum())
        else:
            n_bad[k] = int((~np.isfinite(a)).sum())
    total_bad = sum(n_bad.values())
    # X_cross basis (channel 1) bounded to ±CLIP_BPS
    basis_ch = res["X_cross"][:, :, CROSS_NAMES.index("x_basis_bps")]
    basis_absmax = float(np.nanmax(np.abs(basis_ch)))
    ok_basis = basis_absmax <= B.CLIP_BPS + 1e-3
    # X_long finite at the first window (day-edge, partial 4h lookback)
    edge_finite = bool(np.isfinite(res["X_long"][0]).all())
    # X_cross overall bounded (ratios/levels should be O(10) not exploding)
    cross_absmax = float(np.nanmax(np.abs(res["X_cross"])))
    ok = (total_bad == 0 and ok_basis and edge_finite and cross_absmax < 1e3)
    print(f"  [GATE6 {date_str}] total non-finite={total_bad} {n_bad if total_bad else ''}",
          flush=True)
    print(f"    basis |max|={basis_absmax:.3f} (<= {B.CLIP_BPS}) X_cross |max|={cross_absmax:.3f} "
          f"day-edge X_long finite={edge_finite} -> GATE6 {'PASS' if ok else 'FAIL'}",
          flush=True)
    return ok


# ----------------------------------------------------------------- driver
def validate(days, build_date):
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    gates = {"g2": True, "g3": True, "g5": True, "g6": True}
    leak_max = 0.0
    for d in days:
        out = p.join(OUT_DIR, f"{d}.npz")
        print(f"\n========== building + validating {d} ==========", flush=True)
        st, res = build_one_day(d, out)
        print(f"  built N={st['N']} valid={st['valid']} Xspot_std={st['Xspot_std']:.3f} "
              f"Xperp_std={st['Xperp_std']:.3f} n_nan={st['n_nan']} "
              f"yperp600_std={st['yperp600_std_bps']:.2f}bps {st['mb']:.1f}MB {st['secs']:.1f}s",
              flush=True)
        g2 = gate2_feature_validity(d, res)
        if g2 is not None:
            gates["g2"] &= g2
        gates["g3"] &= gate3_targets_leakfree(d, res)
        gates["g5"] &= gate5_newfeat_leakfree(d)
        gates["g6"] &= gate6_finite_bounded(d, res)

    B._write_meta(build_date, days, leak=leak_max)
    print("\n[validate] " + "  ".join(f"GATE_{k}={'PASS' if v else 'FAIL'}"
                                       for k, v in gates.items()), flush=True)
    print("[validate] NOTE gate1 (source grep) + gate4 (training acceptance) run "
          "separately; see MANIFEST.md.", flush=True)
    if not all(gates.values()):
        sys.exit(1)
