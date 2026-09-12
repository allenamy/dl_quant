"""r16: build w10_r16.py = pinned w10_sleeve.py (sha256 b88e35a4...) + {XMODE, XNULL, AUX16}.
Each replacement asserted to fire exactly once. XMODE="" returns the deployed sm object untouched,
so the DEFAULT path is bitwise-unchanged in rec/W (GATE P proves it empirically on both seeds).
Usage: python mk_device16.py <parent w10_sleeve.py> <out w10_r16.py>"""
import hashlib, sys
PARENT_SHA = "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650"
PREREG_SHA = "68bc4fdb7f619dbb9ca10fc868f86b1f31f227029f7b58aead309f4620ab2b0c"
src, dst = sys.argv[1], sys.argv[2]
s = open(src, "rb").read()
assert hashlib.sha256(s).hexdigest() == PARENT_SHA, hashlib.sha256(s).hexdigest()
s = s.decode()
def sub1(t, old, new):
    assert t.count(old) == 1, (t.count(old), old[:80]); return t.replace(old, new)

# 1. knobs (+ prereg assertion at import)
s = sub1(s, 'SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)\n',
 'XMODE = os.environ.get("XMODE", ""); assert XMODE in ("", "X0", "X1", "X2", "X3", "X4", "X5"), XMODE   # r16 asymmetric band/EMA exemption at the chain band step; "" = deployed, bitwise-neutral\n'
 'XNULL = int(os.environ.get("XNULL", "0")); assert XNULL in (0, 1, 2, 3), XNULL   # r16 matched random-exemption null, default_rng([4242, XNULL]) reseeded per run()\n'
 'assert not (XNULL and not XMODE), "XNULL requires XMODE"\n'
 'AUX16 = int(os.environ.get("AUX16", "0")); assert AUX16 in (0, 1)   # r16 per-anchor per-chain mechanism instrument. ADDITIVE, never read by the book.\n'
 'import hashlib as _hl16\n'
 'PREREG16_SHA = "' + PREREG_SHA + '"\n'
 'PREREG16_PATH = os.environ.get("PREREG16_PATH", "/workspace/uplift_2026-09-11/r16_asym_band/PREREG_r16_asym_band_2026-09-12.md")\n'
 'assert _hl16.sha256(open(PREREG16_PATH, "rb").read()).hexdigest() == PREREG16_SHA, "PREREG r16 sha mismatch"\n'
 'SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)\n')

# 2. self-report in config
s = sub1(s, '"SEATNET": SEATNET,', '"XMODE": XMODE, "XNULL": XNULL, "AUX16": AUX16, "SEATNET": SEATNET,')
s = sub1(s, '_CFG["UPLIFT"]["self_sha256"] = _CFG["HEALTH"]["device_sha256"]\n',
 '_CFG["UPLIFT"]["self_sha256"] = _CFG["HEALTH"]["device_sha256"]\n'
 '_CFG["R16"] = {"device": "w10_r16.py = w10_sleeve.py (sha256 ' + PARENT_SHA + ') + {XMODE, XNULL, AUX16}; XMODE=\'\' => bitwise-unchanged rec/W (GATE P)", "parent_sha256": "' + PARENT_SHA + '", "prereg_sha256": PREREG16_SHA, "XMODE": XMODE, "XNULL": XNULL, "AUX16": AUX16}\n')

