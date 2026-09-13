#!/usr/bin/env python3
"""mk_t2_device.py — generate the T2 derived device w10_sleeve_t2.py from the r18 derived device by exact, once-only
string replacements (PREREG_T2 §1/§3). With T2_MODE=off (default) the T2 device must reproduce the r18 device, hence the
pinned device and the archived A0 / NW arms, BITWISE on rec and W (GATE P). Knobs:
  T2_MODE  off | name | seat      name = ARM-N / ARM-Nσ (fund-leg score = 829-base rank of lam+ x FZ - kappa x carry, both chains)
                                  seat = ARM-SK (seat input = price LR - kappa_i x leg rank-book carry over the trailing window)
  T2_KPATH path npz written by t2_kappa.py (per-anchor active/kappa/lam on the meta axis; E_ts asserted)
  T2_KCOL  scalar | sigma         which path column
  T2_KFORCE "" | 0 | 1            positive controls (PC-0 / PC-1 / WIRE); seat: forced at every anchor; name: forced where the path is active
  T2_INSTR 0 | 1                  per-anchor aux + FZ_book at 12 fixed rec rows (never read by the book)
  T2_CLEAD -1 | 0 | 1             §7 tripwire only: carry input of the name adjustment from panel row j+CLEAD
Usage: mk_t2_device.py <r18 device w10_sleeve_r18.py> <out w10_sleeve_t2.py> <PREREG_T2 md>
"""
import hashlib, sys, difflib, os
PAR, OUT, PREREG = sys.argv[1], sys.argv[2], sys.argv[3]
PAR_SHA = "9b8a6323e8f0ac31ecb4046f6759dce09ba89645cbfc356db71f51c662b2c5c4"
PREREG_SHA = "981293b02b2ddae6574fa6dcf8db9b09a65cfa9f122a8b72d7e604ad5ec87eca"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(PREREG) == PREREG_SHA, ("PREREG SHA MISMATCH", sha(PREREG))
src = open(PAR, "rb").read()
assert hashlib.sha256(src).hexdigest() == PAR_SHA, ("R18 DEVICE SHA MISMATCH", hashlib.sha256(src).hexdigest())
s = src.decode("utf-8")
NREP = [0]
def rep(old, new):
    global s
    n = s.count(old)
    assert n == 1, ("replacement anchor must occur exactly once", n, old[:100])
    s = s.replace(old, new); NREP[0] += 1

# 1 --- knobs
rep('SBAND = float(os.environ.get("SBAND", "2.5e-4")); assert 0.0 <= SBAND <= 4.0e-3, SBAND   # r12-identical knob: no-trade band (weight units); float("2.5e-4") == 2.5e-4 bitwise\n',
    'SBAND = float(os.environ.get("SBAND", "2.5e-4")); assert 0.0 <= SBAND <= 4.0e-3, SBAND   # r12-identical knob: no-trade band (weight units); float("2.5e-4") == 2.5e-4 bitwise\n'
    'T2_MODE = os.environ.get("T2_MODE", "off"); assert T2_MODE in ("off", "name", "seat"), T2_MODE   # T2 carry-net sizing (PREREG_T2 §3); off => bitwise r18 device\n'
    'T2_KPATH = os.environ.get("T2_KPATH", ""); T2_KCOL = os.environ.get("T2_KCOL", "scalar"); assert T2_KCOL in ("scalar", "sigma"), T2_KCOL\n'
    'T2_KFORCE = os.environ.get("T2_KFORCE", ""); assert T2_KFORCE in ("", "0", "1"), T2_KFORCE   # PC-0 / PC-1 / WIRE positive controls\n'
    'T2_INSTR = int(os.environ.get("T2_INSTR", "0")); assert T2_INSTR in (0, 1)\n'
    'T2_CLEAD = int(os.environ.get("T2_CLEAD", "0")); assert T2_CLEAD in (-1, 0, 1), T2_CLEAD   # PREREG_T2 §7 tripwire only (name mode)\n'
    'assert (T2_MODE == "off") == (T2_KPATH == ""), ("T2_KPATH must be set iff T2_MODE != off", T2_MODE, T2_KPATH)\n'
    'assert T2_MODE != "seat" or T2_KCOL == "scalar", "seat mode reads the scalar path only (PREREG_T2 §3)"\n'
    'assert T2_MODE == "name" or T2_CLEAD == 0, "T2_CLEAD applies to name mode only (PREREG_T2 §7)"\n'
    'assert T2_MODE != "off" or (T2_KFORCE == "" and T2_INSTR == 0 and T2_KCOL == "scalar"), "T2 knobs set while T2_MODE=off"\n')

