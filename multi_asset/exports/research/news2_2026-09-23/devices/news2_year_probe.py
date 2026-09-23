"""NEW_S2 cross-year probe: does each fix still DO anything at anchors from every year, and what does
it cost? (PREREG §5.2 / §7 P0 timing.)

The global gate runs on the nine archived live anchors, which are all 2026-09. Two of the fixes have a
reason to behave differently earlier in history:

  D7  the stable local trend replaces a GLOBAL cumulative-moment formula. The producer's mini pipeline
      only ever holds 40 days, so the cumulative log price never grows large and the cancellation the
      stable kernel exists to avoid may simply not arise. If so, D7 buys nothing and costs ~2x wall
      clock. This probe reports, per anchor, whether the EXTRACTED anchor row differs at all - raw and
      after the anchor rank the model actually consumes.
  D8  the tightened support gates remove cells wherever a window is not fully covered. Coverage is much
      worse in 2022-2023 than in 2026, so the damage has to be measured across years, not at one date.

Everything here is a feature-layer measurement: no model, no score, no book number.
usage: python news2_year_probe.py <work_dir> <out.json> [arms] [anchors]
"""
import json, os, subprocess, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import news2_hist_features as H
from news2_global_gate import build_tree, D7_COLS, D8_COLS

W2 = os.environ.get("NEWS2_W", "/dev/shm/news2_2026-09-23")
CACHE_AXES = os.environ["NEWS2_CACHE_AXES"]
CACHE_DATA = os.environ["NEWS2_CACHE_DATA"]
MASK = os.environ["NEWS2_MASK"]
HOLES = os.environ["NEWS2_HOLES"]
FUND = os.environ["NEWS2_FUND"]
CRYPTO = os.environ["NEWS2_CRYPTO"]
CFG = os.environ["NEWS2_CFG"]

DEFAULT_ANCHORS = [1657065600,   # 2022-07-06 08:00Z
                   1688097600,   # 2023-06-30 04:00Z  (the criterion window start)
                   1717200000,   # 2024-06-01 00:00Z
                   1756684800,   # 2025-09-01 00:00Z
                   1780272000]   # 2026-06-01 00:00Z


