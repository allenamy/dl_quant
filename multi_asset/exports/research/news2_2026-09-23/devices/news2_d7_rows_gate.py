"""NEW_S2 admission gate for DESIGN §E4(a): is F8_TREND_ROWS="last" allowed?

"last" computes the stable trend only for the anchor row the producer's mini pipeline extracts. It is
admissible ONLY if the extracted row is BITWISE equal to the row produced with "all" (the researcher's
text). This device measures that on the declared anchors and reports the wall clock of both settings.

Three ways this gate can pass vacuously, all of them reported instead:
  * an anchor where the two settings were never both run          -> UNAVAILABLE, not PASS
  * a run where the "all" setting changed nothing vs base         -> the anchor carries no signal for
    the comparison and is counted separately (n_anchors_where_D7_moves_the_row)
  * zero anchors in the sample where D7 moves the row at all      -> verdict PASS(NO-SIGNAL), naming it

The two anchors where the 24-anchor probe found D7 DOES move the served row are mandatory members of
the sample; the gate refuses to run without them.

usage: python news2_d7_rows_gate.py <work_dir> <out.json> [anchors]
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import news2_hist_features as H
from news2_global_gate import build_tree

CACHE_AXES = os.environ["NEWS2_CACHE_AXES"]
CACHE_DATA = os.environ["NEWS2_CACHE_DATA"]
MASK = os.environ["NEWS2_MASK"]
HOLES = os.environ["NEWS2_HOLES"]
FUND = os.environ["NEWS2_FUND"]
CRYPTO = os.environ["NEWS2_CRYPTO"]
CFG = os.environ["NEWS2_CFG"]

# the two anchors the 24-anchor probe (YEAR_PROBE.json afac8c2f...) found D7 to move; without them the
# gate would be comparing two settings on rows neither of them changes.
MUST_INCLUDE = [1685520000, 1742428800]
DEFAULT_ANCHORS = MUST_INCLUDE + [1657065600, 1688097600, 1717200000, 1756684800, 1780272000, 1787961600]


def main():
    work = os.path.abspath(sys.argv[1])
    out_path = os.path.abspath(sys.argv[2])
    anchors = sorted(set([int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 and sys.argv[3] else DEFAULT_ANCHORS))
    missing = [a for a in MUST_INCLUDE if a not in anchors]
    assert not missing, f"refusing to run: the anchors where D7 moves the served row must be in the sample, missing {missing}"
    os.makedirs(f"{work}/mini", exist_ok=True)
    t0 = time.time()

    ax = np.load(CACHE_AXES, allow_pickle=True)
    ts = ax["ts"].astype(np.int64)
    syms = [str(s) for s in ax["symbols"]]
    chn = [str(c) for c in ax["ch"]]
    if CACHE_DATA.endswith(".npz"):
        with np.load(CACHE_DATA) as z:
            D = z["data"]
    else:
        D = np.load(CACHE_DATA, mmap_mode="r")
    with np.load(HOLES) as z: hz = {"row": z["row"], "col": z["col"]}
    o = np.lexsort((hz["col"], hz["row"]))
    holes = (hz["row"][o].astype(np.int64), hz["col"][o].astype(np.int64))
    with np.load(MASK) as z: mk = {"ts": z["ts"].astype(np.int64), "mask": z["mask"]}
    mts = mk["ts"]
    with np.load(FUND) as z: fr = {k: z[k] for k in ("anchors", "ema_acc", "last_ft", "last_rate", "last_iv")}
    fa = fr["anchors"].astype(np.int64)
    with np.load(CRYPTO) as z: crypto = z["crypto"]
    cfg = json.load(open(CFG))

    def run(arm, rows_mode, A):
        # The two settings differ in the SHIPPED TEXT of combo_stage.py (tree "D7" declares "last",
        # tree "D7all" declares "all"), not in this process's environment: news2_hist_features reads
        # the declaration out of the tree, so an environment variable here would change nothing and
        # the gate would compare a setting against itself.
        H.set_tree(build_tree(work, arm))
        if rows_mode is not None:
            assert H._trend_rows() == rows_mode, (arm, "declares", H._trend_rows(), "expected", rows_mode)
        i = int(np.searchsorted(fa, A))
        mi = int(np.searchsorted(mts, A))
        if i >= len(fa) or fa[i] != A or mi >= len(mts) or mts[mi] != A:
            return None, None
        cand = mk["mask"][mi] & crypto
        ema = {syms[j]: {"acc": float(fr["ema_acc"][i, j])} for j in np.flatnonzero(np.isfinite(fr["ema_acc"][i]))}
        led = {syms[j]: [[int(fr["last_ft"][i, j]), float(fr["last_rate"][i, j]), float(fr["last_iv"][i, j])]]
               for j in np.flatnonzero(fr["last_ft"][i] >= 0)}
        t1 = time.time()
        r = H.replay_anchor(A, D, ts, syms, chn, cand, ema, led, cfg["params"], cfg, f"{work}/mini", holes=holes, cols="members")
        return r, round(time.time() - t1, 2)

    rows, timing = [], {}
    for A in anchors:
        rec = {"anchor": A}
        out = {}
        for tag, arm, mode in (("base", "base", None), ("all", "D7all", "all"), ("last", "D7", "last")):
            r, dt = run(arm, mode, A)
            if r is None or "skip" in r:
                rec["status"] = "UNAVAILABLE"
                rec["why"] = "anchor not on an axis, or the producer would have skipped it"
                break
            out[tag] = r
            timing.setdefault(tag, {})[str(A)] = dt
            print(f"{time.strftime('%H:%M:%S', time.gmtime())} {tag:5s} {A} members={len(r['m'])} {dt}s", flush=True)
        else:
            def diff(a, b):
                a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
                return int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())
            rec["status"] = "OK"
            rec["n_members"] = int(len(out["base"]["m"]))
            rec["D7_moves_the_row"] = diff(out["base"]["X89"], out["all"]["X89"])
            rec["all_vs_last_X89"] = diff(out["all"]["X89"], out["last"]["X89"])
            rec["all_vs_last_X82"] = diff(out["all"]["X82"], out["last"]["X82"])
            rec["all_vs_last_kingX78"] = diff(out["all"]["king_X78"], out["last"]["king_X78"])
            rec["same_members"] = bool(np.array_equal(out["all"]["m"], out["last"]["m"]))
            print(f"   {A} D7_moves_row={rec['D7_moves_the_row']} all_vs_last X89={rec['all_vs_last_X89']} "
                  f"X82={rec['all_vs_last_X82']} king={rec['all_vs_last_kingX78']}", flush=True)
        rows.append(rec)

    ok = [r for r in rows if r.get("status") == "OK"]
    unavail = [r for r in rows if r.get("status") != "OK"]
    bad = [r for r in ok if r["all_vs_last_X89"] or r["all_vs_last_X82"] or r["all_vs_last_kingX78"] or not r["same_members"]]
    with_signal = [r for r in ok if r["D7_moves_the_row"] > 0]
    if not ok:
        verdict = "UNAVAILABLE(no anchor ran)"
    elif bad:
        verdict = "FAIL"
    elif not with_signal:
        verdict = "PASS(NO-SIGNAL: no anchor in this sample is one where D7 moves the served row)"
    else:
        verdict = "PASS"
    med = lambda d: round(float(np.median(list(d.values()))), 2) if d else None
    rec = {"device": "news2_d7_rows_gate.py", "self_sha256": H.sha(os.path.abspath(__file__)),
           "news2_hist_features_sha256": H.sha(os.path.join(HERE, "news2_hist_features.py")),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "python": sys.version.split()[0], "numpy": np.__version__,
           "design_ref": "DESIGN_producer_new_contract_2026-09-23.md E4(a)",
           "must_include_anchors": MUST_INCLUDE, "anchors": anchors,
           "inputs": {p: H.sha(p) for p in (CACHE_AXES, MASK, HOLES, FUND, CRYPTO, CFG)},
           "tree_shas": {arm: json.load(open(f"{work}/tree_{arm}/PATCH_RECEIPT.json"))["outputs"] for arm in ("base", "D7", "D7all")},
           "tree_declared_trend_rows": {arm: json.load(open(f"{work}/tree_{arm}/PATCH_RECEIPT.json"))["config"]["trend_rows_declared"] for arm in ("D7", "D7all")},
           "rows": rows, "n_ok": len(ok), "n_unavailable": len(unavail),
           "n_anchors_where_D7_moves_the_row": len(with_signal),
           "median_seconds": {k: med(v) for k, v in timing.items()}, "seconds_per_anchor": timing,
           "VERDICT": verdict, "seconds": round(time.time() - t0, 1)}
    with open(out_path, "w") as f:
        json.dump(rec, f, indent=1)
    print(f"NEWS2_D7_ROWS_GATE VERDICT={verdict} ok={len(ok)} with_signal={len(with_signal)} "
          f"median_all={rec['median_seconds'].get('all')}s median_last={rec['median_seconds'].get('last')}s "
          f"receipt_sha256={H.sha(out_path)}", flush=True)
    sys.exit(0 if verdict.startswith("PASS") else 1)


if __name__ == "__main__":
    main()
