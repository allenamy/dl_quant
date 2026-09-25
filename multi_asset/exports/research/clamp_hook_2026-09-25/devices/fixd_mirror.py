#!/usr/bin/env python3
"""Build the engine's FIX-D arm inputs on pod2 WITHOUT touching the filed mirror (lead 2026-09-25: "引擎镜像副本(新 pin,不动在案镜像)").
1. copy <src mirror> (paths.exec_mirror of RUN_CONFIG_NEWS2_s42X) to <dst mirror>;
2. apply fixD_anchor_loop.diff (the executor fix-pkg-d commit 1e70316's anchor_loop.py hunks) to <dst>/exec_tree_409ea16/scheduler/anchor_loop.py
   with `patch -p1 --dry-run` first (the 409ea16 withhold_pop / apply_withhold_and_reshape are AST-identical to 96acfdd's — checked
   2026-09-25) — any rejected hunk ⇒ refuse;
3. assert: the ONLY file that differs between src and dst is scheduler/anchor_loop.py (diff -rq);
4. write a copy of INPUT_MANIFEST.json with that one sha replaced, and a derived RUN_CONFIG (paths.exec_mirror, pins.input_manifest {path, sha},
   paths.pod_root) — nothing else changed; every change listed in the config's _diagnostic_note.
usage: /workspace/venv/bin/python fixd_mirror.py <src mirror> <dst mirror> <diff> <base RUN_CONFIG> <out RUN_CONFIG> <pod_root>"""
import hashlib, json, os, shutil, subprocess, sys, copy

src, dst, diff, cfg_in, cfg_out, root = sys.argv[1:7]
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
assert not os.path.exists(dst), f"refusing to overwrite {dst}"
shutil.copytree(src, dst, symlinks=True)
tree = os.path.join(dst, "exec_tree_409ea16")
r = subprocess.run(["patch", "-p1", "--dry-run", "-d", tree, "-i", os.path.abspath(diff)], capture_output=True, text=True)
assert r.returncode == 0, f"dry-run rejected: {r.stdout[-600:]} {r.stderr[-300:]}"
r = subprocess.run(["patch", "-p1", "-d", tree, "-i", os.path.abspath(diff)], capture_output=True, text=True)
assert r.returncode == 0, r.stdout[-600:]
d = subprocess.run(["diff", "-rq", src, dst], capture_output=True, text=True).stdout.strip().splitlines()
assert len(d) == 1 and d[0].endswith("exec_tree_409ea16/scheduler/anchor_loop.py differ"), d
c = json.load(open(cfg_in)); man_in = c["pins"]["input_manifest"]["path"]; m = json.load(open(man_in))
key = "exec_tree_409ea16/scheduler/anchor_loop.py"; old = m["executor_tree"]["files_sha256"][key]
m2 = copy.deepcopy(m); m2["executor_tree"]["files_sha256"][key] = sha(os.path.join(tree, "scheduler", "anchor_loop.py"))
m2["_fixD_note"] = {"derived_from": man_in, "derived_from_sha256": sha(man_in), "changed": {key: [old, m2["executor_tree"]["files_sha256"][key]]}}
man_out = os.path.join(os.path.dirname(dst), "INPUT_MANIFEST_fixD.json"); json.dump(m2, open(man_out, "w"), indent=1)
c2 = copy.deepcopy(c); c2["paths"] = dict(c2["paths"]); c2["paths"]["exec_mirror"] = dst; c2["paths"]["pod_root"] = root
c2["pins"] = dict(c2["pins"]); c2["pins"]["input_manifest"] = {"path": man_out, "sha256": sha(man_out)}
want = "NEWS2_s42X|scaled|rule|raw|UAFE"; c2["runs"] = [copy.deepcopy(r_) for r_ in c["runs"] if r_["tag"] == want]; assert len(c2["runs"]) == 1
c2["_diagnostic_note"] = {"purpose": "FIX-D engine arm (dust pop before reshape), lead 2026-09-25", "derived_from": cfg_in, "derived_from_sha256": sha(cfg_in),
                          "changed": ["paths.exec_mirror -> " + dst, "pins.input_manifest -> " + man_out, "paths.pod_root -> " + root],
                          "mirror_diff": d, "anchor_loop_sha": [old, m2["executor_tree"]["files_sha256"][key]], "diff_sha256": sha(diff)}
json.dump(c2, open(cfg_out, "w"), indent=1)
print("FIXD_MIRROR_OK", json.dumps({"anchor_loop": [old[:12], m2["executor_tree"]["files_sha256"][key][:12]], "manifest": man_out, "config": cfg_out}))
