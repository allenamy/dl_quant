"""#51 basis 外生驱动族 —— 数据拉取 (PREREG_basis_external_driver_2026-08-06, sha 8bee24a6ca2876ab)

只读 Binance 公开端点 premiumIndexKlines(免鉴权)。不触碰 share data, 不触碰实盘, 不占 GPU。
输出: exports/eda/basis_premium_1h.npz  (ts_hour, symbols, PREM[T,N])  —— 逐小时 premium index 收盘值。

★ 因果性: k线的【收盘】值取在 close_time, 我们把它记在 open_time+1h 这个【右端】时刻,
  与面板 ts 对齐时只允许用严格 ≤t 的小时。对齐在建通道那一步做, 本脚本只如实落原始网格。
★ 上市前的时段: 端点对不存在的期间直接不返回, 落 NaN —— 这正是 point-in-time 该有的形状,
  不得前向填充(那会把上市前的"零基差"当成真实状态)。
"""
import json, os, sys, time, urllib.request, urllib.error
import numpy as np

OUT = os.path.expanduser("~/Desktop/quant_research/multi_asset/exports/eda/basis_premium_1h.npz")
MARK = "/tmp/pull_basis.DONE"
PANEL_SYMS = sys.argv[1] if len(sys.argv) > 1 else None
START_MS = 1609459200000          # 2021-01-01, 面板左端(端点实测最早 2022-01-01, 更早自然缺)
END_MS = 1785538800000 + 3600000  # 面板右端 +1h
BASE = "https://fapi.binance.com/fapi/v1/premiumIndexKlines"
LIMIT = 1000


def get(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code == 418:
                time.sleep(5 * (i + 1))          # 限流: 退避, 不放弃
                continue
            if e.code == 400:
                return []                         # 该 symbol 在该窗口不存在 —— 合法的空
            time.sleep(1 + i)
        except Exception:
            time.sleep(1 + i)
    return None                                   # None = 拉取失败(与"空"区分开)


def pull_symbol(sym):
    out, cur, fails = {}, START_MS, 0
    while cur < END_MS:
        url = f"{BASE}?symbol={sym}&interval=1h&startTime={cur}&limit={LIMIT}"
        rows = get(url)
        if rows is None:
            fails += 1
            if fails >= 3:
                return out, False                 # 明确的失败, 不伪装成"没有数据"
            continue
        if not rows:
            break
        for r in rows:
            out[int(r[0])] = float(r[4])          # close of premium index
        nxt = int(rows[-1][0]) + 3600000
        if nxt <= cur:
            break
        cur = nxt
        if len(rows) < LIMIT:
            break
        time.sleep(0.04)                          # ~25 req/s, 远低于 2400 权重/分钟
    return out, True


def main():
    syms = json.load(open(PANEL_SYMS)) if PANEL_SYMS else None
    if syms is None:
        print("需要 symbols json 路径", flush=True); sys.exit(1)
    grid = np.arange(START_MS, END_MS, 3600000, dtype=np.int64)
    gidx = {int(t): i for i, t in enumerate(grid)}
    P = np.full((len(grid), len(syms)), np.nan, np.float32)
    t0, n_ok, n_fail, failed = time.time(), 0, 0, []
    for j, s in enumerate(syms):
        d, ok = pull_symbol(s)
        if not ok:
            n_fail += 1; failed.append(s)
        for t, v in d.items():
            i = gidx.get(t)
            if i is not None:
                P[i, j] = v
        n_ok += bool(d)
        if j % 10 == 0:
            print(f"  {j}/{len(syms)} {s} rows={len(d)} ({time.time()-t0:.0f}s) "
                  f"ok={n_ok} fail={n_fail}", flush=True)
    np.savez_compressed(OUT, ts_hour=grid, symbols=np.array(syms, dtype=object),
                        PREM=P, prereg="PREREG_basis_external_driver_2026-08-06.md",
                        prereg_sha="8bee24a6ca2876ab",
                        source="GET /fapi/v1/premiumIndexKlines interval=1h close",
                        failed_symbols=np.array(failed, dtype=object))
    fin = float(np.isfinite(P).mean())
    print(f"saved -> {OUT}  shape={P.shape} finite={fin:.3f} "
          f"symbols_with_data={n_ok}/{len(syms)} transfer_failures={n_fail}", flush=True)
    json.dump({"finite": fin, "n_ok": n_ok, "n_fail": n_fail, "failed": failed},
              open(MARK, "w"))


if __name__ == "__main__":
    main()
