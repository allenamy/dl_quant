p = "/workspace/uplift_2026-09-11/w10_sleeve.py"; s = open(p).read()
def rep(o,n,c=1):
    global s; assert s.count(o)==c,(s.count(o),o[:70]); s=s.replace(o,n)
rep('FTPOS = int(os.environ.get("FTPOS", "0")); assert FTPOS in (0, 1)',
    'FTPOS = int(os.environ.get("FTPOS", "0")); assert FTPOS in (0, 1)\nRNSM = int(os.environ.get("RNSM", "0")); assert RNSM in (0, 3, 6, 12)   # AMENDMENT 2: FTRIM band read on a CAUSAL trailing mean of rn8 over RNSM panel rows (0 = instantaneous, the deployed form)')
rep('_CFG = {"FTPOS": FTPOS,', '_CFG = {"RNSM": RNSM, "FTPOS": FTPOS,')
rep('_um = os.environ.get("UMASK_NPZ")',
    '''if RNSM:   # causal trailing mean over rows [j-RNSM+1, j] of the SAME panel the live producer reads; no future row touched
    _cs = np.cumsum(np.vstack([np.zeros((1, _RN8.shape[1])), _RN8]), 0)
    _lo = np.maximum(0, np.arange(_RN8.shape[0]) - RNSM + 1)
    _RN8S = (_cs[np.arange(_RN8.shape[0]) + 1] - _cs[_lo]) / (np.arange(_RN8.shape[0]) + 1 - _lo)[:, None]
    print(f"RNSM={RNSM}: rn8 trailing mean, maxabs vs instantaneous {np.abs(_RN8S - _RN8).max():.6f}", flush=True)
_um = os.environ.get("UMASK_NPZ")''')
rep("        _fnp = FN[j, m] * (8.0 / np.where(IV[j, m] > 0, IV[j, m], 8.0)); _fnp = np.where(np.isfinite(_fnp), _fnp, 0.0)",
    "        _fnp = FN[j, m] * (8.0 / np.where(IV[j, m] > 0, IV[j, m], 8.0)); _fnp = np.where(np.isfinite(_fnp), _fnp, 0.0)\n        if RNSM: _fnp = _RN8S[j, m]")
open(p,"w").write(s); print("patched3 ok")
