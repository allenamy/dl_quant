#!/usr/bin/env python3
"""d10_nonstandard_spacing_redcontrol.py -- lead's required red control for the NONSTANDARD_SPACING change.

lead's ruling 2026-09-25: "改 `common/funding_interval.py` 时带红控制(旧代码对 3h 行抛 IntervalError,
新代码给标签且其余行逐位不变)."

INSTRUMENT CHOICE. The claim is about CODE BEHAVIOUR, not about a data sample, so this device does not
sample real rows: it ENUMERATES the resolver's whole decision space (the cross product of the fields
`resolve` reads, including off-grid values, plus the row=None case, times both `allow_spacing` values)
and compares OLD against NEW on every point. "All other rows bitwise unchanged" is then a complete
statement over the decision space rather than a statement about whichever rows happened to be sampled.

OLD is read from git, not reconstructed: a reimplementation of the old behaviour would be the defect
family "「用冻结的 X 口径」只有在 import X 并调用它时才成立".

TWO-SIDED, so it cannot pass vacuously:
  * TARGETED cases (OLD raised "not in the allowed set" from an EXACT_BY_SPACING resolution) must number
    > 0 -- a control that cannot fire proves nothing -- and NEW must label every one of them
    NONSTANDARD_SPACING, with `resolve` not raising and `gate_interval` still refusing.
  * EVERY OTHER case must be bitwise identical between OLD and NEW, for both `resolve` and
    `gate_interval` (value, exception type and message).
"""
import argparse, hashlib, importlib.util, itertools, json, os, subprocess, sys


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def call(fn, *a, **k):
    """return a comparable record of the outcome, whether a value or an exception"""
    try:
        return {"ok": True, "value": fn(*a, **k)}
    except Exception as e:
        return {"ok": False, "exc": type(e).__name__, "msg": str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--rel", default="multi_asset/exports/research/common/funding_interval.py")
    ap.add_argument("--old-rev", default="HEAD")
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    new_path = os.path.join(a.repo, a.rel)
    old_path = os.path.join(a.scratch, "funding_interval_OLD.py")
    os.makedirs(a.scratch, exist_ok=True)
    blob = subprocess.run(["git", "-C", a.repo, "show", f"{a.old_rev}:{a.rel}"],
                          capture_output=True, check=True).stdout
    with open(old_path, "wb") as f:
        f.write(blob)

    OLD = load(old_path, "fi_old")
    NEW = load(new_path, "fi_new")

    rec = {"device": os.path.basename(os.path.realpath(__file__)),
           "self_sha256": sha(os.path.realpath(__file__)), "argv": sys.argv[1:],
           "python": sys.executable,
           "ruling": ("lead 2026-09-25: off-grid spacing on a non-switch row becomes a named UNRESOLVED "
                      "subclass NONSTANDARD_SPACING -- neither raised nor guessed -- and the build continues"),
           "instrument": ("exhaustive enumeration of the resolver's decision space, not a sample of rows, "
                          "because the claim is about code behaviour"),
           "old": {"rev": a.old_rev, "path_in_repo": a.rel, "extracted_to": old_path,
                   "sha256": sha(old_path), "source": "git show, never reimplemented"},
           "new": {"path": new_path, "sha256": sha(new_path)},
           "tier_sets": {"old": sorted(x for x in dir(OLD) if x.isupper()),
                         "new": sorted(x for x in dir(NEW) if x.isupper())}}

    assert not hasattr(OLD, "NONSTANDARD_SPACING"), "OLD must not already have the new tier"
    assert hasattr(NEW, "NONSTANDARD_SPACING"), "NEW must have the new tier"
    assert NEW.NONSTANDARD_SPACING not in NEW.GATEABLE, "the new tier must never be gateable"
    assert OLD.ALLOWED_IV == NEW.ALLOWED_IV, ("ALLOWED_IV must be untouched", OLD.ALLOWED_IV, NEW.ALLOWED_IV)

    ZIP_V = ("", "8.0", "3.0")
    BEST_V = ("", "4.0", "3.0")
    SRC_V = ("", "structure_steady", "conflicting_rules:zip|interest", "unresolved_edge")
    LIKELY_V = ("", "4.0")
    # BACK_V and FWD_V must carry the SAME value set, or an off-grid value can never form a safe
    # (back == fwd) pair and the targeted family silently shrinks. The first version of this device had
    # 5.0 only in BACK_V, so 5.0 was never actually exercised as safe spacing and the targeted count was
    # 4 instead of 8 -- a coverage hole in the control itself, found by checking that the targeted count
    # was EXPLAINED rather than merely non-zero.
    SPACING_V = ("", "1.0", "3.0", "5.0", "8.0")
    BACK_V = SPACING_V
    FWD_V = SPACING_V

    targeted, others, diffs, targeted_bad = 0, 0, [], []
    n = 0
    for z, b, s, lk, gb, gf, allow in itertools.product(ZIP_V, BEST_V, SRC_V, LIKELY_V, BACK_V, FWD_V,
                                                        (True, False)):
        row = {"iv_zip": z, "iv_best": b, "iv_best_source": s, "iv_likely": lk,
               "iv_likely_support": "support", "iv_gap_back": gb, "iv_gap_fwd": gf}
        n += 1
        ro = call(OLD.resolve, row, allow_spacing=allow)
        rn = call(NEW.resolve, row, allow_spacing=allow)
        go = call(OLD.gate_interval, ro["value"], what="t") if ro["ok"] else {"ok": False, "exc": "resolve_raised"}
        gn = call(NEW.gate_interval, rn["value"], what="t") if rn["ok"] else {"ok": False, "exc": "resolve_raised"}

        is_target = (ro["ok"] and ro["value"].get("tier") == OLD.EXACT_BY_SPACING
                     and not go["ok"] and "not in the allowed set" in go.get("msg", ""))
        if is_target:
            targeted += 1
            bad = []
            if not rn["ok"]:
                bad.append("NEW resolve raised; the build must continue")
            else:
                if rn["value"].get("tier") != NEW.NONSTANDARD_SPACING:
                    bad.append("NEW tier is %r, expected NONSTANDARD_SPACING" % rn["value"].get("tier"))
                if rn["value"].get("iv") is not None:
                    bad.append("NEW returned a guessed iv %r" % rn["value"].get("iv"))
                if rn["value"].get("spacing_value") != float(gb):
                    bad.append("NEW lost the off-grid value")
            if gn["ok"]:
                bad.append("NEW gate accepted a non-gateable tier")
            if bad:
                targeted_bad.append({"row": row, "allow_spacing": allow, "problems": bad})
        else:
            others += 1
            if ro != rn or go != gn:
                if len(diffs) < 10:
                    diffs.append({"row": row, "allow_spacing": allow,
                                  "old_resolve": ro, "new_resolve": rn,
                                  "old_gate": go, "new_gate": gn})

    # the row=None case, outside the product
    for allow in (True, False):
        n += 1
        ro, rn = call(OLD.resolve, None, allow_spacing=allow), call(NEW.resolve, None, allow_spacing=allow)
        if ro != rn:
            diffs.append({"row": None, "allow_spacing": allow, "old_resolve": ro, "new_resolve": rn})
        else:
            others += 1

    rec["cases_enumerated"] = n
    rec["targeted_cases_old_raised_offgrid_spacing"] = targeted
    rec["targeted_cases_failing_the_new_contract"] = targeted_bad
    rec["other_cases"] = others
    rec["other_cases_differing"] = len(diffs)
    rec["first_differences"] = diffs
    rec["control_can_fire"] = bool(targeted > 0)

    ok = (targeted > 0 and not targeted_bad and not diffs)
    rec["verdict"] = "RED_CONTROL_PASS" if ok else (
        "RED_CONTROL_VACUOUS_NO_TARGETED_CASE" if targeted == 0 else "RED_CONTROL_FAIL")
    rec["reading"] = ("OLD raised IntervalError on every off-grid safe-spacing case; NEW labels each one "
                      "NONSTANDARD_SPACING without raising and its gate still refuses; every other point "
                      "in the decision space is bitwise identical between OLD and NEW."
                      if ok else "see targeted_cases_failing_the_new_contract / first_differences")
    rec["limits"] = ["this certifies the code change over its decision space; it says nothing about how many "
                     "REAL rows are NONSTANDARD_SPACING -- that count is a separate stage-1 measurement",
                     "the scope is the spacing tier only; a DECLARED off-grid value still refuses (FI8/FI9c)"]
    with open(a.out, "w") as f:
        json.dump(rec, f, indent=2)

    print("VERDICT", rec["verdict"])
    print(f"  cases enumerated            : {n}")
    print(f"  targeted (OLD raised)       : {targeted}   control_can_fire={rec['control_can_fire']}")
    print(f"  targeted failing new contract: {len(targeted_bad)}")
    print(f"  other cases                 : {others}   differing: {len(diffs)}")
    if targeted_bad:
        print("  first targeted failure:", json.dumps(targeted_bad[0])[:400])
    if diffs:
        print("  first difference:", json.dumps(diffs[0])[:400])
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
