#!/usr/bin/env python3
"""mk_r17_device.py — generate the DERIVED device w10_sleeve_r17.py from the PINNED replay device by exact, once-only
string replacements (PREREG_r17 §3). With R17_FILL=0 (and R17_X1=0) the derived device must reproduce the pinned
device BITWISE on rec and W (GATE P1). Knobs (all additive):
  R17_FILL=1        execute only f_hat x intent per name per anchor (intent = target book - executed book); the
                    unfilled residual is NOT chased (policy A): it re-enters next anchor's intent. Dust floor applied.
  R17_TABLE         path of the fitted fill table (r17_fill_table.json); its sha256 is self-reported in config_json
  R17_MODE          det | stoch   (stoch: f drawn from the cell's live empirical distribution, weights = intent)
  R17_SEED          int, default_rng([20260912, R17_SEED]) for stoch
  R17_GROSS_USDT    book USDT scale for the dust floor and participation (default 232000 = NAV 116k x 2.0)
  R17_X1=1          r16 ARM-X1 operator verbatim (de-risk names jump to target on both chains), no null, no aux
  R17_INSTR=1       per-anchor instrument (intent/executed turnover, residual, dust, class sums, residual ages)
Usage: python mk_r17_device.py <pinned w10_sleeve.py> <out w10_sleeve_r17.py>
"""
import hashlib, sys, difflib, os
PIN = sys.argv[1]; OUT = sys.argv[2]
PIN_SHA = "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650"
PREREG_SHA = "a7533b922c68e6dc575b1eadd3d19f62d4d271393ec5d58621c31aa65f5ae272"
AMEND1_SHA = "70c8142ac4595fb4e83659daaa83cd3a68ba1284f103fd77ba3a14ba3f3269bd"
src = open(PIN, "rb").read()
assert hashlib.sha256(src).hexdigest() == PIN_SHA, ("PINNED DEVICE SHA MISMATCH", hashlib.sha256(src).hexdigest())
s = src.decode("utf-8")
def rep(old, new):
    global s
    n = s.count(old); assert n == 1, ("replacement anchor must occur exactly once", n, old[:90]); s = s.replace(old, new)

# 1. knobs
rep('SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)\n',
    'SEATNET = int(os.environ.get("SEATNET", "0")); assert SEATNET in (0, 1)\n'
    'R17_FILL = int(os.environ.get("R17_FILL", "0")); assert R17_FILL in (0, 1)   # r17: partial-fill execution (PREREG_r17 §3); 0 = bitwise-neutral\n'
    'R17_TABLE = os.environ.get("R17_TABLE")   # r17: fitted fill table json (required when R17_FILL=1)\n'
    'R17_MODE = os.environ.get("R17_MODE", "det"); assert R17_MODE in ("det", "stoch"), R17_MODE\n'
    'R17_SEED = int(os.environ.get("R17_SEED", "0"))\n'
    'R17_G = float(os.environ.get("R17_GROSS_USDT", "232000"))\n'
    'R17_X1 = int(os.environ.get("R17_X1", "0")); assert R17_X1 in (0, 1)   # r17: r16 ARM-X1 operator (de-risk names jump to target), verbatim\n'
    'R17_INSTR = int(os.environ.get("R17_INSTR", "0")); assert R17_INSTR in (0, 1)   # r17: per-anchor instrument, additive, never read by the book\n'
    'assert not (R17_FILL and not R17_TABLE), "R17_FILL=1 requires R17_TABLE"\n'
    'import hashlib as _hl17\n'
    'R17_PREREG_SHA = "' + PREREG_SHA + '"; R17_AMEND1_SHA = "' + AMEND1_SHA + '"\n'
    'R17_PREREG_PATH = os.environ.get("R17_PREREG_PATH", "/workspace/uplift_2026-09-11/r17_fill_pricing/PREREG_r17_fill_pricing_2026-09-12.md")\n'
    'R17_AMEND1_PATH = os.environ.get("R17_AMEND1_PATH", "/workspace/uplift_2026-09-11/r17_fill_pricing/PREREG_AMENDMENT_1_r17_2026-09-12.md")\n'
    'assert _hl17.sha256(open(R17_PREREG_PATH, "rb").read()).hexdigest() == R17_PREREG_SHA, "PREREG r17 sha mismatch"\n'
    'assert _hl17.sha256(open(R17_AMEND1_PATH, "rb").read()).hexdigest() == R17_AMEND1_SHA, "PREREG r17 AMENDMENT 1 sha mismatch"\n'
    'R17_TABLE_SHA = _hl17.sha256(open(R17_TABLE, "rb").read()).hexdigest() if R17_TABLE else None\n')
