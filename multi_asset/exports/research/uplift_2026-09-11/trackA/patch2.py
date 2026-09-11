p = "/workspace/uplift_2026-09-11/w10_sleeve.py"; s = open(p).read()
def rep(o,n,c=1):
    global s; assert s.count(o)==c,(s.count(o),o[:70]); s=s.replace(o,n)
rep('assert FTRIM_TH in ("-0.0005", "-0.0010"', 'assert FTRIM_TH in ("-0.00001", "-0.0005", "-0.0010"')
rep('SLEEVE = int(os.environ.get("SLEEVE", "0")); assert SLEEVE in (0, 1)',
    'FTPOS = int(os.environ.get("FTPOS", "0")); assert FTPOS in (0, 1)\nSLEEVE = int(os.environ.get("SLEEVE", "0")); assert SLEEVE in (0, 1)')
rep('_CFG = {"LTRIM_TH": LTRIM_TH,', '_CFG = {"FTPOS": FTPOS, "LTRIM_TH": LTRIM_TH,')
rep('        _smk = sm  ', '''        if FTPOS:
            _kill = np.zeros(NW, bool); _kill[m] = (smb[m] < 0) & (_fnp <= FTRIM_TH)
            if _kill.any():
                _gk0 = np.abs(smb).sum(); smb = np.where(_kill, 0.0, smb); _gk1 = np.abs(smb).sum()
                if _gk1 > 1e-9: smb = smb * (_gk0 / _gk1)
        _smk = sm  ''')
open(p,"w").write(s); print("patched ok")
