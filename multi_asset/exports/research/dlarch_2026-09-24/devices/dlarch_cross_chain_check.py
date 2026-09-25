#!/usr/bin/env python3
"""dlarch_cross_chain_check.py -- do two INDEPENDENT chains produce the same in-service cell, bitwise?

WHY (lead 2026-09-25): my `DLARCH_REF_NC_s42X` and fresh's `SER_EXT_NEWS2_s42X.npz` are the same
in-service NC book on the same X axis, produced by two separately built chains (different arm names,
different roots, different agents). Same config, same path seeds 0..31 => the per-path series should be
bitwise identical. If they are, the two chains mutually certify each other -- a much stronger statement
than either chain's own receipts. If they are not, the difference must be LOCATED (which path, which
anchor, how big) before either is used to judge T0.

WHAT IT COMPARES: every key the two files share, by shape, dtype and raw bytes. For a mismatch it
reports the first differing (path, anchor) with the anchor's UTC time, the two values, and the count and
max size of the differences -- a bare "differs" would be useless for diagnosis.

POSITIVE CONTROL (runs first, on the A side only, in memory): one float64 cell is perturbed by 1 ULP
and must be reported. Without it, "identical" could just mean the comparator never looked.

Read-only. usage: dlarch_cross_chain_check.py <env-whitelist> <A.npz> <B.npz> <out.json> [labelA labelB]
"""
import hashlib
import json
import os
import sys
import time

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cmp_key(k, x, y, anchors):
    """Empty dict == bitwise identical. Otherwise a located, sized description."""
    if x.shape != y.shape:
        return {"kind": "shape", "a": list(x.shape), "b": list(y.shape)}
    if x.dtype != y.dtype:
        return {"kind": "dtype", "a": str(x.dtype), "b": str(y.dtype)}
    if x.tobytes() == y.tobytes():
        return {}
    d = {"kind": "bytes", "a_sha": hashlib.sha256(x.tobytes()).hexdigest()[:16],
         "b_sha": hashlib.sha256(y.tobytes()).hexdigest()[:16]}
    fa, fb = np.asarray(x, np.float64), np.asarray(y, np.float64)
    both = np.isfinite(fa) & np.isfinite(fb)
    ne = (fa != fb) & both
    d["n_differing_finite_cells"] = int(ne.sum())
    d["n_finiteness_mismatch"] = int((np.isfinite(fa) != np.isfinite(fb)).sum())
    if ne.any():
        idx = np.argwhere(ne)
        first = idx[0]
        d["max_abs_delta"] = float(np.abs(fa[ne] - fb[ne]).max())
        if x.ndim == 2:
            pi, ai = int(first[0]), int(first[1])
            d["first_difference"] = {"path_seed": pi, "anchor_index": ai,
                                     "anchor_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(anchors[ai]))) if anchors is not None and ai < len(anchors) else None,
                                     "a": float(fa[pi, ai]), "b": float(fb[pi, ai])}
            d["distinct_path_seeds_affected"] = sorted(set(int(v) for v in idx[:, 0]))[:12]
        else:
            ai = int(first[0])
            d["first_difference"] = {"index": ai, "a": float(fa[ai]), "b": float(fb[ai])}
    return d


def main():
    wl = set(sys.argv[1].split(","))
    extra = sorted(set(os.environ) - wl)
    assert not extra, f"env outside whitelist: {extra}"
    pa, pb, out = sys.argv[2], sys.argv[3], sys.argv[4]
    la = sys.argv[5] if len(sys.argv) > 5 else "A"
    lb = sys.argv[6] if len(sys.argv) > 6 else "B"

    with np.load(pa, allow_pickle=False) as za:
        A = {k: za[k] for k in za.files}
    with np.load(pb, allow_pickle=False) as zb:
        B = {k: zb[k] for k in zb.files}
    shared = sorted(set(A) & set(B))
    anchors = A.get("anchors")
    print(f"{la}: {pa}\n    sha {sha(pa)[:16]}  keys {len(A)}")
    print(f"{lb}: {pb}\n    sha {sha(pb)[:16]}  keys {len(B)}")
    print(f"shared keys: {len(shared)}   only_in_{la}: {sorted(set(A)-set(B))}\n"
          f"                        only_in_{lb}: {sorted(set(B)-set(A))}")

    # ---- positive control, before any green ----
    ctl = "UNAVAILABLE"
    if "r_per_path" in shared and A["r_per_path"].size:
        p2 = A["r_per_path"].copy()
        fin = np.argwhere(np.isfinite(p2))
        if len(fin):
            i, j = int(fin[0][0]), int(fin[0][1])
            p2[i, j] = np.nextafter(p2[i, j], np.inf)          # one ULP: the smallest possible change
            c = cmp_key("control", A["r_per_path"], p2, anchors)
            ctl = (f"PASS (1 ULP at path {i} anchor {j} seen: "
                   f"n={c.get('n_differing_finite_cells')} max_delta={c.get('max_abs_delta'):.3e})"
                   if c else "FAIL -- comparator blind to a 1 ULP change")
    print(f"POSITIVE_CONTROL={ctl}")

    diffs = {}
    for k in shared:
        d = cmp_key(k, A[k], B[k], anchors)
        if d:
            diffs[k] = d
        print(f"  {k:32} {'IDENTICAL' if not d else 'DIFFERS'}")
        if d:
            print(f"      {json.dumps(d)[:300]}")

    rec = {"device": "dlarch_cross_chain_check.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "a": {"label": la, "path": pa, "sha256": sha(pa), "keys": sorted(A)},
           "b": {"label": lb, "path": pb, "sha256": sha(pb), "keys": sorted(B)},
           "shared_keys": shared, "positive_control": ctl,
           "differences": diffs, "ALL_SHARED_KEYS_BITWISE_IDENTICAL": not diffs,
           "meaning": ("identical => two independently built chains certify each other on this cell, "
                       "which neither chain's own receipts can establish alone; "
                       "different => locate before using either to judge T0")}
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dlarch_safe_io as sio
    rsha = sio.write_json(out, rec)
    print(f"receipt {out} sha {rsha}")
    ok = (not diffs) and ctl.startswith("PASS")
    print(f"DLARCH_CROSS_CHAIN identical={not diffs} control={ctl.split()[0]} shared_keys={len(shared)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
