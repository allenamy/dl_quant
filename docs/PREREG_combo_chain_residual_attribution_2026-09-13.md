> **创建:** 2026-09-13 15:4xZ | **Session:** P2 worker「p2-oos-replay」(lead 派: P2 = 主纲领关键修复, 用户 14:1xZ 裁定) | **状态:** 预注册(判据与装置先于任何本题数字) | **作废条件:** 生产 `combo_stage.py` / `dlw_features.py` / `f8_higher_order_features.py` 换代; Phase 1 驱动换代; 本文 AMENDMENT 记录任何修订

# PREREG — 连续 combo 历史链残差(G-P2)归因与认证

## §0 问题与已知事实(均引收据, 本题开始前已存在)
- **缺陷**: Phase 1 链式回放(09-05 16Z → 09-12 08Z, 41 锚)combo 段 `target_live` / `target_combo` **0/41 ≤ 1e-6**, 最大 **1.12547e-4**(`parity_replay_2026-09-12/receipts/PARITY_phase1_chain_full_1788624000_1789200000.json`; G2-C 在 pod2 以拼接缓存逐锚逐位复现同一残差, `phase2/receipts/G2C_verdict.json`)。king 段 41/41 ≤ 9.3e-10; 快照起步 3/3 精确 0.0(Phase 1 AMENDMENT 3; G2-C; G2-C-BIND PASS)。
- **Phase 1 RESULT §3 已排除**: (a) EMA 逆推误差; (b) 线上 combo/DL 状态不连续; (c) 陈旧中间件; (d) 缓存视图**末端**未截断(已按 ≤A 截断); (e) 基名单差。**观察**: 残差只在 DL 腿(kc 状态 L∞ 0.0, f10/fc 有差); 首锚 f10 书差 2.5e-4(ENSOUSDT), ρ(f10,king) 回放 0.1621 vs 线上 0.1619; 越近的锚越一致, 最新锚精确。
- **Phase 1 AMENDMENT 3(含研究员 563e3470 措辞更正)**: 三对快照回填探针全 0(08Z→12Z / 12Z→16Z / 16Z→20Z, 11,472 行 × 829 名 × 7 通道: 回填 / 丢失 / 改写均 0); 未排除「(i) 09-05→09-11 窗内回填/改写; (ii) 当前 rolling **左边界**与旧锚不同、mini 特征历史长度、辅助文件代际; (iii) 每锚重设快照会切断累积误差」。
- **读码事实(本题开始前读, 非数字)**: 生产 combo 段(`combo_stage_replay.py` f5ba9a82… = 生产 b5c698f9… + 3 处替换)每锚在 `need` 分支里「**全尾**」重跑 171 管线: L124 `e_rows` = 缓存里**全部** 4h 锚行(i ≥ 48), L129 把**整个**缓存写成 `mini/cache.npz`, L130–133 目标文件覆盖全尾, L151–153 在全尾上跑 `dlw_features.py` 与 `f8_higher_order_features.build()`; L52–78 `_btcv_series` 是 2016 根滚动 std, 「早期不足 7 天的行: 显式回填首个满窗值(近似, 只影响 causal_z 的早期统计)」(L65)。生产者每锚的 `state/rolling.npz` 恰为 **11,520 行、以 A 结尾**(Phase 1 §1)。Phase 1 链用的是 09-12 08Z 的那一份 11,520 行文件(首行 08-03 08:05Z)再按 ≤A 截断 ⇒ 链首锚 09-05 16Z 的缓存**左边界晚 1,920 行**(生产首行应为 07-27 16:05Z), 之后每锚少 48 行, 末锚 09-12 08Z 缺口为 0。生产 `fea171/` 辅助件 mtime(只读查看): `dlw_features.py` / `f8_higher_order_features.py` / `ref_fea89.npz` 08-24, `f10_live_s42_np.npz` 09-01 08:42Z, `combo_stage.py` 09-02 —— 均早于 09-05 16Z; `xfer_panel_live.npz` 每锚由 aux 重建。Phase 1 链模式首锚已从生产者自己的 `state_H_{f10,kc,fc}_{A−4h}` 与 `weights/{A−4h}` 复制起步(`replay_driver.py` f2ced820… `run_combo_stage` first 分支)。

