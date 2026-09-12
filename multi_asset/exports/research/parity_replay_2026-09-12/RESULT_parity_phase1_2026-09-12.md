> **创建:** 2026-09-12 10:5xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** Phase 1 判决(按 PREREG_producer_parity_replay_2026-09-12 + AMENDMENT 1/2 冻结判据); 全部数字来自 `receipts/PARITY_phase1_chain_full_1788624000_1789200000.json` 与 `receipts/PARITY_GP4_alpha011_*.json` | **作废条件:** 生产代码换代; 12Z 快照起步测试更新 G-P2/G-P3 前向读数

# RESULT · 生产者平价回放 Phase 1 — 装置 = 线上吗?

## §0 一句话
**king 段(`shadow_loop_v3.py` 全路径): 是 —— 41/41 锚, 权重 L∞ ≤ 9.3e-10, 席位用的 40 条腿收益条目逐位相同(差 0.0), w3 / 成员 / 流动性门 / fund_updates 逐锚相同; 红能力控(α 0.1→0.11)三锚全红。combo 段(`combo_stage.py`): 从 09-11 20Z 线上状态起步 3/3 锚精确 0.0; 但从 09-05 16Z 起用逆推状态链式跑 41 锚, DL 腿(F10)排名有 ≤3e-4 的 ρ 差, 使 combo 目标在 14 个名字上出现 ≤1.13e-4 的持久残差(中位 1.05e-5)⇒ G-P2 按字面 FAIL(0/41 ≤1e-6), 机理未闭合; G-P3(内容 sha)0/41 = 持仓 float32 存档精度上限。** 12Z 起改用锚收尾 float64 快照起步评判 G-P2/G-P3。

## §1 装置(全部只读生产文件, 零字节改动)
| 件 | 生产 sha256(前 16) | 装置 sha256(前 16) | 替换 |
|---|---|---|---|
| `shadow_loop_v3.py` → `shadow_loop_v3_replay.py` | e9c9837412130884 | 4d3bc157f03e3462 | 2 处(klines 步 → 缓存行; TAIL_SCORE False)+ 生成的 ReplayFetcher(exchangeInfo 记录基名单 / fundingRate 记录账本; 其它路径拒绝) |
| `fea171/combo_stage.py` → `combo_stage_replay.py` | b5c698f9d1ee9acb | f5ba9a8234ef0c01 | 3 处(WS 根从 env; Telegram 分页压制; `REPLAY_TRUNCATE_CACHE=1` 时缓存视图截到 ≤A) |
| 驱动 `replay_driver.py` | — | 见 SHA256SUMS | 状态重建: H = `weights/{A−4h}.npz`; EMA 由当前状态沿账本**逆推**(roundtrip 最大 4.8e-18); 账本截到 ≤A−4h, 桩服务 (A−4h, A]; LR = bundle + `leg_returns_live` 截到本锚 step 7 时刻; 基名单 = 最新(与 signal 行 base_n 核对); 链式模式携带 float64 状态, step 6 由回放自己算 |
bundle = 线上 `shadow_bundle/`(MANIFEST 校验); 缓存 = 线上 `rolling.npz`(11,520 行); 解释器 = 生产者 venv(python 3.14.4, lightgbm 4.7.0, numpy 2.5.2)。

