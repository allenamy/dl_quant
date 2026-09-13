"""E7 mutation controls: one property removed per mutant in a temp copy; named cells must go red with no traceback."""
import json, os, re, shutil, subprocess, sys, tempfile
SRC = "/Users/haosiyu/cc_tmp/fx_exec"
DS, FR = "ops/daily_summary.py", "ops/first_anchor_review.py"
T_DS, T_RTB = "live/tests_daily_summary.py", "live/tests_readers_three_bucket.py"
MUT = [
 ("M1_stale_row_fallback_back", DS, '    nav = [r for r in nav_all if float(r.get("nav_ts") or 0) >= since]\n',
  '    nav = [r for r in nav_all if float(r.get("nav_ts") or 0) >= since] or nav_all[-1:]\n', T_DS, ["E7-a1"]),
 ("M2_out_of_window_line_dropped", DS, "    if _nav_newest_outside is not None:\n", "    if False:\n", T_DS, ["E7-a2"]),
 ("M3_nan_weight_counted_known", FR, '                if _fin(o.get("target_w")) is not None:', '                if o.get("target_w") is not None:', T_RTB, ["E7-b2"]),
 ("M4_partial_sum_as_intent", FR, "        if anchors and mine and tg is not None and _tw_missing:", "        if False:", T_RTB, ["E7-b1"]),
]
res = []
for name, f, old, new, suite, expect in MUT:
    t = tempfile.mkdtemp(prefix="e7mut_")
    try:
        for d in ("ops", "scheduler", "signal", "config"):
            if os.path.isdir(os.path.join(SRC, d)): shutil.copytree(os.path.join(SRC, d), os.path.join(t, d))
        os.makedirs(os.path.join(t, "live")); os.makedirs(os.path.join(t, "state", "live", "pilot_log"))
        for fn in os.listdir(os.path.join(SRC, "live")):
            if fn.endswith(".py"): shutil.copy(os.path.join(SRC, "live", fn), os.path.join(t, "live", fn))
        p = os.path.join(t, f); s = open(p).read(); n = s.count(old)
        if n != 1:
            res.append((name, "TARGET_MATCH_%d" % n)); print(name, "TARGET_MATCH", n, flush=True); continue
        open(p, "w").write(s.replace(old, new, 1))
        r = subprocess.run(["/usr/bin/python3", os.path.join(t, suite)], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=900, cwd=os.path.join(t, "live"))
        fails = [m.group(1) for l in r.stdout.splitlines() for m in [re.match(r"^\s+FAIL\s+(?:★+ )?(\S+)", l)] if m]
        tb = "Traceback" in r.stdout + r.stderr
        ok = r.returncode != 0 and all(e in fails for e in expect) and not tb
        res.append((name, "KILLED" if ok else "SURVIVED"))
        print(name, "rc", r.returncode, "E7 fails", [x for x in fails if x.startswith("E7")], "expect", expect, "traceback", tb, "=>", "KILLED" if ok else "SURVIVED", flush=True)
        if tb: print((r.stdout + r.stderr)[-600:])
    finally:
        shutil.rmtree(t, ignore_errors=True)
print("SUMMARY", json.dumps({"n": len(res), "killed": sum(1 for x in res if x[1] == "KILLED"), "not_killed": [x[0] for x in res if x[1] != "KILLED"]}))
