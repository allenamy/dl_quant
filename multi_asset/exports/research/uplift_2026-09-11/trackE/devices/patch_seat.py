import re, hashlib, json, sys
P = "/workspace/uplift_2026-09-11/w10_seat.py"
s = open(P).read()
orig = s

# 1) PD override (purely additive; default unchanged)
a = 'B = "pod_backup_2026-08-21"; PD = "probe_artifacts"'
assert s.count(a) == 1
s = s.replace(a, a + '\nPD = os.environ.get("PD_OUT", PD)   # TRACK E: artifact dir override (default unchanged)')

# 2) new knobs after WRULE line
a = 'WRULE = os.environ.get("WRULE", "msharpe")            # msharpe | eq | iv'
assert s.count(a) == 1
s = s.replace(a, a + '''
# ★ TRACK E (PREREG_trackE_legweight_phi_2026-09-11 sha 79acb030): purely additive seat-rule knobs.
#   SEATRULE="" (default) => every code path below is skipped and the device is bitwise the original.
SEATRULE = os.environ.get("SEATRULE", ""); assert SEATRULE in ("", "rp", "book"), SEATRULE
SHRINK = float(os.environ.get("SHRINK", "0")); assert 0.0 <= SHRINK <= 1.0, SHRINK
SEATG_NPZ = os.environ.get("SEATG_NPZ")   # book-layer per-leg g series (ts, g_king, g_fund) for SEATRULE=book''')

# 3) record in _CFG
a = '"LOOK": LOOK, "WRULE": WRULE,'
assert s.count(a) == 1
s = s.replace(a, '"LOOK": LOOK, "WRULE": WRULE, "SEATRULE": SEATRULE, "SHRINK": SHRINK, "SEATG_NPZ": SEATG_NPZ,')

# 4) w3_at body: rp / book / shrink
a = """        r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
        if WRULE == "iv":
            iv = 1.0 / (r.std(1) + 1e-9)
            return iv / iv.sum()
        shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
        w_ = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)
        if LEGS != "111":
            msk = np.array([1.0 if c == "1" else 0.0 for c in LEGS])
            w_ = w_ * msk
            w_ = w_ / w_.sum() if w_.sum() > 1e-12 else msk / max(msk.sum(), 1.0)
        return w_"""
assert s.count(a) == 1
b = """        r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
        if WRULE == "iv":
            iv = 1.0 / (r.std(1) + 1e-9)
            return iv / iv.sum()
        if SEATRULE == "book":   # TRACK E: seat from the BOOK-layer single-leg g series (after FTRIM/band/EMA/reshape/cost/carry)
            r = np.stack([SEATG_ARR[0][sl], SEATG_ARR[1][sl], SEATG_ARR[2][sl]])
        if SEATRULE == "rp":     # TRACK E: risk parity ON THE SURVIVING LEGS (the stock WRULE=iv branch ignores the LEGS mask)
            _mk = np.array([1.0 if c == "1" else 0.0 for c in LEGS])
            _iv = (1.0 / (r.std(1) + 1e-9)) * _mk
            return _iv / _iv.sum() if _iv.sum() > 1e-12 else _mk / max(_mk.sum(), 1.0)
        shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
        w_ = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)
        if LEGS != "111":
            msk = np.array([1.0 if c == "1" else 0.0 for c in LEGS])
            w_ = w_ * msk
            w_ = w_ / w_.sum() if w_.sum() > 1e-12 else msk / max(msk.sum(), 1.0)
        if SHRINK > 0:           # TRACK E: shrink toward equal weight over the surviving legs
            _mk = np.array([1.0 if c == "1" else 0.0 for c in LEGS])
            _we = _mk / max(_mk.sum(), 1.0)
            w_ = (1.0 - SHRINK) * w_ + SHRINK * _we
        return w_"""
s = s.replace(a, b)

# 5) build SEATG_ARR right after legs() is called
a = 'LRa, pos = legs(SLOW); print("legs done", round(time.time() - t0, 1), "s", flush=True)'
assert s.count(a) == 1
b = a + '''
SEATG_ARR = None
if SEATRULE == "book":   # TRACK E: align the book-layer leg g series onto legs()'s p-space (strictly causal: w3_at reads only p-look..p)
    _sg = np.load(SEATG_NPZ); _sts = _sg["ts"].astype(np.int64)
    _n = len(pos); SEATG_ARR = [np.zeros(_n), np.zeros(_n), np.zeros(_n)]
    _map = {int(t): k for k, t in enumerate(_sts)}
    _fill = 0
    for _i, _p in pos.items():
        _k = _map.get(int(E_ts[_i]))
        if _k is None: _fill += 1; continue
        SEATG_ARR[0][_p] = float(_sg["g_king"][_k]); SEATG_ARR[2][_p] = float(_sg["g_fund"][_k])
    print(f"SEATG loaded {SEATG_NPZ}: n_pos {_n}, filled-with-0 {_fill}", flush=True)'''
s = s.replace(a, b)

assert s != orig
open(P, "w").write(s)
print("patched", hashlib.sha256(s.encode()).hexdigest())
