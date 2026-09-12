#!/usr/bin/env python3
"""mk_r15_device.py — generate the DERIVED device w10_sleeve_r15.py from the PINNED replay device
by exact, once-only string replacements. PREREG_r15 §1 / §3: with every R15_* knob unset/default the
derived device must reproduce the pinned device BITWISE on rec and W (GATE P2/P3 prove it at run time).

Additions (and nothing else):
  R15_INSTR=1        per-anchor instrumentation: flagK/flagF (pre-trim z<0 & rn8<=FTRIM_TH per chain),
                     deep (rn8<=FTRIM_TH), kill (FTPOS zero set), member, smr (executor weights), c4 (fnow*4/iv);
                     legs(): per-leg SEATNET-subtraction quantity (rank-book 4h carry, bps/unit gross) recorded always
  R15_KILL_NPZ       alternative rn8 matrix (panel rows x 829) used ONLY in the FTPOS kill test (null injection)
  R15_KILL_TH        alternative threshold used ONLY in the FTPOS kill test (null dose; default = FTRIM_TH)
  R15_SEATC_NPZ      alternative 4h-carry matrix used ONLY in the SEATNET subtraction (null injection)
  R15_SEATC_SCALE    multiplier on the SEATNET subtraction (null dose; default 1.0)
  R15_SB=1           ARM-SB: seat inputs = each leg's own EMA-chain book net (pnl - carry - cost) per unit gross
"""
import hashlib, sys, difflib, os
PIN = sys.argv[1]; OUT = sys.argv[2]
PIN_SHA = "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650"
src = open(PIN, "rb").read()
assert hashlib.sha256(src).hexdigest() == PIN_SHA, ("PINNED DEVICE SHA MISMATCH", hashlib.sha256(src).hexdigest())
s = src.decode("utf-8")

def rep(old, new):
    global s
    n = s.count(old)
    assert n == 1, ("replacement anchor must occur exactly once", n, old[:80])
    s = s.replace(old, new)

# --- knobs
rep('SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)\n',
    'SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)\n'
    'R15_INSTR = int(os.environ.get("R15_INSTR", "0")); assert R15_INSTR in (0, 1)   # r15: instrumentation only (rec/W untouched)\n'
    'R15_KILL_NPZ = os.environ.get("R15_KILL_NPZ")   # r15 null: rn8 matrix used ONLY in the FTPOS kill test\n'
    'R15_KILL_TH = os.environ.get("R15_KILL_TH"); R15_KILL_TH = float(R15_KILL_TH) if R15_KILL_TH else None   # r15 null dose: kill threshold (default FTRIM_TH)\n'
    'R15_SEATC_NPZ = os.environ.get("R15_SEATC_NPZ")   # r15 null: 4h-carry matrix used ONLY in the SEATNET subtraction\n'
    'R15_SEATC_SCALE = float(os.environ.get("R15_SEATC_SCALE", "1.0"))   # r15 null dose: multiplier on the SEATNET subtraction\n'
    'R15_SB = int(os.environ.get("R15_SB", "0")); assert R15_SB in (0, 1)   # r15 ARM-SB: book-path-net seat (PREREG_r15 §2.1)\n')
rep('        "FPRED": os.environ.get("FPRED", "(default f10_V2MAIN_s{FSEED})")}\n',
    '        "FPRED": os.environ.get("FPRED", "(default f10_V2MAIN_s{FSEED})")}\n'
    '_CFG["R15"] = {"R15_INSTR": R15_INSTR, "R15_KILL_NPZ": R15_KILL_NPZ, "R15_KILL_TH": R15_KILL_TH, "R15_SEATC_NPZ": R15_SEATC_NPZ, "R15_SEATC_SCALE": R15_SEATC_SCALE, "R15_SB": R15_SB, "pinned_src_sha256": "' + PIN_SHA + '"}\n')
# --- null matrices
rep('_IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); _RN8 = np.nan_to_num(FN, nan=0.0) * (8.0 / _IVf)   # 8h 当量费率(全宽)\n',
    '_IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); _RN8 = np.nan_to_num(FN, nan=0.0) * (8.0 / _IVf)   # 8h 当量费率(全宽)\n'
    'R15_KILL = None; R15_C4 = None\n'
    'for _nm, _pth in (("KILL", R15_KILL_NPZ), ("C4", R15_SEATC_NPZ)):\n'
    '    if _pth:\n'
    '        _nz_ = np.load(_pth, allow_pickle=True)\n'
    '        assert [str(x) for x in _nz_["symbols"]] == [str(x) for x in PW["symbols"]], f"R15 {_nm} symbols mismatch"\n'
    '        assert np.array_equal(_nz_["ts"].astype(np.int64), PW["ts"].astype(np.int64)), f"R15 {_nm} ts mismatch"\n'
    '        _mat_ = np.asarray(_nz_["mat"], dtype=float); assert _mat_.shape == FN.shape and np.isfinite(_mat_).all(), f"R15 {_nm} shape/finite"\n'
    '        if _nm == "KILL": R15_KILL = _mat_\n'
    '        else: R15_C4 = _mat_\n'
    '        print(f"R15 {_nm} matrix injected: {_pth}", flush=True)\n')
