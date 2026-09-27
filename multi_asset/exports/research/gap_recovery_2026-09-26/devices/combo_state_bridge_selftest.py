#!/usr/bin/env python3
"""Sandbox self-test of combo_state_bridge.py on COPIES of the live files (never touches ~/wide_shadow).
Green baseline first, then each red control must turn red, then rollback. Prints SELFTEST PASS n/n."""
import json, os, shutil, subprocess, sys, tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); DEV = os.path.join(HERE, "combo_state_bridge.py")
S, T = int(sys.argv[1]), int(sys.argv[2])
LIVE_FEA = os.path.expanduser("~/wide_shadow/fea171"); LIVE_ST = os.path.expanduser("~/wide_shadow/state")
res = []


def run(*args):
    p = subprocess.run([sys.executable, DEV, *args], capture_output=True, text=True); return p.returncode, p.stdout + p.stderr


def ok(name, cond, out=""):
    res.append(cond); print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    if not cond: print(out)


def sandbox():
    d = tempfile.mkdtemp(prefix="bridge_selftest_"); fea = os.path.join(d, "fea171"); st = os.path.join(d, "state")
    os.makedirs(fea); os.makedirs(st)
    for leg in ("kc", "fc", "f10"):
        shutil.copy2(f"{LIVE_FEA}/state_H_{leg}_{S}.npz", fea)
    shutil.copy2(f"{LIVE_FEA}/combo_stage.py", fea)
    for f in ("aux.json", "combo_live_status.json"):
        shutil.copy2(f"{LIVE_ST}/{f}", st)
    return d, fea, st


d, fea, st = sandbox(); rc_ = os.path.join(d, "r.json"); base = ["--src", str(S), "--dst", str(T), "--fea", fea, "--state", st]
rc, out = run("check", *base, "--receipt", rc_); ok("baseline check PASS", rc == 0 and "CHECK PASS" in out, out)
rc, out = run("apply", *base, "--receipt", rc_); ok("apply PASS", rc == 0 and "APPLY PASS" in out, out)
rc, out = run("verify", *base, "--receipt", rc_); ok("verify PASS", rc == 0 and "VERIFY PASS" in out, out)
# combo's own predicate on the bridged file, for the anchor that will read it
for leg in ("kc", "fc", "f10"):
    z = np.load(f"{fea}/state_H_{leg}_{T}.npz"); A = T + 14400
    ok(f"combo predicate int(anchor)==A-14400 for {leg}", int(z["anchor"]) == A - 14400)
rc, out = run("apply", *base, "--receipt", rc_ + ".2"); ok("RED re-apply refused (files exist)", rc != 0 and "APPLY FAIL" in out, out)
# tamper one value -> verify red
p = f"{fea}/state_H_kc_{T}.npz"; z = dict(np.load(p)); z["val"] = z["val"].copy(); z["val"][0] += 1e-12
os.remove(p); np.savez(p, **z)
rc, out = run("verify", *base, "--receipt", rc_); ok("RED tampered val -> verify FAIL", rc != 0 and "VERIFY FAIL" in out, out)
rc, out = run("rollback", *base, "--receipt", rc_); ok("RED rollback refuses the changed file", rc != 0 and "changed since the bridge" in out, out)
ok("rollback removed the two unchanged files", not os.path.exists(f"{fea}/state_H_fc_{T}.npz") and not os.path.exists(f"{fea}/state_H_f10_{T}.npz"))
shutil.rmtree(d)
# producer ran since S -> check red
d, fea, st = sandbox(); a = json.load(open(f"{st}/aux.json")); a["last_anchor"] = S + 14400; json.dump(a, open(f"{st}/aux.json", "w"))
rc, out = run("check", "--src", str(S), "--dst", str(T), "--fea", fea, "--state", st, "--receipt", os.path.join(d, "r.json"))
ok("RED producer advanced -> check FAIL", rc != 0 and "producer aux" in out, out); shutil.rmtree(d)
# a state already inside the gap -> check red
d, fea, st = sandbox(); shutil.copy2(f"{fea}/state_H_fc_{S}.npz", f"{fea}/state_H_fc_{S + 14400}.npz")
rc, out = run("check", "--src", str(S), "--dst", str(T), "--fea", fea, "--state", st, "--receipt", os.path.join(d, "r.json"))
ok("RED state inside the gap -> check FAIL", rc != 0 and "inside the gap" in out, out); shutil.rmtree(d)
# combo code changed (predicate gone) -> check red
d, fea, st = sandbox(); src = open(f"{fea}/combo_stage.py").read().replace('if int(zz["anchor"]) == A - 14400:', 'if True:')
open(f"{fea}/combo_stage.py", "w").write(src)
rc, out = run("check", "--src", str(S), "--dst", str(T), "--fea", fea, "--state", st, "--receipt", os.path.join(d, "r.json"))
ok("RED combo predicate changed -> check FAIL", rc != 0 and "predicates" in out, out); shutil.rmtree(d)
# a 4h step needs no bridge -> check red
d, fea, st = sandbox()
rc, out = run("check", "--src", str(S), "--dst", str(S), "--fea", fea, "--state", st, "--receipt", os.path.join(d, "r.json"))
ok("RED T == S (nothing missing) -> check FAIL", rc != 0 and "T > S" in out, out); shutil.rmtree(d)
print(f"SELFTEST {'PASS' if all(res) else 'FAIL'} {sum(res)}/{len(res)}")
sys.exit(0 if all(res) else 1)