## §1 假说(先于数字写定)
- **H-d 左边界 / 全尾长度(主候选)**: 171 管线的全尾因果统计(因果 z、滚动窗首满窗回填等)依赖缓存首行; 链回放喂给早锚的缓存比生产短 1,920 → 0 行 ⇒ DL 腿分数有小差, king 段(只用 ≤40 日内固定窗)不受影响。**预测**: 快照锚上把缓存头部删 K 行会产生只在 DL 腿的残差(kc 状态 0.0), 删 0 行精确; 用逐锚「11,520 行以 A 结尾」的滑窗重跑整链, 残差消失。
- **H-a 数据代际(lead 指示)**: 行 ≤ A 的 5m 数据在 A 之后被回填或改写, 链回放用的晚代际缓存 ≠ F10 当时的输入。4h 尺度已测 0(§0); 多日尺度未测。**预测(若 H-a 是主因)**: 即使滑窗长度对了、但行值取自晚代际, 残差仍在。
- **H-b 起点状态(lead 指示)**: 链首锚的 combo 状态 ≠ 生产者当时的状态。**读码已知**首锚复制生产者自己的 state_H 文件; 预测: 首锚 f10 书差在「H_f10_prev 逐位相同」时仍出现 ⇒ 起点状态不是首锚残差的来源。
- **H-c F10 截面输入(lead 指示)**: 截面特征用到的名单(早期行里的非在役名、死合约冻结行 TRD-01)在回放与生产之间不同, 或死名进入 F10 截面。已知: G2-C 链把 ≤09-01 行里非在役名置 NaN(与生产 rolling 的 NaN 支撑差 5,560,280 格), 残差仍与 Phase 1 **逐位相同** ⇒ 非在役名 NaN 模式在该窗内不影响输出(读收据, 非新数字)。本题另测死名是否触及 F10 截面。
- **H-e 辅助件代际**: 管线辅助文件在 09-05 与回放时不同。读码 + mtime 已排除(§0), 本题只列不测。

## §2 装置(全部运行前提交; pod2 CPU; 只读生产与既有收据; 只写 `/workspace/uplift_r2_2026-09-13/P2/work/attr_*` 与 `P2/receipts/ATTR_*`)
- **Stage B 静态核对** `phase2/devices/p2_attr_stageB.py`: (1) Phase 1 链收据与 G2-C 链收据的每锚 combo 状态来源 `kc_state_source/fc_state_source` 均为 own、首锚 H_f10_prev 所用文件 sha = 生产者文件 sha(H-b 读码事实的收据化); (2) 三份回填探针收据全 0 的复读; (3) Phase 1 链 41 锚的左边界缺口行数表(1,920 − 48k); (4) 41 锚上在役名中「(A−24h, A] 内 5m 成交笔数(log_cnt 通道)全非正或全 NaN」的死名数(用生产者快照 1789200000 的 rolling 与 G2-C 链的长缓存), 其中出现在生产者该锚 `target_live` 权重名单里的数; 三个快照锚上另报死名 ∩ 该锚 king 成员(快照 aux `prev_rec.members`)数(描述量, 无门)。
- **Stage C 快照锚干预** `phase2/devices/p2_attr_stageC.py`: 以 G2-C 的三棵快照树(s12 / s16 / s20, 基线 0.0)为模板, 每个变体建一棵新树, 只替换假 HOME 的 `state/rolling.npz`, 用逐字节 Phase 1 驱动 f2ced820… 快照模式(`REPLAY_COMBO=1`)跑一锚:
  - **V0 正控**: 不改(必须复现 0.0);
  - **V1-K**(H-d): 删去缓存头部 K ∈ {48, 288, 960, 1920} 行(其余逐位不变);
  - **V2**(H-c 死名): 在 V0 缓存上把该锚「(A−24h, A] 内 log_cnt 全非正或全 NaN」的在役名整列置 NaN(描述性: 死名是否触及 F10 截面)。
  - 每变体报: king `weights` L∞、`target_combo` L∞、`target_live` L∞、回放 vs 生产 `state_H_{f10,kc,fc}_A` L∞(生产文件有者)、差 > 1e-6 的名数。
