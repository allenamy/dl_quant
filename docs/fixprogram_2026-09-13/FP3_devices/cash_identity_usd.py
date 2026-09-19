#!/usr/bin/env python3
"""FP3 · 全期现金恒等式, 用账户【自己的计价单位】重写 —— v3: 两条分开命名、永不合并的轨(2026-09-19)。只读。

背景(v1/v2, 见 archive/cash_identity_usd_v2_17b52980.py 与 docs/RESULT_cash_closure_per_trade_2026-09-19.md §3/§5):
  账户 multiAssetsMargin = True ⇒ daily_nav.nav 是 USD(USDT 按 USDTUSD 指数 × (1 − 1e-4), BNB 按 BNBUSD 指数 × 0.95),
  恒等式其它各项都是 USDT。
  恒等式:  N = p·W + b·B
     W1 = W0 + Σ_s(q1·mk1 − q0·mk0) − Σ_全部成交 sgn·quoteQty + Σ_USDT 计收入流水(资金费 / 手续费 / 划转 / 其它)
     B1 = B0 + Σ_BNB 计收入流水
     残差 = (N1 − p1·W1 − b1·B1) / p1,      W0 = (N0 − b0·B0) / p0
  REALIZED_PNL / DELIVERED_SETTELMENT 不进恒等式(已由成交现金 + 持仓市值变化包含)。

★ v3 修的是复审第四轮(REVIEW_cash_closure_and_blend_round4_codex_2026-09-19.md)§4 / §5 / §9 指出的五件事:
  (1) R4-C3 认证边界。v2 的「精确率」p = 钱包 USD / 钱包 USDT, 钱包 USDT 由【被检验的同一套收入流水】倒推 ⇒ 漏一笔出金时
      精确率轨残差恒为 0(复审反例: 漏 100 出金, 独立价格口径 −100, 精确率口径 0)。v2 让精确率在可用处【优先】成为判词,
      于是 49/49、290/291 里有 15 个日窗 / 94 个 4h 窗的判词来自一个认证不了钱包流水的口径。
      v3: 每个窗出两条轨, 分开命名, 永不合并成一个判词:
        INDEPENDENT            计价只来自公开指数(1 分钟 K 线), 与钱包流水无关。主判词。
        CONDITIONAL_EXACT_RATE v2 的精确率残差, 明确标注「以收入流水完整为条件; 不能认证钱包流水, 也不能认证计价」。
  (2) R4-C4 BNB 折价 0.05 是看数据选的 ⇒ 同一份收据里并列 BNB 折价敏感性(0.05 / 0.00 / 0.10), 标注为条件性。
  (3) 输入有限性: NaN 数量能通过、无穷价格除出 0 数量也能通过 ⇒ 在【输入层】拒绝全部被用到的数值字段的非有限值
      (账本成交 / 持仓回读 / NAV 行 / 收入行 / 场所成交 / 账户快照 / K 线), 具名拒绝 REFUSED_*, 退出码 4。
      window() 对成交表再查一次(纵深防御: 绕过输入层直接塞进 NaN 也被拒)。
  (4) 收据依赖: 记录 fills_reader.py、usd_valuation.py、本文件的 sha256, 实际所用 OHLC 缓存的【内容】sha256
      (文件字节 + 本次实际读到的分钟值), 以及每个输入文件的 sha256 与字节数。
  (5) 单位: 残差除以 USDT 计价率 p1 ⇒ 是 USDT 等价, 字段名带 _usdt_eq; 容差同单位: tol = max(2.0, 0.5e-4 × N0 / p0)。

★ 预先声明的规则(写于取 high/low 之前, 不看数字改):
  INDEPENDENT 轨
    点值:   p(ts) = USDTUSD 1m K 线 open→close 按秒线性插值 × (1 − 1e-4);  b(ts) = BNBUSD 同法 × (1 − BNB 折价)
    误差带: 账户在 NAV 时刻实际用的指数价 ∈ 【nav_ts 所在那一分钟】K 线的 [low, high]。
            p0 ∈ [low0, high0]·(1 − 1e-4), p1 ∈ [low1, high1]·(1 − 1e-4), b0、b1 同法。
            残差对 (1/p0, 1/p1, b0, b1) 是多重线性的 ⇒ 区间端点精确地在 16 个角上取到(不是近似)。
    判词:   CONSISTENT ⇔ 残差区间 ∩ [−tol, +tol] ≠ ∅ 且逐名数量闭合且没有 USDT/BNB 以外的资产流水; 否则 INCONSISTENT(附原因)。
    并列:   点值残差(插值)及其是否在容差内 —— 不是判词。
    声明的敏感性(非判词): 误差带加宽到 [m − 1, m, m + 1] 三分钟并集(span=1, 吸收时钟偏差/计价率滞后)。
    本轨【仍然】以两个计价缓冲(USDT 1e-4、BNB 0.05)在 08-01..09-19 为常数为条件 —— 与钱包流水无关, 但不是无条件。
  CONDITIONAL_EXACT_RATE 轨
    只在两端 BNB 余额为 0 且有账户快照时可用; 不可用就是不可用, 不回落到 K 线口径(v2 的混合规则只作对账, 见 legacy_v2_mixed)。
  诊断(非判词): 精确率落在该分钟 [low, high]·(1 − 1e-4) 内的覆盖率 —— 精确率本身以收入流水完整为条件, 只作误差带的旁证。
  BNB 折价敏感性: 0.05(声明值) / 0.00(无折) / 0.10, 三者对两轨各出计数。

全部成交 = 账本成交(规范读者坍缩) ∪ 账本缺失的场所成交(收入流水 (symbol, tradeId) 反连接 + 缺失成交收据)。
账本读取: 先把 pilot_log 的 fills / position_readback / daily_nav 按【完整行】前缀复制进临时目录(一次读取的字节同时用于 sha 与解析),
  --ledger-pin <收据> 则逐文件按收据记下的字节数取前缀并核对 sha256, 不符即拒 —— 追加式账本上离线复跑逐位可复现。
NAV 行只取收入拉取区间 [startTime, endTime] 以内的(区间外的行数与时刻具名记入收据)。
网络: --offline 不联网; 默认只允许公开 K 线端点; 带签名的只读取数(缺失成交 / 数量补拉)只有 --allow-signed-readonly 才会发生。
usage: cash_identity_usd.py <out.json> --income <INCOME_ALL.json> [--income-delta <DELTA.json>] [--account-snapshot <SNAP.json>]
       [--raw <closure_raw.json> ...] [--missing-trades <MISSING_TRADES.json>] [--ledger-root <root>] [--ledger-pin <receipt.json>]
       [--index-cache <OHLC_cache.json>] [--compare-v2 <v2_receipt.json>] [--ablate <term>] [--offline] [--allow-signed-readonly]
退出码: 0 完成 · 2 输入不完整/不衔接 · 3 UNAVAILABLE · 4 输入层具名拒绝(REFUSED_*)"""
import bisect, collections, hashlib, json, math, os, shutil, sys, tempfile, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "multi_asset", "exports", "live", "pilot_journal", "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLS)
import fills_reader as FR
import usd_valuation as UV
from usd_valuation import InputRefused, finite

