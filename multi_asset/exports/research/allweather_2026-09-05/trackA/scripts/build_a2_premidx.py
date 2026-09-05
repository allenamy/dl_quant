"""build_a2_premidx.py — Track A family A2 (premium index 5m path), PREREG_allweather_programme_2026-09-05 §2 row A2 / §3 Track A.
Two stages (STAGE env):
  parse    : premiumIndexKlines monthly zips (/workspace/review_scratch/allweather_trackA/premidx/<S>/<S>-5m-YYYY-MM.zip, 2022-01..2026-08)
             -> premidx_5m.npy (NS=829, T=490753) float32 premium-index CLOSE on the ext-cache 5m grid (row ts = bar CLOSE time = open_time+5min,
             identical to /workspace/data/dlnative_5m_wide829_f16_ext.npz ts axis, asserted), written row by row into a memmap.
             QUOTA MODE (team-lead 2026-09-05 15:1xZ): every zip is sha256-manifested (premidx/a2_manifest.jsonl) and DELETED right after its
             symbol row is written; .404 sentinels are listed in the manifest and deleted too. Write probe (1 MB) before start and every 100 symbols.
             Also premidx_5m_cov.json (per-symbol first/last bar, n bars).
  features : anchor-level features for META anchors (E_ts). Right edge row R = idx(E) - 1 + SHIFT, i.e. with SHIFT=0 the last bar used CLOSES at
             E - 5 min (one bar behind the panel's own edge, PREREG "+1 bar 时移"); every bar used has close time <= E + (SHIFT-1)*5min (asserted).
             SHIFT != 0 only for the lead/lag guard (SHIFT >= 2 deliberately looks into the y4 window).
    prem_accr  : mean premium over bars closing in (S, R] where S = last settlement (00/08/16Z) strictly < ts(R) (count >= 50% of bars in the window, >= 1)
    prem_sl1h  : mean(prem over (R-12, R]) - mean(prem over (R-24, R-12])       (>= 80% coverage in each block)
    prem_sl4h  : mean(prem over (R-48, R]) - mean(prem over (R-96, R-48])       (>= 80% coverage in each block)
    prem_gap   : mean(prem over (R-3, R]) - f_fund_now(panel row ts == E, symbol)   (panel f_fund_now = last settled rate at E, already a baseline column)
   Output npz: F (nA, 829, 4) float32 raw values (the gate device rank-transforms within members; missing = NaN), names, E_ts, avail (nA,829) bool
   = premium close finite at R (source availability, for the hit-rate guard), shift.
env: STAGE ROOT CACHE_IN META_IN PANEL_IN SHIFT OUT NPROC
"""
import os, io, sys, glob, json, time, zipfile, hashlib
import numpy as np
ROOT = os.environ.get("ROOT", "/workspace/review_scratch/allweather_trackA")
STAGE = os.environ.get("STAGE", "features")
SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
sys.path.insert(0, "/workspace")
from zload import zload
CACHE_IN = os.environ.get("CACHE_IN", "/workspace/data/dlnative_5m_wide829_f16_ext.npz")
Z = zload(CACHE_IN, allow_pickle=True)
CTS = Z["ts"].astype(np.int64); SYMS = [str(s) for s in Z["symbols"]]; NS = len(SYMS); T = len(CTS)
assert NS == 829 and np.all(np.diff(CTS) == 300), (NS, T)
T0 = int(CTS[0])
del Z
PREM_NPY = f"{ROOT}/features/premidx_5m.npy"

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()
def write_probe():
    p = f"{ROOT}/logs/_probe_a2"
    try:
        with open(p, "wb") as f: f.write(b"x" * (1 << 20)); f.flush(); os.fsync(f.fileno())
        os.remove(p); return True
    except Exception as e:
        print(f"WRITE_PROBE_FAIL {e!r}", flush=True); return False

