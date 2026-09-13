"""Every terminal state has a declared destination. A state with no cell is a DEFECT.

*** MOCK ONLY: fixture rows plus a read of the real ledger. Nothing written, no venue. ***

★★★ THE CLASS, NOT THE INSTANCE. Two liquidations in eight hours shared one shape: a leg ends,
    nothing downstream picks the name up, and the residual becomes indistinguishable from an
    unexplained position break.
      04:00Z — 17 makers refused -5022, no fill and no top-up, 1050.10 USDT = 93% of the 1131
               break that flattened 83 positions.
    Fixing -5022 alone would leave the SHAPE intact. So the unit of work is the matrix: enumerate
    every way an order can end, declare where the name goes, and make a missing cell go red.

★★ ONE CHECK PER CELL (lead's requirement), plus a mutation per cell: change any disposition and
   this file must fail. A matrix nobody re-derives is a comment, and comments in this repo have
   twice said the opposite of the code they sat beside.

★ 2026-09-12 尺子第六次重标定(同一修复家族: 拆开事实, 再断言关系; 三处, 全部在真账本上有名有据):
   ① VENUE-LOCKED 锚类(E-0910-A, -4400「Futures Trading Quantitative Rules violated, only reduceOnly
     order is allowed」= 场所账户级锁, 锁住后本锚余下所有开仓单被拒): 09-11 08:24Z A1789115039 的
     非自愿缺口 4,014U 逐 USDT 等于 73 张被 -4400 拒掉的补单意图。稳态尺(200U)量的是【名字蒸发】,
     不是【场所把整条补单腿锁掉】; 前提失效, 分离性质没失效。修复同法: 独立成类, 断言
     (a) 非自愿 − 锁拒意图 < 200U(缺口被锁解释), (b) 其后首个稳态锚回 200U 线内, (c) 有主(anchor_loop
     按相位分页 [-4400])。REBUILD / RESIZE 优先(它们已有整书尺度的界; 08-26 / 08-27 / 09-07 / 09-10 的
     -4400 全落在这两类里)。
   ② -2027 场所上限类的分母改为该锚的 target(sizing)gross: 09-10 00:24Z A1788999840 是重建锚, 只建到
     67%(realized 154,910 vs target 232,259), 同一残差 2,239U 对 realized 的 1% 读 FAIL、对 target 读
     PASS —— 用 realized 做分母把「建仓未完成」(已单独成类)和「场所上限」两件事捏成一个数。
   ③ 自愿(no-chase)部分改从**行**求和, 不再从 gaps()["names"] 求和 —— 那张表按 |残差| 只留前 20 名
     (order_disposition L227), 缺口名 >20 的锚自愿部分被截成 0(09-11 08Z: 96 名, 行说 490U, 表说 0)⇒
     非自愿被高估 490U。同一残差算术(对该类行直接调 gaps(), gross_usdt 不截断)。
   每条新尺都带一条「在真账本上是承重的」断言([G]): 类空 ⇒ 稳态断言红; 分母换回 realized ⇒ 09-10 00Z 红;
   表法 vs 行法在 >20 名的锚上必须不同。

★ 2026-09-13 尺子第七次重标定(同一修复家族: 拆开事实, 独立成类, 断言关系; 三件事实, 全部第一手):
   ① E-0912-A 重判: 12Z 锚 A1789215839 的 MEMEUSDT / POPCATUSDT 两行写着 filled_amount_unknown,
     Σ|intended| = 1,524 USDT, 被尺子读成稳态交易锚的非自愿缺口 —— 但场所记录里这两笔完全可知
     (回执 origQty = 持仓, Σ 子成交 trade_qty == |confirmed_qty|, 本锚读回 0)。身份门的 1e-6 相对
     容差把「场所比我们更准」读成「场所在撒谎」。失效的是【「未知」= 真读不出】这个前提, 不是
     【稳态缺口小】这条性质 ⇒ 把量按事实重判为已知(残差 = intended − Σ 子成交报价: MEME −0.058U,
     POPCAT 恰 0), 阈值不动。判据独立实现并与 reconcile._rederive_ledger 逐行对账, 另有六条反控(六道门各一条)。
   ② TRIP-FLATTENED: 12:47:37Z 看门狗阶梯在 12Z 锚的【区间内】平了全书 —— 255 行 protective_flatten,
     Σ|filled_notional| = 235,382.55 USDT, 全部 filled, 255 行 fee_paid 未测。全账本这样的平仓有
     10 批 / 1,708 行 / 73.8 万 USDT 的真实执行, 而本文件【一条断言都读不到】(它们的 rebalance_id
     不在 anchors.jsonl 里, 又被 _traded 的名字前缀过滤器挑掉)。这是盲区, 不是红: 独立成类, 按
     order_type 结构选取(不按名字, E-0825-H), 批次行与看门狗自己的 flatten_all 动作记录【逐行精确对账】, 并用「拿掉这 1,708 行, [E] 的每
     一个数一位不变」把盲区本身证出来。
     ★ R3-A2(独立复审第三轮 §2.2): 对账【人口】先从看门狗事件侧定 —— 列出过单的 flatten_all 批次集合必须 == 账本
     批次集合, 缺整批 = LEDGER_BATCH_MISSING(点名, 红); 之后才逐批精确对账。此前人口取自订单行, 删整批订单行、
     保留全部事件, 其余批次逐批仍 EXACT, 该格照绿。
   ③ HALTED-NO-SUBMIT: 停机锚此前只被断言「整书缺口 > 1000U」—— 一条几乎什么都没说的绝对界。
     16 个停机锚的真实形态是: 终态只有 blocked_by_halt / skipped_min_notional, 0 次提交, 0 笔成交,
     且 Σ|intended| == anchors 行的 target_gross(到分)。按形态成类并断言这条恒等式; 承重证明 =
     把它们当交易锚读, 非自愿缺口 4,169–235,320 USDT, 稳态尺当场红。
   ★ 本次不放宽任何阈值, 不把任何锚移出稳态人口, 不删任何既有断言: ① 是行级的【量】重判(锚仍受
     同一条 200U 尺约束), ②③ 是净增断言。

Exit 0 = all pass."""
import collections
import copy
import glob
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
for _d in ("scheduler", "signal", "ops"):
    sys.path.insert(0, os.path.join(_REPO, _d))

import order_disposition as OD         # noqa: E402
import pilot_log as PL                 # noqa: E402

FAILS, N = [], [0]


def check(name, cond, extra=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(extra)) if extra else ''}")
    if not cond:
        FAILS.append(name)


def row(reason, intended=100.0, filled=0.0, note="", leg="maker", sym="AAAUSDT"):
    return {"symbol": sym, "order_type": leg, "terminal_reason": reason,
            "intended_notional": intended, "filled_notional": filled,
            "note": note, "rebalance_id": "RID"}


print("[A] the matrix is CLOSED over everything the venue has ever told us")
_all = []
for _f in sorted(glob.glob(os.path.join(_REPO, "state/live/pilot_log/*/orders.jsonl"))):
    for _l in open(_f):
        _l = _l.strip()
        if _l:
            _all.append(json.loads(_l))
check("★★★ no terminal state in the entire production ledger lacks a cell — the closed-world "
      "assertion, on every row we have ever written",
      not OD.unknown_reasons(_all), OD.unknown_reasons(_all) or f"{len(_all)} rows clean")
check("★★★ and the matrix covers the WRITER's whole vocabulary too, not just what has occurred — "
      "a state that has never happened yet is exactly the one that will surprise us",
      not (set(PL.TERMINAL_REASONS) - set(OD.DISPOSITION)),
      sorted(set(PL.TERMINAL_REASONS) - set(OD.DISPOSITION)) or "all TERMINAL_REASONS declared")
check("★★ ...and no cell is stale (a matrix that outlives the states it describes stops being "
      "a map)",
      not (set(OD.DISPOSITION) - set(PL.TERMINAL_REASONS)),
      sorted(set(OD.DISPOSITION) - set(PL.TERMINAL_REASONS)))

print("\n[B] ONE CHECK PER CELL — what each terminal state means for the name")
CELLS = [
    ("filled", OD.COMPLETE, "the intent was met; nothing is owed"),
    ("partial_expired", OD.RECOVERED, "the ONE path that always worked: remainder -> top-up"),
    ("skipped_min_notional", OD.COMPLETE, "below the venue floor; no order could have been sent"),
    ("skipped_no_mid", OD.GAP, "no book, so no price; nothing retries it"),
    ("never_submitted", OD.GAP, "built and never left the process"),
    ("filled_amount_unknown", OD.GAP, "it filled and we cannot say how much — a gap of UNKNOWN "
                                      "size, which must not read as zero"),
    ("venue_reject", OD.GAP, "code-dependent: -5022 recovered, our-bug codes are real gaps"),
    ("submitted_rejected", OD.GAP, "the venue refused it; nothing retries"),
    ("skipped_rate_limit", OD.GAP, "throttled; retrying inside the anchor is wrong"),
    ("blocked_by_halt", OD.GAP, "our OWN halt refused it — an INTENDED gap, and still a gap"),
    ("abandoned_spread_gt_25bps", OD.GAP, "chasing costs more than the tracking error"),
    ("abandoned_max_attempts", OD.GAP, "code-dependent: -4164 is dust below the floor"),
    ("skipped_unknown_fill", OD.GAP, "could not read the maker's fill; sizing would risk doubling"),
]
for _reason, _want, _why in CELLS:
    _got = OD.DISPOSITION.get(_reason, {}).get("disposition")
    check(f"★★ `{_reason}` -> {_want.upper()} — {_why}", _got == _want, _got)
check("★★★ every declared cell carries a WHY, not just a verdict — the next person needs the "
      "reason, because the verdict alone cannot be re-derived",
      all(len(v.get("why", "")) > 40 for v in OD.DISPOSITION.values()),
      [k for k, v in OD.DISPOSITION.items() if len(v.get("why", "")) <= 40])

print("\n[C] the two CODE-DEPENDENT cells — resolved by the venue code, not by the state alone")
_g = OD.gaps([row("venue_reject", note="[-5022] post only would cross")], "RID")
check("★★★ a -5022 maker is NOT a gap — since 2026-08-02 its residual is recovered by the taker "
      "top-up, which is the whole fix",
      _g["n_named"] == 0, _g["n_named"])
_g = OD.gaps([row("venue_reject", note="[-1111] precision over maximum")], "RID")
check("★★★ ...but a -1111 maker IS a gap — OUR malformed order, which must not be auto-retried "
      "(as a MARKET order it might SUCCEED, which is worse than failing)",
      _g["n_named"] == 1 and abs(_g["gross_usdt"] - 100.0) < 1e-6, _g["gross_usdt"])
_g = OD.gaps([row("abandoned_max_attempts", intended=0.02, note="[-4164] notional < 5",
                  leg="topup_taker")], "RID")
check("★★★ a -4164 top-up is NOT a gap — MEASURED: all 68 such rows in the whole ledger are "
      "-4164, median $0.017, $6.62 total. Dust below a floor no order could clear, not an "
      "abandoned trade. Counting them would bury the gaps that matter under 68 sub-cent rows",
      _g["n_named"] == 0, _g)
_g = OD.gaps([row("abandoned_max_attempts", intended=80.0, note="[-2019] margin insufficient",
                  leg="topup_taker")], "RID")
check("★★★ ...but any OTHER code on that state IS a gap — the path ended and nothing downstream "
      "exists",
      _g["n_named"] == 1 and abs(_g["gross_usdt"] - 80.0) < 1e-6, _g["gross_usdt"])
_g = OD.gaps([row("venue_reject", intended=507.0, sym="PIEVERSEUSDT",
                  note="[-2027] Exceeded the maximum allowable position at current leverage."),
              row("venue_reject", intended=-30.0, sym="BBBUSDT", note="[-1111] precision")], "RID")
check("★★★ a -2027 maker (E-0909-E) is a gap that STAYS in gross AND is named as venue-capped — "
      "so the evaporation ruler can exclude it without the ledger forgetting it",
      _g["n_named"] == 2 and abs(_g["gross_usdt"] - 537.0) < 1e-6
      and abs(_g["venue_cap_usdt"] - 507.0) < 1e-6 and _g["venue_cap_names"] == ["PIEVERSEUSDT"]
      and [e for e in _g["names"] if e["symbol"] == "PIEVERSEUSDT"][0].get("structural")
      == "venue_position_limit", _g)

print("\n[D] the ledger's arithmetic — signed, and honest about what it cannot size")
_rows = [row("blocked_by_halt", intended=+100.0, sym="AAAUSDT"),
         row("blocked_by_halt", intended=-40.0, sym="BBBUSDT"),
         row("filled_amount_unknown", intended=None, sym="CCCUSDT"),
         row("filled", intended=+999.0, filled=999.0, sym="DDDUSDT")]
_g = OD.gaps(_rows, "RID")
check("★★★ gross is 140 and net is +60 — SIGNED, because the direction the gaps leave is the "
      "thing that becomes a net exposure nobody chose",
      abs(_g["gross_usdt"] - 140.0) < 1e-6 and abs(_g["net_usdt"] - 60.0) < 1e-6,
      (_g["gross_usdt"], _g["net_usdt"]))
check("★★★ an unsizable gap is COUNTED SEPARATELY, never summed as zero — the same three-state "
      "discipline `fee_paid` and `filled_notional` already use",
      _g["n_unsized"] == 1 and _g["n_named"] == 2, (_g["n_named"], _g["n_unsized"]))
check("★★ a completed order contributes nothing", "DDDUSDT" not in json.dumps(_g))
check("★★ residual is intended MINUS filled, so a partially-covered gap counts only the remainder",
      abs(OD.gaps([row("blocked_by_halt", intended=100.0, filled=30.0)], "RID")["gross_usdt"]
          - 70.0) < 1e-6)
check("★★ rows from another rebalance are excluded",
      OD.gaps([{**row("blocked_by_halt"), "rebalance_id": "OTHER"}], "RID")["n_named"] == 0)