VERSION = "v3-2026-09-19"
LEDGER_NAMES = ("fills", "position_readback", "daily_nav")
SNAP_TOL_S = 60.0
BNB_SENSITIVITY = (0.0, 0.10)          # 与声明值 UV.BNB_BID_BUFFER = 0.05 并列
BAND_SPAN_PRIMARY = 0
BAND_SPAN_SENSITIVITY = 1
UNITS = ("residual_* and tol are USDT-equivalent: USD-denominated NAV terms divided by the USDT valuation rate p1 "
         "(index × (1 − 1e-4)); tol = max(2.0, 0.5e-4 × N0 / p0)")
LABEL_INDEPENDENT = ("INDEPENDENT: valuation from the public index only (1m klines; band = [low, high] of the minute containing nav_ts, "
                     "× (1 − buffer)); independent of wallet/income flows. Conditional on the declared buffers (USDT 1e-4, BNB 0.05) "
                     "being constant over 08-01..09-19.")
LABEL_CONDITIONAL = ("CONDITIONAL_EXACT_RATE: conditional on income-flow completeness; cannot certify wallet flows or valuation. "
                     "The rate is reconstructed from the same income flows under test, so a missing wallet flow cancels out.")
U = lambda t: time.strftime("%m-%d %H:%M:%SZ", time.gmtime(float(t)))
DAY = lambda t: time.strftime("%Y%m%d", time.gmtime(float(t)))
sha256_bytes = lambda b: hashlib.sha256(b).hexdigest()


def sha256_file(p):
    with open(p, "rb") as fh: return sha256_bytes(fh.read())


# ───────────────────────────── 输入层(全部被用到的数值字段) ─────────────────────────────
def ledger_trade_rows(fills):
    out = []
    for f in fills:
        k = f"ledger fill {f.get('symbol')}#{f.get('trade_id')}"
        if not f.get("symbol"): raise InputRefused("REFUSED_MISSING_FIELD", k + " symbol")
        side = str(f.get("side")).upper()
        if side not in ("BUY", "SELL"): raise InputRefused("REFUSED_BAD_SIDE", f"{k} side={f.get('side')!r}")
        ts = finite(f.get("fill_ts"), k + " fill_ts")
        px = finite(f.get("fill_px"), k + " fill_px", positive=True)
        nt = finite(f.get("fill_notional"), k + " fill_notional")
        if f.get("commission") is not None: finite(f["commission"], k + " commission")
        sg = 1.0 if side == "BUY" else -1.0
        q = finite(sg * nt / px, k + " qty = notional / px")
        out.append((ts, f["symbol"], q, sg * nt, "L"))
    return out


def check_venue_trade(t):
    k = f"venue trade {t.get('symbol')}#{t.get('id')}"
    if not t.get("symbol"): raise InputRefused("REFUSED_MISSING_FIELD", k + " symbol")
    if not isinstance(t.get("buyer"), bool): raise InputRefused("REFUSED_BAD_SIDE", f"{k} buyer={t.get('buyer')!r}")
    finite(t.get("time"), k + " time"); finite(t.get("qty"), k + " qty"); finite(t.get("quoteQty"), k + " quoteQty")
    return t


def venue_trade_rows(trades):
    out = []
    for t in trades:
        check_venue_trade(t)
        sg = 1.0 if t["buyer"] else -1.0
        out.append((int(t["time"]) / 1000, t["symbol"], sg * abs(float(t["qty"])), sg * abs(float(t["quoteQty"])), "M"))
    return out


def check_income(rows, src):
    for r in rows:
        k = f"{src} income {r.get('incomeType')} {r.get('symbol')} tranId={r.get('tranId')}"
        finite(r.get("income"), k + " income"); finite(r.get("time"), k + " time")
        if not r.get("asset"): raise InputRefused("REFUSED_MISSING_FIELD", k + " asset")
        if not r.get("incomeType"): raise InputRefused("REFUSED_MISSING_FIELD", k + " incomeType")


def check_nav(r):
    k = f"daily_nav row nav_ts={r.get('nav_ts')!r}"
    finite(r.get("nav_ts"), k + " nav_ts"); finite(r.get("nav"), k + " nav", positive=True)
    for f in ("wallet_balance", "external_flow_usdt"):
        if r.get(f) is not None: finite(r[f], f"{k} {f}")


def check_readback(r):
    k = f"position_readback {r.get('symbol')} read_ts={r.get('read_ts')!r}"
    if not r.get("symbol"): raise InputRefused("REFUSED_MISSING_FIELD", k + " symbol")
    finite(r.get("read_ts"), k + " read_ts"); finite(r.get("venue_position_qty"), k + " venue_position_qty")
    finite(r.get("venue_position_notional"), k + " venue_position_notional")


# ───────────────────────────── 计价(公开指数) ─────────────────────────────
class Valuation:
    """INDEPENDENT 轨的全部计价输入: 公开指数 K 线。point / band 都是指数本身(未乘缓冲)。"""

    def __init__(self, cache, offline):
        self.cache = cache; self.offline = offline

    def point(self, pair, ts): return self.cache.point(pair, ts, self.offline)
    def band(self, pair, ts, span=0): return self.cache.band(pair, ts, self.offline, span)


def resid(core, p0, p1, b0, b1):
    """与 v2 逐算子同序: W0 = (N0 − b0·B0)/p0; W1 = W0 + mtm + ΣUSDT; 残差 = (N1 − p1·W1 − b1·B1)/p1 (USDT 等价)。"""
    W0 = (core["N0"] - b0 * core["B0"]) / p0
    W1 = W0 + core["mtm"] + core["flow_usdt"]
    return (core["N1"] - p1 * W1 - b1 * core["B1"]) / p1


