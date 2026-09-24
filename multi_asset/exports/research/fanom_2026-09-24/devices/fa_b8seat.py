"""B8 seat recomputation: derive WL for an arbitrary msharpe_look from the SAVED legs.npz, with no legs rebuild.

Why this is possible (PREREG_fresh_rootcause_B8_2026-09-24.md §1): fresh_legs.py L63-70 computes w3 from exactly two
things -- the running LR history and P["msharpe_look"] -- and LR's per-anchor values are what legs.npz stores as "LR"
(the array named LRm in the source). Nothing in w3 touches the rolling cache or the feature panel, both of which are
deleted.

Reconstruction (read off fresh_legs.py L45-84):
  * LRm row j is written at loop step j+1 (L62), with the value appended to the LR lists at L61 of that same step.
    => the LR list, in append order, is exactly the finite rows of LRm in increasing row order.
  * w3 for anchor i is computed at L64-70 AFTER the append of step i, so it sees appends from steps <= i,
    i.e. LRm rows <= i-1.
  * WL[i] is stored only for recorded anchors (L82); elsewhere it stays NaN.

G1 (gate, asserted BEFORE any short window is produced): at look=900 this must reproduce legs.npz's WL BITWISE on the
ready rows. If it does not, the operator I am recomputing is not the operator that produced the book, and the short-window
numbers would be meaningless. Device exits nonzero and writes no short-window output.

Vacuity guards (the "zero measurement" family): the comparison is only meaningful if (a) some rows were compared, and
(b) the look branch actually engaged, i.e. some compared row differs from the [1/3,1/3,1/3] fallback. Both are asserted.
"""
import os, sys, json, time, hashlib
import numpy as np

ROOTS = {"FRESH": "/dev/shm/fresh_2026-09-23", "NEWS": "/dev/shm/news_2026-09-23"}
OUT = "/dev/shm/fanom_2026-09-24"
LEGS = ("king", "rev24", "fund")
THIRD = np.float32(1.0 / 3.0)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def seat_series(LRm, look, n):
    """WL[i] for every i, using the finite LRm rows with index <= i-1. Mirrors fresh_legs.py L64-70."""
    fin = np.isfinite(LRm).all(1)
    hist = []                                   # append order == increasing row order
    WL = np.full((n, 3), np.nan, np.float64)
    for i in range(n):
        if i - 1 >= 0 and fin[i - 1]:
            hist.append(LRm[i - 1])
        if len(hist) >= look:
            r = np.stack([np.array([h[li] for h in hist[-look:]]) for li in range(3)])
            shp = r.mean(1) / (r.std(1) + 1e-9)
            shp = np.maximum(shp, 0.0)
            w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)
        else:
            w3 = np.array([1 / 3] * 3)
        WL[i] = w3
    return WL


def main():
    t0 = time.time()
    looks = [int(x) for x in sys.argv[1:]] or [900]
    rec = {"device": os.path.basename(os.path.abspath(__file__)), "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "prereg": {"path": "docs/PREREG_fresh_rootcause_B8_2026-09-24.md", "commit": "38f4c0fbd"},
           "reconstruction": "LR list = finite rows of legs.npz['LR'] in row order; WL[i] uses rows <= i-1",
           "looks": looks, "arms": {}, "G1": {}}
    g1_all_ok = True
    for arm, root in ROOTS.items():
        p = f"{root}/work/legs.npz"
        z = np.load(p, allow_pickle=True)
        LRm = np.asarray(z["LR"], np.float64); WL0 = np.asarray(z["WL"]); ready = np.asarray(z["ready"], bool)
        n = LRm.shape[0]
        assert WL0.dtype == np.float32, f"{arm}: WL dtype {WL0.dtype}, expected float32"
        a = {"legs_npz": p, "legs_sha256": sha(p), "n_anchors": int(n), "n_ready": int(ready.sum()),
             "n_lr_finite": int(np.isfinite(LRm).all(1).sum())}

        # ---- G1: look=900 must reproduce the stored WL bitwise on ready rows ----
        look900 = seat_series(LRm, 900, n).astype(np.float32)
        cmp_rows = np.flatnonzero(ready)
        same = np.array_equal(look900[cmp_rows].view(np.uint32), WL0[cmp_rows].view(np.uint32))
        nth = int((np.abs(look900[cmp_rows] - THIRD) > 0).any(1).sum())   # rows where the look branch bit
        g1 = {"compared_rows": int(cmp_rows.size), "bitwise_identical": bool(same),
              "rows_not_equal_to_one_third": nth,
              "n_mismatch_rows": int((~(look900[cmp_rows].view(np.uint32) == WL0[cmp_rows].view(np.uint32)).all(1)).sum()),
              "max_abs_diff": float(np.nanmax(np.abs(look900[cmp_rows] - WL0[cmp_rows]))) if cmp_rows.size else None}
        g1["vacuity_compared_rows_gt_0"] = bool(cmp_rows.size > 0)
        g1["vacuity_look_branch_engaged"] = bool(nth > 0)
        g1["verdict"] = "PASS" if (same and cmp_rows.size > 0 and nth > 0) else "FAIL"
        if g1["verdict"] != "PASS":
            g1_all_ok = False
        rec["G1"][arm] = g1
        a["stored_WL_ready_mean"] = [round(float(x), 6) for x in np.nanmean(WL0[cmp_rows], 0)]
        rec["arms"][arm] = a

    rec["G1"]["all_arms_pass"] = bool(g1_all_ok)
    rec["seconds"] = round(time.time() - t0, 1)

    # short windows are produced ONLY if G1 is green on both arms
    if g1_all_ok:
        os.makedirs(f"{OUT}/b8", exist_ok=True)
        for arm, root in ROOTS.items():
            z = np.load(f"{root}/work/legs.npz", allow_pickle=True)
            LRm = np.asarray(z["LR"], np.float64); ready = np.asarray(z["ready"], bool); n = LRm.shape[0]
            for lk in looks:
                if lk == 900:
                    continue
                WLk = seat_series(LRm, lk, n).astype(np.float32)
                o = f"{OUT}/b8/WL_{arm}_look{lk}.npz"
                np.savez(o, WL=WLk, ready=ready, E_ts=np.asarray(z["E_ts"]), look=np.int64(lk))
                nd = int((~(WLk[ready].view(np.uint32) == np.asarray(z["WL"])[ready].view(np.uint32)).all(1)).sum())
                rec["arms"][arm][f"look{lk}"] = {"out": o, "sha256": sha(o), "rows_differing_from_look900": nd,
                                                 "mean_WL_ready": [round(float(x), 6) for x in np.nanmean(WLk[ready], 0)]}
                assert nd > 0, f"{arm} look={lk}: seat identical to look=900 on every ready row -- switch not wired"

    rp = f"{OUT}/receipts/FA_B8_SEAT.json"
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    json.dump(rec, open(rp, "w"), indent=1)
    print("FA_B8_SEAT " + ("G1_PASS" if g1_all_ok else "G1_FAIL") + " " +
          json.dumps({k: {kk: rec["G1"][k][kk] for kk in ("verdict", "compared_rows", "n_mismatch_rows", "rows_not_equal_to_one_third")}
                      for k in ("FRESH", "NEWS")}), flush=True)
    assert os.path.exists(rp), "receipt not written"
    sys.exit(0 if g1_all_ok else 3)


if __name__ == "__main__":
    main()
