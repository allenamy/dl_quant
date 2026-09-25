#!/usr/bin/env python3
"""Standing test for snap_retention.py (DESIGN_snap_retention_2026-09-25 + correction df8c6262b). Synthetic snapshot tree in a temp dir; no
production file is read or written. DL_QUANT_LIVE_ROOT points at an empty temp dir, so a HIGH page can only print PAGE_FAIL (never sends).

  R0 baseline: 20 daily-spaced snapshots (6 per day would be the real cadence; spacing is irrelevant to the rule) — inside the 14-day window
     nothing changes; outside it exactly the large non-kept files go (rolling.npz, a planted 1.2 MB unknown file), aux.json (1.2 MB) and
     every small file stay; each deletion has its line in RETENTION_DELETED.sha256 (sha == the file's former SHA256SUMS line) and in
     RETENTION_TRIMMED.json; exit 0.
  R1 a rolling.npz whose bytes no longer match SHA256SUMS ⇒ nothing in THAT snapshot is deleted, exit 3, PAGE attempted; others still trimmed.
  R2 a large file without a SHA256SUMS line ⇒ refused the same way.
  R3 the resident list is append-only: bytes that were there before a run are still its exact prefix afterwards.
  R4 idempotent: a second run deletes nothing and appends nothing.
  R5 the window is by NAME, not mtime: an old snapshot touched to now is still trimmed; a new snapshot with an ancient mtime is not.
  R6 RED CONTROL: the former rule `find $SNAP -mindepth 1 -maxdepth 1 -type d -mtime +21 -exec rm -rf {} +` on a copy deletes whole
     snapshots INCLUDING aux.json and the small files — the behaviour the user's ruling replaces.
usage: python test_snap_retention.py
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "snap_retention.py")
FAILS, N = [], [0]


def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def make_snap(root, A, big=1_200_000, extra_big=False, sign=True):
    d = os.path.join(root, str(A)); os.makedirs(d)
    files = {"rolling.npz": os.urandom(big), "aux.json": b"{" + b" " * big + b"}", "leg_returns_live.json": b"{}",
             "generation.json": b"{}", "combo_live_status.json": b"{}", "members_hist.npz": os.urandom(2000)}
    if extra_big: files["mystery.bin"] = os.urandom(big)
    for f, b in files.items():
        open(os.path.join(d, f), "wb").write(b)
    if sign:
        with open(os.path.join(d, "SHA256SUMS"), "w") as fh:
            for f in files: fh.write(f"{sha(os.path.join(d, f))}  {f}\n")
    open(os.path.join(d, "COMPLETE"), "w").write("2026-09-25T00:00:00Z\n")
    return d


def run(root):
    env = {"PATH": "/usr/bin:/bin", "HOME": os.path.expanduser("~"), "DL_QUANT_LIVE_ROOT": tempfile.mkdtemp(prefix="no_executor_")}
    r = subprocess.run([sys.executable, "-B", TOOL, root], capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


def main():
    base = tempfile.mkdtemp(prefix="test_snap_retention_")
    t0 = 1790000000 - (1790000000 % 14400)
    root = os.path.join(base, "snap"); os.makedirs(root)
    As = [t0 + i * 86400 for i in range(20)]                 # 20 days; newest = As[-1]; window start = As[-1] - 14 d = As[5]
    for i, A in enumerate(As):
        make_snap(root, A, extra_big=(i == 1))
    open(os.path.join(root, "RETENTION_DELETED.sha256"), "w").write("# resident list\n")
    before_sums = {A: {l.split()[1]: l.split()[0] for l in open(os.path.join(root, str(A), "SHA256SUMS"))} for A in As}
    prefix = open(os.path.join(root, "RETENTION_DELETED.sha256"), "rb").read()
    rc, out = run(root)
    print("R0 baseline")
    cut = As[-1] - 14 * 86400
    outside = [A for A in As if A < cut]; inside = [A for A in As if A >= cut]
    check("R0 exit 0", rc == 0, out[-300:])
    check("R0 inside the window: every file still there", all(os.path.isfile(os.path.join(root, str(A), f)) for A in inside
                                                               for f in ("rolling.npz", "aux.json", "SHA256SUMS", "members_hist.npz")))
    check("R0 outside the window: rolling.npz gone, aux.json + small files kept", all(not os.path.exists(os.path.join(root, str(A), "rolling.npz"))
          and all(os.path.isfile(os.path.join(root, str(A), f)) for f in ("aux.json", "SHA256SUMS", "members_hist.npz", "COMPLETE", "generation.json"))
          for A in outside), outside)
    check("R0 a planted 1.2 MB unknown file outside the window is deleted too (rule by size, not by name)",
          not os.path.exists(os.path.join(root, str(As[1]), "mystery.bin")))
    lines = [l for l in open(os.path.join(root, "RETENTION_DELETED.sha256")).read().splitlines() if not l.startswith("#")]
    exp = {(before_sums[A]["rolling.npz"], f"{A}/rolling.npz") for A in outside} | {(before_sums[As[1]]["mystery.bin"], f"{As[1]}/mystery.bin")}
    got = {(l.split()[0], l.split()[1]) for l in lines}
    check("R0 every deletion has its resident-list line with the SHA256SUMS sha (and nothing else)", got == exp, (len(got), len(exp)))
    tr = [json.load(open(os.path.join(root, str(A), "RETENTION_TRIMMED.json"))) for A in outside]
    check("R0 RETENTION_TRIMMED.json in every trimmed snapshot names its files", all(any(x["file"] == "rolling.npz" for x in t["deleted"]) for t in tr))
    check("R3 the resident list is append-only (the earlier bytes are its exact prefix)", open(os.path.join(root, "RETENTION_DELETED.sha256"), "rb").read().startswith(prefix))
    size1 = os.path.getsize(os.path.join(root, "RETENTION_DELETED.sha256"))
    rc2, out2 = run(root)
    check("R4 idempotent: second run exit 0, nothing deleted, nothing appended", rc2 == 0 and "deleted=0" in out2
          and os.path.getsize(os.path.join(root, "RETENTION_DELETED.sha256")) == size1, out2[-200:])
    print("R1/R2 refusals")
    root2 = os.path.join(base, "snap2"); os.makedirs(root2)
    for A in As: make_snap(root2, A)
    bad1 = os.path.join(root2, str(As[0]), "rolling.npz"); b = bytearray(open(bad1, "rb").read()); b[100] ^= 0xFF; open(bad1, "wb").write(bytes(b))
    d2 = os.path.join(root2, str(As[2])); open(os.path.join(d2, "unsigned.bin"), "wb").write(os.urandom(1_200_000))
    rc, out = run(root2)
    check("R1 exit 3 and a HIGH page attempted (PAGE / PAGE_FAIL printed)", rc == 3 and ("PAGE" in out), out[-300:])
    check("R1 the mismatching snapshot keeps every file", os.path.isfile(bad1) and os.path.isfile(os.path.join(root2, str(As[0]), "aux.json")))
    check("R2 a large file with no SHA256SUMS line ⇒ that snapshot keeps every file", os.path.isfile(os.path.join(d2, "unsigned.bin")) and os.path.isfile(os.path.join(d2, "rolling.npz")))
    check("R1/R2 the other outside snapshots are still trimmed", not os.path.exists(os.path.join(root2, str(As[3]), "rolling.npz")))
    print("R5 window by name")
    root3 = os.path.join(base, "snap3"); os.makedirs(root3)
    for A in As: make_snap(root3, A)
    now = time.time()
    os.utime(os.path.join(root3, str(As[0])), (now, now)); os.utime(os.path.join(root3, str(As[0]), "rolling.npz"), (now, now))
    os.utime(os.path.join(root3, str(As[-2])), (now - 90 * 86400, now - 90 * 86400))
    rc, out = run(root3)
    check("R5 an old snapshot touched to now is still trimmed; a new one with an ancient mtime is not",
          rc == 0 and not os.path.exists(os.path.join(root3, str(As[0]), "rolling.npz")) and os.path.isfile(os.path.join(root3, str(As[-2]), "rolling.npz")), out[-200:])
    print("R6 red control: the former rule")
    root4 = os.path.join(base, "snap4"); os.makedirs(root4)
    for A in As: make_snap(root4, A)
    old = now - 30 * 86400
    for A in As[:3]: os.utime(os.path.join(root4, str(A)), (old, old))
    subprocess.run(["/usr/bin/find", root4, "-maxdepth", "1", "-mindepth", "1", "-type", "d", "-mtime", "+21", "-exec", "rm", "-rf", "{}", "+"], check=False)
    check("R6 RED CONTROL: the former `find -mtime +21 rm -rf` deletes whole snapshots, aux.json and small files included",
          all(not os.path.exists(os.path.join(root4, str(A))) for A in As[:3]))
    shutil.rmtree(base, ignore_errors=True)
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
    print("TEST_SNAP_RETENTION", "PASS" if not FAILS else "FAIL", FAILS if FAILS else "")
    sys.exit(0 if not FAILS else 1)


if __name__ == "__main__":
    main()
