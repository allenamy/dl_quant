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
指数 K 线来自公开端点 /fapi/v1/indexPriceKlines(无需密钥)。

★ v2(2026-09-19, 复审第四轮 R4-C3): 新增 OhlcCache —— 每分钟存 [open, high, low, close], 给现金恒等式的【独立计价轨】
  一个外生的计价误差带: 账户在 NAV 那一刻实际用的指数价 ∈ 该分钟 K 线的 [low, high]。
  下面的 index_at / p_usdt / b_bnb / save / CACHE 与 v1(archive/usd_valuation_v1_e892221f.py)逐字节同义, 不改 —— 其它装置
  (flatten_window_closure.py)与 v2 恒等式收据依赖它们; OHLC 用另一个缓存文件, 旧缓存不被改写。
  OhlcCache 在输入层拒绝非有限/非正/不自洽(low ≤ open,close ≤ high)的 K 线, 抛 InputRefused。"""
import bisect, hashlib, json, math, os, time, urllib.request

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


# ───────────────────────── v2: OHLC 缓存(独立计价轨的误差带) ─────────────────────────
OHLC_CACHE = os.path.join(HERE, "..", "FP3_receipts", "venue_readonly_2026-09-19", "INDEX_KLINES_1m_OHLC_cache.json")
PUBLIC_KLINE_URL = "https://fapi.binance.com/fapi/v1/indexPriceKlines"
MIN_SLEEP_S = 0.15                      # 公开端点节流: 每次调用之后至少 0.15 s(约束是 ≥ 0.12 s)


class InputRefused(ValueError):
    """输入层拒绝: code 是具名拒绝类(REFUSED_NONFINITE / REFUSED_INCONSISTENT_KLINE / REFUSED_MISSING_FIELD …)。"""

    def __init__(self, code, where):
        super().__init__(f"{code}: {where}"); self.code = code; self.where = where


def finite(x, where, positive=False):
    """把一个【被用到的】数值字段转成有限浮点; None / 非数 / ±inf / NaN(以及 positive=True 时 ≤ 0)一律拒绝。
    拒绝必须发生在输入层 —— 比较表达式对 NaN 恒为 False, 放到判词里就是静默通过(复审 R4 输入有限性)。"""
    if x is None or isinstance(x, bool):
        raise InputRefused("REFUSED_MISSING_FIELD", where)
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise InputRefused("REFUSED_NONNUMERIC", f"{where}={x!r}")
    if not math.isfinite(v):
        raise InputRefused("REFUSED_NONFINITE", f"{where}={x!r}")
    if positive and not v > 0.0:
        raise InputRefused("REFUSED_NONPOSITIVE", f"{where}={x!r}")
    return v


class OhlcCache:
    """每个 (pair, minute_ms) 存 [open, high, low, close](均为浮点)。
    point(ts)   = open + (close − open) × (ts 在该分钟内的秒数 / 60)          —— 与 v1 index_at 同一插值
    band(ts, span) = [min low, max high] over 分钟 m − span … m + span(m = ts 所在分钟) —— span=0 是主规则
    联网只取公开 K 线, 一次取 [m − 1, m, m + 1] 三根(limit=3), 三根都入缓存。offline=True 时缺分钟直接 KeyError。
    content_sha256() = 缓存落盘字节(json, sort_keys)的 sha256; used_sha256() = 本次运行实际读到的分钟值的 sha256。"""

    def __init__(self, path=OHLC_CACHE, fetch=None):
        self.path = path; self.d = None; self.used = {}; self.n_fetch_calls = 0
        self._fetch = fetch                      # 测试注入; None ⇒ 公开端点

    def _load(self):
        if self.d is None:
            if os.path.isfile(self.path):
                with open(self.path, "rb") as fh: raw = fh.read()
                self.d = json.loads(raw); self.loaded_sha256 = hashlib.sha256(raw).hexdigest()
            else:
                self.d = {"source": "/fapi/v1/indexPriceKlines interval=1m (public, no key)",
                          "format": "klines[pair][minute_open_ms] = [open, high, low, close]",
                          "rule": "point(ts) = open + (close − open) × (seconds into minute / 60); band(ts) = [low, high] of the minute containing ts",
                          "klines": {}}
                self.loaded_sha256 = None
        return self.d

    @staticmethod
    def _check(pair, k, v):
        if not (isinstance(v, list) and len(v) == 4):
            raise InputRefused("REFUSED_BAD_KLINE", f"{pair} {k} {v!r}")
        o, h, l, c = (finite(x, f"kline {pair} {k}[{i}]", positive=True) for i, x in enumerate(v))
        if not (l <= min(o, c) and max(o, c) <= h):
            raise InputRefused("REFUSED_INCONSISTENT_KLINE", f"{pair} {k} o={o} h={h} l={l} c={c}")
        return o, h, l, c

    def _default_fetch(self, pair, m):
        url = f"{PUBLIC_KLINE_URL}?pair={pair}&interval=1m&startTime={m - 60000}&limit=3"
        body = json.loads(urllib.request.urlopen(url, timeout=20).read())
        time.sleep(MIN_SLEEP_S)
        return body

    def _get(self, pair, m, offline):
        c = self._load()["klines"].setdefault(pair, {}); k = str(m)
        if k not in c:
            if offline: raise KeyError(f"{pair} minute {m} not in OHLC cache (offline)")
            body = (self._fetch or self._default_fetch)(pair, m); self.n_fetch_calls += 1
            now_ms = time.time() * 1000
            for row in body or []:
                if int(row[6]) >= now_ms: continue            # 未收盘的分钟(high/low 还在变)不入缓存
                c[str(int(row[0]))] = [float(row[1]), float(row[2]), float(row[3]), float(row[4])]
            if k not in c: raise RuntimeError(f"{pair} kline for minute {m} missing: {str(body)[:160]}")
        v = self._check(pair, k, c[k]); self.used[f"{pair}|{k}"] = list(v)
        return v

    def point(self, pair, ts, offline=False):
        ts = finite(ts, f"point ts {pair}"); m = int(ts // 60 * 60 * 1000)
        o, h, l, cl = self._get(pair, m, offline)
        return o + (cl - o) * ((ts - m / 1000) / 60.0)

    def band(self, pair, ts, offline=False, span=0):
        ts = finite(ts, f"band ts {pair}"); m = int(ts // 60 * 60 * 1000)
        lo, hi = math.inf, -math.inf
        for j in range(-span, span + 1):
            o, h, l, cl = self._get(pair, m + 60000 * j, offline)
            lo, hi = min(lo, l), max(hi, h)
        return lo, hi

    def save(self):
        if self.d is None: return None
        raw = json.dumps(self.d, sort_keys=True).encode()
        tmp = self.path + ".part"
        with open(tmp, "wb") as fh: fh.write(raw)
        os.replace(tmp, self.path)
        with open(self.path, "rb") as fh: back = fh.read()
        if back != raw: raise RuntimeError("OHLC cache write-back mismatch")
        return hashlib.sha256(back).hexdigest()

    def content_sha256(self):
        """落盘文件当前内容的 sha256(运行结束时读; 离线运行不写文件, 即读入时的内容)。"""
        with open(self.path, "rb") as fh: return hashlib.sha256(fh.read()).hexdigest()

    def used_sha256(self):
        return hashlib.sha256(json.dumps(self.used, sort_keys=True).encode()).hexdigest()