# 2. self-report
rep('        "FPRED": os.environ.get("FPRED", "(default f10_V2MAIN_s{FSEED})")}\n',
    '        "FPRED": os.environ.get("FPRED", "(default f10_V2MAIN_s{FSEED})")}\n'
    '_CFG["R17"] = {"device": "w10_sleeve_r17.py = w10_sleeve.py (sha256 ' + PIN_SHA + ') + {R17_FILL, R17_TABLE, R17_MODE, R17_SEED, R17_GROSS_USDT, R17_X1, R17_INSTR}; all off => bitwise-unchanged rec/W (GATE P1)",\n'
    '               "pinned_src_sha256": "' + PIN_SHA + '", "prereg_sha256": R17_PREREG_SHA, "amendment1_sha256": R17_AMEND1_SHA, "R17_FILL": R17_FILL, "R17_TABLE": R17_TABLE, "R17_TABLE_SHA256": R17_TABLE_SHA,\n'
    '               "R17_MODE": R17_MODE, "R17_SEED": R17_SEED, "R17_GROSS_USDT": R17_G, "R17_X1": R17_X1, "R17_INSTR": R17_INSTR}\n')
# 3. table + per-anchor liquidity (after meta load; qvk is the v4 meta array, same lineage the fill model was tiered on)
rep('yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829\n',
    'yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts]); nA = len(E_ts); NW = 829\n'
    '_R17_QV4 = None; _R17_FHAT = None; _R17_EMPF = None; _R17_EMPC = None; _R17_PC = None; _R17_FLOOR = None; _R17_RNG = None\n'
    'if R17_FILL:\n'
    '    _tb = json.load(open(R17_TABLE)); assert _tb["prereg_sha256"] == R17_PREREG_SHA, "fill table was fitted under a different prereg"\n'
    '    assert _tb["classes"] == ["ADD", "DERISK", "FLIP", "ZERO_TARGET"] and _tb["tiers"] == [0, 1, 2] and abs(float(_tb["G_USDT"]) - R17_G) < 1e-6, ("table/knob mismatch", _tb.get("G_USDT"), R17_G)\n'
    '    _R17_PC = [float(x) for x in _tb["p_cuts"]]\n'
    '    _R17_FHAT = np.zeros(36); _R17_EMPF = [None] * 36; _R17_EMPC = [None] * 36\n'
    '    for _ci, _c in enumerate(_tb["classes"]):\n'
    '        for _t in (0, 1, 2):\n'
    '            for _q in (0, 1, 2):\n'
    '                _k = "%s|%d|%d" % (_c, _t, _q); _ix = _ci * 9 + _t * 3 + _q\n'
    '                _R17_FHAT[_ix] = float(_tb["fhat"][_k]["fhat"]); _R17_EMPF[_ix] = np.asarray(_tb["emp"][_k]["f_sorted"], float); _R17_EMPC[_ix] = np.asarray(_tb["emp"][_k]["cw"], float)\n'
    '    _R17_QV4 = np.where(np.isfinite(qvk), np.expm1(np.clip(np.nan_to_num(qvk, nan=0.0), 0, 30)) * 48, np.nan)   # same qv4h formula as tier_of()/cost tiers; NaN kept => tier 2, p-tercile 2\n'
    '    print(f"R17 fill table loaded: {R17_TABLE} sha {R17_TABLE_SHA[:16]} mode={R17_MODE} seed={R17_SEED} G={R17_G}", flush=True)\n')
# 4. floors aligned to the replay symbol order (after WSYM)
rep('WSYM = [str(s) for s in PW["symbols"]]\n',
    'WSYM = [str(s) for s in PW["symbols"]]\n'
    'if R17_FILL:\n'
    '    _R17_FLOOR = np.array([float(_tb["floors"].get(_s2, _tb["floor_default"])) for _s2 in WSYM])\n'
    '    print(f"R17 floors: {int((_R17_FLOOR == 5).sum())} x 5 / {int((_R17_FLOOR == 20).sum())} x 20 / {int((_R17_FLOOR == 50).sum())} x 50 USDT; missing->default {int(sum(1 for _s2 in WSYM if _s2 not in _tb[\'floors\']))}", flush=True)\n')