# 3. the exemption operator + matched null (module level, before run())
s = sub1(s, 'W3FC = None\ndef run(SLOW, LRa, pos, depth, need, cool, look=900):\n',
 'W3FC = None\n'
 '_X16_ALPHA = 0.1; _X16_BAND = 2.5e-4; _X16_AEXIT = 0.3   # same literals as the deployed chain step (L253-254 / L293-295)\n'
 '_X16_COLS = ["n_gap", "n_DR", "n_DR_banded", "n_RI_banded", "n_exempt", "n_exempt_moved", "exempt_abs_dw",\n'
 '             "n_zt", "sum_abs_sm_zt", "n_zt_stalled", "n_zt_m", "sum_abs_sm_zt_m", "n_flip", "n_flip_banded"]\n'
 '_X16_ZERO = tuple(0.0 for _ in _X16_COLS)\n'
 'def _x16_matched(T, pool, mag, rng, nb=4):\n'
 '    """PREREG r16 §5: same COUNT as T, same |mag| distribution (pool quartile strata), drawn from pool. T subset of pool."""\n'
 '    k = int(T.sum()); P = np.where(pool)[0]\n'
 '    if k == 0: return np.zeros(len(T), bool)\n'
 '    if k >= len(P): return pool.copy()\n'
 '    edges = np.quantile(mag[P], [0.25, 0.5, 0.75])\n'
 '    bP = np.searchsorted(edges, mag[P], side="right"); bT = np.searchsorted(edges, mag[T], side="right")\n'
 '    out = np.zeros(len(T), bool)\n'
 '    for bb in range(nb):\n'
 '        cand = P[bP == bb]; kb = int((bT == bb).sum())\n'
 '        if kb == 0: continue\n'
 '        if kb >= len(cand): out[cand] = True; continue\n'
 '        out[rng.choice(cand, size=kb, replace=False)] = True\n'
 '    return out\n'
 'def _x16_apply(tgt, H, sm_dep, m, rng):\n'
 '    """PREREG r16 §2-3. tgt/H = THIS chain\'s target and pre-step EMA state; sm_dep = the DEPLOYED result of\n'
 '    EMA 0.1 + band 2.5e-4 (SKIP form). XMODE=="" => sm_dep returned untouched (bitwise-neutral); counters only."""\n'
 '    gap = tgt - H; nz = gap != 0.0; step = _X16_ALPHA * gap\n'
 '    banded = nz & (np.abs(step) < _X16_BAND)\n'
 '    DR = nz & ((tgt * H < 0.0) | (np.abs(tgt) < np.abs(H)))\n'
 '    RI = nz & ~DR; FLIP = nz & (tgt * H < 0.0); ZT = (tgt == 0.0) & (H != 0.0)\n'
 '    inm = np.zeros(len(tgt), bool); inm[m] = True\n'
 '    if XMODE == "":\n'
 '        sm = sm_dep; ex = np.zeros(len(tgt), bool); moved = ex; exdw = 0.0\n'
 '    else:\n'
 '        if XMODE == "X0":   T = DR & banded; pool = banded; mag = np.abs(step)\n'
 '        elif XMODE == "X4": T = RI & banded; pool = banded; mag = np.abs(step)\n'
 '        elif XMODE == "X2": T = FLIP; pool = nz; mag = np.abs(gap)\n'
 '        elif XMODE == "X5": T = ZT; pool = nz; mag = np.abs(gap)\n'
 '        else:               T = DR; pool = nz; mag = np.abs(gap)      # X1, X3\n'
 '        ex = T if XNULL == 0 else _x16_matched(T, pool, mag, rng)\n'
 '        if XMODE in ("X0", "X4"): new = H + step\n'
 '        elif XMODE == "X3":       new = H + _X16_AEXIT * gap\n'
 '        else:                     new = tgt\n'
 '        sm = np.where(ex, new, sm_dep)\n'
 '        moved = ex & (sm != H); exdw = float(np.abs(sm[ex] - sm_dep[ex]).sum())\n'
 '    aux = (float(nz.sum()), float(DR.sum()), float((DR & banded).sum()), float((RI & banded).sum()), float(ex.sum()),\n'
 '           float(moved.sum()), exdw, float(ZT.sum()), float(np.abs(sm[ZT]).sum()), float((ZT & (sm == H)).sum()),\n'
 '           float((ZT & inm).sum()), float(np.abs(sm[ZT & inm]).sum()), float(FLIP.sum()), float((FLIP & banded).sum()))\n'
 '    return sm, aux\n'
 'def run(SLOW, LRa, pos, depth, need, cool, look=900):\n')

# 4. per-run state: rng reseeded, aux accumulator
s = sub1(s, '    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []\n',
 '    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []\n'
 '    _x16_rng = np.random.default_rng([4242, XNULL]) if XNULL else None; _R16A = []   # r16\n')

# 5. king chain: after the deployed band step
s = sub1(s,
 '        sm = H + 0.1 * (tgt - H); trade = sm - H\n'
 '        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H\n',
 '        sm = H + 0.1 * (tgt - H); trade = sm - H\n'
 '        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H\n'
 '        _x16k = _X16_ZERO; _x16f = _X16_ZERO\n'
 '        if XMODE or AUX16:\n'
 '            sm, _x16k = _x16_apply(tgt, H, sm, m, _x16_rng); trade = sm - H\n')

# 6. F10 chain: after the deployed band step
s = sub1(s,
 '                _smf = HF + 0.1 * (_tgtf - HF)\n'
 '                _trf = _smf - HF\n'
 '                _smf = np.where(np.abs(_trf) < 2.5e-4, HF, _smf)\n',
 '                _smf = HF + 0.1 * (_tgtf - HF)\n'
 '                _trf = _smf - HF\n'
 '                _smf = np.where(np.abs(_trf) < 2.5e-4, HF, _smf)\n'
 '                if XMODE or AUX16:\n'
 '                    _smf, _x16f = _x16_apply(_tgtf, HF, _smf, m, _x16_rng)\n')

# 7. collect aux right before rec.append (trr defined at L321)
s = sub1(s, '        netlong = float(sm.sum() / max(np.abs(sm).sum(), 1e-9))\n',
 '        if AUX16:\n'
 '            _R16A.append(tuple(_x16k) + tuple(_x16f) + (float(np.abs(trr).sum()), float(np.abs(trr[m]).sum())))\n'
 '        netlong = float(sm.sum() / max(np.abs(sm).sum(), 1e-9))\n')
s = sub1(s, '    return np.array(rec), np.stack(WS), ((np.array(_SG)',
 '    if AUX16:\n'
 '        globals()["_R16_LAST"] = np.array(_R16A)\n'
 '    return np.array(rec), np.stack(WS), ((np.array(_SG)')
s = sub1(s, '    save[f"{nm}_rec"] = R\n',
 '    save[f"{nm}_rec"] = R\n'
 '    if AUX16:\n'
 '        save[f"{nm}_R16A"] = globals()["_R16_LAST"]\n'
 '        save[f"{nm}_R16A_cols"] = np.array(["k_" + c for c in _X16_COLS] + ["f_" + c for c in _X16_COLS] + ["turn_ex_all", "turn_ex_member"])\n')

open(dst, "w").write(s)
print("w10_r16.py sha256", hashlib.sha256(s.encode()).hexdigest())
