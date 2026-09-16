"""R6 EXTEND step 2: merge 2026-09-01..2026-09-11 00Z into the v4 canonical 5m cache (holefix2).

NOT pod_merge_cache_ext.py: that one hard-codes base=_fresh.npz and output=_ext.npz, i.e. the FORBIDDEN _ext lineage
(caliber lock / PREREG §7.2). The per-symbol MATH below is copied VERBATIM from its build() (L26-L32) so the
extension is bit-identical machinery on a different base and a different output path.

Gates (PREREG §7 X2, §6.1 BW-1, §6.1a):
  X2-A  parity on 2026-08-24 00:05 .. 2026-08-31 00:00  (source zips were present when holefix2 was built)
  X2-B  parity on 2026-08-31 00:05 .. 2026-09-01 00:00  (the day holefix2 HOLE-FILLED: 229,824 cells / 798 symbols;
        the daily archive was .404 then and is 200 now, so this is the first time it can be checked against the venue)
  MERGE only rows strictly after base end  => pre-existing rows untouched BY CONSTRUCTION; BW-1 verifies on the file.
"""
import os, sys, glob, io, json, time, zipfile, hashlib
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd

# ---- E-0826-D: enumerate and assert the env whitelist, record EFFECTIVE values in the artifact ----
ENV_WL = ["CACHE_IN", "PANEL_IN", "FEA_OUT", "META_OUT", "DLWT_CACHE", "DLWT_PANEL", "DLWT_OUT",
          "EXT_DAYS", "EXPORT_PANEL", "EMA_STATE_JSON", "R6_BASE", "R6_OUT", "R6_DL", "R6_SHARED"]
ENV_EFF = {k: os.environ.get(k) for k in ENV_WL}
BASE = os.environ.get("R6_BASE", "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz")
OUT  = os.environ.get("R6_OUT",  "/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz")
DL   = os.environ.get("R6_DL",   "/workspace/uplift_2026-09-11/r6/dl/klines")       # 2026-08-31..09-10 (fetched this round)
SHR  = os.environ.get("R6_SHARED", "/workspace/wide_multisrc/klines5m_daily")        # <= 2026-08-30 (already on disk)
assert "_ext.npz" not in BASE and "dlw_ext" not in BASE, f"FORBIDDEN _ext lineage as base: {BASE}"
RPT = "/workspace/uplift_2026-09-11/r6/RECEIPT_cache_merge.json"

SY = open('/workspace/panel_symbols_wide.txt').read().strip().split('|')
IDX = pd.date_range('2026-08-24', '2026-09-11', freq='5min')          # warmup 7d + frontier 2026-09-11 00:00 bar close
WARM_DAYS = {f"2026-08-{d}" for d in range(24, 31)}                   # taken from the SHARED tree (untouched)
NEW_DAYS  = ["2026-08-31"] + [f"2026-09-{d:02d}" for d in range(1, 11)]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()

def read_zip(path):                       # VERBATIM pod_merge_cache_ext.py L10-13
    try:
        with zipfile.ZipFile(path) as z: raw = z.read(z.namelist()[0])
        return pd.read_csv(io.BytesIO(raw), header=0 if raw[:1].isalpha() else None).iloc[:, :11]
    except Exception: return None

def build(sym):                           # math VERBATIM pod_merge_cache_ext.py L15-33 (only the file list differs)
    files = [f"{SHR}/{sym}/{d}.zip" for d in sorted(WARM_DAYS)] + [f"{DL}/{sym}/{d}.zip" for d in NEW_DAYS]
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

def parity(B, E, label):
    fin_b, fin_e = np.isfinite(B), np.isfinite(E)
    both = fin_b & fin_e
    eq = float((B[both] == E[both]).mean()) if both.any() else float('nan')
    bits = float((B[both].view(np.uint16) == E[both].view(np.uint16)).mean()) if both.any() else float('nan')
    return {"window": label, "cells_total": int(B.size), "cells_both_finite": int(both.sum()),
            "exact_eq_rate": eq, "bitwise_eq_rate": bits,
            "nan_pattern_mismatch_rate": float((fin_b ^ fin_e).mean()),
            "base_finite_ext_nan": int((fin_b & ~fin_e).sum()), "ext_finite_base_nan": int((~fin_b & fin_e).sum()),
            "maxabs_diff_on_both_finite": float(np.abs(B[both].astype(np.float32) - E[both].astype(np.float32)).max()) if both.any() else 0.0}

