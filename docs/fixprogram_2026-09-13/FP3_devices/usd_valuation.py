#!/usr/bin/env python3
"""账户 NAV 的【计价单位】—— 现金恒等式此前漏掉的一整类项(2026-09-19 实测)。只读。

事实(read-only 密钥实测, 收据见 FP3_receipts/venue_readonly_2026-09-19/):
  - 账户开着 multiAssetsMargin = True。
  - daily_nav.nav = totalWalletBalance + totalUnrealizedProfit (/fapi/v3/account), 这两个总额是【USD】, 不是 USDT:
    实测 totalWalletBalance 118,245.47 = USDT walletBalance 118,290.66 × 0.99962; unrealized 同比。
  - 0.99962 = USDTUSD 指数 × (1 − bidBuffer 0.0001), 与 /fapi/v1/assetIndex 的 bidRate 一致。BNB 按 BNBUSD 指数 × (1 − 0.05) 计入。
  - 恒等式其它每一项(持仓市值、成交现金、资金费、手续费)都是 USDT。⇒ 此前的恒等式把 USD 的 NAV 与 USDT 的流量直接相减。
    在 ~85k 的 NAV 上, USDT 指数动 1e-4 就是 ~8.5 USD —— 正是空仓时段 NAV 的 ±8 USD 跳动(9 月 7 个空仓窗, 用本模块解释到 ±0.6)。

本模块只做三件事, 并把每个用到的价格落盘(同一输入复跑逐位相同):
  p_usdt(ts)  = USDTUSD 指数(1 分钟 K 线, 按秒线性插值) × (1 − USDT_BID_BUFFER)
  b_bnb(ts)   = BNBUSD  指数(同上)                     × (1 − BNB_BID_BUFFER)
  bnb_balance(ts) = 由场所收入流水(TRANSFER / COMMISSION, asset = BNB)累加的 BNB 余额路径
已声明的假设(可证伪, 不静默): 两个 bidBuffer 在 08-01..09-19 期间为常数(当下值)。若历史上改过, 空仓窗的闭合会先坏 —— 那是它的检验。
指数 K 线来自公开端点 /fapi/v1/indexPriceKlines(无需密钥)。"""
import bisect, json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
USDT_BID_BUFFER = 0.0001
BNB_BID_BUFFER = 0.05
CACHE = os.path.join(HERE, "..", "FP3_receipts", "venue_readonly_2026-09-19", "INDEX_KLINES_1m_cache.json")
_cache = None


def _load():
    global _cache
    if _cache is None:
        _cache = json.load(open(CACHE)) if os.path.isfile(CACHE) else {"source": "/fapi/v1/indexPriceKlines interval=1m (public)",
                                                                           "rule": "value(ts) = open + (close − open) × (seconds into minute / 60)",
                                                                           "klines": {}}
    return _cache


def save():
    if _cache is None: return
    tmp = CACHE + ".part"
    with open(tmp, "w") as fh: json.dump(_cache, fh, sort_keys=True)
    os.replace(tmp, CACHE)


def index_at(pair, ts, offline=False):
    """pair ∈ {USDTUSD, BNBUSD}; ts = unix seconds. offline=True refuses to fetch (a rerun must reproduce from the cache)."""
    c = _load()["klines"].setdefault(pair, {})
    m = int(float(ts) // 60 * 60 * 1000); k = str(m)
    if k not in c:
        if offline: raise KeyError(f"{pair} minute {m} not in cache (offline)")
        url = f"https://fapi.binance.com/fapi/v1/indexPriceKlines?pair={pair}&interval=1m&startTime={m}&limit=1"
        body = json.loads(urllib.request.urlopen(url, timeout=20).read()); time.sleep(0.12)
        if not body or int(body[0][0]) != m: raise RuntimeError(f"{pair} kline for minute {m} missing: {str(body)[:120]}")
        c[k] = [float(body[0][1]), float(body[0][4])]
    o, cl = c[k]
    return o + (cl - o) * ((float(ts) - m / 1000) / 60.0)


def p_usdt(ts, offline=False): return index_at("USDTUSD", ts, offline) * (1 - USDT_BID_BUFFER)
def b_bnb(ts, offline=False): return index_at("BNBUSD", ts, offline) * (1 - BNB_BID_BUFFER)


class BnbPath:
    """BNB 余额 = 起点 0 + Σ(BNB 的 TRANSFER) + Σ(BNB 的 COMMISSION, 为负) + Σ(其它 BNB 收入)。
    两端都被检验: 第一笔 BNB 流水之前余额必须是 0 且不出现负值; 终点必须等于账户当下的 BNB 余额(调用方传入实测值)。"""

    def __init__(self, rows):
        ev = sorted((int(r["time"]), float(r["income"]), r["incomeType"]) for r in rows if r.get("asset") == "BNB")
        self.t = [e[0] for e in ev]; bal = 0.0; self.b = []; self.min_bal = 0.0; self.by_type = {}
        for t, x, ty in ev:
            bal += x; self.b.append(bal); self.min_bal = min(self.min_bal, bal)
            self.by_type[ty] = self.by_type.get(ty, 0.0) + x
        self.end = bal; self.n = len(ev)

    def at(self, ts):
        """余额在 ts(秒)时刻【之后】的值 —— 含 time ≤ ts 的全部流水"""
        i = bisect.bisect_right(self.t, int(round(float(ts) * 1000)))
        return self.b[i - 1] if i else 0.0
