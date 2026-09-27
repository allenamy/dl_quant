#!/usr/bin/env python3
"""d10_dryrun_run.py -- the rebuild-device dry run, run ENTIRELY on pod2 under setsid (docs/PLAN_rebuild_devices_dry_run_2026-09-27.md,
frozen by lead acd2303b6; pre-run clarifications D4 reference / argv --out / gate_sha256 / interpreter sent to lead before any row ran).

Each row re-runs one device patched in d3a7f013d (+ argv/python in 3 receipts) on the SAME inputs as its delivered run and compares
the outputs with d10_dryrun_compare.py. Order and stop rule per plan s3: a DIFFERS or ERROR row stops everything after it; a
NOT_RUN row (input absent or changed, named) does not pass and does not stop. Rows never overwrite anything: every output goes to
$W/out. Input files are checked against the sha their reference receipt recorded before the device runs.
Log: $W/logs/dryrun.log, one anchored line per event: `<utc> ROW <name> <IDENTICAL|DIFFERS|NOT_RUN|ERROR|PASS|FAIL> ...`, last line
`<utc> DRYRUN_DONE ...` or `<utc> DRYRUN_STOP ...`. Results: $W/out/DRYRUN_RESULT.json (rewritten durably after every row).
usage (pod2): setsid nohup /workspace/venv/bin/python -B $W/devices/d10_dryrun_run.py $W </dev/null >/dev/null 2>&1 &
"""
import hashlib, json, os, shutil, subprocess, sys, time

W = sys.argv[1]
# rev 2 (lead 2026-09-27 06:2xZ, after the D3 EDQUOT stop): --part NAME --rows S0,D4a,... selects rows; --d3-notrun REASON records D3 as
# NOT_RUN without touching the volume; the log/marker lives on /dev/shm (E-0926-E: the failure signal must not sit on the volume
# whose failure it reports); D3 runs only behind a write probe of (reference size + 1 GiB) on the output volume, deleted at once.
_args = sys.argv[2:]
def _opt(k, d=None):
    return _args[_args.index(k) + 1] if k in _args else d
PART = _opt("--part", "part1")
ROWS = set(_opt("--rows", "").split(",")) - {""}
D3_NOTRUN = _opt("--d3-notrun")
DEV, OUT, REFS = f"{W}/devices", f"{W}/out", f"{W}/refs"
LOGD = f"/dev/shm/news2_dryrun_2026-09-27/{PART}" if PART != "part1" else f"{W}/logs"
EXP = "/dev/shm/d10_2026-09-25"
PYV = "/workspace/venv/bin/python"
NF = "/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz"
sys.path.insert(0, DEV)
sys.path.insert(0, f"{W}/common")
import durable_write as DW
import d10_dryrun_compare as CMP

os.makedirs(OUT, exist_ok=True); os.makedirs(LOGD, exist_ok=True)
# rev 3 (lead 2026-09-27, TEAM_PROTOCOL f0ee74b54): no scratch on pod2's root overlay (/tmp). Every tempfile of this runner, its
# comparator and every device it starts goes to a TMPDIR on /dev/shm, removed when the runner ends.
TMPD = f"/dev/shm/news2_dryrun_2026-09-27/{PART}/tmp"
os.makedirs(TMPD, exist_ok=True)
os.environ["TMPDIR"] = TMPD
import tempfile
tempfile.tempdir = TMPD
LOG = f"{LOGD}/dryrun.log"


def want(row):
    return not ROWS or row in ROWS
