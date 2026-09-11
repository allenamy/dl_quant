import hashlib, os
SRC = "/workspace/review_scratch/health_check/w10_health.py"
DST = "/workspace/uplift_2026-09-11/w10_sleeve.py"
s = open(SRC).read()
src_sha = hashlib.sha256(s.encode()).hexdigest()

def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90])
    s = s.replace(old, new)

# --- 1. env knobs (default off => bitwise-unchanged path) ---
old = '''FTRIM = os.environ.get("FTRIM", "off"); assert FTRIM in ("off", "zero"), FTRIM'''
new = '''FTRIM = os.environ.get("FTRIM", "off"); assert FTRIM in ("off", "zero"), FTRIM
LTRIM_TH = os.environ.get("LTRIM_TH", "")   # uplift TrackA: long-side mirror of FTRIM. z>0 and rn8 >= LTRIM_TH => z=0 (both chains). Whitelist only.
assert LTRIM_TH in ("", "0.0005", "0.0010", "0.0020", "0.0030", "0.0050", "0.0100"), LTRIM_TH
LTRIM_TH = float(LTRIM_TH) if LTRIM_TH else None
CDAMP = float(os.environ.get("CDAMP", "0")); assert CDAMP in (0.0, 0.25, 0.5, 1.0, 2.0, 4.0), CDAMP   # uplift TrackA: z /= (1 + CDAMP * max(0, sign(z)*rn8)/0.0010) = alpha-per-unit-carry sizing
FTRIM_TH = os.environ.get("FTRIM_TH", "-0.0010"); assert FTRIM_TH in ("-0.0005", "-0.0010", "-0.0020", "-0.0030", "-0.0050", "-0.0100"), FTRIM_TH
FTRIM_TH = float(FTRIM_TH)
SLEEVE = int(os.environ.get("SLEEVE", "0")); assert SLEEVE in (0, 1)   # uplift TrackA: per-sleeve pnl/carry/cost/gross instrument (pure diagnostic, book untouched)'''
rep(old, new)

# --- 2. self-report config ---
rep('''_CFG = {"COSTB_JSON": COSTB_JSON,''', '''_CFG = {"LTRIM_TH": LTRIM_TH, "CDAMP": CDAMP, "FTRIM_TH": FTRIM_TH, "SLEEVE": SLEEVE, "COSTB_JSON": COSTB_JSON,''')
rep('''_CFG["HEALTH"] = {"device": "w10_health.py''', '''_CFG["UPLIFT"] = {"device": "w10_sleeve.py = w10_health.py (sha256 %s) + {LTRIM_TH, CDAMP, FTRIM_TH, SLEEVE}; all unset/0 and FTRIM_TH=-0.0010 => bitwise-unchanged rec/W", "src_sha256": "%s", "self_sha256": None}
_CFG["HEALTH"] = {"device": "w10_health.py''' % (src_sha[:16], src_sha))
rep('''"device_sha256": _hl.sha256(open(__file__, "rb").read()).hexdigest()}''',
    '''"device_sha256": _hl.sha256(open(__file__, "rb").read()).hexdigest()}
_CFG["UPLIFT"]["self_sha256"] = _CFG["HEALTH"]["device_sha256"]''')

# --- 3. king-book z: FTRIM threshold param + LTRIM + CDAMP ---
old = '''        if FTRIM == "zero":
            _fnp = FN[j, m] * (8.0 / np.where(IV[j, m] > 0, IV[j, m], 8.0)); _fnp = np.where(np.isfinite(_fnp), _fnp, 0.0)
            z = np.where((z < 0) & (_fnp <= -0.0010), 0.0, z)'''
new = '''        _fnp = FN[j, m] * (8.0 / np.where(IV[j, m] > 0, IV[j, m], 8.0)); _fnp = np.where(np.isfinite(_fnp), _fnp, 0.0)   # 8h-equivalent current rate on the member set (was computed inside the FTRIM branch; hoisting is numerically a no-op)
        if FTRIM == "zero":
            z = np.where((z < 0) & (_fnp <= FTRIM_TH), 0.0, z)
        if LTRIM_TH is not None:
            z = np.where((z > 0) & (_fnp >= LTRIM_TH), 0.0, z)
        if CDAMP > 0:
            z = z / (1.0 + CDAMP * np.maximum(0.0, np.sign(z) * _fnp) / 0.0010)'''
