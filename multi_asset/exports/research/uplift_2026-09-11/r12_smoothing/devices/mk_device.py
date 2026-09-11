"""r12: build w10_r12.py = pinned w10_sleeve.py (sha256 b88e35a4...) + {SMA, SBAND, AUX12}.
Each replacement asserted to fire exactly once. float("0.1")==0.1 and float("2.5e-4")==2.5e-4
bit-exactly, so the DEFAULT path is bitwise-unchanged in rec/W (gate G1 proves it empirically)."""
import hashlib
SC = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/r12/"
s = open(SC + "w10_sleeve.py").read()
assert hashlib.sha256(s.encode()).hexdigest()[:16] == "b88e35a46b93d712"
def sub1(t, old, new):
    assert t.count(old) == 1, (t.count(old), old[:80]); return t.replace(old, new)

s = sub1(s, 'SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)\n',
 'SMA = float(os.environ.get("SMA", "0.1")); assert 0.0 < SMA <= 1.0, SMA        # r12 harvest-EMA alpha; deployed 0.1 = wide_shadow/shadow_bundle/config.json params.alpha\n'
 'SBAND = float(os.environ.get("SBAND", "2.5e-4")); assert 0.0 <= SBAND <= 4.0e-3, SBAND   # r12 no-trade band, WEIGHT units; deployed 0.00025 = same file params.band\n'
 'AUX12 = int(os.environ.get("AUX12", "0")); assert AUX12 in (0, 1)   # r12 responsiveness instrument: unshaped target book + per-anchor diagnostics. ADDITIVE — never read by the book.\n'
 'SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)\n')

s = sub1(s, '"SEATNET": SEATNET,', '"SMA": SMA, "SBAND": SBAND, "AUX12": AUX12, "SEATNET": SEATNET,')

s = sub1(s,
 '        sm = H + 0.1 * (tgt - H); trade = sm - H\n'
 '        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H\n',
 '        sm = H + SMA * (tgt - H); trade = sm - H\n'
 '        _r12_nbk = int((np.abs(trade) < SBAND).sum()) if AUX12 else 0\n'
 '        _r12_nbf = 0; _r12_deg = 0\n'
 '        sm = np.where(np.abs(trade) < SBAND, H, sm); trade = sm - H\n')

s = sub1(s,
 '                _smf = HF + 0.1 * (_tgtf - HF)\n'
 '                _trf = _smf - HF\n'
 '                _smf = np.where(np.abs(_trf) < 2.5e-4, HF, _smf)\n',
 '                _smf = HF + SMA * (_tgtf - HF)\n'
 '                _trf = _smf - HF\n'
 '                _r12_nbf = int((np.abs(_trf) < SBAND).sum()) if AUX12 else 0\n'
 '                _smf = np.where(np.abs(_trf) < SBAND, HF, _smf)\n')

# aux accumulators
s = sub1(s, '    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []\n',
 '    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []\n'
 '    _R12T = []; _R12A = []   # r12: unshaped (alpha=1, band=0) blended target book, and per-anchor aux scalars\n')

# _tgtf may be undefined when the F10 chain degenerates; make the fallback explicit
s = sub1(s, '            else:\n                _smf = HF.copy()\n',
 '            else:\n                _smf = HF.copy()\n'
 '                if AUX12: _tgtf = HF.copy(); _r12_deg = 1   # r12: degenerate F10 anchor -> "what the model wants" is "hold" (flagged in _R12A col 7)\n')

# collect aux right before rec.append
s = sub1(s, '        netlong = float(sm.sum() / max(np.abs(sm).sum(), 1e-9))\n',
 '        if AUX12:\n'
 '            _tb = ((1.0 - PHI) * tgt + PHI * _tgtf) if PHI > 0 else tgt.copy()\n'
 '            _tb = np.where(_nonsel, 0.0, _tb)\n'
 '            if depth is not None:\n'
 '                _blx = su > i\n'
 '                if _blx.any(): _tb[_blx] = 0.0\n'
 '            _R12T.append(_tb.astype(np.float32))\n'
 '            _R12A.append((float(np.abs(trr[m]).sum()), float(np.abs(trr).sum()), float(np.abs(_tb).sum()),\n'
 '                          float(np.abs(sm - _tb).sum()), float(_r12_nbk), float(_r12_nbf),\n'
 '                          float(len(m)), float(_r12_deg)))\n'
 '        netlong = float(sm.sum() / max(np.abs(sm).sum(), 1e-9))\n')

s = sub1(s, '    return np.array(rec), np.stack(WS), ((np.array(_SG)',
 '    if AUX12:\n'
 '        globals()["_R12_LAST"] = (np.stack(_R12T), np.array(_R12A))\n'
 '    return np.array(rec), np.stack(WS), ((np.array(_SG)')

s = sub1(s, '    save[f"{nm}_rec"] = R\n',
 '    save[f"{nm}_rec"] = R\n'
 '    if AUX12:\n'
 '        save[f"{nm}_R12T"], save[f"{nm}_R12A"] = globals()["_R12_LAST"]\n'
 '        save[f"{nm}_R12A_cols"] = np.array(["turn_ex_member", "turn_ex_all", "gross_target", "dist_sm_tgt", "n_band_king", "n_band_f10", "nmember", "f10_degenerate"])\n')

# self-identification: the device must name what it is
s = sub1(s, '_CFG["UPLIFT"]["self_sha256"] = _CFG["HEALTH"]["device_sha256"]\n',
 '_CFG["UPLIFT"]["self_sha256"] = _CFG["HEALTH"]["device_sha256"]\n'
 '_CFG["R12"] = {"device": "w10_r12.py = w10_sleeve.py (sha256 b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650) + {SMA, SBAND, AUX12}; SMA=0.1 SBAND=2.5e-4 AUX12=0 => bitwise-unchanged rec/W (gate G1)", "parent_sha256": "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650"}\n')

open(SC + "w10_r12.py", "w").write(s)
print("w10_r12.py sha256", hashlib.sha256(s.encode()).hexdigest())
