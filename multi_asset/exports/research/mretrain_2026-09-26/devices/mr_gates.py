"""mr_gates.py — device gates of DECISION_RULE_king_monthly_retrain_2026-09-26.md §0 (1f2f5c4e9), items 1-3 (item 4, the red
control, is a book-layer reading and is judged by the reading device). Any FAIL => the whole family stops.
  G1 determinism : A0 rs=0 trained twice (arms/A0_m0 and gate/A0_m0_dup) -> KING_OOF arrays bitwise equal
  G2 A0 == in-service King: arrays bitwise equal to news2 work/king/KING_OOF.npz, whose file sha must be a10b8725...
  G3 A0 through the chain: legs arrays == news2 legs (9ee5886f...); combo literal/scaled arrays == news2 combo_s{42,2027};
     adapter targets arrays == the in-service X config's pinned targets.
Container (file) shas are reported too; the gate is on the ARRAYS (the zip container of np.savez may carry a timestamp).
Revision 1 (rule §7, lead da04c28f9, written after the run-2 gate reading): for King OOF files (G1, G2 and the A1/A3 duplicate
check) the gate is on every array EXCEPT the provenance text PROVENANCE (model_sha256: per-anchor sha of the model text file,
which differed by last-ulp leaf_value digits while P / E_ts / symbols were bitwise equal); provenance equality is reported, not gated.
usage: python mr_gates.py <out.json>                       -- device gates G1-G3
       python mr_gates.py --dup <oof> <oof_dup> <out.json>   -- rule §7 duplicate-training check (prints MR_DUP PASS=...)
       python mr_gates.py --identity <oof> <out.json>        -- per-arm model-text and score shas (rule §7 report)"""
import os, sys, json, hashlib, time
import numpy as np
R = "/dev/shm/mretrain_2026-09-26"; N = "/dev/shm/news2_2026-09-23"
KING_SHA = "a10b872506ca60afcd0f69b0e43d17a548cdd7c6956075000aac954b21e3df9a"
LEGS_SHA = "9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


PROVENANCE = ("model_sha256",)   # rule §7: provenance text of a King OOF -- reported, never gated


def same(x, y): return x.dtype == y.dtype and x.shape == y.shape and x.tobytes() == y.tobytes()


def arrays_equal(p, q):
    a, b = np.load(p, allow_pickle=False), np.load(q, allow_pickle=False)
    if sorted(a.files) != sorted(b.files): return False, {"files": [sorted(a.files), sorted(b.files)]}
    bad = [k for k in a.files if not same(a[k], b[k])]
    return not bad, {"differing_arrays": bad}


def oof_equal(p, q):
    """King OOF identity (rule §7): every array except PROVENANCE bitwise equal; the file sets must match (a new array is gated)"""
    a, b = np.load(p, allow_pickle=False), np.load(q, allow_pickle=False)
    if sorted(a.files) != sorted(b.files): return False, {"files": [sorted(a.files), sorted(b.files)]}
    gated = sorted(k for k in a.files if k not in PROVENANCE)
    bad = [k for k in gated if not same(a[k], b[k])]
    return not bad, {"gated_arrays": gated, "differing_arrays": bad,
                     "provenance_equal_reported_not_gated": {k: bool(same(a[k], b[k])) for k in PROVENANCE if k in a.files}}


def identity(p):
    z = np.load(p, allow_pickle=False); ms = z["model_sha256"]
    return {"container_sha256": sha(p), "array_sha256": {k: hashlib.sha256(z[k].tobytes()).hexdigest() for k in sorted(z.files) if k not in PROVENANCE},
            "model_text_sha256_distinct": sorted(set(ms.tolist()) - {""})}


