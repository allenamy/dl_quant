"""w12b_intervene.py = w12_intervene.py + a NULL hook (forced fire mask / symbol-permuted monitor).
With R12_NULL unset it must be bitwise-identical to w12_intervene.py's output (re-verified)."""
import hashlib
SRC="/workspace/uplift_2026-09-11/r12_intervene/w12_intervene.py"
DST="/workspace/uplift_2026-09-11/r12_intervene/w12b_intervene.py"
s=open(SRC).read()
A_OLD='R12_TRAIL = 2190; R12_MINH = 900   # causal reference window / minimum history before any fire\n'
A_NEW=A_OLD+'''R12_NULL = os.environ.get("R12_NULL", "")   # turnover-matched null: npz with per-anchor force_fire (same count, nullified timing) and/or sym_perm (nullified name selection)
_NULL_FIRE = None; _NULL_PERM = None
if R12_NULL:
    _nz = np.load(R12_NULL, allow_pickle=True)
    if "force_fire" in _nz.files: _NULL_FIRE = {int(t): bool(f) for t, f in zip(_nz["ts"].astype(np.int64), _nz["force_fire"])}
    if "sym_perm" in _nz.files: _NULL_PERM = _nz["sym_perm"].astype(np.int64)
    print("R12_NULL loaded: %s fire=%s perm=%s" % (R12_NULL, _NULL_FIRE is not None, _NULL_PERM is not None), flush=True)
'''
assert s.count(A_OLD)==1; s=s.replace(A_OLD,A_NEW)
B_OLD='"R12_TRAIL": R12_TRAIL, "R12_MINH": R12_MINH,'
B_NEW='"R12_TRAIL": R12_TRAIL, "R12_MINH": R12_MINH, "R12_NULL": R12_NULL,'
assert s.count(B_OLD)==1; s=s.replace(B_OLD,B_NEW)
# CEM: forced fire + permuted ranking monitor
C_OLD='''        if CEM_Q:
            if len(_cem_h) >= R12_MINH:
                _cth = float(np.quantile(np.asarray(_cem_h[-R12_TRAIL:]), float(CEM_Q)))
                if _bill0 > _cth:
'''
C_NEW='''        if CEM_Q:
            if _NULL_PERM is not None:   # name-selection null: rank on a permuted funding row, pay the true one
                _c = sm[m] * np.nan_to_num(FN[j, _NULL_PERM[m]], nan=0.0) * (4.0 / np.where(np.isfinite(IV[j, _NULL_PERM[m]]) & (IV[j, _NULL_PERM[m]] > 0), IV[j, _NULL_PERM[m]], 8.0)) * 1e4
                _Sc = float(_c.sum())
            if len(_cem_h) >= R12_MINH:
                _cth = float(np.quantile(np.asarray(_cem_h[-R12_TRAIL:]), float(CEM_Q)))
                _trig = (_NULL_FIRE.get(int(E_ts[i]), False) if _NULL_FIRE is not None else (_bill0 > _cth))
                if _trig:
'''
assert s.count(C_OLD)==1; s=s.replace(C_OLD,C_NEW)
# BYP: forced fire
D_OLD='''                    _fire = (_s6 >= _bq) if BYP_STATE == "rally" else ((_s6 <= -_bq) if BYP_STATE == "rev" else (abs(_s6) >= _bq))
'''
D_NEW='''                    _fire = (_s6 >= _bq) if BYP_STATE == "rally" else ((_s6 <= -_bq) if BYP_STATE == "rev" else (abs(_s6) >= _bq))
                    if _NULL_FIRE is not None: _fire = _NULL_FIRE.get(int(E_ts[i]), False)
'''
assert s.count(D_OLD)==1; s=s.replace(D_OLD,D_NEW)
E_OLD='"device": "w12_intervene.py = PINNED'
E_NEW='"device": "w12b_intervene.py = w12_intervene.py + R12_NULL hook; PINNED'
assert s.count(E_OLD)==1; s=s.replace(E_OLD,E_NEW)
open(DST,"w").write(s)
print("WROTE",DST,"sha256",hashlib.sha256(s.encode()).hexdigest())
