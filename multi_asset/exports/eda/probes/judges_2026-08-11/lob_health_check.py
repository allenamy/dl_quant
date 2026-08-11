"""bookDepth + metrics 三天体检 —— 拉全量之前先验口径与覆盖。

★ 体检要回答的六件事(先写死, 免得看到数据再定标准):
  H1 覆盖率: 110 币宇宙里有多少个能拿到? 缺的是哪些(小币? 新上市?)
  H2 时间网格: 每天多少帧? 是否规整? 与我们的 4h 锚如何对齐?
  H3 字段口径: bookDepth 的 percentage/depth/notional 到底是什么单位、什么符号约定
  H4 缺失形态: 空洞是随机还是成块(成块=交易所侧停更, 会变成假信号)
  H5 ★ 因果性: 每帧的 timestamp 是【区间末】还是【区间初】—— 决定 4h 聚合时能不能用最后一帧
  H6 信息量预览: 深度不平衡与【下一个 4h 收益】的横截面 IC(只作方向, 3 天无统计力)

不做: 任何特征定稿、任何门、任何结论。体检就是体检。
"""
import io
import json
import os
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np

DAYS = ["2026-07-29", "2026-07-30", "2026-07-31"]
OUT = "/tmp/lob_health"
os.makedirs(OUT, exist_ok=True)
BASE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"

P = np.load(f"{BASE}/wide_dl_full_corrfund_causal_0731.npz", allow_pickle=True)
SYMS = [str(s) for s in P["symbols"]]
MEM = P["MEMBER110"]; TS = P["ts"]; Y4 = P["Y4"]; CL4 = P["CL4"]
print(f"宇宙 {len(SYMS)} 币 (面板 symbols)")


def fetch(kind, sym, day):
    u = (f"https://data.binance.vision/data/futures/um/daily/{kind}/{sym}/"
         f"{sym}-{kind}-{day}.zip")
    try:
        r = subprocess.run(["curl", "-sL", "--max-time", "60", u],
                           capture_output=True, timeout=90)
        if r.returncode != 0 or len(r.stdout) < 200:
            return sym, day, None
        z = zipfile.ZipFile(io.BytesIO(r.stdout))
        name = z.namelist()[0]
        return sym, day, z.read(name).decode("utf-8", "replace")
    except Exception:
        return sym, day, None


for KIND in ("bookDepth", "metrics"):
    print(f"\n{'='*70}\n[{KIND}] 三天 × {len(SYMS)} 币")
    jobs = [(KIND, s, d) for s in SYMS for d in DAYS]
    got = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        for sym, day, txt in ex.map(lambda a: fetch(*a), jobs):
            if txt:
                got.setdefault(sym, {})[day] = txt
    full = [s for s in SYMS if len(got.get(s, {})) == len(DAYS)]
    part = [s for s in SYMS if 0 < len(got.get(s, {})) < len(DAYS)]
    none = [s for s in SYMS if not got.get(s)]
    print(f"  H1 覆盖: 全三天 {len(full)}/{len(SYMS)}  部分 {len(part)}  完全无 {len(none)}")
    if none:
        print(f"     无数据的: {none[:12]}{' ...' if len(none)>12 else ''}")
    if part:
        print(f"     部分的:   {part[:8]}")
    if not full:
        continue
    s0 = full[0]
    txt = got[s0][DAYS[0]]
    lines = txt.strip().split("\n")
    print(f"  H3 表头({s0}): {lines[0]}")
    print(f"     首行: {lines[1]}")
    print(f"     末行: {lines[-1]}")
    print(f"  H2 帧数/天: {len(lines)-1}", end="")
    if KIND == "bookDepth":
        # 每个 timestamp 有多少个 percentage 档
        from collections import Counter
        pcs = Counter()
        tss = []
        for l in lines[1:400]:
            p = l.split(",")
            pcs[p[1]] += 1
            tss.append(p[0])
        uniq_ts = sorted(set(tss))
        print(f"  ⇒ 唯一时间戳 {len(uniq_ts)}, 每帧 {len(pcs)} 个价位带")
        print(f"     价位带: {sorted(pcs, key=float)}")
        print(f"     相邻帧间隔: {uniq_ts[0]} → {uniq_ts[1]} → {uniq_ts[2]}")
        # H4 缺失形态: 一天应有多少帧
        allts = sorted({l.split(",")[0] for l in lines[1:]})
        print(f"  H4 全天唯一帧 {len(allts)} (若 1440=每分钟; 缺口成块? "
              f"首 {allts[0]} 末 {allts[-1]})")
    else:
        print()
        allts = [l.split(",")[0] for l in lines[1:]]
        print(f"  H2 间隔: {allts[0]} → {allts[1]}  (共 {len(allts)} 帧/天)")

    json.dump({s: list(d) for s, d in list(got.items())[:5]},
              open(f"{OUT}/{KIND}_sample_index.json", "w"))
    # 存一份供 H6
    if KIND == "bookDepth":
        np.save(f"{OUT}/bd_full_syms.npy", np.array(full))
        with open(f"{OUT}/bd_sample.csv", "w") as f:
            f.write(got[s0][DAYS[0]])
    else:
        np.save(f"{OUT}/mt_full_syms.npy", np.array(full))
        with open(f"{OUT}/mt_sample.csv", "w") as f:
            f.write(got[s0][DAYS[0]])
print("\n体检数据留在", OUT)
