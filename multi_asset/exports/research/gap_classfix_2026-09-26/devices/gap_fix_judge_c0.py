#!/usr/bin/env python3
"""Round 5 (lead ruling 2026-09-27): C0 only, against a SAME-HOST production reference. The production host is now arm64, so the reference for
"the replay reproduces production" must be an anchor produced on arm64 (first one: 08Z 1790496000). The criterion code is NOT rewritten: the C0
section of the frozen gap_fix_judge.py (from '    # C0 ×3' up to '    A = GAP_A') is read from that file, its sha asserted against the literal
below, and executed verbatim with BASE_AS = (A,). Judge file sha is asserted too (literal = the self_sha256 of runs 3 and 4).
usage: ~/wide_shadow/venv/bin/python gap_fix_judge_c0.py <replay root> <A> --out RECEIPT.json   exit 0 = C0 and T PASS, 1 = FAIL, 2 = refused"""
import argparse, hashlib, importlib.util, json, os, sys, time
JUDGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gap_fix_judge.py")
JUDGE_SHA = "01760c370f2078184a89f721c0384f60968a42f75c47645a411a8babaf5b07b3"
C0_BLOCK_SHA = "a6c46dac51768199c3262fb4dd7368b23f041cb00205ddfe9c2587de5141ec31"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("root"); ap.add_argument("A", type=int); ap.add_argument("--out", required=True); a = ap.parse_args()
    raw = open(JUDGE, "rb").read(); js = hashlib.sha256(raw).hexdigest()
    if js != JUDGE_SHA: print(f"REFUSED judge sha {js} != frozen {JUDGE_SHA}"); return 2
    src = raw.decode(); i, j = src.index("    # C0 ×3\n"), src.index("    A = GAP_A\n"); block = src[i:j]
    bs = hashlib.sha256(block.encode()).hexdigest()
    if bs != C0_BLOCK_SHA: print(f"REFUSED C0 block sha {bs} != {C0_BLOCK_SHA}"); return 2
    spec = importlib.util.spec_from_file_location("gap_fix_judge", JUDGE); J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
    ns = dict(vars(J)); ns.update({"a": a, "R": {}, "verdicts": {}, "BASE_AS": (a.A,)})
    exec(compile("if True:\n" + block, JUDGE + ":C0", "exec"), ns)
    R, verdicts = ns["R"], ns["verdicts"]
    for k, v in verdicts.items(): print(f"  {'OK ' if v else 'BAD'} {k}")
    ok = bool(verdicts) and all(verdicts.values())
    rec = {"device": "gap_fix_judge_c0.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "judge_sha256": js, "c0_block_sha256": bs, "reference_anchor": a.A, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "root": a.root, "verdicts": verdicts, "arms": R, "VERDICT": "PASS" if ok else "FAIL"}
    with open(a.out, "w") as f: json.dump(rec, f, indent=1, default=str)
    print(f"GAP_FIX_JUDGE_C0 {'PASS' if ok else 'FAIL'} A={a.A} n_bad={sum(not v for v in verdicts.values())}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
