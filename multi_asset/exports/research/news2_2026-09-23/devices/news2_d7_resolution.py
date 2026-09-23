"""Resolution figures for the D7 `last` admission (lead's ruling 2026-09-23, superseding the
signal-anchor requirement).

What the admission gate proves: the row `last` extracts equals the row `all` extracts, i.e. the
optimisation takes the RIGHT row. Its resolving power therefore depends on whether the trend columns
carry a non-trivial value AT THE SERVED ROW -- if they do, taking the wrong row would show up. It does
NOT depend on whether D7 changes that row relative to the floor arm; that is a different question
(whether the fix does anything), answered separately.

So per anchor this reports, for `C:trend_288` and `C:trend_2016` at the served row:
  * n_finite_nonzero -- cells carrying a rank (X89 is anchor-ranked, so NaN arrives as 0.0; a column
    that is entirely NaN upstream is entirely 0 here and would resolve nothing)
  * xsec_std         -- cross-sectional standard deviation over the members
Both > 0 => that anchor can tell a wrong row from a right one.

Only the `last` arm is run: the gate receipts already record all_vs_last == 0 bitwise on these
anchors, so the two arms' served rows are the same array and measuring either is measuring both.
One arm x N anchors, not the three-arm gate again.

usage: python news2_d7_resolution.py <arms_root> <nc_devices> <cfg> <members_hist.npz> <work> <out.json> <prior_receipt.json> [...] -- <anchor> [...]
"""
import hashlib, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from news2_nc_adapter import Replay

TREND_COLS = ["C:trend_288", "C:trend_2016"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def main():
    argv = sys.argv[1:]
    sep = argv.index("--")
    arms_root, nc_dev, cfg, mh_path, work, out_path = argv[:6]
    priors = argv[6:sep]
    anchors = sorted(set(int(x) for x in argv[sep + 1:]))
    t0 = time.time()

    # carry the already-measured bitwise equality forward rather than recomputing it
    prior_rows = {}
    prior_meta = []
    for p in priors:
        P = json.load(open(p))
        prior_meta.append({"path": p, "sha256": sha(p), "VERDICT": P.get("VERDICT")})
        for r in P.get("rows", []):
            if r.get("status") == "OK":
                prior_rows[int(r["anchor"])] = {k: r[k] for k in
                                                ("all_vs_last_X89", "all_vs_last_X82", "all_vs_last_kingX78",
                                                 "same_members_all_vs_last") if k in r}

    R = Replay(nc_dev, os.path.join(arms_root, "tree_floorD7"), cfg, work, mh_path)
    rows = []
    for A in anchors:
        t1 = time.time()
        r = R.at(A)
        if r.get("X89") is None:
            rows.append({"anchor": A, "status": "UNAVAILABLE", "why": r.get("unavailable")})
            print(json.dumps(rows[-1]), flush=True); continue
        # nc_hist_features.pass2_anchor does not return the F89 column names, but it returns
        # f89_finite_share_raw, whose keys ARE all_rank_names in order (f8 builds it with
        # enumerate(all_rank_names)), and X89 = concat([XR(ranked, same order), Hs(2), Hp(8), I(10)]).
        # So a ranked column's position in that dict is its column index in X89. Asserted, not assumed:
        # if the layout ever changes, the arithmetic below stops adding up and this fails loudly.
        fsr = r.get("f89_finite_share_raw")
        assert isinstance(fsr, dict) and fsr, "pass2 did not return f89_finite_share_raw"
        names = list(fsr)
        X = np.asarray(r["X89"], np.float64)
        assert len(names) + 2 + 8 + 10 == X.shape[1], (
            f"F89 layout changed: {len(names)} ranked + 20 blocks != {X.shape[1]} columns")
        for c in TREND_COLS:
            assert c in names, f"{c} not among the ranked columns"
        rec = {"anchor": A, "status": "OK", "n_members": int(len(r["m"])),
               "seconds": round(time.time() - t1, 2), "trend": {}}
        for c in TREND_COLS:
            v = X[:, names.index(c)]
            nz = int((np.isfinite(v) & (v != 0.0)).sum())
            rec["trend"][c] = {"n_finite_nonzero": nz, "xsec_std": float(np.std(v)),
                               "has_resolution": bool(nz > 0 and float(np.std(v)) > 0.0)}
        rec["anchor_has_resolution"] = all(rec["trend"][c]["has_resolution"] for c in TREND_COLS)
        rec["prior_bitwise"] = prior_rows.get(A)
        rows.append(rec)
        print(f"{A} members={rec['n_members']} " +
              " ".join(f"{c}: nz={rec['trend'][c]['n_finite_nonzero']} sd={rec['trend'][c]['xsec_std']:.4f}"
                       for c in TREND_COLS) +
              f" resolution={rec['anchor_has_resolution']} prior={rec['prior_bitwise']}", flush=True)

    ok = [r for r in rows if r.get("status") == "OK"]
    with_res = [r for r in ok if r["anchor_has_resolution"]]
    # an anchor only counts toward admission if it BOTH resolves and was measured bitwise equal
    admissible = [r for r in with_res if r.get("prior_bitwise")
                  and r["prior_bitwise"].get("all_vs_last_X89") == 0
                  and r["prior_bitwise"].get("all_vs_last_X82") == 0
                  and r["prior_bitwise"].get("all_vs_last_kingX78") == 0
                  and r["prior_bitwise"].get("same_members_all_vs_last")]
    verdict = ("PASS" if len(admissible) >= 6 else
               f"INSUFFICIENT({len(admissible)} anchors both resolve and were measured equal; need >= 6)")
    rec = {"device": "news2_d7_resolution.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "ruling": ("lead 2026-09-23: admission = row-independence AND, on >= 6 cross-year anchors, "
                      "all-vs-last bitwise equal at the served row WITH the trend columns non-trivial "
                      "there. The earlier 'find anchors where D7 moves the row' requirement was aimed "
                      "at the wrong object and is withdrawn."),
           "arm_run": "floorD7 (declares F8_TREND_ROWS=last); the all arm is not re-run because the "
                      "prior receipts record all_vs_last == 0 bitwise on these anchors",
           "prior_receipts": prior_meta, "members_hist": {"path": mh_path, "sha256": sha(mh_path)},
           "anchors": anchors, "rows": rows,
           "n_ok": len(ok), "n_with_resolution": len(with_res), "n_admissible": len(admissible),
           "VERDICT": verdict, "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_D7_RESOLUTION VERDICT={verdict} ok={len(ok)} with_resolution={len(with_res)} "
          f"admissible={len(admissible)} receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