def judge_independent(ctx, core, t0, t1, bnb_buf, span, tol):
    ub = ctx.usdt_buf
    if "usd_unit" in ctx.ABL:
        P0 = P1 = 1.0; L0 = H0 = L1 = H1 = 1.0; ubx = 0.0
    else:
        P0, P1 = ctx.val.point("USDTUSD", t0), ctx.val.point("USDTUSD", t1)
        (L0, H0), (L1, H1) = ctx.val.band("USDTUSD", t0, span), ctx.val.band("USDTUSD", t1, span); ubx = ub
    Q0, Q1 = ctx.val.point("BNBUSD", t0), ctx.val.point("BNBUSD", t1)
    (BL0, BH0), (BL1, BH1) = ctx.val.band("BNBUSD", t0, span), ctx.val.band("BNBUSD", t1, span)
    p0, p1, b0, b1 = P0 * (1 - ubx), P1 * (1 - ubx), Q0 * (1 - bnb_buf), Q1 * (1 - bnb_buf)
    pt = resid(core, p0, p1, b0, b1)
    corners = [resid(core, x0 * (1 - ubx), x1 * (1 - ubx), y0 * (1 - bnb_buf), y1 * (1 - bnb_buf))
               for x0 in (L0, H0) for x1 in (L1, H1) for y0 in (BL0, BH0) for y1 in (BL1, BH1)]
    for v in corners + [pt]:
        if not math.isfinite(v): raise InputRefused("REFUSED_NONFINITE", f"residual {U(t0)}→{U(t1)} = {v}")
    lo, hi = min(corners), max(corners)
    reasons = []
    if core["qfail"]: reasons.append("quantity_failures")
    if core["bad_assets"]: reasons.append("non_usdt_bnb_assets")
    if not (lo <= tol and hi >= -tol): reasons.append("residual_interval_outside_tol")
    return {"verdict": "CONSISTENT" if not reasons else "INCONSISTENT", "reasons": reasons,
            "residual_interval_usdt_eq": [round(lo, 4), round(hi, 4)], "residual_point_usdt_eq": round(pt, 4),
            # 检出力(只报告, 不影响判词): 一笔漏记的钱包流量 δ(漏记出金 δ > 0)使残差整体平移 −δ;
            #   δ ∈ [lo − tol, hi + tol] 时本窗仍判 CONSISTENT —— 即本轨在该窗看不见的漏记流量范围
            "undetectable_missing_flow_range_usdt_eq": [round(lo - tol, 4), round(hi + tol, 4)],
            "point_within_tol": abs(pt) <= tol, "point_inside_interval": lo - 1e-9 <= pt <= hi + 1e-9,
            "p_point": [round(p0, 9), round(p1, 9)], "p_band": [[round(L0 * (1 - ubx), 9), round(H0 * (1 - ubx), 9)],
                                                              [round(L1 * (1 - ubx), 9), round(H1 * (1 - ubx), 9)]],
            "b_point": [round(b0, 6), round(b1, 6)], "b_band": [[round(BL0 * (1 - bnb_buf), 6), round(BH0 * (1 - bnb_buf), 6)],
                                                             [round(BL1 * (1 - bnb_buf), 6), round(BH1 * (1 - bnb_buf), 6)]],
            "_pt": pt, "_lo": lo, "_hi": hi, "_p0": p0}


# ───────────────────────────── 上下文(输入层在这里执行) ─────────────────────────────
def build_context(*, nav_rows, readbacks, ledger_fills, venue_trades, income_rows, i_lo, i_hi, val,
                  exact=None, ablate=(), usdt_buf=UV.USDT_BID_BUFFER, bnb_buf=UV.BNB_BID_BUFFER, sensitivities=True):
    """exact = (W_snap_usdt, t_snap_ms) 或 None。所有数值字段在这里检查, 非有限即抛 InputRefused。"""
    check_income(income_rows, "income")
    for r in nav_rows: check_nav(r)
    for r in readbacks: check_readback(r)
    T = ledger_trade_rows(ledger_fills) + venue_trade_rows(venue_trades)
    T.sort()
    rb = collections.defaultdict(dict)
    for r in readbacks: rb[float(r["read_ts"])][r["symbol"]] = r
    snaps = sorted(rb)

    def snap(ts):
        j = bisect.bisect_left(snaps, ts); c = [s for s in snaps[max(0, j - 2):j + 2] if abs(s - ts) <= SNAP_TOL_S]
        if not c: return None
        st = min(c, key=lambda k: (abs(k - ts), k))
        return {s: (float(r["venue_position_qty"]), abs(float(r["venue_position_notional"])) / abs(float(r["venue_position_qty"]))
                    if float(r["venue_position_qty"]) else 0.0) for s, r in rb[st].items()}
    It = sorted(income_rows, key=lambda r: int(r["time"]))
    path = UV.BnbPath(income_rows)
    p_exact_at = lambda ts, wusd: None
    if exact is not None:
        W_snap = finite(exact[0], "account snapshot USDT walletBalance"); t_snap = int(finite(exact[1], "account snapshot updateTime"))
        Iu = [r for r in It if r.get("asset") == "USDT"]
        after = [r for r in Iu if int(r["time"]) > t_snap]
        if after: raise InputRefused("REFUSED_SNAPSHOT_NOT_LATEST", f"{len(after)} USDT income rows after the account snapshot")
        ut = [int(r["time"]) for r in Iu]; uc = [0.0]
        for r in Iu: uc.append(uc[-1] + float(r["income"]))

        def p_exact_at(ts, wusd):
            if wusd is None or abs(path.at(ts)) > 1e-9: return None
            wu = W_snap - (uc[len(ut)] - uc[bisect.bisect_right(ut, int(float(ts) * 1000))])
            return float(wusd) / wu if wu else None
    return types.SimpleNamespace(T=T, Tt=[x[0] for x in T], snap=snap, It=It, Itt=[int(r["time"]) for r in It], path=path,
                                 p_exact_at=p_exact_at, i_lo=i_lo, i_hi=i_hi, val=val, ABL=set(ablate),
                                 usdt_buf=usdt_buf, bnb_buf=bnb_buf, sensitivities=sensitivities)


