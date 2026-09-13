#!/usr/bin/env python3
"""mk_t1_device.py — generate the T1 derived replay device from the r18 device (PREREG_T1 §3, §9).

usage: python mk_t1_device.py <path/to/w10_sleeve_r18.py> <out/w10_sleeve_t1.py> <path/to/PREREG_T1_edge_diagnosis_2026-09-13.md>

Every replacement below must match EXACTLY ONCE in the source (asserted). With T1_INSTR unset/0 the
device is the r18 device plus dead branches; with T1_INSTR=1 it additionally carries per-leg component
books (king, rev24, fund, f10) through every step of the chain with the combined book's masks/ratios,
so that for every name sum_l component_l == combined quantity. rec / W are never written by the new code
(GATE P checks this bitwise on pod2).
"""
import sys, hashlib
SRC, DST, PREREG = sys.argv[1], sys.argv[2], sys.argv[3]
R18_SHA = "9b8a6323e8f0ac31ecb4046f6759dce09ba89645cbfc356db71f51c662b2c5c4"
PREREG_SHA = "9548214267b5a44900ba90fee6b2fb2bbeb77964d562628b77678b16c56777f6"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(SRC) == R18_SHA, ("r18 device sha", sha(SRC))
assert sha(PREREG) == PREREG_SHA, ("prereg sha", sha(PREREG))
s = open(SRC).read()
REP = []
# 1. knob + incompatibility asserts
REP.append(('R18_INSTR = int(os.environ.get("R18_INSTR", "0")); assert R18_INSTR in (0, 1)   # r18: per-anchor aux record only (rec/W untouched)\n',
            'R18_INSTR = int(os.environ.get("R18_INSTR", "0")); assert R18_INSTR in (0, 1)   # r18: per-anchor aux record only (rec/W untouched)\n'
            'T1_INSTR = int(os.environ.get("T1_INSTR", "0")); assert T1_INSTR in (0, 1)   # T1: per-leg exact-additive component books (rec/W untouched)\n'))
# 2. config self-report (inserted right before the CONFIG print)
REP.append(('print("CONFIG " + json.dumps(_CFG), flush=True)   # E-0826-C/D: 装置必须自报全部生效配置\n',
            '_CFG["T1"] = {"T1_INSTR": T1_INSTR, "r18_src_sha256": "%s", "prereg_sha256": "%s", "device": "w10_sleeve_t1.py = w10_sleeve_r18.py + T1_INSTR per-leg component books (king, rev24, fund, f10); default => bitwise-unchanged; PREREG_T1 §3"}\n'
            'if T1_INSTR:\n'
            '    assert KMOD == 0 and KMOD_F10 == 0 and KMOD_AGREE == 0 and KTAIL == 0 and LTRIM_TH is None and CDAMP == 0 and FTPOS == 0 and SEATF10 == 0 and FUNDSCALE == 0, "T1_INSTR requires the A0 chain (no KMOD/KTAIL/LTRIM/CDAMP/FTPOS/SEATF10/FUNDSCALE)"\n'
            'print("CONFIG " + json.dumps(_CFG), flush=True)   # E-0826-C/D: 装置必须自报全部生效配置\n' % (R18_SHA, PREREG_SHA)))
# 3. state init in run()
REP.append(('    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []; _R18 = []\n',
            '    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []; _R18 = []\n'
            '    _T1 = bool(T1_INSTR and depth is not None)   # T1: instrument the stop-layer arm only (the archived A0 = d30_n2_c42)\n'
            '    if _T1:\n'
            '        HL = np.zeros((4, NW)); HFL = np.zeros((4, NW)); HRL = np.zeros((4, NW))\n'
            '        T1AGG = []; T1ID = []; T1SMR = []; T1TRR = []; T1YV = []; T1C4 = []; T1RN = []; T1RATE = []; T1MEM = []\n'))
# 4. king-half score components
REP.append(('        z = w3[0]*np.nan_to_num(xz(sc["king"])) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*_fs*np.nan_to_num(FZ)\n',
            '        z = w3[0]*np.nan_to_num(xz(sc["king"])) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*_fs*np.nan_to_num(FZ)\n'
            '        if _T1:\n'
            '            ZC = np.stack([w3[0]*np.nan_to_num(xz(sc["king"])), w3[1]*np.nan_to_num(xz(sc["rev24"])), w3[2]*_fs*np.nan_to_num(FZ), np.zeros(len(m))])\n'))
