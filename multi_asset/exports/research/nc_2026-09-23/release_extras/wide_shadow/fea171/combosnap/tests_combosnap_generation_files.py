#!/usr/bin/env python3
"""NC release (DESIGN_producer_new_contract §A7 addendum, lead 2026-09-23): the snapshot agent copies exactly the files the producer's
generation.json commits. Runs combo_state_snapshot.sh (ORIGINAL and PATCHED) end to end in throw-away worlds built from one archived
production snapshot (read-only copies); each world has its own feature_cache_identity.py (the production one for the old contract, the
patched tree's one for the new contract) and the real producer venv (symlink). Never touches ~/wide_shadow.
  B0 baseline green: original script, old-format world (3 signed files)                ⇒ rc 0, COMPLETE snapshot, generation check passes
  T1 patched script, old-format world                                                   ⇒ rc 0, snapshot = exactly {3 signed + generation + status}, check passes
  T2 fixture reproduces the defect: original script, new-format world (5 signed files)  ⇒ rc 3, no snapshot
  T3 patched script, new-format world                                                   ⇒ rc 0, snapshot = exactly {5 signed + generation + status}, check passes,
                                                                                          every copied file byte-identical to its source
  T4 / T5 negative: new-format world with members_hist.npz / boundary_raw.npz missing     ⇒ rc != 0, no snapshot dir, no .tmp left behind
  T6 negative: the marker names a path-like file ("../x.npz")                              ⇒ generation_files.py refuses (rc 3); the agent writes no snapshot
  T7 negative: new-format generation, OLD feature_cache_identity (rollback without state downgrade) ⇒ rc 3, no snapshot
usage: python3 tests_combosnap_generation_files.py <original combo_state_snapshot.sh> <patched combo_state_snapshot.sh> <patched fea171 dir> [anchor]"""
import hashlib, json, os, shutil, subprocess, sys, tempfile
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; HERE = os.path.dirname(os.path.abspath(__file__))
FAILS, N = [], [0]
OLD3 = ["aux.json", "leg_returns_live.json", "rolling.npz"]; NEW5 = sorted(OLD3 + ["boundary_raw.npz", "members_hist.npz"])


def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def world(t, A, fci, script, names, drop=None, gen_override=None):
    w = f"{t}/ws"; st = f"{w}/state"; os.makedirs(st); os.makedirs(f"{w}/fea171/combosnap")
    os.symlink(f"{WS}/venv", f"{w}/venv")
    shutil.copy(fci, f"{w}/fea171/feature_cache_identity.py")
    shutil.copy(f"{WS}/fea171/combosnap/check_snapshot_generation.py", f"{w}/fea171/combosnap/")
    shutil.copy(f"{HERE}/generation_files.py", f"{w}/fea171/combosnap/")
    shutil.copy(script, f"{w}/fea171/combo_state_snapshot.sh")
    src = f"{WS}/state/snap/{A}"
    for f in OLD3 + ["combo_live_status.json"]: shutil.copy(f"{src}/{f}", f"{st}/{f}")
    if "boundary_raw.npz" in names:
        np.savez(f"{st}/boundary_raw.npz", ts=np.array([A - 300], np.int64), col=np.array([7], np.int32), raw=np.array([0.1234567], np.float32))
    if "members_hist.npz" in names:
        np.savez(f"{st}/members_hist.npz", anchors=np.array([A], np.int64), off=np.array([0, 3], np.int64), idx=np.array([1, 2, 3], np.int16))
    gen = gen_override or {"schema_version": 1, "anchor_ts": A, "files": {n: {"sha256": sha(f"{st}/{n}")} for n in names}}
    json.dump(gen, open(f"{st}/generation.json", "w"))
    if drop: os.remove(f"{st}/{drop}")
    return w


def run(w):
    r = subprocess.run(["/bin/bash", f"{w}/fea171/combo_state_snapshot.sh"], env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": f"{w}/nohome", "WIDE_SHADOW_HOME": w},
                       capture_output=True, text=True)
    return r


def snapdir(w, A): return f"{w}/state/snap/{A}"


def gencheck(w, A):
    r = subprocess.run([f"{WS}/venv/bin/python", f"{w}/fea171/combosnap/check_snapshot_generation.py", snapdir(w, A), str(A)], capture_output=True, text=True)
    return r.returncode, r.stderr.strip()[-200:]


