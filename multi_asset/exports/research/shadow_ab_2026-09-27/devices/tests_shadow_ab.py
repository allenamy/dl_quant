"""Known-answer and red tests for the shadow A/B devices (no live file is read or written; everything is synthetic in a temp dir).
usage: python tests_shadow_ab.py   -> prints SHADOW_AB_TESTS passed/total, exit 0 iff all pass"""
import os, sys, json, tempfile, subprocess, hashlib, importlib.util
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("pnl", os.path.join(HERE, "shadow_ab_pnl.py")); P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
R = []
def check(name, ok): R.append((name, bool(ok))); print(("PASS " if ok else "FAIL ") + name)

# 1. price: 48 rows of +0.001 -> compounded 1.001^48-1, summed 0.048; a name with 3 NaN rows (45 finite) is UNPRICED
rr = np.full((48, 3), 0.001, np.float32); rr[:3, 2] = np.nan
c, s, ok = P.price_returns(rr)
r32 = float(np.float32(0.001))   # the channel is float32: the expectation must use the float32 value (first run: my expectation used 0.001 and went red)
check("price compounded known answer", abs(c[0] - ((1 + r32) ** 48 - 1)) < 1e-12 and abs(s[0] - 48 * r32) < 1e-12)
check("price 45 finite rows -> unpriced (never 0)", (not ok[2]) and np.isnan(c[2]))
rr2 = rr.copy(); rr2[:2, 1] = np.nan; c2, s2, ok2 = P.price_returns(rr2)
check("price 46 finite rows -> priced over finite rows", ok2[1] and abs(c2[1] - ((1 + r32) ** 46 - 1)) < 1e-12)
# 2. funding window (A, N]: settlement exactly at A excluded, at N included; absent -> UNKNOWN_ABSENT; tail starting after A -> coverage flag
A, N = 1000 * 14400, 1000 * 14400 + 14400
lt = {"X": [[A - 3600, 0.01, 1.0], [A, 0.02, 1.0], [A + 3600, 0.03, 1.0], [N, 0.04, 1.0]], "Y": [[A + 7200, 0.05, 4.0]]}
tot, st = P.funding_rates(lt, ["X", "Y", "Z"], A, N)
check("funding window (A, N]", abs(tot[0] - 0.07) < 1e-12 and st[0] == "OK")
check("funding coverage flag / absent flag", st[1] == "UNKNOWN_COVERAGE" and st[2] == "UNKNOWN_ABSENT")
# 3. arm metrics: long X short Y, known returns, funding, cost
w = np.array([1.0, -1.0, 0.0]); wp = np.array([0.5, -1.5, 0.0])
m = P.arm_metrics(w, wp, np.array([0.01, 0.02, np.nan]), np.array([0.01, 0.02, np.nan]), np.array([True, True, False]),
                  np.array([0.001, -0.002, 0.0]), np.array(["OK", "OK", "UNKNOWN_ABSENT"], dtype=object))
check("arm price known answer", abs(m["price"] - (0.01 - 0.02)) < 1e-12)
check("arm funding sign (long pays positive, short receives negative rate -> pays)", abs(m["funding"] - (-(0.001) - (0.002))) < 1e-12)
check("arm cost = kappa * sum|dw|", abs(m["cost"] - 3.52e-4 * 1.0) < 1e-15 and abs(m["net"] - (m["price"] + m["funding"] - m["cost"])) < 1e-15)
check("unheld unknown names do not count", m["unpriced_abs_w"] == 0.0 and m["funding_unknown_abs_w"] == 0.0)
m2 = P.arm_metrics(w, None, np.array([0.01, 0.02, 0]), np.array([0.01, 0.02, 0]), np.array([True, True, True]), np.zeros(3), np.array(["OK"] * 3, dtype=object))
check("no previous book -> cost and net unknown (None), not 0", m2["cost"] is None and m2["net"] is None)
# 4. book scaling to constant leverage 2.0
z = {"idx": np.array([0, 1]), "val": np.array([0.3, -0.1])}; b = P.book_nav(z, 3)
check("book scaled to gross 2.0", abs(np.abs(b).sum() - 2.0) < 1e-12 and abs(b[0] / b[1] + 3.0) < 1e-12)
# 5. ledger verifier: good chain passes, tampered line and non-increasing anchor are red
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "l.jsonl"); prev = None; lines = []
    for a in (1, 2, 3):
        d = json.dumps({"anchor": a, "prev_line_sha256": prev}, sort_keys=True); lines.append(d); prev = hashlib.sha256(d.encode()).hexdigest()
    open(p, "w").write("\n".join(lines) + "\n")
    V = [sys.executable, "-B", os.path.join(HERE, "shadow_ab_verify_ledger.py"), p]
    check("ledger good chain", subprocess.run(V, capture_output=True).returncode == 0)
    open(p, "w").write("\n".join([lines[0], lines[1].replace('"anchor": 2', '"anchor": 9'), lines[2]]) + "\n")
    check("ledger tampered line -> BROKEN", subprocess.run(V, capture_output=True).returncode == 5)
