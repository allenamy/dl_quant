"""R6 EXTEND: extend the E-0908-B raw-return patch onto the NEW cache rows.
The v4 DL targets are built with DLWT_RAW_PATCH=raw_patch.npz, which substitutes the EXACT float32 return on every
bar the float16 cache clipped at +-0.3 (clip-then-compound turned -48% into +55%, E-0908-B). That patch was built
over the incumbent rows only; a September bar that hits the clip would silently re-introduce the defect on the new
anchors. Criterion copied VERBATIM from make_raw_patch.py L6/L27-31: candidate = ch0 == +-float16(0.3); keep iff the
exact close_t/close_{t-1}-1 has |rv| > 0.3. Closes come from the same daily zips the extension was built from.
Incumbent rows are carried through unchanged and asserted bitwise.
"""
import os, io, glob, json, time, zipfile, hashlib, sys
import numpy as np, pandas as pd
CACHE = os.environ.get("R6_OUT", "/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz")
OLD   = "/workspace/review_scratch/raw_patch.npz"
OUTP  = os.environ.get("R6_RAW_PATCH", "/workspace/uplift_2026-09-11/r6/out/raw_patch_x0910.npz")
DL    = "/workspace/uplift_2026-09-11/r6/dl/klines"
N_OLD_ROWS = 490753
def sha(p):
    h = hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(1<<24), b""): h.update(c)
    return h.hexdigest()
sys.path.insert(0, "/workspace"); from zload import zload
Z = zload(CACHE, allow_pickle=True); CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]
ch0 = Z["data"][N_OLD_ROWS:, :, 0]
cand = np.isfinite(ch0) & ((ch0 == np.float16(0.3)) | (ch0 == np.float16(-0.3)))
rows, cols = np.where(cand); rows = rows + N_OLD_ROWS
print(f"new-row clip candidates: {len(rows)}", flush=True)
closes = {}
def load_sym(s):
    if s in closes: return closes[s]
    d = {}
    for p in sorted(glob.glob(f"{DL}/{s}/*.zip")):
        try:
            with zipfile.ZipFile(p) as z: raw = z.read(z.namelist()[0])
            k = pd.read_csv(io.BytesIO(raw), header=0 if raw[:1].isalpha() else None).iloc[:, :11]
        except Exception: continue
        ts = (k.iloc[:,0].astype(np.int64)//1000 + 300).to_numpy(); c = k.iloc[:,4].astype(float).to_numpy()
        d.update(dict(zip(ts.tolist(), c.tolist())))
    closes[s] = d; return d
R,C,TS,SY,RAW,CL = [],[],[],[],[],[]; miss=0; notclip=0
for r, c in zip(rows, cols):
    t = int(CTS[r]); d = load_sym(syms[c]); a = d.get(t); b = d.get(t-300)
    if a is None or b is None or b <= 0: miss += 1; continue
    rv = a/b - 1.0
    if abs(rv) <= 0.3: notclip += 1; continue
    R.append(int(r)); C.append(int(c)); TS.append(t); SY.append(syms[c]); RAW.append(np.float32(rv)); CL.append(ch0[r-N_OLD_ROWS, c])
O = np.load(OLD)
out = {k: np.concatenate([O[k], np.array(v, O[k].dtype)]) for k, v in
       (("row",R),("col",C),("ts",TS),("symbol",SY),("raw32",RAW),("clip16",CL))}
assert np.array_equal(out["row"][:len(O["row"])], O["row"]) and np.array_equal(out["raw32"][:len(O["raw32"])], O["raw32"], equal_nan=True)
assert out["row"].max() < len(CTS)
np.savez_compressed(OUTP, **out)
rep = {"old_patch": OLD, "old_sha256": sha(OLD), "old_n": int(len(O["row"])),
       "new_candidates": int(len(rows)), "new_kept": len(R), "new_notclip": notclip, "new_unresolved": miss,
       "new_bars": [{"ts": time.strftime("%F %H:%MZ", time.gmtime(t)), "symbol": s, "raw32": float(x), "clip16": float(y)}
                    for t,s,x,y in zip(TS,SY,RAW,CL)],
       "out": OUTP, "out_sha256": sha(OUTP), "out_n": int(len(out["row"])),
       "incumbent_rows_bitwise_unchanged": True,
       "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(rep, open("/workspace/uplift_2026-09-11/r6/RECEIPT_raw_patch.json","w"), indent=1)
print("R6_RAW_PATCH_DONE " + json.dumps({k: rep[k] for k in ("old_n","new_candidates","new_kept","new_notclip","new_unresolved","out_n")}), flush=True)
if miss: print(f"WARNING {miss} new clip candidates unresolved (no close in the fetched zips)", flush=True)
