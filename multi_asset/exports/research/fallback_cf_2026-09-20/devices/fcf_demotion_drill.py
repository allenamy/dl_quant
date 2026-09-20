#!/usr/bin/env python3
"""fcf_demotion_drill.py — EXERCISE the demotion path instead of asserting it is easy (lead's closing request).

THE CLAIM BEING TESTED: "if the reviewer rules A1 binds, pulling F4b' is ONE LINE and no other number moves."
A claim that a change is cheap is itself a claim, and the cheap way to believe it is to never try it. So this device actually
rebuilds the tables with the arm removed and compares, rather than reasoning about independence.

WHAT IT DOES:
  1. rebuilds the main tables from the PRIMARY frozen config only (no F4b' extra config) -> a genuine "F4b' pulled" artefact;
  2. compares it against the shipped tables cell by cell, over EVERY arm except F4b' and EVERY cell except the two that exist only
     to describe F4b';
  3. REFUSES unless every one of those numbers is BITWISE unchanged. If anything moves, "one line" is false and the doc needs a
     rewrite, not an edit.
  4. re-runs the doc check in --without-arm F4bp mode so we know the remaining prose still verifies with the arm gone.
Comparison is on the JSON-serialised value, so a change of type or of precision counts as a change.

usage: fcf_demotion_drill.py <out.json>
"""
import hashlib, json, os, subprocess, sys, time

OUT = "/workspace/fallback_cf_2026-09-20"
PY = "/workspace/venv/bin/python"
SHIPPED = f"{OUT}/receipts/FCF_TABLES.json"
DRILL = f"{OUT}/work/FCF_TABLES_without_F4bp.json"
ARM = "F4bp"
F4BP_ONLY_CELLS = set()          # cells that exist only because of F4b' — none; the arm adds rows, not cells


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def walk(o, pre=""):
    """flatten to {json-path: scalar}"""
    if isinstance(o, dict):
        for k, v in o.items(): yield from walk(v, f"{pre}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from walk(v, f"{pre}[{i}]")
    else:
        yield pre, o


def main():
    OUTP = sys.argv[1]
    rec = {"device": "fcf_demotion_drill.py", "self_sha256": sha(os.path.abspath(__file__)),
           "claim_under_test": "pulling F4b' is a one-line change and no other number moves",
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": []}
    FAILS = []

    def step(n, ok, d=None):
        rec["steps"].append(dict(step=n, ok=bool(ok), detail=d))
        print(("PASS " if ok else "FAIL ") + n, json.dumps(d, default=str)[:260] if d is not None else "", flush=True)
        if not ok: FAILS.append(n)

    # 1 · rebuild with the arm pulled
    r = subprocess.run([PY, "-B", f"{OUT}/devices/fcf_tables.py",
                        f"{OUT}/RUN_CONFIG_fallback_cf_F_2026-09-20.json", DRILL],
                       capture_output=True, text=True, cwd=OUT)
    step("1.rebuild_tables_with_the_arm_pulled", r.returncode == 0, dict(returncode=r.returncode, tail=r.stdout.strip().splitlines()[-1:] or r.stderr[-200:]))
    if FAILS:
        json.dump(dict(rec, VERDICT="REFUSED", failed=FAILS), open(OUTP, "w"), indent=1); sys.exit(3)

    A = json.load(open(SHIPPED)); B = json.load(open(DRILL))
    step("2.the_pulled_build_really_has_no_F4bp", ARM not in B.get("arms", {}) and ARM not in B.get("paired_vs_F0", {}),
         dict(arms_in_pulled=sorted(B.get("arms", {})), arms_in_shipped=sorted(A.get("arms", {}))))

    # 3 · every number that is not about F4b' must be bitwise unchanged
    def strip(doc):
        d = json.loads(json.dumps(doc))
        d.get("arms", {}).pop(ARM, None); d.get("paired_vs_F0", {}).pop(ARM, None)
        # keys that exist ONLY to describe this arm are removals, not moves. The drill originally missed the §5 block and
        # correctly reported a difference — that is the drill working, so the fix is here rather than in the tolerance.
        for k in [k for k in d.get("prereg_s5_falsification", {}) if ARM in k]:
            d["prereg_s5_falsification"].pop(k)
        for k in ("utc", "self_sha256", "run_config", "bt_tables_sha256"): d.pop(k, None)
        for a in d.get("arms", {}).values(): a.pop("path_npz_sha256", None)
        return d
    fa = dict(walk(strip(A))); fb = dict(walk(strip(B)))
    only_a = sorted(set(fa) - set(fb)); only_b = sorted(set(fb) - set(fa))
    moved = sorted(k for k in set(fa) & set(fb) if json.dumps(fa[k], sort_keys=True) != json.dumps(fb[k], sort_keys=True))
    step("3.no_other_number_moves_when_the_arm_is_pulled", not moved and not only_a and not only_b,
         dict(n_compared=len(set(fa) & set(fb)), n_moved=len(moved), moved=moved[:8],
              only_in_shipped=only_a[:8], only_in_pulled=only_b[:8]))

    # 4 · the doc check still verifies with the arm excluded
    r2 = subprocess.run([PY, "-B", f"{OUT}/devices/fcf_doc_check.py", "--without-arm", ARM],
                        capture_output=True, text=True, cwd=OUT)
    last = (r2.stdout.strip().splitlines() or [""])[-1]
    # A "passes with the arm excluded" step is worthless if nothing was actually excluded — that is how this step read the first
    # time I ran it (checked=284 either way, because the --without-arm flag had silently not been wired). So the number skipped
    # is asserted to be NON-ZERO and to be strictly fewer checks than the full run.
    import re as _re
    m_sk = _re.search(r"skipped\(--without-arm [^)]*\): (\d+)", last)
    m_ck = _re.search(r"checked=(\d+)", last)
    r3 = subprocess.run([PY, "-B", f"{OUT}/devices/fcf_doc_check.py"], capture_output=True, text=True, cwd=OUT)
    full = (r3.stdout.strip().splitlines() or [""])[-1]
    m_full = _re.search(r"checked=(\d+)", full)
    n_sk = int(m_sk.group(1)) if m_sk else 0
    n_ck = int(m_ck.group(1)) if m_ck else -1
    n_full = int(m_full.group(1)) if m_full else -2
    step("4.doc_check_passes_with_the_arm_ACTUALLY_excluded",
         r2.returncode == 0 and "VERDICT=PASS" in last and n_sk > 0 and n_ck == n_full - n_sk,
         dict(returncode=r2.returncode, verdict_line=last, full_verdict_line=full,
              n_skipped=n_sk, n_checked_without_arm=n_ck, n_checked_full=n_full,
              balance="checked_without_arm + skipped == checked_full",
              why="a skip of 0 would make this step a second run of the full check, i.e. a vacuous green"))

    rec["VERDICT"] = "PASS" if not FAILS else "REFUSED"; rec["failed"] = FAILS
    rec["conclusion"] = ("the demotion is genuinely a one-line change: rebuilding without the arm leaves every other number bitwise "
                         "identical and the remaining prose still verifies" if not FAILS else
                         "the demotion is NOT a one-line change; the doc would need a rewrite")
    json.dump(rec, open(OUTP + ".tmp", "w"), indent=1); os.replace(OUTP + ".tmp", OUTP)
    print(f"FCF_DEMOTION_DRILL VERDICT={rec['VERDICT']} steps={len(rec['steps'])} failed={len(FAILS)} receipt_sha256={sha(OUTP)}", flush=True)
    sys.exit(0 if not FAILS else 3)


if __name__ == "__main__":
    main()
