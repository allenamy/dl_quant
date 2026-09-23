#!/usr/bin/env python3
"""m3_strip_receipt — deploy receipt: every M3 insertion stripped from the three modified executor files gives back the BASE blobs
byte for byte (so "mode off == today's executor" rests on (i) this source identity and (ii) tests_beta_overlay [Z], which runs
the new code against the stripped code on the same inputs).
usage: /usr/bin/python3 m3_strip_receipt.py <executor_checkout> <base_sha> <out_json>
Reads the checkout's WORKING TREE files and `git show <base_sha>:<path>`; writes one JSON; exit 0 iff all three are identical."""
import hashlib, json, os, subprocess, sys, importlib.util
root, base, out = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("beta_overlay_r", os.path.join(root, "live", "beta_overlay.py"))
BO = importlib.util.module_from_spec(spec); spec.loader.exec_module(BO)
sha = lambda b: hashlib.sha256(b).hexdigest()
rec = {"device": "m3_strip_receipt.py", "self_sha256": sha(open(os.path.abspath(__file__), "rb").read()), "checkout": root,
       "base": base, "beta_overlay_sha256": sha(open(os.path.join(root, "live", "beta_overlay.py"), "rb").read()), "files": {}}
ok = True
for rel in ("scheduler/anchor_loop.py", "live/binance_executor.py", "live/external_book.py"):
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
