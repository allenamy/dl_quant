"""恢复门 × 划转日 隔离复现装置(2026-09-06; PREREG_watchdog_cond2_resume_semantics §8.2)

结论与装置同寿命(项目纪律): 本脚本产出的两臂读数就是 §8.2 表格里的两行。

问: cond2 判据改为「最近一个已定价日」后, 若次日(09-07)发生资金划转 —— 该日按
    external_flow≠0 记为 UNKNOWN —— `recent` 是否回退到 09-06 的 −4.27% 并再次触发?
答: 是。A 臂(无划转) RESUMABLE / recent=20260907 0.0%;
    B 臂(+50,000 入金) NOT RESUMABLE / recent=20260906 −4.2713%。

只读: 把 pilot_log 复制到临时目录再判, 逐字照抄 ops/resume_from_trip.sh 步骤 1/4 的
      WI.collect + WD.run(MockBroker, 临时 state_dir)。生产树不被写。

跑法: /usr/bin/python3 multi_asset/exports/live/pilot_journal/tools/resume_gate_flowday_probe.py
"""
import json, os, shutil, sys, tempfile
REPO = "/Users/haosiyu/dl_quant_live"
sys.path.insert(0, os.path.join(REPO, "live"))
os.chdir(REPO)
import watchdog as WD, watchdog_inputs as WI

SRC = os.path.join(REPO, "state/live/pilot_log")

def build(flow):
    tree = tempfile.mkdtemp(prefix="flowprobe_"); shutil.rmtree(tree)
    shutil.copytree(SRC, tree)
    last = [json.loads(l) for l in open(os.path.join(SRC, "20260906/daily_nav.jsonl")) if l.strip()][-1]
    nav = float(last["nav"]) + (flow or 0.0)          # deposit lands in the wallet
    row = dict(last)
    row.update({"day": "20260907", "nav": nav, "wallet_balance": nav, "margin_balance": nav,
                "realised_pnl": 0.0, "unrealised_pnl": 0.0,
                "realised_by_type": {"FUNDING_FEE": 0.0, "COMMISSION": 0.0, "REALIZED_PNL": 0.0},
                "realised_truncated": False,
                "prev_day": "20260906", "prev_nav": float(last["nav"]),
                "equity_delta_since_prev": nav - float(last["nav"]),
                "external_flow_usdt": float(flow), "nav_ts": float(last["nav_ts"]) + 86400.0})
    d = os.path.join(tree, "20260907"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "daily_nav.jsonl"), "w") as f:
        f.write(json.dumps(row) + "\n")
    return tree

for label, flow in [("A  09-07 flat, NO transfer   ", 0.0),
                    ("B  09-07 flat, +50,000 deposit", 50000.0)]:
    tree = build(flow)
    ops, ve, _ = WI.collect(tree)
    ev, _, _ = WD.run(tree, broker=WD.MockBroker(), venue_events=ve, ops_stats=ops,
                      verbose=False, state_dir=tempfile.mkdtemp())
    c2 = {}
    for _k in ("detail", "details", "conditions"):
        _d = ev.get(_k) or {}
        if isinstance(_d, dict) and "cond2_day_loss" in _d:
            c2 = _d["cond2_day_loss"]; break
    blind = ev.get("conditions_blind") or []
    print(f"{label} -> tripped={str(ev.get('tripped')):5} blind={blind}")
    print(f"     cond2: recent_day={c2.get('recent_day')} recent_day_pct="
          f"{c2.get('recent_day_pct')} triggered={c2.get('triggered')} "
          f"n_priced={c2.get('n_priced_days')}/{c2.get('n_days')}")
    print(f"     flow_days_named={c2.get('flow_days_UNKNOWN') or c2.get('flow_days') or c2.get('unknown_flow_days')}")
    if ev.get("triggers"): print(f"     triggers={ev['triggers']}")
    print(f"     GATE VERDICT: {'NOT RESUMABLE' if (blind or ev.get('tripped')) else 'RESUMABLE'}")
    print()
    shutil.rmtree(tree, ignore_errors=True)
