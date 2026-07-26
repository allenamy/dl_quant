#!/usr/bin/env python3
"""§4-5b 符号缺陷的红/绿 oracle —— 0C 交付, 供修复方做前后对照 (2026-07-26)。

★ 它检验的命题
`filled_notional` 由 `binance_broker.py` 写成**带符号**的量 (`sign * cq`)。§4-5b 的推算持仓这样读它:

    f = float(o["filled_notional"] or 0.0)
    if f > 0:                                        # 卖单 (f<0) 在这里被整体丢掉
        acc[sym] += (1 if o["side"] == "buy" else -1) * f     # 而且符号被再施加一次

⇒ 对每一笔**已成交的卖单**, 推算持仓贡献 0 ⇒ `expected` 少掉整笔 ⇒ `unexplained_frac` 被推到 1.0。

★ 为什么这是一个"被另一个缺陷掩盖着的缺陷"
2026-07-26T00:17Z 那次 trip 里, 真实缺陷是"下单量被翻倍" ⇒ 每个名字的 frac 本应≈0.5。带上本缺陷,
16 个卖单名字变成 1.0 —— **它们仍然是真阳性**, 所以缺陷完全不可见。**一旦翻倍被修好, 这 16 条会继续
以 frac≈1.0 触发, 现场会读作"翻倍没修好"。**

★ 判据 (这才是 oracle 的用法, 不是"看一眼数好不好看")
    修复前:  as_shipped 呈**两个族群**  (≈0.5 一族 + 恰好 =1.0 一族, 后者与卖单集合逐一对应)
    修复后:  生产 watchdog 的 5b 输出应与本脚本的 sign_corrected 一致 ⇒ **单一族群**
    ⇒ 若修复后仍有 frac==1.0 且该名字当日有成交卖单, 修复未生效 (或只改了四处中的一处)。

★ 它不检验什么 (口径边界, 免得被当成比它更强的证据)
  - 不判定 trip 本身是真阳性还是假阳性 —— 那是另一个判断, 已单独做过 (结论: 真阳性);
  - 不检验 `position_readback` 的写入路径 (与订单表不同源, 我未查);
  - 只覆盖 §4-5b 一处。同族另有三处 (`pilot_metrics` 的 m1:68 / m3:162 / m5:212), 本脚本不碰。

用法:
    python oracle_5b_sign.py --root ~/dl_quant_live/state/testnet/pilot_log --days 20260725,20260726
    python oracle_5b_sign.py --root ... --eval ~/dl_quant_live/state/testnet/watchdog/last_eval.json
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict


def _read(root: str, day: str, table: str):
    p = os.path.join(root, day, f"{table}.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def five_b(root: str, days, sign_corrected: bool):
    """§4-5b 原样复算。`sign_corrected=False` 复制生产代码的行为, 逐字。"""
    anomalies, prev_rb = [], None
    for d in days:
        rb_by = defaultdict(dict)
        for r in _read(root, d, "position_readback"):
            rb_by[r["anchor_ts"]][r["symbol"]] = float(r["venue_position_notional"])
        filled = defaultdict(lambda: defaultdict(float))
        for o in _read(root, d, "orders"):
            f = float(o["filled_notional"] or 0.0)
            if sign_corrected:
                # filled_notional 已带符号: 直接累加, 不再施加 side
                if f != 0.0:
                    filled[o["anchor_ts"]][o["symbol"]] += f
            else:
                if f > 0:
                    filled[o["anchor_ts"]][o["symbol"]] += (1 if o["side"] == "buy" else -1) * f
        for ats in sorted(rb_by):
            cur = rb_by[ats]
            if prev_rb is not None:
                for sym, v in cur.items():
                    exp = prev_rb.get(sym, 0.0) + filled[ats].get(sym, 0.0)
                    un = abs(v - exp)
                    scale = max(abs(exp), abs(v), 1.0)
                    if un / scale > 0.10:
                        anomalies.append({"anchor_ts": ats, "symbol": sym,
                                          "expected": round(exp, 2), "observed": round(v, 2),
                                          "unexplained_frac": round(un / scale, 4)})
            prev_rb = cur
    return anomalies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="pilot_log 根 (含 YYYYMMDD 子目录)")
    ap.add_argument("--days", default="", help="逗号分隔; 留空 = 目录下全部")
    ap.add_argument("--eval", default="", help="可选: watchdog last_eval.json, 用于与生产输出对账")
    a = ap.parse_args()
    days = ([d for d in a.days.split(",") if d] or
            sorted(x for x in os.listdir(a.root) if x.isdigit()))

    sells, buys = set(), set()
    for d in days:
        for o in _read(a.root, d, "orders"):
            f = float(o["filled_notional"] or 0.0)
            (sells if f < 0 else buys if f > 0 else set()).add(o["symbol"])

    shipped, fixed = five_b(a.root, days, False), five_b(a.root, days, True)
    dist_s = Counter(round(x["unexplained_frac"], 1) for x in shipped)
    dist_f = Counter(round(x["unexplained_frac"], 1) for x in fixed)
    ones = [x for x in shipped if x["unexplained_frac"] == 1.0]
    ones_are_sells = sum(1 for x in ones if x["symbol"] in sells)

    print(f"天数 {days}  |  成交卖单名字 {len(sells)}, 成交买单名字 {len(buys)}")
    print(f"as_shipped     n={len(shipped):3d}  分布 {dict(sorted(dist_s.items()))}")
    print(f"sign_corrected n={len(fixed):3d}  分布 {dict(sorted(dist_f.items()))}")
    print(f"frac==1.0 的 {len(ones)} 条里, 有 {ones_are_sells} 条是成交卖单")
    for x in ones[:3]:
        m = [y for y in fixed if y["symbol"] == x["symbol"] and y["anchor_ts"] == x["anchor_ts"]]
        print(f"  {x['symbol']:12s} as_shipped exp={x['expected']:10.2f} frac={x['unexplained_frac']}"
              f"   ->  corrected exp={m[0]['expected'] if m else float('nan'):10.2f} "
              f"frac={m[0]['unexplained_frac'] if m else float('nan')}")

    # ── 判据 ────────────────────────────────────────────────────────────────────────────────
    two_pop = len(ones) > 0 and ones_are_sells == len(ones)
    one_pop = len(set(dist_f)) == 1
    print()
    print(f"[红] as_shipped 呈两族且 1.0 一族全为卖单 : {two_pop}")
    print(f"[绿] sign_corrected 收敛为单一族群       : {one_pop}")

    if a.eval and os.path.exists(a.eval):
        ev = json.load(open(a.eval))
        prod = (ev.get("conditions", {}).get("cond5_venue_event", {})
                  .get("5b_liquidation_anomaly", {}))
        n_prod = prod.get("n")
        ex = {e["symbol"]: e["unexplained_frac"] for e in prod.get("examples", [])}
        mine = {x["symbol"]: x["unexplained_frac"] for x in shipped}
        agree = all(abs(mine.get(s, -9) - v) < 1e-6 for s, v in ex.items())
        print(f"\n生产 last_eval 对账: n={n_prod} vs 本脚本 as_shipped n={len(shipped)} "
              f"({'一致' if n_prod == len(shipped) else '不一致'}); 样例逐条吻合: {agree}")
        print("  ⇒ 一致即证明本脚本复现的是生产代码路径, 而不是我对它的印象。")
        # 修复之后, 生产输出应当改为与 sign_corrected 吻合
        agree_fixed = all(abs({x["symbol"]: x["unexplained_frac"]
                               for x in fixed}.get(s, -9) - v) < 1e-6 for s, v in ex.items())
        print(f"  修复后判据: 生产样例应与 sign_corrected 吻合 (当前 {agree_fixed}) —— "
              f"修复前为 False 才说明 oracle 有区分力。")


if __name__ == "__main__":
    main()
