"""Measure the D4 reference class properly: what dtype does the BASE arm store X82/X89 in, and what is the
median RELATIVE rounding error of that dtype?

lead 2026-09-24: my caveat compared the measured relative change against float32 eps (1.2e-7). The D4 unit
cell says baseline dtype is float16, patched float32. float16 unit roundoff is 2^-11 = 4.88e-4, whose median
relative rounding error lands at ~1e-4 -- which is exactly where my measurement (1.66e-4 / 3.29e-4) sits.
So the reference constant was wrong, and I withdrew a mechanism that the numbers actually support.
This measures the dtype and the f16 roundoff on the real values instead of arguing from constants.
"""
import os, sys
import numpy as np

sys.path.insert(0, "/dev/shm/news2_2026-09-23/devices")
from news2_nc_adapter import Replay

NC = "/dev/shm/nc_2026-09-23"
W = "/dev/shm/news2_2026-09-23"
A = 1789660800

out = {}
for arm in ("base", "D4"):
    R = Replay(f"{NC}/devices_arm", f"{NC}/arms/{arm}", f"{W}/inputs/bundle_config.json",
               f"{W}/scratch/d4dtype/{arm}", f"{W}/work/members_hist_all.npz")
    r = R.at(A)
    out[arm] = {m: (None if r.get(m) is None else np.asarray(r[m])) for m in ("X82", "X89")}
    for m in ("X82", "X89"):
        a = out[arm][m]
        print(f"  {arm:5s} {m:4s} dtype={a.dtype} shape={a.shape}")

print()
for m in ("X82", "X89"):
    b = out["base"][m]
    print(f"--- {m}: median relative error of storing the BASE values at each candidate dtype ---")
    x = np.asarray(b, np.float64)
    fin = np.isfinite(x) & (np.abs(x) > 0)
    xv = x[fin]
    for name, dt in (("float16", np.float16), ("float32", np.float32)):
        rt = np.asarray(xv.astype(dt), np.float64)
        rel = np.abs(rt - xv) / np.abs(xv)
        rel = rel[np.isfinite(rel)]
        print(f"     {name:8s} median_rel={np.median(rel):.3e}  p99_rel={np.percentile(rel,99):.3e} "
              f"max_rel={rel.max():.3e}  unit_roundoff={(2**-11 if dt is np.float16 else 2**-24):.3e}")
    print(f"     MEASURED D4 median relative change on this matrix: "
          f"{'1.66e-04' if m=='X82' else '3.29e-04'}  (from DIAG2_PASS2_REACH.json)")
