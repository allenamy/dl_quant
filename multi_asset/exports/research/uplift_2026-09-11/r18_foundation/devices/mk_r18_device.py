#!/usr/bin/env python3
"""mk_r18_device.py — generate the DERIVED device w10_sleeve_r18.py from the PINNED replay device by exact,
once-only string replacements (PREREG_r18 §1). With every knob at its default the derived device must reproduce
the pinned device BITWISE on rec and W (GATE P proves it at run time against the archived A0 arms).

Knobs: R18_ELIG (causal eligibility: ok = isfinite(y4[i-1, m])), R18_WARM (warm-up seat over ACTIVE legs only),
SMA / SBAND (harvest-EMA alpha / no-trade band, identical replacement text to r12's mk_device.py),
R18_INSTR (per-anchor aux record, never read by the book).
Usage: mk_r18_device.py <pinned w10_sleeve.py> <out w10_sleeve_r18.py> <PREREG md>
"""
import hashlib, sys, difflib, os
PIN, OUT, PREREG = sys.argv[1], sys.argv[2], sys.argv[3]
PIN_SHA = "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650"
PREREG_SHA = "51120518b72f70ce3f78c4ef1e68b0ec655c76eb385692befcf904d0d2883f6c"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(PREREG) == PREREG_SHA, ("PREREG SHA MISMATCH", sha(PREREG))
src = open(PIN, "rb").read()
assert hashlib.sha256(src).hexdigest() == PIN_SHA, ("PINNED DEVICE SHA MISMATCH", hashlib.sha256(src).hexdigest())
s = src.decode("utf-8")

def rep(old, new):
    global s
    n = s.count(old)
    assert n == 1, ("replacement anchor must occur exactly once", n, old[:90])
    s = s.replace(old, new)

# --- knobs (declared next to the other env knobs)
rep('SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)\n',
    'SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)\n'
    'R18_ELIG = int(os.environ.get("R18_ELIG", "0")); assert R18_ELIG in (0, 1)   # r18 N2: 1 = eligibility from the return that CLOSED at E (isfinite(y4[i-1, m])); 0 = pinned forward rule, bitwise\n'
    'R18_WARM = int(os.environ.get("R18_WARM", "0")); assert R18_WARM in (0, 1)   # r18 WU: 1 = warm-up seat is equal weight over the ACTIVE legs (LEGS mask applied inside the early return); 0 = pinned [1/3]*3\n'
    'R18_INSTR = int(os.environ.get("R18_INSTR", "0")); assert R18_INSTR in (0, 1)   # r18: per-anchor aux record only (rec/W untouched)\n'
    'SMA = float(os.environ.get("SMA", "0.1")); assert 0.0 < SMA <= 1.0, SMA        # r12-identical knob: harvest-EMA alpha; float("0.1") == 0.1 bitwise => default path unchanged\n'
    'SBAND = float(os.environ.get("SBAND", "2.5e-4")); assert 0.0 <= SBAND <= 4.0e-3, SBAND   # r12-identical knob: no-trade band (weight units); float("2.5e-4") == 2.5e-4 bitwise\n')
rep('        "FPRED": os.environ.get("FPRED", "(default f10_V2MAIN_s{FSEED})")}\n',
    '        "FPRED": os.environ.get("FPRED", "(default f10_V2MAIN_s{FSEED})")}\n'
    '_CFG["R18"] = {"R18_ELIG": R18_ELIG, "R18_WARM": R18_WARM, "R18_INSTR": R18_INSTR, "SMA": SMA, "SBAND": SBAND, "pinned_src_sha256": "' + PIN_SHA + '", "prereg_sha256": "' + PREREG_SHA + '",\n'
    '               "device": "w10_sleeve_r18.py = pinned w10_sleeve.py + {R18_ELIG, R18_WARM, R18_INSTR, SMA, SBAND}; all default => bitwise-unchanged rec/W (GATE P)"}\n')
# --- N2 in legs()
rep('        ok = np.isfinite(y4[i, m])\n        for leg in LR:\n',
    '        ok = ((np.isfinite(y4[i - 1, m]) if i >= 1 else np.zeros(len(m), bool)) if R18_ELIG else np.isfinite(y4[i, m]))   # r18 N2: causal = the 4h return that closed at E\n'
    '        for leg in LR:\n')
