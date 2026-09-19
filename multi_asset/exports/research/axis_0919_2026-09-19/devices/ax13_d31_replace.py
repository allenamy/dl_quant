"""AX13 (axis_0919, variant x0918r): replace the HOLE-FILLED 2026-08-31 rows of the x0918 cache by the official data.binance.vision DAILY 5m archives,
and emit the matching hole-cell file. x0918 files are only read.

Provenance of the fill (traced from the pod sources, not assumed):
  * pod_merge_cache_ext.py built the `_ext` cache on 2026-09-01 01:52Z, before the 2026-08-31 daily archive existed (wide_multisrc/klines5m_daily
    still holds `<SYM>/2026-08-31.zip.404` markers) => every 08-31 row was NaN in `_ext`;
  * review_scratch/holefix_build.py (Task A, 09-08) filled every NaN August cell FILL-ONLY-NaN from the official 2026-08 MONTHLY 5m archive
    (holefix_build.log: "2026-08-31(D2) 1478732" channel cells);
  * v4_hole_cells.py then recorded every (row, symbol) finite in holefix2 but NaN in `_ext` as a hole cell: the 08-31 day became fill run
    [490465, 490752] (229,824 cells / 798 symbols) with neighbourhood [490417, 499392] = [run_start-48, run_end+8640];
  * MEMBER_LIVENESS treats every hole cell as "not a real bar" => the anchor 2026-09-01T00Z (window = exactly the 288 rows of 08-31) had no live name.

What this device does:
  R1 rebuild rows AX_LO..AX_HI (the replaced range) per symbol from the daily zips of AX_DAY (and AX_PREV_DAY for pct_change continuity) with the
     channel math VERBATIM from r6_merge_cache.py / pod_merge_cache_ext.py (= holefix_build.py's math); zips must be checksum-verified beforehand
     (receipts named in AX_CHECKSUM_RECEIPTS; every zip read here must appear there with status OK, else FAIL);
  R2 compare with the x0918 cells, per channel: bitwise (uint16) on both-finite, NaN-pattern mismatches, max |delta|;
  R3 official-bar evidence per hole cell of the replaced run: the daily archive has a kline row whose close time == the cell's ts;
  R4 the corrected data = x0918 data with the replaced range taken from the official rebuild wherever the archive has a bar, the x0918 value
     otherwise (such cells stay hole-filled and stay in the hole list); if the corrected data is bitwise identical to x0918 (R2 all zero), the
     x0918r cache is written as a BYTE COPY of the x0918 file (one sha for one content), else as a new npz;
  R5 hole-cell file for x0918r = holefix2_cells minus every cell evidenced in R3 (all keys kept; a run whose cells are all removed is dropped from
     fill_runs and its neighbourhood from neigh_rows); plus `removed_*` arrays and a provenance string.
env (all required): AX_CACHE AX_OUT_CACHE AX_HOLES AX_OUT_HOLES AX_DAY AX_PREV_DAY AX_DAY_DIR AX_PREV_DIR AX_LO AX_HI AX_CHECKSUM_RECEIPTS AX_RECEIPT
"""
import os, io, sys, json, time, zipfile, hashlib, shutil
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
REQ = ["AX_CACHE", "AX_OUT_CACHE", "AX_HOLES", "AX_OUT_HOLES", "AX_DAY", "AX_PREV_DAY", "AX_DAY_DIR", "AX_PREV_DIR", "AX_LO", "AX_HI", "AX_CHECKSUM_RECEIPTS", "AX_RECEIPT"]
E = {k: os.environ[k] for k in REQ}
for k in ("AX_OUT_CACHE", "AX_OUT_HOLES", "AX_RECEIPT"): assert not os.path.exists(E[k]), f"refuse to overwrite {E[k]}"
LO, HI = int(E["AX_LO"]), int(E["AX_HI"])
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
SY = open('/workspace/panel_symbols_wide.txt').read().strip().split('|')
# ---- checksum evidence: every zip we read must be OK in a checksum receipt
OKZIP = {}
for rp in E["AX_CHECKSUM_RECEIPTS"].split(","):
    for m in json.load(open(rp))["manifest"]:
        if m.get("status") == "OK" and m.get("local"): OKZIP[m["local"]] = m["local_sha256"]
Z = np.load(E["AX_CACHE"], allow_pickle=True); CTS = Z["ts"].astype(np.int64)
assert [str(s) for s in Z["symbols"]] == SY
T_LO, T_HI = int(CTS[LO]), int(CTS[HI])
IDX = pd.date_range(pd.Timestamp(T_LO - 300, unit="s") - pd.Timedelta("1D") + pd.Timedelta("5min"), pd.Timestamp(T_HI, unit="s"), freq="5min")
RSEL = slice(len(IDX) - (HI - LO + 1), len(IDX))
assert np.array_equal(np.array(IDX[RSEL], dtype="datetime64[s]").astype(np.int64), CTS[LO:HI + 1]), "index misaligned with cache rows"

