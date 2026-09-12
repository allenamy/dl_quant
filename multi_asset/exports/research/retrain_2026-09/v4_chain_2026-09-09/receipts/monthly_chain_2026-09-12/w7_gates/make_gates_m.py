"""make_gates_m.py — PROVENANCE of v4_gate_step1_m.py / v4_gate_step2_m.py (W7, 2026-09-12; PREREG_v4_gates_monthly_2026-09-12 §1).

Builds the month-generic gates FROM the frozen sources by explicit line replacement / insertion, so every line not named here is
byte-identical to the frozen file. Line numbers = `cat -n` of the frozen files (v4_gate_step1.py 278fdce6…, v4_gate_step2.py db7ab356…).
Every emitted line carries the marker `# [M]` (tests_pipeline_gates.py [R] asserts: removed frozen lines == the whitelist below, every
added line carries the marker, threshold literals occur equally often). Also writes the unified diffs beside this script.
usage: python make_gates_m.py <device_dir>   (refuses if the frozen shas differ from the ones this builder was written against)
"""
import difflib, hashlib, os, sys

FROZEN = {"v4_gate_step1.py": "278fdce611e91571d24ec26c78ddc4620668bfd4598a01f577f1f6887dd62be4",
          "v4_gate_step2.py": "db7ab3561f97423a8d5dd74251257adcedd743129d22a07d7cd186d102dd80d8"}

