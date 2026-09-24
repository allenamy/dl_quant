> **创建:** 2026-09-24 13:2xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(B7 执行代理) | **状态:** 冻结 —— 写于本诊断任何数字之前 | **作废条件:** 生产 `beta_overlay_producer.py`(b77c180d)/ `nc_contract.py`(316a0b9b)或 08Z/12Z 快照被改写

# 诊断(非重判):B7 的逐名差是不是 combo_stage.py L403 读错收益通道造成的

**性质**:只读诊断。**不重判 B7**(B7 = UNDECIDED 已收下, 判据不改),不改任何生产文件,不调交易所,不占 GPU。
**来源**:协调者 2026-09-24 13:1xZ 的候选原因 —— `combo_stage.py` L403 调 `_BOP.compute(rts, RD[:, :, 0], ...)`,传的是 ch0(±0.30 裁剪、float16 存储的 5 分钟简单收益);同文件 L50 已算好 `RR = NC.rr_from_ch0(rts, RD[:, :, 0], _bnd["ts"], _bnd["col"], _bnd["raw"])`,是 NC 冻结合同要求所有消费者读的收益通道(界值格用原始值)。协调者指出 B7 的 >1% 名里 B2、TAKE 正是今天部署时补了原始收益的界值格的名。
**读法由协调者给定**(下文 §4 只是把「大幅减少」操作化,并补上装置自身的前提门;操作化是我的,协调者可否决)。

## 1. 输入(全部只读;逐个记 sha256)
- 生产快照:`~/wide_shadow/state/snap/<A>/rolling.npz`、`boundary_raw.npz`(A = 1790236800 / 1790251200),对照快照目录自带的 `SHA256SUMS` 校验;符号轴 `~/wide_shadow/fea171/xfer_syms.npz`(`symbols`,与 combo_stage 经 `capture_producer_inputs` 所读同一文件)。
- 生产代码:`beta_overlay_producer.py`(b77c180d…)与 `nc_contract.py`(316a0b9b…)**复制**进装置目录 `devices/prod_copy/` 后导入(不从 `~/wide_shadow` 导入, 以免写 `__pycache__`);运行时断言副本 sha == 在役文件 sha。
- 宇宙:B7 已提交的 `target_live/<A>.json` 副本的 `universe`(= `target_live_king/<A>.json` 的 universe, 已核相等)。
- 研究侧逐名 β:B7 已提交的 `B7_PER_NAME.csv`(`beta_res`, 研究侧 `m2_lib.betas_at` 从 4h K 线收盘价算得);研究侧 4h 对数收益从已提交的 `KLINES_RAW.jsonl.gz` 取 log(close_T / close_{T−4h})。
- 执行目标:B7 的 orders 副本(只读 `anchor_ts, symbol, target_w` 三键),按 B7 已通过 c1–c3 的同一重建法 t_i = target_w_i × book_gross_usdt;B7_PARITY.json 的记录值。

## 2. 前提门 P0(装置自证, 逐锚)
用快照的 ch0(`data[:, :, 0]`)原样调用生产 `compute(rts, ch0, symbols, universe, A)`,得到的 `betas` 必须与 `target_live` 副本里的生产字段**逐名逐位相等**,且按 `live/beta_overlay.py` 规则算的 betas_sha256 == 该锚执行器记录的 `betas_sha256`。**P0 不过的锚 = 该锚诊断 UNAVAILABLE**(快照不是 combo_stage 当时读的那一代, 或符号轴/宇宙不对),不估计、不替代。

## 3. 计算(逐锚)
1. `RR = NC.rr_from_ch0(rts, ch0, b.ts, b.col, b.raw)`;**非空转断言**:报 RR 与 float32(ch0) 在 β 窗(行 [A − 180×48, A], 共 8,641 行)内逐位不同的格数与名数;若为 0,则如实写「本锚 RR ≡ ch0,换通道对 β 无作用」(不是绿)。
2. `field_rr = compute(rts, RR, symbols, universe, A)`。
3. 第 (i) 层:逐名相对差 rel = |β_rr − β_res| / |β_res|(与 B7 第 (i) 层同式同类别:生产 n_obs ≥ 120 且研究侧已估计);报分位数、>1% 名数与名单;与 ch0 名单(= B7 名单)对照:移出/新增/保留。
4. 第 (ii) 层:β_exec_rr = Σ t_i · β_rr_i(BTC 取 1);报 rel_exec_rr = |β_exec_res − β_exec_rr| / |β_exec_rr|(与 B7 同式, 分母为生产侧);另报 β_exec_rr 与执行器记录值的差。**合池量**(盲态)。
5. 逐格差:对 ch0 名单(两锚并集)里每个名,列出窗内 RR 与 ch0 不同的每一格(收盘时刻、ch0 值、RR 值、差);另报全体名在窗内的不同格总数。
6. 剩余差归因(对 RR 下仍 >1% 的每个名, 描述性):
   (a) 有效条数:n_obs_rr 对 n_obs_res;
   (b) 把研究侧 β 限制在生产侧有效的 bar 上重算(同式 OLS,截距,研究侧收益)得 β_res|V:β_res|V − β_res = 「有效集不同」的份额,β_rr − β_res|V = 「收益值不同」的份额;
   (c) bar 级:|r4h_rr − r4h_res| > 1e-3 的 bar 数,以及其中含「|ch0| ≥ 0.2997 且未被 RR 覆盖」(裁剪格)的 bar 数、含界值表格的 bar 数、两者都不含的 bar 数(= 数据内容差或 float16 累积)。
   另报第 (ii) 层 RR 缺口中来自这些名的合池份额。

## 4. 读法(写死)
- **支持「L403 读错通道」** ⇔ 在 P0 通过的**两个**锚上同时满足:(A) RR 下 >1% 名数 ≤ ⌊ch0 下名数 / 2⌋(「大幅减少」的操作化:至少去掉一半);(B) rel_exec_rr < 0.01。
- 否则写「**不支持为唯一原因**」,并按 §3-6 写明剩下的差来自哪里;若 (A)(B) 只满足其一或只在一锚满足,原样报出是哪一条、哪一锚。
- 任一锚 P0 不过 ⇒ 该锚 UNAVAILABLE;两锚都不过 ⇒ 诊断整体 UNAVAILABLE。
- 本诊断的任何结果都不改变 B7 的判词,也不构成对生产代码的修改建议之外的任何动作;是否改 L403 由协调者/用户定。

## 5. 装置与复跑
`multi_asset/exports/research/m3_shadow_b7_2026-09-24/devices/b7_diag_rr_channel.py`(本文件同一提交);输出 `receipts/diag_rr_2026-09-24/B7_DIAG_RR.json` + `B7_DIAG_RR_per_name.csv` + `B7_DIAG_RR_cells.csv`;判词行 `B7_DIAG_RR READING=…`。本机轻活,在 12Z 锚后的静默窗内跑(启动先调 `venue_quiet_window.py` 自检)。
