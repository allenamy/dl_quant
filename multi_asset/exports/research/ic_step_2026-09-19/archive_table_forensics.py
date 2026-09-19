# -*- coding: utf-8 -*-
"""归档表取证 —— 关闭独立复审 FIC-04 的「7 锚差异」与「旧结论传播检查」两项。

## 问题一: 归档的 fee_table 与今天的原始日志有 7 锚不同, 是「去重修正」还是「后来补入数据」?

做法: 用**与归档同一个算法**(朴素求和)在今天的日志上重算。两边口径相同, 所以任何差异
**只能来自数据本身变了**, 不可能来自去重。

实测结论(2026-09-19):
  · 7 个锚的差全在「归档朴素 → 今朴素」这一段, 即 **09-11 之后回填继续写行**
    (09-09 16Z 补了 940 行 —— 正是 markout 覆盖只有 85.0% 的那一天)。
  · 「今朴素 → 今去重」在这 7 锚上恰好是 2.000 倍, 是纯去重。
  · ⇒ **归档表同时带两种错**: (a) 朴素求和 **且** (b) 在回填未完成的时刻取的快照。

## 问题二: 「除以一个常数」能不能把归档表修回真值?

**不能。** 逐锚倍数(朴素/去重)在今天的日志上就分布在 **2.000–3.000**, 根本不是常数;
归档表上更散(1.830–3.000), 因为它还叠了「快照不完整」。
全史 2.269 是**聚合比值**, 不是逐锚比值。⇒ 归档表不可修, 只能重跑。

## 问题三(复审: 「字段名检索不是数据血缘"): 按【数值】而不是字段名找传播

从朴素产物里取特征数值(逐锚极值与合计), 在全库 `*.md` 里搜这些数值串。
实测: 命中的三处全是巧合(CI 下界 `-28.12` / 逐锚盈亏列 `-11.13` / DSR 概率 `0.672353`)。
⇒ **数值级零命中**, 与字段名检索同结论, 但仪器更强。

**边界(必须写下): 数值检索仍然不是血缘。** 经过换算 / 四舍五入 / 图表的传播它一样看不见。
真正的血缘要靠【装置 → 产物 → 引用】的显式登记, 而那个登记目前**不存在**。

用法: python3 archive_table_forensics.py
"""
import collections
import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/live/pilot_journal/tools")
from fills_reader import collapse_supersedes  # noqa: E402

PL = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
REPO = "/Users/haosiyu/Desktop/quant_research"
OUT = f"{REPO}/multi_asset/exports/research/uplift_2026-09-11"
ARCHIVE = f"{OUT}/fee_table.r0_naive_ff44e1c3.json"
COMBO = 1787716800
U = lambda t: time.strftime("%m-%d %HZ", time.gmtime(t))

FAILS, N = [], [0]
def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(detail)[:300]) if detail != '' else ''}")
    if not cond:
        FAILS.append(name)