# ── STEP1: replacements {frozen line -> new lines}, insertions {after frozen line -> new lines} ──
S1_REPL = {
    9: ['H = np.load(INPUTS["hole_cells"], allow_pickle=True); NEIGH = H["neigh_rows"]; RUNS = H["fill_runs"]; CSYM = H["symbols"]   # [M] $HOLE_CELLS'],
    27: ['A = np.load(INPUTS["dlw_v4raw_targets"], allow_pickle=True); B = np.load(INPUTS["dlw_hf3_targets"], allow_pickle=True)   # [M] $DLW_RAW / $DLW_CLIP (this month RAW vs CLIP)'],
    32: ['P = np.load(INPUTS["raw_patch"]); prow = P["row"].astype(np.int64); pcol = P["col"].astype(np.int64)   # [M] $RAW_PATCH'],
    53: ['C = np.load(INPUTS["dlw_hf2_targets"], allow_pickle=True); RB = {}   # [M] $PREV_DLW_CLIP = the PREVIOUS month\'s contract-pinned CLIP build (September: hf2)'],
    56: ['    only_b = np.setdiff1d(Eb, Ec); only_c = np.setdiff1d(Ec, Eb); rb = (only_b - int(np.load(INPUTS["cache"])["ts"][0])) // 300   # [M] $CACHE',
         '    _tail = only_b > int(Ec.max()); _out = neigh_of(rb) < 0   # [M] extension tail (PREREG §3.4): only-in-new anchors AFTER the reference axis end are this month\'s new data'],
    57: ['    RB["axis_only_hf3"] = len(only_b); RB["axis_only_hf2"] = len(only_c); RB["axis_only_hf3_outside_neigh"] = int((_out & ~_tail).sum())   # [M] tail not counted',
         '    if int((_out & _tail).sum()): RB["axis_only_hf3_tail_exempt"] = int((_out & _tail).sum()); RB["ref_axis_end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(Ec.max())))   # [M] conditional: present iff the tail rule was load-bearing'],
    78: ['    _oa = neigh_of(Erow_a[only_a // NW]) < 0; _ta = Erow_a[only_a // NW] > int(Erow_b.max())   # [M] extension tail (PREREG §3.4): pairs at anchors after the reference\'s last E_row',
         '    res["pairs_only_a_outside_neigh"] = int((_oa & ~_ta).sum()); res["pairs_only_b_outside_neigh"] = int((neigh_of(Erow_b[only_b // NW]) < 0).sum())   # [M] tail not counted',
         '    if int((_oa & _ta).sum()): res["pairs_only_a_tail_exempt"] = int((_oa & _ta).sum())   # [M] conditional: present iff the tail rule was load-bearing'],
    91: ['R["B_fea82_hf3_vs_hf2"] = fea_gate(INPUTS["fea82_hf3"], INPUTS["fea82_hf2"], ErB, ErC, "B fea82:")   # [M] $DLW_CLIP vs $PREV_DLW_CLIP'],
    92: ['R["B_fea89_f8v4_vs_f8hf2"] = fea_gate(INPUTS["fea89_f8v4"], INPUTS["fea89_f8hf2"], ErB, ErC, "B fea89:")   # [M] $F8 vs $PREV_F8'],
    99: ['R["fea82_copy_identical"] = sha(INPUTS["fea82_v4raw"]) == sha(INPUTS["fea82_hf3"])   # [M] $DLW_RAW vs $DLW_CLIP fea82'],
    104: ['finalize("STEP1", R, _OUT, INPUTS)   # [M] names = the REQUIRED_INPUTS registry roles (dlw_hf3_targets = this month\'s CLIP, dlw_hf2_targets = the previous month\'s); `cache` is an extra'],
    105: [], 106: [], 107: [], 108: [],
}
S1_INS = {
    6: ['# [M] MONTH-GENERIC (W7 2026-09-12, docs/PREREG_v4_gates_monthly_2026-09-12.md): every path comes from the month contract env (chain_lib.load_month_env exports it);',
        '# [M] the reference is the PREVIOUS month\'s contract-pinned build (PREV_DLW_CLIP / PREV_F8, September = hf2 / f8_hf2); thresholds and statistics are the frozen ones verbatim;',
        '# [M] anchors/pairs after the reference axis end are the extension tail (§3.4); a reference identical to the candidate is refused (§3.5); missing inputs are refused with a PASS=false receipt (§3.6).'],
    8: ['import os   # [M]',
        'sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from v4_gate_common import finalize, sha256_file   # [M] refusal receipts go through finalize BEFORE any load',
        '_OUT = os.environ.get("STEP1_OUT")   # [M] required, no September default',
        'if not _OUT: print("STEP1_REFUSED missing STEP1_OUT (no receipt path: nothing written)", flush=True); sys.exit(3)   # [M]',
        '_KEYS = ("HOLE_CELLS", "DLW_RAW", "DLW_CLIP", "RAW_PATCH", "PREV_DLW_CLIP", "CACHE", "F8", "PREV_F8")   # [M] month contract keys this gate reads (PREREG §2)',
        '_E = {k: os.environ.get(k, "") for k in _KEYS}; _missing_env = [k for k in _KEYS if not _E[k]]   # [M]',
        'def _p(k, rel=""): return (_E[k] + rel) if _E[k] else None   # [M]',
        'INPUTS = {"dlw_v4raw_targets": _p("DLW_RAW", "/data/dlw_targets.npz"), "dlw_hf3_targets": _p("DLW_CLIP", "/data/dlw_targets.npz"), "dlw_hf2_targets": _p("PREV_DLW_CLIP", "/data/dlw_targets.npz"),   # [M]',
        '          "fea82_hf3": _p("DLW_CLIP", "/data/dlw_fea82.npz"), "fea82_hf2": _p("PREV_DLW_CLIP", "/data/dlw_fea82.npz"), "fea82_v4raw": _p("DLW_RAW", "/data/dlw_fea82.npz"),   # [M]',
        '          "fea89_f8v4": _p("F8", "/data/f8_fea89.npz"), "fea89_f8hf2": _p("PREV_F8", "/data/f8_fea89.npz"), "raw_patch": _p("RAW_PATCH"), "hole_cells": _p("HOLE_CELLS"), "cache": _p("CACHE")}   # [M]',
        '_missing_files = {k: v for k, v in INPUTS.items() if v is None or not os.path.isfile(v)}; _refused = {}   # [M]',
        'if _missing_env: _refused["missing_env"] = _missing_env   # [M]',
        'if _missing_files: _refused["missing_files"] = _missing_files   # [M]',
        'if not _refused:   # [M] reference must not be the candidate (PREREG §3.5): a file compared with itself verifies nothing',
        '    _sh = {}; _S = lambda k: _sh.setdefault(k, sha256_file(INPUTS[k]))   # [M]',
        '    _same = [f"{a}=={b}" for a, b in (("dlw_hf3_targets", "dlw_hf2_targets"), ("fea82_hf3", "fea82_hf2"), ("fea89_f8v4", "fea89_f8hf2")) if _S(a) == _S(b)]   # [M]',
        '    if _same: _refused["reference_is_candidate"] = _same   # [M]',
        'if _refused: print("STEP1_REFUSED", json.dumps(_refused), flush=True); finalize("STEP1", {"PASS": False, "REFUSED": _refused}, _OUT, INPUTS)   # [M] rc 3; receipt PASS=false; missing shas None'],
}

