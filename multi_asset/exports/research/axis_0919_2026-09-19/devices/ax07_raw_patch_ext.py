"""AX07 (axis_0919): extend the E-0908-B raw-return patch onto every cache row after the canonical holefix2 end (row N_OLD_ROWS), then the chain's own
manifest writer (v4_rawpatch_manifest.py, unmodified) and coverage rules (v4_rawpatch_lib.verify_files G1-G9) are run by the caller.
Generalises r6_raw_patch_ext.py (808d2f66): criterion VERBATIM (candidate = ch0 == +-float16(0.3); keep iff exact close_t/close_{t-1}-1 has |rv| > 0.3),
old patch rows carried through and asserted bitwise; closes read from the daily zips in AX_KLINE_DIRS (searched in order, day of open time then close time,
same close convention as v4_rawpatch_lib.read_closes). Candidates that are NOT clipped (|rv| <= 0.3) are left to the manifest's not_clipped class.
Cross-check: the r6 x0910 patch rows beyond N_OLD_ROWS (AKE/BULLA/WOO) must be reproduced bitwise when AX_R6_PATCH is given.
env: AX_CACHE AX_OLD_PATCH AX_N_OLD_ROWS AX_KLINE_DIRS AX_OUT AX_RECEIPT [AX_R6_PATCH]
"""
import os, io, json, time, zipfile, hashlib, sys
import numpy as np
E = {k: os.environ.get(k, "") for k in ("AX_CACHE", "AX_OLD_PATCH", "AX_N_OLD_ROWS", "AX_KLINE_DIRS", "AX_OUT", "AX_RECEIPT", "AX_R6_PATCH")}
for k in ("AX_OUT", "AX_RECEIPT"): assert not os.path.exists(E[k]), f"refuse to overwrite {E[k]}"
N_OLD = int(E["AX_N_OLD_ROWS"]); DIRS = [d for d in E["AX_KLINE_DIRS"].split(",") if d]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
def read_closes(path):          # = v4_rawpatch_lib.read_closes (daily zip branch)
    import pandas as pd
    with zipfile.ZipFile(path) as z: raw = z.read(z.namelist()[0])
    k = pd.read_csv(io.BytesIO(raw), header=0 if raw[:1].isalpha() else None).iloc[:, :11]
    ts = (k.iloc[:, 0].astype(np.int64) // 1000 + 300).to_numpy(); c = k.iloc[:, 4].astype(float).to_numpy()
    return dict(zip(ts.tolist(), c.tolist()))
_cc = {}
def close(sym, t):
    for d in DIRS:
        for day in (time.strftime('%Y-%m-%d', time.gmtime(t - 300)), time.strftime('%Y-%m-%d', time.gmtime(t))):
            p = f"{d}/{sym}/{day}.zip"
            if not os.path.isfile(p): continue
            if p not in _cc: _cc[p] = read_closes(p)
            v = _cc[p].get(int(t))
            if v is not None: return v, p
    return None, None
t0 = time.time()
Z = np.load(E["AX_CACHE"], allow_pickle=True); CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]
ch0 = Z["data"][N_OLD:, :, 0]
cand = np.isfinite(ch0) & ((ch0 == np.float16(0.3)) | (ch0 == np.float16(-0.3)))
rows, cols = np.where(cand); rows = rows + N_OLD
print(f"rows >= {N_OLD}: clip candidates {len(rows)}", flush=True)
R, C, TS, SY, RAW, CL, SRC = [], [], [], [], [], [], []; unres = []; notclip = []
for r, c in zip(rows, cols):
    t = int(CTS[r]); a, pa = close(syms[c], t); b, pb = close(syms[c], t - 300)
    if a is None or b is None or not (b > 0): unres.append({"row": int(r), "symbol": syms[c], "ts": t}); continue
    rv = a / b - 1.0
    if abs(rv) <= 0.3: notclip.append({"row": int(r), "symbol": syms[c], "rv": rv}); continue
    R.append(int(r)); C.append(int(c)); TS.append(t); SY.append(syms[c]); RAW.append(np.float32(rv)); CL.append(ch0[r - N_OLD, c]); SRC.append((pa, pb))
O = np.load(E["AX_OLD_PATCH"])
assert int(O["row"].max()) < N_OLD, "old patch reaches beyond N_OLD_ROWS"
out = {k: np.concatenate([O[k], np.array(v, O[k].dtype)]) for k, v in (("row", R), ("col", C), ("ts", TS), ("symbol", SY), ("raw32", RAW), ("clip16", CL))}
for k in ("row", "col", "ts", "symbol", "raw32", "clip16"):
    a, b = out[k][:len(O[k])], O[k]
    assert (a.view(np.uint8) == b.view(np.uint8)).all() if a.dtype.kind == "f" else np.array_equal(a, b), f"old patch column {k} changed"
xr6 = None
if E["AX_R6_PATCH"]:
    P6 = np.load(E["AX_R6_PATCH"]); m6 = P6["row"] >= N_OLD; mm = out["row"] >= N_OLD
    k6 = {(int(r), int(c)): v for r, c, v in zip(P6["row"][m6], P6["col"][m6], P6["raw32"][m6])}
    k7 = {(int(r), int(c)): v for r, c, v in zip(out["row"][mm], out["col"][mm], out["raw32"][mm])}
    xr6 = {"r6_rows_beyond_old": len(k6), "reproduced_bitwise": sum(1 for kk, v in k6.items() if kk in k7 and np.float32(k7[kk]).view(np.uint32) == np.float32(v).view(np.uint32)),
           "r6_rows_missing_here": [list(kk) for kk in k6 if kk not in k7]}
    xr6["PASS"] = xr6["reproduced_bitwise"] == xr6["r6_rows_beyond_old"]
np.savez_compressed(E["AX_OUT"], **out)
rep = {"device": "ax07_raw_patch_ext.py", "self_sha256": sha(os.path.abspath(__file__)), "env": E, "cache_sha256": sha(E["AX_CACHE"]),
       "old_patch_sha256": sha(E["AX_OLD_PATCH"]), "old_n": int(len(O["row"])), "new_candidates": int(len(rows)), "new_kept": len(R), "new_not_clipped": notclip,
       "new_unresolved": unres, "new_bars": [{"ts": time.strftime("%F %H:%MZ", time.gmtime(t)), "symbol": s, "raw32": float(x), "clip16": float(y), "src": list(sr)}
                                              for t, s, x, y, sr in zip(TS, SY, RAW, CL, SRC)],
       "r6_crosscheck": xr6, "out": E["AX_OUT"], "out_sha256": sha(E["AX_OUT"]), "out_n": int(len(out["row"])),
       "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
json.dump(rep, open(E["AX_RECEIPT"], "w"), indent=1)
print("AX07_DONE", json.dumps({k: rep[k] for k in ("old_n", "new_candidates", "new_kept", "out_n")}), "not_clipped", len(notclip), "unresolved", len(unres), "r6", json.dumps(xr6), flush=True)
sys.exit(0 if (not unres and (xr6 is None or xr6["PASS"])) else 3)
