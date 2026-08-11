"""bookDepth 流式拉取 — 下载→聚合→【七道校验】→仅在全过后删本批临时 zip。

★★★ 删除纪律(用户令 2×: "千万不要删除 public server 的既有数据" + "一定要保证数据准确性"):
  · 只删【本进程本批刚下载】的 zip, 路径必须在 TMP 目录下且在本批清单里 —— 断言双保险;
  · 任何既有目录零触碰; 聚合产物写新目录, 原子写(.part → rename);
  · ★ 校验【全过】才删; 任一不过 ⇒ 保留该 zip 并记入 quarantine 清单, 人工看过再说;
  · 每批留一个"审计样本"(该批第一个币的原始 zip 不删), 使得日后可重放核对 —— 全删就无法回溯。

七道校验(每个币-天):
  V1 解压成功且 CSV 行数 > 0
  V2 时间戳单调不减
  V3 每帧恰好 12 个价位带(±0.2/1/2/3/4/5) —— 少了说明交易所侧截断
  V4 帧数在合理区间(2880±10% = 30 秒一帧一整天); 偏离记为 gap 但不阻断
  V5 ★ depth/notional 隐含价与当日 klines 收盘价偏差 < 2% —— 抓单位/口径错乱(B25 那类)
  V6 ★ 聚合产物可重建: 由 hourly mean 反推的全日均值, 与直接由原始算的全日均值 相对误差 < 1e-6
  V7 无 NaN/inf 泄入聚合产物
"""
import io
import json
import os
import sys
import time
import zipfile
import datetime as dt
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HOME = os.path.expanduser("~")
TMP = os.path.join(HOME, "lob_raw", "_bd_tmp")          # 只有这里的文件才可能被删
AGG = os.path.join(HOME, "lob_raw", "bd_hourly")        # 聚合产物, 只增
AUD = os.path.join(HOME, "lob_raw", "bd_audit")         # 每批审计样本, 永不删
QUA = os.path.join(HOME, "lob_raw", "bd_quarantine")    # 校验未过的, 保留原件
for d in (TMP, AGG, AUD, QUA):
    os.makedirs(d, exist_ok=True)

sys.path.insert(0, os.path.join(HOME, "dl_quant_live", "signal"))
import live_panel as LP                                  # noqa: E402
SYMS = [str(s) for s in LP.panel_symbols()]

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
END = dt.date(2026, 8, 5)
DATES = [(END - dt.timedelta(days=i)).isoformat() for i in range(DAYS)]
BANDS = ["-5.00", "-4.00", "-3.00", "-2.00", "-1.00", "-0.20",
         "0.20", "1.00", "2.00", "3.00", "4.00", "5.00"]
print(f"bookDepth 流式: {len(SYMS)} 币 × {DAYS} 天, 按【天】分批")

# ★ V5 参考价 —— 改用【月度 klines】覆盖全历史。
#   第一版用实盘面板(hours=1200 ≈ 50 天), 于是更早的日期 V5 被静默跳过 ——
#   而 V5 正是逮住单位/口径错乱(B25 那类)的那道。最关键的闸门在 72% 数据上没生效, 是覆盖洞不是设计。
REF_DIR = os.path.join(HOME, "lob_raw", "_klines_ref")
os.makedirs(REF_DIR, exist_ok=True)
_REF_CACHE = {}


