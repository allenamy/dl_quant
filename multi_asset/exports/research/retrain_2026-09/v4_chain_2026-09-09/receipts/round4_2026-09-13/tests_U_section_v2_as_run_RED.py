# ── [U] ROUND 4 (2026-09-13, X3; independent review REVIEW_round3_code_and_research_2026-09-13 §4 + codex_round3_code_review_2026-09-13/retrain/RESULT.md R3-D1 / R3-D3 / R3-D2):
#        every cell runs the ARCHIVED pre-round-4 source (chain_lib.r2_a331f035.sh / v4_gate_step2_m.r2_b2f9cfd4.py = RED) and the current one (GREEN) on the
#        researcher's exact counterexample, in the same run — red and green are observed together, not asserted in prose ──
print("\n[U] round 4 (REVIEW_round3 §4): R3-D1 null sidecar locators, R3-D3 month-contract DATA grammar, R3-D2 member-index dtype — each cell runs the ARCHIVED pre-round-4 source (RED) and the current one (GREEN) on the researcher's counterexample")
import ast as _uast
_R2_LIB = f"{HERE}/chain_lib.r2_a331f035.sh"; _R2_S2 = "v4_gate_step2_m.r2_b2f9cfd4.py"; _NEW_LIB = f"{HERE}/chain_lib.sh"
check("★★★ [U] the pre-round-4 sources are archived beside the current ones and ARE the bytes the reviewer probed (chain_lib a331f035…, v4_gate_step2_m b2f9cfd4… = RESULT.md key-source table); the RED control outlives the verdict",
      _sha(_R2_LIB) == "a331f0351b3eca9ac2e64636e94a906045deb209f25888f38a8ab07e4d715a40" and _sha(f"{HERE}/{_R2_S2}") == "b2f9cfd40b9e356536184a63e202aa9d2a48228be5145bcd81665fb5f7df24e9", (_sha(_R2_LIB)[:8], _sha(f"{HERE}/{_R2_S2}")[:8]))
