"""Exercise the three read-back checks against real adapter outputs, plus a red control."""
import json, sys, hashlib, shutil, os, tempfile
import numpy as np

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def checks(tnpz, tjson):
    R = json.load(open(tjson))                      # 1. receipt parses
    with np.load(tnpz, allow_pickle=False) as z:    # 2. npz arrays read back
        for k in z.files:
            a = z[k]; _ = a.tobytes()[:1] if a.size else b""
    n = sha(tnpz)
    assert R.get("targets_npz_sha256") == n, (      # 3. receipt content ties to artifact
        "receipt records %s but npz is %s" % (str(R.get("targets_npz_sha256"))[:16], n[:16]))
    return True

tnpz, tjson = sys.argv[1], sys.argv[2]
print("GREEN: real adapter outputs ->", checks(tnpz, tjson))

d = tempfile.mkdtemp()
for label, breaker in (
    ("receipt truncated to 50 bytes", lambda np_, js: open(js, "r+b").truncate(50)),
    ("receipt's npz sha altered", lambda np_, js: (lambda R: json.dump({**R, "targets_npz_sha256": "0"*64}, open(js, "w")))(json.load(open(js)))),
    ("npz given a size-preserving NUL tail", lambda np_, js: (lambda f: (f.seek(-200, os.SEEK_END), f.write(b"\0"*200), f.close()))(open(np_, "r+b"))),
):
    a, b = os.path.join(d, "t.npz"), os.path.join(d, "t.json")
    shutil.copy(tnpz, a); shutil.copy(tjson, b)
    breaker(a, b)
    try:
        checks(a, b); print("  RED-FAIL %-40s not caught -- the check is vacuous" % label)
    except Exception as e:
        print("  RED-OK   %-40s %s: %s" % (label, type(e).__name__, str(e)[:60]))
shutil.rmtree(d, ignore_errors=True)
