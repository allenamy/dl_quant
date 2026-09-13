#!/usr/bin/env python3
"""t5d_run2_diff.py — Mac. Proves that bridge run 2 changed no run-1 field (only added the omitted pre-registered descriptive outputs).
Launch: /usr/bin/python3 devices/t5d_run2_diff.py "$PWD"
"""
import os, sys, json, hashlib, time
T = os.path.abspath(sys.argv[1]); sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
A = T + "/receipts/pod2/run1_bridge_incomplete/RECEIPT_T5d_bridge.json"; B = T + "/receipts/pod2/RECEIPT_T5d_bridge.json"
a = json.load(open(A)); b = json.load(open(B)); diffs = []; added = []
def cmp(x, y, p):
    if isinstance(x, dict):
        if not isinstance(y, dict): diffs.append([p, "type"]); return
        for k in x:
            if k not in y: diffs.append([p + "/" + k, "missing in run 2"])
            else: cmp(x[k], y[k], p + "/" + k)
        added.extend(p + "/" + k for k in y if k not in x)
    elif isinstance(x, list):
        if not isinstance(y, list) or len(x) != len(y): diffs.append([p, "list length"]); return
        for i, (u, v) in enumerate(zip(x, y)): cmp(u, v, p + "[%d]" % i)
    elif x != y: diffs.append([p, repr(x), repr(y)])
cmp(a, b, "")
ALLOWED = {"/self_sha256", "/built_utc", "/wall_s"}
RC = dict(self_sha256=sha(os.path.abspath(__file__)), run1=dict(path=os.path.relpath(A, T), sha256=sha(A), device_sha256=a["self_sha256"]), run2=dict(path=os.path.relpath(B, T), sha256=sha(B), device_sha256=b["self_sha256"]),
          run1_fields_changed=diffs, fields_added=added, components_npz_equal=a["components_npz_sha256"] == b["components_npz_sha256"],
          PASS=bool(all(d[0] in ALLOWED for d in diffs) and a["components_npz_sha256"] == b["components_npz_sha256"]), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T + "/receipts/RECEIPT_T5d_bridge_run2_diff.json", "w"), indent=1); print(json.dumps(dict(PASS=RC["PASS"], changed=[d[0] for d in diffs], n_added=len(added))))