def window(ctx, r0, r1):
    t0, t1 = finite(r0.get("nav_ts"), "window nav_ts0"), finite(r1.get("nav_ts"), "window nav_ts1")
    if not (ctx.i_lo <= t0 * 1000 and t1 * 1000 <= ctx.i_hi): return {"from": U(t0), "to": U(t1), "status": "UNAVAILABLE_OUTSIDE_INCOME_PULL"}
    m0, m1 = ctx.snap(t0), ctx.snap(t1)
    if m0 is None or m1 is None: return {"from": U(t0), "to": U(t1), "status": "UNAVAILABLE_TIMING"}
    a, b = bisect.bisect_right(ctx.Tt, t0), bisect.bisect_right(ctx.Tt, t1)
    cash = collections.defaultdict(float); qty = collections.defaultdict(float); n_m = 0
    for ts, s, q, c, src in ctx.T[a:b]:
        if not (math.isfinite(q) and math.isfinite(c)):          # 纵深防御: 绕过输入层塞进来的非有限值
            raise InputRefused("REFUSED_NONFINITE", f"trade table {s} @ {ts}: qty={q} cash={c}")
        if src == "M" and "missing_trades" in ctx.ABL: continue
        cash[s] += c; qty[s] += q; n_m += src == "M"
    names = set(m0) | set(m1) | set(qty); mtm = 0.0; qfail = []
    for s in names:
        q0, k0 = m0.get(s, (0.0, 0.0)); q1, k1 = m1.get(s, (0.0, 0.0))
        mtm += q1 * k1 - q0 * k0 - cash[s]
        if abs(q0 + qty[s] - q1) * (k1 or k0 or 1.0) > 0.01: qfail.append((s, round(q0 + qty[s] - q1, 8)))
    ia, ib = bisect.bisect_right(ctx.Itt, int(t0 * 1000)), bisect.bisect_right(ctx.Itt, int(t1 * 1000))
    flow = collections.defaultdict(float); other = collections.Counter()
    for r in ctx.It[ia:ib]:
        if r["incomeType"] in ("REALIZED_PNL", "DELIVERED_SETTELMENT"): continue
        flow[(r["incomeType"], r.get("asset"))] += float(r["income"])
        if r["incomeType"] not in ("COMMISSION", "FUNDING_FEE", "TRANSFER"): other[r["incomeType"]] += 1
    bad_assets = sorted({a_ for _, a_ in flow} - {"USDT", "BNB"})
    N0, N1 = finite(r0.get("nav"), "window nav0", positive=True), finite(r1.get("nav"), "window nav1", positive=True)
    B0 = ctx.path.at(t0)
    if "bnb_balance" in ctx.ABL:
        B0 = 0.0; flow = {k: v for k, v in flow.items() if k[1] != "BNB"}
    if "venue_transfers" in ctx.ABL:
        flow = {k: v for k, v in flow.items() if k[0] != "TRANSFER"}; flow[("TRANSFER", "USDT")] = float(r1.get("external_flow_usdt") or 0.0)
    core = {"N0": N0, "N1": N1, "B0": B0, "B1": B0 + sum(v for (ty, a_), v in flow.items() if a_ == "BNB"), "mtm": mtm,
            "flow_usdt": sum(v for (ty, a_), v in flow.items() if a_ == "USDT"), "qfail": qfail, "bad_assets": bad_assets}
    # 容差: 与残差同单位(USDT 等价) —— NAV 是 USD, 除以点值 p0
    p0_pt = 1.0 if "usd_unit" in ctx.ABL else ctx.val.point("USDTUSD", t0) * (1 - ctx.usdt_buf)
    tol = max(2.0, 0.5e-4 * N0 / p0_pt)
    ind = judge_independent(ctx, core, t0, t1, ctx.bnb_buf, BAND_SPAN_PRIMARY, tol)
    # ── 条件轨: 精确率(仅两端 BNB = 0) ──
    pe0, pe1 = ctx.p_exact_at(t0, r0.get("wallet_balance")), ctx.p_exact_at(t1, r1.get("wallet_balance"))
    if pe0 is not None and pe1 is not None and "usd_unit" not in ctx.ABL:
        W0x = N0 / pe0; res_x = (N1 - pe1 * (W0x + mtm + core["flow_usdt"])) / pe1
        if not math.isfinite(res_x): raise InputRefused("REFUSED_NONFINITE", f"exact-rate residual {U(t0)}→{U(t1)}")
        cond = {"available": True, "residual_usdt_eq": round(res_x, 4), "p_exact": [round(pe0, 9), round(pe1, 9)],
                "within_tol": abs(res_x) <= tol and not qfail and not bad_assets, "_r": res_x}
    else:
        cond = {"available": False, "why": "BNB balance ≠ 0 at an endpoint, no wallet_balance, or no account snapshot",
                "residual_usdt_eq": None, "within_tol": None, "_r": None}
    legacy = (cond["_r"] if cond["available"] else ind["_pt"])
    out = {"from": U(t0), "to": U(t1), "hours": round((t1 - t0) / 3600, 2), "n_trades": b - a, "n_missing_trades": n_m,
           "n_quantity_failures": len(qfail), "quantity_failures": qfail[:6], "tol_usdt_eq": round(tol, 4),
           "INDEPENDENT": {k: v for k, v in ind.items() if not k.startswith("_")},
           "CONDITIONAL_EXACT_RATE": {k: v for k, v in cond.items() if not k.startswith("_")},
           "legacy_v2_mixed_within_tol": abs(legacy) <= tol and not qfail and not bad_assets,
           "terms": {"B": [round(B0, 8), round(core["B1"], 8)], "N_usd": [N0, N1], "mtm_and_trade_cash_usdt": round(mtm, 4),
                     "flows": {f"{k[0]}|{k[1]}": round(v, 8) for k, v in flow.items()},
                     "ledger_external_flow_usdt_row_t1": float(r1.get("external_flow_usdt") or 0.0)},
           "other_income_types": dict(other), "non_usdt_bnb_assets": bad_assets,
           "_core": core, "_ind": ind, "_cond": cond, "_tol": tol}
    if ctx.sensitivities:
        sens = {}
        for bb in BNB_SENSITIVITY:
            j = judge_independent(ctx, core, t0, t1, bb, BAND_SPAN_PRIMARY, tol)
            sens[f"bnb_buffer={bb:.2f}"] = {"verdict": j["verdict"], "residual_interval_usdt_eq": j["residual_interval_usdt_eq"],
                                            "residual_point_usdt_eq": j["residual_point_usdt_eq"], "point_within_tol": j["point_within_tol"],
                                            "legacy_v2_mixed_within_tol": abs(cond["_r"] if cond["available"] else j["_pt"]) <= tol
                                            and not qfail and not bad_assets}
        j = judge_independent(ctx, core, t0, t1, ctx.bnb_buf, BAND_SPAN_SENSITIVITY, tol)
        sens[f"band_span={BAND_SPAN_SENSITIVITY}"] = {"verdict": j["verdict"], "residual_interval_usdt_eq": j["residual_interval_usdt_eq"]}
        out["sensitivity"] = sens
    return out


def public(w):
    return {k: v for k, v in w.items() if not k.startswith("_")}


# ───────────────────────────── 账本暂存(完整行前缀 + 钉) ─────────────────────────────
def stage_ledger(root, pin=None, stages=None):
    base = os.path.join(root, FR.PILOT_LOG)
    stage = tempfile.mkdtemp(prefix="cash_identity_v3_")
    if stages is not None: stages.append(stage)
    inputs = {}
    if pin is None:
        days = sorted(d for d in os.listdir(base) if d.startswith("2026") and os.path.isdir(os.path.join(base, d)))
        plan = [(d, n, None, None) for d in days for n in LEDGER_NAMES if os.path.isfile(os.path.join(base, d, n + ".jsonl"))]
    else:
        plan = [(key.split("/")[0], key.split("/")[1], v["n_bytes"], v["sha256"]) for key, v in sorted(pin.items())]
        days = sorted({p[0] for p in plan})
    for d, n, nb, sh in plan:
        src = os.path.join(base, d, n + ".jsonl")
        if not os.path.isfile(src): raise InputRefused("REFUSED_LEDGER_PIN_MISSING_FILE", src)
        with open(src, "rb") as fh: raw = fh.read()
        if nb is None:
            raw = raw[:raw.rfind(b"\n") + 1]                  # 只取完整行(追加中的半行不进)
        else:
            if len(raw) < nb: raise InputRefused("REFUSED_LEDGER_PIN_SHORT", f"{src}: {len(raw)} < pinned {nb} bytes")
            raw = raw[:nb]
            if sha256_bytes(raw) != sh: raise InputRefused("REFUSED_LEDGER_PIN_MISMATCH", f"{src}: prefix sha256 ≠ pinned")
        dst = os.path.join(stage, FR.PILOT_LOG, d, n + ".jsonl"); os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fh: fh.write(raw)
        inputs[f"{d}/{n}"] = {"n_bytes": len(raw), "sha256": sha256_bytes(raw)}
    return stage, days, inputs


