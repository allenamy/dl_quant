#!/usr/bin/env python3
"""FP3 · 平仓桶【逐笔】现金闭合 —— 独立研究员第三轮建议 §8-3「平仓桶逐笔现金闭合」。只读。

为什么要这件装置(而不是再算一张 ±120 s 窗的表):
  CASH_RECON v6 的 09-05 20:43 → 09-06 20:39 日窗残差 +2,229.28 USD、238 个持仓缺口。上一版只做到「残差与缺口【共现】」,
  复审明确指出「共现不是归因」。要把它变成归因, 必须逐笔证明:
    (a) 缺口里的每一个名, 其数量变化 = 场所逐笔成交之和(一个名都不能靠推);
    (b) 残差的每一分钱 = 账本缺失的那些成交的现金 + 手续费(身份到 (symbol, trade id));
    (c) 两个互相独立的场所端点(userTrades 与 income)在同一窗口上给出同一个手续费 / 已实现盈亏。
  三条都过, 才叫「闭合」; 任一条缺数据, 整体 UNAVAILABLE(rc 3), 不出部分数。

窗口规则 —— 与 ±120 s 桶的根本区别:
  这里的窗口是【两行 NAV 之间】(t0, t1], 两端都有与 NAV 同一次账户调用的持仓快照(|Δt| ≤ 60 s, fp3 同规则)。
  它不是「围绕某个事件的归因选择」, 而是一个【会计恒等式成立的区间】: 区间内所有流量都必须被找到, 否则残差不为零。
  日窗在 daily_nav 里其实每 4 小时就有一行 —— 用最细的相邻两行把日窗拆开, 平仓落在哪个 4 小时里就只查那一段。

恒等式(与 fp3_cash_recon.py v5 §3 逐字同义):
  ΔNAV − 外部划转 = Σ_s [q1·mk1 − q0·mk0 − Σ_账本成交 sgn·q·px] + 资金费 − 账本手续费 + 残差
  若账本缺了某些成交, 则  残差 = −Σ_缺失成交 sgn·quoteQty − Σ_缺失成交 手续费(USDT 等值)。
  这是可证伪的: 预测残差与实测残差之差必须落在 fp3 同一容差 max(2 USDT, 0.5 bp·NAV) 内。

已声明的边界(不静默):
  - 09-06 的平仓单【没有我们的 clientOrderId】, 当时也【没记场所 orderId】(执行器 binance_broker.py 的注释自述, 该字段是后来补的)。
    ⇒ 订单身份只能靠「本窗内每个 (symbol, side) 场所只有一个 orderId」+「执行器本窗只有 protective_flatten 单」这两条唯一性来对上。
    装置【测量】这两条唯一性, 不假设。
  - BNB 计价手续费按当日收盘价折 USDT(与 fp3 一致); NAV 若计入 BNB 余额的重估, 那一项不在恒等式里 —— 本窗若闭合, 说明它在本窗可忽略;
    不闭合时它是候选之一, 装置不替它背书。
★ v3(2026-09-19, 同日): 恒等式换成账户【自己的计价单位】。
  daily_nav.nav 是 USD(multiAssetsMargin: USDT 按 USDTUSD 指数×(1−1e-4), BNB 按 BNBUSD 指数×0.95 计入), 其它各项是 USDT;
  外部流水 external_flow_usdt 是【自然日累计】且把 BNB 数量当 USDT 相加(08-05: −200 USDT + 0.33275 BNB 记成 −199.667)。
  v3 的恒等式:  N = p·W + b·B,  W(USDT 腿) 与 B(BNB 余额) 各自滚动:
     W1 = W0 + 持仓市值变化与全部成交现金 + 场所资金费 − USDT 计手续费 + USDT 划转
     B1 = B0 − BNB 计手续费 + BNB 划转            (B0 取自场所收入流水累加的 BNB 余额路径, 两端被检验)
     残差(USDT) = (N1 − p1·W1 − b1·B1) / p1
  划转一律取【本窗内】场所 TRANSFER 流水(分资产), 不再用 daily_nav 的自然日累计值。
  订单身份: 执行器记的首/末成交时刻不总是场所第一笔的毫秒(08-21 WIF: 场所 …744/…745 两个毫秒, 执行器记 …745),
     改为「执行器首/末成交时刻落在该场所订单的 [首, 末] 成交毫秒之内(±1 ms)」+ 签名成交额相等(<1e-6)。
★ v4(2026-09-19, 同日; 独立复审第四轮 R4-C1 / R4-C2 / 输入有限性): v3 的 CLOSED 只核现金、数量与两端点【窗口总额】,
  复审在真实 09-06 输入上逐条造出「应拒而判 CLOSED」: 删光平仓单 / 268 单全不匹配 / 268 单全复制 / income tradeId 全换成不存在的值 /
  两条 REALIZED_PNL 各 ±100 互相抵消 / 同数量换一个品种 —— 全部 CLOSED rc 0。v4 把判词拆成独立的门, 缺一不可:
    INPUT_FINITE  在【输入层】拒绝被用到的数值字段里的 NaN / ±inf / 非数 / 缺失(不靠比较表达式: NaN 比较恒假 = 静默通过)。
                  过滤键(nav_ts / read_ts / fill_ts / settlement_ts / submit_ts / first_fill_ts)对【全部载入行】查,
                  值字段对【被用到的行】查; 场所原始件的 userTrades 与 income 行全查; BNB 余额路径行、BNB 日收盘、四个指数价也查。
                  失败 ⇒ REFUSED_INPUT_FINITE(rc 2), 收据里逐条列出 (来源, 键, 字段, 值)。
    POPULATION    应查品种集合与当初【实际查询】的品种集合必须【集合相等】(不是个数相等)。
                  原始件带 symbols_queried ⇒ 集合比较; 不等 ⇒ REFUSED_POPULATION。(v4.1 起过 = 还要逐页凭据, 见 ★ v4.1)
                  旧原始件(v2/v3 拉取)没有这张清单, 只有个数 ⇒ 个数不等照旧拒绝; 个数相等只能给 POPULATION_UNPROVEN_COUNT_ONLY,
                  【不冒充已证】: 这一层的 CLOSED 写成 CLOSED_POPULATION_UNPROVEN(rc 5, 不是 0)。
                  另: userTrades 里出现未被查询的品种 ⇒ REFUSED_POPULATION。
    ATTRIBUTION   (硬门)本窗执行器 protective_flatten 订单集非空且全部属于 --event; 该事件在载入日内的平仓单全部落在窗内;
                  每张执行器单【恰好一个】候选场所订单(场所订单键 = (symbol, orderId), v3 只用 orderId);
                  每个场所订单【至多被消费一次】(v3 的 matched[venue]=o 允许后来者覆盖前者 —— 不是双射);
                  未匹配 = 0、歧义 = 0、执行器重复行 = 0、同一场所订单买卖混向 = 0、左右计数相等。
    ENDPOINT      userTrades 与 income 【逐 (symbol, tradeId)】相等: COMMISSION(连同资产)与 REALIZED_PNL 逐键差 ≤ 1e-8(Decimal);
                  两侧都不许有非零孤儿; 无重复身份((symbol,id) / (incomeType,tranId) / 每键每类至多一行);
                  无跨品种 orderId 碰撞; 两端点的行都落在声明的窗口毫秒内。v3 的窗口总额比较保留在 CASH 里, 不删。
    CASH          v3 的闭合条件原样(数量闭合、账本=场所同笔、总额交叉、BNB 路径、USD 恒等式残差 ≤ 容差)。
  VERDICT = CLOSED(rc 0)仅当 INPUT_FINITE ∧ POPULATION_PASS(v4.1) ∧ ATTRIBUTION ∧ ENDPOINT ∧ CASH;
            CLOSED_POPULATION_UNPROVEN(rc 5)= 其余全过但取数人口只能按个数核;
            OPEN(rc 4)= 任一门 FAIL(failed_gates 逐个列名); REFUSED_<门>(rc 2); UNAVAILABLE(rc 3)。
  其余计算与 v3 逐行同义(A/C/D 各数不变; 复跑十窗逐字段核对见 RESULT_flatten_closure_gates_2026-09-19.md)。
  另: 指数价只读缓存(offline=True, 缺分钟 ⇒ UNAVAILABLE), 且不回写缓存 —— v3 在复用路径上仍可能联网补缺并改写缓存文件(v4.1 起新拉取也如此);
      --ledger-root 让同一装置读隔离副本(电池用), 缺省 = 实盘账本 ~/dl_quant_live(只读); 收据记 ledger_root 与依赖文件 sha256。
★ v4.1(2026-09-19, 同日; 协调者第二轮): 新拉取路径把【证据】落盘, 人口门才可能真的过。
    新拉取原始件(raw_format = RAW_FORMAT_FRESH)写: symbols_queried(实际查询清单)、trades_pages_by_symbol(每个品种 fetch_trades 返回的
    逐页凭据 mode/startTime/endTime/fromId/status/n/weight + completeness + n_rows)、income_pages + income_n_boundary_rows_subtracted、
    两个取数器的 sha256、拉取起止时刻。目标文件已存在 ⇒ 拒绝(拉取收据只追加, 不覆盖旧拉取); 不完整的拉取也落盘但标 INCOMPLETE, 永不可复用。
    复用与新拉取走【同一条】人口校验: 个数 → 集合 → 逐页凭据(page_receipt_problems)。三档:
      POPULATION_PASS                       清单 = 应查集合 且 逐页凭据自洽(全 200、首页 = 本窗口、非末页全满、行数对得上、income Σn − 扣除 = 行数)
      POPULATION_UNPROVEN_NO_PAGE_RECEIPTS  清单相等但没有逐页凭据(每个品种是否取全仍是自述)
      POPULATION_UNPROVEN_COUNT_ONLY        旧原始件, 只有个数
    逐页凭据里有非 200 页 / 声明 INCOMPLETE 的品种 / 缺凭据的查询品种 / 计数不合 ⇒ REFUSED_POPULATION。
    指数价【永远】只读缓存(offline=True, 缺分钟 ⇒ UNAVAILABLE), 装置不再有任何取数器以外的联网。
★ v4.2(2026-09-19, 同日; 独立复审第五轮 R5-08): v4.1 的逐页凭据只【计数】自洽, 复审在真实 09-06 新拉取上造出三类被判 PASS 的不完整证据:
    页凭据说返回 2 行而 body 0 行 / income 末页满页(扣除数配平)/ income 续页游标倒退到窗口之前(另: 负的扣除数)。计数自洽不是完整性证明。
    v4.2 把人口门改成【按取数器自己的规则重放】(page_receipt_findings), 三条性质各自要证:
      (1) 行身份  各页返回、按取数器规则保留的行 == 原始件保存的行(userTrades 按 (symbol, id); income 按全字段行多重集 + 边界多重集扣除);
                  每页声明的 n == 它逐行列出的返回行数; 逐页 n_kept / n_subtracted(若有)== 重放值; 扣除总数 == 重放值。
      (2) 终止    userTrades 每个品种末页 = 短页 / 空页 / 越过窗口; income 末页必须是短页(满页 = 未完成拉取); 满毫秒枚举以短页结束。
      (3) 游标    fromId = 上一页 max(id)+1 且严格递增; income 下一请求 = 取数器按上一页算出的那一个(max(time) 不 +1 / page+1 / 毫秒+1)。
    两类结论, 都不是 PASS:
      凭据与取数器规则【矛盾】 ⇒ REFUSED_POPULATION(rc 2), 与 v4.1「计数不合 ⇒ REFUSED」同一档; 具名原因逐条落收据。
      凭据【不足以证明】      ⇒ POPULATION_UNPROVEN_PAGE_EVIDENCE, 其余全过时判 CLOSED_POPULATION_UNPROVEN(rc 5); 具名原因逐条落收据。
    证据来源: 取数器 v3(fetch_trades / fetch_income_paged)在每页多记逐行证据 returned([id, time] / [sha256(row_identity), time])、
      n_kept、past_window / n_subtracted —— 请求与停止规则与 v2 逐字相同, 只多记账。v2 凭据(只有逐页 n)仍可读: 只有当计数把
      「每页贡献了哪几行」唯一确定时(每页返回行全被保留: userTrades Σn == 保存行数, income 扣除数 == 0)才算证明; 否则具名 UNPROVEN。
    重放只对 FETCHER_REGISTRY 登记过的取数器源码成立(原始件自报 fetch_devices_sha256); 未登记 ⇒ UNPROVEN。页上限取取数器常量, 原始件自报只被核。
usage: flatten_window_closure.py <t0_nav_ts> <t1_nav_ts> <out.json> [raw_trades_out.json] --bnb-rows <INCOME_BNB_ROWS.json> --event <rebalance_id>
                                 [--reuse-raw <raw.json>] [--ledger-root <root containing state/live/pilot_log>]"""
