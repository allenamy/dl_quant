"""Read-only predictor: at which anchors can D7's full-window mask change the served row?

D7's visible effect on the extracted anchor row comes from the mask the researcher's patch carries,
`tr[wsum(CSf, hi, lo_of(w)) != w] = np.nan`. The baseline (global-moment) trend already NaNs a member
with fewer than w//2 supported rows (`tr[(n < w // 2) | ...] = np.nan`). So the two arms can differ at
an anchor only through members whose support lies in **[w//2, w)** -- fully supported members are
unaffected, and members below w//2 are NaN in both. If that set is empty at an anchor, the two arms
are necessarily identical there, and running the admission gate on such an anchor measures nothing.

Hence: count, per anchor, the members whose rr support in [A-w+1, A] falls in [w//2, w). Anchors with
a non-zero count are the ones where the admission gate has resolution.

This reads only prepared arrays (members_hist_all.npz, R_crypto.npy, axes.npz) and writes one JSON.
No producer contact, no GPU, no exchange call.

The counting core is `difference_set_sizes`, deliberately separable so it can be driven by a
constructed input: `--selftest` runs a green baseline (every member fully supported -> zero anchors
with signal) and a red control (one member's support placed inside [w//2, w) -> that anchor must be
reported, naming the member). A predictor that cannot be made to fire is not a predictor.

usage:
  python news2_d7_signal_predictor.py --selftest <out.json>
  python news2_d7_signal_predictor.py <work_dir> <out.json> [--w 2016] [--colchunk 64]
"""
import argparse, hashlib, json, os, sys, time

import numpy as np

W_DEFAULT = 2016


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def difference_set_sizes(support, members, w):
    """support: (n_anchors, n_cols) int support counts in the w-row window ending at each anchor.
    members: list of per-anchor column-index arrays (into the same column axis).
    Returns (sizes, first_examples): per anchor, how many members have w//2 <= support < w."""
    lo = w // 2
    sizes = np.zeros(len(members), np.int64)
    examples = {}
    for i, m in enumerate(members):
        if m is None or len(m) == 0:
            continue
        s = support[i, m]
        hit = (s >= lo) & (s < w)
        n = int(hit.sum())
        sizes[i] = n
        if n:
            examples[i] = [int(m[k]) for k in np.flatnonzero(hit)[:5]]
    return sizes, examples


def selftest(out_path):
    """Green baseline then red control, in that order: a mutation check whose baseline is not green
    proves nothing."""
    w = 2016
    n_anchors, n_cols = 5, 10
    cells = []

    full = np.full((n_anchors, n_cols), w, np.int64)
    members = [np.arange(n_cols) for _ in range(n_anchors)]
    sizes, ex = difference_set_sizes(full, members, w)
    green = int(sizes.sum()) == 0
    cells.append({"cell": "GREEN.full_support", "verdict": "PASS" if green else "FAIL",
                  "expected": "0 anchors with signal", "observed": f"sum(sizes)={int(sizes.sum())}"})
    print(f"  GREEN.full_support     {'PASS' if green else 'FAIL'}  sizes={sizes.tolist()}", flush=True)
    if not green:
        json.dump({"VERDICT": "UNAVAILABLE(baseline not green)", "cells": cells}, open(out_path, "w"), indent=1)
        print("NEWS2_D7_PREDICTOR_SELFTEST VERDICT=UNAVAILABLE(baseline not green)", flush=True)
        sys.exit(1)

    # red control: put ONE member's support inside [w//2, w) at ONE anchor
    inj = full.copy()
    inj[3, 7] = 1500                       # 1008 <= 1500 < 2016
    sizes, ex = difference_set_sizes(inj, members, w)
    red = sizes.tolist() == [0, 0, 0, 1, 0] and ex.get(3) == [7]
    cells.append({"cell": "RED.one_member_in_band", "verdict": "PASS" if red else "FAIL",
                  "expected": "anchor 3 reports exactly member 7",
                  "observed": f"sizes={sizes.tolist()} examples={ {k: v for k, v in ex.items()} }"})
    print(f"  RED.one_member_in_band {'PASS' if red else 'FAIL'}  sizes={sizes.tolist()} examples={ex}", flush=True)

    # boundary control: support exactly w and exactly w//2 - 1 must NOT fire; exactly w//2 must
    inj2 = full.copy()
    inj2[1, 0] = w; inj2[1, 1] = w // 2 - 1; inj2[1, 2] = w // 2
    sizes2, ex2 = difference_set_sizes(inj2, members, w)
    bnd = sizes2.tolist() == [0, 1, 0, 0, 0] and ex2.get(1) == [2]
    cells.append({"cell": "RED.boundaries", "verdict": "PASS" if bnd else "FAIL",
                  "expected": "only support == w//2 fires (w and w//2-1 do not)",
                  "observed": f"sizes={sizes2.tolist()} examples={ {k: v for k, v in ex2.items()} }"})
    print(f"  RED.boundaries         {'PASS' if bnd else 'FAIL'}  sizes={sizes2.tolist()} examples={ex2}", flush=True)

    bad = [c for c in cells if c["verdict"] != "PASS"]
    rec = {"device": "news2_d7_signal_predictor.py --selftest",
           "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "w": w, "band": [w // 2, w], "cells": cells,
           "VERDICT": "PASS" if not bad else "FAIL"}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_D7_PREDICTOR_SELFTEST VERDICT={rec['VERDICT']} cells={len(cells)} "
          f"receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if not bad else 1)