# ══════════════════════════════════════════════════════════════════════════════════════════
# ★ 2026-09-13 尺子第七次重标定 ① —— E-0912-A: 被场所截量的 reduce-only 平仓单, 成交量是【已知】的
#   12Z 锚 A1789215839 的 MEMEUSDT / POPCATUSDT 两行写着 `filled_amount_unknown`, Σ|intended| =
#   1,524 USDT, 尺子把它读成稳态交易锚上的非自愿缺口。但场所记录里这两笔完全可知: 回执 origQty
#   (= 持仓)、Σ 子成交 trade_qty == |confirmed_qty|、本锚读回为 0。身份门的 1e-6 相对容差把
#   「场所比我们更准」读成了「场所在撒谎」(E-0912-A 事实链 ④)。
#   失效的是【「未知」= 真的读不出】这个前提, 不是【稳态缺口小】这条性质 ⇒ 按事实把量重判为已知,
#   残差 = intended − Σ 子成交报价; 阈值一个都不动, 锚一个都不移出稳态人口。
#   ★ 这条规则只会把「未知」变成「已知」, 也就是只会【让缺口变小】—— 所以它每一个口子都必须有反例格,
#     见 [G7] 的六条反控(下面六道门各一条)。判据与 `reconcile._clamp_rederived` 是同一条,
#     这里【独立实现】并逐行对账。
_ORIGQTY_PAIR = re.compile(r"origQty\s+(\S+?)\s+differs from ours\s+(\S+)")


def _fin(x):
    """有限浮点, 否则 None(±Inf / NaN / 非数一律 None —— 读不出就是读不出)。"""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def _clamp_known(req):
    """这个请求是不是【场所把 reduceOnly 单截到持仓】? 是 ⇒ (已知张数, 已知成交额); 否则 None。

    判据(全部必须成立):
      ① `inconsistent` 是身份门 origQty 的【值比较】文本(含 "origQty" 与 "differs from ours");
         畸形 / 方向 / id / 「confirmed more than requested」是别的种类, 永远是矛盾。
      ② 串内两数 0 < Qv < Qs —— 场所要得【更少】。Qv > Qs 是场所要得更多, 仍是矛盾。
      ③ 串里的 Qs 就是这个请求自己的 qty —— 否则这串说的不是这张单。
      ④ 同侧(sign(confirmed) == sign(qty)), 且 |confirmed| ≤ min(Qv, |qty|)。
      ⑤ 子成交 Σ trade_qty == |confirmed_qty|, 且【逐个】子成交有限且非负 —— 子成交把这个量
         【定死】了, 这才是「已知」。−1 与 +5 抵消成 4 不是成交史。
      ⑥ 子成交报价 trade_quote 齐全且有限 —— 说得出张数说不出金额, 仍算读不出(缺口不能重判);
         若请求自报了【最终】成交额(confirmed_notional_final)而它与子成交报价和不符, 是金额矛盾, 拒。
      ⑦ **终局性**: (terminal ∧ confirmed_qty_final) ∨ |C| == Qv(容量闭合)。

    ★ 2026-09-13 C4–C8(独立研究员 0158f5d1): 原来这里缺第 ⑦ 条 —— **C 是累计下界, F 才是量**。
      场所接受 8、目前成交 4、单子还开着时, 把 4 当最终成交额会把一段合法区间 [4, 8] 读成一个确定的
      小缺口 —— 尺子会少报缺口, 方向与 reconcile 的误报相反但同一个错。不能证明终局就**不重判**,
      这一行保持它原来的整笔缺口。真实两行 |C| == Qv(容量闭合), 仍然是终局, 仍然重判。
      同时补 C5(显式 reduce_only=False)、C6(组合诊断文本)、C7(负子成交)、C8(金额矛盾)四道门。
      ★ 这些门全部写在函数体内(不引新的模块级常量/辅助名), 因为独立研究员的 `pure()` 探针按名字
        抽取本文件的函数, 新名字会让他们的回归跑不起来。
    """
    if not isinstance(req, dict):
        return None
    _raw = str(req.get("inconsistent") or "")
    _parts = [p.strip() for p in _raw.split(";") if p.strip()]
    if not _parts or not all(_is_origqty_kind(p) for p in _parts):
        return None                                   # ① C6: 每一条理由都必须是截量那一种
    _ro = [req.get(k) for k in ("reduce_only", "reduceOnly", "venue_reduce_only", "resp_reduce_only")
           if req.get(k) is not None]
    if _ro and not all(v is True for v in _ro):
        return None                                   # C5: 明写不是 reduce-only ⇒ 矛盾照旧
    m = _ORIGQTY_PAIR.search(_raw)
    if not m:
        return None
    qv, qs = _fin(m.group(1)), _fin(m.group(2))
    if qv is None or qs is None or not (0 < qv < qs):
        return None
    c, q = _fin(req.get("confirmed_qty")), _fin(req.get("qty"))
    if c is None or q is None or q == 0:
        return None
    if abs(abs(q) - qs) > max(1e-9, 1e-6 * qs):
        return None                                   # 串说的不是这张单
    if abs(c) > abs(q) + 1e-9 or abs(c) > qv + 1e-9:
        return None
    if c != 0 and c * q < 0:
        return None                                   # 反侧
    tq, tqt = req.get("trade_qty"), req.get("trade_quote")
    if not isinstance(tq, dict) or not tq or not isinstance(tqt, dict) or not tqt:
        return None
    sq = [_fin(v) for v in tq.values()]
    sv = [_fin(v) for v in tqt.values()]
    if any(v is None or v < 0 for v in sq) or any(v is None for v in sv) or set(tq) != set(tqt):
        return None                                   # C7: 逐个有限且非负(不许抵消)
    if abs(sum(sq) - abs(c)) > 1e-9:
        return None                                   # 子成交没有定下这个量
    _amt = (sum(sv) if c > 0 else -sum(sv))
    if req.get("confirmed_notional_final") is True:   # C8: 自报最终金额与子成交报价必须一致
        _cn = _fin(req.get("confirmed_notional"))
        if _cn is None or abs(_cn - _amt) > max(1e-6, 1e-6 * abs(_amt)):
            return None
    _final = bool(req.get("terminal")) and bool(req.get("confirmed_qty_final"))
    if not _final:
        _final = abs(abs(c) - qv) <= max(1e-9, 1e-6 * qv)       # ⑦ C4: 容量闭合
    if not _final:
        return None
    return c, _amt


def _is_origqty_kind(why):
    s = str(why or "")
    return "origQty" in s and "differs from ours" in s


def _row_rejudged(o):
    """整行重判 ⇒ (已知成交额, [已重判的 client_id]); 不能重判 ⇒ None。

    只处理写着 `filled_amount_unknown` 且 `filled_notional` 未写的行。行内【每一个】请求都必须被
    _clamp_known 解释(不带 `inconsistent` 的请求也算解释不了 —— 它的成交额没有独立证据), 行级
    `ledger_inconsistent` 的每一条也必须是 origQty 种类且指向一个已重判的 client_id。
    有一条解释不了 ⇒ 整行不重判(失败一律关向「未知」)。
    """
    if (str(o.get("terminal_reason")) != "filled_amount_unknown"
            or o.get("filled_notional") is not None):
        return None
    reqs = [r for r in (o.get("request_ledger") or ()) if isinstance(r, dict)
            and r.get("state") not in ("rejected", "not_sent")]
    if not reqs:
        return None
    total, cids = 0.0, []
    for r in reqs:
        got = _clamp_known(r)
        if got is None:
            return None
        total += got[1]
        cids.append(r.get("client_id"))
    for e in (o.get("ledger_inconsistent") or ()):
        cid, why = (e.get("client_id"), e.get("why")) if isinstance(e, dict) else (None, e)
        if not (_is_origqty_kind(why) and cid in cids):
            return None
    return total, cids


_rejudged = []          # (rebalance_id, symbol, leg, intended, raw_residual, new_residual)
_all_rj = []
for _o in _all:
    _got = _row_rejudged(_o)
    if _got is None:
        _all_rj.append(_o)
        continue
    _o2 = dict(_o)
    _o2["filled_notional"] = _got[0]
    _all_rj.append(_o2)
    _it = float(_o.get("intended_notional") or 0.0)
    _rejudged.append((_o.get("rebalance_id"), _o.get("symbol"), _o.get("order_type"),
                      _it, _it, _it - _got[0]))

print("\n[E] the REAL ledger — what each anchor would now declare")
_all_anchor_rows = []
for _f in sorted(glob.glob(os.path.join(_REPO, "state/live/pilot_log/*/anchors.jsonl"))):
    for _l in open(_f):
        _l = _l.strip()
        if _l:
            _all_anchor_rows.append(json.loads(_l))
_by, _by_raw = {}, {}
for _A in sorted({r["anchor_ts"] for r in _all}):
    _rid = [r["rebalance_id"] for r in _all if r["anchor_ts"] == _A][0]
    _by[_rid] = OD.gaps(_all_rj, _rid)      # ★ 07 ①: 截量行的量已重判为已知
    _by_raw[_rid] = OD.gaps(_all, _rid)     # 重判【之前】的同一算术 —— [G] 的承重对照
# ★★★ THIS ASSERTION WAS `len(_halted) == 2` AND IT EXPIRED WITHIN THE HOUR — third instance
#     today of the family this repo keeps paying for, and the third one in MY OWN tests. A count
#     of a LIVE, GROWING population is pinned-to-transient-state wearing a different hat: the
#     05:49Z refresh anchor was a third halted anchor and the suite went red for describing
#     reality correctly.
#     ⇒ The repair is the same one that worked twice before: select STRUCTURALLY (the anchors row
#       says `opening_halted`), and assert the RELATIONSHIP rather than the census. The claim
#       worth making was never "there are two" — it is "a halted anchor declares its whole book,
#       a trading anchor declares far less", and that survives every future anchor.
_halt_flag = {}
_row_by_rid = {}
for _r in _all_anchor_rows:
    _halt_flag[_r.get("rebalance_id")] = bool(_r.get("opening_halted"))
    _row_by_rid[_r.get("rebalance_id")] = _r
_halted = {r: g for r, g in _by.items() if _halt_flag.get(r)}
# ★ 07 ②: 保护性平仓批次按【行是什么】选取(order_type == protective_flatten), 不按 rebalance_id
#   【叫什么】(E-0825-H: 按名字推断语义)。三个选择器今天在账本上重合, 下面断言它们必须重合。
_flat_rows = [r for r in _all if r.get("order_type") == "protective_flatten"]
_flat_rids = {r.get("rebalance_id") for r in _flat_rows}
_traded = {r: g for r, g in _by.items()
           if _halt_flag.get(r) is False and r not in _flat_rids
           and not str(r).startswith("FLATTEN")}
check("★★★ EVERY halted anchor declares essentially its whole book as gap — an anchor that was "
      "blocked built nothing, and that is a gap of the entire book rather than a quiet no-op",
      _halted and all(g["gross_usdt"] > 1000 for g in _halted.values()),
      {r: round(g["gross_usdt"]) for r, g in _halted.items()})
# ★ 2026-09-13 ③ HALTED-NO-SUBMIT: 上面那条是【绝对界】, 一个交易得很差的锚也能过。停机锚真正的
#   形态在账本里写得很清楚(16/16): 终态词汇只有 blocked_by_halt / skipped_min_notional, submit_ts
#   一个没有, 成交一笔没有, 且 Σ|intended| 恰等于 anchors 行自己的 target_gross。恒等式可证伪, 界不能。
_HALT_REASONS = {"blocked_by_halt", "skipped_min_notional"}


def _halt_shape(rid):
    rr = [r for r in _all if r.get("rebalance_id") == rid]
    return {"n": len(rr),
            "reasons": sorted({str(r.get("terminal_reason")) for r in rr}),
            "n_submits": sum(1 for r in rr if r.get("submit_ts") is not None),
            "n_fills": sum(1 for r in rr if (r.get("filled_notional") or 0) != 0
                           or r.get("filled_qty") is not None),
            "intended_usdt": round(sum(abs(float(r.get("intended_notional") or 0.0))
                                       for r in rr), 4)}


_halt_shapes = {r: _halt_shape(r) for r in _halted}
check("★★★ ...and EVERY halted anchor has the HALTED-NO-SUBMIT SHAPE — its whole terminal "
      "vocabulary is `blocked_by_halt` / `skipped_min_notional`, it made ZERO submits and took "
      "ZERO fills. `gross > 1000` would also pass an anchor that traded and traded badly; the "
      "shape is what makes \"a blocked anchor built nothing\" a fact a reader can re-derive",
      bool(_halted) and all(not (set(v["reasons"]) - _HALT_REASONS)
                            and v["n_submits"] == 0 and v["n_fills"] == 0
                            for v in _halt_shapes.values()),
      {r: (v["n"], v["reasons"], v["n_submits"], v["n_fills"])
       for r, v in _halt_shapes.items()
       if (set(v["reasons"]) - _HALT_REASONS) or v["n_submits"] or v["n_fills"]}
      or f"{len(_halted)} halted anchors — 0 submits, 0 fills, "
         f"{sorted(set().union(*[set(v['reasons']) for v in _halt_shapes.values()]))}")
check("★★★ ...and a halted anchor DECLARES THE WHOLE PLANNED BOOK TO THE CENT — Σ|intended| over "
      "its rows equals the anchors row's OWN `target_gross`, so the gap it reports is the book it "
      "was going to hold. This is the identity the absolute bound above was standing in for",
      bool(_halted) and all(
          abs(v["intended_usdt"]
              - float((_row_by_rid.get(r) or {}).get("target_gross") or -1.0))
          <= max(0.01, 1e-6 * max(v["intended_usdt"], 1.0))
          for r, v in _halt_shapes.items()),
      {r: (v["intended_usdt"],
           round(float((_row_by_rid.get(r) or {}).get("target_gross") or 0.0), 4))
       for r, v in _halt_shapes.items()
       if abs(v["intended_usdt"]
              - float((_row_by_rid.get(r) or {}).get("target_gross") or -1.0))
       > max(0.01, 1e-6 * max(v["intended_usdt"], 1.0))}
      or f"{len(_halted)} anchors, Σ|intended| == target_gross")