# 2 --- self-report
rep('               "device": "w10_sleeve_r18.py = pinned w10_sleeve.py + {R18_ELIG, R18_WARM, R18_INSTR, SMA, SBAND}; all default => bitwise-unchanged rec/W (GATE P)"}\n',
    '               "device": "w10_sleeve_r18.py = pinned w10_sleeve.py + {R18_ELIG, R18_WARM, R18_INSTR, SMA, SBAND}; all default => bitwise-unchanged rec/W (GATE P)"}\n'
    '_CFG["T2"] = {"T2_MODE": T2_MODE, "T2_KPATH": T2_KPATH, "T2_KCOL": T2_KCOL, "T2_KFORCE": T2_KFORCE, "T2_INSTR": T2_INSTR, "T2_CLEAD": T2_CLEAD,\n'
    '              "T2_KPATH_sha256": (__import__("hashlib").sha256(open(T2_KPATH, "rb").read()).hexdigest() if T2_KPATH else None),\n'
    '              "parent_r18_sha256": "' + PAR_SHA + '", "prereg_sha256": "' + PREREG_SHA + '",\n'
    '              "device": "w10_sleeve_t2.py = r18 derived device + {T2_MODE, T2_KPATH, T2_KCOL, T2_KFORCE, T2_INSTR, T2_CLEAD}; T2_MODE=off => bitwise r18 device (GATE P)"}\n')

# 3 --- path load (needs E_ts)
rep('E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]\n',
    'E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]\n'
    'if T2_MODE != "off":   # T2: per-anchor path on the meta axis written by t2_kappa.py; alignment and ranges asserted\n'
    '    _t2z = np.load(T2_KPATH, allow_pickle=True)\n'
    '    assert np.array_equal(_t2z["E_ts"].astype(np.int64), E_ts), "T2 path E_ts != meta E_ts"\n'
    '    _T2_ACT = np.asarray(_t2z["active_" + T2_KCOL], bool); _T2_KAP = np.asarray(_t2z["kappa_" + T2_KCOL], np.float64); _T2_LAM = np.asarray(_t2z["lam_" + T2_KCOL], np.float64)\n'
    '    assert _T2_ACT.shape == _T2_KAP.shape == _T2_LAM.shape == E_ts.shape\n'
    '    assert np.all(np.isfinite(_T2_KAP[_T2_ACT])) and np.all(np.isfinite(_T2_LAM[_T2_ACT])) and np.all((_T2_KAP[_T2_ACT] >= 0.0) & (_T2_KAP[_T2_ACT] <= 1.0)) and np.all(_T2_LAM[_T2_ACT] >= 0.0), "T2 path out of range"\n'
    '    if T2_KFORCE != "":\n'
    '        _T2_KAP = np.where(_T2_ACT, np.float64(T2_KFORCE), _T2_KAP)   # name mode: forced kappa where active (lam from the path); seat mode forces at every anchor in _t2_seat_kappa\n'
    '    print(f"T2 path loaded: mode={T2_MODE} col={T2_KCOL} force={T2_KFORCE!r} clead={T2_CLEAD} active {int(_T2_ACT.sum())}/{len(_T2_ACT)}", flush=True)\n'
    'T2_WIRE_ROWS = frozenset(900 + 745 * _k for _k in range(12))\n'
    'T2C_ARR = None\n'
    'def _t2_seat_kappa(i):\n'
    '    return float(T2_KFORCE) if T2_KFORCE != "" else (float(_T2_KAP[i]) if _T2_ACT[i] else 0.0)\n')

