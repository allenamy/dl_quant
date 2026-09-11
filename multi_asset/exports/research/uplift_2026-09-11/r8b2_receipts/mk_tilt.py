import hashlib
SRC="/workspace/uplift_2026-09-11/w10_sleeve.py"
DST="/workspace/uplift_2026-09-11/r8b2/w10_sleeve_tilt.py"
s=open(SRC,encoding="utf-8").read()
assert hashlib.sha256(s.encode("utf-8")).hexdigest().startswith("b88e35a46b93d712")

anchor1='FUNDSCALE = int(os.environ.get("FUNDSCALE", "0")); assert FUNDSCALE in (0, 1)'
assert s.count(anchor1)==1
knobs = anchor1 + '''
# ===== BUILD-2 DISPERSION SEAT TILT (round 8). All unset => bitwise-unchanged path. =====
# w3[2] (fund) *= f(sigma_fund at THIS anchor); w3 renormalised to sum 1 => freed weight goes to the
# remaining unmasked legs (for LEGS=101 that is king alone). sigma_fund is measured STRICTLY CAUSALLY:
# 1e4 * population sd (ddof=0) of the finite 8h-equivalent settled funding rates rn8 = f_fund_now*8/f_fund_iv
# over the SAME masked member set m the book ranks at this anchor. Definition copied from
# r7f1/r7_sigma2.py "LIVE" variant (829 qvk base INTERSECT m1 CRYPTO umask), which is the gauge the
# round-7 leg numbers were conditioned on. f_fund_now is the last SETTLED rate at or before the anchor.
TILT = os.environ.get("TILT", "")           # "" = off | step | ramp | pow
assert TILT in ("", "step", "ramp", "pow"), TILT
TILT_TAU = float(os.environ.get("TILT_TAU", "4.75"))   # INHERITED from round 7 profiled step threshold
assert TILT_TAU == 4.75, TILT_TAU
TILT_K = float(os.environ.get("TILT_K", "1"))          # step: kappa below tau | ramp: floor | pow: exponent p
assert TILT_K in (0.0, 0.25, 0.5, 0.75, 1.0), TILT_K
TILT_LO = float(os.environ.get("TILT_LO", "0.25"))     # pow only: clip floor
TILT_HI = float(os.environ.get("TILT_HI", "2.0"))      # pow only: clip ceiling
assert TILT_LO == 0.25 and TILT_HI == 2.0
'''
s=s.replace(anchor1, knobs, 1)

anchor2='_CFG = {"RNSM": RNSM,'
assert s.count(anchor2)==1
s=s.replace(anchor2,'_CFG = {"TILT": TILT, "TILT_TAU": TILT_TAU, "TILT_K": TILT_K, "TILT_LO": TILT_LO, "TILT_HI": TILT_HI, "RNSM": RNSM,',1)

anchor3='if FUNDSCALE:\n    _sig = np.array('
assert s.count(anchor3)==1
s=s.replace(anchor3,'_RN8_RAW = (FN * (8.0 / _IVf)) if TILT else None   # NaN preserved: the gauge drops non-finite, it does not zero them\nif FUNDSCALE:\n    _sig = np.array(',1)

anchor4='        w3 = w3_at(i)\n        _fs = (FUNDSCALE_ROW[j] if FUNDSCALE else 1.0)'
assert s.count(anchor4)==1
tilt_body = '''        w3 = w3_at(i)
        _tsig = np.nan
        if TILT:
            _fr = _RN8_RAW[j, m]; _fr = _fr[np.isfinite(_fr)]
            _tsig = 1e4 * float(np.std(_fr)) if len(_fr) > 50 else np.nan
            if np.isfinite(_tsig):
                if TILT == "step":   _fmul = TILT_K if _tsig < TILT_TAU else 1.0
                elif TILT == "ramp": _fmul = float(np.clip(_tsig / TILT_TAU, TILT_K, 1.0))
                else:                _fmul = float(np.clip((_tsig / TILT_TAU) ** TILT_K, TILT_LO, TILT_HI))
                w3 = w3.copy(); w3[2] = w3[2] * _fmul
                _ws = w3.sum()
                if _ws > 1e-12: w3 = w3 / _ws
        _fs = (FUNDSCALE_ROW[j] if FUNDSCALE else 1.0)'''
s=s.replace(anchor4, tilt_body, 1)

anchor5='float(pnl_r - car_r - cbps_r), pnl_r, car_r, float(cbps_r), netlong))'
assert s.count(anchor5)==1
s=s.replace(anchor5,'float(pnl_r - car_r - cbps_r), pnl_r, car_r, float(cbps_r), netlong) + ((float(_tsig),) if TILT else ()))',1)
anchor6='"cost_ex", "netlong"]'
assert s.count(anchor6)==1
s=s.replace(anchor6,'"cost_ex", "netlong"] + (["sig_tilt"] if TILT else [])',1)

open(DST,"w",encoding="utf-8").write(s)
print("tilt device written", DST)
print("sha256", hashlib.sha256(s.encode("utf-8")).hexdigest())