def strict_rows(stage, day, name):
    p = os.path.join(stage, FR.PILOT_LOG, day, name + ".jsonl")
    if not os.path.isfile(p): return []
    out = []
    with open(p) as fh:
        for i, l in enumerate(fh):
            if not l.strip(): continue
            try: out.append(json.loads(l))
            except ValueError: raise InputRefused("REFUSED_BAD_JSON", f"{day}/{name}.jsonl line {i + 1}")
    return out


# ───────────────────────────── 主流程 ─────────────────────────────
def _power(J):
    """只报告: 每窗本轨看不见的最大漏记流量 max(|lo − tol|, |hi + tol|) 的分布, 以及 ±100 USDT 漏记在多少窗会被判 INCONSISTENT。"""
    if not J: return None
    xs = sorted((max(abs(w["_ind"]["_lo"] - w["_tol"]), abs(w["_ind"]["_hi"] + w["_tol"])), w["from"], w["to"]) for w in J)
    q = lambda f: round(xs[min(len(xs) - 1, int(f * len(xs)))][0], 2)
    c100 = sum(1 for w in J if w["_ind"]["_hi"] + w["_tol"] < 100.0 and w["_ind"]["_lo"] - w["_tol"] > -100.0)
    return {"rule": "a missing wallet flow d shifts the residual by −d; the window stays CONSISTENT iff d ∈ [lo − tol, hi + tol]",
            "max_abs_undetectable_usdt_eq": {"median": q(0.5), "p90": q(0.9), "max": round(xs[-1][0], 2), "argmax": xs[-1][1:]},
            "n_windows_where_pm100_usdt_missing_flow_is_caught": c100, "n": len(J)}


def summarize(W):
    J = [w for w in W if "INDEPENDENT" in w]
    bad = [w for w in J if w["INDEPENDENT"]["verdict"] != "CONSISTENT"]
    av = [w for w in J if w["CONDITIONAL_EXACT_RATE"]["available"]]
    cbad = [w for w in av if not w["CONDITIONAL_EXACT_RATE"]["within_tol"]]
    s = {"n": len(W), "n_judged": len(J), "n_unavailable": len(W) - len(J),
         "n_with_quantity_failures": sum(1 for w in J if w["n_quantity_failures"]),
         "INDEPENDENT": {"label": LABEL_INDEPENDENT, "headline": True,
                         "n_consistent": len(J) - len(bad), "n_inconsistent": len(bad),
                         "n_point_within_tol": sum(w["INDEPENDENT"]["point_within_tol"] for w in J),
                         "residual_point_abs_sum_usdt_eq": round(sum(abs(w["_ind"]["_pt"]) for w in J), 2),
                         "n_point_outside_interval_sanity": sum(not w["INDEPENDENT"]["point_inside_interval"] for w in J),
                         "inconsistent": [{"from": w["from"], "to": w["to"], "interval": w["INDEPENDENT"]["residual_interval_usdt_eq"],
                                           "point": w["INDEPENDENT"]["residual_point_usdt_eq"], "tol": w["tol_usdt_eq"],
                                           "reasons": w["INDEPENDENT"]["reasons"], "B": w["terms"]["B"]} for w in bad],
                         "consistent_only_by_band": [{"from": w["from"], "to": w["to"], "point": w["INDEPENDENT"]["residual_point_usdt_eq"],
                                                      "interval": w["INDEPENDENT"]["residual_interval_usdt_eq"], "tol": w["tol_usdt_eq"],
                                                      "B": w["terms"]["B"], "conditional_exact_rate_residual": w["CONDITIONAL_EXACT_RATE"]["residual_usdt_eq"]}
                                                     for w in J if w["INDEPENDENT"]["verdict"] == "CONSISTENT" and not w["INDEPENDENT"]["point_within_tol"]],
                         "detection_power": _power(J),
                         "worst_point": sorted(((w["from"], w["to"], w["INDEPENDENT"]["residual_point_usdt_eq"],
                                                 w["INDEPENDENT"]["residual_interval_usdt_eq"], w["tol_usdt_eq"]) for w in J),
                                               key=lambda x: -abs(x[2]))[:12]},
         "CONDITIONAL_EXACT_RATE": {"label": LABEL_CONDITIONAL, "headline": False,
                                    "n_available": len(av), "n_not_available": len(J) - len(av), "n_within_tol": len(av) - len(cbad),
                                    "residual_abs_sum_usdt_eq": round(sum(abs(w["_cond"]["_r"]) for w in av), 2),
                                    "not_within_tol": [(w["from"], w["to"], w["CONDITIONAL_EXACT_RATE"]["residual_usdt_eq"], w["tol_usdt_eq"]) for w in cbad]},
         "legacy_v2_mixed_rule_reconciliation_only": {
             "rule": "v2 headline: exact-rate residual where available, else kline point residual; NOT a verdict (merges the two tracks)",
             "n_within_tol": sum(w["legacy_v2_mixed_within_tol"] for w in J)}}
    sens = {}
    for key in ([f"bnb_buffer={bb:.2f}" for bb in BNB_SENSITIVITY] + [f"band_span={BAND_SPAN_SENSITIVITY}"]):
        rows_ = [w for w in J if key in w.get("sensitivity", {})]
        if not rows_: continue
        e = {"n": len(rows_), "INDEPENDENT_n_consistent": sum(w["sensitivity"][key]["verdict"] == "CONSISTENT" for w in rows_),
             "INDEPENDENT_inconsistent": [(w["from"], w["to"], w["sensitivity"][key]["residual_interval_usdt_eq"]) for w in rows_
                                          if w["sensitivity"][key]["verdict"] != "CONSISTENT"]}
        if key.startswith("bnb"):
            e["INDEPENDENT_n_point_within_tol"] = sum(w["sensitivity"][key]["point_within_tol"] for w in rows_)
            e["CONDITIONAL_EXACT_RATE_n_within_tol_of_available"] = f"{len(av) - len(cbad)}/{len(av)} (unaffected: available only where BNB = 0 at both ends)"
            e["legacy_v2_mixed_n_within_tol"] = sum(w["sensitivity"][key]["legacy_v2_mixed_within_tol"] for w in rows_)
        sens[key] = e
    s["sensitivity"] = sens
    return s