def read_zip(path):                       # VERBATIM r6_merge_cache.py / pod_merge_cache_ext.py L10-13
    try:
        with zipfile.ZipFile(path) as z: raw = z.read(z.namelist()[0])
        return pd.read_csv(io.BytesIO(raw), header=0 if raw[:1].isalpha() else None).iloc[:, :11]
    except Exception: return None

def build(sym):
    files = [f"{E['AX_PREV_DIR']}/{sym}/{E['AX_PREV_DAY']}.zip", f"{E['AX_DAY_DIR']}/{sym}/{E['AX_DAY']}.zip"]
    used = [f for f in files if os.path.exists(f)]
    ks = []
    for f in used:
        d = read_zip(f)
        if d is None or len(d) == 0: continue
        d.columns = ['open_time','o','h','l','c','v','close_time','qv','cnt','tbv','tbqv'][:d.shape[1]]
        ks.append(d)
    if not ks: return sym, None, used, None
    k = pd.concat(ks)
    k['ts'] = pd.to_datetime(k.open_time.astype(np.int64), unit='ms') + pd.Timedelta('5min')
    k = k.drop_duplicates('ts').set_index('ts').sort_index().reindex(IDX)
    A = np.full((len(IDX), 7), np.nan, np.float16)                      # math VERBATIM (same 7 lines as the merge / holefix builders)
    A[:,0] = np.clip(k.c.pct_change(fill_method=None), -0.3, 0.3)
    A[:,1] = np.clip((k.h-k.l)/k.c, 0, 0.5)
    A[:,2] = ((k.c-k.l)/(k.h-k.l)).clip(0,1)
    A[:,3] = np.log1p(k.qv).clip(0, 25); A[:,4] = np.log1p(k.cnt).clip(0, 20)
    A[:,5] = np.log((k.qv/k.cnt.replace(0,np.nan))).clip(-5, 15)
    A[:,6] = (k.tbqv/k.qv).clip(0,1)
    has_bar = k.c.notna().to_numpy()                                     # official kline row present at this close time
    return sym, A[RSEL], used, has_bar[RSEL]

t0 = time.time()
res = {}
with ProcessPoolExecutor(max_workers=16) as ex:
    for s, A, used, hb in ex.map(build, SY): res[s] = (A, used, hb)
unverified = sorted({f for (_, used, _) in res.values() for f in used if f not in OKZIP})
if unverified:
    json.dump({"VERDICT": "FAIL_unverified_zips", "unverified": unverified[:50], "n": len(unverified)}, open(E["AX_RECEIPT"], "w"), indent=1)
    print("AX13_FAIL unverified zips", len(unverified), unverified[:5], flush=True); sys.exit(3)
zip_sha_mismatch = [f for (_, used, _) in res.values() for f in used if sha(f) != OKZIP[f]]
assert not zip_sha_mismatch, ("zip changed since checksum verification", zip_sha_mismatch[:5])
NR = HI - LO + 1; NW = len(SY)
NEW = np.full((NR, NW, 7), np.nan, np.float16); HASBAR = np.zeros((NR, NW), bool)
for j, s in enumerate(SY):
    A, used, hb = res[s]
    if A is not None: NEW[:, j, :] = A; HASBAR[:, j] = hb
DATA = Z["data"]; OLD = np.array(DATA[LO:HI + 1])
# ---- R2 per-channel comparison
chs = [str(c) for c in Z["ch"]]; R2 = {}
for c in range(7):
    a, b = OLD[:, :, c], NEW[:, :, c]; fa, fb = np.isfinite(a), np.isfinite(b); both = fa & fb
    R2[chs[c]] = {"cells": int(a.size), "both_finite": int(both.sum()), "bitwise_equal_both_finite": int((a[both].view(np.uint16) == b[both].view(np.uint16)).sum()),
                  "x0918_finite_official_nan": int((fa & ~fb).sum()), "official_finite_x0918_nan": int((~fa & fb).sum()),
                  "maxabs_both_finite": float(np.abs(a[both].astype(np.float32) - b[both].astype(np.float32)).max()) if both.any() else 0.0}
identical = all(v["both_finite"] == v["bitwise_equal_both_finite"] and v["x0918_finite_official_nan"] == 0 and v["official_finite_x0918_nan"] == 0 for v in R2.values())
# ---- R3 hole cells of the replaced range and their official evidence
H = np.load(E["AX_HOLES"], allow_pickle=True); hr = H["row"].astype(np.int64); hc = H["col"].astype(np.int64)
inr = (hr >= LO) & (hr <= HI)
ev = np.zeros(len(hr), bool); ev[inr] = HASBAR[hr[inr] - LO, hc[inr]]
rem = inr & ev; keep = ~rem
# ---- R4 corrected data
CORR = OLD.copy(); sel = HASBAR[:, :, None] & np.ones((1, 1, 7), bool); CORR[sel] = NEW[sel]
corr_equal_old = bool(np.array_equal(CORR.view(np.uint16), OLD.view(np.uint16)))
if identical and corr_equal_old:
    shutil.copyfile(E["AX_CACHE"], E["AX_OUT_CACHE"] + ".part"); os.replace(E["AX_OUT_CACHE"] + ".part", E["AX_OUT_CACHE"])
    cache_mode = "BYTE_COPY_of_x0918 (official rebuild of the replaced range is bitwise identical to the hole-fill, NaN pattern included)"