def main():
    rec = {"device": "mr_gates.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "rule": "docs/DECISION_RULE_king_monthly_retrain_2026-09-26.md (1f2f5c4e9) section 0 + section 7 revision 1 (da04c28f9)", "gates": {}}
    g = rec["gates"]
    A0 = f"{R}/arms/A0_m0"
    ok, det = oof_equal(f"{A0}/work/king/KING_OOF.npz", f"{R}/gate/A0_m0_dup/KING_OOF.npz")
    g["G1_determinism"] = {"PASS": ok, **det, "container_equal": sha(f"{A0}/work/king/KING_OOF.npz") == sha(f"{R}/gate/A0_m0_dup/KING_OOF.npz")}
    ref = f"{N}/work/king/KING_OOF.npz"; ref_ok = sha(ref) == KING_SHA
    ok, det = oof_equal(f"{A0}/work/king/KING_OOF.npz", ref)
    g["G2_A0_equals_in_service_King"] = {"PASS": bool(ok and ref_ok), "reference_sha_ok": ref_ok, **det,
                                         "container_sha": sha(f"{A0}/work/king/KING_OOF.npz"), "container_equal": sha(f"{A0}/work/king/KING_OOF.npz") == KING_SHA}
    g3 = {}
    refl = f"{N}/work/legs.npz"; ok, det = arrays_equal(f"{A0}/work/legs.npz", refl)
    g3["legs"] = {"PASS": bool(ok and sha(refl) == LEGS_SHA), **det, "container_equal": sha(f"{A0}/work/legs.npz") == LEGS_SHA}
    for s in ("42", "2027"):
        for pol in ("literal", "scaled_diagnostic"):
            mine, theirs = f"{A0}/work/combo_s{s}/{pol}.npz", f"{N}/work/combo_s{s}/{pol}.npz"
            ok, det = arrays_equal(mine, theirs)
            g3[f"combo_s{s}_{pol}"] = {"PASS": ok, **det, "container_equal": sha(mine) == sha(theirs)}
        cfg = json.load(open(f"{N}/configs/RUN_CONFIG_NEWS2_s{s}X_2026-09-23.json"))
        r = [x for x in cfg["runs"] if x["tag"] == f"NEWS2_s{s}X|scaled|rule|raw|UAFE"][0]["targets"]["sources"][0]
        mine = f"{A0}/targets/TARGETS_NEWS2_s{s}.npz"
        theirs_ok = os.path.exists(r["npz"]) and sha(r["npz"]) == r["npz_sha256"]
        ok, det = arrays_equal(mine, r["npz"]) if theirs_ok else (False, {"reference_missing_or_changed": r["npz"]})
        g3[f"targets_s{s}"] = {"PASS": ok, **det, "pinned": r["npz_sha256"], "mine": sha(mine), "container_equal": sha(mine) == r["npz_sha256"]}
    g["G3_A0_chain_reproduces_legs_combo_targets"] = {"PASS": all(v["PASS"] for v in g3.values()), "items": g3}
    rec["ALL_PASS"] = all(v["PASS"] for v in g.values())
    json.dump(rec, open(sys.argv[1] + ".tmp", "w"), indent=1); os.replace(sys.argv[1] + ".tmp", sys.argv[1])
    print("MR_GATES ALL_PASS=%s sha=%s" % (rec["ALL_PASS"], sha(sys.argv[1])), json.dumps({k: v["PASS"] for k, v in g.items()}), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "--dup":
        ok, det = oof_equal(sys.argv[2], sys.argv[3])
        r = {"device": "mr_gates.py --dup", "self_sha256": sha(os.path.abspath(__file__)), "rule": "section 7 revision 1 (da04c28f9)", "PASS": bool(ok), **det,
             "identity": {sys.argv[2]: identity(sys.argv[2]), sys.argv[3]: identity(sys.argv[3])}}
        json.dump(r, open(sys.argv[4] + ".tmp", "w"), indent=1); os.replace(sys.argv[4] + ".tmp", sys.argv[4])
        print("MR_DUP PASS=%s" % ok, json.dumps(det), flush=True)
    elif sys.argv[1] == "--identity":
        r = {"device": "mr_gates.py --identity", "self_sha256": sha(os.path.abspath(__file__)), "oof": sys.argv[2], **identity(sys.argv[2])}
        json.dump(r, open(sys.argv[3] + ".tmp", "w"), indent=1); os.replace(sys.argv[3] + ".tmp", sys.argv[3])
        print("MR_IDENTITY", json.dumps({"P": r["array_sha256"]["P"][:16], "models": [m[:16] for m in r["model_text_sha256_distinct"]]}), flush=True)
    else:
        main()