- **Stage D 滑窗链认证** `phase2/devices/p2_attr_chain_asof.py`: 新树 = G2-C 链树 + 一份「长源缓存」(07-27 16:05Z → 09-12 08:00Z 共 13,440 行: ≤ 09-01 00:00Z 取 holefix2 且非在役名置 NaN, 同 G2-C 规则; 之后取生产者快照 1789200000 的 rolling 行)。包装器按模块导入逐字节 Phase 1 驱动(不改一字), 仅在每锚调用原 `run_combo_stage` 之前把回放 `state/rolling.npz` 的符号链接改指向「以 A 结尾的 11,520 行滑窗」文件(单文件逐锚覆写, 134 MB, 无多 GB 写入); king 段读长源缓存(其内部自截 11,520 行)。两种模式各跑整条 41 锚链:
  - **D-id(装置同一性 / 红能力)**: 滑窗改为 Phase 1 几何(以 09-12 08Z 结尾的 11,520 行文件再按 ≤A 截断)⇒ 必须**逐锚逐位**复现 G2-C 链收据的 `weights_npz_Linf` / `target_combo_Linf` / `target_live_Linf`(0/41, 最大 1.12547e-4);
  - **D-asof**: 逐锚 11,520 行以 A 结尾。
  - 另报逐锚回放 vs 生产 `state_H_{f10,kc,fc}_A`(生产者 `~/wide_shadow/fea171/` 110 个 kc 文件等的只读副本, 复制前后 sha 记录)。

## §3 判据(冻结; 红即停; 阈值不改)
- **Stage C — H-d 机制判定**: CONFIRMED ⇔ (C0) V0 在 3/3 锚 `target_live` 与 `target_combo` L∞ = 0.0 且 king L∞ = 0.0; 且 (C1) V1-1920 在 ≥ 2/3 锚 `target_live` L∞ > 1e-6, 且这些锚上 kc 状态 L∞ = 0.0(生产文件可得时)。否则 NOT CONFIRMED(照报, Stage D 仍跑但不作「修复」解释)。K 的单调性只描述。V0 若不为 0.0 ⇒ 装置/树不可信, **停**。
- **Stage D — G2-C-ASOF 认证门**: (D-id) 逐锚逐位复现 G2-C 链收据, 否则**停**(包装器不可信); (D-asof) 41/41 锚 `target_live` L∞ ≤ 1e-6 **且** 41/41 `target_combo` L∞ ≤ 1e-6 **且** king `weights` L∞ ≤ 1e-6(原 G-P2 / G-P1 阈值)⇒ **PASS**: 「连续 combo 历史链在逐锚 as-of 缓存窗下与生产逐锚一致」; 残差归因 = 回放输入的缓存左边界缺陷(装置缺陷)。任一不满足 ⇒ RED, 逐锚列残差, 不认证。
- **H-a 读法**: D-asof PASS 时, 该 41 锚窗内「多日回填/改写」对 combo 输出无可测影响(行值取晚代际而输出逐锚一致)。D-asof RED 时 H-a 与其它未排除项并列未决。
- **H-b 读法**: Stage B(1) 若首锚所用 H_f10_prev 文件 sha = 生产者文件 sha 而首锚 f10 书仍有差 ⇒ 起点状态被排除为首锚残差来源; D-asof PASS 则 H-b 整链排除。
- **H-c 读法**: V2 各锚 L∞ = 0.0 ⇒ 死名不触及 F10 截面(该锚); > 0 ⇒ 触及, 报名数与 L∞, 纳入认证回放的 tradability 消费范围(FX-DATA 模块)。
- **不改写**: Phase 1 G-P2 FAIL 与 G2-C 历史链描述照原记录保留; 本题的新门只做**增补**。认证范围写明: ≤ 08-03 08:05Z 的行取自 holefix2, 与生产行的逐位相等只在 08-03→09-01 由 G2-A 验过; 更早行未经生产文件对照(D-asof PASS 只说明其对输出无可测影响)。

