"""R9 lineage audit of f10_A0 (READ-ONLY). ENV whitelist = EMPTY SET."""
import os, json, time, hashlib, numpy as np
assert [] == []
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
R = {}
# the yearly trainer's own report: which data chain did it read?
for s in ("42", "2027"):
    p = "/workspace/f8_ext/results/f10_V2MAIN_s%s.json" % s
    J = json.load(open(p))
    R["f8_ext_report_s%s" % s] = {k: J.get(k) for k in ("arm","seed","cost","ldd","epochs","lr","win","burn","stride","embargo",
        "self_sha256","targets_sha256","fea82_sha256","fea89_sha256","net_mean_all")}
    R["f8_ext_report_s%s" % s]["folds"] = sorted(J.get("folds", {}).keys())
# the axis that f10_A0 lives on
for k, p in [("dlw_ext_targets", "/workspace/dlw_ext/data/dlw_targets.npz"),
             ("dlw_v4raw_targets", "/workspace/dlw_v4raw/data/dlw_targets.npz")]:
    z = np.load(p, allow_pickle=True); E = z["E_ts"].astype(np.int64)
    R[k] = {"path": p, "sha256": sha(p), "n": int(len(E)), "first": iso(E[0]), "last": iso(E[-1])}
for k, p in [("f8_ext_fea89", "/workspace/f8_ext/data/f8_fea89.npz"),
             ("f8_v4_fea89", "/workspace/f8_v4/data/f8_fea89.npz"),
             ("dlw_ext_fea82", "/workspace/dlw_ext/data/dlw_fea82.npz"),
             ("dlw_v4raw_fea82", "/workspace/dlw_v4raw/data/dlw_fea82.npz")]:
    R[k] = {"path": p, "sha256": sha(p), "X_shape": list(np.load(p, allow_pickle=True)["X"].shape)}
# which 5m cache did the _ext chain come from? read the fea82 meta_json
for k, p in [("dlw_ext_fea82_meta", "/workspace/dlw_ext/data/dlw_fea82.npz"),
             ("dlw_v4raw_fea82_meta", "/workspace/dlw_v4raw/data/dlw_fea82.npz")]:
    try:
        mj = np.load(p, allow_pickle=True)["meta_json"]
        R[k] = json.loads(str(mj)) if mj.dtype.kind in "US" else json.loads(str(mj.item()))
    except Exception as e:
        R[k] = {"err": repr(e)}
print(json.dumps(R, indent=1))
