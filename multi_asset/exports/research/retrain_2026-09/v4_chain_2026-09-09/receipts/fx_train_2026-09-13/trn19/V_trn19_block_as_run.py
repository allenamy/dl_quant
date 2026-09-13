# ── [V] FX-TRAIN (2026-09-13; docs/fixprogram_2026-09-13/FX_TRAIN/, AUDIT_TRAIN 7e1ecf9a): every cell runs the ARCHIVED pre-fix source (RED) and the current one
#        (GREEN) on the same input in the same run; the pre-fix sources are kept beside the current ones as `<name>.r<N>_<sha8>` ──
print("\n[V] FX-TRAIN TRN-19 (AUDIT_TRAIN §4, reviewer P3): a parser output line without '=' — archived pre-fix chain_lib.r3_4ee217e1.sh (RED) vs current chain_lib.sh (GREEN)")
_V3_LIB = f"{HERE}/chain_lib.r3_4ee217e1.sh"; _VNEW_LIB = f"{HERE}/chain_lib.sh"; _VSEP = f"{HERE}/v4_month_2026-09.env"; _VOCT = f"{HERE}/v4_month_2026-10.env.template"
check("★★★ [V] TRN-19 the pre-fix chain_lib is archived beside the current one and IS the source the reviewer froze (4ee217e1…, codex round-4 retrain RESULT.md L51-53); the RED control outlives the verdict",
      _sha(_V3_LIB) == "4ee217e1d761fa13abf34d16222f1dede79ceade3d44547e171aa7477a30288d", _sha(_V3_LIB)[:8])