## §4 后果(预写)
- **若装置缺陷(H-d CONFIRMED 且 D-asof PASS)**: 修复 = 回放驱动在链模式逐锚提供「11,520 行以 A 结尾」的缓存; 以修复后的装置重跑 Phase 1 链等价物(即 D-asof)即认证; G2-C 链标签新增「G2-C-ASOF PASS」一行, 原 0/41 行保留。P2 S2 的 combo 段在 I2 注入下跳过 171 管线(A2.1 I2 / D7: 只读末 2016 行 qv4h 与 ai)⇒ 另写一行说明 H-d 不作用于 S2 的 F10 分数路径, 并以 S2 链日志核对管线跳过的锚数。
- **若参考侧伪迹**: 以正控(as-of 输入逐锚精确)证明, 写认证门绑定该条件, 未认证部分的范围具名。
- **若都不是**: 照报, 标签不变, 列下一步。

## §5 不主张
不主张任何书行为改动; 不注销任何既有 FAIL / RED; 不把快照锚上的精确推广为整链精确(Stage D 才判)。

## AMENDMENT 1 — 2026-09-13 15:5xZ(先于任何本题数字; 只补装置细节, 判据 §3 一字不改)
- **A1.1 生产者 state_H 来源**: G2-C 树只带 4 个锚的生产者 state_H(s20 的 A = 1789243200 没有)。改为: 本机只读复制 `~/wide_shadow/fea171/state_H_{f10,kc,fc}_<A>.npz` 全部逐锚文件(装置 `phase2/devices/p2_attr_prod_stateH_copy.py`: 复制前后各按 t6_sha_guard 规则哈希一次、暂存副本再哈希一次, 三者须相等; 清单 `phase2/receipts/ATTR_prod_stateH_{SHA256SUMS.txt,manifest.json}`), 送 pod2 `P2/work/live_ro/prod_stateH_attr/`; Stage C / D 每次使用前按清单验 sha。
- **A1.2 死名规则逐字化**: log_cnt = 通道 4(`['ret5','range','cpos','log_qv','log_cnt','log_avgsz','tbf']`)= log1p(成交笔数)。死名 ⇔ (A−24h, A] 的 288 根 5m 里**没有**一根 log_cnt 有限且 > 0(NaN 与 0 混合也算死)。§2「全非正或全 NaN」按此读, 与 FX-DATA 可交易性规则「≥1 根成交笔数 > 0」互为否定。
- **A1.3 运行环境**: G2-C 快照运行只记了「pod2 CPU 8 核 taskset」, 线程环境未逐字记录 ⇒ 按冻结 §3, V0 正控是唯一保证。Stage C 三锚各一条车道并行, 每道 `taskset -c {0-7 | 8-15 | 16-23} nice -n 10`, 驱动环境 = `PATH=/usr/bin:/bin`、`HOME=<变体树>/home`、`REPLAY_COMBO=1`、`REPLAY_RECEIPT_TAG=ATTR_<变体>`, 逐字写进收据。
- **A1.4 绑定**: V0 的 rolling 逐字节复制 G2-C 树文件(sha 须 = `G2C_prep.json` 的 hybrid_sha256); 每个变体的驱动收据 `rolling_sha256` 须 = 该变体文件 sha, 否则该变体记失败(V0 失败 ⇒ 停)。
- **A1.5 中间件清理**: 每个变体跑完、sha 入收据后删除变体 rolling.npz、`replay_home/fea171/mini/` 与两份 ref_fea89.npz 副本(避免累计多 GB 写入); 驱动收据、日志、state_H 输出与目标文件保留。
- **A1.6 描述量增补(无门)**: Stage C 另报 target_live 差最大的 5 个名、V2 死名中在生产者该锚 target_live 与 aux `prev_rec.members` 中的名数。
