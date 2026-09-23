#!/usr/bin/env python3
"""m3_strip_receipt — deploy receipt: every M3 insertion stripped from the modified executor files that carry M3 markers (derived, see census) gives back the BASE blobs
byte for byte (so "mode off == today's executor" rests on (i) this source identity and (ii) tests_beta_overlay [Z], which runs
the new code against the stripped code on the same inputs).
usage: /usr/bin/python3 m3_strip_receipt.py <executor_checkout> <base_sha> <out_json>
Reads the checkout's WORKING TREE files and `git show <base_sha>:<path>`; writes one JSON; exit 0 iff every stripped file is identical and the set is non-empty."""
import hashlib, json, os, subprocess, sys, importlib.util
root, base, out = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("beta_overlay_r", os.path.join(root, "live", "beta_overlay.py"))
BO = importlib.util.module_from_spec(spec); spec.loader.exec_module(BO)
sha = lambda b: hashlib.sha256(b).hexdigest()
rec = {"device": "m3_strip_receipt.py", "self_sha256": sha(open(os.path.abspath(__file__), "rb").read()), "checkout": root,
       "base": base, "beta_overlay_sha256": sha(open(os.path.join(root, "live", "beta_overlay.py"), "rb").read()), "files": {}}
ok = True
# The strip set is DERIVED, not listed: every .py file that exists in the base AND carries an M3 marker. A file added to the M3
# wiring tomorrow is covered without editing this device; the census of every modified file is written beside the verdict.
_mod = subprocess.check_output(["git", "-C", root, "diff", "--name-only", base]).decode().split()
_mod += [l[3:] for l in subprocess.check_output(["git", "-C", root, "status", "--porcelain", "--untracked-files=no"]).decode().splitlines()]
_mod = sorted(m for m in set(_mod) if not m.startswith("state/"))   # state/ = the battery's copied live state, not code
_marks = ("# ── M3-BEGIN", "# M3-LINE", "# M3-ORIG:")
def _in_base(rel):
    return subprocess.run(["git", "-C", root, "cat-file", "-e", f"{base}:{rel}"], capture_output=True).returncode == 0
STRIP = [r for r in _mod if r.endswith(".py") and os.path.exists(os.path.join(root, r)) and _in_base(r)
         and any(m in open(os.path.join(root, r), encoding="utf-8").read() for m in _marks)]
rec["census"] = {"modified_vs_base": _mod, "stripped": STRIP,
                 "not_stripped": [r for r in _mod if r not in STRIP],
                 "rule": "stripped = .py in base carrying an M3 marker; the others are new files, tests, config or registries"}
if not STRIP:
    ok = False                                            # an empty strip set proves nothing (never a vacuous IDENTICAL)
for rel in STRIP:
    new = open(os.path.join(root, rel), "rb").read()
    old = subprocess.check_output(["git", "-C", root, "show", f"{base}:{rel}"])
    st = BO.strip_m3(new.decode()).encode()
    same = st == old
    ok &= same
    rec["files"][rel] = {"new_sha256": sha(new), "stripped_sha256": sha(st), "base_blob_sha256": sha(old), "stripped_equals_base": same,
                         "n_lines_new": new.count(b"\n"), "n_lines_base": old.count(b"\n")}
rec["VERDICT"] = "IDENTICAL" if ok else "DIFFERENT"
json.dump(rec, open(out, "w"), indent=1)
print(f"M3_STRIP_RECEIPT VERDICT={rec['VERDICT']} base={base} " + " ".join(f"{k}={'==' if v['stripped_equals_base'] else '!='}" for k, v in rec["files"].items()))
sys.exit(0 if ok else 1)
