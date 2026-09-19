# -*- coding: utf-8 -*-
"""研究仓的**规范成交表访问器** —— LED-01 的研究侧对应物。

## 为什么存在

`state/live/pilot_log/*/fills.jsonl` 是**追加式**日志: markout 回填**不是原地改写, 而是把同一笔
成交再写一遍**(同 `trade_id`, `supersedes_trade_id == trade_id`, 只有 mark 字段不同)。
全史 50 天实测: 唯一成交 53,844 笔里 39,184 笔写了两遍、**14,568 笔写了三遍**;
原始行 122,164 / 唯一 53,844 = **2.269 倍**(单锚最坏 ≈3.00 倍)。

- **直接求和** ⇒ 成交额、费用、笔数虚高 2.07–2.29 倍; 跨源比率(如 换手 = 成交/gross)虚高 2.31–2.38 倍。
- **单纯按 trade_id 保留第一行** ⇒ 把**全部 markout 丢光**(原始行的 mark 恒为 None)。
- **正确动作 = 坍缩**: 一笔成交一行, **金额取一次, mark 取有值的那条**。

执行器仓有一个闭世界 AST 普查器 `live/tests_fills_reader_census.py` 管住它自己的读者, 但其
docstring 明写 `NOT asserted: research-repo readers` —— **这个模块就是补上研究仓这一侧。**

## 契约(与执行器 `live/pilot_log.py` L543–577 同义)

一笔执行 = `(symbol, trade_id)`。Binance 的 trade id 是**逐品种**的, 所以**单独用 `trade_id` 做键
会跨品种合并**。每键在写入顺序上: 恰好一条 ORIGINAL(无 `supersedes_trade_id`), 其后 0..n 条
SUPERSEDE(声明 `supersedes_trade_id == trade_id`), **且与 ORIGINAL 只在 mark 字段上不同**。
**后写的胜出。** 没有 trade id 的行**永不合并**(它们不是一个身份)。

本模块**强制**这条契约: 若同键各行的金额字段不一致, `collapse_supersedes` **抛异常而不是猜**
—— 因为那意味着契约被破坏, 任何一种取法都是错的。

## 用法

    import fills_reader as FR
    fills = FR.read_day(ROOT, "20260919")              # 坍缩后
    fills = FR.read_anchor(ROOT, 1789777442.671038)    # 按 anchor_ts 归属(跨 UTC 日切)
    raw   = FR.read_day(ROOT, "20260919", raw=True)    # 原始行, 写入顺序

出任何聚合数之前先跑一次**免费对账**:

    FR.assert_reconciles(ROOT, "20260919")   # 坍缩成交额 vs orders.filled_notional, 逐分

自检: `python3 fills_reader.py [ROOT]` —— 跑契约自检 + 对执行器实现的漂移守卫。
"""
import json
import os
import sys
from datetime import datetime, timezone

LIVE_ROOT = "/Users/haosiyu/dl_quant_live"
PILOT_LOG = "state/live/pilot_log"          # ★ 不是 state/pilot_log(那里只有 _schema.json, 是个空壳)
GRID_S = 14400

# supersede 行允许与 ORIGINAL 不同的字段 —— 其余字段不一致即契约破坏
MARK_FIELDS = frozenset({
    "mid_at_fill_plus_60s", "mid_at_fill_plus_60s_note", "mark_source", "mark_ts_actual",
    "mark_lag_s", "mark_window_s", "mark_status", "backfilled_utc", "supersedes_trade_id",
})
AMOUNT_FIELDS = ("fill_notional", "fill_px", "commission", "commission_asset",
                 "side", "order_type", "fill_ts", "anchor_ts", "rebalance_id")


class FillsContractError(RuntimeError):
    """同一 (symbol, trade_id) 的多行在【金额类字段】上不一致 —— 契约被破坏, 不猜。"""


