"""GATE P (PREREG r16 §2): XMODE='' with AUX16 in {0,1}, both seeds, must reproduce the ARCHIVED r3k A0 arms
BITWISE on rec and W (NaN positions identical). Fail => STOP."""
import numpy as np, json, time, sys
from concurrent.futures import ThreadPoolExecutor
import common16 as C
C.setup(); dev_sha = C.assert_pins()
print("device sha256", dev_sha, "gpu before:", C.gpu(), "load:", C.loadavg(), flush=True)
assert C.loadavg() <= 6.0, "load > 6, wait"
jobs = [("GP_s42_aux0", 42, "", 0, 0), ("GP_s42_aux1", 42, "", 0, 1), ("GP_s2027_aux0", 2027, "", 0, 0), ("GP_s2027_aux1", 2027, "", 0, 1)]
recs = {}
with ThreadPoolExecutor(max_workers=4) as ex:
    for tag, st, er in ex.map(lambda j: C.run(*j), jobs):
        print(tag, st, flush=True); recs[tag] = er
C.save_env("GATE_RUN_ENV.json", recs)
def cmp(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    nx, ny = np.isnan(x), np.isnan(y)
    bw = bool(x.shape == y.shape and np.array_equal(nx, ny) and np.array_equal(x[~nx], y[~ny]))
    return {"bitwise": bw, "shape": list(x.shape), "maxabs": 0.0 if bw else float(np.nanmax(np.abs(x - y)))}
OUT = {"device": C.DEV, "device_sha256": dev_sha, "parent_sha256": C.sha(C.PARENT), "prereg_sha256": C.sha(C.PREREG)}
ok = True
for s in (42, 2027):
    A = np.load("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s%d.npz" % s, allow_pickle=True)
    for aux in (0, 1):
        Z = np.load(C.R + "/arms/GP_s%d_aux%d.npz" % (s, aux), allow_pickle=True)
        r = {"rec": cmp(Z["rec"], A["rec"]), "W": cmp(Z["W"], A["W"]), "cols_equal": bool(np.array_equal(Z["cols"], A["cols"]))}
        ok &= r["rec"]["bitwise"] and r["W"]["bitwise"] and r["cols_equal"]
        OUT["s%d_aux%d_vs_archived" % (s, aux)] = r
    Z0 = np.load(C.R + "/arms/GP_s%d_aux0.npz" % s, allow_pickle=True); Z1 = np.load(C.R + "/arms/GP_s%d_aux1.npz" % s, allow_pickle=True)
    OUT["s%d_aux0_vs_aux1" % s] = {"rec": cmp(Z0["rec"], Z1["rec"]), "W": cmp(Z0["W"], Z1["W"])}
    ok &= OUT["s%d_aux0_vs_aux1" % s]["rec"]["bitwise"] and OUT["s%d_aux0_vs_aux1" % s]["W"]["bitwise"]
    cfg = json.loads(str(Z1["config_json"])); OUT["s%d_config_R16" % s] = cfg["R16"]
OUT["archived_sha256"] = {k: C.SHA[k] for k in ("A0_s42", "A0_s2027")}
OUT["gpu_after"] = C.gpu(); OUT["PASS"] = bool(ok)
json.dump(OUT, open(C.R + "/receipts/GATE_P.json", "w"), indent=1)
print(json.dumps(OUT, indent=1)); print("GATE_P", "PASS" if ok else "FAIL")