# ── STEP2 ──
S2_REPL = {
    8: ['H = np.load(INPUTS["hole_cells"], allow_pickle=True); NEIGH = H["neigh_rows"]; RUNS = H["fill_runs"]   # [M] $HOLE_CELLS'],
    14: ['CTS = np.load(INPUTS["cache"])["ts"].astype(np.int64)   # [M] $CACHE'],
    15: ['M4 = np.load(INPUTS["wide_fea_v4_meta"], allow_pickle=True); ME = np.load(INPUTS["wide_fea_v2ext_meta"], allow_pickle=True)   # [M] $KING_META vs $PREV_META (the previous month\'s meta; September: v2ext)'],
    22: ['_o4 = (neigh_of(rows_of(x4)) < 0) if len(x4) else np.zeros(0, bool); _t4 = x4 > int(EE.max())   # [M] extension tail (PREREG §3.4): only-in-new anchors AFTER the reference axis end',
         'R["anchors_only_v4_outside_neigh"] = int((_o4 & ~_t4).sum()); R["anchors_only_v2ext_outside_neigh"] = int((neigh_of(rows_of(xE)) < 0).sum()) if len(xE) else 0   # [M] tail not counted',
         'if int((_o4 & _t4).sum()): R["anchors_only_v4_tail_exempt"] = int((_o4 & _t4).sum()); R["ref_axis_end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(EE.max())))   # [M] conditional: present iff the tail rule was load-bearing'],
    27: ['F4 = np.load(INPUTS["wide_fea_v4"], mmap_mode="r"); FC = np.load(INPUTS["wide_fea_v2ext_clamp"], mmap_mode="r"); FE = None if NO_UNCLAMPED else np.load(INPUTS["wide_fea_v2ext"], mmap_mode="r")   # [M] $KING_FEA / $PREV_KING_FEA / $PREV_KING_FEA_UNCLAMPED (NONE allowed, §3.3)'],
    28: ['assert F4.shape[1:] == FC.shape[1:] and F4.shape[0] == len(E4) and FC.shape[0] == len(EE) and (NO_UNCLAMPED or (FE.shape[1:] == FC.shape[1:] and FE.shape[0] == len(EE))), (F4.shape, FC.shape, None if NO_UNCLAMPED else FE.shape)   # [M]'],
    36: ['    idx = np.arange(s, min(s + CH, nA)); a = np.asarray(F4[I4[idx]]); c = np.asarray(FC[IE[idx]]); e = None if NO_UNCLAMPED else np.asarray(FE[IE[idx]])   # [M]'],
    48: ['    if not NO_UNCLAMPED:   # [M] clamp checks only when an unclamped reference exists (PREREG §3.3)',
         '        d2 = cmp(a, e).any((1, 2))   # [M] (frozen L48, indented)'],
    49: ['        S["v4_vs_ext"]["anchors"] += int(d2.sum()); S["v4_vs_ext"]["outside_138_and_neigh"] += int((d2 & ~f138[idx] & (nn[idx] < 0)).sum()); S["v4_vs_ext"]["in_first138"] += int((d2 & f138[idx]).sum())   # [M] (frozen L49, indented)'],
    50: ['        d3 = cmp(c, e).any((1, 2)); S["clamp_vs_ext"]["anchors"] += int(d3.sum()); S["clamp_vs_ext"]["outside_138"] += int((d3 & ~f138[idx]).sum())   # [M] (frozen L50, indented)'],
    58: ['R["PASS"] = bool(S["v4_vs_clamp"]["outside"] == 0 and S["v4_vs_clamp"]["val_sym_bad"] == 0 and (NO_UNCLAMPED or (S["v4_vs_ext"]["outside_138_and_neigh"] == 0 and S["clamp_vs_ext"]["outside_138"] == 0)) and ("tail_quality" not in R or R["tail_quality"]["ok"])   # [M] clamp checks not evaluated under NONE (§3.3); tail quality (AMENDMENT 1); the rest verbatim'],
    64: ['finalize("STEP2", R, _OUT, INPUTS)   # [M] names = the REQUIRED_INPUTS registry roles (wide_fea_v2ext* = the previous month\'s build); `cache` is an extra; wide_fea_v2ext is None under NONE'],
    65: [], 66: [],
}
S2_INS = {
    4: ['# [M] MONTH-GENERIC (W7 2026-09-12, docs/PREREG_v4_gates_monthly_2026-09-12.md): every path comes from the month contract env (chain_lib.load_month_env exports it);',
        '# [M] the reference is the PREVIOUS month\'s contract-pinned king build (PREV_KING_FEA / PREV_META; September = v2ext_clamp / v2ext_meta); PREV_KING_FEA_UNCLAMPED is the unclamped',
        '# [M] build on the reference axis (September: v2ext) or the literal NONE (clamp checks v4_vs_ext / clamp_vs_ext NOT evaluated, recorded in the receipt, §3.3); thresholds/statistics verbatim;',
        '# [M] anchors after the reference axis end are the extension tail (§3.4); a reference identical to the candidate is refused (§3.5); missing inputs are refused with a PASS=false receipt (§3.6).',
        '# [M] AMENDMENT 1 (researcher B-R4): NONE is bound to the builder identity (PREV_CLAMP_BUILDER_SHA256 == preflight-pinned == on-disk pod_fea_ext_clamp.py, else refused); every new-tail anchor',
        '# [M] must have >= 1 member and a member-cell finite fraction >= 0.90 (tail_quality, always present when a tail exists, part of PASS).'],
    7: ['sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from v4_gate_common import finalize, sha256_file   # [M] refusal receipts go through finalize BEFORE any load',
        '_OUT = os.environ.get("STEP2_OUT")   # [M] required, no September default',
        'if not _OUT: print("STEP2_REFUSED missing STEP2_OUT (no receipt path: nothing written)", flush=True); sys.exit(3)   # [M]',
        '_KEYS = ("HOLE_CELLS", "CACHE", "KING_FEA", "KING_META", "PREV_KING_FEA", "PREV_KING_FEA_UNCLAMPED", "PREV_META")   # [M] month contract keys this gate reads (PREREG §2)',
        '_E = {k: os.environ.get(k, "") for k in _KEYS}; _missing_env = [k for k in _KEYS if not _E[k]]   # [M]',
        'NO_UNCLAMPED = _E["PREV_KING_FEA_UNCLAMPED"] == "NONE"   # [M] PREREG §3.3: the contract (user word) says no unclamped build exists on the reference axis',
        'INPUTS = {"wide_fea_v4": _E["KING_FEA"] or None, "wide_fea_v4_meta": _E["KING_META"] or None, "wide_fea_v2ext_clamp": _E["PREV_KING_FEA"] or None,   # [M]',
        '          "wide_fea_v2ext": None if NO_UNCLAMPED else (_E["PREV_KING_FEA_UNCLAMPED"] or None), "wide_fea_v2ext_meta": _E["PREV_META"] or None, "hole_cells": _E["HOLE_CELLS"] or None, "cache": _E["CACHE"] or None}   # [M]',
        '_missing_files = {k: v for k, v in INPUTS.items() if (v is None or not os.path.isfile(v)) and not (k == "wide_fea_v2ext" and NO_UNCLAMPED)}; _refused = {}   # [M]',
        'if _missing_env: _refused["missing_env"] = _missing_env   # [M]',
        'if _missing_files: _refused["missing_files"] = _missing_files   # [M]',
        'if not _refused:   # [M] reference must not be the candidate (PREREG §3.5): a file compared with itself verifies nothing',
        '    _sh = {}; _S = lambda k: _sh.setdefault(k, sha256_file(INPUTS[k]))   # [M]',
        '    _pairs = [("wide_fea_v4", "wide_fea_v2ext_clamp"), ("wide_fea_v4_meta", "wide_fea_v2ext_meta")] + ([] if NO_UNCLAMPED else [("wide_fea_v4", "wide_fea_v2ext"), ("wide_fea_v2ext_clamp", "wide_fea_v2ext")])   # [M]',
        '    _same = [f"{a}=={b}" for a, b in _pairs if _S(a) == _S(b)]   # [M]',
        '    if _same: _refused["reference_is_candidate"] = _same   # [M]',
        '_CLAMP_CHECKS = None   # [M] AMENDMENT 1 (B-R4): under NONE the builder identity is verified here, not assumed',
        'if NO_UNCLAMPED:   # [M]',
        '    _pin = os.environ.get("PREV_CLAMP_BUILDER_SHA256", ""); _root = os.environ.get("R", ""); _deps = os.path.join(_root, "v4_gates", "deps_preflight_device.json") if _root else ""   # [M]',
        '    _dev = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pod_fea_ext_clamp.py"); _why = []; _pf = None; _dv = None   # [M]',
        '    if not _pin: _why.append("PREV_CLAMP_BUILDER_SHA256 unset (the contract must pin the September-verified builder sha)")   # [M]',
        '    if not _root: _why.append("R unset (month root: the preflight deps receipt cannot be located)")   # [M]',
        '    elif not os.path.isfile(_deps): _why.append(f"preflight deps receipt missing: {_deps}")   # [M]',
        '    else:   # [M]',
        '        _dd = json.load(open(_deps)).get("deps_sha256", {}); _hits = [v for k, v in _dd.items() if k.endswith("/pod_fea_ext_clamp.py")]   # [M]',
        '        _pf = _hits[0] if len(_hits) == 1 else None   # [M]',
        '        if _pf is None: _why.append(f"preflight deps receipt pins pod_fea_ext_clamp.py {len(_hits)} times (need exactly 1): {_deps}")   # [M]',
        '    if not os.path.isfile(_dev): _why.append(f"builder missing beside the gate: {_dev}")   # [M]',
        '    else: _dv = sha256_file(_dev)   # [M]',
        '    if _pin and _pf and _pf != _pin: _why.append(f"preflight-pinned builder {_pf[:12]} != contract pin {_pin[:12]}")   # [M]',
        '    if _pin and _dv and _dv != _pin: _why.append(f"on-disk builder {_dv[:12]} != contract pin {_pin[:12]}")   # [M]',
        '    if _why: _refused["clamp_builder_identity"] = {"why": _why, "pinned_sha256": _pin or None, "preflight_pinned_sha256": _pf, "device_file_sha256": _dv}   # [M]',
        '    else: _CLAMP_CHECKS = {"mode": "NOT_EVALUATED: PREV_KING_FEA_UNCLAMPED=NONE (v4_vs_ext / clamp_vs_ext not computed)", "builder": "pod_fea_ext_clamp.py", "pinned_sha256": _pin, "preflight_pinned_sha256": _pf, "device_file_sha256": _dv, "preflight_deps_receipt": _deps}   # [M] identity verified (AMENDMENT 1)',
        'if _refused: print("STEP2_REFUSED", json.dumps(_refused), flush=True); finalize("STEP2", {"PASS": False, "REFUSED": _refused}, _OUT, INPUTS)   # [M] rc 3; receipt PASS=false; missing shas None'],
    33: ['if NO_UNCLAMPED: del S["v4_vs_ext"], S["clamp_vs_ext"]; R["clamp_checks"] = _CLAMP_CHECKS   # [M] conditional: present iff NONE; the builder identity was verified above (AMENDMENT 1)'],
    52: ['_tail_idx = np.searchsorted(E4, x4[_t4]) if len(x4) else np.zeros(0, np.int64)   # [M] AMENDMENT 1 (B-R4): new-tail anchors = only-in-new AND after the reference axis end (§3.4)',
         'if len(_tail_idx):   # [M] tail quality gate: every tail anchor needs >= 1 member and a member-cell finite fraction >= 0.90 (floor pre-registered from the September calibration: min 0.9756, median 1.0)',
         '    _ffs = []; _nms = []   # [M]',
         '    for _i in _tail_idx: _m = np.asarray(M4m[_i], dtype=np.int64); _nms.append(int(len(_m))); _ffs.append(float(np.isfinite(np.asarray(F4[_i])[_m]).mean()) if len(_m) else 0.0)   # [M]',
         '    _ffs = np.array(_ffs); R["tail_quality"] = {"n_tail_anchors": int(len(_tail_idx)), "member_finite_frac_min": float(_ffs.min()), "member_finite_frac_median": float(np.median(_ffs)), "n_members_min": int(min(_nms)), "floor": 0.90, "ok": bool((_ffs >= 0.90).all() and min(_nms) >= 1)}   # [M]'],
}