def main():
    orig, patched, fea_new = sys.argv[1], sys.argv[2], sys.argv[3]
    fci_old = f"{WS}/fea171/feature_cache_identity.py"; fci_new = f"{fea_new}/feature_cache_identity.py"
    snaps = sorted(int(x) for x in os.listdir(f"{WS}/state/snap") if x.isdigit() and os.path.exists(f"{WS}/state/snap/{x}/generation.json"))
    A = int(sys.argv[4]) if len(sys.argv) > 4 else snaps[-1]
    print(f"anchor {A}; fci old {sha(fci_old)[:8]} new {sha(fci_new)[:8]}; original {sha(orig)[:8]} patched {sha(patched)[:8]}")
    with tempfile.TemporaryDirectory() as t:
        w = world(t, A, fci_old, orig, OLD3); r = run(w); d = snapdir(w, A)
        ok = r.returncode == 0 and os.path.exists(f"{d}/COMPLETE")
        check("B0 baseline green: original script, old-format world ⇒ rc 0, COMPLETE snapshot, generation check passes", ok and gencheck(w, A)[0] == 0, (r.returncode, r.stdout[-200:], r.stderr[-200:]))
        if not ok: print("baseline not green; stop"); sys.exit(1)
        base_files = sorted(os.listdir(d))
    with tempfile.TemporaryDirectory() as t:
        w = world(t, A, fci_old, patched, OLD3); r = run(w); d = snapdir(w, A)
        files = sorted(os.listdir(d)) if os.path.isdir(d) else []
        check("T1 patched script, old-format world ⇒ rc 0, same file set as the original script's snapshot, check passes",
              r.returncode == 0 and files == base_files and gencheck(w, A)[0] == 0, (r.returncode, files, r.stderr[-200:]))
    with tempfile.TemporaryDirectory() as t:
        w = world(t, A, fci_new, orig, NEW5); r = run(w)
        check("T2 fixture reproduces the defect: original script, new-format world ⇒ rc 3, no snapshot", r.returncode == 3 and not os.path.exists(snapdir(w, A)),
              (r.returncode, r.stderr.strip().splitlines()[-1:] if r.stderr else ""))
    with tempfile.TemporaryDirectory() as t:
        w = world(t, A, fci_new, patched, NEW5); r = run(w); d = snapdir(w, A)
        files = sorted(os.listdir(d)) if os.path.isdir(d) else []
        want = sorted(NEW5 + ["generation.json", "combo_live_status.json", "SHA256SUMS", "COMPLETE"])
        same = all(sha(f"{d}/{f}") == sha(f"{w}/state/{f}") for f in NEW5 + ["generation.json"]) if files == want else False
        gc = gencheck(w, A) if files else (None, "")
        check("T3 patched script, new-format world ⇒ rc 0, snapshot = 5 signed + generation + status (+SHA256SUMS, COMPLETE), bytes equal, check passes",
              r.returncode == 0 and files == want and same and gc[0] == 0, (r.returncode, files, gc, r.stderr[-200:]))
    for tag, drop in (("T4", "members_hist.npz"), ("T5", "boundary_raw.npz")):
        with tempfile.TemporaryDirectory() as t:
            w = world(t, A, fci_new, patched, NEW5, drop=drop); r = run(w); d = snapdir(w, A)
            check(f"{tag} negative: new-format world with {drop} missing ⇒ rc != 0, no snapshot, no .tmp", r.returncode != 0 and not os.path.exists(d) and not os.path.exists(d + ".tmp"),
                  (r.returncode, r.stderr.strip().splitlines()[-1:] if r.stderr else ""))
    with tempfile.TemporaryDirectory() as t:
        bad = {"schema_version": 1, "anchor_ts": A, "files": {"../x.npz": {"sha256": "0" * 64}, "aux.json": {"sha256": "0" * 64}}}
        w = world(t, A, fci_new, patched, NEW5, gen_override=bad)
        g = subprocess.run([f"{WS}/venv/bin/python", f"{HERE}/generation_files.py", f"{w}/state/generation.json"], capture_output=True, text=True)
        r = run(w)
        check("T6 negative: marker names '../x.npz' ⇒ generation_files.py rc 3 (REFUSED), agent writes no snapshot",
              g.returncode == 3 and "REFUSED" in g.stderr and r.returncode != 0 and not os.path.exists(snapdir(w, A)), (g.returncode, g.stderr.strip()[:160], r.returncode))
    with tempfile.TemporaryDirectory() as t:
        w = world(t, A, fci_old, patched, NEW5); r = run(w)
        check("T7 negative: new-format generation with the OLD feature_cache_identity ⇒ rc 3, no snapshot", r.returncode == 3 and not os.path.exists(snapdir(w, A)),
              (r.returncode, r.stderr.strip().splitlines()[-1:] if r.stderr else ""))
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
    if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    main()
