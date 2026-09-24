"""fa_a2b.py — supplement to A2, ADDED AFTER SEEING A2's output. Purely descriptive, NO criterion attached.
Reason: A2 reported hold fraction and raw gross for the FRESH arm only. A D-minus-A story needs both arms on
the SAME anchor sets, otherwise 'high-seat anchors hold 53% of the time' cannot be read as a difference.
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x
OUT = sys.argv[2]
F = "/dev/shm/fresh_2026-09-23"; N = "/dev/shm/news_2026-09-23"
PRE = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"); Q33, Q67 = 0.5725596881282329, 0.7810047984528542
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def q(v, m):
    vv = v[m]; vv = vv[np.isfinite(vv)]
    return {"median": float(np.median(vv)), "q25": float(np.percentile(vv, 25)), "q75": float(np.percentile(vv, 75))} if len(vv) else None
CF = np.load(f"{F}/work/combo_s42/scaled_diagnostic.npz", allow_pickle=True)
CN = np.load(f"{N}/work/combo_s42/scaled_diagnostic.npz", allow_pickle=True)
ce = CF["E_ts"].astype(np.int64)
LF = np.load(f"{F}/work/legs.npz"); le = LF["E_ts"].astype(np.int64)
sp = {int(t): i for i, t in enumerate(le)}; si = np.array([sp[int(t)] for t in ce])
seat = LF["WL"][si, 0].astype(np.float64)
terc = np.where(seat <= Q33, 0, np.where(seat <= Q67, 1, 2))
pre = (ce >= ts(PRE[0])) & (ce <= ts(PRE[1]))
out = {"device": "fa_a2b.py", "self_sha256": sha(os.path.abspath(__file__)),
       "status": "SUPPLEMENT, added after seeing A2; descriptive only, no criterion",
       "why": "A2's hold/gross table was FRESH-only; a D-minus-A reading needs both arms on the same anchors",
       "gross_floor": 0.4, "arms": {}}
for arm, C in (("FRESH", CF), ("NEWS", CN)):
    g = np.abs(C["raw"]).sum(1); hold = ~np.asarray(C["trade_mask"]).astype(bool)
    rsn = np.array([str(x) for x in C["reason"]])
    d = {}
    for nm, m in (("high_seat", pre & (terc == 2)), ("rest", pre & (terc != 2))):
        gm = g[m]
        d[nm] = {"n": int(m.sum()), "raw_gross": q(g, m), "hold_fraction": float(hold[m].mean()),
                 "frac_gross_below_0.4": float((gm < 0.4).mean()),
                 "reason_counts": {k: int(v) for k, v in zip(*np.unique(rsn[m], return_counts=True))}}
    out["arms"][arm] = d
json.dump(out, open(OUT, "w"), indent=1, default=float)
f = out["arms"]["FRESH"]; n = out["arms"]["NEWS"]
print("FA_A2B high_seat: hold FRESH=%.3f NEWS=%.3f | gross<0.4 FRESH=%.3f NEWS=%.3f | gross med FRESH=%.4f NEWS=%.4f"
      % (f["high_seat"]["hold_fraction"], n["high_seat"]["hold_fraction"], f["high_seat"]["frac_gross_below_0.4"],
         n["high_seat"]["frac_gross_below_0.4"], f["high_seat"]["raw_gross"]["median"], n["high_seat"]["raw_gross"]["median"]), flush=True)
print("FA_A2B rest     : hold FRESH=%.3f NEWS=%.3f | gross<0.4 FRESH=%.3f NEWS=%.3f | gross med FRESH=%.4f NEWS=%.4f"
      % (f["rest"]["hold_fraction"], n["rest"]["hold_fraction"], f["rest"]["frac_gross_below_0.4"],
         n["rest"]["frac_gross_below_0.4"], f["rest"]["raw_gross"]["median"], n["rest"]["raw_gross"]["median"]), flush=True)
print("FA_A2B reasons high_seat FRESH=%s NEWS=%s" % (f["high_seat"]["reason_counts"], n["high_seat"]["reason_counts"]), flush=True)
assert os.path.exists(OUT)