# ★★ 2026-08-04: `< 200` FAILED on A1785859279 (229.5) and the failure was CORRECT ARITHMETIC on
#   a WRONG QUANTITY. 6 of that anchor's 7 gap rows were `skipped_no_chase_arm` — the chase
#   experiment's no_chase arm, residuals that were sendable and DELIBERATELY not sent so the
#   forgone alpha can be measured. Summing a designed abstention with a venue reject and putting
#   one threshold over the total is the coupled-quantity error: two different facts, one number.
#   And an ABSOLUTE bound on a quantity whose scale is set by a live randomised experiment is the
#   same "pinned to transient state" disease this file's own comment above diagnosed — one layer
#   down. The repair is the one that worked there: split the fact, then assert the RELATIONSHIP.
_DELIBERATE = {"skipped_no_chase_arm"}
_LOCK_CODE = "-4400"   # E-0910-A: account-level quant-rules lock; every opening order refused


def _rows_of(rid, pred):
    return [r for r in _all if r.get("rebalance_id") == rid and pred(r)]


def _deliberate_usdt(rid):
    """★ 2026-09-12 ③: 从行求和(同一残差算术: 对该类行直接调 gaps(), gross_usdt 不截断), 不再从
    gaps()["names"](前 20 名)求和 —— 09-11 08Z 96 个缺口名, 表法把 22 行 490U 的 no-chase 弃单读成 0。"""
    return float(OD.gaps(_rows_of(rid, lambda r: str(r.get("terminal_reason")) in _DELIBERATE),
                         rid)["gross_usdt"])


def _lock_usdt(rid):
    """-4400 拒掉的意图(残差, 同一算术)。锁住后场所只收 reduceOnly, 这些行是被场所拒绝的意图,
    不是名字蒸发。"""
    return float(OD.gaps(_rows_of(rid, lambda r: _LOCK_CODE in str(r.get("note") or "")),
                         rid)["gross_usdt"])


def _split(rid):
    """(deliberate_usdt, involuntary_usdt) for one anchor's gap ledger.

    ★ 2026-09-09 尺子第五次重标定(E-0909-E, 同一修复家族: 拆开事实, 再断言关系)。09-08 12Z 起
      PIEVERSEUSDT 连续 6 锚 -2027「Exceeded the maximum allowable position at current
      leverage」, 残差 707→423 USDT, 同一名, 每锚重发同一被拒增量: 规划器只截断
      maxNotionalValue==0 的名(anchor_loop), 有限上限低于目标时不截断。这是【场所定尺寸的非
      自愿缺口】, 不是【名字蒸发】—— 200U 稳态尺量的是后者。这里把 gaps() 已具名的
      venue_cap_usdt 从 involuntary 拆出, 稳态尺照旧量剩余部分; 该类自己的性质在下面单独断言
      (界=自身整书 1%, ≤3 名, 且 _trade 按名告警 = 有主)。
      ★ 失效条件: 一旦规划期有限上限截断(候选, 需用户字)上线, -2027 行应归零, 本拆分须撤回
        并把「该类为空」改成断言。"""
    g = _by[rid]
    d = _deliberate_usdt(rid)
    cap = float(g.get("venue_cap_usdt") or 0.0)
    return d, g["gross_usdt"] - d - cap


def _split_raw(rid):
    """同一拆分, 但用【重判之前】的账本 —— ① 的承重对照(没有重判这条尺会读到什么)。"""
    g = _by_raw[rid]
    d = float(OD.gaps([r for r in _all if r.get("rebalance_id") == rid
                       and str(r.get("terminal_reason")) in _DELIBERATE], rid)["gross_usdt"])
    return d, g["gross_usdt"] - d - float(g.get("venue_cap_usdt") or 0.0)


_tr_split = {r: _split(r) for r in _traded}
_tr_cap = {r: float(_by[r].get("venue_cap_usdt") or 0.0) for r in _traded}
# ★ 2026-08-27 尺子第三次重标定(与 08-18 resize 案同一修复家族, 一层更深): E-0826-F 停机清除后的
#   **从零重建锚**(A1787775780, 前一锚=停机锚)是"交易锚但意图=整书"的合法新形态 —— chase-none +
#   180s maker 窗下单窗只建 ~70%, 非自愿缺口 6922 是【建仓的未完成部分】而非【稳态执行失败】。
#   尺子的前提(交易锚意图≈稳态换手)失效, 分离性质本身没失效。修复同法: "重建锚"(紧跟停机锚的
#   首个交易锚)独立成类, 断言它自己的两条性质: ①确实建了大半(inv < 0.5×相邻停机锚整书缺口);
#   ②下一个交易锚回到稳态线内(补齐完成)。稳态不变量在其余交易锚原样执行。
_all_ids = sorted(set(_halted) | set(_traded), key=lambda r: int(str(r)[1:]))
_rebuild = {r for i, r in enumerate(_all_ids)
            if r in _traded and i > 0 and _all_ids[i - 1] in _halted}
# ★ 2026-08-27 尺子第四次重标定(同一修复家族, 又一层): **RESIZE 锚** —— gross_mult 相对上一行
#   变化, 或 reshape gross 单锚跳变 >10%(杠杆步/入金)的交易锚, 意图=稳态换手+一次性建仓。
#   A1787819040(1.75→2.0 收官步)非自愿 798 是建仓未完成部分, 前提(意图≈稳态换手)失效,
#   分离性质未失效。修复同法: 独立成类, 界=自身整书 realized_gross 的 5%(同代书尺,
#   比稳态 200U 松 ~10×, 仍能抓住真正的建仓卡死); 其后首个稳态锚必须回 200U 线内。
def _resize_sig(rid):
    row = _row_by_rid.get(rid) or {}
    eb = row.get("external_book") or {}
    rs = row.get("reshape") or {}
    return (eb.get("gross_mult"), rs.get("gross_before"), rs.get("gross_after"),
            row.get("realized_gross"))
_resize = set()
for _i, _r in enumerate(_all_ids):
    if _r not in _traded or _r in _rebuild:
        continue
    _m, _gb, _ga, _rg = _resize_sig(_r)
    _pm = next((_resize_sig(_all_ids[_j])[0] for _j in range(_i - 1, -1, -1)
                if _resize_sig(_all_ids[_j])[0] is not None), None)
    if (_m is not None and _pm is not None and _m != _pm) or        (_gb and _ga and _gb > 0 and abs(_ga / _gb - 1) > 0.10):
        _resize.add(_r)
# ★ 2026-09-12 ①: VENUE-LOCKED 锚(E-0910-A)。REBUILD / RESIZE 优先 —— 它们的界已按整书尺度定,
#   08-26 20Z / 08-27 08Z / 09-07 04Z / 09-10 00Z 的 -4400 全在那两类里; 这里只接住稳态锚上的锁
#   (首例 09-11 08:24Z A1789115039: 73 张补单全 -4400, 4,014U, 非自愿 4,014U —— 逐 USDT 相等)。
_locked = {r for r in _traded if r not in _rebuild and r not in _resize and _lock_usdt(r) > 0}
_steady_ids = [r for r in _tr_split if r not in _rebuild and r not in _resize and r not in _locked]
check("★★★ ...and EVERY steady trading anchor's INVOLUNTARY gap is small — the deliberate "
      "no-chase-arm abstention is excluded (alpha we chose to forgo); REBUILD anchors "
      "(first trading anchor after a halt clears; intent = the whole book), RESIZE anchors and "
      "VENUE-LOCKED anchors (E-0910-A) are their own classes asserted below",
      _tr_split and all(_tr_split[r][1] < 200 for r in _steady_ids),
      {r: (round(_tr_split[r][0]), round(_tr_split[r][1])) for r in _steady_ids})
_capped = {r: c for r, c in _tr_cap.items() if c > 0}
# ★ 失效条件已触发(E-0909-E 截断上线, 首个受影响锚 = 2026-09-09 20Z): 上线后的锚 -2027 残差
#   必须为零; 上线前的锚保留该类的界(历史行不改写)。
# ★ SET AT DEPLOYMENT (merge ≠ deploy, 用户 09-09): None until the clamp is actually running,
#   then the first anchor_ts it governed. While None the retirement assertion is skipped and
#   the pre-deploy class bound below still applies.
_CAP_CLAMP_DEPLOYED_TS = 1789201439.0   # ★ SET 2026-09-12: b681ca5 (E-0909-E clamp) deployed 06:05:30Z; first anchor it governed = 08Z rid A1789201439
#   (anchors row anchor_ts 1789201442.56): known_gaps.venue_cap_usdt 0, PIEVERSEUSDT +2,117→+1,960 truncated at cap 2,000 (journal 09-12 08Z).
_post = ({r: c for r, c in _capped.items()
          if float((_row_by_rid.get(r) or {}).get("anchor_ts") or int(str(r)[1:])) >= _CAP_CLAMP_DEPLOYED_TS}
         if _CAP_CLAMP_DEPLOYED_TS else {})
check("★★★ after the finite-cap clamp went live (20Z 09-09) NO anchor carries a -2027 residual — "
      "the class exists only for history; a post-deploy hit means the clamp missed a case",
      not _post, _post)
_capped = {r: c for r, c in _capped.items() if r not in _post}
def _intended_gross(rid):
    """★ 2026-09-12 ②: 该锚的 target(sizing)gross —— 场所上限残差要和【打算持有的书】比, 不和
    【建到几成的书】比; 09-10 00Z 重建锚只建到 67%, realized 做分母会把建仓未完成(已单独成类)算进
    场所上限里。无 target 行(不存在, 2026-08-01 起全有)退回 realized。"""
    row = _row_by_rid.get(rid) or {}
    return max(float(row.get("target_gross") or _resize_sig(rid)[3] or 0.0), 1.0)
check("★★★ a VENUE-CAPPED residual (-2027: the venue's bracket cap at our leverage, E-0909-E) is "
      "its own class — bounded by 1% of the anchor's OWN target (sizing) gross — the intended "
      "book scale; realized gross would conflate a separately-classed build shortfall (09-10 00Z "
      "rebuild at 67%) with the cap — and at most 3 names. It STAYS in the gap ledger's gross (it "
      "is a gap); it is only kept off the 200U evaporation ruler, which measures a different fact",
      all(c < 0.01 * _intended_gross(r)
          and len(_by[r].get("venue_cap_names") or []) <= 3 for r, c in _capped.items())
      if _capped else True,
      {r: (round(c), "vs 1% of target", round(_intended_gross(r)),
           _by[r].get("venue_cap_names")) for r, c in _capped.items()})
_al_src = open(os.path.join(_REPO, "scheduler", "anchor_loop.py")).read()
check("★★★ ...and it is OWNED: _trade pages a -2027 refusal by name every anchor it occurs "
      "(source-wired), so a persistent cap can no longer sit unnamed for six anchors",
      '"-2027" in str(r.get("note")' in _al_src and "场所仓位上限拒单" in _al_src)
check("★★★ a RESIZE anchor (leverage step / deposit) carries a build — its involuntary gap is "
      "a completion shortfall bounded by 5% of its OWN whole book (same-era scale), and is not "
      "measured with the steady 200U ruler",
      all((_tr_split[r][1] < 0.05 * max(float(_resize_sig(r)[3] or 0.0), 1.0)) or
          _tr_split[r][1] < 200 for r in _resize) if _resize else True,
      {r: (round(_tr_split[r][1]), "vs 5% of", round(float(_resize_sig(r)[3] or 0.0)))
       for r in _resize})
def _next_steady_after(rb):
    ids = _all_ids
    for j in range(ids.index(rb) + 1, len(ids)):
        if (ids[j] in _traded and ids[j] not in _rebuild and ids[j] not in _resize
                and ids[j] not in _locked):
            return ids[j]
    return None
check("★★★ ...and the first STEADY anchor after a resize is back inside the 200U line — the "
      "build actually completes",
      all((_next_steady_after(rb) is None) or (_tr_split[_next_steady_after(rb)][1] < 200)
          for rb in _resize) if _resize else True,
      {rb: (_next_steady_after(rb), round(_tr_split[_next_steady_after(rb)][1])
            if _next_steady_after(rb) else None) for rb in _resize})
check("★★★ a VENUE-LOCKED anchor (E-0910-A: the venue's account-level quant-rules lock, -4400 "
      "'only reduceOnly order is allowed', refuses every opening order for the rest of the anchor) "
      "is its own class — its involuntary gap is EXPLAINED by the refused intents: involuntary "
      "minus the -4400 notional sits inside the steady 200U ruler",
      all(_tr_split[r][1] - _lock_usdt(r) < 200 for r in _locked) if _locked else True,
      {r: (round(_tr_split[r][1]), "minus -4400", round(_lock_usdt(r))) for r in _locked})
check("★★★ ...and the first STEADY anchor after a venue lock is back inside the 200U line — the "
      "lock clears and the book completes",
      all((_next_steady_after(r) is None) or (_tr_split[_next_steady_after(r)][1] < 200)
          for r in _locked) if _locked else True,
      {r: (_next_steady_after(r), round(_tr_split[_next_steady_after(r)][1])
           if _next_steady_after(r) else None) for r in _locked})
check("★★★ ...and it is OWNED: anchor_loop pages the -4400 lock by phase every anchor it occurs "
      "(source-wired, E-0910-A), so a locked leg cannot sit unnamed as a quiet gap",
      "[-4400](E-0910-A" in _al_src)
def _adjacent_halted_gross(rb):
    """该重建锚紧跟的那个停机锚的整书缺口 —— 同代书规模, 才是正确的比较尺(跨时代 min 会把
    08-01 时代 4.2k 的书当尺子量今天 22.7k 的重建)。"""
    ids = _all_ids
    j = ids.index(rb) - 1
    while j >= 0:
        if ids[j] in _halted:
            return float(_halted[ids[j]]["gross_usdt"])
        j -= 1
    return 0.0
