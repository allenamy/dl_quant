#!/usr/bin/env python3
"""mk_t5_device.py — generate the T5 replay device from the T1 device (PREREG_T5 §9 step 2).
usage: python mk_t5_device.py <w10_sleeve_t1.py> <out w10_sleeve_t5.py> <PREREG_T5_deployed_carry_gap_2026-09-13.md>
Adds only T5_DUMP=1: for anchors 2026-08-25 20Z..08-30 20Z of the stop-layer arm (d30_n2_c42) it records the chain's entering states
(H, HF, per-leg HL/HFL), the realized stop-block mask, every per-anchor ingredient (members, seat, eligibility, liquidity, raw score / fund /
funding rows) and the resulting books (king-chain sm, F10-chain sm, blend, smr, per-leg books). rec / W / T1 arrays are never written by the
new code (GATE G-P checks bitwise). Every replacement must match exactly once (asserted).
"""
import sys, hashlib
SRC, DST, PREREG = sys.argv[1], sys.argv[2], sys.argv[3]
T1_SHA = "0a8114398e7626abe27a3294c1508e1a46bf2f7c2a6fdbda318bc9a262ca00e3"
PREREG_SHA = "33b20fa10109b95d9b4f0ff480619d82cd9bd1b7d2def7cf0a38c7938e83660f"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(SRC) == T1_SHA, ("T1 device sha", sha(SRC))
assert sha(PREREG) == PREREG_SHA, ("T5 prereg sha", sha(PREREG))
s = open(SRC).read()
REP = []
REP.append(('T1_INSTR = int(os.environ.get("T1_INSTR", "0")); assert T1_INSTR in (0, 1)   # T1: per-leg exact-additive component books (rec/W untouched)\n',
            'T1_INSTR = int(os.environ.get("T1_INSTR", "0")); assert T1_INSTR in (0, 1)   # T1: per-leg exact-additive component books (rec/W untouched)\n'
            'T5_DUMP = int(os.environ.get("T5_DUMP", "0")); assert T5_DUMP in (0, 1)   # T5: window dump 2026-08-25 20Z..08-30 20Z (rec/W/T1 arrays untouched)\n'
            'T5_LO, T5_HI = 1787688000, 1788120000\n'))
REP.append(('print("CONFIG " + json.dumps(_CFG), flush=True)   # E-0826-C/D: 装置必须自报全部生效配置\n',
            '_CFG["T5"] = {"T5_DUMP": T5_DUMP, "t1_src_sha256": "%s", "prereg_sha256": "%s", "window": [T5_LO, T5_HI], "device": "w10_sleeve_t5.py = w10_sleeve_t1.py + T5_DUMP window dump; default => bitwise-unchanged; PREREG_T5 §9"}\n'
            'if T5_DUMP:\n'
            '    assert T1_INSTR == 1, "T5_DUMP requires T1_INSTR=1 (per-leg states are dumped)"\n'
            'print("CONFIG " + json.dumps(_CFG), flush=True)   # E-0826-C/D: 装置必须自报全部生效配置\n' % (T1_SHA, PREREG_SHA)))
REP.append(('    _T1 = bool(T1_INSTR and depth is not None)   # T1: instrument the stop-layer arm only (the archived A0 = d30_n2_c42)\n',
            '    _T1 = bool(T1_INSTR and depth is not None)   # T1: instrument the stop-layer arm only (the archived A0 = d30_n2_c42)\n'
            '    _T5 = bool(T5_DUMP and depth is not None); T5D = {}\n'))
REP.append(('        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}\n',
            '        sc = {"king": SLOW[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}\n'
            '        _t5w = bool(_T5 and T5_LO <= int(E_ts[i]) <= T5_HI)\n'
            '        if _t5w:\n'
            '            _t5 = dict(ts=int(E_ts[i]), i=int(i), j=int(j), H_in=H.copy(), HF_in=HF.copy(), HL_in=HL.copy(), HFL_in=HFL.copy(), bl=(su > i).copy())\n'))
REP.append(('        H = _smk if PHI > 0 else sm      # king 书 EMA 态独立推进(φ=0 时二者同一)\n',
            '        if _t5w:\n'
            '            _mm = np.zeros(NW, bool); _mm[m] = True\n'
            '            _selm = np.zeros(NW, bool); _selm[m[sel]] = True\n'
            '            _okm = np.zeros(NW, bool); _okm[m[ok]] = True\n'
            '            _qv = np.full(NW, np.nan); _qv[m] = qv4h\n'
            '            _umr = UMASK_ROW.get(j) if UMASK_ROW is not None else None\n'
            '            _t5.update(mem=_mm, sel=_selm, ok=_okm, qv4h=_qv, capw=float(capw), w3=np.array(w3, dtype=float), SLOW=np.array(SLOW[i]), F10P=np.array(F10P[i]), FE=np.array(FE[j]), FN=np.array(FN[j]), IV=np.array(IV[j]),\n'
            '                       R24=np.array(R24[j]), Y4=np.array(y4[i]), Y4P=np.array(y4[i - 1]), QVK=np.array(qvk[i]), UM=(np.array(_umr) if _umr is not None else np.ones(NW, bool)), has_um=bool(_umr is not None),\n'
            '                       smk=_smk.copy(), smf=HF.copy(), smb=sm.copy(), smr=smr.copy(), SMC_out=SMC.copy(), SMFC_out=HFL.copy(), SMRC=SMRC.copy(), rec=np.array(rec[-1], dtype=float))\n'
            '            for _k, _v in _t5.items(): T5D.setdefault(_k, []).append(_v)\n'
            '        H = _smk if PHI > 0 else sm      # king 书 EMA 态独立推进(φ=0 时二者同一)\n'))
REP.append(('    global T1_LAST; T1_LAST = ',
            '    global T5_LAST; T5_LAST = ({_k: np.array(_v) for _k, _v in T5D.items()} if _T5 else None)\n'
            '    global T1_LAST; T1_LAST = '))
REP.append(('        for _k, _v in T1_LAST.items(): save[f"{nm}_{_k}"] = _v\n',
            '        for _k, _v in T1_LAST.items(): save[f"{nm}_{_k}"] = _v\n'
            '    if T5_DUMP and T5_LAST is not None:\n'
            '        for _k, _v in T5_LAST.items(): save[f"{nm}_T5_{_k}"] = _v\n'))
for a, b in REP:
    n = s.count(a); assert n == 1, ("replacement must match exactly once", n, a[:90])
    s = s.replace(a, b)
open(DST, "w").write(s)
print("wrote", DST, "sha256", hashlib.sha256(s.encode()).hexdigest(), "replacements", len(REP))
