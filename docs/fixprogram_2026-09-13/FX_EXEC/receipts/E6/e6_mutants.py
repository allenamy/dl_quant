"""E6 mutation controls (one property removed per mutant, temp copy of the tree + the three fixtures tests_per_name_stop reads)."""
import json, os, re, shutil, subprocess, sys, tempfile
SRC = "/Users/haosiyu/cc_tmp/fx_exec"
A, BE, PN = "scheduler/anchor_loop.py", "live/binance_executor.py", "live/per_name_stop.py"
MUT = [
 ("M1_unknown_source_defaults_to_venue", A, '        parts.append(f"来源未记录: {unknown[:8]}")', '        parts.append(f"场所 maxNotionalValue=0(不许开新仓): {unknown[:8]}")', ["E6-A2"]),
 ("M2_held_exit_source_not_recorded", A, '            self._untradable_sources["external_held_exit"] = set(self._ext_held_exit)\n', "", ["E6-A4"]),
 ("M3_stop_source_not_recorded", A, '                    self._untradable_sources["per_name_stop"] = set(self._pns_sets["stop"])\n', "", ["E6-A3"]),
 ("M4_zero_cap_names_empty", A, '                "withheld_zero_cap_names": sorted((set(pred_symbols) - set(_status_withheld)) & blocked),',
  '                "withheld_zero_cap_names": [],', ["E6-A5"]),
 ("M5_residual_text_old_attribution", A, '''            self.alarm("HIGH", reshape_residual_alarm_text(_rs, self.gross))''',
  '''            self.alarm("HIGH", f"撤名残差 {_rs['net_before']:+.2f} USDT, 由 {_rs['n_popped']} 个撤下的名字造成")''', ["E6-C3"]),
 ("M6_producer_net_after_pop", A, "    _net_composed = float(sum(float(v or 0.0) for v in target.values()))\n",
  "    _net_composed = None\n", ["E6-C1"], ("    clamp[\"popped\"] = withhold_pop(target, held, untradable)\n",
  "    clamp[\"popped\"] = withhold_pop(target, held, untradable)\n    _net_composed = float(sum(float(v or 0.0) for v in target.values()))\n")),
 ("M7_policy_text_back_to_E4", BE, 'STOP_EXIT_POLICY = (f"a stopped name exits reduce-only, maker first;',
  'STOP_EXIT_POLICY = ("stopped names exit maker-only, never chased — " f"a stopped name exits reduce-only, maker first;', ["E6-B1"]),
 ("M8_trigger_text_back", PN, 'f"≤ {depth_pct:.0%} ⇒ flatten_only(先挂 reduce-only maker; 被场所拒绝的 maker 转市价 reduce-only, "',
  'f"≤ {depth_pct:.0%} ⇒ flatten_only(maker 出场, 不追)(先挂 reduce-only maker; 被场所拒绝的 maker 转市价 reduce-only, "', ["E6-B1"]),
 ("M9_carried_alarm_spread_literal", A, "受 {_BEXs.MAX_CROSS_BPS:g} bps 点差门", "受 30 bps 点差门", ["E6-B1"]),
]
res = []
for entry in MUT:
    name, f, old, new, expect = entry[:5]; extra = entry[5] if len(entry) > 5 else None
    if sys.argv[1:] and name not in sys.argv[1:]: continue
    t = tempfile.mkdtemp(prefix="e6mut_")
    try:
        for d in ("ops", "scheduler", "signal", "config"):
            if os.path.isdir(os.path.join(SRC, d)): shutil.copytree(os.path.join(SRC, d), os.path.join(t, d))
        os.makedirs(os.path.join(t, "live", "tests_fixtures")); os.makedirs(os.path.join(t, "state", "live"))
        for fn in os.listdir(os.path.join(SRC, "live")):
            if fn.endswith(".py"): shutil.copy(os.path.join(SRC, "live", fn), os.path.join(t, "live", fn))
        for fx in ("e4_stop_exit", "w9_stopped_long", "e6_withheld_sources"):
            shutil.copytree(os.path.join(SRC, "live", "tests_fixtures", fx), os.path.join(t, "live", "tests_fixtures", fx))
        p = os.path.join(t, f); s = open(p).read(); n = s.count(old)
        if n != 1:
            res.append((name, "TARGET_MATCH_%d" % n)); print(name, "TARGET_MATCH", n, flush=True); continue
        s = s.replace(old, new, 1)
        if extra:
            assert s.count(extra[0]) == 1, extra[0]
            s = s.replace(extra[0], extra[1], 1)
        open(p, "w").write(s)
        r = subprocess.run(["/usr/bin/python3", os.path.join(t, "live", "tests_per_name_stop.py")], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=900, cwd=os.path.join(t, "live"))
        fails = [m.group(1) for l in r.stdout.splitlines() for m in [re.match(r"^FAIL (?:★+ )?(\S+)", l)] if m]
        tb = "Traceback" in r.stdout + r.stderr
        ok = r.returncode != 0 and all(e in fails for e in expect) and not tb
        res.append((name, "KILLED" if ok else "SURVIVED"))
        print(name, "rc", r.returncode, "fails", fails, "expect", expect, "traceback", tb, "=>", "KILLED" if ok else "SURVIVED", flush=True)
        if tb: print((r.stdout + r.stderr)[-600:])
    finally:
        shutil.rmtree(t, ignore_errors=True)
print("SUMMARY", json.dumps({"n": len(res), "killed": sum(1 for x in res if x[1] == "KILLED"), "not_killed": [x[0] for x in res if x[1] != "KILLED"]}))