import collections, hashlib, json, math, os, sys, time, traceback
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "multi_asset", "exports", "live", "pilot_journal", "tools"))
import fills_reader as FR                                   # 规范成交读者: (symbol, trade_id) 坍缩, 金额取一次
import usd_valuation as UV
VERSION = "v4.2-2026-09-19"   # v4: 判词拆门; v4.1: 新拉取落逐页凭据, 人口可达 PASS; v4.2: 逐页凭据按取数器规则重放(行身份/终止/游标), 计数自洽不再够
CLI_FLAGS = ("--bnb-rows", "--reuse-raw", "--event", "--ledger-root")
DEFAULT_LEDGER_ROOT = os.path.expanduser("~/dl_quant_live")
LED = os.path.join(DEFAULT_LEDGER_ROOT, FR.PILOT_LOG)       # == v3 的 ~/dl_quant_live/state/live/pilot_log; --ledger-root 改写
SNAP_TOL_S = 60.0
BNB_P = os.path.join(HERE, "..", "FP3_receipts", "BNBUSDT_daily_20260801_20260918.json")
TIER_PASS, TIER_LIST, TIER_COUNT = "POPULATION_PASS", "POPULATION_UNPROVEN_NO_PAGE_RECEIPTS", "POPULATION_UNPROVEN_COUNT_ONLY"
TIER_PAGES = "POPULATION_UNPROVEN_PAGE_EVIDENCE"            # v4.2: 有逐页凭据、不矛盾, 但不足以证明(见 page_receipt_findings)
RAW_FORMAT_FRESH = ("flatten_window_closure v4.2 fresh raw (symbols_queried + per-symbol userTrades page receipts + income page receipts; "
                    "pages carry per-row evidence from fetch_trades v3 / fetch_income_paged v3)")
FETCH_LIMIT = 1000                                           # 两个登记取数器的页上限(LIMIT 常量); 原始件自报的 page_limit 只被核, 不当尺
# v4.2: 重放 = 把取数器自己的规则再写一遍, 只对规则被逐行复现的取数器成立。键 = 写原始件那一刻取数器源码的 sha256(原始件 fetch_devices_sha256 自报)。
#   新取数器版本必须在这里登记后才能 PASS; 未登记 ⇒ POPULATION_UNPROVEN_PAGE_EVIDENCE(FETCHER_NOT_REGISTERED), 永不 PASS。
FETCHER_REGISTRY = {
    "7ad9641848861a9b6e08b735c251d0bca072f5c5651d4b54f82aa26535a6f898":
        ("fetch_trades.py", "v2 R15-I1 (archive/fetch_trades_v2_7ad96418.py): window page then fromId; page receipts carry counts only"),
    "3fcb5b3ff762038cba5244f6b7fc2854586f93b4c0f26fa9bcfe036b9a71ae8e":
        ("fetch_trades.py", "v3 R5-08: v2 requests and stop rules unchanged + per-row [id, time] page evidence"),
    "c7ac556b8fac9cfb487e4a60974b01429eed6172bb08664fc4ab0ce84016161c":
        ("fetch_income_paged.py", "v2 R15-I1 + income_type (archive/fetch_income_paged_v2_c7ac556b.py): page receipts carry counts only"),
    "02114e99946c70ac1a2b730a0afb9459048bf12efe891d1b44189f8c82b53132":
        ("fetch_income_paged.py", "v3 R5-08: v2 requests and stop rules unchanged + per-row [sha256(row_identity), time] page evidence"),
}
RC = {"CLOSED": 0, "REFUSED": 2, "UNAVAILABLE": 3, "OPEN": 4, "CLOSED_POPULATION_UNPROVEN": 5}
ENDPOINT_TOL = Decimal("1e-8")
U = lambda t: time.strftime("%m-%d %H:%M:%SZ", time.gmtime(float(t)))
DAY = lambda t: time.strftime("%Y%m%d", time.gmtime(float(t)))


def rows(day, name):
    p = f"{LED}/{day}/{name}.jsonl"
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.isfile(p) else []


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def check_num(bad, src, key, field, x, allow_none=False, positive=False):
    """输入层有限性(v4): 一个【被用到的】数值字段必须能转成有限浮点; None 只在 v3 本就按 0 / 跳过处理的字段上放行。
    bool 不算数; 非数 / NaN / ±inf 一律记名; positive=True 时 ≤ 0 也记名(被当除数的价格)。"""
    why = None
    if x is None:
        why = None if allow_none else "missing"
    elif isinstance(x, bool):
        why = "bool"
    else:
        try:
            v = float(x)
            if not math.isfinite(v): why = "nonfinite"
            elif positive and not v > 0.0: why = "nonpositive"
        except (TypeError, ValueError):
            why = "nonnumeric"
    if why:
        bad.append({"src": src, "key": str(key)[:80], "field": field, "value": repr(x)[:40], "why": why})