## §2 门读数
| 门 | 定义 | 读数 | 判 |
|---|---|---|---|
| **G-P1** king 段 | 每锚 `weights/{A}.npz` 逐名 L∞ ≤ 1e-6, 通过率 ≥95% | **41/41**, 最大 **9.31e-10**; 附: w3 / members / sel / fund_updates 41/41 相同; 回放 step 6 生成的 LR 条目与线上 `leg_returns_live.json` **40/40 差 0.0** | **PASS** |
| **G-P2** combo 段 | `target_combo` 与 `target_live`(combo 覆写)逐名 L∞ ≤ 1e-6, ≥95% | 链式 09-05 16Z 起: **0/41**; 残差逐锚(e-6): 1.9×3, 1.7×7, **113→101(09-07 08Z–09-08 04Z, POLUSDT)**, 16→7.7 单调衰减; 只 **14 个名字**曾 >1e-6; w3m 41/41 相同, FTRIM 名数 41/41 相同, rc 41/41 = 0。从 09-11 20Z 线上状态起步(非逆推): **3/3 锚 0.0** | **FAIL(按字面)**; 机理见 §3 |
| **G-P3** 内容 sha(AMENDMENT 1) | `idx`/`val` 数组 sha 相等锚数 = G-P1 通过数 | **0/41**; 每锚 ≤51 名差 1 个 float32 ulp(4.7e-10) | **FAIL**; 机理 = 线上把 H 以 float32 存档, 回放从存档起步 ⇒ 与线上内存 float64 差 ≤2⁻²⁴ 相对(AMENDMENT 2) |
| **G-P4** 红能力 | α 0.1→0.11 三锚必红 | L∞ 2.72e-4 / 2.74e-4 / 2.67e-4 | **PASS** |

## §3 G-P2 残差的机理排查(已做 / 未闭合)
- 排除: (a) EMA 逆推误差(roundtrip 4.8e-18; 09-07 08Z 跳变锚上无不可逆推名); (b) 线上 combo/DL 状态不连续(41 锚 kc/fc/h_source 全 own); (c) DL 管线复用陈旧中间件(`mini/results` 只存报告; 每锚清 `mini/data` 重算); (d) 缓存视图未截断(已按 ≤A 截断, 否则 `fe[-1]` 落在错误行 —— 修正前残差 2.8e-4, 修正后 1.9e-6); (e) 基名单差(09-05 16Z–09-06 04Z 线上 528 vs 回放 530, 但 king 段仍 1e-9 相同 ⇒ 差的两名无新鲜结算)。
- 观察: 残差**只在 DL 腿**(kc 状态 41 锚 L∞ 0.0; f10/fc 状态有差), 首锚 09-05 16Z 的 f10 书差 2.5e-4(ENSOUSDT), ρ(f10,king) 回放 0.1621 vs 线上 0.1619; 越近的锚 ρ 越一致, 最新锚精确。
- 未闭合的唯一假说: **缓存 5m 行的事后回填**(生产者「只填 NaN 行」: 时刻 A 缺的 bar 被后续锚的重叠抓取补上)—— 只影响 DL 横截面特征(fea82/fea89 用全部 live 名), 不影响 king(成员窗口, 1e-9 同)。**可直接测**: 今日 08Z 快照 `rolling.npz` vs 12Z 快照, 数行 ≤08Z 上「08Z 为 NaN、12Z 有限」的格。12Z 锚后做, 结果进 AMENDMENT 3。
- 经济含义(只报不判): 残差中位 1.05e-5 ≈ 典型权重 3e-3 的 0.35%, 14/265 名; 不影响任何已发表判决, 但**门是 1e-6, 不改门**。

## §4 结论与前向
1. **king 段装置可用**: 任何只改 `shadow_loop_v3` 路径(席位规则、平滑 α/带、FTRIM 前置、宇宙门)的候选, 可在此装置上做"线上路径"回放; 结论标"生产者平价 king 段 ≤1e-9"。
2. **combo 段**: 从锚收尾 float64 快照起步(`producer_state_snapshots/<anchor>/`, 首份 08Z 已落, 之后每锚落)评判 G-P2/G-P3; 历史窗(09-05→09-12)按字面 FAIL, 机理待 12Z 测量。
3. Phase 2(折外历史水平)预注册已立(`docs/PREREG_producer_parity_phase2_oos_2026-09-12.md`); G2-A 通道平价已 PASS(生产者缓存 vs pod 正典缓存 8,256 时刻 × 829 × 7 逐位相等)。
4. 独立研究员复核请求: (i) G-P2 残差机理的替代假说; (ii) 逆推 EMA 的可接受性; (iii) 是否应把 G-P2 的门定义在"快照起步"而非"逆推起步"(我方认为应分列, 不改门)。
