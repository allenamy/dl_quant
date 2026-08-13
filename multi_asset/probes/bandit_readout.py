"""ε-bandit 正规读数器 (PREREG_placement_bandit f657efde 语义).
- 安全线: behind 绝对成交率 <15% (n>=100) 或实验列缺失 -> eps=0 排查
- n<300 禁臂间对比(除安全线); 主判 ΔV 只在 behind n>=600 跑一次(不在本工具)
- 双向对账: orders.filled_notional 总额 vs fills.fill_notional 总额 (±5% 内)
用法: python3 bandit_readout.py [pilot_log_root]
"""
import json, glob, sys
from collections import Counter, defaultdict

ROOT = sys.argv[1] if len(sys.argv) > 1 else '/Users/haosiyu/dl_quant_live/state/live/pilot_log'

arms = Counter(); att_fill = Counter(); att_full = Counter()
fn_sum = defaultdict(float); it_sum = defaultdict(float)
intents = defaultdict(lambda: [0.0, 0.0])   # key -> [sum_filled_abs, max_intended_abs]
orders_total_fn = 0.0
for f in sorted(glob.glob(ROOT + '/2026*/orders.jsonl')):
    for line in open(f):
        try:
            r = json.loads(line)
        except Exception:
            continue
        fn = abs(float(r.get('filled_notional') or 0))
        orders_total_fn += fn
        a = r.get('placement_arm')
        if not a:
            continue
        it = abs(float(r.get('intended_notional') or 0))
        arms[a] += 1
        if fn > 1e-9:
            att_fill[a] += 1
        if it > 1e-9 and fn >= 0.999*it:
            att_full[a] += 1
        fn_sum[a] += fn; it_sum[a] += it
        k = (a, r.get('rebalance_id'), r.get('symbol'), r.get('side'))
        intents[k][0] += fn
        intents[k][1] = max(intents[k][1], it)

fills_total = 0.0
for f in sorted(glob.glob(ROOT + '/2026*/fills.jsonl')):
    for line in open(f):
        try:
            r = json.loads(line)
        except Exception:
            continue
        fills_total += abs(float(r.get('fill_notional') or 0))

int_n = Counter(); int_fill = Counter(); int_vw_n = defaultdict(float); int_vw_d = defaultdict(float)
for (a, *_k), (sf, mi) in intents.items():
    int_n[a] += 1
    if mi > 1e-9 and sf >= 0.5*mi:
        int_fill[a] += 1
    int_vw_n[a] += min(sf, mi); int_vw_d[a] += mi

print(f"对账: orders侧成交总额 {orders_total_fn:,.0f} vs fills侧 {fills_total:,.0f} "
      f"(差 {100*abs(orders_total_fn-fills_total)/max(fills_total,1e-9):.1f}%"
      f"{' ✓' if abs(orders_total_fn-fills_total) <= 0.05*max(fills_total,1) else ' ⚠️>5% 需查'})")
for a in ('join', 'behind'):
    if arms[a] == 0:
        print(f"{a}: 无样本 ⚠️")
        continue
    ar = 100*att_fill[a]/arms[a]
    fr = 100*att_full[a]/arms[a]
    vr = 100*fn_sum[a]/max(it_sum[a], 1e-9)
    ir = 100*int_fill[a]/max(int_n[a], 1)
    iv = 100*int_vw_n[a]/max(int_vw_d[a], 1e-9)
    print(f"{a}: 尝试 n={arms[a]} 有成交{ar:.0f}% 全额{fr:.0f}% 金额{vr:.0f}% | "
          f"意图 n={int_n[a]} 过半成交{ir:.0f}% 金额加权{iv:.0f}%")
b_rate = 100*fn_sum['behind']/max(it_sum['behind'], 1e-9)
if arms['behind'] >= 100:
    verdict = 'PASS' if b_rate >= 15 else 'TRIP -> eps=0 排查'
else:
    verdict = f"n={arms['behind']}<100 未启用"
print(f"安全线(behind 金额成交率<15%@n>=100): {verdict} (当前 {b_rate:.0f}%)")
print(f"主判进度: behind 尝试 n={arms['behind']}/600; n<300 禁臂间对比(本工具不输出 ΔV)")
