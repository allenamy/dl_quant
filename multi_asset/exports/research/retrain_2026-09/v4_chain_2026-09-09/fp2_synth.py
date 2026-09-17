"""fp2_synth.py — synthetic 5m cache + panels for the FP2 device tests (same generator as tests_fp2_builders_v2.py; factored for reuse)."""
import os, numpy as np
def make(TMP, seed=20260917, TT=8000, NW=80):
    rng = np.random.default_rng(seed); TS0 = 1640995200; CTS = TS0 + 300 * np.arange(TT, dtype=np.int64)
    syms = ["BTCUSDT"] + ["S%02dUSDT" % i for i in range(1, NW)]
    ret = rng.normal(0, 0.005, (TT, NW)).astype(np.float32); ret[:1000, NW - 1] = np.nan
    D = np.empty((TT, NW, 7), np.float16)
    D[:, :, 0] = ret; D[:, :, 1] = rng.uniform(0, 0.02, (TT, NW)); D[:, :, 2] = rng.uniform(0, 1, (TT, NW)); D[:, :, 3] = rng.normal(10, 1, (TT, NW))
    D[:, :, 4] = rng.normal(5, 0.5, (TT, NW)); D[:, :, 5] = rng.normal(5, 1, (TT, NW)); D[:, :, 6] = rng.uniform(0, 1, (TT, NW)); D[:1000, NW - 1, :] = np.nan
    CH = np.array(["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"])
    CACHE = f"{TMP}/cache.npz"; np.savez(CACHE, ts=CTS, symbols=np.array(syms), ch=CH, data=D)
    grid = CTS[CTS % 14400 == 0]; nP = len(grid); gi = np.where(CTS % 14400 == 0)[0]
    r64 = np.where(np.isfinite(D[:, :, 0].astype(np.float64)), D[:, :, 0].astype(np.float64), 0.0)
    Y4 = np.full((nP, NW), np.nan, np.float32)
    for k, e in enumerate(gi):
        if e + 48 <= TT: Y4[k] = r64[e:e + 48].sum(0)
    KPANEL = f"{TMP}/panel_king.npz"; np.savez(KPANEL, ts=grid, f_fund_ema=rng.normal(0, 1e-4, (nP, NW)).astype(np.float32), f_fund_now=rng.normal(0, 1e-4, (nP, NW)).astype(np.float32))
    DPANEL = f"{TMP}/panel_dl.npz"
    np.savez(DPANEL, ts=grid, symbols=np.array(syms), Y4=Y4, **{k: rng.normal(0, 1, (nP, NW)).astype(np.float32) for k in ("f_rev_4h", "f_rev_24h", "f_vol_7d", "f_range_24h", "f_mom_7d", "f_fund_ema")})
    os.makedirs(f"{TMP}/shim", exist_ok=True)
    open(f"{TMP}/shim/zload.py", "w").write(
        "import zipfile, io\nimport numpy as np\nclass _Z(dict):\n    @property\n    def files(self): return list(self.keys())\n"
        "def zload(path, **kw):\n    z = zipfile.ZipFile(path); out = _Z()\n    for n in z.namelist():\n        key = n[:-4] if n.endswith('.npy') else n\n"
        "        with z.open(n) as f: out[key] = np.lib.format.read_array(io.BytesIO(f.read()), allow_pickle=True)\n    return out\n")
    RAWP = f"{TMP}/raw_patch.npz"; np.savez(RAWP, row=np.zeros(0, np.int64), col=np.zeros(0, np.int64), raw32=np.zeros(0, np.float32))
    HOLE = f"{TMP}/holefix2_cells.npz"; np.savez(HOLE, row=np.zeros(0, np.int32), col=np.zeros(0, np.int32), ts=np.zeros(0, np.int64), fill_runs=np.zeros((0, 2), np.int64), neigh_rows=np.zeros((0, 2), np.int64), symbols=np.array(syms), lost_rows=np.zeros(0, np.int32), lost_cols=np.zeros(0, np.int32))
    return dict(CACHE=CACHE, KPANEL=KPANEL, DPANEL=DPANEL, RAWP=RAWP, HOLE=HOLE, grid=grid, syms=syms, NW=NW, nP=nP, shim=f"{TMP}/shim")