def main():
    if "--selftest" in sys.argv:
        i = sys.argv.index("--selftest")
        return selftest(sys.argv[i + 1])
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("out")
    ap.add_argument("--w", type=int, default=W_DEFAULT)
    ap.add_argument("--colchunk", type=int, default=64)
    a = ap.parse_args()
    t0 = time.time()
    WK = a.work
    ax = np.load(f"{WK}/axes.npz", allow_pickle=True)
    ts = ax["ts"].astype(np.int64)
    cols = ax["crypto_cols"].astype(np.int64)          # 829-axis index of each R column
    anchors = ax["anchors"].astype(np.int64)
    R = np.load(f"{WK}/R_crypto.npy", mmap_mode="r")
    assert R.shape[0] == len(ts) and R.shape[1] == len(cols), (R.shape, len(ts), len(cols))
    mh = np.load(f"{WK}/members_hist_all.npz")
    mh_anchors = mh["anchors"].astype(np.int64)
    MH = {int(A): mh["idx"][mh["off"][i]:mh["off"][i + 1]].astype(np.int64) for i, A in enumerate(mh_anchors)}

    ia = np.searchsorted(ts, anchors)
    assert np.array_equal(ts[ia], anchors)
    hi = ia + 1
    lo = np.maximum(hi - a.w, 0)

    support = np.zeros((len(anchors), len(cols)), np.int32)
    for c0 in range(0, len(cols), a.colchunk):
        c1 = min(c0 + a.colchunk, len(cols))
        fin = np.isfinite(np.asarray(R[:, c0:c1]))
        cs = np.zeros((len(ts) + 1, c1 - c0), np.int32)
        np.cumsum(fin, axis=0, dtype=np.int32, out=cs[1:])
        support[:, c0:c1] = cs[hi] - cs[lo]
        del fin, cs
        if c0 % (a.colchunk * 4) == 0:
            print(f"support cols {c0}/{len(cols)} {round(time.time()-t0)}s", flush=True)

    # 829-axis member index -> R column index; a member outside the crypto columns cannot be scored
    col_of = np.full(int(cols.max()) + 1, -1, np.int64)
    col_of[cols] = np.arange(len(cols))
    members, off_axis = [], 0
    for A in anchors:
        m = MH.get(int(A))
        if m is None or len(m) == 0:
            members.append(np.empty(0, np.int64)); continue
        c = col_of[m]
        off_axis += int((c < 0).sum())
        members.append(c[c >= 0])
    sizes, examples = difference_set_sizes(support, members, a.w)

    sig = np.flatnonzero(sizes > 0)
    yrs = np.array([time.gmtime(int(x)).tm_year for x in anchors])
    by_year = {str(y): {"anchors": int((yrs == y).sum()), "with_signal": int(((yrs == y) & (sizes > 0)).sum())}
               for y in sorted(set(yrs.tolist()))}
    # a spread sample of signal anchors, for the admission gate
    pick = []
    for y in sorted(set(yrs[sig].tolist())) if len(sig) else []:
        cand = sig[yrs[sig] == y]
        pick += [int(anchors[k]) for k in cand[:: max(1, len(cand) // 2)][:2]]
    rec = {"device": "news2_d7_signal_predictor.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "derivation": ("two arms can differ only through members with w//2 <= support < w: fully "
                          "supported members are unaffected by the mask, and members below w//2 are "
                          "NaN in both arms. Empty difference set at an anchor => arms identical there."),
           "inputs": {f"{WK}/axes.npz": sha(f"{WK}/axes.npz"),
                      f"{WK}/members_hist_all.npz": sha(f"{WK}/members_hist_all.npz"),
                      f"{WK}/R_crypto.npy": {"shape": list(R.shape), "dtype": str(R.dtype)}},
           "w": a.w, "band": [a.w // 2, a.w], "n_anchors": int(len(anchors)),
           "members_outside_crypto_columns": int(off_axis),
           "n_anchors_with_signal": int(len(sig)),
           "by_year": by_year,
           "difference_set_size_max": int(sizes.max()) if len(sizes) else 0,
           "difference_set_size_mean_over_signal_anchors": float(sizes[sig].mean()) if len(sig) else 0.0,
           "suggested_gate_anchors": pick,
           "examples": {str(int(anchors[k])): examples[k] for k in list(examples)[:20]},
           "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(a.out, "w"), indent=1)
    print(f"NEWS2_D7_PREDICTOR anchors={len(anchors)} with_signal={len(sig)} max_set={rec['difference_set_size_max']} "
          f"suggested={pick} receipt_sha256={sha(a.out)}", flush=True)


if __name__ == "__main__":
    main()