with tempfile.TemporaryDirectory() as d:
    # ── R3-D1: a null locator skipped BOTH the path comparison and the hash — and the helper still said "verified" ───────────────────────────────
    for _r in ("dlw/data", "f8/data", "f8/models"): os.makedirs(f"{d}/{_r}", exist_ok=True)
    _UIN = {"targets": f"{d}/dlw/data/dlw_targets.npz", "fea82": f"{d}/dlw/data/dlw_fea82.npz", "fea89": f"{d}/f8/data/f8_fea89.npz", "legs": f"{d}/f8/data/f10v2_legs.npz"}
    for _k, _v in _UIN.items(): open(_v, "wb").write(_k.encode())
    _UPT = f"{d}/f8/models/f10_live_s42.pt"; open(_UPT, "wb").write(b"weights 42"); _UREF = f"{HERE}/pod_f10_refit_v4.py"; _USAY = f"{d}/say.log"
    _UBASE = {"seed": 42, "best_ep_rule": "fix7", "best_ep_kept": 7, "env_given": {"F10_DLW": f"{d}/dlw", "F10_OUT": f"{d}/f8", "SEED": "42", "BEST_EP_FIX": "7"},   # canonical: the writer's fields and layout ([T] no-drift cells)
              "inputs": dict(_UIN), "inputs_sha256": {k: _sha(v) for k, v in _UIN.items()}, "pt": _UPT, "pt_sha256": _sha(_UPT), "self_sha256": _sha(_UREF)}
    def _uside(lib, obj):   # the seven-argument call the driver makes (chain_v4_monthly.sh arms stage), identical for the old and the new source
        _p = f"{d}/f8/models/f10_live_s42.json"; json.dump(obj, open(_p, "w")); open(_USAY, "w").close()
        rc, out = _bash(f". {lib}; prereq_refit_sidecar arms refit_s42 {_p} {d}/dlw {d}/f8 42 {_UREF}; echo rc=$?", {"L": _USAY, "PY": PY, "R": d})
        return rc, out + open(_USAY).read()   # the ok line goes through `say` to $L; refusals also reach stderr
    _rc_o, _o_o = _uside(_R2_LIB, _UBASE); _rc_n, _o_n = _uside(_NEW_LIB, _UBASE)
    check("★★★ [U] D1 POSITIVE (both sources): the canonical seed-42 sidecar with every file intact ⇒ rc 0 and '4 inputs + weights verified' — round 4 changes nothing for a sound sidecar",
          _rc_o == 0 and _rc_n == 0 and "4 inputs + weights verified against the bytes on disk" in _o_n and "FAIL" not in _o_n, (_rc_o, _rc_n, _o_n[-200:]))
    for _k in ("targets", "fea82", "fea89", "legs"):
        _keep = open(_UIN[_k], "rb").read(); open(_UIN[_k], "wb").write(_keep + b" CHANGED")
        _m = json.loads(json.dumps(_UBASE)); _m["inputs"][_k] = None
        _rc_w, _ = _uside(_R2_LIB, _UBASE)   # the same byte change with the locator KEPT: already refused before round 4 (researcher D1_changed_<role>_with_path_rejected)
        _rc_o, _o_o = _uside(_R2_LIB, _m); _rc_n, _o_n = _uside(_NEW_LIB, _m); open(_UIN[_k], "wb").write(_keep)
        check(f"★★★ [U] D1 (researcher D1_changed_{_k}_null_locator_ACCEPTED, rc 0): {_k} bytes CHANGED and inputs.{_k} = null (key set complete, old sha kept) ⇒ pre-round-4 ACCEPTS rc 0 and prints '4 inputs + weights verified' (with the locator kept it refused, rc {_rc_w}); round 4 REFUSES rc 3 naming the null locator AND the changed bytes at this month's path, and prints no 'verified'",
              _rc_w == 3 and _rc_o == 0 and "4 inputs + weights verified" in _o_o and _rc_n == 3 and f"input {_k} locator is None" in _o_n and f"input {_k} changed since refit" in _o_n and "verified against" not in _o_n and "FAIL_arms_prereq_refit_s42" in _o_n,
              (_rc_w, _rc_o, _rc_n, _o_n[-240:]))
    _m = json.loads(json.dumps(_UBASE)); _m["inputs"] = {k: None for k in _UIN}
    _rc_o, _o_o = _uside(_R2_LIB, _m); _rc_n, _o_n = _uside(_NEW_LIB, _m)
    check("★★★ [U] D1 (researcher D1_all_four_null_locators_ACCEPTED, rc 0): all four input locators null, the four shas kept ⇒ pre-round-4 ACCEPTS rc 0 claiming '4 inputs + weights verified' although no input path was compared; round 4 REFUSES rc 3 naming each null locator",
          _rc_o == 0 and "4 inputs + weights verified" in _o_o and _rc_n == 3 and all(f"input {k} locator is None" in _o_n for k in _UIN) and "verified against" not in _o_n, (_rc_o, _rc_n, _o_n[-240:]))
    _keep = open(_UIN["targets"], "rb").read(); os.remove(_UIN["targets"]); _m = json.loads(json.dumps(_UBASE)); _m["inputs"]["targets"] = None
    _rc_o, _o_o = _uside(_R2_LIB, _m); _rc_n, _o_n = _uside(_NEW_LIB, _m); open(_UIN["targets"], "wb").write(_keep)
    check("★★★ [U] D1 (researcher D1_missing_target_null_locator_ACCEPTED, rc 0): the targets file DELETED and its locator nulled ⇒ pre-round-4 ACCEPTS rc 0; round 4 REFUSES rc 3 'input targets missing on disk at this month's path' — the expected file is checked whatever the locator says",
          _rc_o == 0 and _rc_n == 3 and "input targets missing on disk at this month's path" in _o_n and "input targets locator is None" in _o_n, (_rc_o, _rc_n, _o_n[-240:]))
    _rc_n, _o_n = _uside(_NEW_LIB, _UBASE)
    check("★★ [U] D1 restore: after the mutations the canonical sidecar is accepted again by the round-4 source (rc 0) — every refusal above was caused by its own mutation", _rc_n == 0 and "4 inputs + weights verified" in _o_n, (_rc_n, _o_n[-160:]))
    # ── R3-D3: the month contract is DATA — one grammar, parsed, never sourced ─────────────────────────────────────────────────────────────────────
    _UF = f"{d}/d3"; os.makedirs(_UF, exist_ok=True)
    _UV = dict.fromkeys(_KEYS, f"{_UF}/unused"); _UV.update(V4_MONTH="2026-10", R=f"{_UF}/root", PY=PY, SEEDS="42", MONTHS_ALL="202501,202502,202503,202504", MWF_ROOT="mwf", BUNDLE_GENERATION="v4_test")   # the researcher's generator
    def _ucfg(name, value, key="SEEDS", append=""):
        _v = dict(_UV); _v[key] = value; _p = f"{_UF}/{name}.env"; open(_p, "w").write("".join(f"{k}={_v[k]}\n" for k in _KEYS) + append); return _p
    def _uload(lib, envf, key, extra=None):   # the REAL driver's shell (chain_v4_monthly.sh L29/L34): pipefail on, errexit/nounset off, `load_month_env "$ENVF" || exit 4`
        _e = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PY": PY, "PYTHONDONTWRITEBYTECODE": "1", "L": "/dev/null"}; _e.update(extra or {})
        _p = subprocess.run(["/bin/bash", "-c", 'set -o pipefail; . "$1"; load_month_env "$2" || exit 4; printf "VALUE=<%s>\\n" "${!3}"', "u", lib, envf, key], capture_output=True, text=True, env=_e, cwd=_UF, timeout=60)
        return _p.returncode, _p.stdout + _p.stderr
    _e = _ucfg("bundle_cont", "$R\\\nBUNDLE_TAR=stage", key="BUNDLE_OUT"); _res = {}
    for _lab in ("A", "B"):
        _par = f"{_UF}/parent_bundle_{_lab}"; _res[_lab] = (_uload(_R2_LIB, _e, "BUNDLE_OUT", {"RBUNDLE_TAR": _par}), _uload(_NEW_LIB, _e, "BUNDLE_OUT", {"RBUNDLE_TAR": _par}), _par)
    check("★★★ [U] D3 (researcher D3_bundle_continuation_A/B, rc 0 MONTH_ENV_OK): a trailing backslash joins `BUNDLE_OUT=$R\\` with the next line into $RBUNDLE_TAR, a PARENT variable — the SAME contract bytes give BUNDLE_OUT=<parent A>=stage and =<parent B>=stage under the pre-round-4 loader; round 4 REFUSES both rc 4 month_env_malformed naming the backslash, no MONTH_ENV_OK",
          all(r[0][0] == 0 and f"VALUE=<{r[2]}=stage>" in r[0][1] and "MONTH_ENV_OK" in r[0][1] for r in _res.values())
          and all(r[1][0] == 4 and "FAIL_month_env_malformed_bundle_cont.env" in r[1][1] and "a backslash" in r[1][1] and "MONTH_ENV_OK" not in r[1][1] for r in _res.values()),
          {k: (r[0][0], r[1][0], r[1][1][-200:]) for k, r in _res.items()})
    _e = _ucfg("seeds_cont", "$R\\\nMWF_ROOT=value", append="MWF_ROOT=mwf\n")
    _o = _uload(_R2_LIB, _e, "SEEDS", {"RMWF_ROOT": "PARENT_CONTROLLED"}); _n = _uload(_NEW_LIB, _e, "SEEDS", {"RMWF_ROOT": "PARENT_CONTROLLED"})
    check("★★★ [U] D3 (researcher D3_continuation_forms_external_reference, rc 0): `SEEDS=$R\\` + next line ⇒ pre-round-4 SEEDS = PARENT_CONTROLLED=value (the parent's $RMWF_ROOT, a name no grep saw); round 4 rc 4 month_env_malformed",
          _o[0] == 0 and "VALUE=<PARENT_CONTROLLED=value>" in _o[1] and _n[0] == 4 and "FAIL_month_env_malformed" in _n[1] and "VALUE=<" not in _n[1], (_o[0], _n[0], _n[1][-200:]))
    _e = _ucfg("unclosed_quote", "42", append='X="\n')
    _o = _uload(_R2_LIB, _e, "SEEDS"); _n = _uload(_NEW_LIB, _e, "SEEDS")
    check("★★★ [U] D3 (researcher D3_source_parse_error_ignored, rc 0): 46 complete keys then `X=\"` ⇒ pre-round-4: bash reports 'unexpected EOF' yet the loader returns rc 0 and prints MONTH_ENV_OK (the source rc was never read); round 4 REFUSES rc 4 malformed (X is not a registered key, a quote is not in the grammar), no MONTH_ENV_OK",
          _o[0] == 0 and "unexpected EOF" in _o[1] and "MONTH_ENV_OK" in _o[1] and _n[0] == 4 and "FAIL_month_env_malformed" in _n[1] and "MONTH_ENV_OK" not in _n[1], (_o[0], _n[0], _n[1][-200:]))
    _mk_o = f"{_UF}/GRAMMAR_COMMAND_MARKER_old"; _mk_n = f"{_UF}/GRAMMAR_COMMAND_MARKER_new"
    _o = _uload(_R2_LIB, _ucfg("prefixed_old", f"42 : > {_mk_o}", append="SEEDS=42\n"), "SEEDS"); _n = _uload(_NEW_LIB, _ucfg("prefixed_new", f"42 : > {_mk_n}", append="SEEDS=42\n"), "SEEDS")
    check("★★★ [U] D3 (researcher D3_assignment_prefixed_command_marker_written, rc 0): `SEEDS=42 : > <marker>` then `SEEDS=42` ⇒ pre-round-4 accepts rc 0 AND the redirection CREATED the marker (a KEY=value prefix is a command, not data); round 4 REFUSES rc 4 malformed and its marker does NOT exist — the file is parsed, never executed",
          _o[0] == 0 and os.path.exists(_mk_o) and _n[0] == 4 and "FAIL_month_env_malformed" in _n[1] and not os.path.exists(_mk_n), (_o[0], os.path.exists(_mk_o), _n[0], os.path.exists(_mk_n), _n[1][-200:]))
    _e = _ucfg("tilde", "~/king", key="KING_DIR"); _ro, _rn = {}, {}
    for _h in ("parent_A", "parent_B"):
        os.makedirs(f"{_UF}/{_h}", exist_ok=True); _ro[_h] = _uload(_R2_LIB, _e, "KING_DIR", {"HOME": f"{_UF}/{_h}"}); _rn[_h] = _uload(_NEW_LIB, _e, "KING_DIR", {"HOME": f"{_UF}/{_h}"})
    check("★★ [U] D3 (researcher D3_parent_tilde_parent_A/B, rc 0): `KING_DIR=~/king` holds no $ at all, yet under the pre-round-4 loader it follows the parent HOME (same bytes, two HOMEs, two KING_DIRs); round 4 REFUSES rc 4 for both (a tilde is not in the grammar)",
          all(_ro[h][0] == 0 and f"VALUE=<{_UF}/{h}/king>" in _ro[h][1] for h in _ro) and all(_rn[h][0] == 4 and "a tilde" in _rn[h][1] for h in _rn), ({h: _ro[h][0] for h in _ro}, {h: (_rn[h][0], _rn[h][1][-120:]) for h in _rn}))
    _q = {}
    for _lab, _val in (("double_quoted", '"$R/raw"'), ("single_quoted", "'$R/raw'"), ("escaped", "\\$R/raw")):
        _e = _ucfg("q_" + _lab, _val); _q[_lab] = (_uload(_R2_LIB, _e, "SEEDS"), _uload(_NEW_LIB, _e, "SEEDS"))
    check("★★ [U] D3 (researcher D3_earlier_double_quoted / _single_quoted / _escaped, rc 0; 词法与求值不同): the pre-round-4 loader accepts all three and the same-looking `$R/raw` yields TWO values (double quotes <R>/raw; single quotes and backslash the literal text $R/raw); round 4 has no quoting and no escaping — all three rc 4 malformed",
          all(v[0][0] == 0 for v in _q.values()) and f"VALUE=<{_UF}/root/raw>" in _q["double_quoted"][0][1] and "VALUE=<$R/raw>" in _q["single_quoted"][0][1] and "VALUE=<$R/raw>" in _q["escaped"][0][1]
          and all(v[1][0] == 4 and "FAIL_month_env_malformed" in v[1][1] for v in _q.values()), {k: (v[0][0], v[1][0], v[1][1][-100:]) for k, v in _q.items()})
    _e = _ucfg("dup", "42", append="SEEDS=2027\n"); _o = _uload(_R2_LIB, _e, "SEEDS"); _n = _uload(_NEW_LIB, _e, "SEEDS")
    check("★★ [U] D3 grammar: a key defined TWICE (`SEEDS=42` in place, `SEEDS=2027` appended) ⇒ pre-round-4 silently takes the LAST (SEEDS=2027, rc 0) while a reader of the file sees 42; round 4 REFUSES rc 4 month_env_duplicate_key_SEEDS",
          _o[0] == 0 and "VALUE=<2027>" in _o[1] and _n[0] == 4 and "FAIL_month_env_duplicate_key_SEEDS" in _n[1] and "defined a second time" in _n[1], (_o[0], _n[0], _n[1][-200:]))
    _e = _ucfg("unreg", "42", append="EXTRA_KNOB=1\n"); _o = _uload(_R2_LIB, _e, "EXTRA_KNOB"); _n = _uload(_NEW_LIB, _e, "EXTRA_KNOB")
    check("★★ [U] D3 grammar: a line whose KEY is not registered (`EXTRA_KNOB=1`) ⇒ pre-round-4 exports it too (set -a, rc 0); round 4 REFUSES rc 4 malformed — a contract carries exactly the registered keys",
          _o[0] == 0 and "VALUE=<1>" in _o[1] and _n[0] == 4 and "FAIL_month_env_malformed" in _n[1] and "not a registered contract key" in _n[1], (_o[0], _n[0], _n[1][-200:]))
    _e = _ucfg("braced_earlier", "${R}/raw"); _n = _uload(_NEW_LIB, _e, "SEEDS")
    check("★★ [U] D3 POSITIVE grammar: `${R}/raw` (braced reference to a key defined earlier) ⇒ rc 0 and the parser substitutes R's value itself", _n[0] == 0 and f"VALUE=<{_UF}/root/raw>" in _n[1], (_n[0], _n[1][-160:]))
    def _udump(lib, envf):   # the FULL exported environment after the loader, under a polluted parent
        _e = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PY": PY, "PYTHONDONTWRITEBYTECODE": "1", "L": "/dev/null", "CHAIN_DEVICE_DIR": HERE, "R": "/tmp/inherited_junk", "SEEDS": "999", "UNLISTED_SEEDS": "2027", "RBUNDLE_TAR": "/tmp/parent_junk", "HOME": "/tmp/parent_home"}
        _p = subprocess.run(["/bin/bash", "-c", 'set -o pipefail; . "$1"; load_month_env "$2" || exit 4; env', "u", lib, envf], capture_output=True, text=True, env=_e, cwd=d, timeout=60)
        _ok = [l for l in _p.stdout.splitlines() if l.startswith("MONTH_ENV_OK ")]
        return _p.returncode, _ok, dict(l.split("=", 1) for l in _p.stdout.splitlines() if "=" in l and not l.startswith("MONTH_ENV_OK ")), _p.stderr
    for _cf in ("v4_month_2026-09.env", "v4_month_2026-10.env.template"):
        _o = _udump(_R2_LIB, f"{HERE}/{_cf}"); _n = _udump(_NEW_LIB, f"{HERE}/{_cf}"); _nr = sum(1 for l in open(f"{HERE}/{_cf}") if not l.startswith("#") and "$R" in l)
        check(f"★★★ [U] D3 POSITIVE {_cf} (bytes unchanged, sha {_sha(f'{HERE}/{_cf}')[:8]}): the round-4 parser and the pre-round-4 source-based loader export the IDENTICAL environment (every variable, incl. all 46 keys, V4_MONTH_ENV, the derived V4_* names) and print the identical MONTH_ENV_OK line, under a polluted parent (R, SEEDS, UNLISTED_SEEDS, RBUNDLE_TAR, HOME); its {_nr} `$R/...` values resolve the same",
              _o[0] == 0 and _n[0] == 0 and _o[1] == _n[1] and len(_n[1]) == 1 and _o[2] == _n[2] and all(k in _n[2] for k in _KEYS) and _n[2]["SEEDS"] == "42,2027" and _n[2]["V4_MONTH_ENV"] == f"{HERE}/{_cf}" and _n[3] == "",
              (_o[0], _n[0], sorted(set(_o[2].items()) ^ set(_n[2].items()))[:4], _n[3][-200:]))
    _n = _uload(_NEW_LIB, f"{HERE}/v4_month_2026-09.env", "SEEDS", {"PY": f"{d}/no_such_python"})
    check("★★★ [U] D3 the parser's RETURN CODE is checked: $PY naming a nonexistent interpreter ⇒ rc 4 FAIL_month_env_parser_failed_rc_127 and no MONTH_ENV_OK (the round-3 loader never read its source rc)",
          _n[0] == 4 and "FAIL_month_env_parser_failed_rc_127" in _n[1] and "MONTH_ENV_OK" not in _n[1], (_n[0], _n[1][-200:]))
    _LIAR = f"{d}/liar_python"; open(_LIAR, "w").write("#!/bin/sh\ncat >/dev/null\necho 'SEEDS=42 ; true'\nexit 0\n"); os.chmod(_LIAR, 0o755)
    _n = _uload(_NEW_LIB, f"{HERE}/v4_month_2026-09.env", "SEEDS", {"PY": _LIAR})
    check("★★ [U] D3 rc 0 alone is not trusted: a parser that exits 0 but emits a single key whose value is outside the grammar ⇒ rc 4 FAIL_month_env_parser_output before anything is exported (each line re-validated in bash: registered key, once, LITERAL value; all 46 present)",
          _n[0] == 4 and "FAIL_month_env_parser_output" in _n[1] and "MONTH_ENV_OK" not in _n[1], (_n[0], _n[1][-200:]))
    _rc_n, _o_n = _bash(f"V4_DRYRUN=1 V4_STAGES=preflight bash {HERE}/chain_v4_monthly.sh {_UF}/bundle_cont.env", {"PY": PY, "RBUNDLE_TAR": f"{_UF}/parent_bundle_A"})
    check("★★ [U] D3 end to end: the DRIVER on the continuation contract exits rc 4 at load_month_env (FAIL_month_env_malformed) before any stage runs or any month-root directory is created",
          _rc_n == 4 and "FAIL_month_env_malformed" in _o_n and not os.path.exists(f"{_UF}/root"), (_rc_n, _o_n[-200:]))
    _LIBT = open(_NEW_LIB).read(); _LFN = "\n".join(l for l in _LIBT.split("load_month_env(){", 1)[1].split("\ngate_sha(){", 1)[0].splitlines() if not l.lstrip().startswith("#"))   # code lines only: comments may say what the loader used to do
    check("★★ [U] D3 static: load_month_env no longer sources the contract (no `. \"$f\"`, no `source`, no `set -a`) and the driver still calls it as `load_month_env \"$ENVF\" || exit 4`",
          '. "$f"' not in _LFN and "source " not in _LFN and "set -a" not in _LFN and 'load_month_env "$ENVF" || exit 4' in open(f"{HERE}/chain_v4_monthly.sh").read(), [s for s in ('. "$f"', "source ", "set -a") if s in _LFN])
    # ── R3-D3 on the DRYRUN path (lead follow-up 2026-09-13): chain_v4_monthly_dryrun.sh derived its negative-control env by SOURCING the source contract ─────────
    _R2_DRY = f"{HERE}/chain_v4_monthly_dryrun.r2_6239a691.sh"; _NEW_DRY = f"{HERE}/chain_v4_monthly_dryrun.sh"
    check("★★★ [U] D3 DRYRUN the pre-fix dryrun script is archived beside the current one (chain_v4_monthly_dryrun.r2_6239a691.sh = committed 6239a691…, the version that sources the contract); the RED control outlives the verdict",
          _sha(_R2_DRY) == "6239a69186a22922570829d2db506e05a0a47c667c5cd39ff368724a1212594d", _sha(_R2_DRY)[:8])
    def _udry(script, envf, tag, extra=None):   # one dryrun run on <envf> in a fresh scratch parent; the derived env comes back with that run's random scratch root replaced by <ROOT>
        _par = f"{_UF}/dry_{tag}"; os.makedirs(_par, exist_ok=True)
        rc, out = _bash(f"bash {script} {envf} {_par}", {"PY": PY, **(extra or {})})
        _de = _glob.glob(f"{_par}/v4_dryrun_*/v4_month_dryrun.env")
        return rc, out, (open(_de[0]).read().replace(os.path.dirname(_de[0]), "<ROOT>") if _de else None), _par
    _only = lambda a, b: sorted(set(a.splitlines()) - set(b.splitlines())) if (a is not None and b is not None) else None
    _dmo = f"{_UF}/DRYRUN_COMMAND_MARKER_old"; _dmn = f"{_UF}/DRYRUN_COMMAND_MARKER_new"
    _o = _udry(_R2_DRY, _ucfg("dry_prefixed_old", f"42 : > {_dmo}", append="SEEDS=42\n"), "po"); _n = _udry(_NEW_DRY, _ucfg("dry_prefixed_new", f"42 : > {_dmn}", append="SEEDS=42\n"), "pn")
    check("★★★ [U] D3 DRYRUN (researcher D3_assignment_prefixed_command_marker_written, on the dryrun path): source contract with `SEEDS=42 : > <marker>` then `SEEDS=42` ⇒ the pre-fix dryrun SOURCED it to derive its env, so the redirection RAN (marker created) and the control still said DRYRUN_PASS rc 0; the fixed dryrun reads it only through load_month_env ⇒ rc 2 'dryrun env derivation failed' + FAIL_month_env_malformed, no derived env, no driver run, and its marker does NOT exist",
          _o[0] == 0 and "DRYRUN_PASS" in _o[1] and os.path.exists(_dmo) and _n[0] == 2 and "FAIL_month_env_malformed" in _n[1] and "dryrun env derivation failed" in _n[1] and _n[2] is None
          and not _glob.glob(f"{_n[3]}/v4_dryrun_*/driver.out") and not os.path.exists(_dmn), (_o[0], os.path.exists(_dmo), _n[0], os.path.exists(_dmn), _n[1][-240:]))
    _e = _ucfg("dry_unclosed", "42", append='X="\n'); _o = _udry(_R2_DRY, _e, "qo"); _n = _udry(_NEW_DRY, _e, "qn")
    check("★★★ [U] D3 DRYRUN (researcher D3_source_parse_error_ignored, on the dryrun path): 46 complete keys then `X=\"` ⇒ the pre-fix dryrun printed bash's 'unexpected EOF' from its own source of the contract, ignored it and still said DRYRUN_PASS rc 0; the fixed dryrun refuses the derivation rc 2 (FAIL_month_env_malformed) and runs no driver",
          _o[0] == 0 and "unexpected EOF" in _o[1] and "DRYRUN_PASS" in _o[1] and _n[0] == 2 and "FAIL_month_env_malformed" in _n[1] and _n[2] is None and not _glob.glob(f"{_n[3]}/v4_dryrun_*/driver.out"), (_o[0], _n[0], _n[1][-240:]))
    _e = _ucfg("dry_bundle_cont", "$R\\\nBUNDLE_TAR=stage", key="BUNDLE_OUT"); _dc = {}
    for _lab in ("A", "B"):
        _pb = f"{_UF}/dry_parent_bundle_{_lab}"; _dc[_lab] = (_udry(_R2_DRY, _e, f"co{_lab}", {"RBUNDLE_TAR": _pb}), _udry(_NEW_DRY, _e, f"cn{_lab}", {"RBUNDLE_TAR": _pb}))
    check("★★★ [U] D3 DRYRUN (researcher D3_bundle_continuation_A/B, on the dryrun path): the SAME source contract bytes with parent RBUNDLE_TAR=A or =B ⇒ the pre-fix dryrun derived two different envs whose ONLY differing line is BUNDLE_OUT (…/dry_parent_bundle_A=stage vs …_B=stage: a parent variable reached the derivation through the backslash) and said PASS both times; the fixed dryrun refuses both rc 2 (FAIL_month_env_malformed)",
          all(r[0][0] == 0 and "DRYRUN_PASS" in r[0][1] for r in _dc.values()) and _only(_dc["A"][0][2], _dc["B"][0][2]) == ["BUNDLE_OUT=<ROOT>/root/dry_parent_bundle_A=stage"]
          and all(r[1][0] == 2 and "FAIL_month_env_malformed" in r[1][1] and r[1][2] is None for r in _dc.values()), ({k: (r[0][0], r[1][0]) for k, r in _dc.items()}, _only(_dc["A"][0][2], _dc["B"][0][2])))
    _dp = {}
    for _cf in ("v4_month_2026-09.env", "v4_month_2026-10.env.template"):
        _dp[_cf] = (_udry(_R2_DRY, f"{HERE}/{_cf}", "so_" + _cf[9:16]), _udry(_NEW_DRY, f"{HERE}/{_cf}", "sn_" + _cf[9:16]))
    check("★★★ [U] D3 DRYRUN POSITIVE (both delivered contracts, bytes unchanged): the pre-fix and the fixed dryrun both PASS rc 0 (driver stopped at preflight, nothing launched) and derive the IDENTICAL env once each run's scratch root is replaced by <ROOT> — only HOW the source contract is read changed",
          all(v[0][0] == 0 and v[1][0] == 0 and "DRYRUN_PASS" in v[0][1] and "DRYRUN_PASS" in v[1][1] and v[0][2] is not None and v[0][2] == v[1][2] for v in _dp.values()),
          {k: (v[0][0], v[1][0], _only(v[0][2], v[1][2])) for k, v in _dp.items()})
    _DRYC = "\n".join(l for l in open(_NEW_DRY).read().splitlines() if not l.lstrip().startswith("#"))   # code lines only: comments may say what the dryrun used to do
    check("★★ [U] D3 DRYRUN static: the fixed dryrun no longer sources the source contract (no `. \"$SRC\"`, no `set -a`) and reads it through `load_month_env \"$SRC\"`",
          '. "$SRC"' not in _DRYC and "set -a" not in _DRYC and 'load_month_env "$SRC"' in _DRYC, [s for s in ('. "$SRC"', "set -a") if s in _DRYC])
    # ── R3-D2: the gate must validate the object the exporter indexes, not its int64 cast ───────────────────────────────────────────────────────────
    _EXT = _uast.parse(open(f"{HERE}/pod_export_bundle_v4.py").read())
    _SUB = [n for n in _uast.walk(_EXT) if isinstance(n, _uast.Subscript) and isinstance(n.value, _uast.Name) and n.value.id == "y4" and _uast.unparse(n.slice) == "(i, m)"]
    def _consume(arr):   # ONLY the exporter's own `y4[i, m]` expression taken from its AST, on a 2×6 array — the exporter program is never imported or run
        try:
            eval(compile(_uast.Expression(_SUB[0]), "exporter_subscript_AST", "eval"), {"__builtins__": {}}, {"y4": np.arange(12.).reshape(2, 6), "i": 0, "m": arr}); return "OK"
        except Exception as _x:
            return type(_x).__name__
    _bU = _base(1, _NA_NEW); _write_month(f"{d}/U1", _bU, _NA_NEW, "new"); _write_month(f"{d}/U0", _bU, _NA_REF, "ref")
    _UMF = f"{d}/U1/king_meta.npz"; _UMT = {k: v.copy() for k, v in np.load(_UMF, allow_pickle=True).items()}
    def _umemb(arr, out, script):   # ONE new-tail anchor's persisted member index := `arr` exactly as given (dtype kept), run the gate, restore
        _mm = {k: v.copy() for k, v in _UMT.items()}; _mm["members"][_NA_REF] = arr; np.savez(_UMF, **_mm)
        rc, _, r = _g(script, _none_env(f"{d}/U1", f"{d}/U0", f"{d}/{out}.json", f"{d}/R{out}")); np.savez(_UMF, **_UMT); return rc, r
    check("★ [U] D2 setup: the exporter source has exactly the `y4[i, m]` subscript the review names (the consumer the gate must agree with)", len(_SUB) >= 1, len(_SUB))
    for _lab, _arr, _dt, _who in (("bool_pair", np.array([False, True]), "bool", "researcher D2_tail_boolean"), ("bool_one", np.array([True]), "bool", "researcher D2_tail_bool_one"),
                                  ("float_integral", np.array([0., 1., 2.]), "float64", "researcher D2_tail_float_integral"),
                                  ("object_ints", np.array([0, 1, 2, 3, 4, 5], dtype=object), "object", "adjacent: the shape np.array(MS, dtype=object) takes when every anchor has the same member count")):
        _rc_o, _r_o = _umemb(_arr, f"u2o_{_lab}", _R2_S2); _rc_n, _r_n = _umemb(_arr, f"u2n_{_lab}", "v4_gate_step2_m.py"); _c = _consume(_arr)
        check(f"★★★ [U] D2 ({_who}): a new-tail anchor whose PERSISTED member index is {_dt} {_arr.tolist()} ⇒ pre-round-4 gate PASSes rc 0 with member_index_ok true (it validated the int64 CAST) while the exporter's own y4[i, m] raises {_c} on that array; round 4 FAILs rc 3, member_index_ok false, 'dtype {_dt}' named",
              _rc_o == 0 and _r_o["PASS"] is True and _r_o["tail_quality"]["member_index_ok"] is True and _c == "IndexError" and _rc_n == 3 and _r_n["PASS"] is False
              and _r_n["tail_quality"]["member_index_ok"] is False and f"dtype {_dt}" in _r_n["tail_quality"]["member_index_bad"][0]["why"][0], (_rc_o, _rc_n, _c, _r_n and _r_n.get("tail_quality")))
    _pos = {}
    for _lab, _arr in (("int64_perm", np.array([5, 4, 3, 2, 1, 0], dtype=np.int64)), ("int32", np.arange(6, dtype=np.int32)), ("uint16", np.arange(6, dtype=np.uint16))):
        _pos[_lab] = (_umemb(_arr, f"u2po_{_lab}", _R2_S2), _umemb(_arr, f"u2pn_{_lab}", "v4_gate_step2_m.py"), _consume(_arr))
    check("★★★ [U] D2 POSITIVE (both sources): signed/unsigned INTEGER member indexes (int64 permutation, int32, uint16) PASS rc 0 with member_index_ok true and no member_index_bad, and the exporter's y4[i, m] consumes each — integer KIND is the contract, not int64 exactly",
          all(v[0][0] == 0 and v[1][0] == 0 and v[1][1]["tail_quality"]["member_index_ok"] is True and "member_index_bad" not in v[1][1]["tail_quality"] and v[2] == "OK" for v in _pos.values()),
          {k: (v[0][0], v[1][0], v[2]) for k, v in _pos.items()})
    _rc_n, _r_n = _umemb(np.array([[0, 1], [2, 3]], dtype=np.int64), "u2n_ndim2", "v4_gate_step2_m.py")
    check("★★ [U] D2 the pre-existing structural rules still follow the dtype rule: an INTEGER but 2-D index ⇒ FAIL rc 3 'ndim 2 != 1' (dtype first, then 1-D / range / uniqueness)",
          _rc_n == 3 and _r_n["tail_quality"]["member_index_ok"] is False and "ndim 2" in _r_n["tail_quality"]["member_index_bad"][0]["why"][0], (_rc_n, _r_n and _r_n.get("tail_quality")))
