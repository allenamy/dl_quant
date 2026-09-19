# -*- coding: utf-8 -*-
"""markout 回填覆盖率 —— 互斥分类, 全史逐日。只读。

★ `mark_status` 是【过程标签, 不是终态】: 同一笔成交的多行里可能既有
  `aggtrades_window_expired` 又有后来某一轮真正拿到的 markout。
  **只看最终有没有 `mid_at_fill_plus_60s` 才是覆盖率。**
  按 mark_status 计缺失会把 2,797 夸大成 17,219(6 倍)—— 2026-09-19 实测。

分类互斥且用 assert 钉住(have + no_trade + expired + pending == 唯一成交)。
用法: python3 markout_coverage.py
"""
import json, os, collections

R = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
print(f"{'day':<10}{'唯一':>7}{'有mark':>8}{'覆盖':>8}{'no_trade':>10}{'永久过期':>10}{'未处理':>8}")
tot = collections.Counter()
for d in sorted(x for x in os.listdir(R) if x.isdigit()):
    p = f"{R}/{d}/fills.jsonl"
    if not os.path.exists(p):
        continue
    by = {}
    for l in open(p, errors="ignore"):
        if not l.strip():
            continue
        r = json.loads(l)
        by.setdefault((r["symbol"], r["trade_id"]), []).append(r)
    if not by:
        continue
    n = len(by); have = nt = ex = pend = 0
    for rs in by.values():
        if any(r.get("mid_at_fill_plus_60s") is not None for r in rs):
            have += 1
            continue
        st = {r.get("mark_status") for r in rs if r.get("mark_status")}
        if "aggtrades_window_expired" in st:
            ex += 1
        elif "no_trade_within_window" in st:
            nt += 1
        else:
            pend += 1
    assert have + nt + ex + pend == n, (d, have, nt, ex, pend, n)
    tot["n"] += n; tot["have"] += have; tot["nt"] += nt; tot["ex"] += ex; tot["pend"] += pend
    flag = "  <-" if have / n < 0.97 else ""
    print(f"{d:<10}{n:>7}{have:>8}{have/n*100:>7.1f}%{nt:>10}{ex:>10}{pend:>8}{flag}")
print(f"{'合计':<10}{tot['n']:>7}{tot['have']:>8}{tot['have']/tot['n']*100:>7.1f}%"
      f"{tot['nt']:>10}{tot['ex']:>10}{tot['pend']:>8}")
print()
print("永久过期 = 场所 aggTrades 2 天窗过后再也拿不到")
print("未处理   = 下一轮回填会拿(com.hsy.markout_backfill, 本地 01:05/05:05/09:05… 每 4 小时)")
