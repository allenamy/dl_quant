"""#39 item 2 — does any S2-GENERATION artifact exist? Checked by FIELDS, not names.

★ `wideA_s2_y24_*` is the s2 LEG, not the S2 generation. Same string, different objects — the
  family that bit us today. S2 is defined by: data endpoint 2026-07-31 23:00 UTC, frozen 140
  columns, run suffix `_ac`.
"""
import glob
import os

import numpy as np
import pandas as pd

R = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
TARGET = pd.Timestamp("2026-07-31 23:00", tz="UTC")
print("S2 data endpoint would be: %s\n" % TARGET.isoformat())
print("%-46s %10s %8s %s" % ("panel", "T", "N/cols", "last anchor UTC"))
print("-" * 92)
hits = []
for p in sorted(glob.glob(R + "/*.npz")):
    try:
        z = np.load(p, allow_pickle=True)
        if "ts" not in z.files:
            continue
        ts = np.asarray(z["ts"]).astype(np.int64)          # materialise before the handle closes
        n = int(np.asarray(z["MEMBER110"]).shape[1]) if "MEMBER110" in z.files else -1
        last = pd.to_datetime(int(ts.max()), unit="ms", utc=True)
        z.close()
        flag = ""
        if last >= TARGET:
            flag = "   <-- reaches the S2 endpoint"
            hits.append((p, last))
        print("%-46s %10d %8s %s%s" % (os.path.basename(p), len(ts), n, last.isoformat(), flag))
    except Exception as e:
        print("%-46s  (%s: %s)" % (os.path.basename(p), type(e).__name__, e))
print("\n⇒ panels reaching 2026-07-31 23:00 UTC: %d" % len(hits))
for p, l in hits:
    print("   %s  (last %s)" % (p, l.isoformat()))