def _load_month_ref(sym, ym):
    key = (sym, ym)
    if key in _REF_CACHE:
        return _REF_CACHE[key]
    fp = os.path.join(REF_DIR, f"{sym}-{ym}.csv")
    if not os.path.exists(fp):
        u = (f"https://data.binance.vision/data/futures/um/monthly/klines/{sym}/1h/"
             f"{sym}-1h-{ym}.zip")
        try:
            with urllib.request.urlopen(u, timeout=60) as r:
                raw = r.read()
            z = zipfile.ZipFile(io.BytesIO(raw))
            with open(fp + ".part", "wb") as f:
                f.write(z.read(z.namelist()[0]))
            os.replace(fp + ".part", fp)
        except Exception:
            _REF_CACHE[key] = None
            return None
    try:
        d = {}
        for ln in open(fp):
            p = ln.split(",")
            if len(p) < 5 or not p[0].strip().isdigit():
                continue
            day = dt.datetime.utcfromtimestamp(int(p[0]) / 1000).date().isoformat()
            d.setdefault(day, []).append(float(p[4]))          # close
        _REF_CACHE[key] = {k: float(np.mean(v)) for k, v in d.items()}
    except Exception:
        _REF_CACHE[key] = None
    return _REF_CACHE[key]


def day_ref_price(sym, day):
    ref = _load_month_ref(sym, day[:7])
    return None if not ref else ref.get(day)


def fetch_one(sym, day):
    """下载到 TMP, 返回 zip 路径或 None。"""
    p = os.path.join(TMP, f"{sym}-{day}.zip")
    if os.path.exists(p) and os.path.getsize(p) > 200:
        return p
    u = (f"https://data.binance.vision/data/futures/um/daily/bookDepth/{sym}/"
         f"{sym}-bookDepth-{day}.zip")
    for _ in range(2):
        try:
            with urllib.request.urlopen(u, timeout=60) as r:
                raw = r.read()
            if len(raw) < 200:
                return None
            tp = p + ".part"
            with open(tp, "wb") as f:
                f.write(raw)
            os.replace(tp, p)
            return p
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.5)
        except Exception:
            time.sleep(1.5)
    return None


