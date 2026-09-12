"""w21_intervene.py = w12b_intervene.py (sha256 ce3b7983...) + R21_DOSE: a CONTINUOUS extra kill depth for
turnover-matching the CEM nulls on the EXECUTED book (PREREG_r21 sha256 c4de6df3... SS A2).
With R21_DOSE unset (=0) it must be bitwise-identical to w12b_intervene.py (gate G-A2, asserted by r21_nulls.py).
Every replacement asserts count==1 (auditable string replacement, same discipline as r12 mkdev2.py)."""
import hashlib, sys
SRC = "/workspace/uplift_2026-09-11/r12_intervene/w12b_intervene.py"
DST = "/workspace/uplift_2026-09-11/r21_nulls_costbridge/w21_intervene.py"
s = open(SRC).read()
assert hashlib.sha256(s.encode()).hexdigest() == "ce3b79836a60647d7a110f6e82c0c929e19b4ce86e7e460ebf801f99883f5926", "w12b source is not the archived device"
# 1) env knob, parsed right after the R12_NULL loader block (anchor = the next unrelated line)
A_OLD = 'SEATF10 = int(os.environ.get("SEATF10", "0")); assert SEATF10 in (0, 1)'
A_NEW = ('R21_DOSE = float(os.environ.get("R21_DOSE", "0"))   # r21: continuous extra kill depth for turnover-matched nulls (PREREG_r21 c4de6df3 SSA2); 0 => bitwise w12b\n'
         'assert np.isfinite(R21_DOSE) and -1.0 <= R21_DOSE <= 64.0, R21_DOSE\n' + A_OLD)
assert s.count(A_OLD) == 1; s = s.replace(A_OLD, A_NEW)
# 2) self-report into config_json
B_OLD = '"R12_NULL": R12_NULL,'
B_NEW = '"R12_NULL": R12_NULL, "R21_DOSE": R21_DOSE,'
assert s.count(B_OLD) == 1; s = s.replace(B_OLD, B_NEW)
# 3) the kill step: n_rule names fully zeroed becomes K = max(n_rule + DOSE, 0): floor(K) fully zeroed, the next name scaled by (1 - frac(K))
C_OLD = '''                    _cem_n = int(_hit[0]) + 1 if len(_hit) else int(_pay.sum())
                    if _cem_n > 0:
                        _kill = np.zeros(NW, bool); _kill[m[_o[:_cem_n]]] = True
                        sm = np.where(_kill, 0.0, sm)
                        _g1 = float(np.abs(sm).sum())
                        if CEM_MODE == "neutral" and _g1 > 1e-9: sm = sm * (_Sg / _g1)
'''
C_NEW = '''                    _cem_n = int(_hit[0]) + 1 if len(_hit) else int(_pay.sum())
                    _K = max(float(_cem_n) + R21_DOSE, 0.0); _nf = min(int(np.floor(_K)), len(_o)); _fr = _K - np.floor(_K)   # r21 continuous kill depth; DOSE=0 => _nf=_cem_n, _fr=0.0 => bitwise w12b
                    if _nf > 0 or _fr > 0.0:
                        _kill = np.zeros(NW, bool); _kill[m[_o[:_nf]]] = True
                        sm = np.where(_kill, 0.0, sm)
                        if _fr > 0.0 and _nf < len(_o): sm[m[_o[_nf]]] = sm[m[_o[_nf]]] * (1.0 - _fr)
                        _g1 = float(np.abs(sm).sum())
                        if CEM_MODE == "neutral" and _g1 > 1e-9: sm = sm * (_Sg / _g1)
'''
assert s.count(C_OLD) == 1; s = s.replace(C_OLD, C_NEW)
# 4) device label
D_OLD = '"device": "w12b_intervene.py = w12_intervene.py + R12_NULL hook; PINNED'
D_NEW = '"device": "w21_intervene.py = w12b_intervene.py + R21_DOSE continuous kill depth (PREREG_r21 c4de6df3); w12b = w12_intervene.py + R12_NULL hook; PINNED'
assert s.count(D_OLD) == 1; s = s.replace(D_OLD, D_NEW)
open(DST, "w").write(s)
print("WROTE", DST, "sha256", hashlib.sha256(s.encode()).hexdigest())
