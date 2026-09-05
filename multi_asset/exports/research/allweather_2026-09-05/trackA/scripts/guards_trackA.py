"""guards_trackA.py — the two frozen guards before any gate (PREREG_allweather_programme_2026-09-05 §3 Track A "双守卫") + a bar-shift receipt.
 (i)  hit-rate: for every feature, over member cells (anchor i, symbol m in members[i]) whose source is available (avail[i,m] from the builder =
      source close finite at the right edge), share with a finite feature value; assertion >= 0.95 (overall and by year reported).
 (ii) anchor lead/lag spectrum: IC_k = mean over anchors of Spearman(F_shift0[i, m], y4[i+k, m]) for k in -3..+3 over anchor pairs exactly
      k*4h apart (y4[i+k] = return over [E_{i+k}, E_{i+k}+4h]; k=0 is the target). PASS iff argmax_k |IC_k| <= 0 (peak at lag 0 or on the past side).
 (iii) bar-shift receipt (not a gate): IC vs y4 (k=0) for the feature files built with right edge shifted by j bars (j = -2..+3; j>=2 uses bars
      inside the y4 window) — shows where information enters when the alignment is moved into the future.
env: META_IN FILES ("j=path,..." feature npz per shift; j=0 required) OUT_JSON TAG
"""
import os, json, time, hashlib
import numpy as np
from scipy.stats import spearmanr
SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
META_IN = os.environ.get("META_IN", "/workspace/data/wide_fea_v2ext_meta.npz")
FILES = {int(kv.split("=")[0]): kv.split("=")[1] for kv in os.environ["FILES"].split(",") if kv}
OUT_JSON = os.environ["OUT_JSON"]; TAG = os.environ.get("TAG", "")
MT = np.load(META_IN, allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; nA = len(E_ts)
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
Z0 = np.load(FILES[0], allow_pickle=True); F0 = np.asarray(Z0["F"], np.float32); NAMES = [str(n) for n in Z0["names"]]; AV = np.asarray(Z0["avail"], bool)
assert np.array_equal(Z0["E_ts"].astype(np.int64), E_ts)
print(f"CONFIG {json.dumps({'self_sha256': SELF, 'META_IN': META_IN, 'FILES': FILES, 'TAG': TAG, 'names': NAMES})}", flush=True)
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
res = {"self_sha256": SELF, "tag": TAG, "names": NAMES, "hit_rate": {}, "leadlag_anchor": {}, "barshift": {}, "verdict": {}}
# (i) hit-rate
memmask = np.zeros((nA, y4.shape[1]), bool)
for i in range(nA): memmask[i, members[i]] = True
cells = memmask & AV
print(f"member cells {memmask.sum()} available {cells.sum()} ({cells.sum()/memmask.sum():.3f} of member cells)", flush=True)
for k, nm in enumerate(NAMES):
    fin = np.isfinite(F0[:, :, k]) & cells
    by = {}
    for y in sorted(set(yrs.tolist())):
        r = yrs == y; d = cells[r].sum(); by[str(y)] = round(float(fin[r].sum() / d), 4) if d else None
    hr = float(fin.sum() / cells.sum()) if cells.sum() else float("nan")
    res["hit_rate"][nm] = {"overall": round(hr, 4), "by_year": by, "n_avail_cells": int(cells.sum()), "PASS": bool(hr >= 0.95)}
    print(f"HIT {nm} overall {hr:.4f} by_year {by} {'PASS' if hr >= 0.95 else 'FAIL'}", flush=True)
# (ii) anchor lead/lag
pos = {int(t): i for i, t in enumerate(E_ts)}
for k, nm in enumerate(NAMES):
    spec = {}
    for lag in range(-3, 4):
        ics = []
        for i in range(nA):
            j = pos.get(int(E_ts[i]) + lag * 14400)
            if j is None: continue
            m = members[i]; ics.append(sp(F0[i, m, k], y4[j, m]))
        spec[str(lag)] = round(float(np.nanmean(ics)), 4)
    peak = max(spec, key=lambda s: abs(spec[s]) if np.isfinite(spec[s]) else -1)
    ok = int(peak) <= 0
    res["leadlag_anchor"][nm] = {"ic_by_lag": spec, "peak_lag": int(peak), "PASS": bool(ok)}
    print(f"LEADLAG {nm} {spec} peak {peak} {'PASS' if ok else 'FAIL'}", flush=True)
# (iii) bar-shift receipt
for j in sorted(FILES):
    Zj = np.load(FILES[j], allow_pickle=True); Fj = np.asarray(Zj["F"], np.float32); assert [str(n) for n in Zj["names"]] == NAMES
    row = {}
    for k, nm in enumerate(NAMES):
        ics = [sp(Fj[i, members[i], k], y4[i, members[i]]) for i in range(nA)]
        row[nm] = round(float(np.nanmean(ics)), 4)
    res["barshift"][str(j)] = row
    print(f"BARSHIFT j={j:+d} {row}", flush=True)
res["verdict"] = {"hit_rate_all_pass": bool(all(v["PASS"] for v in res["hit_rate"].values())),
                  "leadlag_all_pass": bool(all(v["PASS"] for v in res["leadlag_anchor"].values()))}
json.dump(res, open(OUT_JSON, "w"), indent=1)
print(f"GUARDS_DONE {TAG} {res['verdict']}", flush=True)