# 5. operators (module level, before run())
rep('W3FC = None\ndef run(SLOW, LRa, pos, depth, need, cool, look=900):\n',
    'W3FC = None\n'
    '_R17_COLS = ["tau_intent", "tau_exec", "gross_target", "gross_prev_held", "resid", "n_resid_m", "n_dust", "dust_notional",\n'
    '             "int_ADD", "int_DERISK", "int_FLIP", "int_ZT", "exec_ADD", "exec_DERISK", "exec_FLIP", "exec_ZT", "age1", "age2", "age3_5", "age6_12", "age_gt12", "n_intent_m", "n_exec_m"]\n'
    'def _r17_x1(tgt, H, sm_dep):\n'
    '    """r16 _x16_apply, XMODE=X1, XNULL=0: T = DR = nz & (flip | |tgt|<|H|); new = tgt; sm = where(T, new, sm_dep)."""\n'
    '    gap = tgt - H; nz = gap != 0.0\n'
    '    DR = nz & ((tgt * H < 0.0) | (np.abs(tgt) < np.abs(H)))\n'
    '    return np.where(DR, tgt, sm_dep)\n'
    'def _r17_execute(sm, HX, i, m, age):\n'
    '    """PREREG_r17 §3: intent = sm - HX; class/tier/participation lookup; dust floor; executed = f*intent; returns (executed book, instrument row)."""\n'
    '    intent = sm - HX; a_int = np.abs(intent); act = a_int > 0.0\n'
    '    hx0 = np.abs(HX) > 0.0; s0 = np.abs(sm) > 0.0\n'
    '    zt = act & hx0 & ~s0; flip = act & (sm * HX < 0.0); derisk = act & ~zt & ~flip & hx0 & (np.abs(sm) < np.abs(HX))\n'
    '    cl = np.where(zt, 3, np.where(flip, 2, np.where(derisk, 1, 0)))\n'
    '    qv = _R17_QV4[i]; tier = np.full(NW, 2, np.int8); tier[qv >= 1e6] = 1; tier[qv >= 5e6] = 0\n'
    '    with np.errstate(all="ignore"):\n'
    '        p = a_int * R17_G / qv\n'
    '    pt = np.where(np.isfinite(p), np.where(p <= _R17_PC[0], 0, np.where(p <= _R17_PC[1], 1, 2)), 2)\n'
    '    idx = cl * 9 + tier.astype(int) * 3 + pt\n'
    '    dust = act & (a_int * R17_G < _R17_FLOOR); send = act & ~dust\n'
    '    f = np.zeros(NW)\n'
    '    if R17_MODE == "det":\n'
    '        f[send] = _R17_FHAT[idx[send]]\n'
    '    else:\n'
    '        _si = np.nonzero(send)[0]\n'
    '        for _cell in np.unique(idx[_si]):\n'
    '            _names = _si[idx[_si] == _cell]; _u = _R17_RNG.random(len(_names))\n'
    '            f[_names] = _R17_EMPF[_cell][np.minimum(np.searchsorted(_R17_EMPC[_cell], _u, side="left"), len(_R17_EMPF[_cell]) - 1)]\n'
    '    ex = f * intent; new = HX + ex\n'
    '    rz = np.abs(sm - new); rn = rz > 5e-5; age[:] = np.where(rn, age + 1, 0)\n'
    '    inm = np.zeros(NW, bool); inm[m] = True\n'
    '    row = (float(a_int.sum()), float(np.abs(ex).sum()), float(np.abs(sm).sum()), float(np.abs(HX).sum()), float(rz.sum()), int((inm & (rz > 1e-12)).sum()), int(dust.sum()), float(a_int[dust].sum()),\n'
    '           float(a_int[cl == 0].sum()), float(a_int[cl == 1].sum()), float(a_int[cl == 2].sum()), float(a_int[cl == 3].sum()),\n'
    '           float(np.abs(ex[cl == 0]).sum()), float(np.abs(ex[cl == 1]).sum()), float(np.abs(ex[cl == 2]).sum()), float(np.abs(ex[cl == 3]).sum()),\n'
    '           int((rn & (age == 1)).sum()), int((rn & (age == 2)).sum()), int((rn & (age >= 3) & (age <= 5)).sum()), int((rn & (age >= 6) & (age <= 12)).sum()), int((rn & (age > 12)).sum()),\n'
    '           int((inm & act).sum()), int((inm & (np.abs(ex) > 0)).sum()))\n'
    '    return new, row\n'
    'def run(SLOW, LRa, pos, depth, need, cool, look=900):\n')
