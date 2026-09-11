"""Build w10_trackF.py = w10_health.py (sha 8684d9a9...) + Track F knobs. Every edit is an exact
string replacement, printed with its count, so the diff is auditable. Default path (all new env
unset) must be BITWISE identical to the parent device's output on d30_n2_c42_rec."""
import hashlib, sys
SRC = "/workspace/uplift_2026-09-11/trackF/w10_health_copy.py"
DST = "/workspace/uplift_2026-09-11/trackF/w10_trackF.py"
s = open(SRC).read()
print("parent sha256", hashlib.sha256(s.encode()).hexdigest())
EDITS = []
def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} occurrences, found {c} of: {old[:90]!r}"
    s = s.replace(old, new); EDITS.append((old[:70], c))

# --- 1. new env knobs, inserted right after the FTRIM assert line
rep('FTRIM = os.environ.get("FTRIM", "off"); assert FTRIM in ("off", "zero"), FTRIM',
    'FTRIM = os.environ.get("FTRIM", "off"); assert FTRIM in ("off", "zero"), FTRIM\n'
    '# ---- Track F (uplift_2026-09-11): regime-conditional FORM. All default-off; unset => bitwise-unchanged path.\n'
    'TF_REGIME_NPZ = os.environ.get("TF_REGIME_NPZ")            # npz with ts(int64), lab(int8 in {-1,0,1,2,3}); label at anchor i uses panel rows <= i only\n'
    'TF_SEATMODE = os.environ.get("TF_SEATMODE", "cal"); assert TF_SEATMODE in ("cal", "regime")\n'
    'TF_LOOK_R = int(os.environ.get("TF_LOOK_R", "900"))        # in-regime seat window (anchors carrying the current label)\n'
    'TF_EMA = float(os.environ.get("TF_EMA", "0.10"))           # base EMA coefficient (device constant was 0.10)\n'
    'TF_EMA_HI = float(os.environ.get("TF_EMA_HI", "0"))        # >0: EMA coefficient used when the disp24 half of the label is HIGH\n'
    'TF_SAVE_W = int(os.environ.get("TF_SAVE_W", "1"))          # 0: omit the (n, 829) weight arrays from the artifact (disk quota)\n')

# --- 2. self-report the new config
rep('_CFG = {"COSTB_JSON": COSTB_JSON,',
    '_CFG = {"TF_REGIME_NPZ": TF_REGIME_NPZ, "TF_SEATMODE": TF_SEATMODE, "TF_LOOK_R": TF_LOOK_R, "TF_EMA": TF_EMA, "TF_EMA_HI": TF_EMA_HI, "COSTB_JSON": COSTB_JSON,')

# --- 3. load the regime label onto the anchor axis (after E_ts exists)
rep('yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829',
    'yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829\n'
    'TF_LAB = np.full(nA, -1, np.int8)\n'
    'if TF_REGIME_NPZ:\n'
    '    _rz = np.load(TF_REGIME_NPZ, allow_pickle=True); _rm = {int(t): int(l) for t, l in zip(_rz["ts"].astype(np.int64), _rz["lab"])}\n'
    '    TF_LAB = np.array([_rm.get(int(t), -1) for t in E_ts], np.int8)\n'
    '    print(f"TF regime labels: {TF_REGIME_NPZ} covered {(TF_LAB >= 0).mean():.4f} cells " + json.dumps({int(k): int((TF_LAB == k).sum()) for k in (-1, 0, 1, 2, 3)}), flush=True)\n'
    'assert not (TF_SEATMODE == "regime" and not TF_REGIME_NPZ), "TF_SEATMODE=regime needs TF_REGIME_NPZ"\n'
    'assert not (TF_EMA_HI > 0 and not TF_REGIME_NPZ), "TF_EMA_HI needs TF_REGIME_NPZ"\n')

# --- 4. regime seat inside w3_at: strictly past, in-regime; falls back to the calendar rule when short
rep('''        p = pos.get(int(i), 0)
        if p < LOOK: return np.array([1/3]*3)
        sl = slice(p - LOOK, p)              # ★ 严格因果: 只用锚 i 之前的腿收益''',
    '''        p = pos.get(int(i), 0)
        if p < LOOK: return np.array([1/3]*3)
        sl = slice(p - LOOK, p)              # ★ 严格因果: 只用锚 i 之前的腿收益
        _tf_sel = None
        if TF_SEATMODE == "regime":
            _L = int(TF_LAB[i])
            if _L >= 0:
                _cand = TF_POS_BY_LAB.get(_L)
                if _cand is not None:
                    _c = _cand[_cand < p]                       # ★ strictly before the current anchor
                    if len(_c) >= TF_LOOK_R: _tf_sel = _c[-TF_LOOK_R:]
            if _tf_sel is None: _tf_sel = np.arange(p - LOOK, p)   # fallback = the calendar rule, identical to A0''')
rep('''        r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])''',
    '''        _ix = _tf_sel if _tf_sel is not None else np.arange(p - LOOK, p)
        r = np.stack([LRa["king"][_ix], LRa["rev24"][_ix], LRa["fund"][_ix]])''')
rep('''            r4 = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl], LRa["f10"][sl]])''',
    '''            _ix4 = _tf_sel if _tf_sel is not None else np.arange(p - LOOK, p)
            r4 = np.stack([LRa["king"][_ix4], LRa["rev24"][_ix4], LRa["fund"][_ix4], LRa["f10"][_ix4]])''')

# --- 5. regime-conditional EMA coefficient (both books)
rep('        sm = H + 0.1 * (tgt - H); trade = sm - H',
    '        _a = TF_EMA_HI if (TF_EMA_HI > 0 and int(TF_LAB[i]) in (1, 3)) else TF_EMA   # labels 1(LH)/3(HH) = HIGH disp24\n'
    '        sm = H + _a * (tgt - H); trade = sm - H')
rep('                _smf = HF + 0.1 * (_tgtf - HF)', '                _smf = HF + _a * (_tgtf - HF)')

# --- 6. build the position-by-label index once, after legs()
rep('LRa, pos = legs(SLOW); print("legs done"',
    'LRa, pos = legs(SLOW)\n'
    'TF_POS_BY_LAB = {}\n'
    'if TF_SEATMODE == "regime":\n'
    '    _ordered = sorted(pos, key=pos.get)\n'
    '    for _L in (0, 1, 2, 3):\n'
    '        TF_POS_BY_LAB[_L] = np.array([pos[_i] for _i in _ordered if int(TF_LAB[_i]) == _L], np.int64)\n'
    '    print("TF seat pools " + json.dumps({int(k): int(len(v)) for k, v in TF_POS_BY_LAB.items()}), flush=True)\n'
    'print("legs done"')

# --- 7. optional small artifact
rep('np.savez_compressed(f"{PD}/w10_ablation_series{_OT}.npz", cols=np.array(COLS), symbols=np.array(WSYM), config_json=np.array(json.dumps(_CFG)), legs_ts=',
    'save = save if TF_SAVE_W else {k: v for k, v in save.items() if not k.endswith("_W")}\n'
    'np.savez_compressed(f"{PD}/w10_ablation_series{_OT}.npz", cols=np.array(COLS), symbols=np.array(WSYM), config_json=np.array(json.dumps(_CFG)), legs_ts=')
open(DST, "w").write(s)
print("child sha256", hashlib.sha256(s.encode()).hexdigest())
print("edits applied:", len(EDITS))
for e, c in EDITS: print("  ", c, e.replace("\n", " | ")[:70])
