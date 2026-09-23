"""Is the tree the models were TRAINED on the same tree that will SHIP, as far as the served features
are concerned?

Why this exists (2026-09-23, found while preparing the FREEZE §3-1 re-runs): the feature package
NC_FEATURES.npz was built from the producer tree whose `shadow_loop_v3.py` is 9403dedd (nc PATCH_RECEIPT
18:17Z). The derivation then continued -- treeNC2/3 (a25a2981), treeNC4 (46c52d94), treeNC5 (a68c7a5f) --
and the deployment tree is the last of those. `shadow_loop_v3.py` is the ONLY file that differs; the
three patched feature files are byte-identical across all of them.

Reading the diff says the changes are all in the live ingestion path (parallel klines, the bulk
fundingRate endpoint, new-name backfill, 429/418 handling) and that the replay never executes any of
it, because the replay injects `st.cd` / `st.cts` / `st.ema` / `st.ledger` from the panel instead of
fetching. That reading is not evidence. A tree difference that reaches the served columns would mean
the models are trained on a different feature contract from the one that ships, which no later gate in
this release would catch -- every one of them runs on ONE tree at a time and would be internally
consistent on either.

So this measures it: same anchors, same inputs, one tree per process (H.set_tree mutates a module-level
singleton, so two trees in one process would contaminate each other), outputs compared bitwise.

NOT a claim that the trees are equivalent in production: the changed code is exactly the code the
replay does not run, so this says only that THE SERVED FEATURES do not move. The live ingestion changes
must be judged by the integrator's own parity gate, on the live path.

usage:
  python news2_tree_parity.py <treeA> <treeB> <nc_devices> <cfg> <work> <members_hist|-> <out.json> <anchor>...
  python news2_tree_parity.py --dump <tree> <nc_devices> <cfg> <work> <members_hist|-> <out.npz> <anchor>...  (internal)
"""
import hashlib, json, os, subprocess, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Compared bitwise at every anchor. King X78 and the two mini matrices are the served columns; members
# and qvm are included because a tree change that moved the member screen would show up there first.
KEYS = ["king_X78", "X82", "X89", "m", "qvm", "fe_v", "fn_v", "iv_v", "btcv_anchor"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


# ★ env whitelist assertion, at the TOP of both entry points. nc_hist_features.pass2_anchor reads
# os.environ["NC_WS"] with no default, ~3 minutes into a run, and the KeyError arrives after the
# windows are already loaded. Asserting up front turns a 3-minute mystery into a one-line refusal that
# names the variable (E-0826-D: the environment is part of the rerun command).
REQUIRED_ENV = ("NC_WS",)


def require_env():
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        print(f"NEWS2_TREE_PARITY VERDICT=REFUSED missing_env={missing} "
              f"(nc_hist_features.pass2_anchor reads them with no default)", flush=True)
        sys.exit(4)
    return {k: os.environ[k] for k in REQUIRED_ENV}


def dump(tree, nc_devices, cfg, work, mh, out_npz, anchors):
    require_env()
    from news2_nc_adapter import Replay
    R = Replay(nc_devices, tree, cfg, work, mh)
    store = {}
    for A in anchors:
        r = R.at(A)
        if r.get("unavailable"):
            # Recorded, not silently dropped: an anchor that yields nothing on BOTH trees would
            # otherwise be counted as agreement.
            store[f"{A}/unavailable"] = np.array(str(r["unavailable"]))
        for k in KEYS:
            v = r.get(k)
            if v is not None:
                store[f"{A}/{k}"] = np.asarray(v)
    np.savez(out_npz, **store)
    print(f"DUMP_DONE tree={tree} anchors={len(anchors)} arrays={len(store)}", flush=True)


def main():
    if sys.argv[1] == "--dump":
        tree, nc_devices, cfg, work, mh, out_npz = sys.argv[2:8]
        dump(tree, nc_devices, cfg, work, (None if mh == "-" else mh), out_npz, [int(x) for x in sys.argv[8:]])
        return

    treeA, treeB, nc_devices, cfg, work, mh, out_path = sys.argv[1:8]
    anchors = [int(x) for x in sys.argv[8:]]
    print(f"NEWS2_TREE_PARITY env={require_env()}", flush=True)
    t0 = time.time()
    os.makedirs(work, exist_ok=True)
    dumps = {}
    for tag, tree in (("A", treeA), ("B", treeB)):
        npz = os.path.join(work, f"parity_{tag}.npz")
        cmd = [sys.executable, os.path.abspath(__file__), "--dump", tree, nc_devices, cfg,
               os.path.join(work, f"w{tag}"), mh, npz] + [str(a) for a in anchors]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"NEWS2_TREE_PARITY VERDICT=ERROR tree{tag} rc={r.returncode}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
            json.dump({"VERDICT": "ERROR", "tree": tree, "rc": r.returncode, "stderr": r.stderr[-4000:]},
                      open(out_path, "w"), indent=1)
            sys.exit(2)
        dumps[tag] = np.load(npz, allow_pickle=True)

    A, B = dumps["A"], dumps["B"]
    per_key, n_diff, n_cmp = [], 0, 0
    keysA, keysB = set(A.files), set(B.files)
    for k in sorted(keysA | keysB):
        if k not in keysA or k not in keysB:
            per_key.append({"key": k, "STATUS": "PRESENT_IN_ONE_TREE_ONLY",
                            "in_A": k in keysA, "in_B": k in keysB})
            n_diff += 1
            continue
        a, b = A[k], B[k]
        if a.shape != b.shape:
            per_key.append({"key": k, "STATUS": "SHAPE", "A": list(a.shape), "B": list(b.shape)})
            n_diff += 1
            continue
        if a.dtype.kind in "fc":
            d = int(np.sum(~((a == b) | (np.isnan(a) & np.isnan(b)))))    # NaN==NaN counts as equal
        else:
            d = int(np.sum(a != b))
        n_cmp += a.size
        per_key.append({"key": k, "cells": int(a.size), "cells_different": d})
        n_diff += d

    # ★ Non-vacuity: a comparison of two empty dumps is 0 != 0 and would read as PASS. The number of
    # cells actually compared is the load-bearing number, so it is a gate, not a footnote.
    enough = n_cmp > 0 and len([p for p in per_key if p.get("cells")]) >= len(anchors)
    rec = {"device": "news2_tree_parity.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "argv": list(sys.argv), "rerun_command": " ".join([sys.executable, os.path.abspath(__file__)] + sys.argv[1:]),
           # The replay core reads NC_W and NC_WS (the latter has NO default and the run dies without
           # it). My earlier gate receipts recorded an empty env dict, which is the E-0826-D gap:
           # the environment is part of the rerun command. Enumerated, not summarised.
           "env": {k: os.environ.get(k) for k in
                   ("NC_W", "NC_WS", "NC_TREE", "NC_CFG", "NC_NEWS2_FAMILIES", "NC_TREND_ROWS",
                    "F8_TREND_ROWS", "CAL", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "TZ")},
           "treeA": treeA, "treeB": treeB,
           "treeA_shadow_loop_sha256": sha(os.path.join(treeA, "shadow_loop_v3.py")),
           "treeB_shadow_loop_sha256": sha(os.path.join(treeB, "shadow_loop_v3.py")),
           "anchors": anchors, "n_anchors": len(anchors),
           "cells_compared": n_cmp, "cells_different": n_diff, "per_key": per_key,
           "scope": ("served feature columns under REPLAY only. The trees differ in the live ingestion "
                     "path, which the replay does not execute; this run does not and cannot judge that path."),
           "seconds": round(time.time() - t0, 1)}
    rec["VERDICT"] = ("PASS" if (n_diff == 0 and enough) else
                      "NO-MEASUREMENT: nothing was compared" if not enough else "FAIL")
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_TREE_PARITY VERDICT={rec['VERDICT']} anchors={len(anchors)} "
          f"cells_compared={n_cmp} cells_different={n_diff} receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if rec["VERDICT"] == "PASS" else 1)


if __name__ == "__main__":
    main()
