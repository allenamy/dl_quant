#!/usr/bin/env python3
"""Sandbox test of members_hist_backfill.py on a COPY of the 08Z snapshot state (production only read).
Fixture: state/snap/1790409600 copied; the 04Z entry (1790395200) deleted from members_hist and generation.json re-signed — the ground
truth of the deleted entry is kept aside. Controls default to the device's rule (two most recent recorded anchors: 00Z, 08Z).
  P1 check PASS   P2 apply PASS and the appended 04Z == the deleted ground truth BITWISE   P3 verify PASS   P4 rollback PASS, bytes restored
  R1 target already present => FAIL (C4)          R2a axis: symbols_panel truncated => FAIL (C3)   R2b target not a rolling row => FAIL (C4)
  R3 member count wrong (NTOP 100 in a bundle copy) => FAIL (C6)   R4 recorded control entry altered => FAIL (C5)
  R5 producer label running (com.hsy.combolive) => FAIL (C1)       R6 rollback after the file changed since => FAIL
usage: ~/wide_shadow/venv/bin/python test_members_hist_backfill.py <work dir>"""
import hashlib, io, json, os, shutil, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); HOME = os.path.expanduser("~"); DEV = f"{HERE}/members_hist_backfill.py"
SNAP = f"{HOME}/wide_shadow/state/snap/1790409600"; T04, C00, C08 = 1790395200, 1790380800, 1790409600
FAILS, N = [], [0]
def check(name, ok, detail=""):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (f"  — {str(detail)[:300]}" if detail else ""), flush=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
def run(state, cmd, targets, receipt, extra=()):
    r = subprocess.run([sys.executable, "-B", DEV, cmd, "--targets", ",".join(map(str, targets)), "--receipt", receipt, "--state", state,
                        "--producer-label", "com.hsy.not_a_label_for_test"] + list(extra), capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr
def fixture(work, tag):
    st = f"{work}/{tag}/state"; os.makedirs(st)
    for f in ("rolling.npz", "aux.json", "leg_returns_live.json", "boundary_raw.npz", "members_hist.npz", "generation.json"):
        shutil.copy2(f"{SNAP}/{f}", f"{st}/{f}")
    with np.load(f"{st}/members_hist.npz") as m: an, off, idx = m["anchors"], m["off"], m["idx"]
    k = int(np.where(an == T04)[0][0]); truth = idx[off[k]:off[k + 1]].copy()
    keep = [j for j in range(len(an)) if j != k]
    b = io.BytesIO(); np.savez(b, anchors=an[keep], off=np.concatenate([[0], np.cumsum([off[j + 1] - off[j] for j in keep])]).astype(off.dtype),
                              idx=np.concatenate([idx[off[j]:off[j + 1]] for j in keep]).astype(idx.dtype))
    open(f"{st}/members_hist.npz", "wb").write(b.getvalue())
    g = json.load(open(f"{st}/generation.json")); g["files"]["members_hist.npz"]["sha256"] = sha(f"{st}/members_hist.npz")
    open(f"{st}/generation.json", "w").write(json.dumps(g))
    return st, truth
def main():
    work = os.path.abspath(sys.argv[1]); assert not os.path.exists(work); os.makedirs(work)
    st, truth = fixture(work, "f1"); rec = f"{work}/f1/RECEIPT.json"
    pre = {f: sha(f"{st}/{f}") for f in ("members_hist.npz", "generation.json")}
    rc, out = run(st, "check", [T04], rec); check("P1 check PASS on the fixture", rc == 0 and "CHECK PASS" in out, out[-300:])
    rc, out = run(st, "apply", [T04], rec); check("P2 apply PASS", rc == 0 and "APPLY PASS" in out, out[-300:])
    with np.load(f"{st}/members_hist.npz") as m: an, off, idx = m["anchors"], m["off"], m["idx"]
    k = int(np.where(an == T04)[0][0]) if T04 in an else None
    check("P2 appended 04Z == the deleted ground truth, bitwise", k is not None and np.array_equal(idx[off[k]:off[k + 1]], truth) and idx.dtype == truth.dtype,
          f"n {len(truth)}")
    rc, out = run(st, "verify", [T04], rec); check("P3 verify PASS", rc == 0 and "VERIFY PASS" in out, out[-300:])
    rc, out = run(st, "check", [C00], f"{work}/r1.json"); check("R1 target already present => FAIL C4", rc == 1 and "already in members_hist" in out, out[-200:])
    rc, out = run(st, "rollback", [T04], rec); check("P4 rollback PASS", rc == 0 and "ROLLBACK PASS" in out, out[-200:])
    check("P4 bytes restored", all(sha(f"{st}/{f}") == s for f, s in pre.items()))
    st2, _ = fixture(work, "f2")
    bun = f"{work}/bundle_short"; shutil.copytree(f"{HOME}/wide_shadow/shadow_bundle", bun, ignore=shutil.ignore_patterns("*.npz", "*.npy", "*.txt", "*tar*"))
    c = json.load(open(f"{bun}/config.json")); c["symbols_panel"] = c["symbols_panel"][:-1]; json.dump(c, open(f"{bun}/config.json", "w"))
    rc, out = run(st2, "check", [T04], f"{work}/r2.json", ["--bundle", bun]); check("R2a axis misaligned => FAIL C3", rc == 1 and "C3 axis" in out, out[-200:])
    rc, out = run(st2, "check", [1780012800], f"{work}/r2b.json"); check("R2b target not a rolling row => FAIL C4", rc == 1 and "not a row" in out, out[-200:])
    bun3 = f"{work}/bundle_ntop"; shutil.copytree(f"{HOME}/wide_shadow/shadow_bundle", bun3, ignore=shutil.ignore_patterns("*.npz", "*.npy", "*.txt", "*tar*"))
    c = json.load(open(f"{bun3}/config.json")); c["params"]["NTOP"] = 100; json.dump(c, open(f"{bun3}/config.json", "w"))
    rc, out = run(st2, "check", [T04], f"{work}/r3.json", ["--bundle", bun3]); check("R3 member count wrong => FAIL C6", rc == 1 and "C6 member count" in out, out[-300:])
    st4, _ = fixture(work, "f4")
    with np.load(f"{st4}/members_hist.npz") as m: an, off, idx = m["anchors"], m["off"].copy(), m["idx"].copy()
    k = int(np.where(an == C08)[0][0]); idx[off[k]] = idx[off[k] + 1]          # alter the recorded 08Z control entry by one element
    b = io.BytesIO(); np.savez(b, anchors=an, off=off, idx=idx); open(f"{st4}/members_hist.npz", "wb").write(b.getvalue())
    g = json.load(open(f"{st4}/generation.json")); g["files"]["members_hist.npz"]["sha256"] = sha(f"{st4}/members_hist.npz"); open(f"{st4}/generation.json", "w").write(json.dumps(g))
    rc, out = run(st4, "check", [T04], f"{work}/r4.json"); check("R4 positive control altered => FAIL C5", rc == 1 and "POSITIVE CONTROL FAILED" in out, out[-300:])
    r = subprocess.run([sys.executable, "-B", DEV, "check", "--targets", str(T04), "--receipt", f"{work}/r5.json", "--state", st2, "--producer-label", "com.hsy.combolive"],
                       capture_output=True, text=True)
    check("R5 producer label running => FAIL C1", r.returncode == 1 and "C1 producer" in r.stdout, r.stdout[-200:])
    st6, _ = fixture(work, "f6"); rec6 = f"{work}/f6/RECEIPT.json"
    rc, out = run(st6, "apply", [T04], rec6)
    open(f"{st6}/generation.json", "a").write(" ")
    rc, out = run(st6, "rollback", [T04], rec6); check("R6 rollback after the file changed => FAIL", rc == 1 and "changed since" in out, out[-200:])
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed"); print("TEST_MEMBERS_HIST_BACKFILL", "PASS" if not FAILS else "FAIL", FAILS or "")
    return 0 if not FAILS else 1
if __name__ == "__main__":
    sys.exit(main())