# 5. king-half FTRIM (mask from the combined pre-trim z)
REP.append(('        if FTRIM == "zero":\n            z = np.where((z < 0) & (_fnp <= FTRIM_TH), 0.0, z)\n',
            '        if FTRIM == "zero":\n'
            '            if _T1: ZC = np.where(((z < 0) & (_fnp <= FTRIM_TH))[None, :], 0.0, ZC)\n'
            '            z = np.where((z < 0) & (_fnp <= FTRIM_TH), 0.0, z)\n'))
# 6. king-half demean / L1 / cap (ratio allocation) — same statements, same order for w
REP.append(('        w /= g; capw = 2.5 / max(int(sel.sum()), 1); w = np.clip(w, -capw, capw)\n',
            '        w /= g; capw = 2.5 / max(int(sel.sum()), 1)\n'
            '        if _T1:\n'
            '            WC = np.where(sel[None, :], ZC, 0.0); WC[:, sel] -= WC[:, sel].mean(axis=1, keepdims=True); WC /= g\n'
            '            _wpre = w.copy()\n'
            '        w = np.clip(w, -capw, capw)\n'
            '        if _T1:\n'
            '            _rat = np.where(_wpre != 0.0, w / np.where(_wpre != 0.0, _wpre, 1.0), 1.0); WC = WC * _rat[None, :]\n'))
REP.append(('        if g2 > 1e-9: w /= g2\n        tgt = np.zeros(NW); tgt[m] = w\n',
            '        if g2 > 1e-9: w /= g2\n'
            '        if _T1 and g2 > 1e-9: WC /= g2\n'
            '        tgt = np.zeros(NW); tgt[m] = w\n'
            '        if _T1: TGC = np.zeros((4, NW)); TGC[:, m] = WC\n'))
# 7. stop layer
REP.append(('            if bl.any(): tgt[bl] = 0.0\n',
            '            if bl.any():\n'
            '                tgt[bl] = 0.0\n'
            '                if _T1: TGC[:, bl] = 0.0\n'))
# 8. EMA + no-trade band (mask from the combined trade)
REP.append(('        sm = H + SMA * (tgt - H); trade = sm - H\n        sm = np.where(np.abs(trade) < SBAND, H, sm); trade = sm - H\n',
            '        sm = H + SMA * (tgt - H); trade = sm - H\n'
            '        if _T1:\n'
            '            SMC = HL + SMA * (TGC - HL); SMC = np.where((np.abs(trade) < SBAND)[None, :], HL, SMC)\n'
            '        sm = np.where(np.abs(trade) < SBAND, H, sm); trade = sm - H\n'))
# 9. forced exit
REP.append(('        sm = np.where(_nonsel, 0.0, sm); trade = sm - H\n',
            '        sm = np.where(_nonsel, 0.0, sm); trade = sm - H\n'
            '        if _T1: SMC[:, _nonsel] = 0.0\n'))
# 10. F10-half score components
REP.append(('                   + _w3f[2] * np.nan_to_num(FZ))\n',
            '                   + _w3f[2] * np.nan_to_num(FZ))\n'
            '            if _T1:\n'
            '                ZFC = np.stack([np.zeros(len(m)), _w3f[1] * np.nan_to_num(xz(sc["rev24"])), _w3f[2] * np.nan_to_num(FZ), _w3f[0] * np.nan_to_num(xz(F10P[i, m]))])\n'))
# 11. F10-half FTRIM
REP.append(('            if FTRIM == "zero":\n                _zf = np.where((_zf < 0) & (_fnp <= FTRIM_TH), 0.0, _zf)\n',
            '            if FTRIM == "zero":\n'
            '                if _T1: ZFC = np.where(((_zf < 0) & (_fnp <= FTRIM_TH))[None, :], 0.0, ZFC)\n'
            '                _zf = np.where((_zf < 0) & (_fnp <= FTRIM_TH), 0.0, _zf)\n'))
# 12. F10-half chain
OLD_F = ('            _wf = np.where(sel, _zf, 0.0)\n'
         '            if sel.any():\n'
         '                _wf[sel] -= _wf[sel].mean()\n'
         '            _gf = np.abs(_wf).sum()\n'
         '            if _gf > 1e-9:\n'
         '                _wf = _wf / _gf\n'
         '                _wf = np.clip(_wf, -capw, capw)\n'
         '                _g2f = np.abs(_wf).sum()\n'
         '                if _g2f > 1e-9:\n'
         '                    _wf = _wf / _g2f\n'
         '                _tgtf = np.zeros(NW); _tgtf[m] = _wf\n'
         '                _smf = HF + SMA * (_tgtf - HF)\n'
         '                _trf = _smf - HF\n'
         '                _smf = np.where(np.abs(_trf) < SBAND, HF, _smf)\n'
         '                _smf = np.where(_nonsel, 0.0, _smf)\n'
         '                if depth is not None:\n'
         '                    _blf = su > i\n'
         '                    if _blf.any(): _smf[_blf] = 0.0\n'
         '            else:\n'
         '                _smf = HF.copy()\n'
         '            HF = _smf\n')