# --- legs(): record the SEATNET-subtraction quantity for every leg; null injection; ARM-SB
rep('def legs(SLOW):\n    LR = {l: [] for l in ("king", "rev24", "fund", "f10")}; idx = []\n',
    'LEGC_R15 = None; LEGP_R15 = None\n'
    'def legs(SLOW):\n    LR = {l: [] for l in ("king", "rev24", "fund", "f10")}; idx = []\n'
    '    LC = {l: [] for l in LR}; LP = {l: [] for l in LR}   # r15: per-leg rank-book 4h carry (bps/unit gross) and price LR, recorded always\n'
    '    _HL = {l: np.zeros(NW) for l in LR}; _HRL = {l: np.zeros(NW) for l in LR}   # r15 ARM-SB: per-leg EMA book states\n')
rep('            _lr = float((z / g * _yy).sum() * 1e4) if g > 1e-9 else 0.0\n'
    '            if SEATNET and g > 1e-9:   # X1: 减去该腿单位 gross 书的 4h carry(多头付正费率), bps\n'
    '                _lr -= float((z / g * np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / _IVf[j, m])).sum() * 1e4)\n'
    '            LR[leg].append(_lr)\n',
    '            _lr = float((z / g * _yy).sum() * 1e4) if g > 1e-9 else 0.0\n'
    '            _lc = float((z / g * np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / _IVf[j, m])).sum() * 1e4) if g > 1e-9 else 0.0   # r15: the SEATNET quantity, recorded for every leg\n'
    '            LC[leg].append(_lc); LP[leg].append(_lr)\n'
    '            if SEATNET and g > 1e-9:   # X1: 减去该腿单位 gross 书的 4h carry(多头付正费率), bps\n'
    '                if R15_C4 is not None or R15_SEATC_SCALE != 1.0:   # r15 null path only\n'
    '                    _c4v = (R15_C4[j, m] if R15_C4 is not None else np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / _IVf[j, m]))\n'
    '                    _lr -= R15_SEATC_SCALE * float((z / g * _c4v).sum() * 1e4)\n'
    '                else:\n'
    '                    _lr -= _lc\n'
    '            if R15_SB and leg != "f10":   # r15 ARM-SB (PREREG_r15 §2.1): this leg\'s own EMA-chain book, executor caliber, net per unit gross\n'
    '                _qv = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48; _sel = ok & (_qv >= 2.5e5); _lr_sb = 0.0\n'
    '                if _sel.sum() >= 80:\n'
    '                    _w = np.where(_sel, z, 0.0); _w[_sel] -= _w[_sel].mean(); _gg = np.abs(_w).sum()\n'
    '                    if _gg > 1e-9:\n'
    '                        _w = _w / _gg; _cw = 2.5 / max(int(_sel.sum()), 1); _w = np.clip(_w, -_cw, _cw); _g2 = np.abs(_w).sum()\n'
    '                        if _g2 > 1e-9: _w = _w / _g2\n'
    '                        _tg = np.zeros(NW); _tg[m] = _w\n'
    '                        _s = _HL[leg] + 0.1 * (_tg - _HL[leg]); _s = np.where(np.abs(_s - _HL[leg]) < 2.5e-4, _HL[leg], _s)\n'
    '                        _ns = np.zeros(NW, bool); _ns[m[~_sel]] = True; _s = np.where(_ns, 0.0, _s)\n'
    '                        _sr = _s.copy(); _nzm = np.abs(_s) > 1e-12\n'
    '                        if _nzm.any():\n'
    '                            _sr[_nzm] -= _sr[_nzm].mean(); _g0 = np.abs(_s).sum(); _g1 = np.abs(_sr).sum()\n'
    '                            if _g1 > 1e-9: _sr *= _g0 / _g1\n'
    '                        _trr = _sr - _HRL[leg]; _gs = np.abs(_sr).sum()\n'
    '                        if _gs > 1e-9:\n'
    '                            _tr = tier_of(_qv); _ta = np.abs(_trr[m])\n'
    '                            _cb = sum(_ta[_tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))\n'
    '                            _pn = float((_sr[m] * _yy).sum() * 1e4); _ca = float((_sr[m] * np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / _IVf[j, m])).sum() * 1e4)\n'
    '                            _lr_sb = (_pn - _ca - _cb) / _gs\n'
    '                        _HL[leg] = _s; _HRL[leg] = _sr\n'
    '                _lr = _lr_sb\n'
    '            LR[leg].append(_lr)\n')
rep('    return {k: np.array(v) for k, v in LR.items()}, {int(i): p for p, i in enumerate(idx)}\n',
    '    global LEGC_R15, LEGP_R15; LEGC_R15 = {k: np.array(v) for k, v in LC.items()}; LEGP_R15 = {k: np.array(v) for k, v in LP.items()}\n'
    '    return {k: np.array(v) for k, v in LR.items()}, {int(i): p for p, i in enumerate(idx)}\n')
