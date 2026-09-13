# Smoke harness patcher (NOT a device; synthetic returns so no real statistic is produced before the prereg freeze).
import re, sys, json, hashlib, os, shutil
S = "/workspace/uplift_r3_2026-09-13/L2_smoke2"
def sub(path, old, new, count=1):
    s = open(path).read(); assert s.count(old) >= 1, (path, old[:60]); s = s.replace(old, new) if count is None else s.replace(old, new, count); open(path, "w").write(s)
d = S + "/devices/"
sub(d + "l2_common.py", 'L2 = "/workspace/uplift_r3_2026-09-13/L2"', 'L2 = "%s"' % S)
sub(d + "run_l2.sh", "cd /workspace/uplift_r3_2026-09-13/L2 ", "cd %s " % S)
sub(d + "l2_b_common.py", '''def check_prereg():
    s = C.sha256(PREREG); fr = open(FREEZE).read()''', '''def check_prereg():
    return dict(prereg="SMOKE")
    s = C.sha256(PREREG); fr = open(FREEZE).read()''')
sub(d + "l2_b_common.py", '''    D["Y"] = np.asarray(M["y4"], np.float64); assert D["Y"].shape == (10182, C.NW)''',
    '''    D["Y"] = np.asarray(M["y4"], np.float64); assert D["Y"].shape == (10182, C.NW)
    _fin = np.isfinite(D["Y"]); D["Y"] = np.where(_fin, np.random.default_rng(12345).normal(0.0, 0.02, D["Y"].shape), np.nan)   # SMOKE: synthetic returns''')
sub(d + "l2_b_common.py", "LGB_ROUNDS = 300", "LGB_ROUNDS = 20")
sub(d + "l2_b_common.py", "MIN_ANCHOR = 10; NB = 2000; NNULL = 500", "MIN_ANCHOR = 10; NB = 200; NNULL = 20")
sub(d + "l2_b_fit.py", '''assert all(stc["gates"].values()), ("selftest gates not all passed", stc["gates"])''', '''print("SMOKE selftest gates", stc["gates"])''')
sub(d + "l2_b_selftest.py", '''assert all(GATES.values()), ("SELFTEST GATE FAILED", GATES)''', '''print("SMOKE GATES", GATES)''')
sub(d + "l2_b_fit.py", "assert n_fits == 96, n_fits", "print('SMOKE n_fits', n_fits)")
# fake pull receipt from a MANIFEST snapshot
man = json.load(open("/workspace/uplift_r3_2026-09-13/L2/out/metrics/MANIFEST.json"))
man = {k: v for k, v in man.items() if os.path.exists(S + "/out/metrics/%s.npz" % k)}
json.dump(man, open(S + "/out/metrics/MANIFEST.json", "w"))
ms = hashlib.sha256(open(S + "/out/metrics/MANIFEST.json", "rb").read()).hexdigest()
tot = dict(files_200=sum(v["files_200"] for v in man.values()), files_failed=0, regime_violations=sum(v["regime_violations"] for v in man.values()),
           regime_counts={k: sum(v["regime_counts"][k] for v in man.values()) for k in ("END", "START", "UNK", "NA")})
json.dump(dict(totals=tot, manifest=dict(sha256=ms)), open(S + "/receipts/RECEIPT_L2_B_pull.json", "w"))
print("smoke patched; manifest symbols", len(man))