WHITELIST = {"v4_gate_step1.py": sorted(S1_REPL), "v4_gate_step2.py": sorted(S2_REPL)}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def build(src_lines, repl, ins):
    out = []
    for i, line in enumerate(src_lines, 1):
        if i in repl:
            out.extend(l + "\n" for l in repl[i])
        else:
            out.append(line)
        if i in ins:
            out.extend(l + "\n" for l in ins[i])
    return out


def main(dev):
    here = os.path.dirname(os.path.abspath(__file__))
    for name, repl, ins in (("v4_gate_step1.py", S1_REPL, S1_INS), ("v4_gate_step2.py", S2_REPL, S2_INS)):
        src = os.path.join(dev, name)
        got = sha(src)
        if got != FROZEN[name]:
            print(f"REFUSED frozen {name} sha {got[:12]} != {FROZEN[name][:12]}"); return 3
        lines = open(src).read().splitlines(keepends=True)
        new = build(lines, repl, ins)
        dst = os.path.join(dev, name.replace(".py", "_m.py"))
        open(dst, "w").write("".join(new))
        diff = list(difflib.unified_diff(lines, new, fromfile=name, tofile=os.path.basename(dst), n=0))
        open(os.path.join(here, os.path.basename(dst).replace(".py", ".diff")), "w").write("".join(diff))
        print(f"{os.path.basename(dst)} sha {sha(dst)} removed_lines={WHITELIST[name]} added={sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
