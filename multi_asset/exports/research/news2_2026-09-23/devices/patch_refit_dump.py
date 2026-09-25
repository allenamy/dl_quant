#!/usr/bin/env python3
"""Add a P-dump to news2_king_refit_perturb.py.

Step 0 needs each refit arm's P on the SAME position set as every other panel, and the first run of
that device never persisted P. Reusing the spearman numbers it printed would be a cross-position-set
comparison, which lead forbade. So: dump P and recompute everything on one common set.
"""
import sys

p = "/dev/shm/pnoise_2026-09-24/devices/news2_king_refit_perturb.py"
s = open(p).read()

old = '    rec["arms"] = cmp_out'
new = '''    rec["arms"] = cmp_out
    dump = os.environ.get("REFIT_DUMP_P")
    if dump:
        os.makedirs(dump, exist_ok=True)
        for _arm, _P in preds.items():
            np.savez(os.path.join(dump, "REFIT_P_%s.npz" % _arm), P=_P, E_ts=a, symbols=syms)
        rec["dumped_p"] = sorted(preds)'''

assert s.count(old) == 1, ("anchor count", s.count(old))
s = s.replace(old, new)
open(p, "w").write(s)
print("patched: dump hook present =", "REFIT_DUMP_P" in s)
