"""ALM-03 mutation controls: each mutant removes ONE property (consumer, #9, or step-9 wiring) in a temp copy of the tree; the suite
must go red on the named cells, without a traceback. Refuses a mutant whose target text does not match exactly once."""
import json, os, re, shutil, subprocess, sys, tempfile
SRC = "/Users/haosiyu/cc_tmp/fx_exec"
R, A, S = "ops/check_rank_monitor_input.py", "ops/assert_anchor_artifacts.py", "scheduler/run_anchor.py"
MUT = [
 ("M1_grace_reset_per_run", R, 'GRACE_UNTIL_TS = calendar.timegm(time.strptime(W1_EVALS_LIVE_UTC, "%Y-%m-%dT%H:%M:%SZ")) + LEDGER_GRACE_H * 3600',
  'GRACE_UNTIL_TS = time.time() + LEDGER_GRACE_H * 3600', ["A5"]),
 ("M2_nine_passes_any_absence", A, '        add(_rm_name, _rm["ok"] or _rm["known_gap"],', '        add(_rm_name, _rm["ok"] or _rm["state"].startswith("LEDGER_ABSENT"),', ["A1"]),
 ("M3_repages_levels", R, '        return done("JUDGED")', '        return done("JUDGED") if level == "OK" else done("EVAL_STALE", f"LEVEL {level}")', ["A6"]),
 ("M4_page_key_carries_age", R, '''f"EVAL_STALE: #55's last evaluation is {iso(eval_at)}, older than {MAX_EVAL_AGE_H} h — the "''',
  '''f"EVAL_STALE: #55's last evaluation is {(now - eval_at) / 3600.0:.1f} h old, older than {MAX_EVAL_AGE_H} h — the "''', ["A4"]),
 ("M5_not_judged_without_windows_accepted", R, '    if judged is False and level == "INCOMPLETE" and cz and isinstance(inc, list) and inc \\',
  '    if judged is False and level == "INCOMPLETE" and cz and isinstance(inc, list) \\', ["A7b"]),
 ("M6_stale_check_removed", R, '    if (now - eval_at) / 3600.0 > MAX_EVAL_AGE_H:', '    if False:', ["A4"]),
 ("M7_unreadable_falls_back", R, '        rec = json.loads(lines[-1])\n    except ValueError as e:\n        return None, f"its last row is not JSON ({e})"',
  '        rec = json.loads(lines[-1])\n    except ValueError as e:\n        rec = json.loads(lines[-2])', ["A8"]),
 ("M8_lag_check_removed", R, '        if lag is None or lag > MAX_LAG_ANCHORS:', '        if False:', ["A10"]),
 ("M9_unstamped_ignored", R, '    if level == "UNSTAMPED":', '    if False:', ["A9"]),
 ("M10_step9_back_to_factor_health", S, '        import check_rank_monitor_input as RMI\n        RMI.run(notifier=notifier, log=log)',
  '        import check_factor_health as RMI\n        RMI.run(notifier=notifier, log=log)', ["A2", "A12", "S3"]),
 ("M11_nine_reads_ok_only_for_judged", A, '        add(_rm_name, _rm["ok"] or _rm["known_gap"],', '        add(_rm_name, _rm["state"] == "JUDGED",', ["A2", "A5"]),
]
only = sys.argv[1:]; res = []
for name, f, old, new, expect in MUT:
    if only and name not in only: continue
    t = tempfile.mkdtemp(prefix="alm03mut_")
    try:
        for d in ("ops", "scheduler", "config", "signal"):
            if os.path.isdir(os.path.join(SRC, d)): shutil.copytree(os.path.join(SRC, d), os.path.join(t, d))
        os.makedirs(os.path.join(t, "live", "tests_fixtures"))
        for fn in os.listdir(os.path.join(SRC, "live")):
            if fn.endswith(".py"): shutil.copy(os.path.join(SRC, "live", fn), os.path.join(t, "live", fn))
        shutil.copytree(os.path.join(SRC, "live", "tests_fixtures", "alm03_rank_monitor"), os.path.join(t, "live", "tests_fixtures", "alm03_rank_monitor"))
        p = os.path.join(t, f); s = open(p).read(); n = s.count(old)
        if n != 1:
            res.append((name, "TARGET_MATCH_%d" % n)); print(name, "TARGET_MATCH", n, flush=True); continue
        open(p, "w").write(s.replace(old, new, 1))
        r = subprocess.run(["/usr/bin/python3", os.path.join(t, "live", "tests_rank_monitor_input.py")], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=600, cwd=os.path.join(t, "live"))
        fails = [m.group(1) for l in r.stdout.splitlines() for m in [re.match(r"^  FAIL  (?:★+ )?(\S+)", l)] if m]
        tb = "Traceback" in r.stdout + r.stderr
        ok = r.returncode != 0 and all(e in fails for e in expect) and not tb
        res.append((name, "KILLED" if ok else "SURVIVED"))
        print(name, "rc", r.returncode, "fails", fails, "expect", expect, "traceback", tb, "=>", "KILLED" if ok else "SURVIVED", flush=True)
        if tb: print((r.stdout + r.stderr)[-800:])
    finally:
        shutil.rmtree(t, ignore_errors=True)
print("SUMMARY", json.dumps({"n": len(res), "killed": sum(1 for x in res if x[1] == "KILLED"), "not_killed": [x[0] for x in res if x[1] != "KILLED"]}))