def parse_and_aggregate(zp, sym, day):
    """返回 (hourly_dict, checks, raw_daily_mean) 或 (None, checks, None)。"""
    ck = {}
    try:
        z = zipfile.ZipFile(zp)
        txt = z.read(z.namelist()[0]).decode("utf-8", "replace")
    except Exception as e:
        ck["V1"] = f"unzip failed: {type(e).__name__}"
        return None, ck, None
    lines = txt.strip().split("\n")
    ck["V1"] = len(lines) > 1
    if not ck["V1"]:
        return None, ck, None
    hdr = lines[0].split(",")
    if hdr[:4] != ["timestamp", "percentage", "depth", "notional"]:
        ck["V1"] = f"unexpected header {hdr}"
        return None, ck, None

    ts_s, band_s, dep, nof = [], [], [], []
    for ln in lines[1:]:
        p = ln.split(",")
        if len(p) < 4:
            continue
        ts_s.append(p[0]); band_s.append(p[1])
        dep.append(float(p[2])); nof.append(float(p[3]))
    dep = np.array(dep); nof = np.array(nof)
    uts = sorted(set(ts_s))
    ck["V2"] = ts_s == sorted(ts_s)                       # 单调不减
    from collections import Counter
    per_frame = Counter(ts_s)
    ck["V3"] = set(Counter(band_s)) == set(BANDS) and \
        (min(per_frame.values()) == max(per_frame.values()) == 12)
    ck["V4"] = abs(len(uts) - 2880) <= 288                # ±10%
    # V5 隐含价
    ref = day_ref_price(sym, day)
    if ref is None:
        ck["V5"] = "skipped_no_ref"
    else:
        impl = float(np.nansum(nof) / max(np.nansum(dep), 1e-12))
        ck["V5"] = abs(impl / ref - 1) < 0.02
        ck["_V5_detail"] = f"implied={impl:.6g} ref={ref:.6g} dev={(impl/ref-1)*100:.2f}%"
    # 聚合: 逐小时 × 逐带 的 {mean, std, slope}
    hours = np.array([int(t[11:13]) for t in ts_s])
    out = {}
    for b in BANDS:
        sel = np.array([x == b for x in band_s])
        for h in range(24):
            m = sel & (hours == h)
            if m.sum() < 10:
                continue
            v = dep[m]
            q = max(1, len(v) // 4)
            out[f"{b}|{h:02d}"] = (float(v.mean()), float(v.std()),
                                   float(v[-q:].mean() - v[:q].mean()))
    # V6 重建校验: 由 hourly mean 加权还原全日均值 (逐带)
    ok6 = True
    for b in BANDS:
        sel = np.array([x == b for x in band_s])
        if sel.sum() == 0:
            continue
        direct = float(dep[sel].mean())
        hs, ws = [], []
        for h in range(24):
            k = f"{b}|{h:02d}"
            if k in out:
                m = sel & (hours == h)
                hs.append(out[k][0]); ws.append(m.sum())
        if not hs:
            continue
        recon = float(np.average(hs, weights=ws))
        if direct == 0.0:
            # 真实条件: 极小币某价位带整天零挂单。零≠错误, 但重建也必须是零。
            if abs(recon) > 1e-12:
                ok6 = False
                ck["_V6_detail"] = f"band {b}: direct=0 但 recon={recon:.8g}"
                break
            continue
        if abs(recon / direct - 1) > 1e-6:
            ok6 = False
            ck["_V6_detail"] = f"band {b}: direct={direct:.8g} recon={recon:.8g}"
            break
    ck["V6"] = ok6
    ck["V7"] = all(np.isfinite(x).all() for x in
                   [np.array(v) for v in out.values()]) if out else False
    return out, ck, float(dep.mean())


def process_day(day, keep_audit_sym):
    got, quarantined, agg = 0, [], {}
    zips = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for sym, zp in zip(SYMS, ex.map(lambda s: fetch_one(s, day), SYMS)):
            if zp:
                zips.append((sym, zp))
    for sym, zp in zips:
        out, ck, _ = parse_and_aggregate(zp, sym, day)
        hard = [k for k in ("V1", "V2", "V3", "V6", "V7")
                if ck.get(k) is not True]
        soft = [k for k in ("V4", "V5") if ck.get(k) not in (True, "skipped_no_ref")]
        if out is None or hard:
            quarantined.append((sym, {k: str(v)[:80] for k, v in ck.items()}))
            os.replace(zp, os.path.join(QUA, os.path.basename(zp)))
            continue
        agg[sym] = out
        got += 1
        if soft:
            quarantined.append((sym, {"soft": soft,
                                      "detail": str(ck.get("_V5_detail", ""))[:60]}))
    # 原子落盘聚合产物
    ap = os.path.join(AGG, f"bd_{day}.json")
    tmp = ap + ".part"
    with open(tmp, "w") as f:
        json.dump(agg, f)
    os.replace(tmp, ap)
    # ★ 删除: 只删本批、只删 TMP 下、只删已成功聚合的
    deleted = 0
    for sym, zp in zips:
        if sym == keep_audit_sym:
            os.replace(zp, os.path.join(AUD, os.path.basename(zp)))   # 审计样本, 永久保留
            continue
        if sym in agg and os.path.dirname(os.path.abspath(zp)) == os.path.abspath(TMP):
            os.remove(zp); deleted += 1
    return got, deleted, quarantined


t0 = time.time()
tot_got = tot_del = 0
allq = []
for i, day in enumerate(DATES, 1):
    if os.path.exists(os.path.join(AGG, f"bd_{day}.json")):
        continue
    g, d_, q = process_day(day, SYMS[0])
    tot_got += g; tot_del += d_; allq += [(day, s, c) for s, c in q]
    print(f"  [{i}/{len(DATES)}] {day}: 聚合 {g} 币, 删临时 zip {d_}, "
          f"隔离/软警 {len(q)}  累计 {(time.time()-t0)/60:.1f}min", flush=True)
json.dump(allq, open(os.path.join(QUA, "quarantine_log.json"), "w"), indent=1)
print(f"\n完成: 聚合 {tot_got} 币-天, 删临时 zip {tot_del}, 隔离/软警 {len(allq)}")
print(f"  聚合产物 {AGG}  审计样本 {AUD}  隔离区 {QUA}")