def _isint(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _as_int(x):
    """页凭据里的整数(id / time / fromId / startTime): int 或纯十进制数字串才算; 其它一律 None(调用处记成 MALFORMED 矛盾, 不猜)。"""
    if _isint(x): return x
    if isinstance(x, str) and x.strip().lstrip("-").isdigit(): return int(x.strip())
    return None


def income_row_digest(r):
    """fetch_income_paged.row_identity 的同一条规则(全字段、sort_keys、(',', ':') 分隔的规范 JSON)再取 sha256 ——
    v3 取数器页凭据 returned 里逐行存的就是它。行身份 = 行, 不是 tranId(E-0909-H)。"""
    return hashlib.sha256(json.dumps(r, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _trades_symbol(sym, e_, rs, s_ms, e_ms, lim, V, U):
    """一个被查询品种的 userTrades 逐页凭据。返回证据级别: ROW_IDENTITY / DEDUCED_EXACT / UNPROVEN / VIOLATION。
    V 追加「与取数器自己的规则矛盾」, U 追加「凭据不足以证明」。取数器规则(fetch_trades v2/v3 同一套):
      首页 = 本窗口(startTime/endTime); 行按 [s, e] 过滤、按 id 去重(id 唯一, 重复只可能是重复请求);
      首页满页才续取; 续页 fromId = 上一页【全部返回行】max(id)+1, 严格递增; 续页在 空页 / 短页 / 有行越过窗口右端 时停。"""
    nV = len(V)
    e_ = e_ if isinstance(e_, dict) else {}
    pg = e_.get("pages") if isinstance(e_.get("pages"), list) else []
    if e_.get("completeness") != "COMPLETE": V.append(f"INCOMPLETE_SYMBOL: {sym} ({e_.get('incomplete_reason')})")
    if not pg: V.append(f"NO_PAGES: {sym}"); return "VIOLATION"
    if not all(isinstance(p, dict) for p in pg): V.append(f"PAGE_MALFORMED: {sym}"); return "VIOLATION"
    for i, p in enumerate(pg):
        if p.get("status") != 200: V.append(f"PAGE_STATUS_NOT_200: {sym} page {i} status {p.get('status')}")
        if not _isint(p.get("n")) or p["n"] < 0: V.append(f"PAGE_N_INVALID: {sym} page {i} n {p.get('n')!r}")
    if len(V) > nV: return "VIOLATION"
    ns = [p["n"] for p in pg]; last = len(pg) - 1
    f0 = pg[0]
    if f0.get("mode") != "window" or f0.get("startTime") != s_ms or f0.get("endTime") != e_ms:
        V.append(f"FIRST_PAGE_NOT_THIS_WINDOW: {sym}")
    if any(p.get("mode") != "fromId" for p in pg[1:]): V.append(f"CONTINUATION_NOT_BY_FROMID: {sym}")
    fids = [_as_int(p.get("fromId")) for p in pg[1:]]
    if any(f is None for f in fids): V.append(f"TRADES_FROMID_MALFORMED: {sym} {[p.get('fromId') for p in pg[1:]][:6]}")
    elif any(b <= a for a, b in zip(fids, fids[1:])): V.append(f"TRADES_FROMID_NOT_INCREASING: {sym} fromId {fids[:6]}")
    if e_.get("n_rows") != len(rs): V.append(f"ROWCOUNT_MISMATCH: {sym} receipt {e_.get('n_rows')} vs body {len(rs)}")
    bid = [_as_int(t.get("id")) for t in rs]; btm = [_as_int(t.get("time")) for t in rs]
    if any(x is None for x in bid + btm): V.append(f"TRADES_BODY_ID_OR_TIME_MALFORMED: {sym}")
    elif len(set(bid)) != len(bid): V.append(f"TRADES_BODY_DUPLICATE_ID: {sym} {len(bid) - len(set(bid))}")
    if len(V) > nV: return "VIOLATION"

    if all(isinstance(p.get("returned"), list) for p in pg):
        # ── 行级凭据(fetch_trades v3): 按取数器自己的规则逐页重放, 不信任何计数 ──
        seen, kept, prev = set(), {}, None
        for i, p in enumerate(pg):
            pr = []
            for x in p["returned"]:
                a, t = (_as_int(x[0]), _as_int(x[1])) if isinstance(x, (list, tuple)) and len(x) == 2 else (None, None)
                if a is None or t is None:
                    V.append(f"TRADES_PAGE_EVIDENCE_MALFORMED: {sym} page {i} entry {str(x)[:40]}"); return "VIOLATION"
                pr.append((a, t))
            if p["n"] != len(pr):
                V.append(f"PAGE_N_NOT_EQUAL_RETURNED: {sym} page {i} declares n {p['n']} but its evidence lists {len(pr)} returned row(s)")
            if i >= 1:
                exp = max(a for a, _ in prev) + 1 if prev else None
                if fids[i - 1] != exp:
                    V.append(f"TRADES_FROMID_NOT_FETCHER_CURSOR: {sym} page {i} fromId {fids[i - 1]} vs fetcher cursor max(id of page {i - 1})+1 = {exp}")
                if any(a < fids[i - 1] for a, _ in pr):
                    V.append(f"TRADES_FROMID_PAGE_ID_BELOW_CURSOR: {sym} page {i} returned an id below its fromId {fids[i - 1]}")
            past, k = False, 0
            for a, t in pr:                                    # fetch_trades.take(), 逐条同义
                if t > e_ms: past = True; continue
                if t < s_ms: continue
                if a in seen: continue
                seen.add(a); kept[a] = t; k += 1
            if "n_kept" in p and p["n_kept"] != k:
                V.append(f"TRADES_PAGE_N_KEPT_DISAGREES_WITH_REPLAY: {sym} page {i} declares {p['n_kept']}, replay keeps {k}")
            if "past_window" in p and p["past_window"] != past:
                V.append(f"TRADES_PAGE_PAST_WINDOW_DISAGREES_WITH_REPLAY: {sym} page {i}")
            stop = (len(pr) < lim) if i == 0 else (len(pr) == 0 or past or len(pr) < lim)
            if stop and i < last:
                V.append(f"TRADES_PAGES_AFTER_STOP: {sym} page {i} is a stopping page under the fetcher's rule, yet {last - i} page(s) follow")
            if not stop and i == last:
                V.append(f"TRADES_FINAL_PAGE_NOT_TERMINAL: {sym} last page {i} holds {len(pr)} row(s), none past the window — "
                         f"the fetcher stops only on a short page, an empty page or a page that ran past the window")
            prev = pr
        body = dict(zip(bid, btm))
        miss = sorted(a for a in kept if a not in body); extra = sorted(a for a in body if a not in kept)
        tdis = sorted(a for a in kept if a in body and body[a] != kept[a])
        if miss: V.append(f"TRADES_RETURNED_ROW_MISSING_FROM_BODY: {sym} {len(miss)} in-window row(s) the pages returned are not in the saved body, ids {miss[:3]}")
        if extra: V.append(f"TRADES_BODY_ROW_NOT_IN_ANY_PAGE: {sym} {len(extra)} saved row(s) no page returned, ids {extra[:3]}")
        if tdis: V.append(f"TRADES_PAGE_TIME_DISAGREES_WITH_BODY: {sym} {len(tdis)} id(s) {tdis[:3]}")
        return "ROW_IDENTITY" if len(V) == nV else "VIOLATION"

    # ── 只有页计数(fetch_trades v2 的凭据): 只在拆分被计数【唯一确定】时才能证明 ──
    if ns[0] < lim and len(pg) > 1: V.append(f"TRADES_PAGES_AFTER_STOP: {sym} page 0 is short ({ns[0]}) yet {last} page(s) follow")
    if ns[0] >= lim and len(pg) == 1: V.append(f"FULL_WINDOW_PAGE_NOT_CONTINUED: {sym}")
    for i in range(1, last):
        if ns[i] < lim: V.append(f"TRADES_PAGES_AFTER_STOP: {sym} page {i} is short/empty ({ns[i]}) yet page(s) follow")
    tot, cnt = sum(ns), len(rs)
    if cnt > tot:
        V.append(f"MORE_ROWS_THAN_PAGES: {sym} body {cnt} > pages returned {tot}")
    elif cnt == tot and len(V) == nV:
        # 取数器只从返回行里保留(kept ⊆ returned, 逐页), 行数相等 ⇒ 每页返回的每一行都在 body 里, 且第 i 页恰好贡献 n_i 行(追加顺序)
        segs, off = [], 0
        for n in ns: segs.append(bid[off:off + n]); off += n
        for i in range(1, len(pg)):
            exp = max(segs[i - 1]) + 1 if segs[i - 1] else None
            if fids[i - 1] != exp:
                V.append(f"TRADES_FROMID_NOT_FETCHER_CURSOR: {sym} page {i} fromId {fids[i - 1]} vs max(id of page {i - 1})+1 = {exp}")
        if last >= 1 and ns[last] >= lim:
            V.append(f"TRADES_FINAL_PAGE_NOT_TERMINAL: {sym} last fromId page is full and every returned row was kept (so none ran "
                     f"past the window) — the fetcher would have continued")
        return "DEDUCED_EXACT" if len(V) == nV else "VIOLATION"
    elif len(V) == nV:
        U.append(f"TRADES_RETURNED_ROWS_NOT_IN_BODY_NO_ROW_EVIDENCE: {sym} pages returned {tot} row(s), body keeps {cnt}; the fetcher "
                 f"drops only out-of-window rows and repeated ids, but these v2 page receipts carry no per-row evidence to show the "
                 f"{tot - cnt} dropped row(s) were such (a v3 re-pull records [id, time] per returned row)")
        return "UNPROVEN"
    return "VIOLATION"


def _income(ip, irows, S, s_ms, e_ms, lim, V, U):
    """income 逐页凭据。返回证据级别(同上)。取数器规则(fetch_income_paged v2/v3 同一套):
      首页 window@s; 页内【边界多重集扣除】: 只在续取的 window 页上、只对 time == 本页 startTime 且与已持有的该毫秒行【全字段同一】的行扣除;
      window 满页: max(time) > min(time) ⇒ 下一请求 window@max(time)(不 +1); 否则整页在同一毫秒 ⇒ 用 page=2,3,… 枚举该毫秒
      (每页扣除该毫秒已持有的同一行), 枚举在短页结束 ⇒ 下一请求 window@该毫秒+1(> e 则结束); 满页却无新行 = 取数器判 INCOMPLETE;
      window 短页 ⇒ 结束。所以一次完整拉取的最后一页必是短页。"""
    nV = len(V)
    if not isinstance(ip, list) or not ip: V.append("NO_INCOME_PAGE_RECEIPTS"); return "VIOLATION"
    if not all(isinstance(p, dict) for p in ip): V.append("INCOME_PAGE_MALFORMED"); return "VIOLATION"
    for i, p in enumerate(ip):
        if p.get("status") != 200: V.append(f"INCOME_PAGE_STATUS_NOT_200: page {i} status {p.get('status')}")
        if not _isint(p.get("n")) or p["n"] < 0: V.append(f"INCOME_PAGE_N_INVALID: page {i} n {p.get('n')!r}")
    if not _isint(S) or S < 0:
        V.append(f"INCOME_SUBTRACTED_INVALID: income_n_boundary_rows_subtracted {S!r} (a count of removed rows: a non-negative integer)")
    if len(V) > nV: return "VIOLATION"
    ns = [p["n"] for p in ip]; last = len(ip) - 1
    mode = lambda p: p.get("mode", "window")
    if sum(ns) - S != len(irows):
        V.append(f"INCOME_ROWCOUNT_IDENTITY: sum(n) {sum(ns)} - subtracted {S} != rows {len(irows)}")
    if mode(ip[0]) != "window" or ip[0].get("startTime") != s_ms: V.append("INCOME_FIRST_PAGE_NOT_THIS_WINDOW")
    if ns[last] >= lim:
        V.append(f"INCOME_FINAL_PAGE_FULL: the last page ({last}) holds {ns[last]} rows = the page limit; the fetcher ends only on a "
                 f"short page, so a full final page is an unfinished pull")
    if len(ip) == 1 and S != 0: V.append(f"INCOME_SUBTRACTED_WITHOUT_CONTINUATION: one page, yet {S} row(s) declared subtracted")
    itm = [_as_int(r.get("time")) if isinstance(r, dict) else None for r in irows]
    if any(t is None for t in itm): V.append("INCOME_BODY_TIME_MALFORMED"); return "VIOLATION"

    if all(isinstance(p.get("returned"), list) for p in ip):
        # ── 行级凭据(fetch_income_paged v3): 整次拉取按取数器自己的规则重放 ──
        held, S_r, boundary, ms_rows = [], 0, collections.Counter(), []
        state, done, broke = ("window", s_ms), False, False
        for i, p in enumerate(ip):
            if done:
                V.append(f"INCOME_PAGES_AFTER_TERMINATION: page {i} follows the page on which the fetcher stops"); broke = True; break
            pr = []
            for x in p["returned"]:
                d, t = (x[0], _as_int(x[1])) if isinstance(x, (list, tuple)) and len(x) == 2 else (None, None)
                if not (isinstance(d, str) and len(d) == 64) or t is None:
                    V.append(f"INCOME_PAGE_EVIDENCE_MALFORMED: page {i} entry {str(x)[:40]}"); return "VIOLATION"
                pr.append((d, t))
            if p["n"] != len(pr):
                V.append(f"INCOME_PAGE_N_NOT_EQUAL_RETURNED: page {i} declares n {p['n']} but its evidence lists {len(pr)} returned row(s)")
            st = _as_int(p.get("startTime"))
            if state[0] == "window":
                cur = state[1]
                if mode(p) != "window" or st != cur:
                    V.append(f"INCOME_CURSOR_NOT_FETCHER_RULE: page {i} is {mode(p)}@{p.get('startTime')}, the fetcher's next request is window@{cur}")
                    broke = True; break
                if any(t < cur or t > e_ms for _, t in pr):
                    V.append(f"INCOME_PAGE_ROW_OUTSIDE_REQUEST: page {i} returned a row outside [{cur}, {e_ms}]")
                at = cur if boundary else None                # fetch_income_paged: record(body, cur if boundary else None)
                kept, sub = [], 0
                for d, t in pr:
                    if at is not None and t == at and boundary[d] > 0:
                        boundary[d] -= 1; sub += 1; continue
                    kept.append((d, t))
            else:
                mx, pgn = state[1], state[2]
                if mode(p) != "saturated_millisecond" or st != mx or _as_int(p.get("endTime")) != mx or p.get("page") != pgn:
                    V.append(f"INCOME_SATURATED_ENUMERATION_BROKEN: page {i} is {mode(p)}@{p.get('startTime')} page {p.get('page')}, "
                             f"the fetcher's next request is saturated_millisecond@{mx} page {pgn}")
                    broke = True; break
                if any(t != mx for _, t in pr):
                    V.append(f"INCOME_SATURATED_PAGE_ROW_OUTSIDE_MS: page {i} returned a row outside millisecond {mx}")
                seen = collections.Counter(ms_rows); kept, sub = [], 0
                for d, t in pr:
                    if seen[d] > 0: seen[d] -= 1; sub += 1; continue
                    kept.append((d, t))
                ms_rows += [d for d, _ in kept]
            held += kept; S_r += sub
            if "n_kept" in p and p["n_kept"] != len(kept):
                V.append(f"INCOME_PAGE_N_KEPT_DISAGREES_WITH_REPLAY: page {i} declares {p['n_kept']}, replay keeps {len(kept)}")
            if "n_subtracted" in p and p["n_subtracted"] != sub:
                V.append(f"INCOME_PAGE_N_SUBTRACTED_DISAGREES_WITH_REPLAY: page {i} declares {p['n_subtracted']}, replay subtracts {sub}")
            if state[0] == "window":
                if len(pr) < lim: done = True; continue
                mx, mn = max(t for _, t in pr), min(t for _, t in pr)
                if mx > mn:
                    boundary = collections.Counter(d for d, t in held if t == mx); state = ("window", mx)
                else:
                    ms_rows = [d for d, _ in kept]; state = ("sat", mx, 2)
            else:
                if len(pr) < lim:
                    if state[1] + 1 > e_ms: done = True
                    else: boundary = collections.Counter(); state = ("window", state[1] + 1)
                elif not kept:
                    V.append(f"INCOME_SATURATED_PAGE_REPEATED: page {i} is full but adds no new row (the fetcher declares INCOMPLETE here)")
                    broke = True; break
                else:
                    state = ("sat", state[1], state[2] + 1)
        if not done and not broke:
            nxt = f"window@{state[1]}" if state[0] == "window" else f"saturated_millisecond@{state[1]} page {state[2]}"
            V.append(f"INCOME_NOT_TERMINATED: the last page is not a stopping page under the fetcher's rules (its next request would be {nxt})")
        if S_r != S: V.append(f"INCOME_SUBTRACTED_DISAGREES_WITH_REPLAY: receipt {S}, replay {S_r}")
        bd = collections.Counter(income_row_digest(r) for r in irows); hd = collections.Counter(d for d, _ in held)
        miss, extra = hd - bd, bd - hd
        if miss: V.append(f"INCOME_RETURNED_ROW_MISSING_FROM_BODY: {sum(miss.values())} row(s) the pages returned and the fetcher's rule keeps are not in the saved body")
        if extra: V.append(f"INCOME_BODY_ROW_NOT_IN_ANY_PAGE: {sum(extra.values())} saved row(s) that no page returned (or that a page returned and the rule subtracted)")
        dt = {income_row_digest(r): t for r, t in zip(irows, itm)}
        if any(d in dt and dt[d] != t for d, t in held): V.append("INCOME_PAGE_TIME_DISAGREES_WITH_ROW")
        return "ROW_IDENTITY" if len(V) == nV else "VIOLATION"

    # ── 只有页计数(fetch_income_paged v2 的凭据): 请求序列的文法照查; 行身份只在 扣除 = 0 时由计数唯一确定 ──
    for i in range(1, len(ip)):
        q, p = ip[i - 1], ip[i]; qst, st = _as_int(q.get("startTime")), _as_int(p.get("startTime"))
        if qst is None or st is None: V.append(f"INCOME_CURSOR_MALFORMED: page {i}"); break
        if mode(q) == "window":
            if q["n"] < lim:
                V.append(f"INCOME_PAGES_AFTER_TERMINATION: page {i - 1} is a short window page (the fetcher stops there) yet page {i} follows"); break
            if mode(p) == "window":
                if not qst < st <= e_ms:
                    V.append(f"INCOME_CURSOR_NOT_ADVANCING: page {i} startTime {st} after a full window page at {qst}; the fetcher's cursor is "
                             f"that page's max(time), which lies in ({qst}, {e_ms}]"); break
            elif mode(p) == "saturated_millisecond":
                if not (st == _as_int(p.get("endTime")) and qst <= st <= e_ms and p.get("page") == 2):
                    V.append(f"INCOME_SATURATED_ENUMERATION_BROKEN: page {i} does not open a saturated-millisecond enumeration at page 2"); break
            else:
                V.append(f"INCOME_PAGE_MODE_UNKNOWN: page {i} {mode(p)!r}"); break
        elif mode(q) == "saturated_millisecond":
            if q["n"] >= lim:
                if not (mode(p) == "saturated_millisecond" and st == qst and _as_int(p.get("endTime")) == qst and p.get("page") == q.get("page", 0) + 1):
                    V.append(f"INCOME_SATURATED_ENUMERATION_BROKEN: page {i} after a full saturated page at {qst} is not its next page"); break
            elif not (mode(p) == "window" and st == qst + 1 and st <= e_ms):
                V.append(f"INCOME_CURSOR_NOT_FETCHER_RULE: page {i} after the short saturated page at {qst}; the fetcher resumes at window@{qst + 1}"); break
        else:
            V.append(f"INCOME_PAGE_MODE_UNKNOWN: page {i - 1} {mode(q)!r}"); break
    if mode(ip[last]) == "saturated_millisecond" and ns[last] < lim and _as_int(ip[last].get("startTime")) is not None \
            and _as_int(ip[last].get("startTime")) + 1 <= e_ms:
        V.append(f"INCOME_NOT_TERMINATED: the pull ends on a short saturated page at {ip[last].get('startTime')}, but the fetcher resumes at +1 ms inside the window")
    if len(V) > nV: return "VIOLATION"
    if S == 0:
        # 没有任何扣除 ⇒ 每页返回的每一行都被追加(kept ⊆ returned 且 Σn = 行数), 第 i 页恰是 body 的第 i 段 ⇒ 逐页核时间与游标
        off = 0
        for i, p in enumerate(ip):
            seg = itm[off:off + p["n"]]; off += p["n"]; st = _as_int(p["startTime"])
            if mode(p) == "window" and any(t < st or t > e_ms for t in seg):
                V.append(f"INCOME_PAGE_ROW_OUTSIDE_REQUEST: page {i}"); break
            if mode(p) == "saturated_millisecond" and any(t != st for t in seg):
                V.append(f"INCOME_SATURATED_PAGE_ROW_OUTSIDE_MS: page {i}"); break
            if i < last and mode(p) == "window" and seg:
                nx = ip[i + 1]; mx, mn = max(seg), min(seg)
                ok = ((mode(nx) == "window" and _as_int(nx["startTime"]) == mx) if mx > mn else
                      (mode(nx) == "saturated_millisecond" and _as_int(nx["startTime"]) == mx))
                if not ok:
                    V.append(f"INCOME_CURSOR_NOT_FETCHER_RULE: page {i + 1} startTime {nx.get('startTime')} vs the fetcher's cursor "
                             f"from page {i} (max time {mx}, min time {mn})"); break
        return "DEDUCED_EXACT" if len(V) == nV else "VIOLATION"
    U.append(f"INCOME_PER_PAGE_SPLIT_NOT_RECORDED: {len(ip)} pages, {S} boundary row(s) subtracted in total; these v2 page receipts "
             f"do not record which page each subtraction came from, so no page's contribution — and no row identity between pages and "
             f"body — can be checked; only the aggregate sum(n) - subtracted = rows holds (a v3 re-pull records [digest, time] per returned row)")
    return "UNPROVEN"


def page_receipt_findings(rd, q_list, trades, irows, s_ms, e_ms):
    """v4.2(R5-08): 逐页凭据【证明】取数完整, 而不是【计数】自洽。只看落盘的凭据与行, 不联网。返回
      violations  凭据与取数器自己的规则矛盾(状态 / 计数 / 行身份 / 终止 / 游标)       ⇒ REFUSED_POPULATION
      unproven    凭据不矛盾, 但不足以证明(取数器未登记 / v2 凭据无逐行证据且拆分不唯一) ⇒ POPULATION_UNPROVEN_PAGE_EVIDENCE
      evidence    每个品种与 income 的证据级别(ROW_IDENTITY / DEDUCED_EXACT / UNPROVEN / VIOLATION)
    两者皆空才是 POPULATION_PASS。三条要证的性质:
      (1) 行身份: 按取数器自己的身份规则(userTrades = (symbol, id); income = 全字段行的多重集 + 边界扣除)把各页【重放】出来的保留行
          必须与原始件保存的行【逐一相同】; 每页声明的 n 必须等于它逐行列出的返回行数。
      (2) 终止: userTrades 每个品种末页是短页 / 空页 / 越过窗口; income 末页必须是短页(满页 = 未完成), 满毫秒枚举必须以短页结束。
      (3) 游标: fromId 严格递增且 = 上一页 max(id)+1; income 的下一请求 = 取数器按上一页算出的那一个(max(time) 不 +1 / 满毫秒 page+1 /
          枚举结束后该毫秒 +1), 因而 startTime 单调不减。
    v2 取数器的凭据只有逐页 n(没有逐行证据): 只有当计数把「每页贡献了哪几行」唯一确定时(每页返回行全被保留)才算证明, 否则 unproven。
    重放只对【登记过】的取数器有效(FETCHER_REGISTRY: 源码 sha256 → 规则); 未登记 ⇒ unproven。"""
    V, U = [], []
    ev = {"fetchers": {}, "trades": collections.Counter(), "income": None}
    fsha = rd.get("fetch_devices_sha256") if isinstance(rd.get("fetch_devices_sha256"), dict) else {}
    for tool in ("fetch_trades.py", "fetch_income_paged.py"):
        h = fsha.get(tool); reg = FETCHER_REGISTRY.get(h) if isinstance(h, str) else None
        ok = bool(reg) and reg[0] == tool
        ev["fetchers"][tool] = {"sha256": h, "registered_rules": reg[1] if ok else None}
        if not ok: U.append(f"FETCHER_NOT_REGISTERED: {tool} sha256 {str(h)[:16]} — the replay reproduces only registered fetchers' rules")
    for key in ("page_limit", "income_page_limit"):
        if key in rd and rd[key] != FETCH_LIMIT:
            V.append(f"PAGE_LIMIT_NOT_FETCHER_LIMIT: {key}={rd[key]!r}, the registered fetchers' LIMIT is {FETCH_LIMIT}")
    lim = FETCH_LIMIT                                           # 取数器的常量, 不取原始件自报(自报只能被核, 不能改尺)
    per = rd.get("trades_pages_by_symbol")
    if not isinstance(per, dict):
        V.append("NO_TRADES_PAGE_RECEIPTS: 没有逐品种 userTrades 页凭据")
    else:
        missing = sorted(set(q_list) - set(per)); extra = sorted(set(per) - set(q_list))
        if missing: V.append(f"QUERIED_SYMBOL_WITHOUT_PAGE_RECEIPT: {len(missing)} {missing[:5]}")
        if extra: V.append(f"PAGE_RECEIPT_FOR_UNQUERIED_SYMBOL: {len(extra)} {extra[:5]}")
        by = collections.defaultdict(list)
        for t in trades: by[t.get("symbol") if isinstance(t, dict) else None].append(t)
        for s in sorted(set(per) & set(q_list)):
            ev["trades"][_trades_symbol(s, per[s], by.get(s, []), s_ms, e_ms, lim, V, U)] += 1
    ev["income"] = {"level": _income(rd.get("income_pages"), irows, rd.get("income_n_boundary_rows_subtracted"), s_ms, e_ms, lim, V, U),
                    "n_pages": len(rd.get("income_pages") or []), "subtracted": rd.get("income_n_boundary_rows_subtracted"),
                    "n_rows": len(irows)}
    ev["trades"] = dict(ev["trades"])
    return {"violations": V, "unproven": U, "evidence": ev}


def page_receipt_problems(rd, q_list, trades, irows, s_ms, e_ms):
    """v4.1 的接口保留: 返回清单, 空 ⇔ POPULATION_PASS。v4.2 起清单含两类, 前缀区分: 「VIOLATION …」(⇒ REFUSED_POPULATION)与
    「UNPROVEN …」(⇒ POPULATION_UNPROVEN_PAGE_EVIDENCE)。"""
    f = page_receipt_findings(rd, q_list, trades, irows, s_ms, e_ms)
    return [f"VIOLATION {x}" for x in f["violations"]] + [f"UNPROVEN {x}" for x in f["unproven"]]


def write_doc(out, doc):
    tmp = out + ".part"
    with open(tmp, "w") as fh: json.dump(doc, fh, indent=1, ensure_ascii=False, allow_nan=False)
    os.replace(tmp, out)                                      # 原子写


class NonFiniteInput(ValueError):
    """计算路径上读到非有限 / 非数值(v4 第二道防线): 输入层扫描按字段清单查, 清单漏列的字段在这里被拦下, 同样判 REFUSED_INPUT_FINITE。"""


def fnum(x):
    """装置内【所有】数值解析都走这里(v4): 非数 / NaN / ±inf 抛 NonFiniteInput, 不让它进比较表达式。"""
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise NonFiniteInput(f"nonnumeric {x!r:.40}")
    if not math.isfinite(v): raise NonFiniteInput(f"nonfinite {x!r:.40}")
    return v


def dec(x):
    v = Decimal(str(x))
    if not v.is_finite(): raise NonFiniteInput(f"nonfinite {x!r:.40}")
    return v


_CTX = {}


def main():
    try:
        return _main()
    except NonFiniteInput as e:                               # 清单漏列的字段: 仍是具名拒绝, 不是崩溃也不是静默通过
        me = os.path.abspath(__file__)
        where = [f"L{f.lineno}: {f.line}" for f in traceback.extract_tb(e.__traceback__) if os.path.abspath(f.filename) == me][-1:]
        det = {"value": str(e), "where": where, "layer": "computation-time guard (field not in the input-layer scan list)"}
        if "refusal" in _CTX: return _CTX["refusal"]("INPUT_FINITE", "计算路径上读到非有限值(输入层扫描清单未列到的字段)", det)
        print("REFUSED[INPUT_FINITE]:", json.dumps(det, ensure_ascii=False)); print("VERDICT REFUSED_INPUT_FINITE"); return RC["REFUSED"]


def _main():
    global LED
    _CTX.clear()
    av = sys.argv[1:]; flags = {}
    for f in CLI_FLAGS:
        if f in av:
            i = av.index(f); flags[f] = av[i + 1]; del av[i:i + 2]
    if "--bnb-rows" not in flags:
        print("REFUSED: --bnb-rows <INCOME_BNB_ROWS.json> 必需(BNB 余额路径; 没有它 USD 恒等式不可判)"); return 2
    if "--event" not in flags:
        print("REFUSED: --event <rebalance_id> 必需(v4 归属门: 不知道本窗应归属哪一次平仓, 就判不了「订单集非空且同属一事件」)"); return 2
    event = flags["--event"]
    ledger_root = os.path.abspath(os.path.expanduser(flags.get("--ledger-root", DEFAULT_LEDGER_ROOT)))
    LED = os.path.join(ledger_root, FR.PILOT_LOG)
    offline = True                                            # v4.1: 指数价【永远】只读缓存、不回写 —— 本装置唯一的联网是两个只读取数器
    t0, t1, out = fnum(av[0]), fnum(av[1]), av[2]
    raw_out = av[3] if len(av) > 3 else out.replace(".json", "_venue_trades.json")
    assert t1 > t0
    days = sorted({DAY(t0 - 86400), DAY(t0), DAY(t1), DAY(t1 + 86400)})
    days = [d for d in days if os.path.isdir(f"{LED}/{d}")]
    inputs = {f"{d}/{n}": hashlib.sha256(open(f"{LED}/{d}/{n}.jsonl", "rb").read()).hexdigest()[:16]
              for d in days for n in ("fills", "orders", "funding", "position_readback", "daily_nav")
              if os.path.isfile(f"{LED}/{d}/{n}.jsonl")}
    gates = {g: "NOT_EVALUATED" for g in ("INPUT_FINITE", "POPULATION", "ATTRIBUTION", "ENDPOINT", "CASH")}
    self_sha = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()

    def refusal(gate, why, detail):
        g = dict(gates); g[gate] = "FAIL"
        doc = {"receipt": "FLATTEN_WINDOW_CLOSURE", "device": f"flatten_window_closure.py {VERSION}", "self_sha256": self_sha,
               "utc": time.strftime("%FT%TZ", time.gmtime()), "argv": sys.argv[1:], "event": event, "ledger_root": ledger_root,
               "inputs_sha16": inputs, "VERDICT": f"REFUSED_{gate}", "gates": g,
               "refusal": {"gate": gate, "why": why, "detail": detail}}
        write_doc(out, doc)
        print(f"REFUSED[{gate}]: {why}", json.dumps(detail, ensure_ascii=False)[:3000])
        print("VERDICT", doc["VERDICT"])
        return RC["REFUSED"]

    _CTX["refusal"] = refusal

    def nf_detail(bad):
        c = collections.Counter((b["src"], b["field"], b["why"]) for b in bad)
        return {"n_offending_fields": len(bad), "by_source_field": [list(k) + [n] for k, n in sorted(c.items())], "sample": bad[:20]}

    BNB = {d: v["close"] for d, v in json.load(open(BNB_P))["days"].items()}

    def fee_usdt(asset, c, ts):
        if asset == "USDT": return c
        if asset == "BNB": return c * BNB[DAY(ts)]           # KeyError = 不可判, 不猜
        raise ValueError(f"commission asset {asset}")

    # ── 0. 输入层有限性(v4): 过滤键查全部载入行 —— 过滤键若是 NaN, 比较恒假会把那一行【静默排除】──
    NF = []
    for d, v in BNB.items(): check_num(NF, "BNBUSDT_daily", d, "close", v, positive=True)
    nav_rows = [r for d in days for r in rows(d, "daily_nav") if r.get("mode") in (None, "LIVE")]
    rb = [r for d in days for r in rows(d, "position_readback")]
    fills_all = FR.read_range(ledger_root, day_list=days)
    fund_all = [x for d in days for x in rows(d, "funding")]
    ord_all = [o for d in days for o in rows(d, "orders")]
    for r in nav_rows: check_num(NF, "daily_nav", r.get("nav_ts"), "nav_ts", r.get("nav_ts"))
    for r in rb: check_num(NF, "position_readback", r.get("symbol"), "read_ts", r.get("read_ts"))
    for f in fills_all: check_num(NF, "fills", (f.get("symbol"), f.get("trade_id")), "fill_ts", f.get("fill_ts"))
    for x in fund_all: check_num(NF, "funding", x.get("symbol"), "settlement_ts", x.get("settlement_ts"))
    for o in ord_all:
        for k in ("submit_ts", "first_fill_ts"): check_num(NF, "orders", o.get("symbol"), k, o.get(k), allow_none=True)
    if NF: return refusal("INPUT_FINITE", "账本过滤键或 BNB 日收盘含非有限/缺失值", nf_detail(NF))

    # ── A. 本地恒等式(fp3 §3 同义) ──
    nav = {fnum(r["nav_ts"]): r for r in nav_rows}
    r0, r1 = nav.get(t0), nav.get(t1)
    if r0 is None or r1 is None:
        print("REFUSED: t0/t1 必须是 daily_nav 的 nav_ts 原值"); return 2
    between = sorted(t for t in nav if t0 < t < t1)
    if between:
        print(f"REFUSED: (t0,t1) 之间还有 {len(between)} 行 NAV —— 用相邻两行, 否则恒等式区间不是最细的"); return 2
    # 值字段: 查【被用到的行】(v4)
    for r, nm in ((r0, "t0"), (r1, "t1")): check_num(NF, "daily_nav", nm, "nav", r.get("nav"))
    check_num(NF, "daily_nav", "t1", "external_flow_usdt", r1.get("external_flow_usdt"), allow_none=True)
    for r in rb:
        if min(abs(fnum(r["read_ts"]) - t0), abs(fnum(r["read_ts"]) - t1)) <= SNAP_TOL_S:
            check_num(NF, "position_readback", (r.get("symbol"), r.get("read_ts")), "venue_position_qty", r.get("venue_position_qty"))
            q_ = r.get("venue_position_qty")
            try: q_nonzero = bool(fnum(q_))
            except (TypeError, ValueError): q_nonzero = True
            if q_nonzero:                                     # v3 只在 q≠0 时读 notional
                check_num(NF, "position_readback", (r.get("symbol"), r.get("read_ts")), "venue_position_notional", r.get("venue_position_notional"))
    fills = [f for f in fills_all if t0 < fnum(f["fill_ts"]) <= t1]
    for f in fills:
        k = (f.get("symbol"), f.get("trade_id"))
        check_num(NF, "fills", k, "fill_notional", f.get("fill_notional"))
        check_num(NF, "fills", k, "fill_px", f.get("fill_px"), positive=True)
        check_num(NF, "fills", k, "commission", f.get("commission"), allow_none=True)
    FUND = [x for x in fund_all if t0 < fnum(x["settlement_ts"]) <= t1]
    for x in FUND: check_num(NF, "funding", x.get("symbol"), "funding_paid", x.get("funding_paid"), allow_none=True)
    # 执行器本窗的订单(按 submit_ts 或 first_fill_ts 落在窗内)
    ords = [o for o in ord_all if any(o.get(k) is not None and t0 < fnum(o[k]) <= t1 for k in ("submit_ts", "first_fill_ts"))]
    for o in ords:
        if o.get("order_type") == "protective_flatten":
            for k in ("first_fill_ts", "last_fill_ts", "filled_notional"):
                check_num(NF, "orders", (o.get("symbol"), o.get("submit_ts")), k, o.get(k), allow_none=True)
    if NF: return refusal("INPUT_FINITE", "账本值字段含非有限/缺失值", nf_detail(NF))

    def snap(ts):
        c = collections.defaultdict(list)
        for r in rb:
            if abs(fnum(r["read_ts"]) - ts) <= SNAP_TOL_S: c[fnum(r["read_ts"])].append(r)
        if not c: return None, None
        st = min(c, key=lambda k: (abs(k - ts), k)); m = {}
        for r in c[st]:
            q = fnum(r["venue_position_qty"])
            if r["symbol"] in m and m[r["symbol"]][0] != q: return None, "CONFLICT"
            m[r["symbol"]] = (q, abs(fnum(r["venue_position_notional"])) / abs(q) if q else 0.0)
        return m, st
    m0, s0 = snap(t0); m1, s1 = snap(t1)
    if m0 is None or m1 is None:
        print("UNAVAILABLE: 端点无同次调用的持仓快照", s0, s1); return 3
    sgn = lambda side: 1.0 if str(side).upper() == "BUY" else -1.0
    cash = collections.defaultdict(float); q_rec = collections.defaultdict(float)
    for f in fills:
        q = fnum(f["fill_notional"]) / fnum(f["fill_px"]) * sgn(f["side"])
        cash[f["symbol"]] += q * fnum(f["fill_px"]); q_rec[f["symbol"]] += q
    names_local = set(m0) | set(m1) | set(q_rec)
    term = sum(m1.get(s, (0, 0))[0] * m1.get(s, (0, 0))[1] - m0.get(s, (0, 0))[0] * m0.get(s, (0, 0))[1] - cash[s] for s in names_local)
    fund = sum(fnum(x.get("funding_paid") or 0.0) for x in FUND)
    fees_led = sum(fee_usdt(f.get("commission_asset"), fnum(f.get("commission") or 0.0), f["fill_ts"]) for f in fills)
    dnav = fnum(r1["nav"]) - fnum(r1.get("external_flow_usdt") or 0.0) - fnum(r0["nav"])
    resid = dnav - (term + fund - fees_led)
    tol = max(2.0, 0.5e-4 * fnum(r0["nav"]))
    gaps = {s: (m0.get(s, (0, 0))[0] + q_rec[s]) - m1.get(s, (0, 0))[0] for s in names_local}
    gaps = {s: g for s, g in gaps.items() if abs(g) * (m1.get(s, (0, 0))[1] or m0.get(s, (0, 0))[1] or 1.0) > 1.0}
    A = {"t0": U(t0), "t1": U(t1), "snapshot_minus_nav_s": [round(s0 - t0, 3), round(s1 - t1, 3)],
         "n_pos_t0": sum(1 for v in m0.values() if v[0]), "n_pos_t1": sum(1 for v in m1.values() if v[0]),
         "dnav_ex_flow": round(dnav, 4), "mtm_positions_and_fills": round(term, 4), "funding_local": round(fund, 4),
         "fees_ledger": round(fees_led, 4), "residual": round(resid, 4), "tol": round(tol, 4),
         "n_ledger_fills": len(fills), "n_position_gaps_gt_1usd": len(gaps)}
    print("A 本地恒等式:", json.dumps(A, ensure_ascii=False))
    ord_types = collections.Counter(o.get("order_type") for o in ords)
    print("  执行器本窗订单:", dict(ord_types))

    # ── B. 场所(只读密钥): income 全品种 + 逐名 userTrades ──
    s_ms, e_ms = int(t0 * 1000) + 1, int(t1 * 1000)          # (t0, t1] 的毫秒闭区间近似; 端点各差 <1 ms, 快照与 NAV 同刻(Δ 0.0 s)
    if "--reuse-raw" in flags:
        # 复用一次【已完整】的拉取 —— 复用不是降低标准: 与新拉取走【同一条】人口校验(下方), 不另开宽松分支。
        rd = json.load(open(flags["--reuse-raw"]))
        raw_out = flags["--reuse-raw"]
    else:
        # v4.1 新拉取: 只经两个只读取数器(fetch_income_paged.run / fetch_trades.fetch_trades, 签名 GET, 硬编码只读密钥文件)。
        # 原始件是只追加的收据: 目标已存在 ⇒ 拒绝, 永不覆盖旧拉取。每个被查询品种的逐页凭据、income 的逐页凭据、实际查询清单全部落盘;
        # 不完整的拉取也落盘(completeness=INCOMPLETE, 供诊断), 但下方的完整性检查使它永远不能被复用成收据。
        if os.path.exists(raw_out) or os.path.exists(raw_out + ".part"):
            print("REFUSED: 原始件目标已存在(拉取收据只追加, 不覆盖):", raw_out); return 2
        import fetch_trades as FT, fetch_income_paged as FI
        f_start = time.strftime("%FT%TZ", time.gmtime())
        ipages, irows_f, istatus, iwhy, isub = FI.run(s_ms, e_ms, "closure")
        inc_syms_f = {r["symbol"] for r in irows_f if r.get("symbol") and r["incomeType"] in ("COMMISSION", "REALIZED_PNL")}
        names_f = sorted(names_local | inc_syms_f)
        trades_f, per_sym, bad = [], {}, []
        if istatus == "COMPLETE":
            for i, s in enumerate(names_f, 1):
                pages, rs, st, why = FT.fetch_trades(s, s_ms, e_ms)
                per_sym[s] = {"pages": pages, "completeness": st, "incomplete_reason": why, "n_rows": len(rs)}
                trades_f += rs
                if st != "COMPLETE": bad.append((s, why))
                if i % 40 == 0: print(f"    trades {i}/{len(names_f)}", flush=True)
        complete = istatus == "COMPLETE" and not bad and len(per_sym) == len(names_f)
        rd = {"device": f"flatten_window_closure.py {VERSION}", "raw_format": RAW_FORMAT_FRESH,
              "endpoint": "/fapi/v1/userTrades (per symbol) + /fapi/v1/income (all types)", "window_ms": [s_ms, e_ms],
              "fetched_utc": [f_start, time.strftime("%FT%TZ", time.gmtime())],
              "fetch_devices_sha256": {"fetch_trades.py": sha256_file(FT.__file__), "fetch_income_paged.py": sha256_file(FI.__file__)},
              "page_limit": FT.LIMIT, "income_page_limit": FI.LIMIT,
              "symbols_required_at_fetch": names_f, "symbols_queried": list(per_sym), "n_symbols_queried": len(per_sym),
              "n_rows": len(trades_f), "completeness": "COMPLETE" if complete else "INCOMPLETE",
              "incomplete_symbols": [[s, w] for s, w in bad],
              "trades_pages_by_symbol": per_sym,
              "income_pages": ipages, "income_completeness": istatus, "income_incomplete_reason": iwhy,
              "income_n_boundary_rows_subtracted": isub,
              "body": trades_f, "income_rows": irows_f}
        tmp = raw_out + ".part"
        with open(tmp, "w") as fh: json.dump(rd, fh)
        os.replace(tmp, raw_out)                              # 原子写: 读者永远看不到半份拉取
        if not complete:
            print("UNAVAILABLE: 拉取不完整(原始件已落盘并标 INCOMPLETE, 不可复用):", iwhy, bad[:10]); return 3
    # 人口校验(v4.1, 复用与新拉取同一条路): 窗口与完整性声明 → 个数 → 集合 → 逐页凭据
    if rd.get("window_ms") != [s_ms, e_ms] or rd.get("completeness") != "COMPLETE" or rd.get("income_completeness") != "COMPLETE":
        print("REFUSED: 原始件的窗口/完整性不符", rd.get("window_ms"), [s_ms, e_ms], rd.get("completeness"), rd.get("income_completeness")); return 2
    irows, trades = rd["income_rows"], rd["body"]
    inc_syms = {r["symbol"] for r in irows if r.get("symbol") and r["incomeType"] in ("COMMISSION", "REALIZED_PNL")}
    names = sorted(names_local | inc_syms)
    q_list = rd.get("symbols_queried")
    has_pages = "trades_pages_by_symbol" in rd or "income_pages" in rd
    pop = {"n_required": len(names), "n_symbols_queried_declared": rd.get("n_symbols_queried"),
           "queried_list_present": q_list is not None, "page_receipts_present": has_pages, "raw_format": rd.get("raw_format")}
    if rd.get("n_symbols_queried") != len(names):
        return refusal("POPULATION", "原始件当初查询的品种个数与本次应查的个数不同", pop)
    if q_list is not None:
        if len(q_list) != len(set(q_list)) or set(q_list) != set(names) or len(q_list) != rd.get("n_symbols_queried"):
            pop.update(only_in_queried=sorted(set(q_list) - set(names))[:20], only_in_required=sorted(set(names) - set(q_list))[:20],
                       n_duplicate_in_queried=len(q_list) - len(set(q_list)))
            return refusal("POPULATION", "原始件当初查询的品种【集合】与本次应查的集合不同(个数相同也拒)", pop)
        queried = set(q_list)
        if has_pages:
            fnd = page_receipt_findings(rd, q_list, trades, irows, s_ms, e_ms)
            pop["page_evidence"] = fnd["evidence"]
            if fnd["violations"]:                             # 凭据与取数器自己的规则矛盾 ⇒ 拒(与 v4.1「计数不合 ⇒ REFUSED」同一档)
                pop.update(n_page_receipt_problems=len(fnd["violations"]), page_receipt_problems=fnd["violations"][:20],
                           n_page_evidence_unproven=len(fnd["unproven"]), page_evidence_unproven=fnd["unproven"][:20])
                return refusal("POPULATION", "逐页凭据与取数器自己的规则矛盾(状态 / 计数 / 行身份 / 终止 / 游标 / INCOMPLETE / 缺凭据)", pop)
            if fnd["unproven"]:                               # 不矛盾但证不了 ⇒ 具名未证, 永不 PASS
                tier = TIER_PAGES
                pop.update(n_page_evidence_unproven=len(fnd["unproven"]), page_evidence_unproven=fnd["unproven"][:40])
            else:
                tier = TIER_PASS
        else:
            tier = TIER_LIST                                  # 有查询清单、无逐页凭据: 集合相等, 但每个品种是否取全仍只是自述
    else:
        if has_pages:
            return refusal("POPULATION", "有逐页凭据却没有查询清单 —— 凭据无法对应到查询人口", pop)
        tier, queried = TIER_COUNT, set(names)                # 旧原始件: 查询集合无记录, 只能以应查集合代入 —— 未证
    # 原始件数值字段(v4 输入层): userTrades 与 income 行全查
    for t in trades:
        for fld in ("time", "qty", "quoteQty", "commission", "realizedPnl", "price"):
            check_num(NF, "userTrades", (t.get("symbol"), t.get("id")), fld, t.get(fld))
    for r in irows:
        for fld in ("income", "time"):
            check_num(NF, "income", (r.get("incomeType"), r.get("tranId")), fld, r.get(fld))
    if NF: return refusal("INPUT_FINITE", "场所原始件含非有限/缺失值", nf_detail(NF))
    stray = sorted({t["symbol"] for t in trades} - queried)
    if stray:
        pop["userTrades_symbols_not_queried"] = stray[:20]
        return refusal("POPULATION", "userTrades 含未被查询的品种", pop)
    pop.update(tier=tier, required_symbols=names,
               required_symbols_sha256=hashlib.sha256(json.dumps(names).encode()).hexdigest(),
               reads=("POPULATION_PASS (v4.2): the saved query list equals the required set AND, replaying each registered fetcher's own "
                      "rules over the page receipts, (1) the rows the pages returned and the rule keeps are exactly the saved rows "
                      "(userTrades by (symbol, id); income as a full-row multiset after boundary subtraction) and every page's n equals the "
                      "rows it lists, (2) every userTrades symbol ends on a short / empty / past-window page and the income pull ends on a short "
                      "page (saturated milliseconds enumerated to a short page), (3) every cursor is the one the fetcher computes (fromId = "
                      "max(id)+1 strictly increasing; income startTime = previous max(time), page+1, or ms+1). Count-only (v2) receipts pass "
                      "only where the counts force the page split (every returned row kept). POPULATION_UNPROVEN_PAGE_EVIDENCE: receipts "
                      "consistent but insufficient (named reasons). POPULATION_UNPROVEN_NO_PAGE_RECEIPTS: query list equal but no page receipts. "
                      "POPULATION_UNPROVEN_COUNT_ONLY: legacy raw without a query list; only the count could be compared."))
    gates["INPUT_FINITE"] = "PASS"                             # 余下的输入(BNB 路径行、指数价)在 D 段载入时再查, 不过即拒
    gates["POPULATION"] = {TIER_PASS: "PASS", TIER_PAGES: "UNPROVEN_PAGE_EVIDENCE", TIER_LIST: "UNPROVEN_NO_PAGE_RECEIPTS",
                           TIER_COUNT: "UNPROVEN_COUNT_ONLY"}[tier]

    # ── C. 闭合 ──
    led_ids = {(f["symbol"], str(f["trade_id"])) for f in fills}
    ven_ids = {(t["symbol"], str(t["id"])) for t in trades}
    ledger_only = sorted(led_ids - ven_ids)                  # 账本有、场所无 = 合同违例
    missing = [t for t in trades if (t["symbol"], str(t["id"])) not in led_ids]
    q_miss = collections.defaultdict(float)
    for t in missing: q_miss[t["symbol"]] += (1.0 if t["buyer"] else -1.0) * abs(fnum(t["qty"]))
    # (a) 逐名数量闭合: q0 + 账本成交 + 缺失成交 == q1
    qfail = []
    for s in sorted(names_local | set(q_miss)):
        q0 = m0.get(s, (0, 0))[0]; q1 = m1.get(s, (0, 0))[0]; mk = m1.get(s, (0, 0))[1] or m0.get(s, (0, 0))[1]
        d = q0 + q_rec[s] + q_miss[s] - q1
        if abs(d) * (mk or 1.0) > 0.01 or (mk == 0 and abs(d) > 1e-9): qfail.append((s, round(d, 10)))
    # (b) 现金闭合
    miss_cash = sum((1.0 if t["buyer"] else -1.0) * abs(fnum(t["quoteQty"])) for t in missing)
    miss_fee_native = collections.Counter()
    for t in missing: miss_fee_native[t["commissionAsset"]] += fnum(t["commission"])
    miss_fee = sum(fee_usdt(t["commissionAsset"], fnum(t["commission"]), int(t["time"]) / 1000) for t in missing)
    predicted = -miss_cash - miss_fee
    gap_cash = resid - predicted
    # (c) 两端点交叉: userTrades vs income (全部场所成交, 不只缺失的) —— 窗口总额(v3, 保留在 CASH 条件里)
    inc = collections.defaultdict(float)
    for r in irows: inc[(r["incomeType"], r.get("asset"))] += fnum(r["income"])
    tr_fee = collections.Counter(); tr_rpnl = 0.0
    for t in trades: tr_fee[t["commissionAsset"]] += fnum(t["commission"]); tr_rpnl += fnum(t["realizedPnl"])
    cross = {"commission_by_asset_userTrades": {k: round(v, 8) for k, v in tr_fee.items()},
             "commission_by_asset_income": {a: round(-v, 8) for (ty, a), v in inc.items() if ty == "COMMISSION"},
             "realized_pnl_userTrades": round(tr_rpnl, 6),
             "realized_pnl_income": round(sum(v for (ty, a), v in inc.items() if ty == "REALIZED_PNL"), 6),
             "funding_income": round(sum(v for (ty, a), v in inc.items() if ty == "FUNDING_FEE"), 6), "funding_local": round(fund, 6),
             "income_types": sorted({ty for ty, a in inc})}
    cross_ok = (all(abs(cross["commission_by_asset_userTrades"].get(a, 0.0) - cross["commission_by_asset_income"].get(a, 0.0)) < 1e-6
                    for a in set(cross["commission_by_asset_userTrades"]) | set(cross["commission_by_asset_income"]))
                and abs(cross["realized_pnl_userTrades"] - cross["realized_pnl_income"]) < 1e-4)
    # (c') v4 ENDPOINT: 逐 (symbol, tradeId) 对账 —— 总额相等挡不住「互相抵消」与「身份全错而金额总和不变」
    tkeys = collections.Counter((t["symbol"], str(t["id"])) for t in trades)
    dup_trade = sorted(k for k, n in tkeys.items() if n > 1)
    tran = collections.Counter((r["incomeType"], str(r.get("tranId"))) for r in irows)
    dup_tran = sorted(k for k, n in tran.items() if n > 1)
    i_fee, i_rp = collections.defaultdict(list), collections.defaultdict(list)
    for r in irows:
        k = (r.get("symbol"), str(r.get("tradeId")))
        if r["incomeType"] == "COMMISSION": i_fee[k].append(r)
        elif r["incomeType"] == "REALIZED_PNL": i_rp[k].append(r)
    dup_inc = sorted([("COMMISSION",) + k for k, v in i_fee.items() if len(v) > 1] + [("REALIZED_PNL",) + k for k, v in i_rp.items() if len(v) > 1])
    fee_bad, rp_bad, asset_bad, t_orph = [], [], [], []
    tmap = {}
    for t in trades: tmap.setdefault((t["symbol"], str(t["id"])), t)
    for k, t in tmap.items():
        c = dec(t["commission"]); rf = i_fee.get(k, [])
        if len(rf) == 1:
            if rf[0].get("asset") != t["commissionAsset"]: asset_bad.append([k, t["commissionAsset"], rf[0].get("asset")])
            if abs(-dec(rf[0]["income"]) - c) > ENDPOINT_TOL: fee_bad.append([k, str(t["commission"]), str(rf[0]["income"])])
        elif not rf and c != 0: t_orph.append(["COMMISSION", k, str(t["commission"])])
        p = dec(t["realizedPnl"]); rr = i_rp.get(k, [])
        if len(rr) == 1:
            if abs(dec(rr[0]["income"]) - p) > ENDPOINT_TOL: rp_bad.append([k, str(t["realizedPnl"]), str(rr[0]["income"])])
        elif not rr and p != 0: t_orph.append(["REALIZED_PNL", k, str(t["realizedPnl"])])
    i_orph = ([["COMMISSION", k, [r["income"] for r in v]] for k, v in i_fee.items() if k not in tmap and any(dec(r["income"]) != 0 for r in v)]
              + [["REALIZED_PNL", k, [r["income"] for r in v]] for k, v in i_rp.items() if k not in tmap and any(dec(r["income"]) != 0 for r in v)])
    oid_syms = collections.defaultdict(set)
    for t in trades: oid_syms[t["orderId"]].add(t["symbol"])
    oid_collisions = sorted([str(o), sorted(s)] for o, s in oid_syms.items() if len(s) > 1)
    t_out = sum(1 for t in trades if not (s_ms <= int(t["time"]) <= e_ms))
    i_out = sum(1 for r in irows if not (s_ms <= int(r["time"]) <= e_ms))
    ep_reasons = [f"{n}: {len(v) if isinstance(v, list) else v}" for n, v in (
        ("DUPLICATE_TRADE_IDENTITY", dup_trade), ("DUPLICATE_INCOME_TRANID", dup_tran), ("DUPLICATE_INCOME_PER_TRADE_KEY", dup_inc),
        ("COMMISSION_PER_TRADE_MISMATCH", fee_bad), ("COMMISSION_ASSET_MISMATCH", asset_bad), ("REALIZED_PNL_PER_TRADE_MISMATCH", rp_bad),
        ("USERTRADES_NONZERO_ORPHAN", t_orph), ("INCOME_NONZERO_ORPHAN", i_orph), ("CROSS_SYMBOL_ORDERID_COLLISION", oid_collisions),
        ("USERTRADES_OUTSIDE_WINDOW", t_out), ("INCOME_OUTSIDE_WINDOW", i_out)) if v]
    gates["ENDPOINT"] = "PASS" if not ep_reasons else "FAIL"
    endpoint = {"key": "(symbol, tradeId); COMMISSION compared with asset; tolerance 1e-8 (Decimal)", "n_trade_keys": len(tmap),
                "n_income_commission_keys": len(i_fee), "n_income_realized_pnl_keys": len(i_rp),
                "n_duplicate_trade_identity": len(dup_trade), "n_duplicate_income_tranId": len(dup_tran),
                "n_duplicate_income_per_trade_key": len(dup_inc), "n_commission_mismatch": len(fee_bad),
                "n_commission_asset_mismatch": len(asset_bad), "n_realized_pnl_mismatch": len(rp_bad),
                "n_userTrades_nonzero_orphans": len(t_orph), "n_income_nonzero_orphans": len(i_orph),
                "n_cross_symbol_orderId_collisions": len(oid_collisions), "n_userTrades_outside_window": t_out,
                "n_income_outside_window": i_out,
                "samples": {"commission_mismatch": fee_bad[:5], "realized_pnl_mismatch": rp_bad[:5], "asset_mismatch": asset_bad[:5],
                            "userTrades_orphans": t_orph[:5], "income_orphans": i_orph[:5], "orderId_collisions": oid_collisions[:5],
                            "duplicate_trade": dup_trade[:5], "duplicate_tranId": dup_tran[:5], "duplicate_income_key": dup_inc[:5]},
                "fail_reasons": ep_reasons, "ENDPOINT": gates["ENDPOINT"]}
    # 账本已记成交 vs 场所: 同一 (symbol, trade id) 的金额与手续费必须一致(正对照: 09-09 / 09-12 平仓成交已入账)
    vt = {(t["symbol"], str(t["id"])): t for t in trades}
    led_amt = [abs(fnum(f["fill_notional"]) - abs(fnum(vt[k]["quoteQty"]))) for f in fills
               for k in [(f["symbol"], str(f["trade_id"]))] if k in vt]
    led_fee = [abs(fnum(f.get("commission") or 0.0) - fnum(vt[k]["commission"])) for f in fills
               for k in [(f["symbol"], str(f["trade_id"]))] if k in vt and f.get("commission_asset") == vt[k]["commissionAsset"]]
    led_asset_mismatch = sum(1 for f in fills for k in [(f["symbol"], str(f["trade_id"]))]
                             if k in vt and f.get("commission_asset") != vt[k]["commissionAsset"])
    # 订单身份(v2): 执行器每张 protective_flatten 单记着场所的【首/末成交毫秒】(场所时钟)与签名成交额。
    #   场所端按 (symbol, orderId) 分组(v4; v3 只按 orderId); 一张执行器单 ⇔ 同 (symbol, side) 且首/末成交毫秒落在其内的场所订单 —— 必须【恰好一个】, 金额再核一次。
    #   这把「按 ±120 s 时间窗归因」换成「按订单身份归因」: 旧窗以本地回读时刻为中心, 平仓开始得更早,
    #   09-06 桶漏了前 23 秒(31 名)、08-26 桶漏了前 26 秒 —— 不是个例而是窗规则的类缺陷, 所以换规则而不是挪窗。
    #   v4: 候选唯一 ≠ 双射。每个场所订单被几张执行器单认领, 逐个计数; >1 即 FAIL(v3 的 matched[venue]=o 会让后来者静默覆盖前者)。
    vo = collections.defaultdict(list)
    for t in trades: vo[(t["symbol"], t["orderId"])].append(t)
    mixed_side = sorted([k[0], str(k[1])] for k, ts_ in vo.items() if len({bool(t["buyer"]) for t in ts_}) > 1)
    vspan = collections.defaultdict(list)                     # (symbol, side) -> [((symbol, orderId), first ms, last ms, signed cash)]
    for vk, ts_ in vo.items():
        vspan[(vk[0], "buy" if ts_[0]["buyer"] else "sell")].append(
            (vk, min(int(t["time"]) for t in ts_), max(int(t["time"]) for t in ts_),
             sum((1.0 if t["buyer"] else -1.0) * abs(fnum(t["quoteQty"])) for t in ts_)))
    flat = [o for o in ords if o.get("order_type") == "protective_flatten"]
    assign = collections.defaultdict(list); zero, many, amt, unfilled = [], [], [], []
    for i, o in enumerate(flat):
        if o.get("first_fill_ts") is None or o.get("last_fill_ts") is None:
            zero.append(o["symbol"]); unfilled.append(o["symbol"]); continue
        f_ms, l_ms = int(round(fnum(o["first_fill_ts"]) * 1000)), int(round(fnum(o["last_fill_ts"]) * 1000))
        fn = o.get("filled_notional")
        c = [vk for vk, a, b, v in vspan.get((o["symbol"], str(o.get("side")).lower()), [])
             if a - 1 <= f_ms <= b + 1 and a - 1 <= l_ms <= b + 1 and fn is not None and abs(v - fnum(fn)) < 1e-6]
        if len(c) == 1:
            assign[c[0]].append(i)
            v = sum((1.0 if t["buyer"] else -1.0) * abs(fnum(t["quoteQty"])) for t in vo[c[0]])
            amt.append(abs(v - fnum(o["filled_notional"])) if o.get("filled_notional") is not None else float("inf"))
        elif not c: zero.append(o["symbol"])
        else: many.append((o["symbol"], [vk[1] for vk in c]))
    matched = {vk: flat[ix[0]] for vk, ix in assign.items()}  # 键集合与 v3 的 matched 相同(下游数字只用键)
    consumed_twice = {vk: len(ix) for vk, ix in assign.items() if len(ix) > 1}
    ex_id = collections.Counter((o.get("symbol"), o.get("side"), o.get("submit_ts"), o.get("first_fill_ts"), o.get("last_fill_ts"),
                                 o.get("filled_notional")) for o in flat)
    ex_dup = sum(n - 1 for n in ex_id.values() if n > 1)
    event_all = [o for o in ord_all if o.get("order_type") == "protective_flatten" and o.get("rebalance_id") == event]
    event_in = [o for o in flat if o.get("rebalance_id") == event]
    foreign = sorted({str(o.get("rebalance_id")) for o in flat if o.get("rebalance_id") != event})
    at_reasons = []
    if not flat: at_reasons.append("EMPTY_EXECUTOR_FLATTEN_SET: 本窗没有任何 protective_flatten 执行器订单")
    if foreign: at_reasons.append(f"FOREIGN_EVENT_ORDERS_IN_WINDOW: {sum(1 for o in flat if o.get('rebalance_id') != event)} 单属于 {foreign[:5]}")
    if len(event_all) != len(event_in): at_reasons.append(f"EVENT_NOT_CONTAINED_IN_WINDOW: 载入日内 {len(event_all)} 单, 窗内 {len(event_in)} 单")
    if unfilled: at_reasons.append(f"EXECUTOR_ORDER_WITHOUT_FILL_TIMES: {len(unfilled)}")
    if len(zero) - len(unfilled): at_reasons.append(f"UNMATCHED: {len(zero) - len(unfilled)}")
    if many: at_reasons.append(f"AMBIGUOUS: {len(many)}")
    if consumed_twice: at_reasons.append(f"VENUE_ORDER_CONSUMED_MORE_THAN_ONCE: {len(consumed_twice)} 个场所订单被 {sum(consumed_twice.values())} 张执行器单认领")
    if ex_dup: at_reasons.append(f"EXECUTOR_DUPLICATE_ROWS: {ex_dup}")
    if mixed_side: at_reasons.append(f"VENUE_ORDER_MIXED_SIDE: {len(mixed_side)}")
    if len(flat) != len(assign): at_reasons.append(f"LEFT_RIGHT_COUNT_MISMATCH: 执行器 {len(flat)} 单 vs 被消费的场所订单 {len(assign)} 个")
    gates["ATTRIBUTION"] = "PASS" if not at_reasons else "FAIL"
    attribution = {"event": event, "venue_order_key": "(symbol, orderId)", "n_executor_flatten_orders_in_window": len(flat),
                   "n_event_flatten_orders_in_loaded_days": len(event_all), "n_event_flatten_orders_in_window": len(event_in),
                   "foreign_rebalance_ids_in_window": foreign[:10], "n_executor_orders_without_fill_times": len(unfilled),
                   "n_unmatched": len(zero), "n_ambiguous": len(many), "n_executor_duplicate_rows": ex_dup,
                   "n_venue_orders_consumed": len(assign), "n_venue_orders_consumed_more_than_once": len(consumed_twice),
                   "consumed_more_than_once_sample": [[vk[0], str(vk[1]), n] for vk, n in list(consumed_twice.items())[:10]],
                   "n_venue_orders_mixed_side": len(mixed_side), "left_right_counts_equal": len(flat) == len(assign),
                   "fail_reasons": at_reasons, "ATTRIBUTION": gates["ATTRIBUTION"]}
    ft = [t for vk in matched for t in vo[vk]]
    ft_fee_native = collections.Counter()
    for t in ft: ft_fee_native[t["commissionAsset"]] += fnum(t["commission"])
    ft_fee = sum(fee_usdt(t["commissionAsset"], fnum(t["commission"]), int(t["time"]) / 1000) for t in ft)
    ft_rpnl = sum(fnum(t["realizedPnl"]) for t in ft)
    groups = sorted({o.get("rebalance_id") for o in flat})
    other_missing = [t for t in missing if (t["symbol"], t["orderId"]) not in matched]
    om_orders = collections.defaultdict(list)
    for t in other_missing: om_orders[(t["symbol"], t["orderId"])].append(t)
    flatten = {"rebalance_ids": groups, "n_executor_flatten_orders": len(flat), "n_matched_one_to_one": len(matched),
               "n_no_venue_order": len(zero), "no_venue_order": zero[:10], "n_ambiguous": len(many), "ambiguous": many[:10],
               "max_abs_signed_notional_diff_executor_vs_venue": (round(max(amt), 6) if amt else None),
               "n_trades": len(ft), "n_trades_already_in_ledger": sum(1 for t in ft if (t["symbol"], str(t["id"])) in led_ids),
               "time_span": ([U(min(int(t["time"]) for t in ft) / 1000), U(max(int(t["time"]) for t in ft) / 1000)] if ft else None),
               "gross_usdt": round(sum(abs(fnum(t["quoteQty"])) for t in ft), 4),
               "realized_pnl_venue": round(ft_rpnl, 4), "fee_native": {k: round(v, 8) for k, v in ft_fee_native.items()},
               "fee_usdt_eq": round(ft_fee, 4), "realized_after_fee": round(ft_rpnl - ft_fee, 4),
               "reads": "realized P&L of the flatten ORDERS (identity-joined), measured against each name's average cost basis — "
                        "a cash identity, NOT the counterfactual cost of flattening"}
    other = {"n_trades": len(other_missing), "n_orders": len(om_orders),
             "orders": [{"orderId": vk[1], "symbol": ts_[0]["symbol"], "side": "buy" if ts_[0]["buyer"] else "sell",
                         "first": U(min(int(t["time"]) for t in ts_) / 1000), "n": len(ts_),
                         "signed_cash": round(sum((1.0 if t["buyer"] else -1.0) * abs(fnum(t["quoteQty"])) for t in ts_), 4),
                         "realized": round(sum(fnum(t["realizedPnl"]) for t in ts_), 4)} for vk, ts_ in list(om_orders.items())[:40]],
             "reads": "venue trades in the window that are absent from the ledger AND do not belong to an identity-matched flatten order"}
    # ── D. USD 计价恒等式(v3) ──
    bnb_rows = json.load(open(flags["--bnb-rows"]))
    if bnb_rows.get("completeness") != "COMPLETE": print("UNAVAILABLE: BNB 余额路径输入不完整"); return 3
    for r in bnb_rows["body"]:
        if r.get("asset") == "BNB":
            for fld in ("income", "time"): check_num(NF, "bnb_rows", (r.get("incomeType"), r.get("tranId")), fld, r.get(fld))
    if NF: return refusal("INPUT_FINITE", "BNB 余额路径行含非有限/缺失值", nf_detail(NF))
    path = UV.BnbPath(bnb_rows["body"])
    try:
        p0, p1, b0, b1 = (UV.p_usdt(t0, offline=offline), UV.p_usdt(t1, offline=offline),
                          UV.b_bnb(t0, offline=offline), UV.b_bnb(t1, offline=offline))
    except KeyError as e:
        print("UNAVAILABLE: 离线复用时指数价缓存缺分钟(不联网补):", e); return 3
    for nm, v in (("p_usdt_t0", p0), ("p_usdt_t1", p1), ("b_bnb_t0", b0), ("b_bnb_t1", b1)):
        check_num(NF, "index_price", nm, "value", v, positive=True)
    if NF: return refusal("INPUT_FINITE", "指数价非有限/非正", nf_detail(NF))
    B0, B1_path = path.at(t0), path.at(t1)
    N0, N1 = fnum(r0["nav"]), fnum(r1["nav"])
    W0 = (N0 - b0 * B0) / p0
    xfer = collections.defaultdict(float)
    for r in irows:
        if r["incomeType"] == "TRANSFER": xfer[r.get("asset")] += fnum(r["income"])
    # DELIVERED_SETTELMENT(场所拼写)= 合约下市结算: 场所把它作为一笔 userTrade 给出(08-26 SCRT/STORJ 已在 RESULT_FP3_I1 §3.1 核过),
    # 现金由那笔成交承担; 这条收入行与 REALIZED_PNL 一样是钱包对成交的记账, 不进恒等式, 否则重复。
    other_types = sorted({r["incomeType"] for r in irows} - {"TRANSFER", "COMMISSION", "REALIZED_PNL", "FUNDING_FEE", "DELIVERED_SETTELMENT"})
    fund_v = sum(fnum(r["income"]) for r in irows if r["incomeType"] == "FUNDING_FEE" and r.get("asset") == "USDT")
    fee_u = sum(fnum(t["commission"]) for t in trades if t["commissionAsset"] == "USDT")
    fee_b = sum(fnum(t["commission"]) for t in trades if t["commissionAsset"] == "BNB")
    bad_assets = sorted({t["commissionAsset"] for t in trades} - {"USDT", "BNB"} | {a for a in xfer if a not in ("USDT", "BNB")})
    term_full = term - miss_cash                              # 账本成交现金已在 term 里; 缺失成交的现金补上
    W1 = W0 + term_full + fund_v - fee_u + xfer.get("USDT", 0.0)
    B1 = B0 - fee_b + xfer.get("BNB", 0.0)
    resid_usd = N1 - (p1 * W1 + b1 * B1); resid_v3 = resid_usd / p1
    ext_led = fnum(r1.get("external_flow_usdt") or 0.0)
    D = {"p_usdt": [round(p0, 8), round(p1, 8)], "b_bnb": [round(b0, 6), round(b1, 6)], "bnb_balance": [round(B0, 8), round(B1, 8)],
         "bnb_balance_path_at_t1": round(B1_path, 8), "bnb_path_vs_window_rollforward": round(B1 - B1_path, 10),
         "W0_usdt": round(W0, 4), "W1_pred_usdt": round(W1, 4), "N0_usd": N0, "N1_usd": N1,
         "transfers_venue_in_window": {k: round(v, 8) for k, v in xfer.items()}, "external_flow_usdt_ledger_row_t1": ext_led,
         "funding_venue": round(fund_v, 6), "funding_local": round(fund, 6), "fee_usdt": round(fee_u, 6), "fee_bnb": round(fee_b, 10),
         "other_income_types_in_window": other_types, "non_usdt_bnb_assets": bad_assets,
         "residual_v3_usdt": round(resid_v3, 4), "residual_v2_usdt_caliber": round(gap_cash, 4), "tol": round(tol, 4),
         "reads": "residual_v3 is the residual of the identity written in the account's own unit; residual_v2 is the USDT-only closure gap kept for comparison"}
    tmin = min((int(t["time"]) for t in missing), default=None); tmax = max((int(t["time"]) for t in missing), default=None)
    closed = (not other_types and not bad_assets and abs(D["bnb_path_vs_window_rollforward"]) < 1e-9 and not ledger_only and not qfail and cross_ok
              and (max(led_amt) if led_amt else 0.0) < 1e-6 and (max(led_fee) if led_fee else 0.0) < 1e-8 and led_asset_mismatch == 0)
    closed_v3 = closed and abs(resid_v3) <= tol
    gates["CASH"] = "PASS" if closed_v3 else "FAIL"
    # ── E. 判词(v4): 现金闭合不能代替身份归属; 取数人口未证时不许写成裸 CLOSED ──
    core = gates["INPUT_FINITE"] == "PASS" and gates["ATTRIBUTION"] == "PASS" and gates["ENDPOINT"] == "PASS"
    failed = [g for g in ("INPUT_FINITE", "ATTRIBUTION", "ENDPOINT", "CASH") if gates[g] != "PASS"]
    accept = lambda cash_ok: ("OPEN" if not (core and cash_ok) else ("CLOSED" if tier == TIER_PASS else "CLOSED_POPULATION_UNPROVEN"))
    verdict = accept(closed_v3)
    C = {"n_venue_trades": len(trades), "n_symbols_queried": len(names), "n_income_only_symbols": len(inc_syms - names_local),
         "n_ledger_only_trades": len(ledger_only), "ledger_only_sample": ledger_only[:10],
         "ledger_vs_venue_same_trade": {"n": len(led_amt), "max_abs_notional_diff": (round(max(led_amt), 9) if led_amt else None),
                                        "max_abs_commission_diff": (round(max(led_fee), 10) if led_fee else None),
                                        "n_commission_asset_mismatch": led_asset_mismatch},
         "n_missing_trades": len(missing), "n_missing_symbols": len({t['symbol'] for t in missing}),
         "missing_time_span": [U(tmin / 1000) if tmin else None, U(tmax / 1000) if tmax else None],
         "missing_maker_share": round(sum(1 for t in missing if t["maker"]) / len(missing), 4) if missing else None,
         "missing_gross_usdt": round(sum(abs(fnum(t["quoteQty"])) for t in missing), 4),
         "missing_signed_cash_usdt": round(miss_cash, 4), "missing_fee_native": {k: round(v, 8) for k, v in miss_fee_native.items()},
         "missing_fee_usdt_eq": round(miss_fee, 4), "missing_realized_pnl_venue": round(sum(fnum(t["realizedPnl"]) for t in missing), 4),
         "quantity_closure_failures": qfail[:20], "n_quantity_closure_failures": len(qfail),
         "predicted_residual": round(predicted, 4), "measured_residual": round(resid, 4), "closure_gap": round(gap_cash, 4), "tol": round(tol, 4),
         "cross_endpoint": cross, "cross_endpoint_ok": cross_ok,
         "flatten_orders": flatten, "other_missing": other,
         "executor_order_types_in_window": dict(ord_types),
         "identity_boundary": "flatten orders carry no clientOrderId of ours and (before the broker fix) no recorded venue orderId; the join is "
                              "(symbol, side, first-fill ms, last-fill ms) with measured one-to-one uniqueness and an amount check, not an id join",
         "D_usd_identity": D,
         "attribution": attribution, "endpoint_per_trade": endpoint, "population": pop,
         "gates": dict(gates), "failed_gates": failed,
         "VERDICT_v2_usdt_caliber": accept(closed and abs(gap_cash) <= tol),
         "VERDICT": verdict}
    deps = {"fills_reader.py": sha256_file(FR.__file__), "usd_valuation.py": sha256_file(UV.__file__),
            "BNBUSDT_daily": sha256_file(BNB_P), "bnb_rows": sha256_file(flags["--bnb-rows"])}
    if os.path.isfile(UV.CACHE): deps["index_klines_cache"] = sha256_file(UV.CACHE)
    for fn in ("fetch_trades.py", "fetch_income_paged.py"):
        if os.path.isfile(os.path.join(HERE, fn)): deps[fn] = sha256_file(os.path.join(HERE, fn))
    doc = {"receipt": "FLATTEN_WINDOW_CLOSURE", "device": f"flatten_window_closure.py {VERSION}", "self_sha256": self_sha,
           "utc": time.strftime("%FT%TZ", time.gmtime()), "argv": sys.argv[1:], "event": event, "ledger_root": ledger_root,
           "inputs_sha16": inputs, "deps_sha256": deps, "index_prices_offline": offline,
           "raw_trades_file": os.path.basename(raw_out), "raw_trades_sha256": sha256_file(raw_out),
           "VERDICT": verdict, "gates": dict(gates),
           "A_local_identity": A, "C_closure": C}
    write_doc(out, doc)
    print("C 闭合:", json.dumps({k: v for k, v in C.items() if k not in ("cross_endpoint", "flatten_orders", "other_missing", "D_usd_identity",
                                                                       "attribution", "endpoint_per_trade", "population")}, ensure_ascii=False))
    print("  USD 恒等式:", json.dumps(D, ensure_ascii=False))
    print("  两端点(窗口总额):", json.dumps(cross, ensure_ascii=False))
    print("  平仓单(身份对齐):", json.dumps(flatten, ensure_ascii=False))
    print("  其它缺失成交:", json.dumps({k: (v if k != "orders" else v[:8]) for k, v in other.items()}, ensure_ascii=False))
    print("  归属门:", json.dumps(attribution, ensure_ascii=False))
    print("  逐笔端点门:", json.dumps({k: v for k, v in endpoint.items() if k != "samples"}, ensure_ascii=False))
    print("  取数人口:", json.dumps({k: v for k, v in pop.items() if k != "required_symbols"}, ensure_ascii=False))
    print("  门:", json.dumps(gates, ensure_ascii=False), "failed:", failed)
    print("VERDICT", verdict)
    return RC[verdict]


if __name__ == "__main__":
    sys.exit(main())
