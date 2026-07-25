# Hyperliquid archive — 只读公开行情落库

> **创建:** 2026-07-25 JST | **Session:** multi-asset-v2 (0B) | **状态:** live (cron 常驻)
> **作废条件:** 放弃 HL 作为候选场所; 或 HL 改变 API 限制/端点
> 纪律: 只打公开 `/info` 与公开 websocket, **未碰任何 trading/auth 端点**, 无任何绕过地理限制的操作

## 为什么现在就要落库 (时间敏感)

**HL 的 `candleSnapshot` 有 5000 行硬顶 ⇒ 小时线只有一个滚动 ~210 天窗口** (实测 BTC/ETH/SOL 都恰好回溯到 210 天, 更早返回空数组)。**每过一天不落库, 就永久少一天可回测的小时历史。** 三个月后再想在自己交易的场所上回测, 那三个月已经拿不回来了。

`fundingHistory` 回溯 ~1171 天 (2023-05-11, 约 HL 主网上线), 暂无即刻风险, 但一并深回填。

**附带解决幸存者偏差**: 每天存一份 `metaAndAssetCtxs` 快照 ⇒ 从今天起自动积累 **point-in-time 名册** (上市/下架日期、24h 成交额、OI、funding)。以后所有 HL 分析都不必再 bisect 上市日期, `venue_feasibility.md` 里那条"名册幸存者偏差"会随时间自然关闭。

## 组件

| 文件 | 作用 | 节奏 |
|---|---|---|
| `pull_daily.py` | 增量拉 1h K 线 + funding + 当日名册快照 | 每日 08:00 UTC |
| `record_l2.py` | **websocket** L2 盘口录制, 每币每分钟 1 快照 | 常驻 (cron 每 30 min 用 flock 复活) |
| `run_daily.sh` | 编排 (`pull` / `l2` / `backfill` 三模式) | — |

## 存储布局 `exports/hl_archive/`

```
klines/<COIN>.npz     a = (N,7)  t,o,h,l,c,v,n     小时线, 去重+排序
funding/<COIN>.npz    a = (N,3)  time,rate,premium
roster/<YYYYMMDD>.json                              每日名册+成交额+OI+funding+impactPxs
l2/<YYYYMMDD>.npz     ts,coin,bid(M,10,2),ask(M,10,2),coins
_state.json                                         逐币 last-seen 时间戳 (断点续传)
logs/
```

## cron (已装, 与 live shadow 并存不冲突)

```
0 8  * * *   flock -n /tmp/hl_arch_pull.lock bash .../hl_archive/run_daily.sh pull
*/30 * * * * flock -n /tmp/hl_arch_l2.lock   bash .../hl_archive/run_daily.sh l2
```

- **`flock` 保证同一时刻只有一个实例**; L2 录制器 `--minutes 1440`, 健康时每 30 min 的 cron 是 no-op, 死了则 30 min 内自动复活。
- `pull` 带 `--max_seconds 5400` 时间预算 + **逐币落盘的断点续传**, 单次跑不完下次接着跑。
- 一次性深回填: `bash run_daily.sh backfill` (funding ~1171 天, 数小时; 2026-07-25 已跑)。

## 工程要点 (踩过的坑)

1. **短 timeout + 多重试。** 这台机到 HL 的路径**少数调用会 stall ~30s** (不是限速 —— 正常调用 0.4-2.2s)。25s timeout 会把 15 分钟的活拖成 6 小时。现用 **timeout=8s, 5 次重试**。
2. **限速**: HL `/info` 预算 1200 weight/min, 多数调用 weight 20 ⇒ 60 req/min。`PAUSE=0.9s` 留了余量。
3. **L2 用 websocket 不用 REST 轮询** —— 60 币 × 1440 次/天 = 40 req/min 会吃掉整个 `/info` 预算。
4. **L2 内存缓冲, 每 30 min 落一次盘。** 每分钟重写一个增长中的 npz ≈ 每天 20 GB 无谓 I/O; 缓冲一整天只占 ~14 MB。UTC 跨日先 flush 再切文件。
5. `websockets` 包**没装**, 装了 `websocket-client` 1.8.0 (`import websocket`) —— 用的是后者的 `WebSocketApp`, 带自动重连循环。

## 这些数据将来回答什么

- **`l2/` 是回答 "HL 上 maker 执行是否可行" 的唯一数据来源** —— 排队位置与逆选择无法从单张快照测出 (`venue_feasibility.md` 标为"最大剩余未知", `min_notional_band.md` 的 maker 表里那个待填的 X)。**只有先开始录, 日后才有可能关掉这个未知。**
- `roster/` 累积 point-in-time 名册 ⇒ 消除名册幸存者偏差。
- `klines/` + `funding/` ⇒ 在 HL 自己的价格上做回测与执行研究。

## 检查是否健康

```bash
ls -la exports/hl_archive/l2/ exports/hl_archive/roster/ | tail
python -c "import numpy as np,glob; z=np.load(sorted(glob.glob('exports/hl_archive/l2/*.npz'))[-1],allow_pickle=True); print({k:z[k].shape for k in z.files})"
tail exports/hl_archive/logs/*.log
```
