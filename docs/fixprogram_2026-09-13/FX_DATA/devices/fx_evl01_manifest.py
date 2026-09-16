#!/usr/bin/env python3
"""fx_evl01_manifest.py — EVL-01 (c): enumerate the devices whose launch must carry CAL. Committed before it is run.

The lead's ruling is (a) + (c), not (b): the 54 archived devices keep every byte, because SPEC section 7 pins `w10_sleeve.py` at
sha b88e35a4 as the A0 reference and 54 committed devices write their self-sha into receipts, so editing the default would break a
frozen spec and 54 reproductions at once. The protection goes on the LAUNCH side instead.

This device builds the manifest the guard reads. It keys on the device's **sha256**, not its path, for two reasons: the same blob
appears at two paths (the workspace mirror), and the A0 device that actually runs on pod2 is not a git file at all.

Detection is by AST, not by text. A text match counts every file that merely QUOTES the pattern — the first run of this device
matched 56 files, two of which were an FX-DATA device whose docstring mentions the default and this manifest builder itself, whose
`PAT` constant is the pattern. Those are mentions, not readers, and demanding CAL at their launch would be absurd. The predicate is
therefore: the module contains a call to `os.environ.get` (or `environ.get`) whose first argument is the literal "CAL" and which has
a second argument that is not "log" — i.e. a reader with a non-log default. Quoting is irrelevant to an AST, so single quotes and
whitespace variants are caught too.

Sources:
  * every committed .py whose AST contains such a call, read as a git blob at a pinned commit (never the working tree);
  * the pod2 runtime `w10_sleeve.py` sha b88e35a4, added explicitly because SPEC section 7 pins it and it is the A0 device.

Usage: python3 fx_evl01_manifest.py <commit> <out_manifest.json>
"""
import os, sys, json, time, hashlib, subprocess
COMMIT, OUT = sys.argv[1], sys.argv[2]
A0_DEVICE = {"name": "w10_sleeve.py (pod2 runtime, not a git file)",
             "sha256": "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650",
             "why": "SPEC section 7 pins this exact sha as the A0 reference device; it reads CAL with the same default"}

def git(*a):
    return subprocess.run(["git"] + list(a), capture_output=True, text=True, check=True).stdout

import ast

def reads_cal_with_non_log_default(src):
    """True iff the module CALLS os.environ.get("CAL", <default != "log">). A string that merely contains the text is not a call."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False, None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
            continue
        v = node.func.value
        ok_recv = (isinstance(v, ast.Attribute) and v.attr == "environ") or (isinstance(v, ast.Name) and v.id == "environ")
        if not ok_recv or not node.args:
            continue
        a0 = node.args[0]
        if not (isinstance(a0, ast.Constant) and a0.value == "CAL"):
            continue
        if len(node.args) < 2:
            return True, None                      # no default at all is fine for a new device, but record it
        a1 = node.args[1]
        dflt = a1.value if isinstance(a1, ast.Constant) else "<non-literal>"
        if dflt != "log":
            return True, dflt
    return False, None

# -z: NUL-separated and UNQUOTED. Without it git quotes any path containing a space or a non-ASCII byte, and this tree has
# such paths, so the plain-text form is not a usable path list.
cand = sorted(set(x.split(":", 1)[1] for x in git("grep", "-l", "-z", "-F", "CAL", COMMIT, "--", "*.py").split("\0") if ":" in x))
paths, defaults = [], {}
for p in cand:
    blob = subprocess.run(["git", "show", "%s:%s" % (COMMIT, p)], capture_output=True, check=True).stdout
    hit, dflt = reads_cal_with_non_log_default(blob.decode("utf-8", "replace"))
    if hit:
        paths.append(p); defaults[p] = dflt
rows = {}
for p in paths:
    blob = subprocess.run(["git", "show", "%s:%s" % (COMMIT, p)], capture_output=True, check=True).stdout
    h = hashlib.sha256(blob).hexdigest()
    rows.setdefault(h, {"sha256": h, "paths": [], "bytes": len(blob), "default": defaults[p]})["paths"].append(p)
man = {"tool": "fx_evl01_manifest.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
       "commit": COMMIT, "detection": "AST: a call to os.environ.get('CAL', <default != log>); text mentions are not counted",
       "candidate_prefilter": "git grep -l -F CAL", "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "ruling": "FIXPROGRAM EVL-01 = (a) archives untouched + (c) launch-side guard; never (b) re-pin the frozen spec",
       "n_paths": len(paths), "n_distinct_blobs": len(rows),
       "devices": sorted(rows.values(), key=lambda r: r["paths"][0]), "extra": [A0_DEVICE]}
man["requiring_cal_sha256"] = sorted(set([r["sha256"] for r in man["devices"]] + [A0_DEVICE["sha256"]]))
man["a0_sha_already_among_the_git_copies"] = A0_DEVICE["sha256"] in {r["sha256"] for r in man["devices"]}
json.dump(man, open(OUT, "w"), indent=1)
print("FX_EVL01_MANIFEST_DONE", json.dumps({"paths": len(paths), "distinct_blobs": len(rows),
                                            "shas_requiring_cal": len(man["requiring_cal_sha256"])}), flush=True)
