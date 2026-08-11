"""阶段 A 拉取 — metrics(持仓/多空比/主动买卖比) 全宇宙 × 180 天。

★ 纪律(用户令 + 项目家规):
  · 只【新增】不删除不覆盖: 目标目录是新建的 lob_raw/, 已存在的文件直接跳过(断点续传);
  · 礼貌限速: 6 并发 + 每请求间隔, 避免重蹈 sshd 那种自找的封禁;
  · 断线无关: 本机跑, nohup 式后台, ssh 状态不影响;
  · 先 metrics 后 bookDepth: metrics 服务侧零风险(简单 REST 全宇宙), bookDepth 宽带卡在
    REST 1000 档复现不了 BTC/ETH ⇒ 不让它挡住能立刻做的那半。
  · 口径已查实: data/futures/um/ = USDⓈ-M 【永续】, 与目标 y 同市场(避免 B25 那类 spot/perp 错配)。
"""
import io
import os
import sys
import time
import zipfile
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.error

OUT = os.path.expanduser("~/lob_raw/metrics")  # 只增, 已有的自动跳过
os.makedirs(OUT, exist_ok=True)
DAYS = 1160   # 全史: 2022-06 起(训练面板年折需要多年)
END = dt.date(2026, 8, 5)          # 归档 T+1, 08-06 尚无
DATES = [(END - dt.timedelta(days=i)).isoformat() for i in range(DAYS)]

# 宇宙: 用实盘面板的 symbols(与训练面板一致)
sys.path.insert(0, os.path.expanduser("~/dl_quant_live/signal"))
import numpy as np
try:
    import live_panel as LP
    SYMS = [str(s) for s in LP.panel_symbols()]
except Exception:
    SYMS = []
if not SYMS:
    print("panel_symbols 不可用, 退出"); sys.exit(1)
print(f"宇宙 {len(SYMS)} 币 × {DAYS} 天 = {len(SYMS)*DAYS:,} 文件")

done = skip = fail = 0
t0 = time.time()


def one(sym, day):
    path = os.path.join(OUT, f"{sym}-{day}.csv")
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return "skip"
    u = (f"https://data.binance.vision/data/futures/um/daily/metrics/{sym}/"
         f"{sym}-metrics-{day}.zip")
    for attempt in range(2):
        try:
            with urllib.request.urlopen(u, timeout=45) as r:
                raw = r.read()
            z = zipfile.ZipFile(io.BytesIO(raw))
            data = z.read(z.namelist()[0])
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)          # 原子: 半截文件不会被后续跑当成完成
            return "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "404"               # 该币该日无数据(退市/未上市) — 正常, 不重试
            time.sleep(1.5)
        except Exception:
            time.sleep(1.5)
    return "fail"


jobs = [(s, d) for s in SYMS for d in DATES]
print(f"起拉 {len(jobs):,} 个 (已存在的自动跳过)")
with ThreadPoolExecutor(max_workers=6) as ex:
    futs = {ex.submit(one, s, d): (s, d) for s, d in jobs}
    for i, fu in enumerate(as_completed(futs), 1):
        r = fu.result()
        if r == "ok": done += 1
        elif r == "skip": skip += 1
        else: fail += 1
        if i % 500 == 0:
            el = time.time() - t0
            print(f"  {i:,}/{len(jobs):,}  新拉 {done:,} 跳过 {skip:,} 无数据/失败 {fail:,}  "
                  f"{el/60:.1f}min  预计还需 {(len(jobs)-i)*el/i/60:.0f}min", flush=True)
print(f"完成: 新拉 {done:,} 跳过 {skip:,} 无/失败 {fail:,}  用时 {(time.time()-t0)/60:.1f}min")
print(f"落在 {OUT}")