def _jl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, errors="ignore") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def collapse_supersedes(rows):
    """一笔执行一行。键 = (symbol, trade_id); **整行取最后一条**; 无 trade id 的行永不合并。

    ★ 语义与执行器 `live/pilot_log.collapse_supersedes` **逐笔等价**, 由本模块的漂移守卫在真实
      数据上钉住。**取整行, 不做逐字段合并** —— 合并会把 ORIGINAL 行那句
      `mid_at_fill_plus_60s_note = "…pending backfill, NOT zero"` 和一个**已经拿到的 mark**
      留在同一行里, 自相矛盾。(2026-09-19: 本模块第一版就是合并式, 漂移守卫首跑即抓到, 287/320 笔受影响。)
    ★ **顺序保留最后一条所在的位置**, 与执行器一致 —— 按时序走表的调用者仍拿到时序。

    额外(执行器没做, 本模块做): 同键各行的 AMOUNT_FIELDS 必须一致, 否则抛 FillsContractError。
    契约说 supersede 行与 ORIGINAL **只在 mark 字段上不同**; 金额不同意味着契约破坏, 任何取法都是错的。
    """
    last = {}
    for i, r in enumerate(rows):
        tid = r.get("trade_id")
        if tid is None:
            continue
        last[(r.get("symbol"), tid)] = i

    # 契约检查(不改变返回值)
    seen = {}
    for r in rows:
        tid = r.get("trade_id")
        if tid is None:
            continue
        k = (r.get("symbol"), tid)
        if k not in seen:
            seen[k] = r
            continue
        prev = seen[k]
        for f in AMOUNT_FIELDS:
            a, b = prev.get(f), r.get(f)
            if a is None or b is None:
                continue
            if isinstance(a, float) and isinstance(b, float):
                if abs(a - b) > 1e-9 * max(1.0, abs(a)):
                    raise FillsContractError(f"{k} 字段 {f} 不一致: {a!r} vs {b!r}")
            elif a != b:
                raise FillsContractError(f"{k} 字段 {f} 不一致: {a!r} vs {b!r}")

    out = []
    for i, r in enumerate(rows):
        tid = r.get("trade_id")
        if tid is None or last.get((r.get("symbol"), tid)) == i:
            out.append(r)
    return out


def read_day(root=LIVE_ROOT, day=None, raw=False):
    rows = _jl(os.path.join(root, PILOT_LOG, day, "fills.jsonl"))
    return rows if raw else collapse_supersedes(rows)


def read_orders(root=LIVE_ROOT, day=None):
    return _jl(os.path.join(root, PILOT_LOG, day, "orders.jsonl"))


def days(root=LIVE_ROOT):
    base = os.path.join(root, PILOT_LOG)
    return sorted(d for d in os.listdir(base) if d.isdigit()) if os.path.isdir(base) else []


def read_range(root=LIVE_ROOT, day_list=None, raw=False):
    out = []
    for d in (day_list if day_list is not None else days(root)):
        out.extend(read_day(root, d, raw=raw))
    return out


def read_anchor(root=LIVE_ROOT, anchor_ts=None, raw=False):
    """按 `anchor_ts` 归属, 而不是按文件名 —— 日文件按 UTC 日切, 只读一天会漏。"""
    t = float(anchor_ts)
    ds = sorted({datetime.fromtimestamp(t + k, tz=timezone.utc).strftime("%Y%m%d")
                 for k in (-GRID_S, 0, GRID_S)})
    rows = [r for d in ds for r in read_day(root, d, raw=True)
            if float(r.get("anchor_ts") or -1) == t]
    return rows if raw else collapse_supersedes(rows)


def reconcile(root=LIVE_ROOT, day=None):
    """坍缩成交额 vs orders.filled_notional 合计。免费、逐分、当场判真假。"""
    f = sum(abs(float(r.get("fill_notional") or 0.0)) for r in read_day(root, day))
    o = sum(abs(float(r.get("filled_notional") or 0.0)) for r in read_orders(root, day))
    return {"day": day, "fills_collapsed": f, "orders_filled_notional": o, "diff": f - o}


def assert_reconciles(root=LIVE_ROOT, day=None, tol=0.01):
    r = reconcile(root, day)
    if abs(r["diff"]) > tol:
        raise AssertionError(f"{day} 坍缩成交额 {r['fills_collapsed']:.2f} 与 orders "
                             f"{r['orders_filled_notional']:.2f} 不符, 差 {r['diff']:+.2f}")
    return r


