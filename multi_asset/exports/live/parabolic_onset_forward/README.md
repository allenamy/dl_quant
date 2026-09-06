> **创建:** 2026-09-06 06:2xZ | **Session:** b9646a9e(track-a-newinfo) | **状态:** 前向只读日志(零接触; 生产者与执行器文件只读, 不调 API) | **预注册:** PREREG_crash_continuation_parabolic_stratum_2026-09-06 commit 26aeb23 §2(复判六条); 受据 RESULT_crash_risk_long_end §Phase 2b/2c(c1a061f, UNDECIDED 5/6) | **作废条件:** 触碰实盘; 复判规则在看前向数字后被改

# parabolic_onset_forward — 抛物线名锚内崩跌起始的前向离线日志

**脚本**: `multi_asset/exports/live/pilot_journal/tools/parabolic_onset_forward_log.py`(研究仓)。只读 `~/wide_shadow/state/rolling.npz`(生产者 5m 缓存: ts = bar 收盘时刻, 5 分钟网格, 40 日尾; data (T, 829, 7) f16, 通道 [ret5, rng, cpos, lqv, lcnt, lasz, tbf], 与 pod ext 缓存同式, 运行时断言)、`~/wide_shadow/shadow_bundle/config.json`(symbols_panel, params.cap_mult)与 `~/wide_shadow/state/target_live_king/<A>.json`(king 形态目标权重, Σ|w| = gross_norm, n_names)。**不写 ~/wide_shadow 与 ~/dl_quant_live 的任何文件, 不调任何 API**; 只追加本目录 `events.jsonl` 与 `run_log.jsonl`。

**每次运行**处理所有"已完整过去且未记录"的锚区间 [A, A+4h](缓存需覆盖 E−863..E+48 行): 队列 = 该锚书多头名 w_norm ≥ 0.5·capw(w_norm = w/Σ|w|, capw = cap_mult/n_names); **fund_ema 前 15% 未纳入**(状态文件只有最新一锚的 EMA, 过去锚不可重建), 每条记录 `cohort_def = "book_long_only"`; P 层 = 锚前 864 行 3 日涨幅 ≥ +20%(≥ 80% 有限 bar, 否则 U), Q = 其余; 起始 = 锚内首次累计 ≤ −θ(θ 5/8/12%), 镜像上涨(≥ +θ)作对照; 前向 r(τ→1h/3h/下一锚/12h) 含首根(`fwd_incl`)与 τ+5m 起(`fwd_delay5m`, 主); 缓存未覆盖处为 null, 之后的运行以 `{"update": true, id, …}` 记录补齐(读者取每个 id 的最新记录); `value_bps = −r(τ+5m→下一锚)·1e4 − 8.9`; `w_raw`(目标文件权重)与 `w_norm`。

**记录类型**: `anchor`(每锚一条: n_cohort, n_P/n_Q/n_U, capw, target_sha, booster_sha)、`onset`、`mirror`(id = `<anchor>:<symbol>:theta<θ>:<type>`)、以及 `update`。`run_log.jsonl` 每次运行一行: 缓存 sha 与范围、新增锚/事件数、2026-09+ 累计摘要(P/Q/mirror_P 事件数、已填 r(τ+5m→下一锚) 的均值)。

**复判规则(冻结, 由 lead 执行, 脚本只记录)**: 累计 ≥ 14 个日历日且 P 层 θ=8% 已填事件 ≥ 200 后, 对 2026-09+ 样本按 PREREG_crash_continuation_parabolic_stratum §2 六条逐字复判: 确认 = P 层 r(τ+5m→下一锚) CI95 上界 < 0(UTC 日块 bootstrap 2000, 种子 20260905)且 θ5/θ12 同号且镜像安慰剂不为负且 P − Q 差 CI 上界 < 0 且价值上界 ≥ +0.03 bps/锚/gross(CI 下界 > 0); 否决 = P 层 CI 下界 > −15 或镜像显著为负; 其余 UNDECIDED。

**恒等收据(VERIFIED, pod `crash_risk/results/forward_identity.json`, 脚本 `crash_forward_identity.py` sha 2f056abe; 生产者缓存副本 sha df21dec6 = 本机 rolling.npz 09-06 04:00Z 版)**: 生产者缓存与 pod ext 缓存在 2026-07-28 04:05 → 09-01 00:00 重叠行、829 名(符号顺序相等)上七通道全部 **max|Δ| 0.0, 不等格占比 0.0**(5.97M 格); 生产者只拉 symbols_live(450), 其余 379 名在生产者缓存为 NaN(ret5 684,864 格)。同一起始检测代码 + pod Phase 0 队列掩码在两缓存的重叠锚上: θ=8% 事件 543(生产者)vs 545(pod), 差 2 个全是生产者 NaN 名, 匹配事件 r(τ+5m→下一锚) max|Δ| 0.0, 均值 12.25 vs 12.81 bps; θ5 1,214 vs 1,219(差 5), θ12 250 vs 251(差 1); pod 存档 θ8 事件表 = 现算逐位相等。**pod 事件研究到 2026-08-30 20:00 为止, 与本日志的 2026-09 区间无重叠**, 故 09-01→09-05 无 pod 对照; 以上是数据与代码两层的恒等。

**回填(2026-09-01 00:00 → 09-06 00:00, 31 锚, 运行 06:20:51Z, 缓存 sha df21dec6)**: 队列 43.8 名/锚(书多头), P 4.3 名/锚; 事件 θ5 P 45 / Q 95 / 镜像 168, **θ8 P 26 / Q 38 / 镜像 91**, θ12 P 13 / Q 19 / 镜像 54; θ8 延迟 5m r(τ→下一锚) 均值 **P −205.8 bps(26/26 已填)**, Q −54.2(37/38), P 层镜像 +204.2(30/32); θ12 P −575.2(13), Q −42.3(19); θ5 P 见 run_log。样本极小(2 周内含 09-05/06 的回吐周), 只作累计起点, 不作判读。
