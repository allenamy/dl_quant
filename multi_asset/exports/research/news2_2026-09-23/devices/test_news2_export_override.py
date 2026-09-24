"""Red/green cells for the user-override gate in news2_export_models.py (lead, 2026-09-24).

The frozen verdict is NO_DEPLOY and the user released s42 on top of it
(docs/RULING_user_NC_s42_override_2026-09-24.md). The gate that implements that permission is the only
thing standing between "a deliberate exception" and "an exporter that ignores its own verdict", so it
gets the same treatment as any other gate here: baseline green FIRST, then the refusals.

  GREEN.correct        the override named, its sha verified, seed s42  -> exports, files written
  RED.no_override      no --user-override / --user-override-sha        -> refuse, NOTHING written
  RED.wrong_sha        override sha does not match the file            -> refuse, NOTHING written
  RED.wrong_seed       seed s2027 under the same override              -> refuse, NOTHING written

"NOTHING written" is asserted by counting files in the output dir afterwards, not by reading the exit
code: a refusal whose side effects already happened is not a refusal.

The green cell writes into a TEMP output dir so the real deploy artefacts are produced by a separate,
clean formal run -- a test that doubles as the deliverable cannot be re-run without disturbing it.

usage: python test_news2_export_override.py <ruling_path> <ruling_sha> <work_dir> <out.json>
"""
import hashlib, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.path.join(HERE, "news2_export_models.py")
PV = "/workspace/venv/bin/python"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def main():
    ruling, ruling_sha, work, out_path = sys.argv[1:5]
    work = os.path.abspath(work)
    cells, t0 = [], time.time()

    def cell(tag, ok, want, got):
        cells.append({"cell": tag, "verdict": "PASS" if ok else "FAIL", "expected": want, "observed": got})
        print(f"  {tag:20s} {'PASS' if ok else 'FAIL':5s} expected={want}  observed={got}", flush=True)

    def run(tag, extra):
        d = os.path.join(work, tag)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        cmd = [PV, "-B", DEV, "--out-dir", d, "--manifest", os.path.join(d, "MANIFEST.json")] + extra
        r = subprocess.run(cmd, capture_output=True, text=True)
        left = sorted(f for f in os.listdir(d) if f != "MANIFEST.json")
        first = (r.stdout + r.stderr).strip().splitlines()
        return r.returncode, (first[-1] if first else ""), left, d

    # ---- BASELINE GREEN FIRST. A refusal check whose green case cannot export proves nothing: it would
    #      "catch" all three mutations because the exporter is broken, not because the gate works.
    rc, line, left, d = run("green_correct", ["--seed", "s42", "--user-override", ruling,
                                              "--user-override-sha", ruling_sha])
    man = {}
    if os.path.exists(os.path.join(d, "MANIFEST.json")):
        man = json.load(open(os.path.join(d, "MANIFEST.json")))
    ok = (rc == 0 and "slow2026.txt" in left and "f10_live_s42_np.npz" in left
          and man.get("VERDICT") == "NO_DEPLOY" and man.get("USER_OVERRIDE") == ruling_sha
          and man.get("seed") == "s42" and len(man.get("exported_files", [])) == 2)
    cell("GREEN.correct", ok,
         "rc 0, both files written, manifest VERDICT=NO_DEPLOY + USER_OVERRIDE + seed=s42 + 2 exported_files",
         f"rc={rc} files={left} VERDICT={man.get('VERDICT')} OVERRIDE={str(man.get('USER_OVERRIDE'))[:12]} "
         f"seed={man.get('seed')} n_exported={len(man.get('exported_files', []))}")

    rc, line, left, _ = run("red_no_override", ["--seed", "s42"])
    cell("RED.no_override", rc == 3 and not left and "both required" in line,
         "rc 3, nothing written, reason names both flags", f"rc={rc} files={left} {line[:80]}")

    rc, line, left, _ = run("red_wrong_sha", ["--seed", "s42", "--user-override", ruling,
                                              "--user-override-sha", "0" * 64])
    cell("RED.wrong_sha", rc == 3 and not left and "sha mismatch" in line,
         "rc 3, nothing written, reason names the mismatch", f"rc={rc} files={left} {line[:80]}")

    rc, line, left, _ = run("red_wrong_seed", ["--seed", "s2027", "--user-override", ruling,
                                               "--user-override-sha", ruling_sha])
    cell("RED.wrong_seed", rc == 3 and not left and "s42 only" in line,
         "rc 3, nothing written, reason says the override covers s42 only",
         f"rc={rc} files={left} {line[:80]}")

    bad = [c for c in cells if c["verdict"] != "PASS"]
    rec = {"device": "test_news2_export_override.py", "self_sha256": sha(os.path.abspath(__file__)),
           "subject": DEV, "subject_sha256": sha(DEV),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "ruling": {"path": ruling, "sha256_declared": ruling_sha, "sha256_measured": sha(ruling),
                      "matches": sha(ruling) == ruling_sha},
           "why": ("the exporter must refuse to write under a non-DEPLOY verdict unless the user override "
                   "is named, hashed and limited to s42. Baseline green runs first, because three refusals "
                   "on a broken exporter would look identical to three working refusals."),
           "cells": cells, "n_cells": len(cells), "n_not_pass": len(bad),
           "VERDICT": "PASS" if not bad else "FAIL", "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"EXPORT_OVERRIDE_TEST VERDICT={rec['VERDICT']} cells={len(cells)} not_pass={len(bad)} "
          f"receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