# --- run(): instrumentation + kill-test injection
rep('    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []\n',
    '    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []; _R15 = []\n')
rep('        if FTRIM == "zero":\n            z = np.where((z < 0) & (_fnp <= FTRIM_TH), 0.0, z)\n',
    '        _r15_flagK = (z < 0) & (_fnp <= FTRIM_TH); _r15_flagF = np.zeros(len(m), bool)   # r15: pre-trim flag, king chain\n'
    '        if FTRIM == "zero":\n            z = np.where((z < 0) & (_fnp <= FTRIM_TH), 0.0, z)\n')
rep('            if FTRIM == "zero":\n                _zf = np.where((_zf < 0) & (_fnp <= FTRIM_TH), 0.0, _zf)\n',
    '            _r15_flagF = (_zf < 0) & (_fnp <= FTRIM_TH)   # r15: pre-trim flag, F10 chain\n'
    '            if FTRIM == "zero":\n                _zf = np.where((_zf < 0) & (_fnp <= FTRIM_TH), 0.0, _zf)\n')
rep('        if FTPOS:\n            _kill = np.zeros(NW, bool); _kill[m] = (smb[m] < 0) & (_fnp <= FTRIM_TH)\n',
    '        _kill = np.zeros(NW, bool)\n'
    '        if FTPOS:\n'
    '            _r15_fk = (R15_KILL[j, m] if R15_KILL is not None else _fnp); _r15_th = (R15_KILL_TH if R15_KILL_TH is not None else FTRIM_TH)   # r15 null injection point (default = pinned expression)\n'
    '            _kill[m] = (smb[m] < 0) & (_r15_fk <= _r15_th)\n')
rep('        rec.append((int(E_ts[i]), float(pnl_raw - car - cbps), pnl_raw, float(car), float(cbps), gt, gm, gsel, int(sel.sum()), int(len(m)), fires_i,\n',
    '        if R15_INSTR:   # r15 instrumentation (read-only of the state)\n'
    '            _fkf = np.zeros(NW, bool); _fkf[m] = _r15_flagK; _fff = np.zeros(NW, bool); _fff[m] = _r15_flagF\n'
    '            _dpf = np.zeros(NW, bool); _dpf[m] = (_fnp <= FTRIM_TH); _mmf = np.zeros(NW, bool); _mmf[m] = True\n'
    '            _c4f = np.zeros(NW, np.float32); _c4f[m] = (fnow * (4.0 / ivv)).astype(np.float32)\n'
    '            _R15.append((_fkf, _fff, _dpf, _kill.copy(), _mmf, smr.astype(np.float32), _c4f))\n'
    '        rec.append((int(E_ts[i]), float(pnl_raw - car - cbps), pnl_raw, float(car), float(cbps), gt, gm, gsel, int(sel.sum()), int(len(m)), fires_i,\n')
rep('    return np.array(rec), np.stack(WS), ((np.array(_SG), np.array(_SP), np.array(_SC), np.array(_SK)) if SLEEVE else None)\n',
    '    global R15_LAST; R15_LAST = _R15\n'
    '    return np.array(rec), np.stack(WS), ((np.array(_SG), np.array(_SP), np.array(_SC), np.array(_SK)) if SLEEVE else None)\n')
rep('    save[f"{nm}_rec"] = R\n    save[f"{nm}_W"] = WS\n',
    '    save[f"{nm}_rec"] = R\n    save[f"{nm}_W"] = WS\n'
    '    if R15_INSTR and R15_LAST:\n'
    '        for _k, _nm2 in enumerate(("flagK", "flagF", "deep", "kill", "member", "smr", "c4")):\n'
    '            save[f"{nm}_R15_{_nm2}"] = np.stack([r[_k] for r in R15_LAST])\n')
rep('legs_king=LRa["king"], legs_rev24=LRa["rev24"], legs_fund=LRa["fund"], **save)',
    'legs_king=LRa["king"], legs_rev24=LRa["rev24"], legs_fund=LRa["fund"], '
    'legs_carry_king=LEGC_R15["king"], legs_carry_rev24=LEGC_R15["rev24"], legs_carry_fund=LEGC_R15["fund"], '
    'legs_price_king=LEGP_R15["king"], legs_price_rev24=LEGP_R15["rev24"], legs_price_fund=LEGP_R15["fund"], **save)')

open(OUT, "w", encoding="utf-8").write(s)
out_sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
diff = "".join(difflib.unified_diff(src.decode("utf-8").splitlines(True), s.splitlines(True), "w10_sleeve.py (pinned " + PIN_SHA[:16] + ")", "w10_sleeve_r15.py (" + out_sha[:16] + ")"))
open(os.path.splitext(OUT)[0] + ".diff", "w", encoding="utf-8").write(diff)
print("PINNED", PIN_SHA); print("DERIVED", out_sha); print("diff lines", diff.count("\n"))
