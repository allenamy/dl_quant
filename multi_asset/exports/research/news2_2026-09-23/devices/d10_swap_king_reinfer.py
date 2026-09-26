#!/usr/bin/env python3
"""d10_swap_king_reinfer.py -- line D control cell, stage 1: SAME King boosters, funding inputs swapped (DECISION_RULE_D10_stage2 s4,
"model unchanged, only the features swapped"; PLAN_funding_only_control_cell rev 1).

Why this stage exists: the 09-26 plan (e786a9ade) said "King OOF not recomputed", which contradicts the cell's definition -- King's
X78 carries fe_v / fn_v (FE_ANCH cols 80/81 = X78 cols 76/77, bundle keep_idx), so without re-inference the King leg never sees the
swapped features. The per-fold boosters and the per-anchor model sha are archived, so the swap is exact.

Order (each step must be green before the next is even computed; red => STOP, nothing written):
  C0 column map  : NEWS_FEATURES X78[:,76] == f32(nan_to_num(fe_v)) and X78[:,77] == f32(nan_to_num(fn_v)) on every member row, bitwise
                   (proves WHICH columns are the funding inputs before replacing them; also X82[:,80:82] for the F10 stage);
  C1 identity    : each archived booster, reloaded from its text file, re-predicts its own fold's rows on the ORIGINAL X78 and must equal
                   KING_OOF.P bitwise (NaN pattern included). A reload that is not bitwise would make every swap delta uninterpretable;
  C1b red control: the same re-prediction with one X78 cell of col 76 perturbed must NOT be bitwise equal (else C1 cannot see inputs);
  SWAP           : X78 cols 76/77 := rebuilt fe_v / fn_v (rebuilt_features_d10.npz, pinned) -> KING_OOF_SWAP.npz; input and output
                   difference profile reported as counts, split at the ledger cut (anchors after it have no rebuilt events).
No book-layer number is produced here.
"""
import argparse, hashlib, json, os, time
import numpy as np