NEW_F = ('            _wf = np.where(sel, _zf, 0.0)\n'
         '            if sel.any():\n'
         '                _wf[sel] -= _wf[sel].mean()\n'
         '            if _T1:\n'
         '                WFC = np.where(sel[None, :], ZFC, 0.0)\n'
         '                if sel.any(): WFC[:, sel] -= WFC[:, sel].mean(axis=1, keepdims=True)\n'
         '            _gf = np.abs(_wf).sum()\n'
         '            if _gf > 1e-9:\n'
         '                _wf = _wf / _gf\n'
         '                if _T1: WFC = WFC / _gf; _wfpre = _wf.copy()\n'
         '                _wf = np.clip(_wf, -capw, capw)\n'
         '                if _T1:\n'
         '                    _ratf = np.where(_wfpre != 0.0, _wf / np.where(_wfpre != 0.0, _wfpre, 1.0), 1.0); WFC = WFC * _ratf[None, :]\n'
         '                _g2f = np.abs(_wf).sum()\n'
         '                if _g2f > 1e-9:\n'
         '                    _wf = _wf / _g2f\n'
         '                    if _T1: WFC = WFC / _g2f\n'
         '                _tgtf = np.zeros(NW); _tgtf[m] = _wf\n'
         '                _smf = HF + SMA * (_tgtf - HF)\n'
         '                _trf = _smf - HF\n'
         '                if _T1:\n'
         '                    TGFC = np.zeros((4, NW)); TGFC[:, m] = WFC\n'
         '                    SMFC = HFL + SMA * (TGFC - HFL); SMFC = np.where((np.abs(_trf) < SBAND)[None, :], HFL, SMFC)\n'
         '                _smf = np.where(np.abs(_trf) < SBAND, HF, _smf)\n'
         '                _smf = np.where(_nonsel, 0.0, _smf)\n'
         '                if _T1: SMFC[:, _nonsel] = 0.0\n'
         '                if depth is not None:\n'
         '                    _blf = su > i\n'
         '                    if _blf.any():\n'
         '                        _smf[_blf] = 0.0\n'
         '                        if _T1: SMFC[:, _blf] = 0.0\n'
         '            else:\n'
         '                _smf = HF.copy()\n'
         '                if _T1: SMFC = HFL.copy()\n'
         '            HF = _smf\n'
         '            if _T1: HFL = SMFC\n')
REP.append((OLD_F, NEW_F))
# 13. blend
REP.append(('            smb = (1.0 - PHI) * sm + PHI * _smf\n        else:\n            smb = sm\n',
            '            smb = (1.0 - PHI) * sm + PHI * _smf\n'
            '            if _T1: SMBC = (1.0 - PHI) * SMC + PHI * SMFC\n'
            '        else:\n'
            '            smb = sm\n'
            '            if _T1: SMBC = SMC.copy()\n'))
# 14. executor reshape
REP.append(('        nz = np.abs(sm) > 1e-12\n        smr = sm.copy()\n        if nz.any():\n            smr[nz] -= smr[nz].mean()\n            _g0 = np.abs(sm).sum(); _g1 = np.abs(smr).sum()\n            if _g1 > 1e-9:\n                smr *= _g0 / _g1\n        trr = smr - HR\n',
            '        nz = np.abs(sm) > 1e-12\n'
            '        smr = sm.copy()\n'
            '        if _T1: SMRC = SMBC.copy()\n'
            '        if nz.any():\n'
            '            smr[nz] -= smr[nz].mean()\n'
            '            if _T1: SMRC[:, nz] -= SMRC[:, nz].mean(axis=1, keepdims=True)\n'
            '            _g0 = np.abs(sm).sum(); _g1 = np.abs(smr).sum()\n'
            '            if _g1 > 1e-9:\n'
            '                smr *= _g0 / _g1\n'
            '                if _T1: SMRC *= _g0 / _g1\n'
            '        trr = smr - HR\n'
            '        if _T1: TRRC = SMRC - HRL; _HRprev = HR.copy()\n'))
