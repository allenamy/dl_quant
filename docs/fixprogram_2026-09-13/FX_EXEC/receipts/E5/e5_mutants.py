"""E5 mutation controls: one property removed per mutant, in a temp copy (live/ ops/ scheduler/ signal/ config/ + the e0912a_12z
fixture); the named cells must go red with no traceback. Refuses a mutant whose target does not match exactly once."""
import json, os, re, shutil, subprocess, sys, tempfile
SRC = "/Users/haosiyu/cc_tmp/fx_exec"
RC, RJ, DM = "live/reconcile.py", "ops/rejudge_ledger_rows.py", "live/tests_disposition_matrix.py"
T_ROC, T_DM = "live/tests_reduce_only_clamp.py", "live/tests_disposition_matrix.py"
MUT = [
 ("M1_several_pairs_accepted", RC, "    if pairs is None or len(pairs) != 1:", "    if not pairs:", T_ROC, ["E5-5"]),
 ("M2_whole_string_first_pair", RC, "        ms = _ORIGQTY_PAIR.findall(p)\n        if len(ms) != 1:\n            return None",
  "        ms = _ORIGQTY_PAIR.findall(str(why))[:1]\n        if len(ms) != 1:\n            return None", T_ROC, ["E5-4"]),
 ("M3_row_equality_dropped", RC, "        if cid in known and str(why) == known_why.get(cid):", "        if cid in known:", T_ROC, ["E5-6"]),
 ("M4_row_kind_test_back", RC, "        if cid in known and str(why) == known_why.get(cid):",
  "        if _is_identity_origqty_kind(why) and cid in known and str(why) == known_why.get(cid):", T_ROC, ["E5-7"]),
 ("M5_rejudge_first_pair", RJ, '            _one_pair = len(_pairs) == 1 and None not in _pairs[0]', '            _one_pair = bool(_pairs) and None not in _pairs[0]', T_ROC, ["E5-9"]),
 ("M6_ruler_several_reasons", DM, "    if len(_pairs) != 1 or len(_pairs[0]) != 1:", "    if len(_pairs[0]) != 1:", T_DM, ["E5-R1"]),
 ("M7_ruler_row_equality_dropped", DM, "        if not (cid in cids and str(why) == _whys.get(cid)):", "        if not (cid in cids):", T_DM, ["E5-R3"]),
 ("M8_ruler_row_kind_back", DM, "        if not (cid in cids and str(why) == _whys.get(cid)):", "        if not (_is_origqty_kind(why) and cid in cids and str(why) == _whys.get(cid)):", T_DM, ["E5-R3b"]),
]
only = sys.argv[1:]; res = []
for name, f, old, new, suite, expect in MUT:
    if only and name not in only: continue
    t = tempfile.mkdtemp(prefix="e5mut_")
    try:
        for d in ("ops", "scheduler", "signal", "config"):
            if os.path.isdir(os.path.join(SRC, d)): shutil.copytree(os.path.join(SRC, d), os.path.join(t, d))
        os.makedirs(os.path.join(t, "live", "tests_fixtures")); os.makedirs(os.path.join(t, "state", "live"))
        for fn in os.listdir(os.path.join(SRC, "live")):
            if fn.endswith(".py"): shutil.copy(os.path.join(SRC, "live", fn), os.path.join(t, "live", fn))
        shutil.copytree(os.path.join(SRC, "live", "tests_fixtures", "e0912a_12z"), os.path.join(t, "live", "tests_fixtures", "e0912a_12z"))
        if suite == T_DM:   # the ruler suite reads the REAL ledger: copy ONLY the subtrees it reads (pilot_log orders/anchors + watchdog events)
            src_st = "/Users/haosiyu/cc_tmp/fx_exec_ledger/state/live"
            for d in sorted(os.listdir(os.path.join(src_st, "pilot_log"))):
                for fn in ("orders.jsonl", "anchors.jsonl"):
                    sp = os.path.join(src_st, "pilot_log", d, fn)
                    if os.path.exists(sp):
                        os.makedirs(os.path.join(t, "state", "live", "pilot_log", d), exist_ok=True); shutil.copy(sp, os.path.join(t, "state", "live", "pilot_log", d, fn))
            os.makedirs(os.path.join(t, "state", "live", "watchdog"), exist_ok=True)
            shutil.copy(os.path.join(src_st, "watchdog", "events.jsonl"), os.path.join(t, "state", "live", "watchdog", "events.jsonl"))
        p = os.path.join(t, f); s = open(p).read(); n = s.count(old)
        if n != 1:
            res.append((name, "TARGET_MATCH_%d" % n)); print(name, "TARGET_MATCH", n, flush=True); continue
        open(p, "w").write(s.replace(old, new, 1))
        r = subprocess.run(["/usr/bin/python3", os.path.join(t, suite)], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=900, cwd=os.path.dirname(os.path.join(t, suite)))
        fails = [m.group(1) for l in r.stdout.splitlines() for m in [re.match(r"^  FAIL\s+(?:★+ )?(\S+)", l)] if m]
        tb = "Traceback" in r.stdout + r.stderr
        ok = r.returncode != 0 and all(e in fails for e in expect) and not tb
        res.append((name, "KILLED" if ok else "SURVIVED"))
        print(name, "rc", r.returncode, "E5 fails", [x for x in fails if x.startswith("E5")], "expect", expect, "traceback", tb, "=>", "KILLED" if ok else "SURVIVED", flush=True)
        if tb: print((r.stdout + r.stderr)[-600:])
    finally:
        shutil.rmtree(t, ignore_errors=True)
print("SUMMARY", json.dumps({"n": len(res), "killed": sum(1 for x in res if x[1] == "KILLED"), "not_killed": [x[0] for x in res if x[1] != "KILLED"]}))
