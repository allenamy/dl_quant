#!/usr/bin/env python3
"""news2_king_refit_perturb.py -- two single-variable King refits, to separate the two candidates.

Pre-registration: docs/PREREG_king_refit_perturbations_2026-09-24.md (committed ebe3448a2, BEFORE any
number here). The reading rules are lead's and are frozen there.

CANDIDATES (each on its own sufficient to make P differ everywhere):
  (a) the 136 training pairs NC lacks (anchor 1641571200, inside every fold's training window)
  (b) fund_ema / fund_now, whose divergence traces to the D10 iv-source choice

ARMS -- each changes ONE thing, everything else bitwise unchanged:
  baseline   unmodified NC inputs. Its P MUST equal the archived KING_OOF.npz bitwise, or this
             device's training path is not equivalent to the original and NOTHING below it holds.
  (a) +136rows   inject the researcher's 136 rows at anchor 1641571200
  (b) +resfund   overwrite fund_ema/fund_now with the researcher's values on shared pairs

STATED LIMITS (from the pre-registration, repeated because they bound the reading):
  - (b) can only replace the 2,742,865 SHARED pairs. The 42,889 NC-only pairs have no researcher
    value and keep NC's; counted in the receipt. This is a NAMED PARTIAL replacement, not "the
    funding columns swapped".
  - (a)'s injected rows necessarily carry the RESEARCHER's feature values (their only source), so (a)
    is not a pure row-count change; it also introduces 136 rows of researcher-caliber features.
  - each arm is ONE perturbation, not a distribution. Nothing here bounds the variance of perturbations.

NOT MEASURED: book layer (needs the engine); which side is right (contract question).
"""
import argparse, calendar, datetime, hashlib, json, os, sys, time

import numpy as np
from scipy.stats import rankdata

SELF = os.path.realpath(__file__)
PARAMS = dict(n_estimators=400, learning_rate=.05, num_leaves=63, subsample=.8,
              colsample_bytree=.8, n_jobs=8, verbose=-1, random_state=0)
INJECT_ANCHOR = 1641571200


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def build_target(y, pa, ps, n_anchor):
    """verbatim from news2_train_king.py: within-anchor rank of the raw label over members with >=50 finite"""
    target = np.full(len(pa), np.nan, np.float32)
    st = np.searchsorted(pa, np.arange(n_anchor + 1))
    for i in range(n_anchor):
        ixx = np.arange(st[i], st[i + 1])
        if ixx.size == 0:
            continue
        vals = y[i, ps[ixx]]
        good = np.isfinite(vals)
        if good.sum() >= 50:
            target[ixx[good]] = rankdata(vals[good]) / max(good.sum() - 1, 1) - .5
    return target


def run_king(x, pa, ps, target, a, y, n_sym, fold_rows, log):
    import lightgbm as lgb
    pred = np.full((len(a), n_sym), np.nan, np.float32)
    utc = lambda yr, mo=1, day=1: calendar.timegm((yr, mo, day, 0, 0, 0))
    specs = [("2022H2_WARMUP", utc(2022, 7), utc(2023))] + \
            [(str(yr), utc(yr), utc(yr + 1)) for yr in (2023, 2024, 2025, 2026)]
    folds = []
    for tag, start, end in specs:
        train, test = fold_rows(a, start, end, 60)
        tr = np.isin(pa, train) & np.isfinite(target)
        te = np.isin(pa, test)
        t0 = time.monotonic()
        model = lgb.LGBMRegressor(**PARAMS).fit(x[tr], target[tr])
        pred[pa[te], ps[te]] = model.predict(x[te])
        folds.append({"fold": tag, "train_pairs": int(tr.sum()), "scored_pairs": int(te.sum()),
                      "seconds": round(time.monotonic() - t0, 1)})
        log(f"    {tag}: train {int(tr.sum())} scored {int(te.sum())} "
            f"({folds[-1]['seconds']}s)")
    return pred, folds