# 6. hook insertion: unique line + names -> OK; missing line / missing name -> refuse
stage_ok = "\n".join(["legz=zf=w3m=rn8_m=FTRIM_HI=H_kc_prev=H_fc_prev=combo=kc_src=fc_src=syms=NW=A=H=0",
                      "def chain(z): return z", "def exec_reshape(w): return w", "H = 1; sm_kc = chain(1)", "sm_fc = chain(2)",
                      'log(f"④ COMBO 落盘 x")', "rest = 1"])
with tempfile.TemporaryDirectory() as t:
    for name, src, want in (("hook ok", stage_ok, 0), ("hook no insertion line -> refuse", stage_ok.replace("④", "4"), 3),
                            ("hook missing sm_fc -> refuse", stage_ok.replace("sm_fc = chain(2)", "x = 2"), 3)):
        sp = os.path.join(t, "s.py"); open(sp, "w").write(src)
        r = subprocess.run([sys.executable, "-B", os.path.join(HERE, "shadow_ab_insert_hook.py"), sp, os.path.join(HERE, "ab_hook_block.py"), os.path.join(t, "h.json")], capture_output=True)
        check(name, r.returncode == want)
# 7. collect identity: equal -> 0; one weight off by 1e-8 -> 2 (VOID), arms still stored for forensics
with tempfile.TemporaryDirectory() as t:
    sb = os.path.join(t, "sb"); out = os.path.join(sb, "ab_out"); os.makedirs(out); open(os.path.join(sb, "ISOLATION_OK"), "w").write("x")
    names = ["AUSDT", "BUSDT", "CUSDT"]; json.dump({"anchor": 14400 * 5, "w3m": [0.4, 0.0, 0.6], "names": names, "arms": {"LIVE_REPLAY": {}}}, open(os.path.join(out, "AB_META.json"), "w"))
    np.savez(os.path.join(out, "LIVE_REPLAY_combo.npz"), anchor=14400 * 5, idx=np.array([0, 2]), val=np.array([0.12345678, -0.12345678]))
    live = os.path.join(t, "live.json")
    for name, wts, want in (("collect identity equal -> 0", {"AUSDT": 0.12345678, "CUSDT": -0.12345678}, 0),
                            ("collect identity off by 1e-8 -> VOID (2)", {"AUSDT": 0.12345679, "CUSDT": -0.12345678}, 2)):
        json.dump({"anchor_ts": 14400 * 5, "weights": wts, "w3_masked": [0.4, 0.0, 0.6]}, open(live, "w"))
        home = os.path.join(t, "home_" + str(want))
        r = subprocess.run([sys.executable, "-B", os.path.join(HERE, "shadow_ab_collect.py"), str(14400 * 5), live, sb, "0", home, os.path.join(t, "rc.json")], capture_output=True)
        check(name, r.returncode == want and os.path.exists(os.path.join(home, "state", str(14400 * 5), "COLLECT.json")))
n_ok = sum(ok for _, ok in R)
print(f"SHADOW_AB_TESTS {n_ok}/{len(R)}")
sys.exit(0 if n_ok == len(R) else 1)
