"""把 data/wide 的 140 列 CSV 从 2026-06-30 延到 2026-07-31 —— S2 的前置。

★ 两条已付过代价的教训直接编进来:
 1. **低并发 + 区分 404 与传输失败**。B4 用 -P 16 时对已知存在的符号拿到 `000`,
    那是 curl 传输失败被误读成 404(记忆 ma_v3_track2 的"限流假 NODATA")。本脚本
    并发=4, 对非 404 的失败退避重试 4 次, 且**只有 HTTP 404 才算"该月不存在"**。
 2. **断言拼接真的发生且没有重叠/空洞**。新数据的首个时间戳必须严格大于原末行,
    且间隔正好是一个 bar(klines 1h)。不满足就跳过该符号并具名报告, 绝不静默拼。

★ 只增不改: 原 CSV 先复制到 *.bak_pre0731, 再原地追加。任何断言失败 ⇒ 该符号整体跳过。
"""
import io, os, sys, csv, time, zipfile, shutil, json
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

R = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
W = R + "/data/wide"
CDN = "https://data.binance.vision/data/futures/um/monthly"
YM = "2026-07"
UA = {"User-Agent": "Mozilla/5.0 (research data pull)"}
NPAR = 4
RETRY = 4
HOUR_MS = 3600_000


def fetch(url):
    """(status, bytes). status: 200 / 404 / -1(传输失败, 已重试). ★404 与 -1 必须分开。"""
    last = None
    for i in range(RETRY):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return 200, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, b""          # 真 404: 该月不存在, 不重试
            last = f"HTTP {e.code}"
        except Exception as e:
            last = repr(e)[:80]
        time.sleep(1.5 * (i + 1))        # 退避
    return -1, last.encode() if isinstance(last, str) else b""


def rows_from_zip(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = z.namelist()[0]
        txt = z.read(name).decode("utf-8", "replace")
    out = list(csv.reader(io.StringIO(txt)))
    # 归档可能带表头也可能不带: 首格不是数字就当表头丢掉
    if out and out[0]:
        try:
            float(out[0][0])
        except ValueError:
            out = out[1:]
    return out


def last_ts(path):
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        back = min(4096, end)
        f.seek(end - back)
        tail = f.read().decode("utf-8", "replace").strip().splitlines()
    return int(tail[-1].split(",")[0])


def do_symbol(sym):
    rep = {"sym": sym}
    kpath = f"{W}/{sym}_klines_1h.csv"
    fpath = f"{W}/{sym}_funding.csv"
    if not (os.path.exists(kpath) and os.path.exists(fpath)):
        rep["skip"] = "csv missing"; return rep

    # ── klines ────────────────────────────────────────────────────────────────
    st, blob = fetch(f"{CDN}/klines/{sym}/1h/{sym}-1h-{YM}.zip")
    rep["klines_status"] = st
    if st == -1:
        rep["skip"] = "klines transfer failure (NOT 404)"; return rep
    krows = rows_from_zip(blob) if st == 200 else []

    # ── funding ───────────────────────────────────────────────────────────────
    st2, blob2 = fetch(f"{CDN}/fundingRate/{sym}/{sym}-fundingRate-{YM}.zip")
    rep["funding_status"] = st2
    if st2 == -1:
        rep["skip"] = "funding transfer failure (NOT 404)"; return rep
    frows = rows_from_zip(blob2) if st2 == 200 else []

    if not krows and not frows:
        rep["skip"] = "both 404 (月内无该符号)"; return rep

    # ── 断言 + 追加 ───────────────────────────────────────────────────────────
    for path, rows, kind in ((kpath, krows, "klines"), (fpath, frows, "funding")):
        if not rows:
            rep[f"{kind}_appended"] = 0; continue
        lt = last_ts(path)
        new = [r for r in rows if int(float(r[0])) > lt]
        rep[f"{kind}_last_old"] = lt
        rep[f"{kind}_first_new"] = int(float(new[0][0])) if new else None
        if not new:
            rep[f"{kind}_appended"] = 0; continue
        if kind == "klines":
            gap = int(float(new[0][0])) - lt
            if gap != HOUR_MS:                      # 必须正好一个 bar
                rep["skip"] = f"klines gap {gap} ms != 1h — 不静默拼"; return rep
        shutil.copy(path, path + ".bak_pre0731")
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            for r in new:
                if kind == "klines":
                    # 归档列: 0 open_time,1 o,2 h,3 l,4 c,5 vol,6 close_time,7 quote_vol
                    w.writerow([int(float(r[0])), r[1], r[2], r[3], r[4], r[5], r[7]])
                else:
                    # 归档列: 0 calc_time,1 funding_interval_hours,2 last_funding_rate
                    w.writerow([int(float(r[0])), r[1], r[2]])
        rep[f"{kind}_appended"] = len(new)
    return rep


syms = sorted({f.split("_klines_1h.csv")[0] for f in os.listdir(W) if f.endswith("_klines_1h.csv")})
print(f"符号数 = {len(syms)}  月份 = {YM}  并发 = {NPAR}", flush=True)
reps = []
with ThreadPoolExecutor(max_workers=NPAR) as ex:
    futs = {ex.submit(do_symbol, s): s for s in syms}
    for i, fu in enumerate(as_completed(futs)):
        r = fu.result(); reps.append(r)
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(syms)}", flush=True)

ok = [r for r in reps if "skip" not in r]
sk = [r for r in reps if "skip" in r]
tr = [r for r in sk if "transfer failure" in r.get("skip", "")]
print(f"\n完成: 成功 {len(ok)}  跳过 {len(sk)}")
print(f"  ★ 传输失败(必须为 0, 否则是限流不是缺数): {len(tr)}")
for r in tr[:8]:
    print(f"      {r['sym']}: {r['skip']}")
from collections import Counter
print("  跳过原因:", dict(Counter(r["skip"] for r in sk)))
kadd = sum(r.get("klines_appended", 0) for r in ok)
fadd = sum(r.get("funding_appended", 0) for r in ok)
print(f"  追加行数: klines {kadd:,}  funding {fadd:,}")
mx = max((r.get("klines_first_new") or 0) for r in ok) if ok else 0
print(f"  新数据最早时间戳(应为 2026-07-01 00:00Z = 1782892800000): "
      f"{min((r.get('klines_first_new') or 9e18) for r in ok):.0f}")
json.dump(reps, open("/tmp/extend_0731_report.json", "w"), indent=1)
print("report -> /tmp/extend_0731_report.json")