arch = {r["A"]: r for r in json.load(open(ARCHIVE))}
raw_n, raw_v, ded_n, ded_v = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
for d in sorted(x for x in os.listdir(PL) if x.isdigit()):
    p = f"{PL}/{d}/fills.jsonl"
    if not os.path.exists(p):
        continue
    rows = [json.loads(l) for l in open(p, errors="ignore") if l.strip()]
    byA = collections.defaultdict(list)
    for r in rows:
        byA[int(float(r.get("anchor_ts") or 0) // 14400 * 14400)].append(r)
    for A, rs in byA.items():
        cs = collapse_supersedes(rs)
        raw_n[A] += len(rs); raw_v[A] += sum(abs(r["fill_notional"]) for r in rs)
        ded_n[A] += len(cs); ded_v[A] += sum(abs(r["fill_notional"]) for r in cs)

print("① 归档朴素 vs 今天同算法朴素(两边口径相同 ⇒ 差异只能来自数据本身变了)")
diff = [A for A, r in arch.items() if A in raw_n and (raw_n[A] != r["n_fills"] or abs(raw_v[A] - r["traded_notional"]) > 0.01)]
check("差异锚数 = 7(复审 FIC-04 所报)", len(diff) == 7, f"{len(diff)} 个")
for A in sorted(diff):
    print(f"      {U(A)}  笔数 {arch[A]['n_fills']:>5} → {raw_n[A]:>5} ({raw_n[A]-arch[A]['n_fills']:+d})"
          f"   今朴素/今去重 = {raw_n[A]/ded_n[A]:.3f}")
check("这 7 锚今天的朴素/去重倍数全是 2.000(⇒ 差异不是去重造成的)",
      all(abs(raw_n[A] / ded_n[A] - 2.0) < 1e-9 for A in diff))

print("\n② 「除以一个常数」能不能修回真值")
ks = [A for A in arch if A in ded_v and arch[A].get("traded_notional")]
r_arch = np.array([arch[A]["traded_notional"] / ded_v[A] for A in ks])
r_now = np.array([raw_v[A] / ded_v[A] for A in ks])
print(f"      今朴素/今去重  中位 {np.median(r_now):.4f}  范围 [{r_now.min():.4f}, {r_now.max():.4f}]")
print(f"      归档朴素/今去重 中位 {np.median(r_arch):.4f}  范围 [{r_arch.min():.4f}, {r_arch.max():.4f}]")
check("逐锚倍数【不是常数】(⇒ 除以 2.269 必然失败)", r_now.max() - r_now.min() > 0.5,
      f"今日志上就跨 {r_now.min():.3f}–{r_now.max():.3f}")
check("归档表比今日志更散(它还叠了「快照不完整」)", r_arch.std() > r_now.std(),
      f"sd {r_arch.std():.4f} vs {r_now.std():.4f}")

print("\n③ 按【数值】找传播(复审: 字段名检索不是数据血缘)")
C = [r for r in arch.values() if r["A"] >= COMBO and r.get("gross")]
tv = [r["turnover_frac"] for r in C if r.get("turnover_frac")]
vals = {
    "fee_bps_of_gross 均值": np.mean([r["fee_bps_of_gross"] for r in C if r.get("fee_bps_of_gross") is not None]),
    "turnover_frac 均值 %": np.mean(tv) * 100,
    "turnover_frac 中位 %": np.median(tv) * 100,
    "fee_usdt_total 合计": sum(r["fee_usdt_total"] for r in C),
    "traded_notional 合计": sum(r["traded_notional"] for r in C),
}
# ★★ 数值检索有一个【固有上限】, 必须先说清楚再用:
#   只有**高熵**的值才能靠数值追踪。像 0.672 这样的 3 位小数在全库有 40+ 处无关命中,
#   把它算进"传播"等于没扫。所以把模式分成两档, 只对高熵档下结论:
#     · 高熵(≥7 位有效数字, 如 2,528,534 / 51,659): 命中几乎必然是真传播。
#     · 低熵(≤4 位有效数字, 如 0.672 / 28.12): **本方法查不了**, 只能登记为盲区。
HI, LO = set(), set()
for v in vals.values():
    if abs(v) >= 10000:
        HI |= {f"{v:,.0f}", f"{int(round(v))}"}
    elif abs(v) >= 100:
        HI |= {f"{v:.4f}"}          # 708.9649 有 7 位有效数字
        LO |= {f"{v:.2f}"}
    else:
        LO |= {f"{v:.4f}", f"{v:.3f}"}
SKIP = ("fee_table", "LED01", "REVIEW_RESPONSE", "archive_table_forensics")
def scan(ps):
    out = []
    for q in sorted(ps):
        r = subprocess.run(["git", "-C", REPO, "grep", "-l", "-F", q, "--", "*.md"], capture_output=True, text=True)
        out += [(q, f) for f in r.stdout.split("\n") if f and not any(x in f for x in SKIP)]
    return out
hi, lo = scan(HI), scan(LO)
print(f"      高熵模式 {len(HI)} 个 {sorted(HI)}  ⇒ 命中 {len(hi)} 处")
for q, f in hi[:10]:
    print(f"        ★真传播候选  {q!r}  {f}")
if not hi:
    print("        (零命中 —— 朴素产物的高熵数值没有出现在任何 md 里)")
print(f"      低熵模式 {len(LO)} 个 {sorted(LO)}  ⇒ 命中 {len(lo)} 处, **本方法查不了, 登记为盲区**")
check("高熵数值零命中(⇒ 没有已发布结论抄了朴素产物的可追踪数字)", not hi, f"{len(hi)} 处")
print("      ★ 低熵命中 2026-09-19 抽样人读: 全为巧合(CI 下界 -28.12 / 逐锚盈亏 -11.13 / DSR 概率 0.672353)")
print("      ★ 边界: 数值检索【仍然不是血缘】—— 换算/舍入/图表的传播它一样看不见。")
print("         真正的血缘要靠【装置→产物→引用】的显式登记, 该登记目前不存在。")

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
