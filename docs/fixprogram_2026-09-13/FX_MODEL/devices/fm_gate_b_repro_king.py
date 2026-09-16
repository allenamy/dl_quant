#!/usr/bin/env python3
"""fm_gate_b_repro_king.py -- GATE B-REPRO, KING side. pod2, READ-ONLY, CPU only.

FROZEN PREREG (sha256 d17ea08949e8d2c731327b75d14dc3c4cf5bc75ec5584b5a63ddfc84fe73f671) section 2.1, and the lead's
ruling that this is a COMMON precondition: **any historical OOF arm is unavailable until its checkpoint can be
certified reproducible.**

King differs from DL in BOTH failure modes, which is why it is a separate device (lead: "do not write them as two
instances of one constraint"):
  - King has **no feature normalisation** -- LightGBM is fit on raw features -- so there is no mu/sd to freeze. What
    must be frozen instead is the **feature order and support**, and the exporter already asserts it:
    `[names[k] for k in keep] == PINS["keep_names"]` (pod_export_bundle_v4.py:47). This device re-asserts it.
  - Only the SHIPPED booster was saved. `slow2026.txt` exists; the 2024 and 2025 fold boosters are the local variable
    `g2` (L75-76) and were **never written to disk**.

So the two halves of this gate are of different strength, and are reported separately rather than averaged:
  K-2026  NO RECONSTRUCTION NEEDED. Load the saved `slow2026.txt`, predict, compare to the stored PRED. This is a pure
          check that the row construction (X/Y/A) here is identical to the exporter's -- if it fails, nothing else in
          this device is interpretable, and the 2024/2025 result would be meaningless.
  K-2024 / K-2025  RECONSTRUCTION. Re-fit with the exporter's exact parameters on the exact same rows, predict, compare
          to the stored PRED. LightGBM is deterministic given identical data, parameters and threading -- but thread
          count affects histogram summation order, and the original run's effective thread count is not recorded. That
          risk is declared HERE, before running, not after seeing the answer.

Reproduced verbatim from pod_export_bundle_v4.py (sha 42555a37c0cd3a7e128ac8823a8bec3e2f77a1230d205707b046aca20eed5118):
  L46  keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
  L47  assert [names[k] for k in keep] == PINS["keep_names"]
  L53-60 per anchor: ok = isfinite(y4[i, m]); skip if ok.sum() < 50; rr = rankdata(yv[ok]) / max(ok.sum()-1, 1) - 0.5
  L63  tr = YRA < 2026; te = YRA == 2026
  L67-68 / L75-76  LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63, subsample=0.8,
                   colsample_bytree=0.8, n_jobs=100, verbose=-1)
  L79-81 / L90-92  PRED[a, m[okm]] = pv[sel]

This device does NOT run the exporter. The exporter writes a bundle and can `sys.exit(3)` on its own export gates;
running it would touch `BUNDLE_OUT`. Nothing is written here except the receipt.

Usage: FM_GK_OUT=<receipt.json> [FM_GK_REFIT=1] python3 fm_gate_b_repro_king.py
       FM_GK_REFIT=0 runs only K-2026 (cheap); =1 adds the 2024/2025 refits.
"""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import rankdata

T0 = time.time()
OUT = os.environ["FM_GK_OUT"]
REFIT = int(os.environ.get("FM_GK_REFIT", "1"))
META = "/workspace/data/wide_fea_v4_meta.npz"
FEAP = "/workspace/data/wide_fea_v4.npy"
PINSP = "/workspace/live_pins.json"
STORED = "/workspace/review_scratch/king_v4/SLOW_v4.npy"
BOOST = "/workspace/shadow_bundle_v4/slow2026.txt"
EXPORTER = "/workspace/review_scratch/pod_export_bundle_v4.py"
EXPECT = {META: "12ea42c4557093f10f954f648db9239f4dd8283ea365ba299f31bd81e7e5ab51",
          FEAP: "268f6c9c247cdf1fffb6cea442437ab21b3f13993f9d821cfb09f417417cad7a",
          PINSP: "fd27fe485417d307e5bc41ee382a2db098118bee1fe2a13ebde98c7e7d3caece",
          BOOST: "f23657710f3a6d0068bca8a95082965d694de805195ef143be64951c0f2f203a"}