if __name__ == '__main__':
    t0 = time.time()
    rep = {"self_sha256": sha(os.path.abspath(__file__)), "env_effective": ENV_EFF, "env_whitelist": ENV_WL,
           "base": BASE, "base_sha256": sha(BASE), "out": OUT, "dl_dir": DL, "shared_dir": SHR,
           "idx_start": str(IDX[0]), "idx_end": str(IDX[-1]), "new_days": NEW_DAYS, "warm_days": sorted(WARM_DAYS),
           "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    print("R6 merge: base sha", rep["base_sha256"][:16], flush=True)
    res = {}
    with ProcessPoolExecutor(max_workers=16) as ex:
        for i, (s, arr) in enumerate(ex.map(build, SY)):
            res[s] = arr
            if (i+1) % 200 == 0: print('build', i+1, f"{time.time()-t0:.0f}s", flush=True)
    ext = np.stack([res[s] if res[s] is not None else np.full((len(IDX), 7), np.nan, np.float16) for s in SY], axis=1)
    ets = np.array(IDX, dtype='datetime64[s]').astype(np.int64)
    rep["ext_shape"] = list(ext.shape); rep["ext_symbols_with_data"] = int(sum(v is not None for v in res.values()))
    print("ext built", ext.shape, f"{time.time()-t0:.0f}s", flush=True)

    Z = np.load(BASE, allow_pickle=True)
    bts = Z["ts"].astype(np.int64); bdat = Z["data"]; bsym = [str(x) for x in Z["symbols"]]
    assert bsym == SY, "symbol axis mismatch"
    assert np.all(np.diff(bts) == 300), "base ts not 300s-regular"
    rep["base_n"] = int(len(bts)); rep["base_end_utc"] = time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(bts[-1])))

    # ---- X2 parity, split by provenance of the day in the INCUMBENT build ----
    cut_b = int(pd.Timestamp('2026-08-31 00:00').value // 10**9)
    for lab, lo, hi in (("X2-A 2026-08-24 00:05..2026-08-31 00:00 (archive present at holefix2 build time)",
                         int(pd.Timestamp('2026-08-24 00:05').value // 10**9), cut_b),
                        ("X2-B 2026-08-31 00:05..2026-09-01 00:00 (the day holefix2 HOLE-FILLED, archive was 404 then)",
                         cut_b + 300, int(bts[-1]))):
        bm = (bts >= lo) & (bts <= hi); em = (ets >= lo) & (ets <= hi)
        assert bm.sum() == em.sum() and (bts[bm] == ets[em]).all(), f"overlap grid misaligned {lab}"
        p = parity(bdat[bm], ext[em], lab); p["n_rows"] = int(bm.sum())
        rep.setdefault("X2_parity", []).append(p)
        print(f"X2 {lab}\n   rows {p['n_rows']} both-finite {p['cells_both_finite']:,} exact {p['exact_eq_rate']:.6f} "
              f"bitwise {p['bitwise_eq_rate']:.6f} nan_mismatch {p['nan_pattern_mismatch_rate']:.6f} "
              f"maxabs {p['maxabs_diff_on_both_finite']:.3e}", flush=True)

    # ---- merge: base verbatim + rows strictly after base end ----
    keep = ets > int(bts[-1])
    mts = np.concatenate([bts, ets[keep]]); mdat = np.concatenate([bdat, ext[keep]], axis=0)
    assert np.all(np.diff(mts) == 300), "merged ts not 300s-regular"
    rep["new_rows"] = int(keep.sum()); rep["merged_n"] = int(len(mts))
    rep["merged_end_utc"] = time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(mts[-1])))
    rep["new_cells"] = int(keep.sum()) * len(SY) * 7
    tmp = OUT + ".tmp.npz"
    np.savez_compressed(tmp, ts=mts, symbols=Z["symbols"], ch=Z["ch"], data=mdat)
    os.replace(tmp, OUT)
    rep["out_sha256"] = sha(OUT); rep["out_bytes"] = os.path.getsize(OUT)
    rep["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); rep["wall_s"] = round(time.time()-t0, 1)
    json.dump(rep, open(RPT, "w"), indent=1)
    print(f"R6_MERGE_DONE n={len(mts)} end={rep['merged_end_utc']} new_rows={rep['new_rows']} sha={rep['out_sha256'][:16]}", flush=True)