# 6. per-run state
rep('    H = np.zeros(NW); HR = np.zeros(NW); Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW)\n',
    '    H = np.zeros(NW); HR = np.zeros(NW); Pi = np.ones(NW); sh = np.zeros(NW); cb = np.zeros(NW)\n'
    '    HX = np.zeros(NW); _R17_AGE = np.zeros(NW, np.int64); _R17 = []   # r17: executed-book state, residual ages, instrument rows\n'
    '    global _R17_RNG\n'
    '    if R17_FILL and R17_MODE == "stoch": _R17_RNG = np.random.default_rng([20260912, R17_SEED])   # reseeded per run() (S0 and d30 arms each start fresh)\n')
# 7. X1 at the king chain band step (verbatim r16 placement)
rep('        sm = H + 0.1 * (tgt - H); trade = sm - H\n'
    '        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H\n',
    '        sm = H + 0.1 * (tgt - H); trade = sm - H\n'
    '        sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H\n'
    '        if R17_X1:\n'
    '            sm = _r17_x1(tgt, H, sm); trade = sm - H\n')
# 8. X1 at the F10 chain band step (verbatim r16 placement)
rep('                _smf = HF + 0.1 * (_tgtf - HF)\n'
    '                _trf = _smf - HF\n'
    '                _smf = np.where(np.abs(_trf) < 2.5e-4, HF, _smf)\n',
    '                _smf = HF + 0.1 * (_tgtf - HF)\n'
    '                _trf = _smf - HF\n'
    '                _smf = np.where(np.abs(_trf) < 2.5e-4, HF, _smf)\n'
    '                if R17_X1:\n'
    '                    _smf = _r17_x1(_tgtf, HF, _smf)\n')
# 9. the execution step: after the blend (and FTPOS kill), before any accounting
rep('        _smk = sm                     # ★ king 书自己的 sm 必须留住: 它的 EMA 态独立推进\n'
    '        sm = smb                      # 此后一切记账(盈亏/成本/carry/深度)都在混合书上\n'
    '        trade = sm - HB\n',
    '        _smk = sm                     # ★ king 书自己的 sm 必须留住: 它的 EMA 态独立推进\n'
    '        sm = smb                      # 此后一切记账(盈亏/成本/carry/深度)都在混合书上\n'
    '        if R17_FILL:   # r17: sm becomes the EXECUTED book (target = smb stays inside the chain states H/HF only)\n'
    '            sm, _r17row = _r17_execute(sm, HX, i, m, _R17_AGE)\n'
    '            if R17_INSTR: _R17.append(_r17row)\n'
    '        trade = sm - HB\n')
# 10. state update
rep('        HB = sm; HR = smr; Pi = Pi * (1.0 + yfull)\n',
    '        HB = sm; HR = smr; Pi = Pi * (1.0 + yfull); HX = sm\n')
# 11. hand the instrument out
rep('    return np.array(rec), np.stack(WS), ((np.array(_SG), np.array(_SP), np.array(_SC), np.array(_SK)) if SLEEVE else None)\n',
    '    global _R17_LAST; _R17_LAST = np.array(_R17, float) if _R17 else None\n'
    '    return np.array(rec), np.stack(WS), ((np.array(_SG), np.array(_SP), np.array(_SC), np.array(_SK)) if SLEEVE else None)\n')
rep('    save[f"{nm}_rec"] = R\n    save[f"{nm}_W"] = WS\n',
    '    save[f"{nm}_rec"] = R\n    save[f"{nm}_W"] = WS\n'
    '    if R17_INSTR and R17_FILL and _R17_LAST is not None:\n'
    '        save[f"{nm}_R17"] = _R17_LAST; save[f"{nm}_R17_cols"] = np.array(_R17_COLS)\n')
open(OUT, "w", encoding="utf-8").write(s)
out_sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
diff = "".join(difflib.unified_diff(src.decode("utf-8").splitlines(True), s.splitlines(True), "w10_sleeve.py (pinned " + PIN_SHA[:16] + ")", "w10_sleeve_r17.py (" + out_sha[:16] + ")"))
open(os.path.splitext(OUT)[0] + ".diff", "w", encoding="utf-8").write(diff)
print("PINNED", PIN_SHA); print("DERIVED", out_sha); print("diff lines", diff.count("\n"))
