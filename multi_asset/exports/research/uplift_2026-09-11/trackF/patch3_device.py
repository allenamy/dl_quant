"""Fix TF_FUNDOFF: only reallocate away from the funding leg when the KING leg is actually live in
the seat window (non-degenerate leg returns). In 2022-23 king's leg return is identically 0, so the
guard keeps the book and its gross untouched there; the intervention is a 2024+ form change."""
import hashlib
P = "/workspace/uplift_2026-09-11/trackF/w10_trackF.py"
s = open(P).read()
print("before sha256", hashlib.sha256(s.encode()).hexdigest())
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90]); s = s.replace(old, new)
rep('''def TF_fundoff(w_, i):
    if not TF_FUNDOFF or int(TF_LAB[i]) not in (0, 2): return w_
    w2 = w_.copy(); w2[2] = 0.0
    if w2.sum() <= 1e-12: return w_          # no other live leg: leave the book (and its gross) alone
    return w2 / w2.sum()''',
    '''def TF_fundoff(w_, i, king_live):
    """Zero the funding leg in the LOW-price-dispersion labels, but ONLY where the king leg is live
    (its seat-window returns are non-degenerate). Otherwise the book would have no live score and the
    anchor would be dropped, which would change gross — Track F changes form only."""
    if not TF_FUNDOFF or int(TF_LAB[i]) not in (0, 2) or not king_live: return w_
    w2 = w_.copy(); w2[2] = 0.0
    if w2.sum() <= 1e-12: return w_
    return w2 / w2.sum()''')
rep('''        w_ = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)
        w_ = TF_fundoff(w_, i)''',
    '''        w_ = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)
        _kl = bool(np.std(r[0]) > 1e-12)
        w_ = TF_fundoff(w_, i, _kl)''')
rep('''            w_ = w_ / w_.sum() if w_.sum() > 1e-12 else msk / max(msk.sum(), 1.0)
        return w_''',
    '''            w_ = w_ / w_.sum() if w_.sum() > 1e-12 else msk / max(msk.sum(), 1.0)
            w_ = TF_fundoff(w_, i, _kl)
        return w_''')
open(P, "w").write(s); print("after  sha256", hashlib.sha256(s.encode()).hexdigest())
