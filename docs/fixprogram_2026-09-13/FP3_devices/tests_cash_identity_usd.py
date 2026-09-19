#!/usr/bin/env python3
"""cash_identity_usd 的行为电池(2026-09-19, 复审第四轮 R4-C3 / R4-C4 / 输入有限性 / 单位)。离线, 不联网, 不读实盘。

每一格都在【构造的夹具】上跑被测装置【真实的】窗口函数, 断言的是行为(判词 / 拒绝), 不是文本:
  C01 基线为绿(先断言; 基线红则其余各格不跑, 整体判红 —— 基线已红时「能变红」的检查恒真, 不算数)
  C02 持有 BNB 的基线为绿, 且条件轨如实报「不可用」(两端 BNB ≠ 0)
  C03 复审反例: 收入文件漏掉一笔 100 USDT 出金 ⇒ 主判词(INDEPENDENT)必须 INCONSISTENT, 残差 ≈ −100
  C04 同一反例: 条件轨(精确率)残差 ≈ 0、在容差内 —— 【已知盲区当作测试写下来】: 哪天它「抓到了」反而说明精确率不再由同一套流水倒推
  C05 场所成交数量 NaN ⇒ 输入层具名拒绝(REFUSED_NONFINITE)
  C06 账本成交价格 inf(有限名义 ÷ inf = 0 数量)⇒ 输入层具名拒绝
  C07 绕过输入层把 NaN 直接塞进成交表 ⇒ window() 具名拒绝(纵深防御)
  C08 NAV 为 NaN ⇒ 具名拒绝          C09 收入流水金额 NaN ⇒ 具名拒绝          C10 持仓回读数量 NaN ⇒ 具名拒绝
  C11 残差点值超出容差、但在计价误差带之内 ⇒ CONSISTENT
  C12 残差区间整体在容差之外(账户实际计价率在该分钟 [low, high] 之外)⇒ INCONSISTENT
  C13 容差与残差同单位(USDT 等价): p = 0.9 时漏 4.7 USDT 的窗, USDT 等价容差 5.0 内 ⇒ CONSISTENT(USD 容差 4.50 会判红)
用法: tests_cash_identity_usd.py [--device <cash_identity_usd.py 路径>]   缺省 = 同目录的现役装置
      对归档 v2(archive/cash_identity_usd_v2_17b52980.py)跑: v2 的 window 是 main() 里的嵌套函数, 用 AST 原样取出执行,
      判词映射 = v2 的 headline `ok`(它把精确率与 K 线点值合成一个判词)。v2 必须在 C03/C05–C11/C13 上判红。
每格一行 PASS/FAIL; 末行计数; 任一 FAIL ⇒ 退出码 1。"""
import ast, bisect, collections, copy, hashlib, importlib.util, json, math, os, sys, tempfile, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "multi_asset", "exports", "live", "pilot_journal", "tools"))
sys.path.insert(0, HERE); sys.path.insert(0, TOOLS)
sys.dont_write_bytecode = True
import usd_valuation as UV

