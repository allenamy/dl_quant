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


def run(nc, w2, out, phase, extra=()):
    r = subprocess.run([sys.executable, DEV, nc, w2, out, "--phase", phase, *extra], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else ""


def cell(tag, ok, want, got):
    R.append({"cell": tag, "verdict": "PASS" if ok else "FAIL", "expected": want, "observed": got})
    print(f"  {tag:18s} {'PASS' if ok else 'FAIL':5s} expected={want}  observed={got}", flush=True)
    return ok


def fixtures(nc, build_done=True):
    for rel, body in (("work/NC_FEATURES.npz", b"FEATURES-FIXTURE"), ("work/members_hist_all.npz", b"MH-FIXTURE"),
                      ("inputs/bundle_config.json", b'{"params":{}}'), ("work/legs.npz", b"LEGS-FIXTURE")):
        os.makedirs(os.path.dirname(f"{nc}/{rel}"), exist_ok=True)
        open(f"{nc}/{rel}", "wb").write(body)
    os.makedirs(f"{nc}/receipts", exist_ok=True)
    json.dump({"sha256": sha(f"{nc}/work/NC_FEATURES.npz")}, open(f"{nc}/receipts/NC_FEATURES.json", "w"))
    json.dump({"sha256": sha(f"{nc}/work/legs.npz")}, open(f"{nc}/receipts/NC_LEGS.json", "w"))
    os.makedirs(f"{nc}/logs", exist_ok=True)
    open(f"{nc}/logs/nc_build.log", "w").write("START p2\nDONE p2\n" + ("BUILD_DONE\n" if build_done else ""))


def main():
    work, out_path = sys.argv[1], sys.argv[2]
    work = os.path.abspath(work)
    t0 = time.time()

    # RED.order and RED.missing first, on an EMPTY nc root and an empty news2 root
    nc = f"{work}/nc_empty"; w2 = f"{work}/w2_empty"
    shutil.rmtree(nc, ignore_errors=True); shutil.rmtree(w2, ignore_errors=True)
    os.makedirs(nc); os.makedirs(w2)
    # the build FINISHED but produced nothing here: these two cells are about order and absence, so
    # the build-completion guard must not be what fires
    os.makedirs(f"{nc}/logs", exist_ok=True); open(f"{nc}/logs/nc_build.log", "w").write("BUILD_DONE\n")
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

    # RED.unfinished_build: every file present and its receipt binding it, but the producing build has
    # not written BUILD_DONE -- the live 2026-09-23 shape after merge2 OOM'd and was restarted.
    nc3 = f"{work}/nc_unfinished"; w23 = f"{work}/w2_unfinished"
    shutil.rmtree(nc3, ignore_errors=True); shutil.rmtree(w23, ignore_errors=True)
    os.makedirs(nc3); os.makedirs(w23)
    fixtures(nc3, build_done=False)
    rc, line = run(nc3, w23, f"{work}/o_unfin.json", "pre_king")
    left3 = [f for _, _, files in os.walk(w23) for f in files]
    cell("RED.unfinished_build", rc == 5 and not left3, "rc 5 and nothing staged",
         f"rc={rc} files_left={left3}")
    rc, line = run(nc3, w23, f"{work}/o_unfin_ovr.json", "pre_king", ("--allow-incomplete-build",))
    cell("GREEN.override_named", rc == 0 and "VERDICT=STAGED" in line,
         "rc 0 with the override, recorded as such", f"rc={rc} {line[:70]}")

    # RED.partial: one required source missing -> refuses AND stages nothing. The old code linked
    # what it found before refusing; on 2026-09-23 that would have hard-linked a 3 GB NC_FEATURES.npz
    # that merge2 was still writing.
    nc2 = f"{work}/nc_partial"; w22 = f"{work}/w2_partial"
    shutil.rmtree(nc2, ignore_errors=True); shutil.rmtree(w22, ignore_errors=True)
    os.makedirs(nc2); os.makedirs(w22)
    fixtures(nc2)
    os.remove(f"{nc2}/receipts/NC_FEATURES.json")          # the live shape: payload present, receipt not yet
    rc, line = run(nc2, w22, f"{work}/o_partial.json", "pre_king")
    left = [f for _, _, files in os.walk(w22) for f in files]
    cell("RED.partial", rc == 2 and not left, "rc 2 and nothing staged",
         f"rc={rc} files_left={left}")

    # RED.binding: change the file after its receipt was written
    open(f"{nc}/work/legs.npz", "wb").write(b"TAMPERED")
    rc, line = run(nc, w2, f"{work}/o_bind.json", "post_king")
    cell("RED.binding", rc == 3 and "does not bind" in line, "rc 3, refuses the unbound file", f"rc={rc} {line[:90]}")

    # ★ GREEN.in_place: the source root IS the news2 root, so source and destination are one inode.
    # The first version did `os.remove(dest)` then `os.link(source, dest)` -- one unlink on one inode,
    # i.e. it DELETED the artifact and then failed to link a path that no longer existed. This cell
    # asserts the artifact SURVIVES with unchanged bytes, not merely that the verdict string is right:
    # a verdict-only assertion would have passed on the broken code right up to the missing file.
    one = f"{work}/one_root"
    shutil.rmtree(one, ignore_errors=True); os.makedirs(one)
    fixtures(one)
    rc, line = run(one, one, f"{work}/o_pre_one.json", "pre_king")
    pre_ok = rc == 0 and "VERDICT=STAGED" in line
    legs_before = sha(f"{one}/work/legs.npz")
    rc, line = run(one, one, f"{work}/o_in_place.json", "post_king")
    survived = os.path.exists(f"{one}/work/legs.npz") and sha(f"{one}/work/legs.npz") == legs_before
    how = json.load(open(f"{work}/o_in_place.json")).get("staged", {}).get("work/legs.npz", {}).get("how") \
        if os.path.exists(f"{work}/o_in_place.json") else None
    cell("GREEN.in_place", pre_ok and rc == 0 and "VERDICT=STAGED" in line and survived and how == "in_place",
         f"rc 0, STAGED, how=in_place, legs.npz still sha {legs_before[:12]}",
         f"rc={rc} how={how} survived={survived} sha_now="
         f"{(sha(f'{one}/work/legs.npz')[:12] if os.path.exists(f'{one}/work/legs.npz') else 'FILE GONE')}")

    # GREEN.alt_receipt: the legs receipt under the name nc_legs.py actually writes when it is invoked
    # with explicit output paths (work/NC_LEGS_RECEIPT.json), the tabled name absent. The chosen
    # candidate must be recorded, otherwise the receipt cannot say which file it verified.
    alt = f"{work}/alt_root"; w2a = f"{work}/w2_alt"
    shutil.rmtree(alt, ignore_errors=True); shutil.rmtree(w2a, ignore_errors=True)
    os.makedirs(alt); os.makedirs(w2a)
    fixtures(alt)
    os.rename(f"{alt}/receipts/NC_LEGS.json", f"{alt}/work/NC_LEGS_RECEIPT.json")
    run(alt, w2a, f"{work}/o_pre_alt.json", "pre_king")
    rc, line = run(alt, w2a, f"{work}/o_alt.json", "post_king")
    chosen = json.load(open(f"{work}/o_alt.json")).get("staged", {}).get("receipts/P3_LEGS.json", {}).get("source") \
        if os.path.exists(f"{work}/o_alt.json") else None
    cell("GREEN.alt_receipt", rc == 0 and "VERDICT=STAGED" in line and chosen and chosen.endswith("work/NC_LEGS_RECEIPT.json"),
         "rc 0, STAGED, receipt resolved to the alternate name and recorded",
         f"rc={rc} chosen={chosen}")

    # ★ RED.producer_running: post_king's completion evidence is "no nc_legs.py process is alive".
    # Spawn a REAL process whose command line matches, and require the refusal. Note the baseline: the
    # three post_king GREEN cells above ran through this same guard and passed, so a green here is not
    # an artefact of the guard never firing -- it is the same guard, with the condition flipped.
    prod = f"{work}/fake_producer"
    shutil.rmtree(prod, ignore_errors=True); os.makedirs(prod)
    os.makedirs(f"{prod}/root"); fixtures(f"{prod}/root")
    run(f"{prod}/root", f"{prod}/w2", f"{work}/o_pre_prod.json", "pre_king")
    open(f"{prod}/nc_legs.py", "w").write("import time; time.sleep(120)\n")
    proc = subprocess.Popen([sys.executable, f"{prod}/nc_legs.py"])
    try:
        time.sleep(1.0)  # let it appear in the process table
        legs_before = sha(f"{prod}/root/work/legs.npz")
        rc, line = run(f"{prod}/root", f"{prod}/w2", f"{work}/o_prod.json", "post_king")
        staged_now = os.path.exists(f"{prod}/w2/receipts/P3_LEGS.json")
        matches = json.load(open(f"{work}/o_prod.json")).get("completion_check", {}).get("n_matches") \
            if os.path.exists(f"{work}/o_prod.json") else None
        intact = sha(f"{prod}/root/work/legs.npz") == legs_before
        cell("RED.producer_running",
             rc == 5 and "has not finished" in line and not staged_now and (matches or 0) >= 1 and intact,
             "rc 5, names the live producer, nothing staged, source intact",
             f"rc={rc} n_matches={matches} staged={staged_now} source_intact={intact}")
    finally:
        proc.kill(); proc.wait()  # killed by the PID THIS device started; never by name

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