check("★★★ [U] G0 the contract-frozen and do-not-touch files are byte-identical after round 4: v4_gate_step1 278fdce6, v4_gate_step2 db7ab356, ELIGIBILITY_CONTRACT 1188267a, v4e_gate_export_v2 d63f4ec3, v4_gate_common 24e813f1, judge_v4 c2a81c48, make_sha_manifest ba521004, tests_judge_dynamic_deps 4dfee3fd",
      all(_sha(f"{HERE}/{f}") == s for f, s in (("v4_gate_step1.py", "278fdce611e91571d24ec26c78ddc4620668bfd4598a01f577f1f6887dd62be4"), ("v4_gate_step2.py", "db7ab3561f97423a8d5dd74251257adcedd743129d22a07d7cd186d102dd80d8"),
                                                ("ELIGIBILITY_CONTRACT.json", "1188267adf420c0b3a39a4b20a8a131ee80ae5d667b5056006465dbaba50a732"), ("v4e_gate_export_v2.py", "d63f4ec3f9e657259c2d4826f95552007f34eb63eab1d67357d8ad5b54cd5c1e"),
                                                ("v4_gate_common.py", "24e813f145c35033552ee54ae166092a8204490ff52c011a87217a8e81a187a1"), ("judge_v4.py", "c2a81c48f037756067b23225b5a6bbee43ce6589898db3230437a17d398956ba"),
                                                ("make_sha_manifest.py", "ba521004daaa164e815d92a7ee28810f84e1d4dd526fd3ed06550720e50cd4b1"), ("tests_judge_dynamic_deps.py", "4dfee3fd016a708ee320c5d23585632071e4f79331209d6a88f06d9829aa5122"))),
      [_sha(f"{HERE}/{f}")[:8] for f in ("v4_gate_step1.py", "v4_gate_step2.py", "ELIGIBILITY_CONTRACT.json", "v4e_gate_export_v2.py", "v4_gate_common.py", "judge_v4.py", "make_sha_manifest.py", "tests_judge_dynamic_deps.py")])
