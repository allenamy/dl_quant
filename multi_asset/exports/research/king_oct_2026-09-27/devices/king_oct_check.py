"""king_oct_check.py -- device controls of king_oct_train.py (fresh2 2026-09-27). Criteria frozen here, before any run exists:
  same   A B            : KING_OOF arrays E_ts, symbols, P bitwise equal (model_sha256 is provenance, reported, not gated: model
                          text differs by ulps between runs while scores do not -- rule revision 1, 1da5ea3d5)
  served RUN FEAT FSHA  : the fold "2026" model file (the served booster) has the sha its receipt names, and reloaded from that
                          text it reproduces the OOF P of every fold-2026 cell bitwise (float32) -- the served file IS the judged model
  differ A B            : P differs in > 0 cells finite in both (a feature swap that changes nothing did not happen); reports counts
Prints one line-anchored "KOC_CHECK <mode> PASS=True|False {json}" and writes the same record to OUT through durable_write.
usage: python king_oct_check.py <mode> <args...> <out.json>
"""
import os, sys, json, hashlib
import numpy as np

for _c in (os.path.dirname(os.path.realpath(__file__)),
           os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "common"),
           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "common")):
    if os.path.exists(os.path.join(_c, "durable_write.py")):
        sys.path.insert(0, _c)
        break
else:
    raise ImportError("common/durable_write.py not found next to or above this device; deploy it with the device")
import durable_write as DW


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def arr_sha(x): return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()


def same(a, b):
    A, B = np.load(a), np.load(b)
    diff = [k for k in ("E_ts", "symbols", "P") if not (A[k].shape == B[k].shape and A[k].dtype == B[k].dtype and A[k].tobytes() == B[k].tobytes())]
    return not diff, {"a": a, "a_sha256": sha(a), "b": b, "b_sha256": sha(b), "P_sha256": [arr_sha(A["P"]), arr_sha(B["P"])],
                      "differing_arrays": diff, "model_sha256_equal_reported_not_gated": bool(np.array_equal(A["model_sha256"], B["model_sha256"]))}


def served(run, feat, fsha):
    import lightgbm as lgb
    rec = json.load(open(os.path.join(run, "TRAIN_RECEIPT.json")))
    f26 = [f for f in rec["folds"] if f["fold"] == "2026"]; assert len(f26) == 1, "exactly one fold 2026"
    f26 = f26[0]; mp = f26["model_path"]
    file_ok = os.path.exists(mp) and sha(mp) == f26["model_sha256"]
    assert sha(feat) == fsha, "features identity"
    F = np.load(feat); O = np.load(os.path.join(run, "KING_OOF.npz"))
    a = F["anchors"].astype(np.int64); cnt = F["count"]; pa = np.repeat(np.arange(len(a)), cnt).astype(np.int64); ps = F["m"].astype(np.int64)
    assert np.array_equal(O["E_ts"].astype(np.int64), a)
    rows = (a[pa] >= f26["score_start"]) & (a[pa] <= f26["score_end"])
    got = lgb.Booster(model_file=mp).predict(F["X78"][rows].astype(np.float32)).astype(np.float32)
    want = O["P"][pa[rows], ps[rows]]
    n_diff = int(np.sum(got.view(np.uint32) != want.view(np.uint32)))   # bit patterns: no float tolerance, NaN == NaN only if same bits
    return file_ok and n_diff == 0 and rows.sum() == f26["scored_pairs"], {
        "run": run, "model_path": mp, "model_file_sha_matches_receipt": file_ok, "rows": int(rows.sum()), "receipt_scored_pairs": f26["scored_pairs"],
        "cells_differing_bitwise": n_diff, "features": feat, "features_sha256": fsha}


def differ(a, b):
    A, B = np.load(a)["P"], np.load(b)["P"]
    assert A.shape == B.shape
    both = np.isfinite(A) & np.isfinite(B)
    nd = int(np.sum(both & (A != B)))
    return nd > 0, {"a": a, "b": b, "cells_finite_in_both": int(both.sum()), "cells_differing": nd,
                    "nan_pattern_differs": int(np.sum(np.isfinite(A) != np.isfinite(B)))}


def main():
    mode, args, out = sys.argv[1], sys.argv[2:-1], sys.argv[-1]
    ok, rec = {"same": same, "served": served, "differ": differ}[mode](*args)
    rec = {"device": "king_oct_check.py", "self_sha256": sha(os.path.realpath(__file__)), "mode": mode, "PASS": bool(ok), **rec}
    s = DW.write_json(out, rec, indent=1)
    print("KOC_CHECK %s PASS=%s %s" % (mode, bool(ok), json.dumps({**rec, "out_sha256": s})[:600]), flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
