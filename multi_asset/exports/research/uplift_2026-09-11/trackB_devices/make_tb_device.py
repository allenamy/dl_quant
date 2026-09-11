import hashlib, re, sys
SRC="/workspace/review_scratch/health_check/w10_health.py"
DST="/workspace/uplift_2026-09-11/w10_tb.py"
s=open(SRC).read()
src_sha=hashlib.sha256(s.encode()).hexdigest()
def rep(old,new,n=1):
    global s
    assert s.count(old)==n, (s.count(old), n, old[:70])
    s=s.replace(old,new)

# --- 0. knobs, inserted right after COSTB_JSON parse block
rep('COST_B_OVERRIDE = None\n',
    'COST_B_OVERRIDE = None\n'
    'TB_BAND = float(os.environ.get("TB_BAND", "2.5e-4"))   # TRACK B: no-trade band per name (producer smoothing layer)\n'
    'TB_EMA  = float(os.environ.get("TB_EMA",  "0.1"))      # TRACK B: EMA alpha (producer smoothing layer)\n'
    'TB_CAD  = int(os.environ.get("TB_CAD",   "1"))         # TRACK B: retarget cadence in 4h anchors (1=4h, 2=8h, 3=12h, 6=24h); non-update anchors hold the book\n'
    'TB_TOPD = int(os.environ.get("TB_TOPD",  "0"))         # TRACK B: >0 execute only the N largest |book delta| this anchor\n'
    'TB_HOLD = int(os.environ.get("TB_HOLD",  "0"))         # TRACK B: >0 per-name minimum anchors between book-level trades\n'
    'TB_COSTM= float(os.environ.get("TB_COSTM","1.0"))      # TRACK B: multiply every COST_B tier (re-pricing at the re-audited line)\n')

# --- 1. self-report
rep('_CFG = {"COSTB_JSON": COSTB_JSON,',
    '_CFG = {"TB_BAND": TB_BAND, "TB_EMA": TB_EMA, "TB_CAD": TB_CAD, "TB_TOPD": TB_TOPD, "TB_HOLD": TB_HOLD, "TB_COSTM": TB_COSTM, "COSTB_JSON": COSTB_JSON,')

# --- 2. cost multiplier (after the tier override is resolved)
rep('_CFG["COST_B"] = [list(t) for t in COST_B];',
    'if TB_COSTM != 1.0: COST_B = [(mk * TB_COSTM, tk * TB_COSTM, fr) for (mk, tk, fr) in COST_B]\n'
    '_CFG["COST_B"] = [list(t) for t in COST_B];')

# --- 3. state for min-hold
rep('    cnt = np.zeros(NW, int); su = np.full(NW, -1)\n',
    '    cnt = np.zeros(NW, int); su = np.full(NW, -1)\n'
    '    _last_tr = np.full(NW, -10**6, int)   # TRACK B: anchor index of each name\'s last book-level trade\n')

# --- 4. cadence flag, computed from the anchor clock (not the loop index)
rep('        j = pw_row.get(int(E_ts[i]))\n        if j is None: continue\n        m = members[i]\n        if UMASK_ROW is not None and UMASK_SCOPE in ("members", "m1"):\n            _mk = UMASK_ROW.get(j)\n            if _mk is not None: m = m[_mk[m]]\n        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}\n        FZ =',
    '        j = pw_row.get(int(E_ts[i]))\n        if j is None: continue\n        _upd = (TB_CAD == 1) or ((int(E_ts[i]) // 14400) % TB_CAD == 0)   # TRACK B cadence: retarget only on multiples of TB_CAD 4h anchors\n        m = members[i]\n        if UMASK_ROW is not None and UMASK_SCOPE in ("members", "m1"):\n            _mk = UMASK_ROW.get(j)\n            if _mk is not None: m = m[_mk[m]]\n        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}\n        FZ =')

# --- 5. cadence hold on the king target
rep('        tgt = np.zeros(NW); tgt[m] = w\n        if depth is not None:',
    '        tgt = np.zeros(NW); tgt[m] = w\n        if not _upd: tgt = H.copy()   # TRACK B: hold anchor -> no retarget (forced exits + stop blackout below still apply)\n        if depth is not None:')

# --- 6. EMA/band parameters, king chain
rep('        sm = H + 0.1 * (tgt - H); trade = sm - H\n        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H\n',
    '        sm = H + TB_EMA * (tgt - H); trade = sm - H\n        sm = np.where(np.abs(trade) < TB_BAND, H, sm); trade = sm - H\n')

# --- 7. cadence hold + EMA/band, F10 chain
rep('                _tgtf = np.zeros(NW); _tgtf[m] = _wf\n                _smf = HF + 0.1 * (_tgtf - HF)\n                _trf = _smf - HF\n                _smf = np.where(np.abs(_trf) < 2.5e-4, HF, _smf)\n',
    '                _tgtf = np.zeros(NW); _tgtf[m] = _wf\n                if not _upd: _tgtf = HF.copy()   # TRACK B cadence\n                _smf = HF + TB_EMA * (_tgtf - HF)\n                _trf = _smf - HF\n                _smf = np.where(np.abs(_trf) < TB_BAND, HF, _smf)\n')

# --- 8. book-level execution filter (top-N deltas / min holding period)
rep('        trade = sm - HB\n        nz = np.abs(sm) > 1e-12\n',
    '        trade = sm - HB\n'
    '        if TB_TOPD > 0 or TB_HOLD > 0:   # TRACK B: executor-side suppression; forced liquidity exits are never suppressed\n'
    '            _keep = np.ones(NW, bool)\n'
    '            if TB_HOLD > 0: _keep &= (i - _last_tr) >= TB_HOLD\n'
    '            if TB_TOPD > 0:\n'
    '                _a = np.abs(np.where(_keep, trade, 0.0))\n'
    '                if int((_a > 0).sum()) > TB_TOPD:\n'
    '                    _k2 = np.zeros(NW, bool); _k2[np.argsort(-_a)[:TB_TOPD]] = True; _keep &= _k2\n'
    '            _keep |= _nonsel\n'
    '            sm = np.where(_keep, sm, HB); trade = sm - HB\n'
    '            _last_tr = np.where(np.abs(trade) > 1e-12, i, _last_tr)\n'
    '        nz = np.abs(sm) > 1e-12\n')

open(DST,"w").write(s)
print("SRC", SRC, src_sha)
print("DST", DST, hashlib.sha256(s.encode()).hexdigest())