def sp_median(P, Q, rowP, rowQ, off, m, anchors):
    """per-year within-anchor spearman between two prediction panels on the same members.
    rowP/rowQ map NC's anchor position -> that panel's own row (-1 = anchor absent from that panel).
    The two panels do NOT share an anchor axis (NC 10333 vs researcher 10321), so indexing one with
    the other's position silently reads the wrong anchor -- that is what crashed the first run."""
    out = {}
    for i, t in enumerate(anchors):
        rp, rq = rowP[i], rowQ[i]
        if rp < 0 or rq < 0:
            continue
        b, e = off[i], off[i + 1]
        cols = m[b:e]
        p, q = P[rp, cols], Q[rq, cols]
        f = np.isfinite(p) & np.isfinite(q)
        if f.sum() < 5:
            continue
        pr = np.argsort(np.argsort(p[f])).astype(np.float64)
        qr = np.argsort(np.argsort(q[f])).astype(np.float64)
        sp_, sq_ = pr.std(), qr.std()
        if sp_ < 1e-15 or sq_ < 1e-15:
            continue
        r = float(((pr - pr.mean()) * (qr - qr.mean())).mean() / (sp_ * sq_))
        y = datetime.datetime.utcfromtimestamp(int(t)).year
        out.setdefault(y, []).append(r)
    return {str(y): {"n_anchors": len(v), "median": float(np.median(v)),
                     "p10": float(np.percentile(v, 10))} for y, v in sorted(out.items())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nc-features", required=True)
    ap.add_argument("--nc-king", required=True)
    ap.add_argument("--researcher-king", required=True)
    ap.add_argument("--researcher-panel", required=True)
    ap.add_argument("--researcher-axis", required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--keep-idx-config", required=True)
    ap.add_argument("--devices-dir", required=True)
    ap.add_argument("--arms", default="baseline,a,b")
    ap.add_argument("--out", required=True)
    a_ = ap.parse_args()

    def log(*x):
        print(time.strftime("%H:%M:%S", time.gmtime()), *x, flush=True)

    sys.path.insert(0, a_.devices_dir)
    from king_folds import fold_rows

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "prereg": "docs/PREREG_king_refit_perturbations_2026-09-24.md @ ebe3448a2",
           "status": "SINGLE_VARIABLE_PERTURBATION_NOT_BOOK_LAYER",
           "params": PARAMS,
           "king_folds_sha256": sha(os.path.join(a_.devices_dir, "king_folds.py")),
           "limits": [
               "(b) replaces only the 2,742,865 shared pairs; NC-only pairs keep NC values (counted)",
               "(a)'s injected rows carry researcher feature values -- not a pure row-count change",
               "each arm is ONE perturbation, not a distribution"],
           "inputs": {}}
    for k, p in (("nc_features", a_.nc_features), ("nc_king", a_.nc_king),
                 ("researcher_king", a_.researcher_king), ("researcher_panel", a_.researcher_panel),
                 ("targets", a_.targets)):
        rec["inputs"][k] = {"path": p, "bytes": os.path.getsize(p)}

    F = np.load(a_.nc_features, allow_pickle=False)
    T = np.load(a_.targets, allow_pickle=True)
    NK = np.load(a_.nc_king, allow_pickle=False)
    RK = np.load(a_.researcher_king, allow_pickle=False)
    R = np.load(a_.researcher_panel, allow_pickle=False)
    AX = np.load(a_.researcher_axis, allow_pickle=False)

    a = F["anchors"].astype(np.int64); syms = F["symbols"]; off = F["off"].astype(np.int64)
    cnt = F["count"].astype(np.int64)
    ya = T["E_ts"].astype(np.int64)
    y = np.full((len(a), len(syms)), np.nan, np.float32)
    ix = np.searchsorted(ya, a); ok = (ix < len(ya)) & (ya[np.minimum(ix, len(ya) - 1)] == a)
    y[ok] = T["y4s"][ix[ok]]
    pa0 = np.repeat(np.arange(len(a)), cnt).astype(np.int64)
    ps0 = F["m"].astype(np.int64)
    x0 = F["X78"].astype(np.float32)
    assert x0.shape[1] == 78 and len(pa0) == len(ps0) == len(x0) == off[-1]

    cfg = json.load(open(a_.keep_idx_config))
    ki = list(cfg["keep_idx"])
    names78 = [str(R["names"][i]) for i in ki]
    j_fe, j_fn = names78.index("fund_ema"), names78.index("fund_now")
    rec["fund_columns_in_X78"] = {"fund_ema": j_fe, "fund_now": j_fn}

    r_ts_all = AX["E_ts"].astype(np.int64)
    r_anchor = r_ts_all[R["pair_a"].astype(np.int64)]
    r_sym = R["pair_s"].astype(np.int64)
    XR78 = np.asarray(R["X"])[:, ki]

    SCALE = 1024
    k_r = r_anchor * SCALE + r_sym
    k_n = np.repeat(a, cnt) * SCALE + ps0
    common, ir, inn = np.intersect1d(k_r, k_n, assume_unique=True, return_indices=True)
    rec["shared_pairs"] = int(common.size)
    rec["nc_only_pairs_not_replaceable"] = int(k_n.size - common.size)

    arms = [s.strip() for s in a_.arms.split(",") if s.strip()]
    preds, fold_info = {}, {}

    if "baseline" in arms:
        log("arm baseline (must reproduce KING_OOF.npz bitwise)")
        tgt = build_target(y, pa0, ps0, len(a))
        preds["baseline"], fold_info["baseline"] = run_king(x0, pa0, ps0, tgt, a, y, len(syms), fold_rows, log)

    if "a" in arms:
        log("arm (a) +136rows")
        ai = int(np.flatnonzero(a == INJECT_ANCHOR)[0])
        sel = r_anchor == INJECT_ANCHOR
        n_inj = int(sel.sum())
        rec["arm_a_injected_rows"] = n_inj
        rec["arm_a_anchor"] = {"ts": INJECT_ANCHOR,
                               "utc": datetime.datetime.utcfromtimestamp(INJECT_ANCHOR).strftime("%Y-%m-%dT%H:%MZ"),
                               "nc_rows_before": int(cnt[ai])}
        pos = int(off[ai])          # insert at this anchor's (empty) slot to keep pa sorted
        xa = np.concatenate([x0[:pos], XR78[sel].astype(np.float32), x0[pos:]])
        paa = np.concatenate([pa0[:pos], np.full(n_inj, ai, np.int64), pa0[pos:]])
        psa = np.concatenate([ps0[:pos], r_sym[sel], ps0[pos:]])
        tgt = build_target(y, paa, psa, len(a))
        preds["a"], fold_info["a"] = run_king(xa, paa, psa, tgt, a, y, len(syms), fold_rows, log)
        del xa, paa, psa

    if "b" in arms:
        log("arm (b) +resfund")
        xb = x0.copy()
        xb[inn, j_fe] = XR78[ir, j_fe].astype(np.float32)
        xb[inn, j_fn] = XR78[ir, j_fn].astype(np.float32)
        rec["arm_b_cells_replaced"] = {"fund_ema": int(common.size), "fund_now": int(common.size)}
        finite_ok = bool(np.isfinite(xb).all())
        rec["arm_b_all_finite_after_replacement"] = finite_ok
        if not finite_ok:
            rec["verdict"] = "UNAVAILABLE"
            rec["why"] = ("replacement introduced non-finite values; the trainer asserts isfinite, so "
                          "this arm is not runnable without changing the trainer")
            json.dump(rec, open(a_.out, "w"), indent=2)
            print("KING_REFIT VERDICT=UNAVAILABLE non-finite after replacement"); return 2
        tgt = build_target(y, pa0, ps0, len(a))
        preds["b"], fold_info["b"] = run_king(xb, pa0, ps0, tgt, a, y, len(syms), fold_rows, log)
        del xb

    rec["folds"] = fold_info

    # ---- RED CONTROL ----
    NP_, RP_ = np.asarray(NK["P"]), np.asarray(RK["P"])
    ctrl = {}
    if "baseline" in preds:
        b = preds["baseline"]
        both_nan = (~np.isfinite(b)) & (~np.isfinite(NP_))
        eq = (b == NP_) | both_nan
        ctrl["baseline_vs_archived_frac_identical"] = float(eq.mean())
        ctrl["baseline_reproduces_archived_bitwise"] = bool(eq.all())
    else:
        ctrl["baseline_reproduces_archived_bitwise"] = None
    ctrl["baseline_green"] = bool(ctrl.get("baseline_reproduces_archived_bitwise"))
    rec["red_control"] = ctrl

    if not ctrl["baseline_green"]:
        rec["verdict"] = "UNAVAILABLE"
        rec["why"] = ("red control: this device's training path did not reproduce the archived "
                      "KING_OOF.npz bitwise, so no arm below it can be read")
        json.dump(rec, open(a_.out, "w"), indent=2)
        print(f"KING_REFIT VERDICT=UNAVAILABLE baseline reproduced "
              f"{ctrl.get('baseline_vs_archived_frac_identical')} of cells"); return 2

    # ---- comparisons ----
    json.dump(rec, open(a_.out, "w"), indent=2)      # persist the red control before anything can crash
    m_arr = ps0
    nc_ts = NK["E_ts"].astype(np.int64)
    rk_ts = RK["E_ts"].astype(np.int64)
    pos_nc = {int(t): i for i, t in enumerate(nc_ts)}
    pos_rk = {int(t): i for i, t in enumerate(rk_ts)}
    row_self = np.arange(len(a))                      # arms are built on NC's axis
    row_nc = np.array([pos_nc.get(int(t), -1) for t in a])
    row_rk = np.array([pos_rk.get(int(t), -1) for t in a])
    rec["axis_rows"] = {"nc_anchors": int(nc_ts.size), "researcher_anchors": int(rk_ts.size),
                        "nc_anchors_absent_from_researcher": int((row_rk < 0).sum())}
    rec["reference_baseline_nc_vs_researcher"] = sp_median(NP_, RP_, row_nc, row_rk, off, m_arr, a)
    cmp_out = {}
    for arm in ("a", "b"):
        if arm not in preds:
            continue
        cmp_out[arm] = {
            "vs_nc": sp_median(preds[arm], NP_, row_self, row_nc, off, m_arr, a),
            "vs_researcher": sp_median(preds[arm], RP_, row_self, row_rk, off, m_arr, a),
            "bitwise_identical_to_nc": bool((((preds[arm] == NP_) |
                                              ((~np.isfinite(preds[arm])) & (~np.isfinite(NP_)))).all())),
        }
    rec["arms"] = cmp_out
    rec["verdict"] = "MEASURED"
    json.dump(rec, open(a_.out, "w"), indent=2)

    print(f"KING_REFIT VERDICT={rec['verdict']}")
    print(f"  red control: baseline reproduces archived KING_OOF bitwise = "
          f"{ctrl['baseline_reproduces_archived_bitwise']} "
          f"(frac identical {ctrl.get('baseline_vs_archived_frac_identical')})")
    print(f"  shared pairs {rec['shared_pairs']}, NC-only not replaceable "
          f"{rec['nc_only_pairs_not_replaceable']}")
    ref = rec["reference_baseline_nc_vs_researcher"]
    ys = sorted(ref)
    print("  REFERENCE  NC vs researcher (median within-anchor spearman):")
    print("    " + "  ".join(f"{y}={ref[y]['median']:.4f}" for y in ys))
    for arm, d in cmp_out.items():
        print(f"  ARM ({arm}) bitwise_identical_to_nc={d['bitwise_identical_to_nc']}")
        print("    vs NC        : " + "  ".join(
            f"{y}={d['vs_nc'].get(y, {}).get('median', float('nan')):.4f}" for y in ys))
        print("    vs researcher: " + "  ".join(
            f"{y}={d['vs_researcher'].get(y, {}).get('median', float('nan')):.4f}" for y in ys))
    return 0


if __name__ == "__main__":
    sys.exit(main())
