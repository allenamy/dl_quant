"""最小测试(提案随附; 只读 ~/wide_shadow 文件, 不写; 运行: python3 test_shadow_tail_fix.py).
T1 纯函数 exit_out_of_universe: 只清数据宇宙外的名, 成员/宇宙内名逐位不动, 强制量 = 被清名 |w| 之和.
T2 纯函数 score_tail_positions: 注入假 fetch(5 根 1h bar + 1 次结算) ⇒ 盈亏/资金费按定义; bar 不全 ⇒ 记未知不记 0.
T3 存档权重(最新 weights/*.npz)上的机制事实: 数据宇宙外名数 296 / gross ≈ 0.2502 / 最大 |w| ≤ 带冻结上界 2.5e-3(+1e-6).
T4 两份 diff 对运行中的 ~/wide_shadow/shadow_loop.py 干跑可应用(patch --dry-run), 且其 SHA = 提案所对 445a9870….
"""
import os, sys, json, glob, hashlib, subprocess, importlib.util, numpy as np
D = os.path.dirname(os.path.abspath(__file__)); SHD = os.path.expanduser("~/wide_shadow")
def load(name):
    spec = importlib.util.spec_from_file_location(name, f"{D}/{name}.py"); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
fails = []
def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg); (None if cond else fails.append(msg))

# T1
B = load("shadow_loop_b_exit_on_leave")
sm = np.array([0.01, -0.002, 0.0, 0.0015, -0.03]); H = sm.copy(); keep = np.array([True, False, True, False, True])
sm2, forced, n = B.exit_out_of_universe(sm, H, keep)
check(np.array_equal(sm2, np.array([0.01, 0.0, 0.0, 0.0, -0.03])), "T1 exit_out_of_universe zeroes only non-kept names")
check(abs(forced - 0.0035) < 1e-12 and n == 2, f"T1 forced abs sum 0.0035 / n 2 (got {forced}, {n})")
check(B.EXIT_ON_LEAVE is True and B.EXIT_NON_MEMBERS is False and B.FORCED_EXIT_COST_BPS == 4.7, "T1 defaults: EXIT_ON_LEAVE on, EXIT_NON_MEMBERS off, forced cost 4.7")

# T2
A = load("shadow_loop_a_tail_scoring")
T = 1787356800
def fake_fetch(path, params, weight):
    if path.endswith("klines"):
        if params["symbol"] == "BADUSDT": return [[(T - 3600) * 1000, 0, 0, 0, "1.0"]]          # 只有 1 根 bar ⇒ 未知
        bars = []
        for k in range(5):
            ot = (T - 3600 + k * 3600) * 1000; close = "100.0" if k == 0 else ("110.0" if k == 4 else "105.0")
            bars.append([ot, "0", "0", "0", close])
        return bars
    if path.endswith("fundingRate"):
        return [{"fundingTime": (T + 4 * 3600) * 1000, "fundingRate": "0.0001"}, {"fundingTime": T * 1000, "fundingRate": "0.9"}]   # 后者在窗外(=T)不计
    return {"_err": "x"}
syms = ["GOODUSDT", "BADUSDT"]
r = A.score_tail_positions(None, syms, {0: 0.002, 1: -0.001}, T, fetch=fake_fetch)
check(abs(r["tail_gross_bps"] - 0.002 * 0.10 * 1e4) < 1e-9, f"T2 tail gross = w*(110/100-1)*1e4 = 2.0 bps (got {r['tail_gross_bps']})")
check(abs(r["tail_carry_bps"] - 0.002 * 1e-4 * 1e4) < 1e-9, f"T2 tail carry = w*rate*1e4 = 0.002 bps, 窗外结算不计 (got {r['tail_carry_bps']})")
check(r["tail_n"] == 1 and abs(r["tail_unknown_gross"] - 0.001) < 1e-12, f"T2 bad symbol counted unknown not zero (n={r['tail_n']}, unknown={r['tail_unknown_gross']})")

# T3
cfg = json.load(open(f"{SHD}/shadow_bundle/config.json")); psy = cfg["symbols_panel"]; live = set(cfg["symbols_live"])
wf = sorted(glob.glob(f"{SHD}/state/weights/*.npz"))
if wf:
    z = np.load(wf[-1]); out = [(psy[int(j)], float(v)) for j, v in zip(z["idx"], z["val"]) if psy[int(j)] not in live]
    g = sum(abs(v) for _, v in out); mx = max(abs(v) for _, v in out) if out else 0.0
    check(len(out) >= 250 and abs(g - 0.2502) < 0.01, f"T3 latest weights {os.path.basename(wf[-1])}: out-of-universe names {len(out)} gross {g:.4f} (expected ~296 / 0.2502)")
    check(mx <= 2.5e-3 + 1e-6, f"T3 max |w| of frozen tails {mx:.6f} ≤ band-freeze bound 2.5e-3 (mechanism: |0.1·H|<2.5e-4 ⇒ frozen)")
    live_mask = np.zeros(len(psy), bool); live_mask[[psy.index(s) for s in live]] = True
    full = np.zeros(len(psy)); full[z["idx"]] = z["val"]
    sm2, forced, n = B.exit_out_of_universe(full, full, live_mask)
    check(n == len(out) and abs(forced - g) < 1e-9 and np.array_equal(sm2[live_mask], full[live_mask]), "T3 applying (b) to archived weights zeroes exactly the out-of-universe names and leaves in-universe weights bitwise unchanged")
else:
    check(False, "T3 no archived weights found")

# T4
sha = hashlib.sha256(open(f"{SHD}/shadow_loop.py", "rb").read()).hexdigest()
check(sha.startswith("445a9870"), f"T4 running shadow_loop.py sha {sha[:12]} == proposal target 445a9870")
for nm in ("a_tail_scoring.diff", "b_exit_on_leave.diff"):
    p = subprocess.run(["patch", "--dry-run", "-p1", "-i", f"{D}/{nm}", f"{SHD}/shadow_loop.py"], capture_output=True, text=True)
    check(p.returncode == 0, f"T4 {nm} applies cleanly (dry-run) -> {p.stdout.strip().splitlines()[-1] if p.stdout else p.stderr.strip()[:80]}")
# variants must still compile
for nm in ("shadow_loop_a_tail_scoring", "shadow_loop_b_exit_on_leave"):
    p = subprocess.run([sys.executable, "-m", "py_compile", f"{D}/{nm}.py"], capture_output=True, text=True); check(p.returncode == 0, f"T4 {nm}.py compiles")
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL")
sys.exit(1 if fails else 0)
