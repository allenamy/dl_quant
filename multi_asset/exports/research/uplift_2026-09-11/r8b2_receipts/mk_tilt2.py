import hashlib
SRC="/workspace/uplift_2026-09-11/r8b2/w10_sleeve_tilt.py"
DST="/workspace/uplift_2026-09-11/r8b2/w10_sleeve_tilt2.py"
s=open(SRC,encoding="utf-8").read()
assert hashlib.sha256(s.encode("utf-8")).hexdigest().startswith("7dd6324acd361081")
a1='assert TILT_LO == 0.25 and TILT_HI == 2.0'
assert s.count(a1)==1
s=s.replace(a1, a1+'''
TILT_SIG_NPZ = os.environ.get("TILT_SIG_NPZ")   # turnover-matched null feed: npz(ts,sig) REPLACES the
# internally computed sigma. Unset => the device computes sigma itself, bitwise-identical to tilt device 1.
_SIGFEED = None
if TILT_SIG_NPZ:
    assert TILT, "TILT_SIG_NPZ without TILT is meaningless"
    _sz = np.load(TILT_SIG_NPZ, allow_pickle=True)
    _SIGFEED = {int(t): float(v) for t, v in zip(_sz["ts"].astype(np.int64), _sz["sig"])}
    print("TILT_SIG_NPZ injected: %s n=%d" % (TILT_SIG_NPZ, len(_SIGFEED)), flush=True)''',1)
# numpy is imported AFTER this block in the source; move the feed load to just after `import numpy as np`
s=s.replace('''TILT_SIG_NPZ = os.environ.get("TILT_SIG_NPZ")   # turnover-matched null feed: npz(ts,sig) REPLACES the
# internally computed sigma. Unset => the device computes sigma itself, bitwise-identical to tilt device 1.
_SIGFEED = None
if TILT_SIG_NPZ:
    assert TILT, "TILT_SIG_NPZ without TILT is meaningless"
    _sz = np.load(TILT_SIG_NPZ, allow_pickle=True)
    _SIGFEED = {int(t): float(v) for t, v in zip(_sz["ts"].astype(np.int64), _sz["sig"])}
    print("TILT_SIG_NPZ injected: %s n=%d" % (TILT_SIG_NPZ, len(_SIGFEED)), flush=True)''',
'TILT_SIG_NPZ = os.environ.get("TILT_SIG_NPZ")   # turnover-matched null feed: npz(ts,sig) REPLACES the internally computed sigma. Unset => device computes sigma itself, bitwise-identical to tilt device 1.',1)
a2='_RN8_RAW = (FN * (8.0 / _IVf)) if TILT else None'
assert s.count(a2)==1
s=s.replace(a2, a2+'''
_SIGFEED = None
if TILT_SIG_NPZ:
    assert TILT, "TILT_SIG_NPZ without TILT is meaningless"
    _sz = np.load(TILT_SIG_NPZ, allow_pickle=True)
    _SIGFEED = {int(t): float(v) for t, v in zip(_sz["ts"].astype(np.int64), _sz["sig"])}
    print("TILT_SIG_NPZ injected: %s n=%d" % (TILT_SIG_NPZ, len(_SIGFEED)), flush=True)''',1)
a3='''            _fr = _RN8_RAW[j, m]; _fr = _fr[np.isfinite(_fr)]
            _tsig = 1e4 * float(np.std(_fr)) if len(_fr) > 50 else np.nan'''
assert s.count(a3)==1
s=s.replace(a3,'''            if _SIGFEED is not None:
                _tsig = _SIGFEED.get(int(E_ts[i]), np.nan)
            else:
                _fr = _RN8_RAW[j, m]; _fr = _fr[np.isfinite(_fr)]
                _tsig = 1e4 * float(np.std(_fr)) if len(_fr) > 50 else np.nan''',1)
a4='_CFG = {"TILT": TILT,'
assert s.count(a4)==1
s=s.replace(a4,'_CFG = {"TILT_SIG_NPZ": TILT_SIG_NPZ, "TILT": TILT,',1)
open(DST,"w",encoding="utf-8").write(s)
print("written",DST); print("sha256",hashlib.sha256(s.encode("utf-8")).hexdigest())