# 4 --- legs(): keep the leg rank-book carry separately in seat mode (the exact SEATNET quantity)
rep('    LR = {l: [] for l in ("king", "rev24", "fund", "f10")}; idx = []\n',
    '    LR = {l: [] for l in ("king", "rev24", "fund", "f10")}; idx = []; _T2C = {l: [] for l in ("king", "rev24", "fund", "f10")}\n')
rep('            LR[leg].append(_lr)\n        idx.append(i)\n    return {k: np.array(v) for k, v in LR.items()}, {int(i): p for p, i in enumerate(idx)}\n',
    '            LR[leg].append(_lr)\n'
    '            if T2_MODE == "seat":   # T2 ARM-SK: unit-gross rank-book 4h carry of the leg = the expression SEATNET subtracts, stored apart; w3_at applies the current kappa\n'
    '                _T2C[leg].append(float((z / g * np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / _IVf[j, m])).sum() * 1e4) if g > 1e-9 else 0.0)\n'
    '        idx.append(i)\n'
    '    global T2C_ARR; T2C_ARR = {k: np.array(v) for k, v in _T2C.items()}\n'
    '    return {k: np.array(v) for k, v in LR.items()}, {int(i): p for p, i in enumerate(idx)}\n')

# 5 --- w3_at(): seat input net of kappa_i x carry over the trailing window
rep('        r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])\n        if WRULE == "iv":\n',
    '        r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])\n'
    '        if T2_MODE == "seat":   # T2 ARM-SK (PREREG_T2 §3): current kappa on the whole trailing window; kappa=1 == SEATNET=1 elementwise, kappa=0 == A0\n'
    '            _k2 = _t2_seat_kappa(i)\n'
    '            r = np.stack([LRa["king"][sl] - _k2 * T2C_ARR["king"][sl], LRa["rev24"][sl] - _k2 * T2C_ARR["rev24"][sl], LRa["fund"][sl] - _k2 * T2C_ARR["fund"][sl]])\n'
    '        if WRULE == "iv":\n')

# 6 --- run(): aux containers
rep('    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []; _R18 = []\n',
    '    rec = []; WS = []; _SG = []; _SP = []; _SC = []; _SK = []; _R18 = []; _T2A = []; _T2W = {}\n')

# 7 --- run(): name-mode fund score
rep('        FZ = FZB(j, m) if UMASK_SCOPE == "m1" else xz(sc["fund"])   # fund z used by both books and the leg-contribution diagnostic\n',
    '        FZ = FZB(j, m) if UMASK_SCOPE == "m1" else xz(sc["fund"])   # fund z used by both books and the leg-contribution diagnostic\n'
    '        _FZ0 = FZ   # T2: the leg-contribution diagnostic keeps the unadjusted fund score\n'
    '        _t2_used = False\n'
    '        if T2_MODE == "name" and _T2_ACT[i] and not (_T2_LAM[i] == 0.0 and _T2_KAP[i] == 0.0):   # T2 ARM-N / ARM-Nσ: 829-base rank of expected net = lam+ x FZ - kappa x carry (PREREG_T2 §3)\n'
    '            assert UMASK_SCOPE == "m1", "T2 name mode is defined for the m1 fund score only"\n'
    '            _t2_jc = j + T2_CLEAD\n'
    '            _t2_c = (np.nan_to_num(FN[_t2_jc, :], nan=0.0) * (4.0 / _IVf[_t2_jc, :])) if 0 <= _t2_jc < FN.shape[0] else np.zeros(FN.shape[1], np.float32)\n'
    '            FZ = xz(_T2_LAM[i] * xz(FE[j, :]) - _T2_KAP[i] * _t2_c)[m]\n'
    '            _t2_used = True\n')

# 8 --- leg-contribution diagnostic keeps the unadjusted score
rep('            zz = np.nan_to_num(FZ if leg == "fund" else xz(sc[leg])); gl = np.abs(zz).sum()\n',
    '            zz = np.nan_to_num(_FZ0 if leg == "fund" else xz(sc[leg])); gl = np.abs(zz).sum()\n')

