"""Red/green test for news2_stage_inputs.py, including the ordering defect the integrator found.

Four cells, green first. A refusal-only suite would prove the device can say no, not that it can
stage; a staging-only suite would prove it can copy, not that it guards. Both halves are here.

  GREEN.pre_king        with fixtures present, stages 4 files and binds the feature receipt
  GREEN.post_king       after pre_king, stages legs and binds its receipt
  RED.order             post_king BEFORE pre_king -> refused (this is the defect: legs need the King
                        OOF, which this chain produces, so they cannot be a pre-chain input)
  RED.missing           pre_king with nothing present -> refused, naming every absent source
  RED.binding           legs rewritten after its receipt was written -> refused

usage: python test_news2_stage_inputs.py <work> <out.json>
"""
import hashlib, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.path.join(HERE, "news2_stage_inputs.py")
R = []


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def run(nc, w2, out, phase):
    r = subprocess.run([sys.executable, DEV, nc, w2, out, "--phase", phase], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else ""


def cell(tag, ok, want, got):
    R.append({"cell": tag, "verdict": "PASS" if ok else "FAIL", "expected": want, "observed": got})
    print(f"  {tag:18s} {'PASS' if ok else 'FAIL':5s} expected={want}  observed={got}", flush=True)
    return ok


def fixtures(nc):
    for rel, body in (("work/NC_FEATURES.npz", b"FEATURES-FIXTURE"), ("work/members_hist_all.npz", b"MH-FIXTURE"),
                      ("inputs/bundle_config.json", b'{"params":{}}'), ("work/legs.npz", b"LEGS-FIXTURE")):
        os.makedirs(os.path.dirname(f"{nc}/{rel}"), exist_ok=True)
        open(f"{nc}/{rel}", "wb").write(body)
    os.makedirs(f"{nc}/receipts", exist_ok=True)
    json.dump({"sha256": sha(f"{nc}/work/NC_FEATURES.npz")}, open(f"{nc}/receipts/NC_FEATURES.json", "w"))
    json.dump({"sha256": sha(f"{nc}/work/legs.npz")}, open(f"{nc}/receipts/NC_LEGS.json", "w"))


def main():
    work, out_path = sys.argv[1], sys.argv[2]
    work = os.path.abspath(work)
    t0 = time.time()

    # RED.order and RED.missing first, on an EMPTY nc root and an empty news2 root
    nc = f"{work}/nc_empty"; w2 = f"{work}/w2_empty"
    shutil.rmtree(nc, ignore_errors=True); shutil.rmtree(w2, ignore_errors=True)
    os.makedirs(nc); os.makedirs(w2)
    rc, line = run(nc, w2, f"{work}/o_order.json", "post_king")
    cell("RED.order", rc == 4 and "pre_king has not been staged" in line, "rc 4, refuses out of order", f"rc={rc} {line[:90]}")
    rc, line = run(nc, w2, f"{work}/o_missing.json", "pre_king")
    cell("RED.missing", rc == 2 and "required inputs missing" in line, "rc 2, names the absent sources", f"rc={rc} {line[:90]}")

    # GREEN both phases
    nc = f"{work}/nc_full"; w2 = f"{work}/w2_full"
    shutil.rmtree(nc, ignore_errors=True); shutil.rmtree(w2, ignore_errors=True)
    os.makedirs(nc); os.makedirs(w2)
    fixtures(nc)
    rc, line = run(nc, w2, f"{work}/o_pre.json", "pre_king")
    ok_pre = rc == 0 and "VERDICT=STAGED" in line and "bindings_ok=1/1" in line
    cell("GREEN.pre_king", ok_pre, "rc 0, STAGED, bindings_ok=1/1", f"rc={rc} {line[:90]}")
    rc, line = run(nc, w2, f"{work}/o_post.json", "post_king")
    cell("GREEN.post_king", rc == 0 and "VERDICT=STAGED" in line, "rc 0, STAGED", f"rc={rc} {line[:90]}")

    # RED.binding: change the file after its receipt was written
    open(f"{nc}/work/legs.npz", "wb").write(b"TAMPERED")
    rc, line = run(nc, w2, f"{work}/o_bind.json", "post_king")
    cell("RED.binding", rc == 3 and "does not bind" in line, "rc 3, refuses the unbound file", f"rc={rc} {line[:90]}")

    bad = [x for x in R if x["verdict"] != "PASS"]
    rec = {"device": "test_news2_stage_inputs.py", "self_sha256": sha(os.path.abspath(__file__)),
           "subject_sha256": sha(DEV), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "defect_this_covers": ("the first version of news2_stage_inputs.py listed legs.npz as a pre-chain "
                                  "input; legs consume the King OOF, which this chain produces, so the chain "
                                  "was unstartable. Found by the integrator 2026-09-23."),
           "cells": R, "n_cells": len(R), "n_not_pass": len(bad),
           "VERDICT": "PASS" if not bad else "FAIL", "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_STAGE_TEST VERDICT={rec['VERDICT']} cells={rec['n_cells']} not_pass={rec['n_not_pass']} "
          f"receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