RESULT = {"plan": "docs/PLAN_rebuild_devices_dry_run_2026-09-27.md (frozen acd2303b6 + addendum 1)",
          "output_kinds": {"D1": "new_ledger.sha256 -> ledger_full_ms.npz (npz: file sha volatile, arrays compared)",
                           "D2a": "output.sha256 -> fund_state_snap.npz (npz)", "D2b": "output.sha256 -> fund_state_d10.npz (npz)",
                           "D3": "output.sha256 -> NEWS_FEATURES_D10.npz (npz)"}, "runner_sha256": None, "rows": [],
          "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pgid": os.getpgid(0)}


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def say(msg):
    with open(LOG, "a") as f:  # durable-exempt: append-only progress log, never read as an artifact by any device
        f.write(f"{utc()} {msg}\n")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def save():
    name = "DRYRUN_RESULT.json" if PART == "part1" else f"DRYRUN_RESULT_{PART}.json"
    DW.write_json(f"{LOGD}/{name}", RESULT, indent=1, allow_nan=True, default=str)   # tmpfs copy: always writable
    try:
        DW.write_json(f"{OUT}/{name}", RESULT, indent=1, allow_nan=True, default=str)
    except OSError as e:
        say(f"NOTE result copy on the output volume failed ({type(e).__name__}: {e}); the /dev/shm copy is authoritative")


def write_probe(dirpath, nbytes):
    """Write-then-delete probe on the output volume (df does not show the pod2 quota). True iff nbytes were written and fsync'd."""
    p = os.path.join(dirpath, ".quota_probe_news2")
    chunk = b"\0" * (64 << 20)
    done = 0
    try:
        with open(p, "wb") as f:  # durable-exempt: space probe, deleted in the finally below, never read by anyone
            while done < nbytes:
                n = min(len(chunk), nbytes - done)
                f.write(chunk[:n]); done += n
            f.flush(); os.fsync(f.fileno())
        return True, done
    except OSError:
        return False, done
    finally:
        try:
            os.unlink(p)
        except FileNotFoundError:
            pass


def resource_gate():
    """Team gate (read-only; never signals anything): others' bt_launch <= 2 distinct PGIDs, cgroup headroom >= 24 GiB, /dev/shm >= 4 GiB."""
    me = os.getpgid(0)
    ps = subprocess.run(["ps", "-eo", "pgid=,args="], capture_output=True, text=True).stdout.splitlines()
    others = {l.split(None, 1)[0] for l in ps if "bt_launch" in l and l.split(None, 1)[0] != str(me)}
    head = None
    try:
        mx = open("/sys/fs/cgroup/memory.max").read().strip(); cur = int(open("/sys/fs/cgroup/memory.current").read())
        head = (int(mx) - cur) / 2**30 if mx != "max" else float("inf")
    except Exception as e:
        return False, f"cgroup unreadable ({type(e).__name__}) -- unknown is not open"
    st = os.statvfs("/dev/shm"); shm = st.f_bavail * st.f_frsize / 2**30
    ok = len(others) <= 2 and head >= 24 and shm >= 4
    return ok, f"others_bt_launch_pgids={len(others)} cgroup_headroom_gib={head:.1f} shm_free_gib={shm:.1f}"


def inputs_ok(inputs):
    for p, want in inputs.items():
        if not os.path.exists(p):
            return False, f"NOT_RUN (input absent) {p}"
        got = sha(p)
        if not got.startswith(want):
            return False, f"NOT_RUN (input changed) {p} sha {got[:16]} != recorded {want[:16]}"
    return True, ""


def run_cmd(name, cmd, cwd=None, env=None):
    e = dict(os.environ); e.update(env or {})
    t0 = time.time()
    with open(f"{LOGD}/{name}.log", "w") as fo:  # durable-exempt: the row's own stdout/stderr capture, a log, not an artifact
        p = subprocess.run(["nice", "-n", "10"] + cmd, cwd=cwd, env=e, stdout=fo, stderr=subprocess.STDOUT)
    return p.returncode, round(time.time() - t0, 1), open(f"{LOGD}/{name}.log").read()


def cmp_npz(ref, new, tag):
    return CMP.compare_npz(ref, new) | {"tag": tag}


def cmp_json(ref, new, vol, oneway, tag, argv_out=()):
    return CMP.compare_json(ref, new, vol, oneway, argv_out=argv_out) | {"tag": tag}


