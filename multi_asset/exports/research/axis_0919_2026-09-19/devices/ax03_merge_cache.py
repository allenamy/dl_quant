"""AX03 (axis_0919, stream D): append 5m rows to the research cache holefix2_x0910 (-> 2026-09-19T00:00Z bar close).

Lineage: holefix2 canon (rows -> 2026-09-01T00:00Z) -> r6 x0910 (append-only, BW-1 PASS, rows -> 2026-09-11T00:00Z) -> THIS (rows -> AX_IDX_END).
Per-symbol MATH copied VERBATIM from r6_merge_cache.py build() (= pod_merge_cache_ext.py L15-33); only the file lists and the index change, all by env.
Nothing is hard-coded to a month: base, output, warm-up days/dir, new days/dir, index start/end, parity window all come from env (E-0826-D: the
effective values are written into the receipt).

Gates (all computed here; BW is re-read from the WRITTEN file by ax03b_bw_gate.py):
  PAR  rows [AX_PARITY_LO .. base end] rebuilt from the SAME zips the base was built from must equal the base bitwise (proves this device reproduces
       the base's own construction). AX_PARITY_LO must be the THIRD index row: row 1 (= AX_IDX_START) has no bar in the warm-up zips (its bar opens the
       previous day) and row 2 has a close but no predecessor, so its ret5 is NaN by construction (rehearsal 07:02Z: exactly 798 = one cell per listed
       symbol, all finite cells bitwise equal). The appended rows are unaffected: their first predecessor close (base end) is inside the loaded zips.
  MRG  only rows strictly after the base end are appended; ts step 300 s over the merged axis; merged end == AX_IDX_END.
  DAY  per new day: symbols with >=1 bar, with all 288 bars (descriptive; the coverage gate v2 decides).
Refuses to overwrite AX_OUT or the receipt.
"""
import os, sys, io, json, time, zipfile, hashlib
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd

