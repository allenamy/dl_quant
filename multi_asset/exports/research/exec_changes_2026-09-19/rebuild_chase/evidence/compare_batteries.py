"""Compare two battery runs: per-suite exit code, and per-suite set of FAIL check names (text up to ' — ')."""
import os, re, sys
acc, s0, s1 = sys.argv[1], sys.argv[2], sys.argv[3]
def table(stamp, runlog):
    t = {}
    for line in open(runlog):
        m = re.match(r"^(\S+)\s+(\S+)\s+(\S+_(\S+)\.log)$", line.strip())
        if m and stamp in m.group(3):
            t[m.group(1)] = m.group(2)
    return t
def fails(stamp, suite):
    p = os.path.join(acc, f"{stamp}_{suite}.log")
    if not os.path.exists(p): return None
    out = set()
    for line in open(p, errors="replace"):
        if re.match(r"^\s*FAIL\b", line):
            out.add(re.sub(r"\s+—\s.*$", "", line.strip())[:160])
    return out
t0, t1 = table(s0, sys.argv[4]), table(s1, sys.argv[5])
print(f"suites baseline={len(t0)} after={len(t1)} exit0 baseline={sum(v=='0' for v in t0.values())} after={sum(v=='0' for v in t1.values())}")
for s in sorted(set(t0) | set(t1)):
    a, b = t0.get(s), t1.get(s)
    fa, fb = fails(s0, s), fails(s1, s)
    if a != b or fa != fb:
        print(f"DIFF {s}: exit {a} -> {b}; FAIL-set equal={fa == fb}")
        for x in sorted((fa or set()) - (fb or set())): print("   only baseline:", x[:150])
        for x in sorted((fb or set()) - (fa or set())): print("   only after:   ", x[:150])
    elif a != "0":
        print(f"SAME-RED {s}: exit {a}; {len(fa or ())} FAIL lines, identical set")
