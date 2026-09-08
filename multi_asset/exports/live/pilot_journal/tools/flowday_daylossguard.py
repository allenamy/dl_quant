"""划转日 单日止损人工代偿守卫(只读; 2026-09-08 入金 +35,007.38 USDT 当日)

★ 为什么需要它: `live/watchdog.py` L1095-1104 —— 当日任一 daily_nav 行 `external_flow_usdt ≠ 0`,
  cond2 就把该日记 None(UNKNOWN)并放进 `flow_days`, 于是 **该日没有任何单日止损保护**。
  隔离实测(本会话 flowday_probe_20260908.py, 四臂):
    B 入金行写入后            -> recent_day 回退到 20260907 (+0.446%), triggered=False  ← 无误触发
    C 入金行 + 当日 −6%        -> triggered=**False**                                   ← 盲区实证
    D 同样 −6% 但无划转        -> triggered=True, "−5.87% of EQUITY"                    ← 对照, 守卫本身正常
  cond4(累计 −25%)不受影响, 仍在岗; 盲的只有单日线。

★ 口径逐字照抄 watchdog.py L1106:
    day_pct = (当日最后 nav − **前一日最后 nav**) / 前一日最后 nav × 100
  本脚本在分子里再减去当日 TRANSFER 净额, 即「把入金摘掉之后, 这一天真实亏了多少」。
  阈值与在役一致: 告警 −2.68%, 底线 −4.0%(live/watchdog.py DAY_LOSS_LIMIT_PCT)。

★ 只读: 一次 /fapi/v3/account + 一次 /fapi/v1/income(TRANSFER)。不下单, 不写实盘状态。
★ 它不会平仓 —— 它只报数。真要动书, 由用户裁定。

跑法: /usr/bin/python3 multi_asset/exports/live/pilot_journal/tools/flowday_daylossguard.py
退出码: 0 正常 / 3 越过告警线 / 4 越过底线 / 1 读取失败
"""
import json, os, sys, time, calendar
REPO = "/Users/haosiyu/dl_quant_live"
for d in ("live", "ops"):
    sys.path.insert(0, os.path.join(REPO, d))
os.chdir(REPO)
import envfile; envfile.load(); os.environ.setdefault("LIVE_MODE", "LIVE")
from binance_broker import BinanceBroker

ALERT, LIMIT = -2.68, -4.0
today = time.strftime("%Y%m%d", time.gmtime())
day0 = calendar.timegm(time.strptime(today, "%Y%m%d")) * 1000

# 前一日最后 nav —— 从 pilot_log 逐日目录取, 与 watchdog 同源同字段
root = os.path.join(REPO, "state/live/pilot_log")
days = sorted(d for d in os.listdir(root) if d.isdigit() and d < today)
prev_day, prev_nav = None, None
for d in reversed(days):
    p = os.path.join(root, d, "daily_nav.jsonl")
    if not os.path.exists(p):
        continue
    rows = [json.loads(l) for l in open(p) if l.strip()]
    if rows and rows[-1].get("nav"):
        prev_day, prev_nav = d, float(rows[-1]["nav"]); break
if prev_nav is None:
    print("FAIL 没有可用的前一日 nav"); sys.exit(1)

B = BinanceBroker(mode="LIVE")
snap = B.account_snapshot(); inc = B.income_since(day0)
eq = float(snap["equity"])
flow = float((inc or {}).get("external_flow") or 0.0)
raw_pct = (eq - prev_nav) / prev_nav * 100.0
net_pct = (eq - flow - prev_nav) / prev_nav * 100.0
state = "OK" if net_pct > ALERT else ("ALERT" if net_pct > LIMIT else "LIMIT")
print("%s  %s  今日=%s 前一日=%s(nav %.2f)" % (
    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), state, today, prev_day, prev_nav))
print("  equity %.2f | TRANSFER 今日 %+.2f | 划转净掉后权益 %.2f" % (eq, flow, eq - flow))
print("  day_pct 原始 %+.3f%%  |  ★ 划转净掉后 %+.3f%%   (告警 %.2f%% / 底线 %.2f%%)"
      % (raw_pct, net_pct, ALERT, LIMIT))
print("  gross %.2f (%.3fx equity), %d 名" % (
    sum(abs(v) for v in snap["positions_notional"].values()),
    sum(abs(v) for v in snap["positions_notional"].values()) / max(eq, 1e-9),
    len(snap["positions_notional"])))
print("  注: cond2 今日记 UNKNOWN(external_flow≠0), 单日止损**不会**自动触发; cond4 累计线仍在岗。")
sys.exit(0 if state == "OK" else (3 if state == "ALERT" else 4))
