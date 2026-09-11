"""Add TF_FUNDOFF: zero the funding leg's seat weight in the LOW-price-dispersion labels (LL=0, HL=2),
renormalising onto the remaining legs. If that would leave no live leg (2022-23, where king's leg
return is identically 0), the original weights are kept UNCHANGED so that no anchor is dropped and
gross is untouched — Track F changes FORM only, never gross (that is Track C's axis)."""
import hashlib
P = "/workspace/uplift_2026-09-11/trackF/w10_trackF.py"
s = open(P).read()
print("before sha256", hashlib.sha256(s.encode()).hexdigest())
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:80])
    s = s.replace(old, new)
rep('TF_SAVE_W = int(os.environ.get("TF_SAVE_W", "1"))',
    'TF_FUNDOFF = int(os.environ.get("TF_FUNDOFF", "0")); assert TF_FUNDOFF in (0, 1)   # 1: fund seat weight -> 0 in labels {0 LL, 2 HL} (low price dispersion)\n'
    'TF_SAVE_W = int(os.environ.get("TF_SAVE_W", "1"))')
rep('_CFG = {"TF_REGIME_NPZ": TF_REGIME_NPZ,', '_CFG = {"TF_FUNDOFF": TF_FUNDOFF, "TF_REGIME_NPZ": TF_REGIME_NPZ,')
rep('assert not (TF_EMA_HI > 0 and not TF_REGIME_NPZ), "TF_EMA_HI needs TF_REGIME_NPZ"',
    'assert not (TF_EMA_HI > 0 and not TF_REGIME_NPZ), "TF_EMA_HI needs TF_REGIME_NPZ"\n'
    'assert not (TF_FUNDOFF and not TF_REGIME_NPZ), "TF_FUNDOFF needs TF_REGIME_NPZ"\n'
    'def TF_fundoff(w_, i):\n'
    '    if not TF_FUNDOFF or int(TF_LAB[i]) not in (0, 2): return w_\n'
    '    w2 = w_.copy(); w2[2] = 0.0\n'
    '    if w2.sum() <= 1e-12: return w_          # no other live leg: leave the book (and its gross) alone\n'
    '    return w2 / w2.sum()')
# apply at every return point of w3_at that can carry a fund weight
rep('''        shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
        w_ = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)''',
    '''        shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
        w_ = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)
        w_ = TF_fundoff(w_, i)''')
open(P, "w").write(s)
print("after  sha256", hashlib.sha256(s.encode()).hexdigest())