with tempfile.TemporaryDirectory() as _vd:
    def _vload(lib, envf, key, py, tag):   # the REAL driver's shell (chain_v4_monthly.sh L29/L34): pipefail on, errexit/nounset off, `load_month_env "$ENVF" || exit 4`; the env after loading is dumped for comparison
        _dump = f"{_vd}/env_{tag}.txt"
        _p = subprocess.run(["/bin/bash", "-c", 'set -o pipefail; . "$1"; load_month_env "$2" || exit 4; printf "VALUE=<%s>\\n" "${!3}"; env | LC_ALL=C sort > "$4"', "v", lib, envf, key, _dump],
                            capture_output=True, text=True, env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PY": py, "PYTHONDONTWRITEBYTECODE": "1", "L": "/dev/null"}, cwd=_vd, timeout=60)
        _env = [l for l in open(_dump).read().splitlines() if not l.startswith(("_=", "SHLVL=", "PWD=", "OLDPWD="))] if os.path.exists(_dump) else None
        return _p.returncode, _p.stdout + _p.stderr, _env
    # the TRUE parser output for the September contract: the 46 KEY=VALUE pairs the current loader exports with this interpreter (= what chain_lib L130-131 prints)
    _p = subprocess.run(["/bin/bash", "-c", '. "$1"; load_month_env "$2" >/dev/null || exit 4; for k in $V4_MONTH_KEYS; do printf "%s=%s\\n" "$k" "${!k}"; done', "v", _VNEW_LIB, _VSEP],
                        capture_output=True, text=True, env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PY": PY, "L": "/dev/null"}, cwd=_vd, timeout=60)
    _VTRUE = _p.stdout.splitlines()
    check("★ [V] TRN-19 setup: the September contract's true parser output is 46 KEY=VALUE lines (R first-class, SEEDS=42,2027)", _p.returncode == 0 and len(_VTRUE) == 46 and "R=/workspace/review_scratch" in _VTRUE and "SEEDS=42,2027" in _VTRUE, (_p.returncode, len(_VTRUE), _p.stderr[-200:]))
    def _vstub(tag, lines):   # an interpreter that swallows the parser heredoc, prints exactly `lines` and exits 0 (the reviewer's transparent stub)
        _s = f"{_vd}/stub_{tag}"; open(_s, "w").write("#!/bin/sh\ncat >/dev/null\ncat <<'EOT'\n" + "\n".join(lines) + "\nEOT\nexit 0\n"); os.chmod(_s, 0o755); return _s
    def _vrepl(key, new):
        return [new if l.split("=", 1)[0] == key else l for l in _VTRUE]
    # V1 — the reviewer's exact probe: the R line replaced by a bare `R`
    _s = _vstub("bare_R", _vrepl("R", "R")); _o = _vload(_V3_LIB, _VSEP, "R", _s, "o_bare_R"); _n = _vload(_VNEW_LIB, _VSEP, "R", _s, "n_bare_R")
    check("★★★ [V] TRN-19 (reviewer parser_bare_registered_key_OUTPUT_ACCEPTED): a parser that exits 0 printing 45 valid lines and a BARE `R` ⇒ pre-fix loader rc 0, MONTH_ENV_OK, R exported as the relative path `R`; fixed loader rc 4 FAIL_month_env_parser_output naming the missing '=', no MONTH_ENV_OK",
          _o[0] == 0 and "MONTH_ENV_OK" in _o[1] and "VALUE=<R>" in _o[1] and _n[0] == 4 and "FAIL_month_env_parser_output_v4_month_2026-09.env" in _n[1] and "has no '='" in _n[1] and "MONTH_ENV_OK" not in _n[1],
          (_o[0], _o[1][-120:], _n[0], _n[1][-200:]))
    # V2 — neighbour: another registered key (SEEDS) bare
    _s = _vstub("bare_SEEDS", _vrepl("SEEDS", "SEEDS")); _o = _vload(_V3_LIB, _VSEP, "SEEDS", _s, "o_bare_SEEDS"); _n = _vload(_VNEW_LIB, _VSEP, "SEEDS", _s, "n_bare_SEEDS")
    check("★★ [V] TRN-19 neighbour: a BARE `SEEDS` (another registered key, value becomes the word SEEDS) ⇒ pre-fix rc 0 SEEDS=SEEDS; fixed rc 4 parser_output, no MONTH_ENV_OK",
          _o[0] == 0 and "VALUE=<SEEDS>" in _o[1] and _n[0] == 4 and "FAIL_month_env_parser_output" in _n[1] and "MONTH_ENV_OK" not in _n[1], (_o[0], _n[0], _n[1][-160:]))
    # V3 — neighbour: all 46 valid lines plus a bare UNREGISTERED word (already refused before the fix; the refusal class is unchanged)
    _s = _vstub("bare_extra", _VTRUE + ["BOGUS"]); _o = _vload(_V3_LIB, _VSEP, "R", _s, "o_bare_extra"); _n = _vload(_VNEW_LIB, _VSEP, "R", _s, "n_bare_extra")
    check("★★ [V] TRN-19 neighbour: 46 valid lines + a bare UNREGISTERED word ⇒ refused rc 4 parser_output by BOTH sources (pre-fix: unregistered key; fixed: no '=') — the fix narrows nothing that was already closed",
          _o[0] == 4 and "FAIL_month_env_parser_output" in _o[1] and "unregistered key BOGUS" in _o[1] and _n[0] == 4 and "FAIL_month_env_parser_output" in _n[1] and "has no '='" in _n[1], (_o[0], _o[1][-120:], _n[0], _n[1][-120:]))
    # V4 — neighbour: an empty key `=R` appended (has '=', key empty)
    _s = _vstub("empty_key", _VTRUE + ["=R"]); _o = _vload(_V3_LIB, _VSEP, "R", _s, "o_empty_key"); _n = _vload(_VNEW_LIB, _VSEP, "R", _s, "n_empty_key")
    check("★ [V] TRN-19 neighbour: 46 valid lines + `=R` (an '=' but an empty key) ⇒ both sources rc 4 'not KEY=VALUE' (the character-class check still owns this case)",
          _o[0] == 4 and _n[0] == 4 and "parser output line is not KEY=VALUE" in _o[1] and "parser output line is not KEY=VALUE" in _n[1], (_o[0], _n[0], _n[1][-120:]))
    # V5 — positive: a stub that prints exactly the true 46 lines ⇒ both rc 0 and the SAME environment
    _s = _vstub("true46", _VTRUE); _o = _vload(_V3_LIB, _VSEP, "R", _s, "o_true46"); _n = _vload(_VNEW_LIB, _VSEP, "R", _s, "n_true46")
    check("★★★ [V] TRN-19 POSITIVE (both sources): a stub printing exactly the true 46 KEY=VALUE lines ⇒ rc 0, MONTH_ENV_OK, identical exported environment — well-formed output is not refused",
          _o[0] == 0 and _n[0] == 0 and _o[2] is not None and _o[2] == _n[2] and "VALUE=</workspace/review_scratch>" in _n[1], (_o[0], _n[0], sorted(set(_o[2] or []) ^ set(_n[2] or []))[:4]))
    # V6 — positive with the REAL parser on both delivered contracts
    _res6 = {}
    for _cf in (_VSEP, _VOCT):
        _res6[os.path.basename(_cf)] = (_vload(_V3_LIB, _cf, "R", PY, f"o_real_{os.path.basename(_cf)}"), _vload(_VNEW_LIB, _cf, "R", PY, f"n_real_{os.path.basename(_cf)}"))
    check("★★★ [V] TRN-19 POSITIVE real parser: the September contract and the October template load rc 0 under both sources with the IDENTICAL environment (the fix is invisible to the real parser)",
          all(o[0] == 0 and n[0] == 0 and o[2] == n[2] and "MONTH_ENV_OK" in n[1] for o, n in _res6.values()), {k: (o[0], n[0], sorted(set(o[2] or []) ^ set(n[2] or []))[:2]) for k, (o, n) in _res6.items()})
    # V7 — the inheritor: the dryrun derives its env through load_month_env, so the liar interpreter is refused there too (rc 2, no derived env, no driver run)
    _s = _vstub("bare_R_dry", _vrepl("R", "R")); os.makedirs(f"{_vd}/dry", exist_ok=True)
    _p = subprocess.run(["bash", f"{HERE}/chain_v4_monthly_dryrun.sh", _VSEP, f"{_vd}/dry"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PY": _s}, cwd=_vd, timeout=120)
    _dr = [x for x in os.listdir(f"{_vd}/dry")]; _drv = [p for p in _dr if os.path.exists(f"{_vd}/dry/{p}/driver.out")]
    _ld = open(f"{_vd}/dry/{_dr[0]}/source_env_load.txt").read() if _dr and os.path.exists(f"{_vd}/dry/{_dr[0]}/source_env_load.txt") else ""
    check("★★ [V] TRN-19 inheritor: chain_v4_monthly_dryrun.sh with the bare-R interpreter ⇒ rc 2 'dryrun env derivation failed', no MONTH_ENV_OK in its load record, no driver run",
          _p.returncode == 2 and "dryrun env derivation failed" in _p.stderr and "MONTH_ENV_OK" not in _ld and not _drv, (_p.returncode, _p.stderr[-160:], _dr, _drv))
    # V8 — static: the '=' guard precedes the split in the code lines of load_month_env
    _LFN8 = [l for l in open(_VNEW_LIB).read().split("load_month_env(){", 1)[1].split("\ngate_sha(){", 1)[0].splitlines() if not l.lstrip().startswith("#")]
    _ig = [i for i, l in enumerate(_LFN8) if "case $line in *=*) ;;" in l]; _is = [i for i, l in enumerate(_LFN8) if "k=${line%%=*}; v=${line#*=}" in l]
    check("★ [V] TRN-19 static: in load_month_env the `case $line in *=*)` guard is a code line immediately before the only `k=${line%%=*}; v=${line#*=}` split",
          len(_ig) == 1 and len(_is) == 1 and _ig[0] + 1 == _is[0], (_ig, _is))
    # ── sibling in the same family: the dryrun NEGATIVE CONTROL trusted its interpreter's rc 0 twice (the derived env; the receipt program) ──────────────────
    _V3_DRY = f"{HERE}/chain_v4_monthly_dryrun.r3_407aa438.sh"; _VNEW_DRY = f"{HERE}/chain_v4_monthly_dryrun.sh"
    check("★★ [V] TRN-19 sibling: the pre-fix dryrun is archived beside the current one (chain_v4_monthly_dryrun.r3_407aa438.sh = the committed 407aa438…)",
          _sha(_V3_DRY) == "407aa438f31171921746be2378314472db4e36b7664f4bca90712919038d710b", _sha(_V3_DRY)[:8])
    _VLAB = ("V4_MONTH", "MONTHS_ALL", "SEEDS", "MWF_ROOT", "BUNDLE_GENERATION", "EXPORT_ARM", "GATE_STEP1", "GATE_STEP2")
    _VFR = f"{_vd}/foreign_root"   # NEVER created: every path a stub emits points below it, so no run of any source can write anywhere real, on any machine (E-0912-B rule)
    def _vforeign(py):
        out = []
        for l in _VTRUE:
            k, v = l.split("=", 1)
            out.append(l if k in _VLAB else (f"PY={py}" if k == "PY" else (f"R={_VFR}" if k == "R" else f"{k}={_VFR}/{os.path.basename(v.rstrip('/')) or k.lower()}")))
        return out
    def _vdispatch(tag, derive_under_root):   # an interpreter that swallows stdin; >=5 args (the receipt program) ⇒ prints nothing, exit 0; 4 args (the derivation) ⇒ foreign lines, or lines under ITS $2/root when derive_under_root; else (the loader) ⇒ foreign lines
        _s = f"{_vd}/disp_{tag}"; fl = "\n".join(_vforeign(_s))
        body = "#!/bin/sh\ncat >/dev/null\nif [ \"$#\" -ge 5 ]; then exit 0; fi\n"
        if derive_under_root:
            lab = "".join(f"    {k}) echo \"{l}\" ;;\n" for l in _VTRUE for k in [l.split('=', 1)[0]] if k in _VLAB)
            body += ("if [ \"$#\" -eq 4 ]; then\n  echo '# stub derivation'\n  for k in $3; do case $k in\n" + lab +
                     "    PY) echo \"PY=$4\" ;;\n    R) echo \"R=$2/root\" ;;\n    *) echo \"$k=$2/root/stub_$k\" ;;\n  esac; done\n  exit 0\nfi\n")
        body += "cat <<'EOT'\n" + fl + "\nEOT\nexit 0\n"
        open(_s, "w").write(body); os.chmod(_s, 0o755); return _s
    def _vdry(script, py, tag):
        _par = f"{_vd}/dry_{tag}"; os.makedirs(_par, exist_ok=True)
        _p = subprocess.run(["bash", script, _VSEP, _par], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PY": py}, cwd=_vd, timeout=180)
        _sub = [f"{_par}/{x}" for x in os.listdir(_par)]; _root = _sub[0] if _sub else None
        _denv = open(f"{_root}/v4_month_dryrun.env").read() if _root and os.path.exists(f"{_root}/v4_month_dryrun.env") else ""
        return _p.returncode, _p.stdout + _p.stderr, _root, _denv, bool(_root and os.path.exists(f"{_root}/driver.out")), bool(_root and os.path.exists(f"{_root}/dryrun_receipt.json"))
    _s9 = _vdispatch("v9", False); _o = _vdry(_V3_DRY, _s9, "o9"); _n = _vdry(_VNEW_DRY, _s9, "n9")
    check("★★★ [V] TRN-19 sibling V9: an interpreter that exits 0 printing a contract whose paths lie OUTSIDE the scratch root (here: a never-created foreign root) as the 'derived env' ⇒ pre-fix dryrun ran the DRIVER against R=<foreign root> and exited rc 0; fixed dryrun refuses rc 2 'derived env REFUSED' naming R, driver not run",
          _o[4] and f"R={_VFR}" in _o[3] and _o[0] == 0 and _n[0] == 2 and "dryrun derived env REFUSED" in _n[1] and f"R={_VFR} is not" in _n[1] and not _n[4] and not os.path.exists(_VFR),
          (_o[0], _o[4], _n[0], _n[4], _n[1][-240:]))
    _s10 = _vdispatch("v10", True); _o = _vdry(_V3_DRY, _s10, "o10"); _n = _vdry(_VNEW_DRY, _s10, "n10")
    check("★★★ [V] TRN-19 sibling V10: an interpreter whose derivation stays under the scratch root but whose receipt program exits 0 WITHOUT writing a receipt ⇒ pre-fix dryrun rc 0 with no dryrun_receipt.json (a 'passed' negative control with no evidence); fixed dryrun rc 1 'receipt … missing or not PASS'",
          _o[0] == 0 and not _o[5] and _o[4] and _n[0] == 1 and not _n[5] and "DRYRUN_FAIL receipt program exited 0" in _n[1] and not os.path.exists(_VFR),
          (_o[0], _o[5], _n[0], _n[5], _n[1][-200:]))
    _o = _vdry(_V3_DRY, PY, "o11"); _n = _vdry(_VNEW_DRY, PY, "n11")
    check("★★★ [V] TRN-19 sibling POSITIVE: with the REAL interpreter both dryruns PASS rc 0 (DRYRUN_PASS, receipt PASS true) — the bash re-check accepts every line the real derivation writes",
          _o[0] == 0 and _n[0] == 0 and "DRYRUN_PASS" in _n[1] and _n[5] and '"PASS": true' in open(f"{_n[2]}/dryrun_receipt.json").read(), (_o[0], _n[0], _n[1][-200:]))