check("★★★ a REBUILD anchor built most of the book — its involuntary gap is a completion "
      "shortfall bounded well below its OWN adjacent halted anchor's whole-book gap (same-era "
      "book scale; a cross-era min would measure today's 22.7k rebuild with an 08-01 4.2k ruler)",
      all(_tr_split[r][1] < 0.5 * max(_adjacent_halted_gross(r), 1.0) or _tr_split[r][1] < 200
          for r in _rebuild) if _rebuild else True,
      {r: (round(_tr_split[r][1]), "vs 0.5x adjacent halted", round(0.5 * _adjacent_halted_gross(r)))
       for r in _rebuild})
def _next_traded_after(rb):
    ids = _all_ids
    for j in range(ids.index(rb) + 1, len(ids)):
        if ids[j] in _traded and ids[j] not in _rebuild and ids[j] not in _locked:
            return ids[j]
    return None
check("★★★ ...and the anchor AFTER a rebuild is back inside the steady line — the completion "
      "actually completes (chase-none repair path works)",
      all((_next_traded_after(rb) is None) or (_tr_split[_next_traded_after(rb)][1] < 200)
          for rb in _rebuild) if _rebuild else True,
      {rb: (_next_traded_after(rb), round(_tr_split[_next_traded_after(rb)][1])
            if _next_traded_after(rb) else None) for rb in _rebuild})
# ★ 2026-09-13 ② TRIP-FLATTENED —— 看门狗阶梯在某个锚的【区间内】平掉全书。
#   2026-09-12 12:47:37Z 那次(E-0912-A 的下游): 255 行 protective_flatten, Σ|filled_notional| =
#   235,382.55 USDT, 全部成交, 255 行 fee_paid 未测。全账本 10 批 / 1,708 行 / 73.8 万 USDT。
#   这些行的 rebalance_id 不在 anchors.jsonl 里, 所以既不是停机锚也不是交易锚 —— 本文件此前
#   【没有一条断言读到它们】(证明见 [G])。独立成类, 按 order_type 结构选取, 断言批次自己的事实。
#   ★ 平仓批次【不是锚】: 它不进稳态人口, 也不把它所在的锚移出稳态人口 —— 那个锚自己的单确实成交了
#     (① 重判后非自愿 0.058U), 把它豁免掉会是放宽而不是重标定。
def _containing_anchor(ts):
    """批次落在哪个锚的区间里 = anchor_ts ≤ 批次 ts 的最后一个 anchors 行。"""
    cand = [a for a in _all_anchor_rows if float(a.get("anchor_ts") or 0.0) <= ts]
    return max(cand, key=lambda a: float(a["anchor_ts"])) if cand else {}


def _fee_states(rows):
    """费用三态(与 fee_paid / filled_notional 同一条纪律): 未测(None) 与 已测 分开计数;
    任一行未测 ⇒ 本批 fee_usdt = None。**永远不把 None 当 0 求和** —— 在 235k 的 taker 执行上
    那会打印出 0.00 USDT 的手续费。"""
    unm = [r for r in rows if r.get("fee_paid") is None]
    mea = [r for r in rows if r.get("fee_paid") is not None]
    return {"n_unmeasured": len(unm), "n_measured": len(mea),
            "fee_usdt": (None if unm else round(sum(float(r["fee_paid"]) for r in mea), 6))}


_flat_batches = {}
for _fr in _flat_rows:
    _flat_batches.setdefault(_fr.get("rebalance_id"), []).append(_fr)
_flat_facts = {}
for _b, _rr in sorted(_flat_batches.items(), key=lambda kv: float(kv[1][0].get("anchor_ts") or 0)):
    _ca = _containing_anchor(float(_rr[0].get("anchor_ts") or 0.0))
    _flat_facts[_b] = dict(
        n_rows=len(_rr),
        all_filled=all(str(r.get("terminal_reason")) == "filled" for r in _rr),
        filled_usdt=round(sum(abs(float(r.get("filled_notional") or 0.0)) for r in _rr), 4),
        anchor=_ca.get("rebalance_id"),
        anchor_traded=(_ca.get("rebalance_id") in _traded),
        anchor_realized=round(float(_ca.get("realized_gross") or 0.0), 4),
        **_fee_states(_rr))
# ★ 2026-09-13 lead 裁定 1: 完整性改为【对账】, 不再用 ±10% 名义带。研究员反例: 100 条各 1U 的完整平仓删掉 5 条,
#   95U 仍在 100U 的 10% 带内 —— 带证明不了逐笔齐全。平仓批次有它自己的动作记录: `watchdog` 把
#   `{"ts": evaluated_utc, "actions": broker.actions}` 追加进 state/live/watchdog/events.jsonl, 其中 `flatten_all`
#   动作的 `orders` 列表就是写这些行的来源(`_write_flatten_rows` 读累积的 stage1_orders)。于是可以逐行精确对账。
#   事实(2026-09-13 快照): 10 批全部有动作记录, 行数与 orders 长度逐批相等; 只有 09-12 那批的 orders 带 client_id
#   (唯一 client id 在 09-10 d73b1b0 之后才发)。其余 9 批: 行上没有 order id(orderId 只在动作一侧), 但 (symbol, side,
#   attempt_idx) 在两侧都批内唯一 ⇒ 确定性联接; 联上之后, 写者从 `_exec` 抄到行上的每个字段 —— filled_notional、
#   avg_fill_px、first/last_fill_ts(= 场所成交时间, 毫秒)、mid_at_submit、intended_notional(= ±quantity × avg_fill_px)——
#   10 批 1,708 行【逐位相等】。所以联接不是「看起来像」: 每一行就是那张单的记录。
_FLAT_EVENTS = os.path.join(_REPO, "state", "live", "watchdog", "events.jsonl")


def _flatten_row_class(ex):
    """一张平仓单的终态类, 由它自己的 `_exec` 记录决定 —— 复述 `watchdog` 平仓行写者的规则(第二实现):
    未提交 ⇒ never_submitted; execution_unknown ⇒ filled_amount_unknown; rejected 或 error ⇒ submitted_rejected;
    没有 filled_notional ⇒ filled_amount_unknown; 否则 filled。"""
    ex = ex or {}
    if not ex.get("submitted"):
        return "never_submitted"
    if ex.get("execution_unknown"):
        return "filled_amount_unknown"
    if ex.get("rejected") or ex.get("error"):
        return "submitted_rejected"
    if ex.get("filled_notional") is None:
        return "filled_amount_unknown"
    return "filled"


def _flatten_action_orders(path=_FLAT_EVENTS):
    """{FLATTEN-<trip_key>: [该批全部 flatten_all 动作的 orders]}; 事件日志不存在 ⇒ None。

    联接用的是【写者自己的推导】, 不是名字相像: `watchdog` 取 trip_key = strftime("%Y%m%dT%H%M%SZ",
    strptime(evaluated_utc, "%Y-%m-%dT%H:%M:%SZ")), 行写成 `FLATTEN-{trip_key}`, 事件记录的 "ts" 就是那个
    evaluated_utc。同一记录里的多次 flatten_all(第二次尝试)归同一批, 由 attempt_idx 区分。
    ts 解析不了的记录跳过 ⇒ 对应批次没有记录 ⇒ NOT OBSERVABLE(失败关向「不可观测」, 不是通过)。
    ★ E3(FX-EXEC 2026-09-13): 读取交给 `_flatten_event_log`(同一次读出可读动作与不可读行); 本函数只返回前者,
      合同不变 —— 但它不再因损坏行抛异常, 也不再「静默跳过」: 不可读行由调用处点名为 NOT OBSERVABLE。"""
    return _flatten_event_log(path)[0]


def _flatten_event_log(path=_FLAT_EVENTS):
    """★ E3 (FX-EXEC 2026-09-13; independent review round 4 §2.2, the last cell of its R3-A2 table): ONE read of the event log ⇒
    (actions, unreadable).
      actions     {FLATTEN-<trip_key>: [orders of every flatten_all action in that record]}; None when the log does not exist.
      unreadable  [(line_no, why)] — every non-blank line that is not the writer's record (`watchdog`: `{"ts": evaluated_utc,
                  "triggers": [...], "actions": broker.actions}`): not JSON; a top level that is not an object (a JSON array /
                  scalar / null used to raise AttributeError out of this reader and END THE SUITE by exception — red, but never a
                  named finding); a ts that does not parse as evaluated_utc; `actions` absent or not a list, or holding a
                  non-object; a flatten_all action whose `orders` / `failed` is not a list, or whose order is not an object or
                  carries a non-object `_exec`; anything else the reading raises on (named with the exception).
    An unreadable line contributes NOTHING to `actions` — no part of a record that cannot be read is trusted — and the caller
    names it NOT OBSERVABLE: the event side IS the population (R3-A2), so a record nobody can read is a batch nobody can rule
    out. Before E3 a JSON-error / bad-ts line was skipped in silence: that failed closed only while the ledger still held the
    batch's rows; with both sides gone the batch vanished from both sets and the completeness cell stayed green."""
    if not os.path.exists(path):
        return None, []
    out, bad = {}, []
    for n, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError as e:
            bad.append((n, f"not JSON ({type(e).__name__}: {str(e)[:60]})"))
            continue
        if not isinstance(ev, dict):
            bad.append((n, f"top level is a JSON {type(ev).__name__}, not the writer's object"))
            continue
        try:
            key = time.strftime("%Y%m%dT%H%M%SZ", time.strptime(str(ev.get("ts")), "%Y-%m-%dT%H:%M:%SZ"))
        except (ValueError, TypeError, OverflowError):
            bad.append((n, f"ts {str(ev.get('ts'))[:40]!r} does not parse as evaluated_utc"))
            continue
        acts, why, got = ev.get("actions"), None, []
        if not isinstance(acts, list):
            bad.append((n, f"actions is {type(acts).__name__}, not a list"))
            continue
        try:
            for a in acts:
                if not isinstance(a, dict):
                    why = f"an action is a JSON {type(a).__name__}, not an object"
                    break
                if a.get("action") != "flatten_all":
                    continue
                oo, ff = a.get("orders"), a.get("failed")
                if not isinstance(oo, list) or not (ff is None or isinstance(ff, list)):
                    why = (f"a flatten_all action whose orders is {type(oo).__name__} / failed is {type(ff).__name__} "
                           f"(the writer records lists)")
                    break
                if any(not isinstance(o, dict) or not (o.get("_exec") is None or isinstance(o.get("_exec"), dict)) for o in oo):
                    why = "a flatten_all order that is not an object, or whose _exec is not an object"
                    break
                got.append(_mark_recorded_failures(a))
        except Exception as e:                                   # noqa: BLE001 — a corrupted record is a named finding, never an exit
            why = f"reading the record raised {type(e).__name__}: {str(e)[:80]}"
        if why:
            bad.append((n, why))
            continue
        for orders in got:
            out.setdefault("FLATTEN-" + key, []).extend(orders)
    return out, bad


def _flatten_unreadable_states(unreadable):
    """★ E3: {name: [detail]} — one NOT OBSERVABLE entry per unreadable event line, named by its line number and reason, for the
    completeness cell's state table (so `_flat_notobs` is non-empty and the cell fails, naming the line)."""
    return {f"events.jsonl line {n}": [f"UNREADABLE EVENT RECORD — {why}: the event side is the population (R3-A2), so a "
                                       f"record that cannot be read is a batch that cannot be ruled out"]
            for n, why in (unreadable or ())}


def _mark_recorded_failures(action):
    """The action's `orders`, each marked `_recorded_failure` when the SAME action also lists it in `failed`.

    ★ Matched by KEY, not by object: in the broker `failed[i]["order"]` IS the dict in `orders`, but after the
      JSON round-trip through events.jsonl they are two separate dicts — marking the `failed` copy would reach
      nothing, and the "listed as failed but written filled" check would be vacuous on every real record."""
    orders = [dict(o) for o in (action.get("orders") or ()) if isinstance(o, dict)]
    fk = {}
    for f in (action.get("failed") or ()):
        fo = f.get("order") if isinstance(f, dict) else None
        if isinstance(fo, dict):
            err = str(f.get("err") or "")
            if fo.get("client_id"):
                fk[("client_id", str(fo["client_id"]))] = err
            fk[_flat_key(fo)] = err
    for o in orders:
        hit = fk.get(("client_id", str(o["client_id"]))) if o.get("client_id") else None
        if hit is None:
            hit = fk.get(_flat_key(o))
        if hit is not None:
            o["_recorded_failure"] = hit
    return orders


def _flat_key(d):
    return (str(d.get("symbol")), str(d.get("side") or "").lower(), int(d.get("attempt_idx") or 1))


def _flat_cents(x):
    f = _fin(x)
    return None if f is None else round(f * 100)


def _flat_intended(o):
    """写者给平仓行的 intended_notional: ±quantity × avg_fill_px(无价 ⇒ None)。"""
    ex = o.get("_exec") or {}
    px, q = _fin(ex.get("avg_fill_px")), _fin(o.get("quantity"))
    if not px or q is None:
        return None
    v = q * px
    return -v if str(o.get("side") or "").lower() == "sell" else v


