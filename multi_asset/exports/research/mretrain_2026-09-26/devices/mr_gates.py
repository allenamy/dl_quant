"""mr_gates.py — device gates of DECISION_RULE_king_monthly_retrain_2026-09-26.md §0 (1f2f5c4e9), items 1-3 (item 4, the red
control, is a book-layer reading and is judged by the reading device). Any FAIL => the whole family stops.
  G1 determinism : A0 rs=0 trained twice (arms/A0_m0 and gate/A0_m0_dup) -> KING_OOF arrays bitwise equal
  G2 A0 == in-service King: arrays bitwise equal to news2 work/king/KING_OOF.npz, whose file sha must be a10b8725...
  G3 A0 through the chain: legs arrays == news2 legs (9ee5886f...); combo literal/scaled arrays == news2 combo_s{42,2027};
     adapter targets arrays == the in-service X config's pinned targets.
Container (file) shas are reported too; the gate is on the ARRAYS (the zip container of np.savez may carry a timestamp).
usage: python mr_gates.py <out.json>"""
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


def arrays_equal(p, q):
    a, b = np.load(p, allow_pickle=False), np.load(q, allow_pickle=False)
    if sorted(a.files) != sorted(b.files): return False, {"files": [sorted(a.files), sorted(b.files)]}
    bad = [k for k in a.files if not (a[k].dtype == b[k].dtype and a[k].shape == b[k].shape and a[k].tobytes() == b[k].tobytes())]
    return not bad, {"differing_arrays": bad}


rec = {"device": "mr_gates.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "rule": "docs/DECISION_RULE_king_monthly_retrain_2026-09-26.md (1f2f5c4e9) section 0", "gates": {}}
g = rec["gates"]
A0 = f"{R}/arms/A0_m0"
ok, det = arrays_equal(f"{A0}/work/king/KING_OOF.npz", f"{R}/gate/A0_m0_dup/KING_OOF.npz")
g["G1_determinism"] = {"PASS": ok, **det, "container_equal": sha(f"{A0}/work/king/KING_OOF.npz") == sha(f"{R}/gate/A0_m0_dup/KING_OOF.npz")}
ref = f"{N}/work/king/KING_OOF.npz"; ref_ok = sha(ref) == KING_SHA
ok, det = arrays_equal(f"{A0}/work/king/KING_OOF.npz", ref)
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
