#!/usr/bin/env python3
"""mk_t5c_device.py — generate the T5c replay device from the T5 device (PREREG_T5c §9 step 3).
usage: python mk_t5c_device.py <w10_sleeve_t5.py> <out w10_sleeve_t5c.py> <PREREG_T5c_september_replay_vs_deployed_2026-09-13.md>
Only the T5_DUMP window moves to 2026-08-30 00Z..2026-09-10 00Z and the config self-report names the T5c prereg. rec / W / T1 arrays are untouched
(gate G-X compares them bitwise with the T1 arms on every anchor <= 2026-08-30 20Z). Each replacement must match exactly once.
"""
import sys, hashlib
SRC, DST, PREREG = sys.argv[1], sys.argv[2], sys.argv[3]
T5_SHA = "4c5b972eebfb48c3423b0f6c1336b13cb588fb8ec8edf9c7948d67c59dc05add"; PREREG_SHA = "a669c62782c58d424eed17cf3c7b2a8ad78050c059f43cb2e6496737eaf56a48"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(SRC) == T5_SHA, ("T5 device sha", sha(SRC)); assert sha(PREREG) == PREREG_SHA, ("T5c prereg sha", sha(PREREG))
s = open(SRC).read()
REP = [("T5_LO, T5_HI = 1787688000, 1788120000\n", "T5_LO, T5_HI = 1788048000, 1788998400   # T5c: dump window 2026-08-30 00Z..2026-09-10 00Z\n"),
       ('"device": "w10_sleeve_t5.py = w10_sleeve_t1.py + T5_DUMP window dump; default => bitwise-unchanged; PREREG_T5 §9"}\n',
        '"device": "w10_sleeve_t5c.py = w10_sleeve_t5.py with the T5_DUMP window moved; default => bitwise-unchanged", "t5_src_sha256": "%s", "t5c_prereg_sha256": "%s"}\n' % (T5_SHA, PREREG_SHA))]
for a, b in REP:
    n = s.count(a); assert n == 1, ("replacement must match exactly once", n, a[:80])
    s = s.replace(a, b)
open(DST, "w").write(s); print("wrote", DST, "sha256", hashlib.sha256(s.encode()).hexdigest())