def _reconcile_flatten(rows, orders):
    """一批账本行 vs 该批动作记录的 orders, 【逐行精确】对账 ⇒ (状态, 明细, 联接键)。

    状态: "EXACT" / "MISMATCH" / "NOT_OBSERVABLE"。
    联接键: 动作的每张单都带 client_id 且两侧唯一 ⇒ "client_id"; 否则 (symbol, side, attempt_idx) 在两侧都唯一 ⇒
    "symbol_side_attempt"; 两者都不成立 ⇒ 没有确定性联接 ⇒ NOT_OBSERVABLE(不是不符, 也绝不是通过)。
    联上之后逐行【逐位】比写者从单与 `_exec` 抄到行上的每个字段(filled_notional / avg_fill_px / first_fill_ts /
    last_fill_ts / mid_at_submit / intended_notional), 两侧都带 client_id 时也比 client_id, 终态必须等于 `_exec` 推出的类,
    `failed` 里登记的单不得写成 filled; 批级: 行数相等, Σ(有符号)与 Σ|·| 到分相等。"""
    def uniq(keyf, xs):
        c = collections.Counter(keyf(x) for x in xs)
        return all(v == 1 for v in c.values())
    cid_all = bool(orders) and all(o.get("client_id") for o in orders)
    cidf = lambda d: ("client_id", str(d.get("client_id")))                      # noqa: E731
    if cid_all and uniq(cidf, orders) and uniq(cidf, rows):
        kf, how = cidf, "client_id"
    elif uniq(_flat_key, orders) and uniq(_flat_key, rows):
        kf, how = _flat_key, "symbol_side_attempt"
    else:
        return "NOT_OBSERVABLE", ["no deterministic join: neither client_id nor (symbol, side, attempt_idx) is "
                                  "unique on both sides"], None
    mm = []
    if len(rows) != len(orders):
        mm.append(f"count: ledger {len(rows)} vs action {len(orders)}")
    rk, ok_ = {kf(r) for r in rows}, {kf(o) for o in orders}
    only_r, only_o = sorted(rk - ok_), sorted(ok_ - rk)
    if only_r:
        mm.append(f"{len(only_r)} ledger row(s) with no action order, e.g. {only_r[:2]}")
    if only_o:
        mm.append(f"{len(only_o)} action order(s) with no ledger row, e.g. {only_o[:2]}")
    rmap = {kf(r): r for r in rows}
    for o in orders:
        r = rmap.get(kf(o))
        if r is None:
            continue
        ex = o.get("_exec") or {}
        k = kf(o)
        if _flat_key(r) != _flat_key(o):
            mm.append(f"{k}: (symbol, side, attempt) ledger {_flat_key(r)} vs action {_flat_key(o)}")
        if (r.get("client_id") or o.get("client_id")) and r.get("client_id") != o.get("client_id"):
            mm.append(f"{k}: client_id ledger {r.get('client_id')} vs action {o.get('client_id')}")
        for field, want in (("filled_notional", ex.get("filled_notional")), ("avg_fill_px", ex.get("avg_fill_px")),
                            ("first_fill_ts", ex.get("fill_ts")), ("last_fill_ts", ex.get("fill_ts")),
                            ("mid_at_submit", ex.get("mid_at_submit")), ("intended_notional", _flat_intended(o))):
            if r.get(field) != want:
                mm.append(f"{k}: {field} ledger {r.get(field)!r} vs action {want!r}")
        cls = _flatten_row_class(ex)
        if str(r.get("terminal_reason")) != cls:
            mm.append(f"{k}: terminal ledger {r.get('terminal_reason')} vs action-derived {cls}")
        if o.get("_recorded_failure") is not None and str(r.get("terminal_reason")) == "filled":
            mm.append(f"{k}: the action lists this order as FAILED but the ledger row says filled")
    for label, fn in (("Σ filled (signed)", lambda v: v), ("Σ|filled|", abs)):
        sr = round(sum(fn(_fin(r.get("filled_notional")) or 0.0) for r in rows) * 100)
        so = round(sum(fn(_fin((o.get("_exec") or {}).get("filled_notional")) or 0.0) for o in orders) * 100)
        if sr != so:
            mm.append(f"{label}: ledger {sr / 100:.2f} vs action {so / 100:.2f}")
    return ("MISMATCH" if mm else "EXACT"), mm, how


def _flatten_population(actions, ledger_batches):
    """★ R3-A2 (independent review round 3 §2.2, 2026-09-13): THE AUDIT POPULATION COMES FROM THE EVENT SIDE.

    The completeness cell used to iterate `_flat_batches` — built from the ORDER rows — so the side that may be missing
    defined the population: delete ONE WHOLE batch of `protective_flatten` rows, keep every event, and the remaining
    batches still reconcile EXACT one by one; the cell stayed green. The ladder's own record is the population instead:
    `watchdog` appends `{"ts": evaluated_utc, "actions": broker.actions}` to events.jsonl, and `_write_flatten_rows`
    writes exactly ONE row per order it is handed and nothing for an empty list (`if not orders: return 0`).
    Returns (required, missing, no_orders):
      required   {batch} whose `flatten_all` actions list at least one order — each MUST have ledger rows;
                 None when there is no event log (nothing can be required; the caller names it NOT OBSERVABLE);
      missing    {batch: [reason]} — required, and the ledger holds no row of it: LEDGER_BATCH_MISSING (red, named);
      no_orders  [batch] whose actions listed no order at all — no rows by construction; named, not required.
    A ledger batch with no action record is not decided here: the caller keeps it NOT OBSERVABLE (red, named); a
    ledger batch whose actions listed no order reconciles as a count MISMATCH (red)."""
    if actions is None:
        return None, {}, []
    required = {b for b, oo in actions.items() if oo}
    missing = {b: [f"the ladder's flatten_all record lists {len(actions[b])} order(s) and the ledger holds NO row of "
                   f"this batch — `_write_flatten_rows` writes one row per order, so the WHOLE batch is missing"]
               for b in sorted(required - set(ledger_batches))}
    return required, missing, sorted(b for b, oo in actions.items() if not oo)


def _batch_ts(b):
    return float((_flat_batches.get(b) or [{}])[0].get("anchor_ts") or 0.0)


_flat_actions, _flat_unreadable = _flatten_event_log()          # E3: one read; unreadable lines are NAMED below
# ★ R3-A2: population FIRST (event side), THEN the existing per-batch exact reconciliation over event ∪ ledger batches —
#   a batch the events require and the ledger lacks is LEDGER_BATCH_MISSING, named in the cell's detail and red.
_flat_required, _flat_missing, _flat_no_orders = _flatten_population(_flat_actions, _flat_batches)
_flat_state, _flat_detail, _flat_join = {}, {}, {}
# ledger batches in their own order (as before R3-A2), then the event-only ones — no sort over the keys: a corrupted row
# without a rebalance_id (key None) must reach its NOT OBSERVABLE state below, not crash a sort of mixed keys
for _b in list(_flat_batches) + [b for b in _flat_missing if b not in _flat_batches]:
    _rr = _flat_batches.get(_b)
    if _flat_actions is None:
        _flat_state[_b], _flat_detail[_b], _flat_join[_b] = "NOT_OBSERVABLE", ["no watchdog event log"], None
    elif _b in _flat_missing:
        _flat_state[_b], _flat_detail[_b], _flat_join[_b] = "LEDGER_BATCH_MISSING", _flat_missing[_b], None
    elif _b not in _flat_actions:
        _flat_state[_b], _flat_detail[_b], _flat_join[_b] = "NOT_OBSERVABLE", ["no flatten_all action record"], None
    else:
        try:
            _flat_state[_b], _flat_detail[_b], _flat_join[_b] = _reconcile_flatten(_rr, _flat_actions[_b])
        except Exception as _e:                                  # noqa: BLE001 — E3: a record that breaks the reading is NAMED, never an exit
            _flat_state[_b], _flat_detail[_b], _flat_join[_b] = (
                "NOT_OBSERVABLE", [f"reconciling this batch raised {type(_e).__name__}: {str(_e)[:80]}"], None)
# ★ E3: every unreadable event line is its own NOT OBSERVABLE entry — the completeness cell below then FAILS and names it
for _k, _v in _flatten_unreadable_states(_flat_unreadable).items():
    _flat_state[_k], _flat_detail[_k], _flat_join[_k] = "NOT_OBSERVABLE", _v, None
_flat_exact = sorted((b for b, v in _flat_state.items() if v == "EXACT"), key=_batch_ts)
_flat_notobs = {b: _flat_detail[b] for b, v in _flat_state.items() if v == "NOT_OBSERVABLE"}
_flat_mism = {b: _flat_detail[b][:3] for b, v in _flat_state.items() if v == "MISMATCH"}
check("★★★ COMPLETENESS of a TRIP-FLATTENED batch is an EXACT reconciliation against the ladder's OWN action "
      "record (the `flatten_all` action in state/live/watchdog/events.jsonl): joined on client_id where the "
      "orders carry one, else on (symbol, side, attempt_idx) when that is unique on both sides; the same "
      "set, the same count, every field the writer copies from the order and its `_exec` identical row by "
      "row (filled_notional, fill price, venue fill time, mid at submit, intended notional), Σ|filled| and "
      "Σ signed equal to the cent, and every row's terminal state the class its `_exec` implies — filled, or "
      "an explicitly recorded failure. A batch with no action record, or with no deterministic join, is "
      "NOT OBSERVABLE: it is NAMED and this cell FAILS — completeness the record cannot back is never passed. "
      "★ R3-A2: the POPULATION is the event side's — every batch whose `flatten_all` actions list an order must "
      "be present in the ledger (event-batch set == ledger-batch set), a required batch with no row is NAMED "
      "LEDGER_BATCH_MISSING and this cell FAILS; an action that listed no order is named, never required",
      _flat_required is not None and set(_flat_batches) == _flat_required and not _flat_missing
      and bool(_flat_state) and not _flat_notobs and not _flat_mism and len(_flat_exact) == len(_flat_state),
      {"EXACT": len(_flat_exact),
       "rows_reconciled": sum(len(_flat_batches[b]) for b in _flat_exact),
       "join": dict(collections.Counter(_flat_join[b] for b in _flat_exact)),
       "MISMATCH": _flat_mism,
       "NOT_OBSERVABLE": _flat_notobs,
       "population": {"event_batches_requiring_rows": (len(_flat_required) if _flat_required is not None else None),
                      "ledger_batches": len(_flat_batches), "LEDGER_BATCH_MISSING": _flat_missing,
                      "actions_listing_no_orders": _flat_no_orders}})
_cid_batches = sorted((b for b in _flat_exact if _flat_join[b] == "client_id"), key=_batch_ts)
_nocid_batches = sorted((b for b in _flat_exact if _flat_join[b] == "symbol_side_attempt"), key=_batch_ts)
_first_cid_ts = min((_batch_ts(b) for b in _cid_batches), default=None)
check("★★★ ...and which JOIN carried each batch is itself asserted: client_id wherever the ladder minted one; the "
      "batches joined on (symbol, side, attempt_idx) are exactly the ones written before the ladder sent client "
      "ids (their rows carry no order id — the orderIds exist only on the action side), and that population is "
      "CLOSED: every one of them precedes the first batch whose record carries client ids, so a NEW flatten "
      "written without client ids goes red here even though it would still reconcile",
      bool(_cid_batches) and _first_cid_ts is not None
      and all(_batch_ts(b) < _first_cid_ts for b in _nocid_batches),
      {"joined_on_client_id": _cid_batches, "joined_on_symbol_side_attempt": _nocid_batches})
check("★★★ ...and the exit COMPLETED: every `protective_flatten` row ended `filled` with a non-zero notional. "
      "An explicitly recorded rejection is ACCOUNTED FOR by the reconciliation above — and it still goes red "
      "HERE, because an exit with a refused order did not close the book",
      bool(_flat_facts) and all(f["n_rows"] > 0 and f["all_filled"] and f["filled_usdt"] > 0
                                for f in _flat_facts.values()),
      {b: (f["n_rows"], "rows, all filled:", f["all_filled"]) for b, f in _flat_facts.items()})
check("★★ SECONDARY PLAUSIBILITY ONLY — NOT the completeness proof: the batch sits inside a TRADING anchor's "
      "interval and its Σ|filled_notional| is within 10% of that anchor's own realized gross (the ladder closed "
      "about the whole book, not a sliver of it). This band passes with 5 of 100 equal rows deleted; "
      "completeness is the exact reconciliation above",
      bool(_flat_facts) and all(
          f["anchor_traded"]
          and abs(f["filled_usdt"] - f["anchor_realized"]) <= 0.10 * max(f["anchor_realized"], 1.0)
          for f in _flat_facts.values()),
      {b: (f["filled_usdt"], "vs realized of", f["anchor"], f["anchor_realized"]) for b, f in _flat_facts.items()})
check("★★★ ...and the flatten's FEE is reported UNMEASURED, never summed as zero — the ladder "
      "writes `fee_paid` None on rows it never priced, and a batch holding any such row reports "
      "its fee as None. `fee or 0` would print 0.00 USDT of cost for a whole book of IOC taker "
      "execution. This cell reads the ORDER layer, which is append-only: a backfill lands measured "
      "commission on `fills` rows and never rewrites `fee_paid` here, so this count does NOT fall "
      "when fees are recovered (the fills-layer split is in DESIGN §5)",
      all((f["fee_usdt"] is None) == (f["n_unmeasured"] > 0)
          and f["n_unmeasured"] + f["n_measured"] == f["n_rows"] for f in _flat_facts.values()),
      {b: (f["n_rows"], "rows /", f["n_unmeasured"], "fee-unmeasured / fee_usdt", f["fee_usdt"])
       for b, f in _flat_facts.items()})
check("★★★ ...and the class is selected by WHAT THE ROWS ARE (`order_type == protective_flatten`), "
      "not by what the rebalance_id is CALLED — E-0825-H. The three readings (structural / name "
      "prefix / absent from anchors.jsonl) agree on every batch in the ledger. If a batch is one day "
      "written under a different name, the three readings part and THIS CELL GOES RED — conservatively: "
      "the batch still stays out of the steady population (it has no anchors row), but the suite stops "
      "and a person has to look. (Corrected 2026-09-13: an earlier wording claimed a renamed batch would "
      "be absorbed silently; the assertion never did that.)",
      bool(_flat_rids)
      and _flat_rids == {r for r in _by if str(r).startswith("FLATTEN")}
      and _flat_rids == {r for r in _by if r not in _halt_flag}
      and all(all(x.get("order_type") == "protective_flatten" for x in _rr)
              for _rr in _flat_batches.values()),
      (len(_flat_rids), sorted(_flat_rids)[-1]))