def log(*a):
    print("[%7.1fs]" % (time.time() - T0), *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def main():
    import lightgbm as lgb
    rc = {"device": os.path.basename(__file__), "self_sha256": sha(os.path.abspath(__file__)),
          "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "python": sys.version.split()[0], "numpy": np.__version__, "lightgbm": lgb.__version__,
          "prereg_sha256": "d17ea08949e8d2c731327b75d14dc3c4cf5bc75ec5584b5a63ddfc84fe73f671",
          "gate": "B-REPRO (king)", "device_used": "cpu", "writes_nothing_but_the_receipt": True,
          "threading_caveat": ("LightGBM is deterministic given identical data, params AND thread count; thread count "
                               "changes histogram summation order. The original run's effective thread count is not "
                               "recorded anywhere, so a 2024/2025 mismatch may be threading rather than a real "
                               "irreproducibility. Declared before running. A failure is NOT waved through."),
          "omp_num_threads_env": os.environ.get("OMP_NUM_THREADS"), "inputs": {}}
    for p, want in EXPECT.items():
        got = sha(p)
        rc["inputs"][p] = got
        assert got == want, ("INPUT SHA MISMATCH", p, got, want)
    rc["inputs"][STORED] = sha(STORED)
    log("input shas asserted")

    MT = np.load(META, allow_pickle=True)
    E_ts = MT["E_ts"].astype(np.int64)
    members = MT["members"]
    y4 = MT["y4"]
    names = [str(n) for n in MT["names"]]
    PINS = json.load(open(PINSP))
    FEA = np.load(FEAP)
    nA, NW = len(E_ts), 829
    yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])

    keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
    parity = ([names[k] for k in keep] == PINS["keep_names"])
    rc["K0_feature_order_and_support"] = {"PASS": bool(parity), "n_kept": len(keep), "n_builder_cols": len(names),
                                          "meaning": "this is what king's arm B must freeze in place of mu/sd "
                                                     "(pod_export_bundle_v4.py:47)"}
    assert parity, "keep_names parity failed"
    log("K0 feature order/support PASS; kept", len(keep), "of", len(names))

    rows_X, rows_y, rows_a = [], [], []
    for i in range(nA):
        m = members[i]
        yv = y4[i, m]
        ok = np.isfinite(yv)
        if ok.sum() < 50:
            continue
        rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5
        rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))
        rows_y.append(rr.astype(np.float32))
        rows_a.append(np.full(ok.sum(), i, np.int32))
    X = np.concatenate(rows_X); Y = np.concatenate(rows_y); A = np.concatenate(rows_a)
    del rows_X, rows_y, rows_a, FEA
    YRA = yrs[A]
    rc["rows"] = {"n_rows": int(X.shape[0]), "n_cols": int(X.shape[1]),
                  "by_year": {str(y): int((YRA == y).sum()) for y in sorted(set(YRA.tolist()))}}
    log("rows built", X.shape)

    P_stored = np.load(STORED)
    assert P_stored.shape == (nA, NW), P_stored.shape

    def compare(yv, pv, a_te):
        """scatter predictions the way the exporter does and compare to the stored PRED for that year"""
        rep = np.full((nA, NW), np.nan, np.float32)
        for a in np.unique(a_te):
            sel = a_te == a
            m = members[a]
            okm = np.isfinite(y4[a, m])
            rep[a, m[okm]] = pv[sel]
        rowsel = (yrs == yv)
        fs, fr = np.isfinite(P_stored[rowsel]), np.isfinite(rep[rowsel])
        pat = bool(np.array_equal(fs, fr))
        both = fs & fr
        mx = float(np.max(np.abs(P_stored[rowsel][both] - rep[rowsel][both]))) if both.any() else float("nan")
        eq = int((P_stored[rowsel][both] == rep[rowsel][both]).sum())
        return {"year": int(yv), "nan_pattern_equal": pat, "cells_compared": int(both.sum()),
                "cells_bitwise_equal": eq, "maxabs": mx,
                "PASS_bitwise": bool(pat and both.any() and eq == int(both.sum())),
                "PASS_1e-5": bool(pat and mx <= 1e-5)}

    results = {}
    # ---- K-2026: the SAVED booster, no reconstruction. If this fails nothing else is interpretable. ----
    te = YRA == 2026
    bst = lgb.Booster(model_file=BOOST)
    pv = bst.predict(X[te])
    results["K_2026_saved_booster"] = compare(2026, pv, A[te])
    results["K_2026_saved_booster"]["reconstruction_needed"] = False
    log("K-2026", results["K_2026_saved_booster"])

    if REFIT:
        for YV in (2024, 2025):
            t1 = time.time()
            tr_, te_ = YRA < YV, YRA == YV
            g2 = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=63,
                                   subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(X[tr_], Y[tr_])
            pv2 = g2.predict(X[te_])
            r = compare(YV, pv2, A[te_])
            r["reconstruction_needed"] = True
            r["n_train_rows"] = int(tr_.sum())
            r["wall_s"] = round(time.time() - t1, 1)
            results["K_%d_refit" % YV] = r
            log("K-%d" % YV, r)
    else:
        rc["refit_skipped"] = "FM_GK_REFIT=0"

    rc["per_fold"] = results
    saved_ok = results["K_2026_saved_booster"]["PASS_1e-5"]
    refits = [v for k, v in results.items() if v.get("reconstruction_needed")]
    refit_ok = all(v["PASS_1e-5"] for v in refits) if refits else None
    rc["summary"] = {"K0_feature_parity": bool(parity),
                     "K_2026_saved_booster_PASS": bool(saved_ok),
                     "K_2026_bitwise": results["K_2026_saved_booster"]["PASS_bitwise"],
                     "refits_PASS": refit_ok, "n_refits": len(refits)}
    if not saved_ok:
        rc["GATE_B_REPRO_KING"] = "INVALID"
        rc["consequence"] = ("The SAVED booster does not reproduce the stored PRED, so the row construction here is not "
                             "the exporter's. Nothing in this device is interpretable and no conclusion about arm B "
                             "may be drawn from it.")
    elif refit_ok is None:
        rc["GATE_B_REPRO_KING"] = "PARTIAL (2026 only)"
        rc["consequence"] = "Row construction certified against the saved booster; the 2024/2025 refits were not run."
    elif refit_ok:
        rc["GATE_B_REPRO_KING"] = "PASS"
        rc["consequence"] = ("arm B is AVAILABLE for the king family: the 2024/2025 fold boosters, which were never "
                             "saved, are reproducible from identical data and parameters.")
    else:
        rc["GATE_B_REPRO_KING"] = "FAIL"
        rc["consequence"] = ("arm B is NOT AVAILABLE for the king family on the historical folds. Per the frozen prereg "
                             "this is reported as unavailable and NOT substituted or approximated. Note the threading "
                             "caveat above: the cause may be thread-count-dependent histogram summation rather than "
                             "genuine irreproducibility, and that distinction is itself unresolved, not assumed away.")
    rc["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rc["wall_s"] = round(time.time() - T0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    json.dump(rc, open(OUT, "w"), indent=1, default=float)
    print("GATE_B_REPRO_KING=%s  K0=%s  2026=%s(bitwise %s)  refits=%s  wall=%.0fs"
          % (rc["GATE_B_REPRO_KING"], parity, saved_ok, results["K_2026_saved_booster"]["PASS_bitwise"],
             refit_ok, rc["wall_s"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
