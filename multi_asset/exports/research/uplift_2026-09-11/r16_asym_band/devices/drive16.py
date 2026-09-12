"""r16 driver. arms: 6 XMODE x 2 seeds (AUX16=1). nulls: 6 XMODE x XNULL 1..3 x 2 seeds (AUX16=1, W not kept)."""
import json, sys, time
from concurrent.futures import ThreadPoolExecutor
import common16 as C
C.setup(); dev_sha = C.assert_pins()
assert C.loadavg() <= 6.0, "load > 6, wait"
print("device sha256", dev_sha, "gpu before:", C.gpu(), "load:", C.loadavg(), flush=True)
which = sys.argv[1]; jobs = []
for xm in ("X0", "X1", "X2", "X3", "X4", "X5"):
    for sd in (42, 2027):
        if which == "arms": jobs.append(("A_%s_s%d" % (xm, sd), sd, xm, 0, 1, True))
        elif which == "nulls":
            for d in (1, 2, 3): jobs.append(("N_%s_d%d_s%d" % (xm, d, sd), sd, xm, d, 1, False))
recs = {}; t0 = time.time()
with ThreadPoolExecutor(max_workers=6) as ex:
    for tag, st, er in ex.map(lambda j: C.run(*j), jobs):
        print("%-22s %s  %.0fs" % (tag, st, time.time() - t0), flush=True); recs[tag] = er
C.save_env("R16_RUN_ENV.json", recs)
print("gpu after:", C.gpu()); print("DRIVE_DONE", which)
