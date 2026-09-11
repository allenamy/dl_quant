import hashlib
src=open("/workspace/uplift_2026-09-11/w10_sleeve.py").read()
assert hashlib.sha256(src.encode()).hexdigest().startswith("b88e35a46b93d712")
old='W3FIX = os.environ.get("W3FIX")   # '
assert src.count(old)==1
new=('W3SEQ_NPZ = os.environ.get("W3SEQ_NPZ")   # ANGLE2 cross-decomposition knob (r5a2): externally supplied per-anchor w3.\n'
     '# Unset => untouched path (GATE P bitwise). Set => w3_at(i) returns the supplied row for E_ts[i]; every anchor must be present.\n'
     +old)
src=src.replace(old,new,1)
old2='"W3FIX": W3FIX,'
assert src.count(old2)==1
src=src.replace(old2,'"W3FIX": W3FIX, "W3SEQ_NPZ": W3SEQ_NPZ,',1)
old3="yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829"
assert src.count(old3)==1
src=src.replace(old3,old3+'''
W3SEQ_MAP = None
if W3SEQ_NPZ:
    _wz = np.load(W3SEQ_NPZ, allow_pickle=True)
    _wts = _wz["ts"].astype(np.int64); _wv = np.asarray(_wz["w3"], dtype=float)
    assert _wv.shape == (len(_wts), 3), _wv.shape
    W3SEQ_MAP = {int(t): _wv[k] for k, t in enumerate(_wts)}
    print(f"W3SEQ injected: {W3SEQ_NPZ} rows {len(_wts)}", flush=True)''',1)
old4='    def w3_at(i):\n        if W3FIX is not None:'
assert src.count(old4)==1
new4=('    def w3_at(i):\n'
      '        if W3SEQ_MAP is not None:\n'
      '            _w = W3SEQ_MAP.get(int(E_ts[i]))\n'
      '            assert _w is not None, f"W3SEQ missing anchor {int(E_ts[i])}"\n'
      '            return _w\n'
      '        if W3FIX is not None:')
src=src.replace(old4,new4,1)
open("/workspace/uplift_2026-09-11/r5a2/w10_sleeve_w3seq.py","w").write(src)
print("wrote sha", hashlib.sha256(src.encode()).hexdigest()[:16])