# ---------------------------------------------------------------- 自检 + 漂移守卫
def _selftest(root=LIVE_ROOT):
    fails = []

    def ck(name, cond, detail=""):
        print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(detail)[:200]) if detail else ''}")
        if not cond:
            fails.append(name)

    base = [{"symbol": "AUSDT", "trade_id": 1, "fill_notional": 10.0, "fill_px": 1.0,
             "side": "buy", "mid_at_fill_plus_60s": None}]
    sup = dict(base[0], supersedes_trade_id=1, mid_at_fill_plus_60s=1.01, backfilled_utc="x")
    out = collapse_supersedes(base + [sup])
    ck("坍缩: 两行 -> 一笔, 金额取一次, mark 取有值的那条",
       len(out) == 1 and out[0]["fill_notional"] == 10.0 and out[0]["mid_at_fill_plus_60s"] == 1.01)

    other = dict(base[0], symbol="BUSDT")
    ck("跨品种同 trade_id 不合并(trade id 是逐品种的)",
       len(collapse_supersedes([base[0], other])) == 2)

    ck("无 trade id 的行永不合并",
       len(collapse_supersedes([{"symbol": "A", "trade_id": None},
                                {"symbol": "A", "trade_id": None}])) == 2)

    try:
        collapse_supersedes([base[0], dict(sup, fill_notional=999.0)])
        ck("金额不一致 ⇒ 抛 FillsContractError(不猜)", False, "没有抛")
    except FillsContractError:
        ck("金额不一致 ⇒ 抛 FillsContractError(不猜)", True)

    ds = days(root)
    if not ds:
        print("  SKIP  真实数据自检 — 读不到 pilot_log, 报 UNAVAILABLE 而不是 PASS")
        return fails, "UNAVAILABLE"

    d = ds[-1]
    raw, col = read_day(root, d, raw=True), read_day(root, d)
    ck(f"真实数据 {d}: 坍缩后 <= 原始行", len(col) <= len(raw), f"{len(raw)} -> {len(col)}")
    rc = reconcile(root, d)
    ck(f"真实数据 {d}: 坍缩成交额与 orders.filled_notional 逐分相同",
       abs(rc["diff"]) <= 0.01, f"{rc['fills_collapsed']:.2f} vs {rc['orders_filled_notional']:.2f} 差 {rc['diff']:+.4f}")

    # ★ 漂移守卫: 与执行器自己的实现逐笔比。读不到 ⇒ UNAVAILABLE, 不是 PASS。
    pl = os.path.join(root, "live")
    if os.path.isdir(pl):
        sys.path.insert(0, pl)
        try:
            import pilot_log as PL  # noqa
            theirs = PL.collapse_supersedes(list(raw))
            mine = col
            same = len(theirs) == len(mine) and all(a == b for a, b in zip(theirs, mine))
            detail = f"executor {len(theirs)} vs mine {len(mine)}"
            if not same:
                for i, (a, b) in enumerate(zip(theirs, mine)):
                    if a != b:
                        fs = [f for f in set(a) | set(b) if a.get(f) != b.get(f)]
                        detail = (f"首个差异 @{i} 键 {(a.get('symbol'), a.get('trade_id'))} vs "
                                  f"{(b.get('symbol'), b.get('trade_id'))} 字段 {fs[:3]}")
                        break
            ck("★ 漂移守卫: 与执行器 pilot_log.collapse_supersedes 在真实数据上【整行逐笔相同】",
               same, detail)
            # 多跑几天, 一天相同不等于实现相同
            for d2 in ds[-6:-1]:
                r2 = read_day(root, d2, raw=True)
                ck(f"  漂移守卫 {d2}", PL.collapse_supersedes(list(r2)) == collapse_supersedes(list(r2)))
        except Exception as e:
            print(f"  UNAVAIL 漂移守卫: 无法 import 执行器 pilot_log ({type(e).__name__}: {e}) "
                  f"—— 报 UNAVAILABLE, 不当作通过")
            return fails, "UNAVAILABLE"
    else:
        print("  UNAVAIL 漂移守卫: 执行器 live/ 不在, 报 UNAVAILABLE, 不当作通过")
        return fails, "UNAVAILABLE"
    return fails, "CHECKED"


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else LIVE_ROOT
    print(f"fills_reader 自检 (root={root})")
    fails, drift = _selftest(root)
    print(f"\n{'ALL PASS' if not fails else 'FAILURES: ' + str(fails)}   漂移守卫={drift}")
    sys.exit(1 if fails else 0)