T0 = 1789000017.0                  # 某分钟的第 17 秒
T1 = T0 + 14400.0
MS = lambda t: int(round(t * 1000))
MIN = lambda t: str(int(t // 60 * 60 * 1000))
UB = UV.USDT_BID_BUFFER
BB = UV.BNB_BID_BUFFER


# ───────────────────────────── 夹具 ─────────────────────────────
def kl(v, lo=None, hi=None):
    return [v, v if hi is None else hi, v if lo is None else lo, v]


def fx_baseline(withdrawal_in_income=True):
    """平仓起步 → 买 10 X @ 100(费 0.4 USDT)→ 出金 100 USDT → X 标记 101。USDTUSD = 0.9995 平。"""
    p = 0.9995 * (1 - UB)
    W0 = 100000.0; W1 = W0 - 0.4 - 100.0; upnl1 = 10 * 101.0 - 1000.0
    inc = [{"time": MS(T0 + 100), "income": "-0.4", "asset": "USDT", "incomeType": "COMMISSION", "symbol": "XUSDT", "tradeId": "1", "tranId": 11}]
    if withdrawal_in_income:
        inc.append({"time": MS(T0 + 200), "income": "-100", "asset": "USDT", "incomeType": "TRANSFER", "symbol": "", "tranId": 12})
    return {"nav": [{"nav_ts": T0, "nav": p * W0, "wallet_balance": p * W0, "mode": "LIVE"},
                    {"nav_ts": T1, "nav": p * (W1 + upnl1), "wallet_balance": p * W1, "mode": "LIVE"}],
            "readbacks": [{"read_ts": T0, "symbol": "XUSDT", "venue_position_qty": 0.0, "venue_position_notional": 0.0},
                          {"read_ts": T1, "symbol": "XUSDT", "venue_position_qty": 10.0, "venue_position_notional": 1010.0}],
            "fills": [{"symbol": "XUSDT", "trade_id": 1, "side": "BUY", "fill_ts": T0 + 100, "fill_px": 100.0, "fill_notional": 1000.0,
                       "commission": 0.4, "commission_asset": "USDT"}],
            "venue_trades": [], "income": inc, "i_lo": MS(T0 - 3600), "i_hi": MS(T1 + 3600),
            "klines": {"USDTUSD": {MIN(T0): kl(0.9995), MIN(T1): kl(0.9995)}, "BNBUSD": {MIN(T0): kl(600.0), MIN(T1): kl(610.0)}},
            "exact": (W1, MS(T1 + 60))}


def fx_bnb():
    """平仓; 钱包 50,000 USDT + 0.5 BNB(窗前划入), 窗内 BNB 手续费 −0.001; BNB 600 → 610。"""
    p = 0.9995 * (1 - UB); b0, b1 = 600.0 * (1 - BB), 610.0 * (1 - BB); W = 50000.0
    inc = [{"time": MS(T0 - 1000), "income": "0.5", "asset": "BNB", "incomeType": "TRANSFER", "symbol": "", "tranId": 21},
           {"time": MS(T0 + 300), "income": "-0.001", "asset": "BNB", "incomeType": "COMMISSION", "symbol": "XUSDT", "tradeId": "9", "tranId": 22}]
    return {"nav": [{"nav_ts": T0, "nav": p * W + b0 * 0.5, "wallet_balance": p * W + b0 * 0.5, "mode": "LIVE"},
                    {"nav_ts": T1, "nav": p * W + b1 * 0.499, "wallet_balance": p * W + b1 * 0.499, "mode": "LIVE"}],
            "readbacks": [{"read_ts": T0, "symbol": "XUSDT", "venue_position_qty": 0.0, "venue_position_notional": 0.0},
                          {"read_ts": T1, "symbol": "XUSDT", "venue_position_qty": 0.0, "venue_position_notional": 0.0}],
            "fills": [], "venue_trades": [], "income": inc, "i_lo": MS(T0 - 3600), "i_hi": MS(T1 + 3600),
            "klines": {"USDTUSD": {MIN(T0): kl(0.9995), MIN(T1): kl(0.9995)}, "BNBUSD": {MIN(T0): kl(600.0), MIN(T1): kl(610.0)}},
            "exact": (W, MS(T1 + 60))}


def fx_flat_rate(true_index_t1, band_t1=(0.9994, 0.9996), mid=0.9995):
    """平仓无流水, 钱包 100,000 USDT。t1 那一分钟 K 线: open = close = mid, [low, high] = band_t1; 账户实际用的指数 = true_index_t1。"""
    W = 100000.0
    return {"nav": [{"nav_ts": T0, "nav": mid * (1 - UB) * W, "mode": "LIVE"},
                    {"nav_ts": T1, "nav": true_index_t1 * (1 - UB) * W, "mode": "LIVE"}],
            "readbacks": [{"read_ts": T0, "symbol": "XUSDT", "venue_position_qty": 0.0, "venue_position_notional": 0.0},
                          {"read_ts": T1, "symbol": "XUSDT", "venue_position_qty": 0.0, "venue_position_notional": 0.0}],
            "fills": [], "venue_trades": [], "income": [], "i_lo": MS(T0 - 3600), "i_hi": MS(T1 + 3600),
            "klines": {"USDTUSD": {MIN(T0): kl(mid), MIN(T1): kl(mid, lo=band_t1[0], hi=band_t1[1])},
                       "BNBUSD": {MIN(T0): kl(600.0), MIN(T1): kl(600.0)}},
            "exact": None}


def fx_units():
    """USDTUSD = 0.9(夸张但合法), 钱包 100,000 USDT, 窗内真实漏记 4.7 USDT(资金费)。
    USDT 等价残差 −4.7; USDT 等价容差 max(2, 0.5e-4 × N0/p0) = 5.0; 若容差按 USD(0.5e-4 × N0 = 4.4996)则判红。"""
    p = 0.9 * (1 - UB); W = 100000.0
    f = fx_flat_rate(0.9, band_t1=(0.9, 0.9), mid=0.9)
    f["nav"] = [{"nav_ts": T0, "nav": p * W, "mode": "LIVE"}, {"nav_ts": T1, "nav": p * (W - 4.7), "mode": "LIVE"}]
    return f


# ───────────────────────────── 被测装置驱动 ─────────────────────────────
class Refused(Exception):
    def __init__(self, code): super().__init__(code); self.code = code


def cache_for(fx):
    c = UV.OhlcCache(path=os.path.join(tempfile.mkdtemp(prefix="cid_battery_"), "never_written.json"))
    c.d = {"klines": copy.deepcopy(fx["klines"])}; c.loaded_sha256 = None
    return c


class V3Driver:
    """现役形态: 模块顶层有 build_context / window。"""

    def __init__(self, mod): self.M = mod

    def run(self, fx, poison_trade_table=False):
        M = self.M
        try:
            ctx = M.build_context(nav_rows=fx["nav"], readbacks=fx["readbacks"], ledger_fills=fx["fills"], venue_trades=fx["venue_trades"],
                                  income_rows=fx["income"], i_lo=fx["i_lo"], i_hi=fx["i_hi"], val=M.Valuation(cache_for(fx), True),
                                  exact=fx["exact"], sensitivities=False)
            if poison_trade_table:
                ts, s, q, c, src = ctx.T[0]; ctx.T[0] = (ts, s, float("nan"), c, src)
            return M.window(ctx, fx["nav"][0], fx["nav"][1])
        except M.InputRefused as e:
            raise Refused(e.code)

    @staticmethod
    def headline_ok(w): return w["INDEPENDENT"]["verdict"] == "CONSISTENT"
    @staticmethod
    def point(w): return w["INDEPENDENT"]["residual_point_usdt_eq"]
    @staticmethod
    def cond(w):
        c = w["CONDITIONAL_EXACT_RATE"]
        return (c["available"], c["residual_usdt_eq"], c["within_tol"])


class V2Driver:
    """归档 v2: window / snap / p_exact_at 是 main() 里的嵌套函数 —— 用 AST 原样取出, 在夹具构造的命名空间里执行。
    成交表按 v2 main() 的原表达式构造(它没有输入层); headline = v2 的 `ok`。"""

    def __init__(self, path):
        tree = ast.parse(open(path).read())
        self.fn = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in ("window", "snap", "p_exact_at")}
        assert set(self.fn) == {"window", "snap", "p_exact_at"}, sorted(self.fn)

    def run(self, fx, poison_trade_table=False):
        c = cache_for(fx)
        T = [(float(f["fill_ts"]), f["symbol"], (1.0 if str(f["side"]).upper() == "BUY" else -1.0) * float(f["fill_notional"]) / float(f["fill_px"]),
              (1.0 if str(f["side"]).upper() == "BUY" else -1.0) * float(f["fill_notional"]), "L") for f in fx["fills"]]
        T += [(int(t["time"]) / 1000, t["symbol"], (1.0 if t["buyer"] else -1.0) * abs(float(t["qty"])),
               (1.0 if t["buyer"] else -1.0) * abs(float(t["quoteQty"])), "M") for t in fx["venue_trades"]]
        T.sort()
        if poison_trade_table:
            ts, s, q, cc, src = T[0]; T[0] = (ts, s, float("nan"), cc, src)
        rb = collections.defaultdict(dict)
        for r in fx["readbacks"]: rb[float(r["read_ts"])][r["symbol"]] = r
        It = sorted(fx["income"], key=lambda r: int(r["time"]))
        ns = dict(bisect=bisect, collections=collections, i_lo=fx["i_lo"], i_hi=fx["i_hi"], T=T, Tt=[x[0] for x in T],
                  It=It, Itt=[int(r["time"]) for r in It], ABL=set(), offline=True, rb=rb, snaps=sorted(rb), SNAP_TOL_S=60.0,
                  UV=types.SimpleNamespace(p_usdt=lambda ts, off=False: c.point("USDTUSD", ts, True) * (1 - UB),
                                           b_bnb=lambda ts, off=False: c.point("BNBUSD", ts, True) * (1 - BB)),
                  path=UV.BnbPath(fx["income"]), U=lambda t: time.strftime("%m-%d %H:%M:%SZ", time.gmtime(float(t))))
        if fx["exact"] is not None:
            W_snap, t_snap = fx["exact"]; Iu = [r for r in It if r.get("asset") == "USDT"]
            ut = [int(r["time"]) for r in Iu]; uc = [0.0]
            for r in Iu: uc.append(uc[-1] + float(r["income"]))
            ns.update(W_snap=W_snap, ut=ut, uc=uc)
            exec(compile(ast.Module(body=[self.fn["p_exact_at"]], type_ignores=[]), "v2_p_exact_at", "exec"), ns)
        else:
            ns["p_exact_at"] = lambda ts, wusd: None
        exec(compile(ast.Module(body=[self.fn["snap"], self.fn["window"]], type_ignores=[]), "v2_nested", "exec"), ns)
        return ns["window"](fx["nav"][0], fx["nav"][1])          # v2 没有具名拒绝 —— 这里不会抛 Refused

    @staticmethod
    def headline_ok(w): return bool(w["ok"])
    @staticmethod
    def point(w): return w["residual_usd_identity"]
    @staticmethod
    def cond(w):
        r = w["residual_exact_p"]
        return (r is not None, r, None if r is None else abs(r) <= w["tol"])


def load_driver(path):
    src = open(path).read()
    if "def build_context(" in src:
        spec = importlib.util.spec_from_file_location("cid_under_test", path); m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m); return V3Driver(m)
    return V2Driver(path)