GATE_OLD_SHA = "793c5eb2e85e8423"   # d10_manifest_gate.py as the reference receipts recorded it (fa6ac194b)
GATE_NEW_SHA = "6a8b16ca268aa585"   # after d3a7f013d (durable-exempt comments only -- to be PROVEN, not assumed)


def gate_ast_check():
    """lead freeze addendum 1 item 3: gate_sha256 is exempt only if ast.dump of the two gate versions is equal."""
    import ast
    old, new = f"{REFS}/d10_manifest_gate_793c5eb2.py", f"{DEV}/d10_manifest_gate.py"
    so, sn = sha(old), sha(new)
    ao, an = ast.dump(ast.parse(open(old).read())), ast.dump(ast.parse(open(new).read()))
    r = {"old_file_sha256": so, "new_file_sha256": sn, "old_ast_sha256": hashlib.sha256(ao.encode()).hexdigest(),
         "new_ast_sha256": hashlib.sha256(an.encode()).hexdigest(), "ast_equal": ao == an,
         "files_are_the_named_versions": so.startswith(GATE_OLD_SHA) and sn.startswith(GATE_NEW_SHA)}
    r["exempt"] = bool(r["ast_equal"] and r["files_are_the_named_versions"])
    return r


def gate_values_check(ref, new, g):
    """When exempting, the receipts must carry exactly the two proven versions -- not some third gate."""
    rv, nv = json.load(open(ref)).get("gate_sha256"), json.load(open(new)).get("gate_sha256")
    ok = rv == g["old_file_sha256"] and nv == g["new_file_sha256"]
    return {"kind": "gate_sha_values", "tag": "gate_sha256", "ref": rv, "new": nv, "verdict": "IDENTICAL" if ok else "DIFFERS"}


def finish(name, verdict, detail, comps=None, rc=None, secs=None, argv=None):
    row = {"row": name, "verdict": verdict, "detail": detail, "rc": rc, "seconds": secs, "argv": argv, "comparisons": comps or [],
           "utc": utc()}
    RESULT["rows"].append(row); save()
    say(f"ROW {name} {verdict} {detail}")
    if verdict in ("DIFFERS", "ERROR", "FAIL"):
        say(f"DRYRUN_STOP at {name}: {verdict} -- rows after it are not run (plan s3)")
        RESULT["final"] = f"STOP at {name}"; save(); sys.exit(1)


def identity_row(name, cmd, cwd, inputs, compares, env=None, gate=False):
    if gate:
        ok, why = resource_gate(); say(f"GATE {name} {'OPEN' if ok else 'CLOSED'} {why}")
        if not ok:
            RESULT["final"] = f"STOP at {name}: resource gate closed ({why})"; save()
            say(f"DRYRUN_STOP at {name}: resource gate closed -- relaunch later, rows done so far stand"); sys.exit(2)
    ok, why = inputs_ok(inputs)
    if not ok:
        return finish(name, "NOT_RUN", why, argv=cmd)
    rc, secs, _ = run_cmd(name, cmd, cwd, env)
    comps = []
    try:
        for c in compares:
            comps.append(c())
    except Exception as e:
        return finish(name, "ERROR", f"comparison crashed or output missing (device rc {rc}): {type(e).__name__}: {e}", comps, rc, secs, cmd)
    v = "IDENTICAL" if comps and all(c["verdict"] == "IDENTICAL" for c in comps) else "DIFFERS"
    brief = "; ".join(f"{c['tag']}={c['verdict']}" + (f"(keys {c.get('differing_keys')})" if c.get("differing_keys") else "")
                      + (f"(paths {[d['path'] for d in c.get('differ', [])][:4]} only_ref {c.get('only_ref', [])[:3]} only_new {c.get('only_new', [])[:3]})"
                         if c["kind"] == "json" and c["verdict"] != "IDENTICAL" else "") for c in comps)
    finish(name, v, f"rc={rc} {secs}s {brief}", comps, rc, secs, cmd)