# 9 --- per-anchor aux (read-only of the state)
rep('        netlong = float(sm.sum() / max(np.abs(sm).sum(), 1e-9))\n',
    '        if T2_INSTR:   # T2 aux: path use and score-change size per anchor, FZ_book at 12 fixed rec rows (never read by the book)\n'
    '            _f0 = np.asarray(_FZ0, np.float64); _f1 = np.asarray(FZ, np.float64); _okf = np.isfinite(_f0) & np.isfinite(_f1)\n'
    '            _cc = float(np.corrcoef(_f0[_okf], _f1[_okf])[0, 1]) if (_t2_used and _okf.sum() > 2) else 1.0\n'
    '            _nm_act = bool(T2_MODE == "name" and _T2_ACT[i])\n'
    '            _T2A.append((int(E_ts[i]), float(_t2_used), float(_T2_KAP[i]) if _nm_act else float("nan"), float(_T2_LAM[i]) if _nm_act else float("nan"),\n'
    '                         float((_okf & (_f0 != _f1)).sum()), float(np.abs(_f1[_okf] - _f0[_okf]).mean()) if _okf.any() else 0.0, _cc,\n'
    '                         float(_t2_seat_kappa(i)) if T2_MODE == "seat" else float("nan"), float(w3[0])))\n'
    '            if len(rec) in T2_WIRE_ROWS: _T2W[len(rec)] = (int(E_ts[i]), np.array(m, np.int64), _f1.copy())\n'
    '        netlong = float(sm.sum() / max(np.abs(sm).sum(), 1e-9))\n')

# 10 --- export aux from run()
rep('    global R18_LAST; R18_LAST = _R18\n',
    '    global R18_LAST; R18_LAST = _R18\n'
    '    global T2_LAST, T2W_LAST; T2_LAST = _T2A; T2W_LAST = _T2W\n')

# 11 --- save aux
rep('    save[f"{nm}_rec"] = R\n    save[f"{nm}_W"] = WS\n',
    '    save[f"{nm}_rec"] = R\n    save[f"{nm}_W"] = WS\n'
    '    if T2_INSTR and T2_LAST:\n'
    '        save[f"{nm}_T2A"] = np.array(T2_LAST); save[f"{nm}_T2A_cols"] = np.array(["ts", "name_path_used", "kappa_name", "lam_name", "n_fz_changed", "mean_abs_dfz", "corr_fz_book_vs_fz", "kappa_seat", "w3_king"])\n'
    '        _wr = sorted(T2W_LAST); save[f"{nm}_T2W_rows"] = np.array(_wr, np.int64); save[f"{nm}_T2W_ts"] = np.array([T2W_LAST[_r][0] for _r in _wr], np.int64)\n'
    '        _wf = np.full((len(_wr), NW), np.nan)\n'
    '        for _q, _r in enumerate(_wr): _wf[_q, T2W_LAST[_r][1]] = T2W_LAST[_r][2]\n'
    '        save[f"{nm}_T2W_fz"] = _wf\n'
    '    if T2_MODE == "seat": save["T2C_king"], save["T2C_rev24"], save["T2C_fund"] = T2C_ARR["king"], T2C_ARR["rev24"], T2C_ARR["fund"]\n')

open(OUT, "w", encoding="utf-8").write(s)
out_sha = sha(OUT)
diff = "".join(difflib.unified_diff(src.decode("utf-8").splitlines(True), s.splitlines(True), "w10_sleeve_r18.py (" + PAR_SHA[:16] + ")", "w10_sleeve_t2.py (" + out_sha[:16] + ")"))
open(os.path.splitext(OUT)[0] + ".diff", "w", encoding="utf-8").write(diff)
print("PARENT_R18", PAR_SHA); print("PREREG", PREREG_SHA); print("DERIVED_T2", out_sha); print("replacements", NREP[0], "diff lines", diff.count("\n"))