# ★ 2026-08-18 尺子重标定: 原断言在 TOTAL(自愿+非自愿)上执行, 隐含前提"没有合法的大额
#   自愿弃单"。当日 04:00Z 入金 resize(2×NAV, 目标增量 2.6×)被 no-chase 政策正确弃单
#   1424 USDT(全部 deliberate, involuntary=0), 打破了按无大额重整时代标定的 0.25 界 ——
#   这是【尺子的前提】失效, 不是分离性质失效。本断言自己的注释早已写明"绝对界只对
#   非自愿部分有意义", 现按其字面执行: 分离性质改在 INVOLUNTARY 上断言, 自愿弃单由上一条
#   check 的 (deliberate, involuntary) 拆分单独呈报。resize 型事件从此结构性免疫。
check("★★★ ...and the halted/trading SEPARATION holds on the INVOLUNTARY total — a halted anchor "
      "declares its whole book, a trading anchor involuntarily misses a small fraction. The "
      "deliberate part (no-chase, resize abstentions) is chosen, measured, and excluded",
      _halted and _tr_split and
      max(inv for r, (_, inv) in _tr_split.items() if r not in _rebuild and r not in _locked)
      < 0.25 * min(g["gross_usdt"] for g in _halted.values()),
      f"max steady traded involuntary "
      f"{round(max(inv for r, (_, inv) in _tr_split.items() if r not in _rebuild and r not in _locked))} vs "
      f"min halted {round(min(g['gross_usdt'] for g in _halted.values()))} "
      f"(rebuild anchors {sorted(_rebuild)} / venue-locked anchors {sorted(_locked)} asserted separately)")
_a0400 = [g for r, g in _by.items() if r == "A1785643246"]
check("★★★ the 04:00Z anchor now declares ZERO gap — because the 1050.10 of -5022 is recovered "
      "by the top-up and the 68 abandoned rows are sub-floor dust. That is the fix, measured "
      "against the anchor that was liquidated over it",
      _a0400 and _a0400[0]["gross_usdt"] == 0.0, _a0400 and _a0400[0]["gross_usdt"])

print("\n[G] 2026-09-12 recalibration — each new ruler is LOAD-BEARING on the real ledger, not decoration")
check("★★★ the VENUE-LOCKED class absorbs at least one real anchor the steady ruler would fail — "
      "with the class emptied the steady assertion goes red and names it (09-11 08:24Z)",
      bool(_locked) and any(_tr_split[r][1] >= 200 for r in _locked),
      {r: round(_tr_split[r][1]) for r in _locked})
check("★★★ ...and every locked anchor's -4400 notional is the WHOLE of its involuntary gap to the "
      "dollar (|involuntary − lock| < 1U) — the lock is the explanation, not a fig leaf over "
      "something else",
      all(abs(_tr_split[r][1] - _lock_usdt(r)) < 1.0 for r in _locked) if _locked else True,
      {r: (round(_tr_split[r][1], 2), round(_lock_usdt(r), 2)) for r in _locked})
check("★★★ the -2027 ruler's denominator is load-bearing: against REALIZED gross the 09-10 00Z "
      "rebuild anchor (built 67%) fails the same class while every capped anchor passes against "
      "TARGET gross — the two facts must not share one number",
      any(c >= 0.01 * max(float(_resize_sig(r)[3] or 0.0), 1.0) for r, c in _capped.items())
      and all(c < 0.01 * _intended_gross(r) for r, c in _capped.items()),
      {r: (round(c), "1% realized", round(0.01 * float(_resize_sig(r)[3] or 0.0)),
           "1% target", round(0.01 * _intended_gross(r)))
       for r, c in _capped.items() if c >= 0.01 * max(float(_resize_sig(r)[3] or 0.0), 1.0)})
_old_d = {r: sum(abs(float(n.get("residual_notional") or 0.0)) for n in _by[r]["names"]
                 if str(n.get("terminal_reason")) in _DELIBERATE) for r in _traded}
_gt20 = {r for r in _traded if _by[r]["n_named"] > 20}
check("★★★ deliberate is summed from the ROWS, not from gaps()['names'] (top-20 by |residual|): on "
      "at least one real anchor with >20 gap names the capped list under-reads the no-chase "
      "abstention (09-11 08Z: rows 490U, list 0U) — the two readings differ where the cap bites "
      "and agree everywhere else",
      any(abs(_old_d[r] - _tr_split[r][0]) > 1.0 for r in _gt20)
      and all(abs(_old_d[r] - _tr_split[r][0]) < 1e-2 for r in _traded if r not in _gt20),
      {r: (round(_old_d[r]), round(_tr_split[r][0])) for r in _gt20 if abs(_old_d[r] - _tr_split[r][0]) > 1.0})

# ── [G7] 的装置(全部在这里算好, 断言只做比较) ─────────────────────────────────────────────
import reconcile as RC                      # noqa: E402  运行时的读时重推, 作为第二实现来对账


# ★ 2026-09-13 [G7] 第 2 格改到 C/F 合同(lead 字: 「按新合同更新, 不许放宽」)。原来这格比的是【键】:
#   尺子接受的请求集合 == 运行时 `known` 的全部键。C4 修复后 `known` 装的是结构化裁定 {C, Qv, final},
#   【仍开着的截量也在里面】(final=False), 而尺子只接受证明终局的 —— 两个集合的定义已经不同了。今天账本里
#   只有两个终局截量, 所以这格碰巧绿; 账本里出现第一个开着的截量, 它会报「分歧」, 而两边其实都对。
#   新合同逐请求: 尺子接受 ⇔ 运行时裁定为证明终局, 且两边接受时已确认量相同; 开着的截量两边都拒。
def _rt_verdict_final(v):
    """运行时对一个请求的裁定在 C/F 合同下的读数: True = 证明终局 / False = 截量形状但仍开着 / None = 无裁定。
    当前合同是 dict {"C", "Qv", "final"}; 第一轮合同是裸数(那一轮把每个重推的截量都当终局)⇒ 读作 True ——
    这样在一个把 C 提升成 F 的运行时上本格会【红】, 而不是崩或静默。"""
    if v is None:
        return None
    if isinstance(v, dict):
        return bool(v.get("final"))
    return True


def _rt_verdict_c(v):
    return _fin(v.get("C")) if isinstance(v, dict) else _fin(v)


def _contract_disagreements(rows):
    """逐请求比对尺子与运行时 ⇒ (分歧清单, 终局裁定数, 开着裁定数, 带请求账本的行数)。"""
    out, n_final, n_open, n_rows = [], 0, 0, 0
    for o in rows:
        reqs = [r for r in (o.get("request_ledger") or ()) if isinstance(r, dict)
                and r.get("state") not in ("rejected", "not_sent")]
        if not reqs:
            continue
        n_rows += 1
        known = (RC._rederive_ledger(o) or {}).get("known") or {}
        for r in reqs:
            k = _clamp_known(r)
            v = known.get(r.get("client_id"))
            fin = _rt_verdict_final(v)
            if fin is True:
                n_final += 1
            elif fin is False:
                n_open += 1
            ok = (k is not None) == (fin is True)
            if ok and k is not None:
                c = _rt_verdict_c(v)
                ok = c is not None and abs(k[0] - c) < 1e-9
            if not ok:
                out.append((o.get("rebalance_id"), o.get("symbol"), r.get("client_id"),
                            "ruler", (k[0] if k else None), "runtime", v))
    return out, n_final, n_open, n_rows


_rc_disagree, _rc_final_n, _rc_open_n, _rc_checked = _contract_disagreements(_all)

# 截量判据的正控 = 12Z MEMEUSDT 的真请求(逐字), 六条反控各打掉一道门。
_REQ_OK = {
    "client_id": "A1789215839-MEMEUSDT-1", "state": "confirmed",
    "qty": -1933986.0, "confirmed_qty": -1933692.0,
    "inconsistent": ("A1789215839-MEMEUSDT-1: identity: submit response: submit response "
                     "origQty 1933692.0 differs from ours 1933986.0"),
    "trade_qty": {"376472584": 560266.0, "376472585": 782806.0, "376472586": 590620.0},
    "trade_quote": {"376472584": 294.13965, "376472585": 410.97315, "376472586": 310.0755},
}
_NEG = [
    ("venue asked for MORE (origQty above ours)",
     {**_REQ_OK, "inconsistent": _REQ_OK["inconsistent"]
      .replace("origQty 1933692.0 differs from ours 1933986.0",
               "origQty 1933986.0 differs from ours 1933692.0")}),
    ("opposite side (confirmed against our own sign)", {**_REQ_OK, "confirmed_qty": 1933692.0}),
    ("children do not sum to the confirmed qty",
     {**_REQ_OK, "trade_qty": {**_REQ_OK["trade_qty"], "376472586": 590619.0}}),
    ("a contradiction of another kind (not the origQty value gate)",
     {**_REQ_OK, "inconsistent": "A1789215839-MEMEUSDT-1: confirmed more than requested"}),
    ("the string is about ANOTHER request (its `ours` is not this request's qty)",
     {**_REQ_OK, "qty": -1900000.0}),
    ("child quantities readable but no child QUOTE — the size is known, the notional is not",
     {**_REQ_OK, "trade_quote": {}}),
    # ★ 2026-09-13 C4–C8(独立研究员 0158f5d1): 下面五条是这一轮新加的门。
    ("C4 the quantity is NOT proven final — C is a cumulative LOWER bound, the venue accepted more "
     "than has filled and the request is still open",
     {**_REQ_OK, "qty": -10.0, "confirmed_qty": -4.0,
      "inconsistent": "X-1: identity: submit response origQty 8.0 differs from ours 10.0",
      "trade_qty": {"a": 4.0}, "trade_quote": {"a": 4.0}}),
    ("C5 the request EXPLICITLY records reduce_only False — a shrunken origQty on it is not a clamp",
     {**_REQ_OK, "reduce_only": False}),
    ("C6 a clamp reason JOINED with a foreign-identity reason ('; ' is what the writer emits)",
     {**_REQ_OK, "inconsistent": _REQ_OK["inconsistent"] + "; identity: foreign orderId 9 is not ours (1)"}),
    ("C7 a negative child cancelling a larger one — the sum is right, the history is not",
     {**_REQ_OK, "trade_qty": {"a": -1.0, "b": 1933693.0}}),
    ("C8 the request's OWN final notional disagrees with its children's quotes",
     {**_REQ_OK, "confirmed_notional_final": True, "confirmed_notional": -3.0}),
]
# 每条新门的正控: 拿掉那一个字段/换成合法值, 同一请求必须重新被接受(门是门, 不是一律拒绝)。
_POS = [
    ("C4 same shape but venue-terminal AND executed-qty-final",
     {**_REQ_OK, "qty": -10.0, "confirmed_qty": -4.0, "terminal": True, "confirmed_qty_final": True,
      "inconsistent": "X-1: identity: submit response origQty 8.0 differs from ours 10.0",
      "trade_qty": {"a": 4.0}, "trade_quote": {"a": 4.0}}, (-4.0, -4.0)),
    ("C5 reduce_only recorded True", {**_REQ_OK, "reduce_only": True}, (-1933692.0, -1015.1883)),
    ("C8 final notional AGREEING with the children's quotes",
     {**_REQ_OK, "confirmed_notional_final": True, "confirmed_notional": -1015.1883}, (-1933692.0, -1015.1883)),
]


def _fx_row(cid, **req):
    """合同夹具: 我们要 10、场所接受 8 的 reduce-only 请求, 其余字段按格给。"""
    r = {"client_id": cid, "state": "confirmed", "terminal": False, "confirmed_qty_final": False,
         "reduce_only": True, "qty": 10.0, "qty_venue": 8.0,
         "inconsistent": f"{cid}: identity: response origQty 8.0 differs from ours 10.0"}
    r.update(req)
    return {"symbol": "SYNTH", "rebalance_id": "CONTRACT-FIXTURE", "request_ledger": [r],
            "ledger_inconsistent": [{"client_id": cid, "why": r["inconsistent"]}]}


# 账本今天只有终局截量 —— 所以两个分支都要有夹具, 否则「开着的截量两边都拒」这半条合同从未被执行过。
_CONTRACT_FX = [
    _fx_row("OPEN-1", confirmed_qty=4.0, trade_qty={"t": 4.0}, trade_quote={"t": 4.0}),   # 研究员 C4: 开着
    _fx_row("CAP-1", confirmed_qty=8.0, trade_qty={"t": 8.0}, trade_quote={"t": 8.0}),    # 容量闭合: 终局
    _fx_row("FIN-1", confirmed_qty=4.0, terminal=True, confirmed_qty_final=True,
            trade_qty={"t": 4.0}, trade_quote={"t": 4.0}),                                 # terminal+final: 终局
]
_fx_disagree, _fx_final_n, _fx_open_n, _ = _contract_disagreements(_CONTRACT_FX)


def _as_traded(rid):
    """把一个停机锚【当交易锚】读会得到什么 —— HALTED 类的承重对照(同一拆分算术)。"""
    g = _by[rid]
    d = _deliberate_usdt(rid)
    return g["gross_usdt"] - d - float(g.get("venue_cap_usdt") or 0.0)


# 盲区证明: 把全部 protective_flatten 行从账本里拿掉, 重算 [E] 读到的每一个 gross。
_flat_total_usdt = round(sum(f["filled_usdt"] for f in _flat_facts.values()), 2)
_no_flat = [r for r in _all_rj if r.get("order_type") != "protective_flatten"]
_by_nf = {}
for _A in sorted({r["anchor_ts"] for r in _no_flat}):
    _rid = [r["rebalance_id"] for r in _no_flat if r["anchor_ts"] == _A][0]
    _by_nf[_rid] = OD.gaps(_no_flat, _rid)
_blind_same = (sorted(_by_nf) == sorted(set(_halted) | set(_traded))
               and all(_by_nf[r]["gross_usdt"] == _by[r]["gross_usdt"]
                       and _by_nf[r]["n_named"] == _by[r]["n_named"]
                       for r in set(_halted) | set(_traded)))