def main():
    work = os.path.abspath(sys.argv[1])
    out_path = os.path.abspath(sys.argv[2])
    arms = (sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else ["base", "D7", "D8", "all"])
    anchors = ([int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 and sys.argv[4] else DEFAULT_ANCHORS)
    os.makedirs(f"{work}/mini", exist_ok=True)
    t0 = time.time()

    ax = np.load(CACHE_AXES, allow_pickle=True)
    ts = ax["ts"].astype(np.int64)
    syms = [str(s) for s in ax["symbols"]]
    chn = [str(c) for c in ax["ch"]]
    # CACHE_DATA is either a .npy (mmap) or the source .npz (deflate-compressed, so it has to be read
    # into RAM once; pod2 has ~190 GB free and the array is 5.8 GB).
    if CACHE_DATA.endswith(".npz"):
        t_load = time.time()
        with np.load(CACHE_DATA) as z:
            D = z["data"]
            ts_src = z["ts"].astype(np.int64)
        assert np.array_equal(ts_src, ts), "cache npz ts axis does not match the axes file"
        print(f"cache loaded {D.shape} {D.dtype} in {time.time()-t_load:.0f}s", flush=True)
    else:
        D = np.load(CACHE_DATA, mmap_mode="r")
    assert D.shape[0] == len(ts) and D.shape[1] == len(syms), (D.shape, len(ts), len(syms))
    with np.load(HOLES) as z: hz = {"row": z["row"], "col": z["col"]}
    o = np.lexsort((hz["col"], hz["row"]))
    holes = (hz["row"][o].astype(np.int64), hz["col"][o].astype(np.int64))
    # Materialise every array ONCE. An NpzFile decompresses on every __getitem__, and these are read
    # per anchor; leaving them lazy cost ~70 s per anchor in the first probe run.
    with np.load(MASK) as z: mk = {"ts": z["ts"].astype(np.int64), "mask": z["mask"]}
    mts = mk["ts"]
    with np.load(FUND) as z: fr = {k: z[k] for k in ("anchors", "ema_acc", "last_ft", "last_rate", "last_iv")}
    fa = fr["anchors"].astype(np.int64)
    with np.load(CRYPTO) as z: crypto = z["crypto"]
    cfg = json.load(open(CFG))

    res, timing = {}, {}
    for arm in arms:
        tree = build_tree(work, arm)
        H.set_tree(tree)
        res[arm], timing[arm] = {}, {}
        for A in anchors:
            i = int(np.searchsorted(fa, A))
            if i >= len(fa) or fa[i] != A:
                res[arm][A] = {"unavailable": "anchor not in the funding replay axis"}
                continue
            mi = int(np.searchsorted(mts, A))
            if mi >= len(mts) or mts[mi] != A:
                res[arm][A] = {"unavailable": "anchor not on the mask axis"}
                continue
            cand = mk["mask"][mi] & crypto
            ema = {syms[j]: {"acc": float(fr["ema_acc"][i, j])} for j in np.flatnonzero(np.isfinite(fr["ema_acc"][i]))}
            led = {syms[j]: [[int(fr["last_ft"][i, j]), float(fr["last_rate"][i, j]), float(fr["last_iv"][i, j])]]
                   for j in np.flatnonzero(fr["last_ft"][i] >= 0)}
            t1 = time.time()
            try:
                r = H.replay_anchor(A, D, ts, syms, chn, cand, ema, led, cfg["params"], cfg, f"{work}/mini", holes=holes, cols="members")
            except AssertionError as e:
                res[arm][A] = {"unavailable": f"assertion: {str(e)[:200]}"}
                print(f"{arm:6s} {A} UNAVAILABLE {str(e)[:120]}", flush=True)
                continue
            timing[arm][str(A)] = round(time.time() - t1, 2)
            if "skip" in r:
                res[arm][A] = {"unavailable": "producer would have skipped this anchor"}
                continue
            res[arm][A] = r
            print(f"{time.strftime('%H:%M:%S', time.gmtime())} {arm:6s} {A} members={len(r['m'])} {timing[arm][str(A)]}s", flush=True)

    names = None
    for A in anchors:
        if isinstance(res["base"].get(A), dict) and "f89_names" in res["base"][A]:
            names = res["base"][A]["f89_names"]
            break
    rows = []
    for arm in arms:
        if arm == "base":
            continue
        for A in anchors:
            b, x = res["base"].get(A), res[arm].get(A)
            if not isinstance(b, dict) or "X89" not in b or not isinstance(x, dict) or "X89" not in x:
                rows.append({"arm": arm, "anchor": A, "status": "UNAVAILABLE",
                             "why": (x or {}).get("unavailable") or (b or {}).get("unavailable")})
                continue
            same_members = bool(np.array_equal(b["m"], x["m"]))
            rec = {"arm": arm, "anchor": A, "status": "OK", "same_members": same_members,
                   "n_members": int(len(b["m"])), "member_symmetric_difference": int(len(set(b["m"].tolist()) ^ set(x["m"].tolist())))}
            if same_members:
                b89 = np.asarray(b["X89"], np.float64); x89 = np.asarray(x["X89"], np.float64)
                def nd(a, c):
                    return ~((a[:, c] == x89[:, c]) | (np.isnan(a[:, c]) & np.isnan(x89[:, c])))
                rec["X89_cells_changed"] = int(sum(int(nd(b89, c).sum()) for c in range(b89.shape[1])))
                rec["X82_cells_changed"] = int((~((np.asarray(b["X82"], np.float64) == np.asarray(x["X82"], np.float64)) |
                                                 (np.isnan(np.asarray(b["X82"], np.float64)) & np.isnan(np.asarray(x["X82"], np.float64))))).sum())
                rec["kingX78_cells_changed"] = int((~((np.asarray(b["king_X78"], np.float64) == np.asarray(x["king_X78"], np.float64)) |
                                                      (np.isnan(np.asarray(b["king_X78"], np.float64)) & np.isnan(np.asarray(x["king_X78"], np.float64))))).sum())
                if arm in ("D7", "all"):
                    rec["trend_ranked_cells_changed"] = {c: int(nd(b89, names.index(c)).sum()) for c in D7_COLS}
                    rec["trend_raw_finite_share"] = {c: [round(b["f89_finite_share_raw"][c], 5), round(x["f89_finite_share_raw"][c], 5)] for c in D7_COLS}
                if arm in ("D8", "all"):
                    rec["D8_finite_share_drop"] = {c: [round(b["f89_finite_share_raw"][c], 4), round(x["f89_finite_share_raw"][c], 4)]
                                                   for c in D8_COLS if c in b["f89_finite_share_raw"]}
                    rec["f89_finite_share_mean"] = [round(float(np.mean(list(b["f89_finite_share_raw"].values()))), 4),
                                                    round(float(np.mean(list(x["f89_finite_share_raw"].values()))), 4)]
            rows.append(rec)
            print(f"   {arm:5s} {A} same_members={rec['same_members']} X89changed={rec.get('X89_cells_changed')} "
                  f"X82changed={rec.get('X82_cells_changed')} king={rec.get('kingX78_cells_changed')}", flush=True)

    rec = {"device": "news2_year_probe.py", "self_sha256": H.sha(os.path.abspath(__file__)),
           "news2_hist_features_sha256": H.sha(os.path.join(HERE, "news2_hist_features.py")),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "python": sys.version.split()[0], "numpy": np.__version__,
           "config": {"arms": arms, "anchors": anchors, "cols": "members"},
           "inputs": {p: H.sha(p) for p in (CACHE_AXES, MASK, HOLES, FUND, CRYPTO, CFG)},
           "cache_source_sha256": H.sha(CACHE_DATA),
           "cache_data": {"path": CACHE_DATA, "shape": list(D.shape), "dtype": str(D.dtype)},
           "tree_shas": {arm: json.load(open(f"{work}/tree_{arm}/PATCH_RECEIPT.json"))["outputs"] for arm in arms},
           "seconds_per_anchor": timing, "rows": rows, "seconds": round(time.time() - t0, 1)}
    with open(out_path, "w") as f:
        json.dump(rec, f, indent=1)
    print(f"NEWS2_YEAR_PROBE rows={len(rows)} receipt_sha256={H.sha(out_path)}", flush=True)


if __name__ == "__main__":
    main()