ENV_WL = ["AX_BASE", "AX_OUT", "AX_RECEIPT", "AX_WARM_DIR", "AX_WARM_DAYS", "AX_NEW_DIR", "AX_NEW_DAYS", "AX_IDX_START", "AX_IDX_END", "AX_PARITY_LO"]
ENV = {k: os.environ[k] for k in ENV_WL}
BASE, OUT, RPT = ENV["AX_BASE"], ENV["AX_OUT"], ENV["AX_RECEIPT"]
WARM_DIR, NEW_DIR = ENV["AX_WARM_DIR"], ENV["AX_NEW_DIR"]
WARM_DAYS = [d for d in ENV["AX_WARM_DAYS"].split(",") if d]; NEW_DAYS = [d for d in ENV["AX_NEW_DAYS"].split(",") if d]
IDX = pd.date_range(ENV["AX_IDX_START"], ENV["AX_IDX_END"], freq='5min')
PAR_LO = int(pd.Timestamp(ENV["AX_PARITY_LO"]).value // 10**9)
for p in (OUT, RPT): assert not os.path.exists(p), f"refuse to overwrite {p}"
assert "_ext.npz" not in BASE and "dlw_ext" not in BASE, f"FORBIDDEN _ext lineage as base: {BASE}"
SY = open('/workspace/panel_symbols_wide.txt').read().strip().split('|')

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()

def read_zip(path):                       # VERBATIM r6_merge_cache.py / pod_merge_cache_ext.py L10-13
    try:
        with zipfile.ZipFile(path) as z: raw = z.read(z.namelist()[0])
        return pd.read_csv(io.BytesIO(raw), header=0 if raw[:1].isalpha() else None).iloc[:, :11]
    except Exception: return None

def build(sym):                           # math VERBATIM r6_merge_cache.py build() (only the file list differs)
    files = [f"{WARM_DIR}/{sym}/{d}.zip" for d in WARM_DAYS] + [f"{NEW_DIR}/{sym}/{d}.zip" for d in NEW_DAYS]
    ks = []
    for f in files:
        if not os.path.exists(f): continue
        d = read_zip(f)
        if d is None or len(d) == 0: continue
        d.columns = ['open_time','o','h','l','c','v','close_time','qv','cnt','tbv','tbqv'][:d.shape[1]]
        ks.append(d)
    if not ks: return sym, None
    k = pd.concat(ks)
    k['ts'] = pd.to_datetime(k.open_time.astype(np.int64), unit='ms') + pd.Timedelta('5min')
    k = k.drop_duplicates('ts').set_index('ts').sort_index().reindex(IDX)
    A = np.full((len(IDX), 7), np.nan, np.float16)
    A[:,0] = np.clip(k.c.pct_change(fill_method=None), -0.3, 0.3)
    A[:,1] = np.clip((k.h-k.l)/k.c, 0, 0.5)
    A[:,2] = ((k.c-k.l)/(k.h-k.l)).clip(0,1)
    A[:,3] = np.log1p(k.qv).clip(0, 25); A[:,4] = np.log1p(k.cnt).clip(0, 20)
    A[:,5] = np.log((k.qv/k.cnt.replace(0,np.nan))).clip(-5, 15)
    A[:,6] = (k.tbqv/k.qv).clip(0,1)
    return sym, A

def parity(B, E):
    fb, fe = np.isfinite(B), np.isfinite(E); both = fb & fe
    return {"cells_total": int(B.size), "cells_both_finite": int(both.sum()),
            "bitwise_eq_cells_both_finite": int((B[both].view(np.uint16) == E[both].view(np.uint16)).sum()),
            "nan_pattern_mismatch_cells": int((fb ^ fe).sum()),
            "maxabs_diff_both_finite": float(np.abs(B[both].astype(np.float32) - E[both].astype(np.float32)).max()) if both.any() else 0.0}

if __name__ == '__main__':
    t0 = time.time()
    rep = {"device": "ax03_merge_cache.py", "self_sha256": sha(os.path.abspath(__file__)), "env_effective": ENV,
           "base_sha256": sha(BASE), "idx_start": str(IDX[0]), "idx_end": str(IDX[-1]), "idx_n": int(len(IDX)),
           "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    print("AX03 base sha", rep["base_sha256"][:16], "idx", IDX[0], IDX[-1], flush=True)
    res = {}
    with ProcessPoolExecutor(max_workers=16) as ex:
        for i, (s, arr) in enumerate(ex.map(build, SY)):
            res[s] = arr
            if (i + 1) % 200 == 0: print('build', i + 1, f"{time.time()-t0:.0f}s", flush=True)
    ext = np.stack([res[s] if res[s] is not None else np.full((len(IDX), 7), np.nan, np.float16) for s in SY], axis=1)
    ets = np.array(IDX, dtype='datetime64[s]').astype(np.int64)
    rep["ext_shape"] = list(ext.shape); rep["ext_symbols_with_data"] = int(sum(v is not None for v in res.values()))
    Z = np.load(BASE, allow_pickle=True)
    bts = Z["ts"].astype(np.int64); bdat = Z["data"]; bsym = [str(x) for x in Z["symbols"]]
    assert bsym == SY, "symbol axis mismatch"
    assert np.all(np.diff(bts) == 300), "base ts not 300s-regular"
    rep["base_n"] = int(len(bts)); rep["base_end_utc"] = time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(bts[-1])))
    # ---- PAR: rebuilt overlap vs base, bitwise ----
    bm = (bts >= PAR_LO) & (bts <= bts[-1]); em = (ets >= PAR_LO) & (ets <= bts[-1])
    assert bm.sum() == em.sum() > 0 and (bts[bm] == ets[em]).all(), "overlap grid misaligned"
    p = parity(bdat[bm], ext[em]); p["n_rows"] = int(bm.sum())
    p["window"] = f"{time.strftime('%F %H:%MZ', time.gmtime(PAR_LO))} .. {rep['base_end_utc']}"
    p["PASS"] = bool(p["nan_pattern_mismatch_cells"] == 0 and p["bitwise_eq_cells_both_finite"] == p["cells_both_finite"])
    rep["PAR"] = p
    print("PAR", json.dumps(p), flush=True)
    # ---- DAY census on new rows ----
    keep = ets > int(bts[-1])
    new = ext[keep]; nts = ets[keep]; day = (nts - 300) // 86400          # a bar belongs to the day of its OPEN time
    dc = {}
    for d in np.unique(day):
        sel = day == d; fin = np.isfinite(new[sel, :, 0]); cnt = fin.sum(0)
        dc[time.strftime("%F", time.gmtime(int(d) * 86400))] = {"rows": int(sel.sum()), "symbols_any_bar": int((cnt > 0).sum()),
                                                                   "symbols_full": int((cnt == sel.sum()).sum())}
    rep["DAY_new_rows"] = dc
    # ---- MRG ----
    mts = np.concatenate([bts, nts]); mdat = np.concatenate([bdat, new], axis=0)
    assert np.all(np.diff(mts) == 300), "merged ts not 300s-regular"
    assert int(mts[-1]) == int(ets[-1]), "merged end != index end"
    rep["new_rows"] = int(keep.sum()); rep["merged_n"] = int(len(mts))
    rep["merged_first_new_utc"] = time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(nts[0])))
    rep["merged_end_utc"] = time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(mts[-1])))
    rep["new_cells"] = int(keep.sum()) * len(SY) * 7
    rep["new_rows_clip_candidates_ch0"] = int((np.isfinite(new[:, :, 0]) & (np.abs(new[:, :, 0]) == np.float16(0.3))).sum())
    if not p["PASS"]:
        rep["VERDICT"] = "FAIL_PAR (nothing written)"; json.dump(rep, open(RPT, "w"), indent=1); print("AX03_FAIL_PAR", flush=True); sys.exit(3)
    tmp = OUT[:-4] + ".tmp.npz"
    np.savez_compressed(tmp, ts=mts, symbols=Z["symbols"], ch=Z["ch"], data=mdat)
    os.replace(tmp, OUT)
    rep["out"] = OUT; rep["out_sha256"] = sha(OUT); rep["out_bytes"] = os.path.getsize(OUT)
    rep["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); rep["wall_s"] = round(time.time() - t0, 1)
    rep["VERDICT"] = "WRITTEN (BW gate pending: ax03b)"
    json.dump(rep, open(RPT, "w"), indent=1)
    print(f"AX03_MERGE_DONE n={len(mts)} end={rep['merged_end_utc']} new_rows={rep['new_rows']} sha={rep['out_sha256'][:16]}", flush=True)
