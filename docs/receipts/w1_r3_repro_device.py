"""R3-PRE: 用研究员的两组完整输入集, 在【修前】代码上复现 W1-N1/N2/N3。只读, 内存 sender。"""
import copy, importlib.util, json, math, os, sys, tempfile
os.environ["LIVE_ALARM_SUPPRESS"] = "1"
_T = tempfile.mkdtemp(prefix="w1r3pre_")
os.environ["LIVE_NOTIFY_AUDIT"] = os.path.join(_T, "a.jsonl")
SRC = sys.argv[1] if len(sys.argv) > 1 else "/Users/haosiyu/cc_tmp/exec_w1/ops/ic_monitor.py"
spec = importlib.util.spec_from_file_location("icm", SRC)
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
G, W = M.GRID_S, M.WINDOW_START_TS
NOW = W + 60 * G + M.MATURE_LAG_S + 60

def initial(r24sum, r48sum, first36):
    rows = []
    older = [i for i in range(8, 36) if i not in {18, 19, 20, 21}]
    assert len(older) == 24
    for i in range(60):
        if i in {18, 19, 20, 21}:
            continue
        value = .05 if i < 8 else (.1 if i == 8 else (r48sum - r24sum - .1) / 23) if i < 36 \
            else (first36 if i == 36 else (r24sum - first36) / 23)
        rows.append({"anchor_ts": W + i * G, "rank_ic": value})
    assert all(-1 <= r["rank_ic"] <= 1 for r in rows)
    return rows

a0 = initial(-1.08, -.72, -.6); a1 = a0 + [{"anchor_ts": W + 60 * G, "rank_ic": 0.}]
A = [("r24 DECIDE delivered", a0, NOW),
     ("new r48 DECIDE during same-level cooldown", a1, NOW + G),
     ("anchor 61 missing; r48 unavailable, r24 healthy", a1, NOW + 2 * G)]
b0 = initial(-.504, -.816, .1); b1 = b0 + [{"anchor_ts": W + 61 * G, "rank_ic": -.1}]
b2 = b1 + [{"anchor_ts": W + 62 * G, "rank_ic": -1.}]
B = [("r48 DECIDE delivered", b0, NOW),
     ("anchor 60 missing; r24 ALERT, r48 unavailable", b1, NOW + 2 * G),
     ("r24 now DECIDE; old DECIDE cooldown active", b2, NOW + 3 * G)]

def run(name, steps):
    sp = os.path.join(_T, name + ".json"); json.dump({}, open(sp, "w"))
    print("=" * 100); print(name)
    for label, rows, t in steps:
        v = M.check(rows, now=t)
        res = M.deliver(v, now=t, state_path=sp,
                        sender=lambda s, b: {"delivered_offbox": True, "status": "STUB"})
        st = json.load(open(sp))
        ev = st.get("event") or {}
        print(f"  {label}\n    level={v['level']} trigger={v.get('trigger')} judged_w={v.get('judged_windows')} "
              f"r24={v.get('r24')} r48={v.get('r48')} miss24={v['census']['r24']['missing']} "
              f"miss48={v['census']['r48']['missing']}\n    deliveries={[x['kind'] for x in res]} "
              f"event.level={ev.get('level')} event.tw={ev.get('trigger_windows')} open={ev.get('open')} "
              f"last_delivered_level={st.get('last_delivered_level')}")

run("new_trigger_lost", A)
run("downgrade_then_suppressed_upgrade", B)

# N3: NaN 账本
print("=" * 100); print("nan_ledger")
nan_rows = [{"anchor_ts": W + i * G, "rank_ic": float("nan")} for i in range(60)]
v = M.check(nan_rows, now=NOW)
print(f"  check: level={v['level']} judged={v['judged']} judged_w={v.get('judged_windows')} "
      f"r24={v.get('r24')} r48={v.get('r48')} n={v['n_post_deploy']} miss24={v['census']['r24']['missing']}")
sp = os.path.join(_T, "nan.json")
json.dump({"event": {"open": True, "level": "DECIDE", "trigger_windows": ["r48"],
                     "opened_at": NOW - 3 * 86400, "delivered": {"DECIDE": NOW - 3 * 86400}}}, open(sp, "w"))
res = M.deliver(v, now=NOW, state_path=sp, sender=lambda s, b: {"delivered_offbox": True, "status": "STUB"})
print(f"  deliveries={[x['kind'] for x in res]}  last_delivered_level={json.load(open(sp)).get('last_delivered_level')}")