rep(old, new)

# --- 4. F10-book _zf: same three ---
old = '''            if FTRIM == "zero":
                _zf = np.where((_zf < 0) & (_fnp <= -0.0010), 0.0, _zf)'''
new = '''            if FTRIM == "zero":
                _zf = np.where((_zf < 0) & (_fnp <= FTRIM_TH), 0.0, _zf)
            if LTRIM_TH is not None:
                _zf = np.where((_zf > 0) & (_fnp >= LTRIM_TH), 0.0, _zf)
            if CDAMP > 0:
                _zf = _zf / (1.0 + CDAMP * np.maximum(0.0, np.sign(_zf) * _fnp) / 0.0010)'''
rep(old, new)

# --- 5. sleeve accumulation (ex caliber = the judge's numerator) ---
old = '''        netlong = float(sm.sum() / max(np.abs(sm).sum(), 1e-9))'''
new = '''        if SLEEVE:
            _sw = smr[m]; _rn = fnow * (8.0 / ivv); _fin = np.isfinite(FN[j, m])
            _b = np.full(len(m), 6, np.int64)   # 6 = no funding quote
            _b[_fin & (_rn <= -0.0030)] = 0
            _b[_fin & (_rn > -0.0030) & (_rn <= -0.0010)] = 1
            _b[_fin & (_rn > -0.0010) & (_rn < 0.0)] = 2
            _b[_fin & (_rn >= 0.0) & (_rn < 0.0010)] = 3
            _b[_fin & (_rn >= 0.0010) & (_rn < 0.0030)] = 4
            _b[_fin & (_rn >= 0.0030)] = 5
            _k = np.where(_sw < 0, 7, 0) + _b
            _rate = np.array([fr * mk + (1 - fr) * tk for (mk, tk, fr) in COST_B])[tr]
            _SG.append(np.bincount(_k, np.abs(_sw), 14)); _SP.append(np.bincount(_k, _sw * yv * 1e4, 14))
            _SC.append(np.bincount(_k, _sw * fnow * (4.0 / ivv) * 1e4, 14)); _SK.append(np.bincount(_k, tabs_r * _rate, 14))
            assert abs(_SP[-1].sum() - pnl_r) < 1e-7 and abs(_SC[-1].sum() - car_r) < 1e-7 and abs(_SK[-1].sum() - cbps_r) < 1e-7, "sleeve identity"
        netlong = float(sm.sum() / max(np.abs(sm).sum(), 1e-9))'''
rep(old, new)
rep('''    rec = []; WS = []''', '''    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []''')
rep('''    return np.array(rec), np.stack(WS)''', '''    return np.array(rec), np.stack(WS), ((np.array(_SG), np.array(_SP), np.array(_SC), np.array(_SK)) if SLEEVE else None)''')
rep('''    R, WS = run(SLOW, LRa, pos, d, n_, c)''', '''    R, WS, SLV = run(SLOW, LRa, pos, d, n_, c)''')
rep('''    save[f"{nm}_rec"] = R
    save[f"{nm}_W"] = WS''', '''    save[f"{nm}_rec"] = R
    save[f"{nm}_W"] = WS
    if SLV is not None:
        save[f"{nm}_SLV_gross"], save[f"{nm}_SLV_pnl"], save[f"{nm}_SLV_carry"], save[f"{nm}_SLV_cost"] = SLV
        save[f"{nm}_SLV_names"] = np.array(["L|<=-30bp", "L|-30..-10", "L|-10..0", "L|0..10", "L|10..30", "L|>=30bp", "L|nofund",
                                            "S|<=-30bp", "S|-30..-10", "S|-10..0", "S|0..10", "S|10..30", "S|>=30bp", "S|nofund"])''')
open(DST, "w").write(s)
print("written", DST, "src_sha", src_sha[:16], "dst_sha", hashlib.sha256(s.encode()).hexdigest()[:16])