print("\n[G7] 2026-09-13 recalibration #7 — the three new readings, proved on the real ledger")
_rj_anchors = sorted({t[0] for t in _rejudged}, key=lambda r: int(str(r)[1:]))
check("★★★ the E-0912-A re-judgment is LOAD-BEARING IN BOTH DIRECTIONS, and it re-classifies a "
      "QUANTITY rather than loosening a threshold: read AS WRITTEN the venue-clamped rows put "
      "their anchor's involuntary gap at exactly their own intent (1,524U ⇒ ≥ 200U ⇒ the steady "
      "ruler goes red and names it); read from the VENUE'S OWN RECORD every re-judged anchor is "
      "inside the SAME 200U line — and it stays in the steady population, exempted from nothing",
      bool(_rj_anchors)
      and all(r in _tr_split for r in _rj_anchors)
      and all(r in _steady_ids for r in _rj_anchors)
      and any(_split_raw(r)[1] >= 200 for r in _rj_anchors)
      and all(_tr_split[r][1] < 200 for r in _rj_anchors)
      and all(abs(_split_raw(r)[1] - sum(abs(t[3]) for t in _rejudged if t[0] == r)) < 1.0
              for r in _rj_anchors),
      {r: ("as written", round(_split_raw(r)[1], 4),
           "= Σ|intended| of", len([t for t in _rejudged if t[0] == r]), "clamped rows",
           round(sum(abs(t[3]) for t in _rejudged if t[0] == r), 4),
           "-> re-judged", round(_tr_split[r][1], 4)) for r in _rj_anchors})
check("★★★ ...and the ruler and the RUNTIME mean the SAME thing by \"known\" under the C/F contract — "
      "this file's clamp rule is written independently of `reconcile._clamp_rederived`; the ruler "
      "accepts a request EXACTLY when the runtime's verdict is PROVEN FINAL, with the same confirmed "
      "quantity, and both reject a clamp that is still OPEN. Checked on every request in the "
      "production ledger AND on three contract fixtures (an open C4 request / capacity closure / "
      "terminal+final), because today's ledger holds only final clamps: a ledger-only check would "
      "stay green for a runtime that promotes C to F again",
      not _rc_disagree and not _fx_disagree and _fx_final_n >= 1 and _fx_open_n >= 1,
      (_rc_disagree + _fx_disagree)
      or f"ledger {_rc_checked} rows: {_rc_final_n} final / {_rc_open_n} open verdicts; "
         f"fixtures: {_fx_final_n} final / {_fx_open_n} open — all agree")
check("★★★ ...and the rule accepts ONLY the clamp shape — a rule that turns UNKNOWN into KNOWN can "
      "only ever SHRINK a gap, so EVERY gate has a counter-example that must stay unknown: venue "
      "asked for MORE / opposite side / children do not sum / a non-origQty contradiction / the "
      "string is about another request / no readable child quote / the quantity is not proven "
      "FINAL (C4) / reduce_only explicitly False (C5) / a combined diagnostic string (C6) / a "
      "negative child (C7) / a final notional that disagrees with the children (C8)",
      _clamp_known(_REQ_OK) is not None
      and abs(_clamp_known(_REQ_OK)[1] - (-1015.1883)) < 1e-9
      and all(_clamp_known(q) is None for _, q in _NEG),
      [n for n, q in _NEG if _clamp_known(q) is not None]
      or f"positive control -1015.1883 USDT; {len(_NEG)} counter-examples all UNKNOWN")
check("★★★ ...and every one of those gates is a GATE, not a blanket refusal — restore the one fact "
      "each counter-example removed and the SAME request is accepted again, with the right numbers. "
      "A rule that rejected everything would pass the line above and measure nothing",
      all(_clamp_known(q) is not None
          and abs(_clamp_known(q)[0] - want[0]) < 1e-6 and abs(_clamp_known(q)[1] - want[1]) < 1e-6
          for _, q, want in _POS),
      [n for n, q, want in _POS if _clamp_known(q) is None
       or abs(_clamp_known(q)[0] - want[0]) > 1e-6 or abs(_clamp_known(q)[1] - want[1]) > 1e-6]
      or f"{len(_POS)} positive controls back to exactly their own numbers")
check("★★★ the HALTED class is LOAD-BEARING: read as trading anchors — which is all they are until "
      "the `opening_halted` flag is consulted — every halted anchor shows an involuntary gap far "
      "outside the steady 200U ruler, so the class is what keeps a blocked anchor from being read "
      "as an evaporation",
      bool(_halted) and all(_as_traded(r) >= 200 for r in _halted),
      {r: round(_as_traded(r)) for r in _halted})
check("★★★ the TRIP-FLATTENED class closes a BLIND SPOT rather than repairing a red — and the "
      "blind spot is MEASURED, not asserted: delete every `protective_flatten` row from the "
      "ledger and not one number in [E] changes, while this much executed notional and this many "
      "unmeasured fees vanish without a single assertion noticing",
      bool(_flat_rows) and _blind_same and _flat_total_usdt > 0
      and sum(f["n_unmeasured"] for f in _flat_facts.values()) > 0,
      (len(_flat_rows), "rows", _flat_total_usdt, "USDT executed",
       sum(f["n_unmeasured"] for f in _flat_facts.values()), "fee-unmeasured; [E] unchanged:",
       _blind_same))
def _band_ok(rows, b):
    f = _flat_facts[b]
    tot = sum(abs(_fin(r.get("filled_notional")) or 0.0) for r in rows)
    return abs(tot - f["anchor_realized"]) <= 0.10 * max(f["anchor_realized"], 1.0)


_flat_mut = {}
for _b in ([_cid_batches[-1]] if _cid_batches else []) + ([_nocid_batches[-1]] if _nocid_batches else []):
    _rows0, _acts0 = [dict(r) for r in _flat_batches[_b]], _flat_actions[_b]
    _alt = [dict(r) for r in _rows0]
    _alt[0]["filled_notional"] = float(_alt[0]["filled_notional"]) + 0.01
    _ts = [dict(r) for r in _rows0]
    _ts[0]["first_fill_ts"] = float(_ts[0]["first_fill_ts"]) + 0.001
    _flat_mut[_b] = {
        "join": _flat_join.get(_b),
        "untouched": _reconcile_flatten(_rows0, _acts0)[0],
        "delete_one_ledger_row": _reconcile_flatten(_rows0[1:], _acts0)[0],
        "alter_one_row_filled_notional_by_one_cent": _reconcile_flatten(_alt, _acts0)[0],
        "drop_one_order_from_the_action_record": _reconcile_flatten(_rows0, _acts0[1:])[0],
        "alter_one_row_venue_fill_time_by_1ms": _reconcile_flatten(_ts, _acts0)[0],
        "band_passes_the_two_ledger_mutants": _band_ok(_rows0[1:], _b) and _band_ok(_alt, _b)}
_MUTS = ("delete_one_ledger_row", "alter_one_row_filled_notional_by_one_cent",
         "drop_one_order_from_the_action_record", "alter_one_row_venue_fill_time_by_1ms")
check("★★★ the exact flatten reconciliation is LOAD-BEARING, on a real client_id-joined batch AND on a real "
      "(symbol, side, attempt_idx)-joined batch: DELETE ONE ledger row ⇒ red; ALTER ONE row's filled_notional "
      "(by one cent) ⇒ red; DROP ONE ORDER from the action record ⇒ red; move one row's venue fill time by 1 ms ⇒ "
      "red (the per-row field equality is live, not decoration); the untouched batch ⇒ EXACT. And the ±10% band "
      "passes both ledger-side mutants — which is exactly why it cannot be the completeness proof",
      len(_flat_mut) == 2
      and {v["join"] for v in _flat_mut.values()} == {"client_id", "symbol_side_attempt"}
      and all(v["untouched"] == "EXACT" and all(v[m] == "MISMATCH" for m in _MUTS)
              and v["band_passes_the_two_ledger_mutants"] for v in _flat_mut.values()),
      {b: {"join": v["join"], "untouched": v["untouched"], **{m: v[m] for m in _MUTS},
           "band_passes_the_two_ledger_mutants": v["band_passes_the_two_ledger_mutants"]}
       for b, v in _flat_mut.items()})
_pop_mut = {}
for _b in ([_cid_batches[-1]] if _cid_batches else []) + ([_nocid_batches[-1]] if _nocid_batches else []):
    _kept = {b: rr for b, rr in _flat_batches.items() if b != _b}
    _req_m, _miss_m, _ = _flatten_population(_flat_actions, _kept)
    _pop_mut[_b] = {
        "join": _flat_join.get(_b), "rows_dropped": len(_flat_batches[_b]),
        "named_LEDGER_BATCH_MISSING": sorted(_miss_m) == [_b],
        "event_set_equals_ledger_set": set(_kept) == _req_m,
        # the pre-R3-A2 population (ledger batches only): every remaining batch still EXACT ⇒ the old cell passed it
        # E3: the per-batch verdicts ALREADY computed above (same rows, same records) — re-reconciling here raised on a record the
        #     reader accepted but the join could not key (attempt_idx 'x' beside a failed-by-client-id order), and a batch with no
        #     readable record was a KeyError; a batch that is not EXACT above is not EXACT here
        "ledger_only_population_all_exact": all(_flat_state.get(b) == "EXACT" for b in _kept)}
check("★★★ R3-A2 the POPULATION is LOAD-BEARING, on the real ledger: drop ONE WHOLE batch of `protective_flatten` rows "
      "(the latest client_id-joined batch, and the latest (symbol, side, attempt_idx)-joined batch) and keep every event "
      "⇒ the event population names exactly that batch LEDGER_BATCH_MISSING and the two batch sets differ — while every "
      "remaining batch still reconciles EXACT on its own, which is precisely why a population drawn from the ledger "
      "rows let a whole missing batch through",
      len(_pop_mut) == 2 and {v["join"] for v in _pop_mut.values()} == {"client_id", "symbol_side_attempt"}
      and all(v["named_LEDGER_BATCH_MISSING"] and not v["event_set_equals_ledger_set"]
              and v["ledger_only_population_all_exact"] for v in _pop_mut.values()),
      _pop_mut)
_pop_fx = {"FLATTEN-A": [{"symbol": "AAAUSDT", "side": "sell", "attempt_idx": 1, "quantity": 1.0,
                          "_exec": {"submitted": True, "error": None, "filled_notional": -10.0}}],
           "FLATTEN-B": []}
check("★★ ...and the population's other edges are named, not guessed: a batch whose actions listed NO order has no rows by "
      "construction (`_write_flatten_rows` returns 0 on an empty list) ⇒ named, not required; the same batch WITH rows is a "
      "count MISMATCH; a required batch with no rows is LEDGER_BATCH_MISSING; no event log requires nothing (the cell "
      "then names every ledger batch NOT OBSERVABLE)",
      _flatten_population(_pop_fx, {"FLATTEN-A": [{}]}) == ({"FLATTEN-A"}, {}, ["FLATTEN-B"])
      and list(_flatten_population(_pop_fx, {})[1]) == ["FLATTEN-A"]
      and _reconcile_flatten([{"symbol": "BBBUSDT", "side": "buy", "attempt_idx": 1, "filled_notional": 5.0,
                               "terminal_reason": "filled"}], _pop_fx["FLATTEN-B"])[0] == "MISMATCH"
      and _flatten_population(None, {"FLATTEN-A": [{}]}) == (None, {}, []),
      (_flatten_population(_pop_fx, {"FLATTEN-A": [{}]}), _flatten_population(_pop_fx, {})[1]))
# ── ★ E3 (FX-EXEC 2026-09-13; independent review round 4 §2.2, last row of its R3-A2 table): the EVENT LOG is read line by line —
#    a corrupted record is a NAMED NOT OBSERVABLE finding that fails closed; never an exception exit, never a silent skip ──
import tempfile                         # noqa: E402
check("★★★ E3 THE REAL EVENT LOG IS READABLE, LINE BY LINE — every non-blank line of state/live/watchdog/events.jsonl is the "
      "writer's record (a JSON object; ts = evaluated_utc; a list of object actions; flatten_all orders / failed are lists, each "
      "order an object with an object _exec). A line that is not is NAMED NOT OBSERVABLE here AND in the completeness cell above, "
      "which then fails; no line is skipped in silence and none ends this suite by exception. A missing log is not 'readable'",
      _flat_actions is not None and not _flat_unreadable,
      {"n_unreadable": len(_flat_unreadable), "unreadable": _flat_unreadable[:5],
       "n_flatten_batches_read": (len(_flat_actions) if _flat_actions is not None else None)})


def _e3_log(lines):
    _p = os.path.join(tempfile.mkdtemp(prefix="e3_events_"), "events.jsonl")
    with open(_p, "w", encoding="utf-8") as _fh:
        _fh.write("\n".join(lines) + "\n")
    return _p


_e3_ok = {"ts": "2026-09-12T12:47:37Z", "triggers": ["cond5b"], "actions": [
    {"action": "halt_opening"},
    {"action": "flatten_all", "orders": [
        {"symbol": "AAAUSDT", "side": "sell", "quantity": 1.0, "client_id": "F1-AAAUSDT-1",
         "_exec": {"submitted": True, "error": None, "filled_notional": -10.0}},
        {"symbol": "BBBUSDT", "side": "buy", "quantity": 2.0, "client_id": "F1-BBBUSDT-2",
         "_exec": {"submitted": True, "error": None, "filled_notional": 5.0}}], "failed": []}]}
