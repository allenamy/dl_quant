"""三个候选族的【数据可得性】前置门 —— 在做任何因子之前。

教训来源(今天): 解锁轨把数据抓了、特征做了、G1 三个符号全对, 最后死在
「覆盖 25% + 视界严重错配」—— 而**那两件在抓数据之前就能知道**。
⇒ 此后每个新族先过这道门: 覆盖率 / 历史长度 / 更新频率 / 与 110 宇宙的交集。

① 期限结构(季度合约 vs 永续): 110 宇宙里有几个有季度合约?  <20 ⇒ 当场划掉整族
② 借贷利率(做空现货成本, 与永续 funding 不是同一个量): 有没有公开路径?
③ 跨场所(Hyperliquid): symbol 交集多大? funding 历史能拉多久?
"""
import json, urllib.request, urllib.error, time
import numpy as np

UA = {"User-Agent": "Mozilla/5.0"}


def get(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def post(url, payload, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={**UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


UNIV = [str(s) for s in json.load(
    open("/Users/haosiyu/dl_quant_live/state/live/preds_latest.json"))["symbols"]]
print(f"在役宇宙 n={len(UNIV)}\n")

# ═══ ① 期限结构覆盖率 ═══
print("═"*70)
print("① 期限结构 —— 110 宇宙里有几个有季度合约?")
try:
    ei = get("https://fapi.binance.com/fapi/v1/exchangeInfo")
    ct = {}
    for s in ei["symbols"]:
        ct.setdefault(s.get("contractType") or "?", []).append(s["symbol"])
    print(f"  USDT-M 全部合约类型: { {k: len(v) for k, v in ct.items()} }")
    base = {u[:-4] for u in UNIV if u.endswith("USDT")}
    q = [s for k, v in ct.items() if "QUARTER" in k for s in v]
    hitq = sorted({s.split("_")[0] for s in q} & {u for u in UNIV})
    print(f"  季度合约总数 {len(q)}  其中 base 属于在役宇宙的: {len(hitq)}  {hitq[:8]}")
    # COIN-M 也看一眼
    try:
        di = get("https://dapi.binance.com/dapi/v1/exchangeInfo")
        dct = {}
        for s in di["symbols"]:
            dct.setdefault(s.get("contractType") or "?", []).append(s["symbol"])
        dq = [s for k, v in dct.items() if "QUARTER" in k for s in v]
        dbase = sorted({s.split("_")[0].replace("USD", "USDT") for s in dq} & set(UNIV))
        print(f"  COIN-M 季度 {len(dq)} 个, base 命中在役宇宙 {len(dbase)}: {dbase[:8]}")
    except Exception as e:
        print(f"  COIN-M 查询失败: {e}")
    n = len(set(hitq) | set(dbase if 'dbase' in dir() else []))
    print(f"  ⇒ 合并命中 {n} / {len(UNIV)}  "
          f"{'★ <20 ⇒ 做不成 110 名的横截面腿, 整族划掉' if n < 20 else '可继续'}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

# ═══ ② 借贷利率 ═══
print("\n" + "═"*70)
print("② 借贷利率 —— 有没有【公开】路径(不动交易密钥)?")
cands = [
    ("bapi 跨杠杆全量", "https://www.binance.com/bapi/margin/v1/public/margin/vip/spec/list-all"),
    ("bapi 逐币利率", "https://www.binance.com/bapi/margin/v1/public/margin/interest-rate?asset=BTC"),
]
for name, u in cands:
    try:
        d = get(u, timeout=12)
        s = json.dumps(d)[:220]
        print(f"  ✓ {name}: {s}")
    except Exception as e:
        print(f"  ✗ {name}: {type(e).__name__} {getattr(e,'code','')}")

# ═══ ③ Hyperliquid 交集与 funding ═══
print("\n" + "═"*70)
print("③ 跨场所 Hyperliquid —— symbol 交集与 funding 可得性")
try:
    d = post("https://api.hyperliquid.xyz/info", {"type": "metaAndAssetCtxs"})
    meta, ctxs = d[0], d[1]
    names = [u["name"] for u in meta["universe"]]
    print(f"  HL perp n={len(names)}")
    inter = sorted({n for n in names if f"{n}USDT" in UNIV})
    print(f"  与在役宇宙交集: {len(inter)}  {inter[:12]}")
    fr = {}
    for nm, c in zip(names, ctxs):
        if nm in inter and c.get("funding") is not None:
            fr[nm] = float(c["funding"])
    v = np.array(list(fr.values()))
    print(f"  当前 funding 可读 {len(fr)} 个  "
          f"分位[1,50,99] = {np.percentile(v,[1,50,99]).round(7) if len(v) else '—'}")
    # 历史 funding
    try:
        h = post("https://api.hyperliquid.xyz/info",
                 {"type": "fundingHistory", "coin": "BTC",
                  "startTime": int((time.time()-86400*30)*1000)})
        print(f"  BTC 近 30 天 funding 历史条数: {len(h)}  "
              f"(样本 {h[0] if h else '—'})")
    except Exception as e:
        print(f"  历史查询失败: {type(e).__name__}: {e}")
    print(f"  ⇒ 交集 {len(inter)}/{len(UNIV)} "
          f"{'★ 足够做横截面' if len(inter) >= 40 else '★ 偏薄, 只能做子集腿'}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")