def parse_sym(s):
    import pandas as pd
    out = np.full(T, np.nan, np.float32); n = 0; first = None; last = None; man = []
    for f in sorted(glob.glob(f"{ROOT}/premidx/{s}/{s}-5m-*.zip")):
        try:
            sha = sha256_file(f); nb = os.path.getsize(f)
            with zipfile.ZipFile(f) as z: raw = z.read(z.namelist()[0])
            d = pd.read_csv(io.BytesIO(raw), header=0 if raw[:1].isalpha() else None, usecols=[0, 4])
        except Exception as e:
            man.append({"sym": s, "file": os.path.basename(f), "status": f"BAD {e!r}"}); print(f"BAD_ZIP {f} {e!r}", flush=True); continue
        ot = d.iloc[:, 0].to_numpy(np.int64); c = d.iloc[:, 1].to_numpy(np.float64)
        ot = np.where(ot > 10**14, ot // 1000000, ot // 1000)
        idx = (ot + 300 - T0) // 300
        ok = (idx >= 0) & (idx < T) & (ot % 300 == 0)
        out[idx[ok]] = c[ok]; n += int(ok.sum())
        man.append({"sym": s, "file": os.path.basename(f), "sha256": sha, "bytes": nb, "n_rows": int(len(ot)), "n_on_grid": int(ok.sum())})
        if ok.any():
            first = int(ot[ok].min()) if first is None else min(first, int(ot[ok].min()))
            last = int(ot[ok].max()) if last is None else max(last, int(ot[ok].max()))
    for f in sorted(glob.glob(f"{ROOT}/premidx/{s}/*.404")): man.append({"sym": s, "file": os.path.basename(f), "status": 404})
    return s, out, {"n": n, "first": first, "last": last, "n_zips": sum(1 for m in man if "sha256" in m), "n_404": sum(1 for m in man if m.get("status") == 404)}, man

if STAGE == "parse":
    from concurrent.futures import ProcessPoolExecutor
    NPROC = int(os.environ.get("NPROC", "16")); DELETE = os.environ.get("DELETE_ZIPS", "1") == "1"
    print(f"CONFIG {json.dumps({'self_sha256': SELF, 'stage': STAGE, 'CACHE_IN': CACHE_IN, 'NPROC': NPROC, 'T': T, 'NS': NS, 'DELETE_ZIPS': DELETE})}", flush=True)
    assert write_probe(), "write probe failed before start"
    P = np.lib.format.open_memmap(PREM_NPY, mode="w+", dtype=np.float32, shape=(NS, T))
    cov = {}; t0 = time.time(); freed = 0; MAN = open(f"{ROOT}/premidx/a2_manifest.jsonl", "a")
    with ProcessPoolExecutor(max_workers=NPROC) as ex:
        for k, (s, arr, c, man) in enumerate(ex.map(parse_sym, SYMS)):
            j = SYMS.index(s); P[j] = arr; P.flush(); cov[s] = c
            for m in man: MAN.write(json.dumps(m) + "\n")
            MAN.flush()
            if DELETE:
                for f in glob.glob(f"{ROOT}/premidx/{s}/*"): freed += os.path.getsize(f); os.remove(f)
                os.rmdir(f"{ROOT}/premidx/{s}")
            if (k + 1) % 100 == 0:
                print(f"parsed {k+1}/{NS} ({time.time()-t0:.0f}s) freed_MB {freed/1e6:.0f}", flush=True)
                if not write_probe(): print("HALT: write probe failed", flush=True); sys.exit(3)
    MAN.close(); P.flush(); del P
    json.dump({"self_sha256": SELF, "grid_T0": T0, "T": T, "coverage": cov, "freed_bytes": freed}, open(f"{ROOT}/features/premidx_5m_cov.json", "w"), indent=0)
    nsym = sum(1 for c in cov.values() if c["n"] > 0)
    P = np.load(PREM_NPY, mmap_mode="r")
    print(f"PARSE_DONE symbols_with_data {nsym}/{NS} finite_frac {np.isfinite(P).mean():.4f} zips {sum(c['n_zips'] for c in cov.values())} n404 {sum(c['n_404'] for c in cov.values())} freed_MB {freed/1e6:.0f} sha256 {sha256_file(PREM_NPY)[:16]}", flush=True)
    sys.exit(0)

# ---------------- features ----------------
META_IN = os.environ.get("META_IN", "/workspace/data/wide_fea_v2ext_meta.npz")
PANEL_IN = os.environ.get("PANEL_IN", "/workspace/data/wide_panel_4h_v2ext.npz")
SHIFT = int(os.environ.get("SHIFT", "0")); OUT = os.environ["OUT"]
MT = np.load(META_IN, allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); nA = len(E_ts)
PW = np.load(PANEL_IN, allow_pickle=True); assert [str(s) for s in PW["symbols"]] == SYMS
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}; FN = PW["f_fund_now"]
prow = np.array([pw_row.get(int(t), -1) for t in E_ts])   # META anchors before the panel's first row (2022-01-08..01-30, 30-day panel lookback) have no f_fund_now -> prem_gap NaN there
FNrow = np.where(prow[:, None] >= 0, FN[np.maximum(prow, 0)], np.nan); print(f"anchors_without_panel_row {(prow < 0).sum()}/{nA} (prem_gap NaN there)", flush=True)
Ei = (E_ts - T0) // 300; assert np.all(CTS[Ei] == E_ts)
R = Ei - 1 + SHIFT
assert np.all(CTS[R] <= E_ts + (SHIFT - 1) * 300), "right edge beyond convention"
if SHIFT <= 1: assert np.all(CTS[R] <= E_ts), "future row used"
NAMES = ["prem_accr", "prem_sl1h", "prem_sl4h", "prem_gap"]
print(f"CONFIG {json.dumps({'self_sha256': SELF, 'stage': STAGE, 'META_IN': META_IN, 'PANEL_IN': PANEL_IN, 'SHIFT': SHIFT, 'OUT': OUT, 'nA': nA, 'right_edge_minus_E_seconds': int((CTS[R] - E_ts).max())})}", flush=True)
P = np.load(PREM_NPY, mmap_mode="r")
# settlement S = last 00/08/16Z strictly < ts(R) (so a right edge closing exactly at a settlement takes the full 8h window)
tsR = CTS[R]; S = ((tsR - 1) // 28800) * 28800; Si = (S - T0) // 300   # row whose close time == S; window = rows (Si, R]
F = np.full((nA, NS, len(NAMES)), np.nan, np.float32); AV = np.zeros((nA, NS), bool)
def wmean(cs, cn, lo, hi, minfrac):
    """mean over rows (lo, hi] using cumsums cs/cn (length T+1); NaN if count < minfrac*(hi-lo) or < 1."""
    lo = np.maximum(lo, -1); n = cn[hi + 1] - cn[lo + 1]; need = np.maximum(1, np.ceil(minfrac * (hi - lo)))
    with np.errstate(invalid="ignore", divide="ignore"):
        m = (cs[hi + 1] - cs[lo + 1]) / n
    return np.where(n >= need, m, np.nan)
t0 = time.time()
for j in range(NS):
    x = np.asarray(P[j], np.float64); fin = np.isfinite(x)
    if not fin.any(): continue
    cs = np.concatenate([[0.0], np.cumsum(np.where(fin, x, 0.0))]); cn = np.concatenate([[0], np.cumsum(fin)])
    AV[:, j] = fin[R]
    F[:, j, 0] = wmean(cs, cn, Si, R, 0.5)
    F[:, j, 1] = wmean(cs, cn, R - 12, R, 0.8) - wmean(cs, cn, R - 24, R - 12, 0.8)
    F[:, j, 2] = wmean(cs, cn, R - 48, R, 0.8) - wmean(cs, cn, R - 96, R - 48, 0.8)
    F[:, j, 3] = wmean(cs, cn, R - 3, R, 0.8) - FNrow[:, j]
    if (j + 1) % 200 == 0: print(f"fea {j+1}/{NS} ({time.time()-t0:.0f}s)", flush=True)
np.savez_compressed(OUT, F=F, names=np.array(NAMES), E_ts=E_ts, avail=AV, shift=SHIFT, self_sha256=SELF)
print(f"A2_FEATURES_DONE {F.shape} finite_by_col {[round(float(np.isfinite(F[:, :, k]).mean()), 4) for k in range(len(NAMES))]} avail {AV.mean():.4f} sha256 {hashlib.sha256(open(OUT,'rb').read()).hexdigest()[:16]}", flush=True)
