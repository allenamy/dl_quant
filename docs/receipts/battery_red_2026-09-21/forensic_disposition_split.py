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

_HERE = os.path.expanduser("~/dl_quant_live/live")
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
    # E5: 恰好【一条】理由、恰好【一对】数, 逐条单独解析(连接符不会漏进数字)。多条比较 —— 一致也好不一致也好 —— 一律不重判:
    #     规则只在单理由的真实行上验证过; 两条记录报不同容量是冲突(R3-A1/E2); 结论不得依赖理由的顺序。
    _pairs = [_ORIGQTY_PAIR.findall(p) for p in _parts]
    if len(_pairs) != 1 or len(_pairs[0]) != 1:
        return None
    qv, qs = _fin(_pairs[0][0][0]), _fin(_pairs[0][0][1])
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
    total, cids, _whys = 0.0, [], {}
    for r in reqs:
        got = _clamp_known(r)
        if got is None:
            return None
        total += got[1]
        cids.append(r.get("client_id"))
        _whys[r.get("client_id")] = str(r.get("inconsistent"))[:120]
    for e in (o.get("ledger_inconsistent") or ()):
        cid, why = (e.get("client_id"), e.get("why")) if isinstance(e, dict) else (None, e)
        # E5: 行级条目必须【就是】写者对该请求串的拷贝(str(inconsistent)[:120]), 同一 client_id 下别的 origQty 矛盾解释不了;
        #     拷贝本身不再做种类判断 —— 超过 120 字的理由截断后丢了 "differs from ours", 旧判据会让写者自己的拷贝永远解释不了
        if not (cid in cids and str(why) == _whys.get(cid)):
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

# ── 取证: 用装置自己的 OD.gaps + 重判行, 逐行拆 ────────────────────────────
import collections as _c
TARGETS = {}
for _A in sorted({r["anchor_ts"] for r in _all}):
    _rid = [r["rebalance_id"] for r in _all if r["anchor_ts"] == _A][0]
    TARGETS[_rid] = _A
_DEL = {"skipped_no_chase_arm"}
print("\n\n================ FORENSIC ================")
rows=[]
for rid, A in TARGETS.items():
    g = OD.gaps(_all_rj, rid)
    d = float(OD.gaps([r for r in _all_rj if r.get("rebalance_id")==rid
                       and str(r.get("terminal_reason")) in _DEL], rid)["gross_usdt"])
    cap = float(g.get("venue_cap_usdt") or 0.0)
    inv = g["gross_usdt"] - d - cap
    rows.append((A, rid, d, inv, cap, g["gross_usdt"], g["n_named"], g["n_unsized"]))
rows.sort()
import datetime as dt
print("\n-- 非自愿 > 200U 的锚(全史) --")
for A,rid,d,inv,cap,tot,nn,nu in rows:
    if inv > 200:
        print(f"{dt.datetime.utcfromtimestamp(A).strftime('%Y-%m-%d %HZ')} {rid} inv={inv:9.1f} del={d:8.1f} cap={cap:8.1f} tot={tot:9.1f} named={nn} unsized={nu}")
print("\n-- 逐行明细(非自愿>200 的锚) --")
for A,rid,d,inv,cap,tot,nn,nu in rows:
    if inv <= 200: continue
    print(f"\n### {dt.datetime.utcfromtimestamp(A).strftime('%Y-%m-%d %HZ')} {rid}  inv={inv:.1f}")
    per = _c.Counter(); per_n = _c.Counter()
    for r in _all_rj:
        if r.get("rebalance_id")!=rid: continue
        tr=str(r.get("terminal_reason")); note=str(r.get("note") or "")
        cell=OD.DISPOSITION.get(tr)
        if not cell or cell["disposition"]!=OD.GAP: continue
        if tr=="venue_reject" and "-5022" in note: continue
        if tr=="abandoned_max_attempts" and "-4164" in note: continue
        it=r.get("intended_notional")
        if it is None: continue
        res=abs(float(it)-float(r.get("filled_notional") or 0.0))
        code="".join(ch for ch in note if ch) 
        import re as _re
        m=_re.search(r"-\d{4}", note)
        key=(tr, m.group(0) if m else "")
        per[key]+=res; per_n[key]+=1
    for k,v in per.most_common():
        print(f"    {k[0]:28s} {k[1]:6s} n={per_n[k]:4d} gross={v:10.1f}")

print("\n\n== skipped_stop_maker_only 全史(每行) ==")
hist=[]
for r in _all_rj:
    if str(r.get("terminal_reason"))!="skipped_stop_maker_only": continue
    it=r.get("intended_notional"); 
    res=None if it is None else abs(float(it)-float(r.get("filled_notional") or 0.0))
    hist.append((r.get("anchor_ts"), r.get("rebalance_id"), r.get("symbol"), r.get("order_type"), res, float(it or 0)))
hist.sort()
for a,rid,sym,ot,res,it in hist:
    print(f"{dt.datetime.utcfromtimestamp(a).strftime('%m-%d %HZ')} {rid} {str(sym):14s} {str(ot):18s} intended={it:9.1f} residual={res}")
print(f"总行数 {len(hist)}")
print("\n== 该终态在矩阵里的判定 ==")
c=OD.DISPOSITION["skipped_stop_maker_only"]; print(c["disposition"], "| recoverable=", c["recoverable"]); print(c["why"])

print("\n\n== 两个被止损名的后续锚(是否平掉) ==")
for sym, t0 in (("GUSDT",1789748640),("STARUSDT",1789820640)):
    print(f"\n--- {sym} ---")
    seen=[r for r in _all_rj if r.get("symbol")==sym and float(r.get("anchor_ts") or 0)>=t0-14400]
    seen.sort(key=lambda r: float(r.get("anchor_ts") or 0))
    for r in seen:
        a=float(r.get("anchor_ts") or 0)
        print(f"  {dt.datetime.utcfromtimestamp(a).strftime('%m-%d %HZ')} {str(r.get('order_type')):18s} "
              f"{str(r.get('terminal_reason')):26s} intended={float(r.get('intended_notional') or 0):9.1f} "
              f"filled={r.get('filled_notional')} note={str(r.get('note') or '')[:40]}")