def main(argv=None):
    av = sys.argv[1:] if argv is None else list(argv)
    out = av[0]; flags = collections.defaultdict(list); i = 1
    while i < len(av):
        if av[i] in ("--offline", "--allow-signed-readonly"): flags[av[i]].append(True); i += 1
        else: flags[av[i]].append(av[i + 1]); i += 2
    stages = []                                              # 暂存目录登记: 任何退出路径(含具名拒绝)都清掉
    try:
        rc, _ = _main(out, flags, stages)
        return rc
    except InputRefused as e:
        print(f"{e.code}: {e.where}"); return 4
    except KeyError as e:
        if "offline" not in str(e): raise
        print(f"UNAVAILABLE: {e} —— 离线运行缺 K 线分钟(先联网取公开 K 线一次)"); return 3
    finally:
        for st in stages:
            if os.path.isdir(st): shutil.rmtree(st)


def _main(out, flags, stages):
    offline = bool(flags.get("--offline")); signed_ok = bool(flags.get("--allow-signed-readonly")) and not offline
    ABL = set(flags.get("--ablate", []))
    assert ABL <= {"missing_trades", "usd_unit", "bnb_balance", "venue_transfers"}, ABL
    files = {}
    def rec(p): files[os.path.relpath(os.path.abspath(p), HERE)] = {"sha256": sha256_file(p), "n_bytes": os.path.getsize(p)}
    inc = json.load(open(flags["--income"][0])); rec(flags["--income"][0])
    if inc.get("completeness") != "COMPLETE" or inc.get("incomeType") not in (None, "ALL"):
        print("REFUSED: --income 必须是【全类型】且 COMPLETE 的收入拉取"); return 2, None
    I = inc["body"]; i_lo, i_hi = inc["startTime"], inc["endTime"]
    dlt = None
    if flags.get("--income-delta"):
        dlt = json.load(open(flags["--income-delta"][0])); rec(flags["--income-delta"][0])
        if dlt.get("completeness") != "COMPLETE" or dlt["startTime"] != i_hi + 1:
            print("REFUSED: --income-delta 不完整或不与主拉取首尾相接"); return 2, None
        I = I + dlt["body"]; i_hi = dlt["endTime"]
    check_income(I, "income")
    pin = None
    if flags.get("--ledger-pin"):
        pin = json.load(open(flags["--ledger-pin"][0]))["inputs"]["ledger"]; rec(flags["--ledger-pin"][0])
    stage, days, ledger_inputs = stage_ledger(flags.get("--ledger-root", [FR.LIVE_ROOT])[0], pin, stages)
    for d in days: strict_rows(stage, d, "fills")             # fills_reader 对坏行静默跳过; 这里先严格解析, 坏行即具名拒绝

    # ── 成交: 账本(坍缩) + 缺失 ──
    fills = FR.read_range(root=stage, day_list=days)
    T_led = ledger_trade_rows(fills)                                   # 输入层: 先验再用
    led = {(f["symbol"], str(f["trade_id"])): f for f in fills}
    TRADE_TYPES = ("COMMISSION", "REALIZED_PNL", "DELIVERED_SETTELMENT")
    ven_ids = {}
    for r in I:
        if r["incomeType"] in TRADE_TYPES and r.get("tradeId") not in (None, ""):
            ven_ids.setdefault((r["symbol"], str(r["tradeId"])), r)
    miss_ids = sorted(set(ven_ids) - set(led))
    led_not_in_income = sorted(k for k, f in led.items() if float(f.get("commission") or 0.0) != 0.0
                               and i_lo <= float(f["fill_ts"]) * 1000 <= i_hi and k not in ven_ids)
    have = {}
    for p in flags.get("--raw", []):
        rd = json.load(open(p)); rec(p)
        if rd.get("completeness") != "COMPLETE": print("REFUSED: --raw 不完整", p); return 2, stage
        for t in rd["body"]: have[(t["symbol"], str(t["id"]))] = check_venue_trade(t)
    mt_path = flags.get("--missing-trades", [None])[0]
    if mt_path and os.path.isfile(mt_path):
        md = json.load(open(mt_path)); rec(mt_path)
        for t in md["body"]: have[(t["symbol"], str(t["id"]))] = check_venue_trade(t)
    need = [k for k in miss_ids if k not in have]
    if need:
        if not signed_ok: print(f"UNAVAILABLE: {len(need)} 笔缺失成交不在任何输入里(带签名取数未允许)"); return 3, stage
        import fetch_trades as FT
        by_sym = collections.defaultdict(list)
        for s, tid in need: by_sym[s].append(int(ven_ids[(s, tid)]["time"]))
        fetched, bad = [], []
        for s, ts_ in sorted(by_sym.items()):
            ts_.sort(); cl = [[ts_[0], ts_[0]]]
            for t in ts_[1:]:
                if t - cl[-1][1] <= 3_600_000: cl[-1][1] = t
                else: cl.append([t, t])
            for a, b in cl:
                pages, rs, st, why = FT.fetch_trades(s, a - 1000, b + 1000)
                if st != "COMPLETE": bad.append((s, a, b, why)); continue
                fetched += rs
        if bad: print("UNAVAILABLE: userTrades 不完整", bad[:5]); return 3, stage
        for t in fetched: have[(t["symbol"], str(t["id"]))] = check_venue_trade(t)
        mt_path = mt_path or out.replace(".json", "_MISSING_TRADES.json")
        if os.path.isfile(mt_path):
            prev = json.load(open(mt_path))["body"]; seen = {(t["symbol"], str(t["id"])) for t in fetched}
            fetched = [t for t in prev if (t["symbol"], str(t["id"])) not in seen] + fetched
        doc = {"device": f"cash_identity_usd.py {VERSION}", "endpoint": "/fapi/v1/userTrades", "completeness": "COMPLETE", "body": fetched}
        with open(mt_path + ".part", "w") as fh: json.dump(doc, fh)
        os.replace(mt_path + ".part", mt_path); rec(mt_path)
    still = [k for k in miss_ids if k not in have]
    if still: print(f"UNAVAILABLE: {len(still)} 笔缺失成交拉不到", still[:5]); return 3, stage
    from_file = set()
    if mt_path and os.path.isfile(mt_path):
        from_file = {(t["symbol"], str(t["id"])) for t in json.load(open(mt_path))["body"]} - set(led)
    miss_keys = sorted(set(miss_ids) | from_file)
    missing = [have[k] for k in miss_keys]
    amt_diff = [abs(float(led[k]["fill_notional"]) - abs(float(have[k]["quoteQty"]))) for k in led if k in have]

    # ── 精确率所需的账户快照 ──
    exact = None
    if flags.get("--account-snapshot") and dlt is not None:
        snp = json.load(open(flags["--account-snapshot"][0])); rec(flags["--account-snapshot"][0])
        usdt = [x for x in snp["assets"] if x["asset"] == "USDT"][0]
        exact = (finite(usdt.get("walletBalance"), "snapshot USDT walletBalance"), finite(usdt.get("updateTime"), "snapshot USDT updateTime"))
        if dlt["endTime"] < int(exact[1]): print("REFUSED: 收入流水没有覆盖到快照时刻"); return 2, stage

    # ── NAV 行 / 回读 ──
    nav_all_rows = [r for d in days for r in strict_rows(stage, d, "daily_nav") if r.get("mode") in (None, "LIVE")]
    for r in nav_all_rows: check_nav(r)
    nav_all = sorted({float(r["nav_ts"]): r for r in nav_all_rows}.values(), key=lambda r: float(r["nav_ts"]))
    nav = [r for r in nav_all if i_lo <= float(r["nav_ts"]) * 1000 <= i_hi]
    nav_excluded = [U(r["nav_ts"]) for r in nav_all if not (i_lo <= float(r["nav_ts"]) * 1000 <= i_hi)]
    readbacks = [r for d in days for r in strict_rows(stage, d, "position_readback")]

    cache = UV.OhlcCache(path=flags.get("--index-cache", [UV.OHLC_CACHE])[0])
    val = Valuation(cache, offline)
    kw = dict(nav_rows=nav, readbacks=readbacks, ledger_fills=fills, income_rows=I, i_lo=i_lo, i_hi=i_hi, val=val, exact=exact, ablate=ABL)
    ctx = build_context(venue_trades=missing, **kw)
    W4 = [window(ctx, a_, b_) for a_, b_ in zip(nav, nav[1:])]

    # ── 数量缺口定点补拉(只在允许带签名取数时) ──
    sweep = {"n_pairs": 0, "n_trades_added": 0, "pairs": [], "status": "NO_QUANTITY_FAILURES"}
    qpairs = [(s_, w["from"], w["to"]) for w in W4 if w.get("n_quantity_failures") for s_, _ in w["quantity_failures"]]
    if qpairs and not signed_ok:
        sweep["status"] = "NOT_RUN_SIGNED_FETCH_DISALLOWED"; sweep["n_pairs"] = len(qpairs)   # 这些窗保持 INCONSISTENT(quantity_failures)
    elif qpairs:
        import fetch_trades as FT
        navt = {U(r["nav_ts"]): float(r["nav_ts"]) for r in nav}; added = []
        mk = {(t["symbol"], str(t["id"])) for t in missing}
        for s_, f_, t_ in qpairs:
            pages, rs, st, why = FT.fetch_trades(s_, int(navt[f_] * 1000) + 1, int(navt[t_] * 1000))
            if st != "COMPLETE": print("UNAVAILABLE: 补拉不完整", s_, f_, why); return 3, stage
            new = [check_venue_trade(t) for t in rs if (t["symbol"], str(t["id"])) not in led and (t["symbol"], str(t["id"])) not in mk]
            added += new; sweep["pairs"].append({"symbol": s_, "from": f_, "to": t_, "venue_trades": len(rs), "added": len(new)})
        sweep.update(n_pairs=len(qpairs), n_trades_added=len(added), status="RUN")
        if added:
            missing += added
            mt_path2 = mt_path or out.replace(".json", "_MISSING_TRADES.json")
            prev = json.load(open(mt_path2))["body"] if os.path.isfile(mt_path2) else []
            with open(mt_path2 + ".part", "w") as fh:
                json.dump({"device": f"cash_identity_usd.py {VERSION}", "endpoint": "/fapi/v1/userTrades", "completeness": "COMPLETE",
                           "body": prev + added}, fh)
            os.replace(mt_path2 + ".part", mt_path2); rec(mt_path2)
            ctx = build_context(venue_trades=missing, **kw)
            W4 = [window(ctx, a_, b_) for a_, b_ in zip(nav, nav[1:])]
    lastday = {}
    for r in nav: lastday[DAY(r["nav_ts"])] = r
    dl = [lastday[d] for d in sorted(lastday)]
    WD = [window(ctx, a_, b_) for a_, b_ in zip(dl, dl[1:])]

    # ── 诊断(非判词): 精确率是否落在该分钟 [low, high]·(1 − 1e-4) 内 ──
    cov = []
    for r in nav:
        t = float(r["nav_ts"]); pe = ctx.p_exact_at(t, r.get("wallet_balance"))
        if pe is None: continue
        e = {"t": U(t), "p_exact": round(pe, 9)}
        for span in (BAND_SPAN_PRIMARY, BAND_SPAN_SENSITIVITY):
            lo, hi = (x * (1 - UV.USDT_BID_BUFFER) for x in val.band("USDTUSD", t, span))
            e[f"inside_span{span}"] = lo <= pe <= hi
            e[f"excursion_ppm_span{span}"] = round((pe - min(max(pe, lo), hi)) / pe * 1e6, 4)
        e["point_minus_exact_ppm"] = round((val.point("USDTUSD", t) * (1 - UV.USDT_BID_BUFFER) - pe) / pe * 1e6, 2)
        cov.append(e)
    coverage = {"label": "DIAGNOSTIC ONLY (not a verdict): the exact rate is itself conditional on income-flow completeness",
                "n": len(cov), **{f"n_inside_span{s}": sum(e[f"inside_span{s}"] for e in cov) for s in (BAND_SPAN_PRIMARY, BAND_SPAN_SENSITIVITY)},
                "outside_span0": [e for e in cov if not e[f"inside_span{BAND_SPAN_PRIMARY}"]],
                "max_abs_excursion_ppm_span0": max((abs(e[f"excursion_ppm_span{BAND_SPAN_PRIMARY}"]) for e in cov), default=None),
                "precision_note": "index klines are printed to 8 decimals (≈0.005–0.01 ppm at USDTUSD ≈ 1); inside/outside flags are strict (no rounding allowance)",
                "abs_point_minus_exact_ppm_max": max((abs(e["point_minus_exact_ppm"]) for e in cov), default=None)}
    if not offline: cache.save()
    # ── 与 v1 缓存(只存 open/close)逐位对账 ──
    xc = {"n_compared": 0, "n_equal": 0, "max_abs_diff": 0.0}
    if os.path.isfile(UV.CACHE):
        old = json.load(open(UV.CACHE))["klines"]
        for pair, mins in old.items():
            for k, (o, c) in mins.items():
                v = cache._load()["klines"].get(pair, {}).get(k)
                if v is None: continue
                xc["n_compared"] += 1; d_ = max(abs(v[0] - o), abs(v[3] - c)); xc["n_equal"] += d_ == 0.0
                xc["max_abs_diff"] = max(xc["max_abs_diff"], d_)
    # ── 与 v2 收据逐窗对账(算术回归; 可选) ──
    cmp = None
    if flags.get("--compare-v2"):
        v2 = json.load(open(flags["--compare-v2"][0])); rec(flags["--compare-v2"][0]); cmp = {}
        for name, mine, theirs in (("4h", W4, v2["windows_4h"]), ("daily", WD, v2["windows_daily"])):
            th = {(w["from"], w["to"]): w for w in theirs}; c = collections.Counter(); dmax = [0.0, 0.0]
            for w in mine:
                o = th.get((w["from"], w["to"]))
                if o is None or "INDEPENDENT" not in w: c["unmatched"] += 1; continue
                d1 = abs(w["INDEPENDENT"]["residual_point_usdt_eq"] - o["residual_usd_identity"]); dmax[0] = max(dmax[0], d1); c["point_equal"] += d1 == 0.0
                x = w["CONDITIONAL_EXACT_RATE"]["residual_usdt_eq"]; y = o["residual_exact_p"]
                if (x is None) != (y is None): c["exact_availability_differs"] += 1
                elif x is not None:
                    d2 = abs(x - y); dmax[1] = max(dmax[1], d2); c["exact_equal"] += d2 == 0.0; c["exact_compared"] += 1
                c["matched"] += 1
            cmp[name] = {"n_mine": len(mine), "n_v2": len(theirs), **c, "max_abs_diff_point_vs_v2_kline": dmax[0], "max_abs_diff_exact_vs_v2": dmax[1]}

    fr_path = os.path.abspath(FR.__file__); uv_path = os.path.abspath(UV.__file__)
    doc = {"receipt": "CASH_IDENTITY_TWO_TRACK", "device": f"cash_identity_usd.py {VERSION}", "ablated": sorted(ABL),
           "utc": time.strftime("%FT%TZ", time.gmtime()), "argv": sys.argv[1:],
           "units": UNITS, "headline_track": "INDEPENDENT",
           "tracks": {"INDEPENDENT": LABEL_INDEPENDENT, "CONDITIONAL_EXACT_RATE": LABEL_CONDITIONAL},
           "rules": {"independent_band": "[low, high] of the 1m index kline whose minute contains nav_ts, × (1 − buffer); residual interval "
                                         "= exact min/max over the 16 corners of (p0, p1, b0, b1) (residual is multilinear in 1/p0, 1/p1, b0, b1)",
                     "independent_verdict": "CONSISTENT iff interval ∩ [−tol, +tol] ≠ ∅ and no quantity failures and no non-USDT/BNB assets",
                     "tol_usdt_eq": "max(2.0, 0.5e-4 × N0 / p0_point)",
                     "sensitivities_declared_not_verdicts": {"bnb_buffer": [UV.BNB_BID_BUFFER, *BNB_SENSITIVITY],
                                                             "band_span_minutes_each_side": BAND_SPAN_SENSITIVITY},
                     "conditional_track": "only where BNB = 0 at both ends; never falls back to kline; never merged with INDEPENDENT"},
           "network": {"offline": offline, "signed_readonly_allowed": signed_ok,
                       "public_kline_calls": cache.n_fetch_calls, "public_min_sleep_s": UV.MIN_SLEEP_S},
           "dependencies": {"self_sha256": sha256_file(os.path.abspath(__file__)),
                            "usd_valuation": {"path": os.path.relpath(uv_path, HERE), "sha256": sha256_file(uv_path)},
                            "fills_reader": {"path": os.path.relpath(fr_path, HERE), "sha256": sha256_file(fr_path)},
                            "index_ohlc_cache": {"path": os.path.relpath(os.path.abspath(cache.path), HERE),
                                                 "file_sha256_at_load": cache.loaded_sha256, "file_sha256_at_end": cache.content_sha256(),
                                                 "used_values_sha256": cache.used_sha256(), "n_minutes_used": len(cache.used)},
                            "python": sys.version.split()[0], "executable": sys.executable},
           "inputs": {"ledger_root": flags.get("--ledger-root", [FR.LIVE_ROOT])[0], "ledger_pinned_from": flags.get("--ledger-pin", [None])[0],
                      "ledger": ledger_inputs, "files": files},
           "valuation": {"usdt_bid_buffer": UV.USDT_BID_BUFFER, "bnb_bid_buffer": UV.BNB_BID_BUFFER},
           "nav_rows": {"n_in_income_pull": len(nav), "n_excluded_outside_income_pull": len(nav_excluded), "excluded": nav_excluded},
           "trades": {"n_ledger_collapsed": len(fills), "n_venue_commission_rows_with_tradeId": len(ven_ids),
                      "n_missing_from_ledger": len(missing), "n_missing_income_joined": len(miss_ids),
                      "n_missing_from_receipt_only": len(from_file - set(miss_ids)),
                      "n_ledger_trades_with_nonzero_fee_absent_from_income": len(led_not_in_income),
                      "ledger_vs_venue_same_trade_max_abs_notional_diff": (round(max(amt_diff), 9) if amt_diff else None), "n_compared": len(amt_diff)},
           "input_layer": {"n_ledger_fills_checked": len(T_led), "n_venue_trades_checked": len(have), "n_income_rows_checked": len(I),
                           "n_nav_rows_checked": len(nav_all_rows), "n_readbacks_checked": len(readbacks)},
           "bnb_path": {"n_rows": ctx.path.n, "min_balance": round(ctx.path.min_bal, 10), "end_balance": round(ctx.path.end, 10),
                        "by_type": {k: round(v, 10) for k, v in ctx.path.by_type.items()}},
           "quantity_sweep": sweep, "exact_rate_band_coverage": coverage, "index_cache_vs_v1_open_close": xc, "compare_v2": cmp,
           "summary_4h": summarize(W4), "summary_daily": summarize(WD),
           "windows_4h": [public(w) for w in W4], "windows_daily": [public(w) for w in WD]}
    with open(out + ".part", "w") as fh: json.dump(doc, fh, indent=1, ensure_ascii=False, allow_nan=False)
    os.replace(out + ".part", out)
    for nm in ("summary_4h", "summary_daily"):
        s = doc[nm]; I_, C_ = s["INDEPENDENT"], s["CONDITIONAL_EXACT_RATE"]
        print(f"{nm}: n={s['n']} judged={s['n_judged']} | INDEPENDENT consistent {I_['n_consistent']}/{s['n_judged']} "
              f"(point within tol {I_['n_point_within_tol']}) | CONDITIONAL_EXACT_RATE within tol {C_['n_within_tol']}/{C_['n_available']} available "
              f"| legacy mixed {s['legacy_v2_mixed_rule_reconciliation_only']['n_within_tol']}")
        for x in I_["inconsistent"]: print("   INCONSISTENT", x)
        print("   detection_power:", {k: v for k, v in I_["detection_power"].items() if k != "rule"}, "| consistent only by band:", len(I_["consistent_only_by_band"]))
        for k, e in s["sensitivity"].items(): print(f"   sens {k}: consistent {e['INDEPENDENT_n_consistent']}/{e['n']}",
                                                    {kk: vv for kk, vv in e.items() if kk not in ('n', 'INDEPENDENT_n_consistent', 'INDEPENDENT_inconsistent')})
    print("coverage:", {k: v for k, v in coverage.items() if k not in ("outside_span0", "label")})
    print("cache_vs_v1:", xc, "| compare_v2:", json.dumps(cmp, ensure_ascii=False))
    print("trades:", json.dumps(doc["trades"], ensure_ascii=False)); print("nav_rows:", doc["nav_rows"]); print("sweep:", {k: v for k, v in sweep.items() if k != "pairs"})
    return 0, stage


if __name__ == "__main__":
    sys.exit(main())