# ───────────────────────────── 电池 ─────────────────────────────
def main():
    dev = os.path.join(HERE, "cash_identity_usd.py")
    if "--device" in sys.argv: dev = os.path.abspath(sys.argv[sys.argv.index("--device") + 1])
    sha = hashlib.sha256(open(dev, "rb").read()).hexdigest()
    D = load_driver(dev)
    print(f"device = {os.path.relpath(dev, HERE)}  sha256 = {sha}  driver = {type(D).__name__}")
    res = []

    def ck(name, fn):
        try:
            ok, detail = fn()
        except Refused as e:
            ok, detail = False, f"unexpected named refusal {e.code}"
        except Exception as e:                                     # 被测装置崩溃 ≠ 通过
            ok, detail = False, f"device raised {type(e).__name__}: {e}"
        res.append(ok); print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
        return ok

    def refused(fx, poison=False):
        try:
            w = D.run(fx, poison_trade_table=poison)
        except Refused as e:
            return True, f"refused {e.code}"
        return False, f"NOT refused: headline_ok={D.headline_ok(w)} point={D.point(w)}"

    def c01():
        w = D.run(fx_baseline()); av, r, wt = D.cond(w)
        return (D.headline_ok(w) and abs(D.point(w)) < 1e-3 and av and wt and abs(r) < 1e-3,
                f"headline_ok={D.headline_ok(w)} point={D.point(w)} conditional=(available={av}, residual={r}, within_tol={wt})")
    if not ck("C01 baseline_green", c01):
        names = ["C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C12", "C13"]
        for n in names: res.append(False); print(f"FAIL {n}: NOT RUN (baseline red — capability checks on a red baseline are vacuous)")
        print(f"RESULT {sum(res)}/{len(res)} PASS, {len(res) - sum(res)} FAIL — device sha256 {sha[:16]}"); return 1

    def c02():
        w = D.run(fx_bnb()); av, r, wt = D.cond(w)
        return D.headline_ok(w) and abs(D.point(w)) < 1e-3 and not av, f"headline_ok={D.headline_ok(w)} point={D.point(w)} conditional_available={av}"
    ck("C02 bnb_baseline_green_and_conditional_unavailable", c02)

    def c03():
        w = D.run(fx_baseline(withdrawal_in_income=False))
        return (not D.headline_ok(w)) and abs(D.point(w) + 100.0) < 1e-3, f"headline_ok={D.headline_ok(w)} point={D.point(w)} (expect INCONSISTENT, ≈ −100)"
    ck("C03 missing_100_withdrawal_caught_by_headline_INDEPENDENT", c03)

    def c04():
        w = D.run(fx_baseline(withdrawal_in_income=False)); av, r, wt = D.cond(w)
        return av and wt and abs(r) < 1e-3, f"conditional=(available={av}, residual={r}, within_tol={wt}) — documented blind spot"
    ck("C04 missing_100_withdrawal_NOT_caught_by_CONDITIONAL_EXACT_RATE_(known_blind_spot)", c04)

    def c05():
        f = fx_baseline(); f["venue_trades"] = [{"symbol": "XUSDT", "id": 77, "time": MS(T0 + 50), "qty": "NaN", "quoteQty": "0", "buyer": True}]
        return refused(f)
    ck("C05 nan_venue_quantity_refused_at_input_layer", c05)

    def c06():
        f = fx_baseline(); f["fills"][0]["fill_px"] = float("inf"); return refused(f)
    ck("C06 inf_ledger_price_refused_at_input_layer", c06)

    def c07(): return refused(fx_baseline(), poison=True)
    ck("C07 nan_injected_into_trade_table_refused_in_window", c07)

    def c08():
        f = fx_baseline(); f["nav"][1]["nav"] = float("nan"); return refused(f)
    ck("C08 nan_nav_refused", c08)

    def c09():
        f = fx_baseline(); f["income"][0]["income"] = "NaN"; return refused(f)
    ck("C09 nan_income_refused", c09)

    def c10():
        f = fx_baseline(); f["readbacks"][1]["venue_position_qty"] = float("nan"); return refused(f)
    ck("C10 nan_readback_quantity_refused", c10)

    def c11():
        w = D.run(fx_flat_rate(0.9996))                  # 账户用了该分钟的 high; 点值(mid)残差 ≈ +10 > 容差 5
        return D.headline_ok(w) and abs(D.point(w)) > 5.0, f"headline_ok={D.headline_ok(w)} point={D.point(w)} (point outside tol, inside band ⇒ expect CONSISTENT)"
    ck("C11 residual_inside_valuation_band_is_CONSISTENT", c11)

    def c12():
        w = D.run(fx_flat_rate(0.9999))                  # 账户计价率在该分钟 [low, high] 之外 ⇒ 区间 ≈ [+30, +50]
        return not D.headline_ok(w), f"headline_ok={D.headline_ok(w)} point={D.point(w)} (expect INCONSISTENT)"
    ck("C12 residual_outside_valuation_band_is_INCONSISTENT", c12)

    def c13():
        w = D.run(fx_units())
        return D.headline_ok(w) and abs(D.point(w) + 4.7) < 1e-3, f"headline_ok={D.headline_ok(w)} point={D.point(w)} (USDT-eq tol 5.0; USD tol would be 4.4996)"
    ck("C13 tolerance_in_same_unit_as_residual_USDT_eq", c13)

    n_fail = len(res) - sum(res)
    print(f"RESULT {sum(res)}/{len(res)} PASS, {n_fail} FAIL — device sha256 {sha[:16]}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