else:
    FULL = np.array(DATA); FULL[LO:HI + 1] = CORR
    tmp = E["AX_OUT_CACHE"][:-4] + ".tmp.npz"; np.savez_compressed(tmp, ts=CTS, symbols=Z["symbols"], ch=Z["ch"], data=FULL); os.replace(tmp, E["AX_OUT_CACHE"])
    cache_mode = "NEW_NPZ (replaced cells differ from the hole-fill; see R2)"
# ---- R5 hole-cell file
runs = [tuple(map(int, r)) for r in H["fill_runs"]]; neigh = [tuple(map(int, r)) for r in H["neigh_rows"]]
assert len(runs) == len(neigh)
runs2, neigh2, dropped = [], [], []
for (a, b), nb in zip(runs, neigh):
    m = keep & (hr >= a) & (hr <= b)
    if m.any(): runs2.append((a, b)); neigh2.append(nb)
    else: dropped.append({"fill_run": [a, b], "neigh_rows": list(nb), "ts": [U(CTS[a]), U(CTS[b])]})
prov = (f"x0918r hole cells = {os.path.basename(E['AX_HOLES'])} minus {int(rem.sum())} cells of rows [{LO},{HI}] ({U(CTS[LO])}..{U(CTS[HI])}) whose bar is present in the "
        f"checksum-verified official daily archive {E['AX_DAY']} (device ax13_d31_replace.py); cells without an official bar stay listed")
out = {k: H[k] for k in H.files}
out.update(row=H["row"][keep], col=H["col"][keep], ts=H["ts"][keep], fill_runs=np.array(runs2, np.int64), neigh_rows=np.array(neigh2, np.int64),
           removed_row=H["row"][rem], removed_col=H["col"][rem], provenance=np.array(prov), source_holes_sha256=np.array(sha(E["AX_HOLES"])))
tmp = E["AX_OUT_HOLES"][:-4] + ".tmp.npz"; np.savez(tmp, **out); os.replace(tmp, E["AX_OUT_HOLES"])
back = np.load(E["AX_OUT_HOLES"], allow_pickle=True)
assert np.array_equal(back["row"], H["row"][keep]) and np.array_equal(back["col"], H["col"][keep]) and [str(s) for s in back["symbols"]] == SY
# ---- per-symbol evidence summary of the replaced run
sym_hole = np.zeros(NW, np.int64); sym_ev = np.zeros(NW, np.int64)
np.add.at(sym_hole, hc[inr], 1); np.add.at(sym_ev, hc[rem], 1)
rep = {"device": "ax13_d31_replace.py", "self_sha256": sha(os.path.abspath(__file__)), "env": E, "cache_sha256": sha(E["AX_CACHE"]), "holes_sha256": sha(E["AX_HOLES"]),
       "replaced_range": {"rows": [LO, HI], "ts": [U(CTS[LO]), U(CTS[HI])], "n_rows": NR},
       "zips_read": sum(len(u) for (_, u, _) in res.values()), "zips_all_checksum_verified": True, "symbols_with_official_bars": int(HASBAR.any(0).sum()),
       "official_bars_in_range": int(HASBAR.sum()), "R2_per_channel": R2, "R2_bitwise_identical": bool(identical),
       "R3_hole_cells_in_range": int(inr.sum()), "R3_hole_cells_with_official_bar_removed": int(rem.sum()), "R3_hole_cells_without_official_bar_kept": int((inr & ~ev).sum()),
       "R3_symbols_in_range_hole_list": int((sym_hole > 0).sum()), "R3_symbols_fully_evidenced": int(((sym_hole > 0) & (sym_ev == sym_hole)).sum()),
       "R3_cells_kept_first": [(U(CTS[r]), SY[c]) for r, c in zip(hr[inr & ~ev][:30], hc[inr & ~ev][:30])],
       "official_bars_not_in_hole_list": int(HASBAR.sum() - rem.sum()),
       "R4_cache_mode": cache_mode, "out_cache": E["AX_OUT_CACHE"], "out_cache_sha256": sha(E["AX_OUT_CACHE"]),
       "R5_holes": {"n_cells_before": int(len(hr)), "n_cells_after": int(keep.sum()), "fill_runs_after": runs2, "neigh_rows_after": neigh2, "dropped_runs": dropped,
                    "out": E["AX_OUT_HOLES"], "out_sha256": sha(E["AX_OUT_HOLES"]), "provenance": prov},
       "wall_s": round(time.time() - t0, 1), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(rep, open(E["AX_RECEIPT"], "w"), indent=1, default=str)
print("AX13_DONE", json.dumps({k: rep[k] for k in ("replaced_range", "symbols_with_official_bars", "official_bars_in_range", "R2_bitwise_identical", "R3_hole_cells_in_range",
      "R3_hole_cells_with_official_bar_removed", "R3_hole_cells_without_official_bar_kept", "R4_cache_mode", "out_cache_sha256")}, default=str), flush=True)
print("R5", json.dumps(rep["R5_holes"], default=str)[:800], flush=True)