# --- N2 in run()
rep('        ok = np.isfinite(y4[i, m]); qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48\n',
    '        ok = ((np.isfinite(y4[i - 1, m]) if i >= 1 else np.zeros(len(m), bool)) if R18_ELIG else np.isfinite(y4[i, m])); qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48   # r18 N2\n')
# --- WU: LEGS mask inside the warm-up early return
rep('        if p < LOOK: return np.array([1/3]*3)\n',
    '        if p < LOOK:\n'
    '            if R18_WARM:   # r18 WU: equal weight over the ACTIVE legs only ([1/2, 0, 1/2] for LEGS=101; [1/3]*3 for LEGS=111)\n'
    '                _e = np.array([1.0 if c == "1" else 0.0 for c in LEGS]); return _e / max(_e.sum(), 1.0)\n'
    '            return np.array([1/3]*3)\n')
# --- SMA / SBAND, king chain (r12 text)
rep('        sm = H + 0.1 * (tgt - H); trade = sm - H\n'
    '        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H\n',
    '        sm = H + SMA * (tgt - H); trade = sm - H\n'
    '        sm = np.where(np.abs(trade) < SBAND, H, sm); trade = sm - H\n')
# --- SMA / SBAND, F10 chain (r12 text)
rep('                _smf = HF + 0.1 * (_tgtf - HF)\n'
    '                _trf = _smf - HF\n'
    '                _smf = np.where(np.abs(_trf) < 2.5e-4, HF, _smf)\n',
    '                _smf = HF + SMA * (_tgtf - HF)\n'
    '                _trf = _smf - HF\n'
    '                _smf = np.where(np.abs(_trf) < SBAND, HF, _smf)\n')
# --- instrumentation (read-only of the state)
rep('    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []\n',
    '    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []; _R18 = []\n')
rep('        netlong = float(sm.sum() / max(np.abs(sm).sum(), 1e-9))\n',
    '        if R18_INSTR:   # r18 aux: unknown-return exposure and eligibility-rule disagreement, per anchor (never read by the book)\n'
    '            _r18_liq = qv4h >= 2.5e5; _r18_old = np.isfinite(y4[i, m]); _r18_new = (np.isfinite(y4[i - 1, m]) if i >= 1 else np.zeros(len(m), bool))\n'
    '            _r18_un = sel & ~_r18_old\n'
    '            _R18.append((int(E_ts[i]), float(sel.sum()), float(_r18_un.sum()), float(np.abs(sm[m][_r18_un]).sum()), float(((_r18_old != _r18_new) & _r18_liq).sum()),\n'
    '                         float((_r18_new & ~_r18_old & _r18_liq).sum()), float((~_r18_new & _r18_old & _r18_liq).sum())))\n'
    '        netlong = float(sm.sum() / max(np.abs(sm).sum(), 1e-9))\n')
rep('    return np.array(rec), np.stack(WS), ((np.array(_SG), np.array(_SP), np.array(_SC), np.array(_SK)) if SLEEVE else None)\n',
    '    global R18_LAST; R18_LAST = _R18\n'
    '    return np.array(rec), np.stack(WS), ((np.array(_SG), np.array(_SP), np.array(_SC), np.array(_SK)) if SLEEVE else None)\n')
rep('    save[f"{nm}_rec"] = R\n    save[f"{nm}_W"] = WS\n',
    '    save[f"{nm}_rec"] = R\n    save[f"{nm}_W"] = WS\n'
    '    if R18_INSTR and R18_LAST:\n'
    '        save[f"{nm}_R18A"] = np.array(R18_LAST); save[f"{nm}_R18A_cols"] = np.array(["ts", "n_sel", "n_sel_y4nan", "gross_y4nan", "n_elig_changed", "n_elig_new_only", "n_elig_old_only"])\n')

open(OUT, "w", encoding="utf-8").write(s)
out_sha = sha(OUT)
diff = "".join(difflib.unified_diff(src.decode("utf-8").splitlines(True), s.splitlines(True), "w10_sleeve.py (pinned " + PIN_SHA[:16] + ")", "w10_sleeve_r18.py (" + out_sha[:16] + ")"))
open(os.path.splitext(OUT)[0] + ".diff", "w", encoding="utf-8").write(diff)
print("PINNED", PIN_SHA); print("PREREG", PREREG_SHA); print("DERIVED", out_sha); print("diff lines", diff.count("\n"))