def main():
    RESULT["runner_sha256"] = sha(os.path.realpath(__file__))
    RESULT["comparator_sha256"] = sha(f"{DEV}/d10_dryrun_compare.py")
    RESULT["devices_sha256"] = {n: sha(f"{DEV}/{n}") for n in sorted(os.listdir(DEV)) if n.endswith((".py", ".sh"))}
    RESULT["common_sha256"] = {n: sha(f"{W}/common/{n}") for n in sorted(os.listdir(f"{W}/common")) if n.endswith(".py")}
    say(f"START pgid={os.getpgid(0)} runner={RESULT['runner_sha256'][:16]} W={W}")
    save()

    # S0 -- plan s1.5: comparator self-test on a real reference npz + json before any row is read
    st = CMP.selftest(f"{EXP}/lineD/stage2/fund_state_snap.npz", f"{REFS}/fund_state_snap_RECEIPT.json")
    RESULT["selftest"] = st; save()
    say(f"ROW S0_comparator_selftest {'PASS' if st['verdict'] == 'SELFTEST_PASS' else 'FAIL'} {json.dumps(st['cells'])[:400]}")
    if st["verdict"] != "SELFTEST_PASS":
        RESULT["final"] = "STOP at S0"; save(); say("DRYRUN_STOP at S0: comparator has no demonstrated power"); sys.exit(1)

    # D7 symlists: every file byte-for-byte, and the same file set
    if want('D7_symlists'):
        cmd = [PYV, "-B", f"{DEV}/d10_make_symlists.py", f"{REFS}/D10_S1_ARCHIVE_INVENTORY.json", f"{OUT}/symlists"]
        rc, secs, _ = run_cmd("D7_symlists", cmd)
        new = sorted(os.listdir(f"{OUT}/symlists")) if os.path.isdir(f"{OUT}/symlists") else []
        ref = sorted(n for n in os.listdir(f"{EXP}/symlists") if n.endswith(".txt"))
        comps = [CMP.compare_bytes(f"{EXP}/symlists/{n}", f"{OUT}/symlists/{n}") | {"tag": n} for n in sorted(set(new) & set(ref))]
        bad = [c["tag"] for c in comps if c["verdict"] != "IDENTICAL"]
        sets = {"only_ref": sorted(set(ref) - set(new)), "only_new": sorted(set(new) - set(ref))}
        v = "IDENTICAL" if rc == 0 and not bad and not sets["only_ref"] and not sets["only_new"] else "DIFFERS"
        finish("D7_symlists", v, f"rc={rc} files={len(comps)} differing={bad[:6]} sets={sets}", comps + [{"kind": "set", **sets}], rc, secs, cmd)

    # D8 manifest gate self-test (only durable-exempt comments changed)
    if want('D8_manifest_gate_selftest'):
        cmd = [PYV, "-B", f"{DEV}/d10_manifest_gate.py", "--selftest", f"{EXP}/zips/2026-08", "2026-08"]
        rc, secs, out = run_cmd("D8_manifest_gate_selftest", cmd)
        green = any(l.startswith("SELFTEST GREEN") for l in out.splitlines())
        finish("D8_manifest_gate_selftest", "PASS" if rc == 0 and green else "FAIL", f"rc={rc} {secs}s last={out.strip().splitlines()[-1:]}", rc=rc, secs=secs, argv=cmd)

    # D1 ledger_ms (inputs hardwired in the device; OLD's sha is asserted by the device itself)
    if want('D1_ledger_ms'):
        identity_row("D1_ledger_ms", [PYV, "-B", f"{DEV}/d10_build_ledger_ms.py", "--out", f"{OUT}/ms"], None,
                     {"/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz": "bea6f5752772d54e"},
                     [lambda: cmp_npz(f"{EXP}/ms/ledger_full_ms.npz", f"{OUT}/ms/ledger_full_ms.npz", "npz"),
                      lambda: cmp_json(f"{REFS}/D10_LEDGER_MS_BUILD.json", f"{OUT}/ms/D10_LEDGER_MS_BUILD.json",
                                       ["self_sha256", "seconds", "new_ledger.path", "new_ledger.sha256"], ["argv", "python"], "receipt")],
                     gate=True)

    # D2a / D2b fund_state
    if want('D2a_fund_state_snap') or want('D2b_fund_state_d10'):
        common_in = {f"{EXP}/ms/ledger_full_ms.npz": "e179071d5955", "/dev/shm/nc_2026-09-23/work/axes.npz": "ec7723c4a4df",
                     "/dev/shm/nc_2026-09-23/devices_arm/nc_contract.py": "316a0b9bcf14"}
        base = [PYV, "-B", f"{DEV}/d10_build_fund_state.py", "--ledger-ms", f"{EXP}/ms/ledger_full_ms.npz",
                "--ledger-ms-sha", "e179071d595521987450f89e1774a95775a2593d76277a9c9dc6d86dcbc31a88", "--axes", "/dev/shm/nc_2026-09-23/work/axes.npz"]
        vol2 = ["self_sha256", "seconds", "output.path", "output.sha256"]
        identity_row("D2a_fund_state_snap", base + ["--mode", "snap", "--out", f"{OUT}/fund_state_snap.npz",
                                                    "--compare", "/dev/shm/nc_2026-09-23/work/fund_state.npz", "--compare-sha", "a12a8ed3"], EXP,
                     dict(common_in, **{"/dev/shm/nc_2026-09-23/work/fund_state.npz": "a12a8ed347ee"}),
                     [lambda: cmp_npz(f"{EXP}/lineD/stage2/fund_state_snap.npz", f"{OUT}/fund_state_snap.npz", "npz"),
                      lambda: cmp_json(f"{REFS}/fund_state_snap_RECEIPT.json", f"{OUT}/fund_state_snap_RECEIPT.json", vol2, ["argv", "python"], "receipt")])
        identity_row("D2b_fund_state_d10", base + ["--mode", "d10", "--out", f"{OUT}/fund_state_d10.npz"], EXP, common_in,
                     [lambda: cmp_npz(f"{EXP}/lineD/stage2/fund_state_d10.npz", f"{OUT}/fund_state_d10.npz", "npz"),
                      lambda: cmp_json(f"{REFS}/fund_state_d10_RECEIPT.json", f"{OUT}/fund_state_d10_RECEIPT.json", vol2, ["argv", "python"], "receipt")])

    # D3 assemble: argv verbatim from its receipt, only --out replaced; cwd = EXP (--rebuilt is relative)
    if D3_NOTRUN:
        finish("D3_assemble", "NOT_RUN", f"(quota) {D3_NOTRUN}")
    if want('D3_assemble') and not D3_NOTRUN:
        ref3 = "/workspace/d10_lineD_2026-09-26/stage2/NEWS_FEATURES_D10.npz"
        need = os.path.getsize(ref3) + (1 << 30)
        okp, wrote = write_probe(OUT, need)
        say(f"PROBE D3_assemble need={need} wrote={wrote} {'OK' if okp else 'FAILED'} (deleted)")
        RESULT.setdefault("probes", []).append({"row": "D3_assemble", "need_bytes": need, "wrote_bytes": wrote, "ok": okp, "utc": utc()}); save()
    if want('D3_assemble') and not D3_NOTRUN and not okp:
        finish("D3_assemble", "NOT_RUN", f"(quota) write probe of {need} bytes on {OUT} failed after {wrote} bytes")
    elif want('D3_assemble') and not D3_NOTRUN:
        ra = json.load(open(f"{REFS}/NEWS_FEATURES_D10_RECEIPT.json"))["argv"]
        assert ra[12] == "--out", ra
        argv3 = ra[:13] + [f"{OUT}/NEWS_FEATURES_D10.npz"]
        identity_row("D3_assemble", [PYV, "-B", f"{DEV}/d10_stage2_assemble.py"] + argv3, EXP,
                     {NF: "3c886a2bc0ff", f"{EXP}/ms/rebuilt_features_d10.npz": "2be2d7c89598"},
                     [lambda: cmp_npz("/workspace/d10_lineD_2026-09-26/stage2/NEWS_FEATURES_D10.npz", f"{OUT}/NEWS_FEATURES_D10.npz", "npz"),
                      lambda: cmp_json(f"{REFS}/NEWS_FEATURES_D10_RECEIPT.json", f"{OUT}/NEWS_FEATURES_D10_RECEIPT.json",
                                       ["device_sha256", "utc", "output.path", "output.sha256"], [], "receipt", argv_out=[13])],
                     gate=True)

    # D4 parity gate: identity against the two receipts of the immediate predecessor 521c6a28 (lead-acked reference, see header)
    if want('D4a_parity_snap_control') or want('D4b_parity_common_window') or want('D4pc_parity_positive_control'):
        cols = "fund_now:fn_v:fn_v:float64,fund_ema:fe_v:fe_v:float64,iv:iv_v:iv_v:float64"
        for tag, a_side, a_sha, ref in (("D4a_parity_snap_control", f"{EXP}/ms/rebuilt_features_snap.npz", "209c8f5338d3", "D10_PARITY_SNAP_CONTROL.json"),
                                        ("D4b_parity_common_window", f"{EXP}/ms/rebuilt_features_d10.npz", "2be2d7c89598", "D10_PARITY_COMMON_WINDOW.json")):
            identity_row(tag, [PYV, "-B", f"{DEV}/d10_parity_gate.py", "--a", a_side, "--b", NF, "--features", NF, "--columns", cols,
                               "--anchor-max-utc", "2026-09-01T02:00Z", "--out", f"{OUT}/{ref}"], None, {a_side: a_sha, NF: "3c886a2bc0ff"},
                         [lambda ref=ref: cmp_json(f"{REFS}/{ref}", f"{OUT}/{ref}", ["self_sha256"], ["argv", "python"], "receipt")])
        cmd = [PYV, "-B", f"{DEV}/d10_parity_gate.py", "--a", NF, "--b", NF, "--features", NF, "--columns", cols, "--positive-control",
               "--out", f"{OUT}/D10_PARITY_POSITIVE_CONTROL.json"]
        rc, secs, _ = run_cmd("D4pc_parity_positive_control", cmd)
        try:
            pc = json.load(open(f"{OUT}/D10_PARITY_POSITIVE_CONTROL.json"))
            ok = pc.get("verdict") == "POSITIVE_CONTROL_RUN_NOT_A_GATE" and pc.get("positive_control", {}).get("verdict") == "CONTROL_PASS"
            finish("D4pc_parity_positive_control", "PASS" if ok else "FAIL", f"rc={rc} {secs}s verdict={pc.get('verdict')} control={pc.get('positive_control', {}).get('verdict')}",
                   rc=rc, secs=secs, argv=cmd)
        except Exception as e:
            finish("D4pc_parity_positive_control", "ERROR", f"rc={rc} receipt unreadable: {type(e).__name__}: {e}", rc=rc, secs=secs, argv=cmd)

    # gate_sha256 exemption for D5/D6 is conditional on the AST proof (addendum 1 item 3); proof and ast shas go into the result
    if any(want(r) for r in ('D5a_p2_old_vs_archive', 'D5b_ledger_ms_vs_archive', 'D5c_legs_rn8_vs_archive', 'D6_live_ledger_vs_archive')):
        G = gate_ast_check(); RESULT["gate_sha256_ast_proof"] = G; save()
        say(f"GATE_AST_PROOF exempt={G['exempt']} ast_equal={G['ast_equal']} old_ast={G['old_ast_sha256'][:16]} new_ast={G['new_ast_sha256'][:16]}")
        gvol = ["gate_sha256"] if G["exempt"] else []

    # D5 re-audits: argv verbatim from each receipt, only --out replaced; cwd = EXP (as the re-audit driver ran)
    if any(want(r) for r in ('D5a_p2_old_vs_archive', 'D5b_ledger_ms_vs_archive', 'D5c_legs_rn8_vs_archive')):
        for tag, dev, ref, zin in (("D5a_p2_old_vs_archive", "d10_p2_ledger_vs_archive.py", "D10_P2_LEDGER_VS_ARCHIVE_JAN_AUG.json",
                                    {"/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz": "bea6f5752772"}),
                                   ("D5b_ledger_ms_vs_archive", "d10_p2_ledger_vs_archive.py", "D10_LEDGER_MS_VS_ARCHIVE_JAN_AUG.json",
                                    {f"{EXP}/ms/ledger_full_ms.npz": "e179071d5955"}),
                                   ("D5c_legs_rn8_vs_archive", "d10_legs_rn8_vs_archive.py", "D10_LEGS_RN8_VS_ARCHIVE_JAN_AUG.json",
                                    {"/dev/shm/news2_2026-09-23/work/legs.npz": "9ee5886f", NF: "3c886a2bc0ff"})):
            rv = json.load(open(f"{REFS}/{ref}"))["argv"]
            i = rv.index("--out") + 1
            argv = rv[:i] + [f"{OUT}/{ref}"] + rv[i + 1:]
            identity_row(tag, [PYV, "-B", f"{DEV}/{dev}"] + argv, EXP, zin,
                         [lambda ref=ref, i=i: cmp_json(f"{REFS}/{ref}", f"{OUT}/{ref}", ["self_sha256"] + gvol, [], "receipt", argv_out=[i])]
                         + ([lambda ref=ref: gate_values_check(f"{REFS}/{ref}", f"{OUT}/{ref}", G)] if G["exempt"] else []))

    # D6 live ledger vs archive: argv verbatim; an absent input is NOT_RUN, never substituted (lead decision 2)
    if want('D6_live_ledger_vs_archive'):
        ref = "D10_LIVE_LEDGER_VS_ARCHIVE_2026-08_RESIGNED.json"
        rv = json.load(open(f"{REFS}/{ref}"))["argv"]
        i = rv.index("--out") + 1
        argv = rv[:i] + [f"{OUT}/{ref}"] + rv[i + 1:]
        rj = json.load(open(f"{REFS}/{ref}"))
        live_in = {rv[rv.index("--live") + 1]: "", rv[rv.index("--mask") + 1]: "", rv[rv.index("--crypto-axis") + 1]: ""}
        ext_sha = (rj.get("live_ledger") or {}).get("extract_sha256") or (rj.get("live_ledger") or {}).get("sha256") or ""
        live_in[rv[rv.index("--live") + 1]] = ext_sha
        identity_row("D6_live_ledger_vs_archive", [PYV, "-B", f"{DEV}/d10_live_ledger_vs_archive.py"] + argv, EXP, live_in,
                     [lambda: cmp_json(f"{REFS}/{ref}", f"{OUT}/{ref}", ["self_sha256"] + gvol, [], "receipt", argv_out=[i])]
                     + ([lambda: gate_values_check(f"{REFS}/{ref}", f"{OUT}/{ref}", G)] if G["exempt"] else []))

    # D9 inventory, 3 names, real listing requests (public CDN): the three names' inventory entries must equal the reference
    if want('D9_inventory_3'):
        names = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        DW.write_bytes(f"{OUT}/syms3.txt", ("\n".join(names) + "\n").encode())
        inv_ref = json.load(open(f"{REFS}/D10_S1_ARCHIVE_INVENTORY.json"))
        led = inv_ref["argv"][inv_ref["argv"].index("--ledger") + 1]
        cmd = [PYV, "-B", f"{DEV}/d10_archive_inventory.py", "--symbols", f"{OUT}/syms3.txt", "--ledger", led,
               "--out", f"{OUT}/INVENTORY_3.json", "--progress", f"{OUT}/INVENTORY_3_progress.json"]
        rc, secs, _ = run_cmd("D9_inventory_3", cmd)
        try:
            new = json.load(open(f"{OUT}/INVENTORY_3.json"))["inventory"]
            diffs = {s: {"ref": inv_ref["inventory"].get(s), "new": new.get(s)} for s in names if inv_ref["inventory"].get(s) != new.get(s)}
            finish("D9_inventory_3", "IDENTICAL" if not diffs else "DIFFERS", f"rc={rc} {secs}s differing={sorted(diffs)}",
                   [{"kind": "inventory_subset", "diffs": diffs}], rc, secs, cmd)
        except Exception as e:
            finish("D9_inventory_3", "ERROR", f"rc={rc}: {type(e).__name__}: {e}", rc=rc, secs=secs, argv=cmd)

    # D10 real 3-name pull of 2026-08 through the new driver in its own EXP
    if want('D10_pull_3'):
        X = f"{W}/pullx"
        for d in ("devices", "common", "symlists", "zips", "logs"):
            os.makedirs(f"{X}/{d}", exist_ok=True)
        for n in ("p9_pull_monthly_funding_zips.py", "p9_pull_verdict.py", "d10_month_state.py", "d10_manifest_gate.py",
                  "d10_drop_mismatched.py", "d10_pull_months_pod2.sh"):
            shutil.copy(f"{DEV}/{n}", f"{X}/devices/{n}")
        shutil.copy(f"{W}/common/durable_write.py", f"{X}/common/durable_write.py")
        DW.write_bytes(f"{X}/symlists/2026-08.txt", ("\n".join(names) + "\n").encode())
        cmd = ["bash", f"{X}/devices/d10_pull_months_pod2.sh", "2026-08"]
        rc, secs, _ = run_cmd("D10_pull_3", cmd, env={"EXP": X, "PY": PYV})
        try:
            last = open(f"{X}/logs/pull_months_pod2.log").read().strip().splitlines()[-1]
            refm = json.load(open(f"{EXP}/zips/2026-08/MANIFEST_2026-08.json"))["files"]
            newm = json.load(open(f"{X}/zips/2026-08/MANIFEST_2026-08.json"))["files"]
            keys = ("status", "bytes", "sha256", "checksum_file_sha256_field", "checksum_match", "member", "rows", "iv_counts")
            comps = [CMP.compare_bytes(f"{EXP}/zips/2026-08/{s}-fundingRate-2026-08.zip", f"{X}/zips/2026-08/{s}-fundingRate-2026-08.zip") | {"tag": s}
                     for s in names]
            mdiff = {s: {k: [refm[s].get(k), newm.get(s, {}).get(k)] for k in keys if refm[s].get(k) != newm.get(s, {}).get(k)} for s in names}
            mdiff = {s: v for s, v in mdiff.items() if v}
            ok = rc == 0 and " COMPLETE all_verified=yes" in last and all(c["verdict"] == "IDENTICAL" for c in comps) and not mdiff
            finish("D10_pull_3", "IDENTICAL" if ok else "DIFFERS", f"rc={rc} {secs}s last='{last[-60:]}' zips={[c['verdict'] for c in comps]} manifest_diffs={mdiff}",
                   comps + [{"kind": "manifest_entries", "diffs": mdiff}], rc, secs, cmd)
        except Exception as e:
            finish("D10_pull_3", "ERROR", f"rc={rc}: {type(e).__name__}: {e}", rc=rc, secs=secs, argv=cmd)

    counts = {}
    for r in RESULT["rows"]:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    RESULT["final"] = f"DONE {counts}"; save()
    say(f"DRYRUN_DONE {json.dumps(counts)} not_run={[r['row'] for r in RESULT['rows'] if r['verdict'] == 'NOT_RUN']}")


def _cleanup_tmp():
    import shutil
    shutil.rmtree(TMPD, ignore_errors=True)


if __name__ == "__main__":
    import atexit
    atexit.register(_cleanup_tmp)
    try:
        main()
    except SystemExit:
        raise
    except BaseException as e:
        say(f"DRYRUN_STOP runner crashed: {type(e).__name__}: {e}")
        RESULT["final"] = f"STOP runner crashed {type(e).__name__}"
        try:
            save()
        except Exception:
            pass
        sys.exit(3)