# 15. per-anchor per-leg per-side aggregates + per-name arrays (right after the exec cost is computed)
REP.append(('        cbps_r = sum(tabs_r[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))\n',
            '        cbps_r = sum(tabs_r[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))\n'
            '        if _T1:\n'
            '            _rate = np.array([fr * mk + (1 - fr) * tk for (mk, tk, fr) in COST_B])[tr]\n'
            '            _c4 = fnow * (4.0 / ivv); _smr_m = smr[m]; _sgn_tr = np.sign(trr[m])\n'
            '            _side = np.where(_smr_m != 0.0, np.sign(_smr_m), np.sign(_HRprev[m]))\n'
            '            _Pn = SMRC[:, m] * yv[None, :] * 1e4; _Cn = SMRC[:, m] * _c4[None, :] * 1e4; _Kn = _rate[None, :] * TRRC[:, m] * _sgn_tr[None, :]\n'
            '            _Lp = _smr_m > 0; _Sp = _smr_m < 0; _Lk = _side > 0; _Sk = _side < 0\n'
            '            T1AGG.append(np.stack([_Pn[:, _Lp].sum(1), _Pn[:, _Sp].sum(1), _Cn[:, _Lp].sum(1), _Cn[:, _Sp].sum(1), _Kn[:, _Lk].sum(1), _Kn[:, _Sk].sum(1)]))\n'
            '            T1ID.append((float(np.abs(SMRC.sum(0) - smr).max()), float(_Pn.sum() - pnl_r), float(_Cn.sum() - car_r), float(_Kn.sum() - cbps_r), float(np.abs(SMRC[1]).max()), float(np.abs(SMC.sum(0) - _smk).max()) if PHI > 0 else 0.0))\n'
            '            T1SMR.append(SMRC.astype(np.float32)); _tq = np.zeros((4, NW), np.float32); _tq[:, m] = TRRC[:, m]; T1TRR.append(_tq)\n'
            '            _a = np.zeros(NW, np.float32); _a[m] = yv; T1YV.append(_a)\n'
            '            _a = np.zeros(NW, np.float32); _a[m] = _c4; T1C4.append(_a)\n'
            '            _a = np.full(NW, np.nan, np.float32); _a[m] = _fnp; T1RN.append(_a)\n'
            '            _a = np.full(NW, np.nan, np.float32); _a[m] = _rate; T1RATE.append(_a)\n'
            '            _b = np.zeros(NW, bool); _b[m] = True; T1MEM.append(_b)\n'))
# 16. state advance
REP.append(('        H = _smk if PHI > 0 else sm      # king 书 EMA 态独立推进(φ=0 时二者同一)\n        HB = sm; HR = smr; Pi = Pi * (1.0 + yfull)\n',
            '        H = _smk if PHI > 0 else sm      # king 书 EMA 态独立推进(φ=0 时二者同一)\n'
            '        HB = sm; HR = smr; Pi = Pi * (1.0 + yfull)\n'
            '        if _T1:\n'
            '            HL = SMC if PHI > 0 else SMBC; HRL = SMRC\n'))
# 17. export
REP.append(('    global R18_LAST; R18_LAST = _R18\n',
            '    global R18_LAST; R18_LAST = _R18\n'
            '    global T1_LAST; T1_LAST = (dict(T1AGG=np.array(T1AGG), T1ID=np.array(T1ID), T1SMR=np.stack(T1SMR), T1TRR=np.stack(T1TRR), T1YV=np.stack(T1YV), T1C4=np.stack(T1C4), T1RN=np.stack(T1RN), T1RATE=np.stack(T1RATE), T1MEM=np.stack(T1MEM)) if _T1 else None)\n'))
REP.append(('    save[f"{nm}_W"] = WS\n',
            '    save[f"{nm}_W"] = WS\n'
            '    if T1_INSTR and T1_LAST is not None:\n'
            '        for _k, _v in T1_LAST.items(): save[f"{nm}_{_k}"] = _v\n'
            '        save[f"{nm}_T1AGG_axes"] = np.array(["rows: pnlL,pnlS,carL,carS,costL,costS", "cols: king,rev24,fund,f10", "T1ID: maxabs(sum_l smr_l - smr), pnl_id, carry_id, cost_id, max|rev24 smr comp|, maxabs(sum_l SMC - king-half sm)"])\n'))
for old, new in REP:
    n = s.count(old)
    assert n == 1, ("replacement must match exactly once", n, old[:120])
    s = s.replace(old, new)
open(DST, "w").write(s)
print("wrote", DST, "sha256", sha(DST), "replacements", len(REP))
