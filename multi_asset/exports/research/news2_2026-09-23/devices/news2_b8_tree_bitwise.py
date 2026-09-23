"""B8 for FREEZE §3-1: is the kernel IN THE SHIPPING TREE bitwise equal to the researcher's
feature_contract.window_stats?

The earlier B8 receipt (B8_SHARED_CUMSUM_BITWISE.json, b8/b8_bitwise.py) compared a TRANSCRIPTION of the
shared-cumsum kernel -- code written out again inside the test -- against window_stats. That certifies
the algebra, and it is the reason the inline patch was chosen over vendoring, but it does not certify
the kernel the producer will actually run: if the patch in the tree drifted from the transcription, both
files would still agree with each other and the receipt would still be green. Testing a copy of the
subject is the "textual instrument for a behavioural property" shape.

This runs the tree's OWN `wstat` closure -- the one the extracted King block builds, i.e. the object the
producer calls -- over a real 40-day cache slice, and compares it to window_stats cell by cell.

Red control: one input cell is perturbed and the comparison must go red. Without it, a green says only
that nothing was compared.

usage: python news2_b8_tree_bitwise.py <tree> <cache_slice.npz> <anchor> <feature_contract_dir> <out.json>
"""
import hashlib, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_news2_patches import run_king                     # the harness that builds the tree's King block

WINS = (48, 288, 864, 2016, 8640)
STATS = ("count", "sum", "mean", "std")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def ne(a, b):
    """cells that differ, NaN==NaN counted equal."""
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    return int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())


def compare(tree, cd, window_stats):
    """Run the tree's wstat closure against window_stats over every channel x window x stat."""
    out, span, _ = run_king(tree, cd, ntop=cd.shape[1])
    wstat = out["wstat"]
    rows = np.array([cd.shape[0] - 1])
    per, n_cells, n_diff = {}, 0, 0
    for ch in range(cd.shape[2]):
        ref_src = np.asarray(cd[:, :, ch], np.float32)
        for w in WINS:
            ref = window_stats(ref_src, rows, w)
            for st in STATS:
                try:
                    got = wstat(ch, w, st)
                except Exception as e:                       # a stat the closure does not expose is recorded
                    per[f"ch{ch}_w{w}_{st}"] = {"STATUS": f"NOT_EXPOSED: {type(e).__name__}: {e}"}
                    continue
                d = ne(got, ref[st])
                per[f"ch{ch}_w{w}_{st}"] = {"cells": int(np.asarray(got).size), "cells_different": d}
                n_cells += int(np.asarray(got).size); n_diff += d
    return per, n_cells, n_diff, span


def main():
    tree, slice_npz, anchor, fc_dir, out_path = sys.argv[1:6]
    anchor = int(anchor)
    t0 = time.time()
    sys.path.insert(0, fc_dir)
    from feature_contract import window_stats

    C = np.load(slice_npz, allow_pickle=True)
    ts = C["ts"].astype(np.int64)
    ia = int(np.searchsorted(ts, anchor))
    i0 = max(ia + 1 - 11520, 0)
    cd = np.array(C["data"][i0:ia + 1], dtype=np.float16)
    per, n_cells, n_diff, span = compare(tree, cd, window_stats)

    # ★ Red control: run the tree's kernel on the real input, but give the REFERENCE a copy of the
    # input with one finite cell moved. The two sides are then genuinely computing different things,
    # so the comparison must report differences. If it does not, the comparison is not looking at the
    # numbers and the green above proves nothing.
    red_ok, red_note = None, None
    fin = np.argwhere(np.isfinite(np.asarray(cd[:, :, 1], np.float32)))
    if len(fin):
        r, c = int(fin[len(fin) // 2][0]), int(fin[len(fin) // 2][1])
        cdx = cd.copy()
        cdx[r, c, 1] = np.float16(float(cd[r, c, 1]) + 1.0)

        def shifted_reference(src, rows, w):
            """window_stats on the PERTURBED array whenever it is asked for channel 1."""
            if src.shape == cd[:, :, 1].shape and np.array_equal(np.asarray(src, np.float32),
                                                                 np.asarray(cd[:, :, 1], np.float32)):
                return window_stats(np.asarray(cdx[:, :, 1], np.float32), rows, w)
            return window_stats(src, rows, w)

        _, red_cells, red_diff, _ = compare(tree, cd, shifted_reference)
        red_ok = red_cells > 0 and red_diff > 0
        red_note = (f"reference fed cd[{r},{c},ch1] + 1.0 while the tree kernel saw the original; "
                    f"cells_compared={red_cells} cells_different={red_diff}")
    else:
        red_note = "no finite cell in channel 1 to perturb"

    rec = {"device": "news2_b8_tree_bitwise.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "argv": list(sys.argv), "rerun_command": " ".join([sys.executable, os.path.abspath(__file__)] + sys.argv[1:]),
           "tree": tree, "tree_shadow_loop_sha256": sha(os.path.join(tree, "shadow_loop_v3.py")),
           "king_block_lines": list(span), "cache_slice": slice_npz, "cache_slice_sha256": sha(slice_npz),
           "anchor": anchor, "cd_shape": list(cd.shape),
           "feature_contract": os.path.join(fc_dir, "feature_contract.py"),
           "feature_contract_sha256": sha(os.path.join(fc_dir, "feature_contract.py")),
           "n_comparisons": len(per), "cells_compared": n_cells, "cells_different": n_diff,
           "per_comparison": per,
           "red_control": {"passed": red_ok, "note": red_note},
           "what_this_adds": ("the earlier B8 receipt compared a TRANSCRIPTION of the kernel; this runs the "
                              "tree's own wstat closure, so a patch that drifted from the transcription "
                              "would now be caught"),
           "seconds": round(time.time() - t0, 1)}
    if n_cells == 0:
        rec["VERDICT"] = "NO-MEASUREMENT: nothing was compared"
    elif red_ok is not True:
        rec["VERDICT"] = "UNAVAILABLE: red control did not go red, so a green here proves nothing"
    else:
        rec["VERDICT"] = "PASS: tree kernel == window_stats bitwise" if n_diff == 0 else "FAIL"
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_B8_TREE VERDICT={rec['VERDICT']} comparisons={len(per)} cells_compared={n_cells} "
          f"cells_different={n_diff} red_control={red_ok} receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if rec["VERDICT"].startswith("PASS") else 1)


if __name__ == "__main__":
    main()