KING_FOLDS = ["2022H2_WARMUP", "2023", "2024", "2025", "2026"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def stop(msg):
    print("STOP", msg, flush=True); raise SystemExit(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True); ap.add_argument("--features-sha", required=True)
    ap.add_argument("--rebuilt", required=True); ap.add_argument("--rebuilt-sha", required=True)
    ap.add_argument("--king-dir", required=True); ap.add_argument("--oof-sha", required=True)
    ap.add_argument("--ledger-cut", type=int, required=True, help="first epoch with no rebuilt events (ledger_full_ms end)")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    import lightgbm as lgb
    for p, s in ((a.features, a.features_sha), (a.rebuilt, a.rebuilt_sha), (os.path.join(a.king_dir, "KING_OOF.npz"), a.oof_sha)):
        if sha(p) != s: stop(f"sha {p}: {sha(p)[:12]} != pinned {s[:12]}")
    if os.path.exists(os.path.join(a.out_dir, "KING_OOF_SWAP.npz")): stop("refusing to overwrite")
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "lightgbm": lgb.__version__, "numpy": np.__version__,
           "inputs": {"features": [a.features, a.features_sha], "rebuilt": [a.rebuilt, a.rebuilt_sha], "king_oof": a.oof_sha},
           "ledger_cut": a.ledger_cut, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    F = np.load(a.features, allow_pickle=False); Rb = np.load(a.rebuilt, allow_pickle=False)
    K = np.load(os.path.join(a.king_dir, "KING_OOF.npz"), allow_pickle=False)
    A = F["anchors"].astype(np.int64); off = F["off"]; m = F["m"].astype(np.int64); cnt = F["count"]
    for k in ("anchors", "off", "m", "symbols"):
        if not np.array_equal(F[k], Rb[k]): stop(f"rebuilt {k} != NEWS_FEATURES {k}")
    if not (np.array_equal(K["E_ts"].astype(np.int64), A) and np.array_equal(K["symbols"], F["symbols"])): stop("KING_OOF axis != features")
    pa = np.repeat(np.arange(len(A)), cnt).astype(np.int64)
    X = F["X78"]; X82 = F["X82"]
    # C0
    c0 = {}
    for name, got, want in (("X78[:,76]==fe_v", X[:, 76], np.nan_to_num(F["fe_v"], nan=0).astype(np.float32)),
                            ("X78[:,77]==fn_v", X[:, 77], np.nan_to_num(F["fn_v"], nan=0).astype(np.float32)),
                            ("X82[:,80]==fe_v", X82[:, 80], np.nan_to_num(F["fe_v"], nan=0).astype(np.float32)),
                            ("X82[:,81]==fn_v", X82[:, 81], np.nan_to_num(F["fn_v"], nan=0).astype(np.float32))):
        c0[name] = int((got.view(np.uint32) != want.view(np.uint32)).sum())
    rec["C0_column_map_differing_rows"] = c0
    print("C0", c0, flush=True)
    if any(c0.values()): stop(f"C0 column map not bitwise: {c0}")
    # C1 identity + C1b red control, per fold
    P0 = K["P"]; msha = K["model_sha256"]
    boosters = {}
    for tag in KING_FOLDS:
        p = os.path.join(a.king_dir, f"king_{tag}.txt"); boosters[sha(p)] = (tag, lgb.Booster(model_file=p))
    if set(np.unique(msha[msha != ""])) - set(boosters): stop("an anchor's model sha has no archived booster")
    Pid = np.full(P0.shape, np.nan, np.float32); c1 = {}
    for h, (tag, b) in boosters.items():
        rows = np.flatnonzero(np.isin(pa, np.flatnonzero(msha == h)))
        Pid[pa[rows], m[rows]] = b.predict(X[rows]).astype(np.float32)
        c1[tag] = int(len(rows))
    same_nan = np.array_equal(np.isnan(Pid), np.isnan(P0))
    nbad = int((Pid[np.isfinite(P0)].view(np.uint32) != P0[np.isfinite(P0)].view(np.uint32)).sum()) if same_nan else -1
    rec["C1_identity"] = {"rows_per_fold": c1, "nan_pattern_equal": same_nan, "finite_cells_not_bitwise": nbad}
    print("C1", rec["C1_identity"], flush=True)
    if not same_nan or nbad: stop(f"C1 identity failed: nan_equal={same_nan} not_bitwise={nbad}")
    # C1b: perturb col 76 on the first 2026 row; re-prediction of that row must change (the path sees its input)
    h26 = next(h for h, (t, _) in boosters.items() if t == "2026")
    r = int(np.flatnonzero(np.isin(pa, np.flatnonzero(msha == h26)))[0])
    xr = X[r:r + 1].copy(); xr[0, 76] = xr[0, 76] + np.float32(1.0)
    moved = bool(boosters[h26][1].predict(xr)[0] != boosters[h26][1].predict(X[r:r + 1])[0])
    rec["C1b_red_control"] = {"row": r, "prediction_changed_by_col76_plus_1": moved}
    print("C1b", rec["C1b_red_control"], flush=True)
    if not moved: stop("C1b: prediction does not respond to col 76 -- the swap would be invisible")
    # SWAP
    fe1 = np.nan_to_num(Rb["fe_v"], nan=0).astype(np.float32); fn1 = np.nan_to_num(Rb["fn_v"], nan=0).astype(np.float32)
    Xs = X.copy(); Xs[:, 76] = fe1; Xs[:, 77] = fn1
    Ps = np.full(P0.shape, np.nan, np.float32)
    for h, (tag, b) in boosters.items():
        rows = np.flatnonzero(np.isin(pa, np.flatnonzero(msha == h)))
        Ps[pa[rows], m[rows]] = b.predict(Xs[rows]).astype(np.float32)
    pre = A[pa] < a.ledger_cut
    def prof(mask_rows):
        d76 = (Xs[mask_rows, 76].view(np.uint32) != X[mask_rows, 76].view(np.uint32)); d77 = (Xs[mask_rows, 77].view(np.uint32) != X[mask_rows, 77].view(np.uint32))
        pr = Ps[pa[mask_rows], m[mask_rows]]; p0 = P0[pa[mask_rows], m[mask_rows]]; fin = np.isfinite(p0)
        dp = np.abs(pr[fin].astype(np.float64) - p0[fin])
        return {"member_rows": int(mask_rows.sum()), "rows_fe_v_differs": int(d76.sum()), "rows_fn_v_differs": int(d77.sum()),
                "scored_rows": int(fin.sum()), "scored_rows_P_differs": int((dp > 0).sum()),
                "abs_dP_median_over_differing": float(np.median(dp[dp > 0])) if (dp > 0).any() else 0.0,
                "abs_dP_p99_over_differing": float(np.quantile(dp[dp > 0], .99)) if (dp > 0).any() else 0.0}
    rec["swap_profile"] = {"before_ledger_cut": prof(pre), "after_ledger_cut_NO_REBUILT_EVENTS": prof(~pre)}
    print("SWAP", json.dumps(rec["swap_profile"]), flush=True)
    os.makedirs(a.out_dir, exist_ok=True)
    op = os.path.join(a.out_dir, "KING_OOF_SWAP.npz")
    np.savez(op, P=Ps, E_ts=A, symbols=F["symbols"], model_sha256=msha)
    rec["output"] = {"path": op, "sha256": sha(op)}
    rp = os.path.join(a.out_dir, "KING_SWAP_RECEIPT.json")
    with open(rp, "w") as fh:
        fh.write(json.dumps(rec, indent=1)); fh.flush(); os.fsync(fh.fileno())
    print("KING_SWAP_DONE", rec["output"]["sha256"], flush=True)


if __name__ == "__main__":
    main()