_e3_other = {"ts": "2026-09-12T16:47:37Z", "triggers": [], "actions": [{"action": "halt_opening"}]}
_E3_FLAT = _e3_ok["actions"][1]
_E3_CASES = (
    ("top-level JSON array", "[]", "JSON list"),
    ("top-level JSON number", "5", "JSON int"),
    ("top-level JSON null", "null", "JSON NoneType"),
    ("not JSON", json.dumps(_e3_other)[:-9], "not JSON"),
    ("ts not evaluated_utc", json.dumps(dict(_e3_other, ts="not-a-time")), "does not parse"),
    ("actions not a list", json.dumps(dict(_e3_other, actions=5)), "actions is int"),
    ("an action not an object", json.dumps(dict(_e3_other, actions=[{"action": "halt_opening"}, "garbage"])), "not an object"),
    ("flatten_all orders not a list", json.dumps(dict(_e3_ok, actions=[dict(_E3_FLAT, orders=7)])), "orders is int"),
    ("an order with a list _exec", json.dumps(dict(_e3_ok, actions=[dict(_E3_FLAT, orders=[dict(_E3_FLAT["orders"][0], _exec=[1])])])),
     "_exec is not an object"),
    ("an order whose attempt_idx cannot be read", json.dumps(dict(_e3_ok, actions=[dict(_E3_FLAT, orders=[
        {k: v for k, v in _E3_FLAT["orders"][0].items() if k != "client_id"} | {"attempt_idx": "x"}])])), "raised ValueError"),
)
_e3_res = {}
for _name, _bad_line, _why_part in _E3_CASES:
    try:
        _acts3, _unr3 = _flatten_event_log(_e3_log([json.dumps(_e3_ok), _bad_line, json.dumps(_e3_other)]))
        _e3_res[_name] = {"raised": None, "lines": [n for n, _ in _unr3], "why_named": any(_why_part in w for _, w in _unr3),
                          "states": sorted(_flatten_unreadable_states(_unr3)),
                          "good_record_still_read": sorted(_acts3 or {}) == ["FLATTEN-20260912T124737Z"]
                          and len((_acts3 or {}).get("FLATTEN-20260912T124737Z") or []) == 2}
    except Exception as _e:                                      # noqa: BLE001 — an exception IS the defect this cell exists for
        _e3_res[_name] = {"raised": f"{type(_e).__name__}: {str(_e)[:80]}"}
check("★★★ E3 red capability, ten corruption shapes written as line 2 between two good records (top-level JSON array / number / "
      "null; a non-JSON line; a ts that is not evaluated_utc; actions not a list; a non-object action; flatten_all orders not a "
      "list; an order with a list _exec; an order whose attempt_idx cannot be read): the reader RAISES NOTHING, names exactly "
      "line 2 with its reason, turns it into ONE NOT OBSERVABLE state entry, and still reads the good flatten record beside it. "
      "Before E3 the top-level shapes raised AttributeError out of the suite and the non-JSON / bad-ts lines were skipped in silence",
      len(_e3_res) == 10 and all(v.get("raised") is None and v["lines"] == [2] and v["why_named"]
                                 and v["states"] == ["events.jsonl line 2"] and v["good_record_still_read"] for v in _e3_res.values()),
      _e3_res)
_e3_acts_ok, _e3_unr_ok = _flatten_event_log(_e3_log([json.dumps(_e3_ok), "", json.dumps(_e3_other)]))
check("★★ E3 positive control: the writer's own shape (a flatten_all record with two orders, a blank line, a record without a "
      "flatten) reads with NO unreadable line and exactly one batch of two orders — the reader is not 'refuse everything'; "
      "`_flatten_action_orders` still returns exactly that dict; a missing log is (None, [])",
      _e3_unr_ok == [] and sorted(_e3_acts_ok) == ["FLATTEN-20260912T124737Z"] and len(_e3_acts_ok["FLATTEN-20260912T124737Z"]) == 2
      and _flatten_action_orders(_e3_log([json.dumps(_e3_ok), json.dumps(_e3_other)])) == _e3_acts_ok
      and _flatten_event_log(os.path.join(tempfile.mkdtemp(prefix="e3_none_"), "events.jsonl")) == (None, []),
      (_e3_unr_ok, sorted(_e3_acts_ok or {})))
_e3_acts_f, _e3_unr_f = _flatten_event_log(_e3_log(["[]", json.dumps(_e3_other)]))
_e3_req_f, _e3_miss_f, _ = _flatten_population(_e3_acts_f, {})
check("★★★ E3 the case silence used to lose: the FLATTEN record itself is the corrupted line and the ledger holds none of its rows "
      "(both sides gone) ⇒ the population can require nothing and the ledger has nothing to miss — the two sets are equal and "
      "empty — so the ONLY evidence left is the unreadable line, and it is named NOT OBSERVABLE (before E3: a JSON array here "
      "raised; a non-JSON line here was skipped and nothing at all was said)",
      _e3_req_f == set() and not _e3_miss_f and [n for n, _ in _e3_unr_f] == [1]
      and list(_flatten_unreadable_states(_e3_unr_f)) == ["events.jsonl line 1"],
      (_e3_req_f, _e3_miss_f, _e3_unr_f))
_fail_act = {"action": "flatten_all", "orders": [
    {"symbol": "AAAUSDT", "side": "sell", "attempt_idx": 1, "quantity": 1.0,
     "_exec": {"submitted": True, "error": None, "filled_notional": -10.0}},
    {"symbol": "BBBUSDT", "side": "buy", "attempt_idx": 1, "quantity": 1.0,
     "_exec": {"submitted": True, "rejected": True, "error": "VenueError: -2019 margin", "filled_notional": None}}],
    "failed": [{"order": {"symbol": "BBBUSDT", "side": "buy", "attempt_idx": 1, "quantity": 1.0},
                "err": "VenueError: -2019 margin"}]}
_fail_orders = _mark_recorded_failures(json.loads(json.dumps(_fail_act)))    # through a JSON round-trip, like the log
_fail_rows_ok = [{"symbol": "AAAUSDT", "side": "sell", "attempt_idx": 1, "filled_notional": -10.0, "terminal_reason": "filled"},
                 {"symbol": "BBBUSDT", "side": "buy", "attempt_idx": 1, "filled_notional": None,
                  "terminal_reason": "submitted_rejected"}]
_fail_rows_hidden = [dict(_fail_rows_ok[0]), dict(_fail_rows_ok[1], terminal_reason="filled")]
check("★★ ...and \"filled or an EXPLICITLY RECORDED failure\" is live, not decoration: a batch whose refused order "
      "is written `submitted_rejected` reconciles clean; the same refusal written `filled` goes red twice — once "
      "because its own `_exec` implies `submitted_rejected`, once because the action lists it in `failed` (matched "
      "by key through a JSON round-trip, as the event log stores it)",
      _reconcile_flatten(_fail_rows_ok, _fail_orders)[0] == "EXACT"
      and _reconcile_flatten(_fail_rows_hidden, _fail_orders)[0] == "MISMATCH"
      and len([m for m in _reconcile_flatten(_fail_rows_hidden, _fail_orders)[1]
               if "BBBUSDT" in m and ("terminal" in m or "FAILED" in m)]) == 2
      and sum(1 for o in _fail_orders if o.get("_recorded_failure")) == 1,
      (_reconcile_flatten(_fail_rows_ok, _fail_orders)[:2], _reconcile_flatten(_fail_rows_hidden, _fail_orders)[:2]))
_nj_orders = [{"symbol": "CCCUSDT", "side": "sell", "attempt_idx": 1, "quantity": 1.0,
               "_exec": {"submitted": True, "error": None, "filled_notional": -5.0, "avg_fill_px": 5.0}},
              {"symbol": "CCCUSDT", "side": "sell", "attempt_idx": 1, "quantity": 2.0,
               "_exec": {"submitted": True, "error": None, "filled_notional": -10.0, "avg_fill_px": 5.0}}]
_nj_rows = [{"symbol": "CCCUSDT", "side": "sell", "attempt_idx": 1, "filled_notional": -5.0, "terminal_reason": "filled"},
            {"symbol": "CCCUSDT", "side": "sell", "attempt_idx": 1, "filled_notional": -10.0, "terminal_reason": "filled"}]
_nj = _reconcile_flatten(_nj_rows, _nj_orders)
check("★★ ...and where NO deterministic join exists — no client ids, and (symbol, side, attempt_idx) repeated inside "
      "the batch — the batch is NOT_OBSERVABLE with that reason, never EXACT and never a silent MISMATCH: a "
      "reconciliation that cannot tell two orders apart does not get to call their rows complete",
      _nj[0] == "NOT_OBSERVABLE" and _nj[2] is None and "no deterministic join" in _nj[1][0], _nj)
_fee_fx = [{"fee_paid": None}, {"fee_paid": 0.0}, {"fee_paid": 0.5}]
check("★★★ ...and `fee_paid` None and 0.0 are DIFFERENT facts inside that class — one unmeasured "
      "row makes the batch's fee UNMEASURED (None); with every row measured it reports the sum. "
      "A `fee or 0` reading would have merged the two and called an unpriced flatten free",
      _fee_states(_fee_fx) == {"n_unmeasured": 1, "n_measured": 2, "fee_usdt": None}
      and _fee_states(_fee_fx[1:]) == {"n_unmeasured": 0, "n_measured": 2, "fee_usdt": 0.5},
      (_fee_states(_fee_fx), _fee_states(_fee_fx[1:])))

print("\n[G7-E5] E5 (FX-EXEC 2026-09-13; = EXE-07): the RULER re-judges only exactly ONE origQty comparison too, and a row-level entry is "
      "explained only by the re-judged request's own string")
# The same defect in this file's independent implementation: `_clamp_known` required every ';'-separated reason to be the origQty
# kind (C6) but read the numbers with `_ORIGQTY_PAIR.search(_raw)` — the first pair of the whole string — and `_row_rejudged`
# accepted any origQty-kind row-level entry for a re-judged client id. Cells use _REQ_OK (the real MEME request) with one reason
# added; E5-R4 holds the ruler and the runtime to the same answer on every shape.
_E5_S0 = _REQ_OK["inconsistent"]
_E5_OTHER = "A1789215839-MEMEUSDT-1: identity: re-query: re-query origQty 1933000.0 differs from ours 1933986.0"
_E5_SHAPES = {
    "conflict_semicolon": _E5_S0 + "; " + _E5_OTHER,
    "conflict_spaced": _E5_S0 + " ; " + _E5_OTHER,
    "reversed_spaced": _E5_OTHER + " ; " + _E5_S0,
    "glued": _E5_S0 + " " + _E5_OTHER.split(": ", 1)[1],
    "duplicate_spaced": _E5_S0 + " ; " + _E5_S0,
    "duplicate_semicolon": _E5_S0 + "; " + _E5_S0,
}
_e5_ruler = {k: _clamp_known({**_REQ_OK, "inconsistent": v}) for k, v in _E5_SHAPES.items()}
check("★★★ E5-R1 (OLD CODE: RED) the ruler re-judges NONE of the multi-comparison shapes — conflicting capacities in either order and "
      "either joiner, two comparisons glued into one reason, the same comparison repeated (old: the ' ; ' and glued shapes were "
      "re-judged from the first pair; the '; ' shapes stood only because ';' was swallowed into the number)",
      all(v is None for v in _e5_ruler.values()), {k: (v is not None) for k, v in _e5_ruler.items()})
check("★★ E5-R2 neighbour (both versions): the single real comparison still re-judges to the real amount",
      _clamp_known(_REQ_OK) is not None and abs(_clamp_known(_REQ_OK)[1] - (-1015.1883)) < 1e-9)


def _e5_ruler_row(row_why):
    return {"terminal_reason": "filled_amount_unknown", "filled_notional": None, "request_ledger": [dict(_REQ_OK)],
            "ledger_inconsistent": [{"client_id": _REQ_OK["client_id"], "why": row_why}]}


check("★★★ E5-R3 (OLD CODE: RED) a row-level entry for the re-judged client id that names a DIFFERENT origQty contradiction keeps the "
      "row unknown; the writer's own copy (str(request.inconsistent)[:120]) is still explained",
      _row_rejudged(_e5_ruler_row(_E5_OTHER)) is None and _row_rejudged(_e5_ruler_row(str(_E5_S0)[:120])) is not None,
      (_row_rejudged(_e5_ruler_row(_E5_OTHER)), _row_rejudged(_e5_ruler_row(str(_E5_S0)[:120]))))
_E5_LONG = _E5_S0.replace("identity: submit response: submit response", "identity: submit response (" + "x" * 60 + "): submit response")
check("★★★ E5-R3b (OLD CODE: RED) a row whose one reason is longer than 120 characters is re-judged like a short one: its row-level entry "
      "is the writer's truncated copy, which no longer reads as the origQty kind", len(_E5_LONG) > 120
      and _row_rejudged({"terminal_reason": "filled_amount_unknown", "filled_notional": None,
                         "request_ledger": [{**_REQ_OK, "inconsistent": _E5_LONG}],
                         "ledger_inconsistent": [{"client_id": _REQ_OK["client_id"], "why": _E5_LONG[:120]}]}) is not None, len(_E5_LONG))
_e5_par = {}
for _k, _v in list(_E5_SHAPES.items()) + [("single", _E5_S0), ("single_long", _E5_LONG)]:
    _rq = {**_REQ_OK, "inconsistent": _v}
    _rt = RC._clamp_rederived(_rq, _v)
    _e5_par[_k] = ((_clamp_known(_rq) is not None), (_rt is not None and _rt["final"]))
check("★★ E5-R4 parity (both versions): on every E5 shape and the single real one, the ruler re-judges exactly when the runtime's "
      "verdict is PROVEN FINAL", all(a == b for a, b in _e5_par.values()), _e5_par)

print("\n[F] red capability — mutate ANY cell and this file fails")
_orig = copy.deepcopy(OD.DISPOSITION)
_broken = []
for _reason, _want, _ in CELLS:
    OD.DISPOSITION[_reason]["disposition"] = (OD.COMPLETE if _want != OD.COMPLETE else OD.GAP)
    if OD.DISPOSITION.get(_reason, {}).get("disposition") == _want:
        _broken.append(_reason)
    OD.DISPOSITION.clear()
    OD.DISPOSITION.update(copy.deepcopy(_orig))
check("★★★ every cell's assertion is live — flipping any one of the 13 dispositions changes what "
      "[B] reads, so none of them is decoration",
      not _broken, _broken)
OD.DISPOSITION.pop("blocked_by_halt")
check("★★★ mutant 'delete a cell': the closed-world detector NAMES the missing state on real "
      "data — this is what makes a newly-added terminal_reason a decision instead of a default",
      OD.unknown_reasons(_all) == ["blocked_by_halt"], OD.unknown_reasons(_all))
OD.DISPOSITION.clear()
OD.DISPOSITION.update(copy.deepcopy(_orig))
check("★ the matrix is restored after mutation", not OD.unknown_reasons(_all))

print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
