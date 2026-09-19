> **创建:** 2026-09-19 | **Session:** session_01KW6frfphbFmFzx7wUtGhLb(流 D 数据轴代理) | **状态:** 研究数据层已延到 5m bar 收盘 2026-09-19T00:00Z(新根 pod2 `/workspace/axis_0919/`, 全部组件已建并逐项过前缀恒等证明); 交 lead / 复审 | **作废条件:** 任一组件按 §8 复跑命令逐字复跑后 sha256 不同; 或 §3 任一前缀证明在同输入上复算出非零差; 或场所改写了 2026-09-11..09-18 的日档(`.CHECKSUM` 变化)

# 研究数据层延伸到 2026-09-19T00:00Z(axis_0919, 纲领 §2 流 D)

纲领: `docs/PROGRAM_credible_replay_regime_optimization_2026-09-19.md` §2 流 D。普查: `docs/READINESS_october_v4_chain_2026-09-19.md`。口径钉: `multi_asset/exports/research/uplift_2026-09-11/CALIBER_PIN_v4_2026-09-11.md`(记账 = RAW Π(1+r)−1, 禁用缓存 ret5 重算收益)。
装置与收据(git): `multi_asset/exports/research/axis_0919_2026-09-19/`(`devices/` 本轮装置 + 打过补丁的构建器副本, `receipts/` 两个 diff 与装置 sha 清单)。pod 上的收据、日志、峰值文件按 pod 相对路径原样镜像在 `receipts/pod2/`: 下文写 `receipts/X.json` 即 `receipts/pod2/receipts/X.json`, `logs/…` 即 `receipts/pod2/logs/…`。收据里记录的每个装置 self_sha256 都与 git 中同名文件相等(21 份收据逐一核对)。数据数组(npz/npy)只在 pod 上。

## 0. 结论(白话)

1. **轴**: 缓存末行 = 2026-09-19T00:00Z 收盘的 5m bar ⇒ 锚 2026-09-18T20:00Z 的 4h 标签完整。DL 目标(RAW 与 CLIP)、king 特征、记账元的锚轴都是 **10,319 个锚, 2022-01-03T00:00Z → 2026-09-18T20:00Z**; 格点应有 10,320 个, **唯一缺的是 2026-09-01T00:00Z**(普查 B3 的预言: 08-31 整天 798 名×288 行是 holefix 补洞, 判活规则不认补洞 bar ⇒ 该锚 24h 窗内无活名 ⇒ 成员 < 50 ⇒ 构建器丢锚)。按仅追加规则(TRN-16)不替换补洞行, 所以这个缺口是**规则的后果, 不是缺数据**; 真实 08-31 日档现在存在(r6 X2-B 已比过), 要不要回填需裁定。
2. **仅追加**: 每个延长的数组在与来源重叠的部分**逐位相同**(缓存对 holefix2 正典 28.5 亿格、对 x0910 28.6 亿格, 差 0; 面板前缀 21 个键全等; 可交易性、两种成员掩码、RAW/CLIP 目标、fea82、fea89、king 特征对最近的同构建器参照逐格对比)。所有非零差都**具名并逐格归因**(§3), 没有一格"未解释"。
3. **资金费区间**: 新账本不用任何取数时刻的 `fundingInfo` 区间; 98,087 次结算里 98,066 次由相邻结算时间差得出, 与在役生产者账本 82,728 次、T5d 账本 46,311 次**逐次相同**(0 不一致)。r6 x0910 的区间缺陷(547 格 / 23 名)在新面板里消失, 差异格数与记忆里的缺陷记录逐数吻合。
4. **两处需要注意的既有性质(不是本轮引入的)**: ① `pod_panel_ext.py` 的 v1 面板自检在所有 holefix 谱系缓存上都读 `f_amihud_24h` Pearson 0.0546 并 rc 3(r6 已诊断), 本轮读数与 r6 **逐行相同**, 门未改; ② 面板 `f_fund_ema_v2` 的 span = 整段尾部结算区间的中位数, **数据延长会改动更早尾部锚的 v2 值**(10 个名, 逐格证明)。v2 不进本轮任何构建器, 但下游若用 v2 需知道它不是追加稳定的。

## 1. 新根与组件

全部产物在 pod2 `/workspace/axis_0919/`(新目录; 未写任何既有路径)。演练目录 `rehearsal_0917/`(首次演练在奇偶校验窗参数处 FAIL, 见 §6)、`rehearsal_0917b/`(09-11..09-17 全链演练)保留作证据, 不是交付物。

| # | 组件 | 路径(相对 `/workspace/axis_0919/`) | sha256 | 首 / 末时间戳 | 形状 |
|---|---|---|---|---|---|
| 1 | 5m 缓存(holefix2 正典 + r6 x0910 + 本轮追加) | `data/dlnative_5m_wide829_f16_holefix2_x0918.npz` | `1db49ce6f5ca3431e99ce5abb630b296d2effbb130dfe17974d2b5319f926d2e` | 2022-01-01T00:00Z / **2026-09-19T00:00Z** | data (495,937, 829, 7) f16 |
| 1b | RAW 补丁(E-0908-B) + manifest | `data/raw_patch.npz` / `data/raw_patch.manifest.json` | `0a4cfb5988ae8679…` / `9b1cec6d385394d7…` | 补丁行 2022-05-11 … 2026-09-16 02:30Z | 959 行 |
| 1c | 补洞格(holefix2_cells 原样拷贝, 几何不变) | `inputs/holefix2_cells.npz` | `6156f97a0709f073…`(= 源) | 行 ≤ 2026-09-01T00:00Z | 1,422,720 格 |
| 2 | 资金费结算账本 | `funding/funding_ledger.npz` | `74b69e635efbf3556fe706520fda9d5a1b5cda86dda9d04a844ba5d617a3a09d` | 2026-08-21T00:00Z / **2026-09-19T00:00Z** | 98,087 次结算, 679 名 |
| 2b | 4h 记账资金费表 | `funding/funding_4h_accounting.npz` | `2838e5f6cf42fff5619460f64708d952cd56e23e6621195d8e3d8bd5466aca72` | 2026-08-21T00Z / 2026-09-19T00Z | 175 锚 × 829 |
| 3a | 原始面板(pod_panel_ext 输出) | `panels/wide_panel_4h_rawbuild_x0918.npz` | `fe4c77c19a59757771149aa26ae1c1feb3d89284f7d0b61c298e99fa83270f67` | 2022-01-31 / 2026-09-18T00:00Z | 10,147 锚 |
| 3b | v2ext 型面板(king 用) | `panels/wide_panel_4h_v2ext_x0918.npz` | `e5fcb4198ddebb52fe6e92438c5111ed22f41dbacbd9ec9af459c9ac6c40b47c` | 2022-01-31 / 2026-09-18T00:00Z | 10,147 锚(前缀 10,039 + 尾 108) |
| 3c | v3splice 型面板(DL 目标/fea82 用) | `panels/wide_panel_4h_v3splice_x0918.npz` | `293a14cf65f422bfbd849993b6b37b27c8dee7fd03b2ab37cc562ce636751ce0` | 2020-01-31 / 2026-09-18T00:00Z | 14,533 锚(前缀 14,425 + 尾 108) |
| 3d | EMA 状态(canoncont) | `panels/fund_state_canoncont_{v2ext,v3splice}_x0918.json` | `4d67ef63…` / `f4c72fb9…` | — | — |
| 3e | 记账元 `meta_newprod_v4` 型 | `meta/meta_newprod_v4_x0918.npz` | `22e990f86babd64a30801992627ee2f175e0c920aa442943629f200f16406d1e` | 2022-01-03T00Z / **2026-09-18T20:00Z** | 10,319 锚 |
| 4 | king v4 特征 + 元(新构建器 v2 + 成员掩码) | `data/wide_fea_v4.npy` / `data/wide_fea_v4_meta.npz` | `8c5cffe5d1427120cf84f1bc94e403e58e1cab838df52122e46e22b131eea763` / `a022d7035709e77aad894d25ed0eea4fb77b7f953545205cc9089de361c19c9e` | 2022-01-03T00Z / 2026-09-18T20:00Z | (10,319, 829, 82) f16 |
| 5a | DL 目标 RAW(dlw_v4raw 型) | `dlw_v4raw/data/dlw_targets.npz` | `8df390b6ee7748a284df81723188221eff82cb9202c982b35b4c38716c3f2391` | 2022-01-03T00Z / 2026-09-18T20:00Z | 10,319 锚 |
| 5b | DL 目标 CLIP(对照臂; fea89 的输入) | `dlw_hf3/data/dlw_targets.npz` | `891f2eb5bdf08d0477df2de07559b4dfb915e83b89e923c541b9d9242381d2d3` | 同上 | 10,319 锚 |
| 5c | fea82 | `dlw_hf3/data/dlw_fea82.npz`(逐字节拷贝到 `dlw_v4raw/data/`) | `10db570458bd010eccf59543fbecd15367194e7eb143f2691289b6c08c3fd788`(两处逐字节相同) | 同上 | X (2,792,891, 82) f16 |
| 5d | fea89(f8) | `f8_v4/data/f8_fea89.npz` | `ef120d0f272449f4fe037f016d008f2128c96fdf09c30a3fde4969060c292e56` | 同上 | X (2,792,891, 89) f32 |
| 6a | 可交易性(SPEC_TRADABILITY) | `trd/tradability_v1.npz` | `bebf69ab9ddb3b05b49552e66dccf9b8cde3caee0593b14e1b3fe1a4c93c9db8` | 2022-01-01T00Z / 2026-09-19T00Z | 10,333 锚; ts5 495,937 |
| 6b | 成员掩码 可交易 W24H | `masks/member_mask_tradable_W24H_cachegrid.npz` | `9793722e325fc71650ed497ebbf9587a326247c8066ea93f5b9c20b4550ef628` | 同上 | (10,333, 829) |
| 6c | 成员掩码 可交易 ∧ 判活 W24H | `masks/member_mask_tradable_AND_live_W24H_cachegrid.npz` | `04aeefbb10feb19a48970c262d921aa6d1799fb66aa918164744d3131fb81a2f` | 同上 | (10,333, 829) |

原始下载(只读输入): `dl/klines5m/<SYM>/<day>.zip`(09-11..09-18, 每日 798 个), `dl/funding/fund_rest_20260820_20260919T00.json.gz`(sha `803c17e6…`; 文件名里的 0820 是我算错的标签, 实际窗 08-21T00Z 起, 见 §4), `t7_klines_1h_x0918/`(T7 第三方 1h 对照延长), `inputs/producer_ledger_tail_20260919.json`(在役生产者 `aux.json` 的 `ledger_tail` 只读拷贝抽取, sha `e9dd86a0…`, 源文件 sha `20cc2b75…`)。

## 2. 构建链(谁产出什么, 用的是哪个构建器)

驱动 `devices/ax_chain.sh`(每步 `env -i` + 显式键; 任一步非零即停)。s1–s9 跑的是 `ax_chain.r1_a5b25b8b.sh`, s10 起是 `ax_chain.sh`(`a934bb72`, 只多了测峰值内存的包装 `ax_peakrss.py`, 构建命令逐字相同)。

| 步 | 内容 | 构建器(sha 前 8) | 改动 |
|---|---|---|---|
| s1 | 缓存追加 | `ax03_merge_cache.py`(逐字抄 r6_merge_cache / pod_merge_cache_ext 的逐名数学) | 新装置; 基 = x0910, 只追加基末行之后的行 |
| s2 | 逐位追加门 | `ax03b_bw_gate.py`(r6_bw1_gate 泛化到多个基) | 新装置 |
| s3 | 覆盖门 | `cache_coverage_gate_v2.py` 23584a0c | **未改** |
| s4 | RAW 补丁 + manifest + 覆盖门 | `ax07_raw_patch_ext.py` → `v4_rawpatch_manifest.py` db68f3bf → `v4_gate_rawpatch.py` | 后两者**未改** |
| s5 | 可交易性 | `ax06_fx_trd_build.py` = `fx_trd_build.py` 066c3d74 仅把扩展缓存路径与其 sha16 改为 env(diff: git `axis_0919_2026-09-19/receipts/ax06_fx_trd_build.diff`) | 路径补丁 |
| s6 | 掩码 | `fp2_member_mask_build.py` a2d5493a → `v4_member_mask_liveness.py` a369e1c0 | **未改** |
| s7 | 资金费账本 | `ax04_funding_ledger.py` | 新装置 |
| s8 | 原始面板 | `pod_panel_ext.py` db7f0474 | **未改**(见 §5.1 的 rc 3) |
| s9 | 面板拼接 | `ax05_panel_splice_ivledger.py` = `r6_panel_splice.py` cccc5b6b + 3 处补丁(diff: git `axis_0919_2026-09-19/receipts/ax05_vs_r6_panel_splice.diff`) | 区间来自账本 |
| s15 | king 特征 | `pod_fea_ext_clamp_v2.py` 7b8b843d + `MEMBER_MASK_NPZ` = 6c | **未改**; 单独运行 |
| s10 | DL 目标 RAW / CLIP | `pod_dlw_targets_raw_v2.py` 9e9dfd94 + 掩码 6c(RAW 带 1b 补丁, CLIP 补丁显式为空) | **未改** |
| s11 | fea82 | `pod_dlw_features_ext.py` e86725cc | **未改** |
| s12 | fea89 | `pod_f8_build_ext.py build` f606bffa | **未改** |
| s16 | 记账元 | `ax09_meta_newprod.py`(逐字抄 build_dev_v4.py L14-18 的元部分, 不建 dev 树) | 新装置 |

构建器清单与 FP3-live(`/workspace/fp3_live_2026-09`, 09-18 按判活掩码重建的研究臂, 非月链决策)相同; git 装置目录 `retrain_2026-09/v4_chain_2026-09-09/` 整体拷到 pod `devices/v4chain/`, 177 个文件逐个 sha256 与 git 相等(git `axis_0919_2026-09-19/receipts/v4chain_device_sums_pod.txt`)。

## 3. 前缀恒等证明(每个延长数组)

| 组件 | 参照(来源) | 比较范围 | 结果 |
|---|---|---|---|
| 5m 缓存 | holefix2 正典 `1d7f459d` | 490,753 行 × 829 × 7 = **2,847,839,659 格** | 位模式差 0, NaN 模式差 0, max\|Δ\| 0.0; ts/符号/通道全等(`receipts/CACHE_BW.json`) |
| 5m 缓存 | r6 x0910 `81152994` | 493,633 行 × 829 × 7 = **2,864,552,299 格** | 同上, 全 0 |
| 5m 缓存(构造复现) | x0910 自身的 09-04T00:10..09-11T00:00 | 2,015 行, 10,351,733 个有限格 | 用同一批日档重建, 逐位相等, NaN 模式差 0(`CACHE_MERGE.json` PAR) |
| RAW 补丁 | FP2 补丁 952 行 | 全部旧行 6 列 | 逐字节相同; r6 x0910 的 3 个新行(AKE/BULLA/WOO)逐位复现 |
| 可交易性 | 已认证 `tradability_v1.npz` 54d409d0(到 09-11T00Z) | 10,285 个共同锚 × 829; 5m 位图前缀 | state_W24H / W4H / truncated 差 0; ts5 与 traded/nodata/tradable 位图前缀逐字节相等 |
| 掩码 可交易 W24H | FP2 `e0f67739` | 10,225 锚 × 829 | 差 0 |
| 掩码 可交易∧判活 | FP2 `9b59678b`(判活构建器旧版 0704cde5) | 10,225 锚 × 829 | 差 0(新旧判活构建器在 300 s 网格上结果相同) |
| 原始面板 | r6 x0910 原始面板 | 10,099 锚, 21 个键 | 差 0 |
| v2ext 面板 | 正典 v2ext `5e67c055` | 10,039 锚, 21 个键 | 差 0(拼接内置 BW-2 也 PASS) |
| v3splice 面板 | 正典 v3splice `c5d10f6a` | 14,425 锚, 21 个键 | 差 0 |
| v2ext 面板尾部 | T5d 区间修正版 `a5d7fb97`(08-31T04Z..09-10T00Z) | 60 锚, 21 个键 | 仅 `f_fund_ema_v2` 581 格 / 10 名不同; `f_fund_now`/`f_fund_iv`/`f_fund_ema`/`f_fund_ema_v1` 与其余全等。**10 名逐格归因**: 把 span 的中位数窗口截到 T5d 当时的流末(09-11 15:00Z)重算, 581 格逐位等于 T5d(`receipts/V2SPAN_ATTRIBUTION.json`) |
| v3splice 面板尾部 | r6 x0910(**带区间缺陷**) | 60 锚, 21 个键 | 仅三键不同: `f_fund_iv` **547 格 / 23 名**、`f_fund_ema_v1` **870 格**(与记忆 x0910_fund_iv_interval_mismatch 的 547 / 870 逐数相同)、`f_fund_ema_v2` 992 格(= 缺陷 924 + span 窗口) |
| DL 目标 RAW / CLIP | FP3-live 同构建器同掩码规则 | 10,212 个共同锚(FP3 轴 2022-01-03 → 08-31T20Z)× 829, 9 个键 | 两者都: 成员 10,212/10,212 锚全等; y4s / y4old / qvk / btcv / yrs / E_row 差 0; YR4s / YRZ / has_panel 只在 FP3 无面板行的 5 锚不同(各 2,000 格, FP3 为 NaN) |
| DL 目标 RAW 的 y4s | r6 x0910(无掩码 v1 构建器) | 10,271 个共同锚(→ 09-10T20Z)× 829 = 8,514,659 格 | 差 0(x0910 段的 RAW 标签与本轮逐位相同) |
| fea82 | FP3-live | 10,212 锚, 225,507,462 格(按成员对齐) | 成员不同的锚 0; 只有 FP3 无面板行 5 锚的 `fund_ema`(2,000 格)/`fund_now`(1,866 格)不同, 其余 80 列全等 |
| fea89 | FP3-live | 10,212 锚, 244,758,099 格 | 差 0 |
| king 特征 + 元 | FP3-live | 10,212 锚 × 829 × 82 = 694,191,336 格 + 元的 members / y4 / qvk | 成员不同的锚 0; 元 y4 / qvk 差 0; 特征只在 FP3 无面板行 5 锚的 `fund_ema`/`fund_now`(各 2,000 格)不同 |
| 记账元 | 九月 `meta_newprod_v4.npz`(无掩码 v1 轴) | 10,182 个共同锚中补洞邻域外 9,670 个 | y4 逐位相等(有限模式相同, max\|Δ\| 0.0), qvk 相等; 成员规则用链里唯一实现 `fp2_gate_lib.members_subset_check`(截断感知)PASS: 移除 2,376 格全是掩码假, 新增 145 格 / 108 锚全在参照截断到 400 的锚且掩码真, 保留成员全掩码真(`receipts/META_MEMBER_RULE.json`) |

"FP3-live 最后 5 锚(08-31T04Z..20Z)资金费列不同"一类的差, 原因都是: 九月构建的面板止于 08-31T00Z(构造上比轴末早 20 h), 那 5 锚没有面板行 ⇒ 资金费特征为 0/NaN; 本轮面板延长后这些锚有了值。比较器把它归为 `ref_no_panel_row`, 只允许资金费列不同, 其余列必须逐位相等。

## 4. 资金费账本与区间

- 来源: 公开 REST `fapi/v1/fundingRate`(无密钥, 1.4 次/秒, 避开锚窗), 829 名请求, 679 名有数据、150 名空(窗前已下架/从未上市), 98,539 行, 取数 06:24:40Z–06:34:41Z; 另并入月度归档 zip 与 `fund_aug.json.gz`。窗 = **2026-08-21T00:00Z → 2026-09-19T00:00Z**(含; 09-19T00Z 之后的 452 行被切掉)。
- **区间规则**(`ax04` 文档串): 归档行自带区间列 > 相邻结算时间差(圆整到 {1,2,4,6,8}) > 生产者账本同一结算 > **8**(构建器自己的回退值)。**从不使用取数时刻的 fundingInfo**(r6 缺陷根源)。
- 结果: 时间差 98,066 次; 回退 8 共 **21 次, 全部是代币化股票永续上"前一次结算之后 1 秒又结算一次"的第二次**(CRM/EBAY/GLW/GOOGL/GS/HD/HPE/HYUNDAI/NVDA/PYPL/QCOM/SKHYNIX/SPY/STRC×2/TER/TSM/VRT/WDC/WEN/WMT); 下一个时间差另存为诊断列 `iv_next_gap`。演练里我先用了"取下一个时间差"作回退, 它把 GLW/STRC 的 v1 EMA 推离了构建器规则(T5d 在这两处用的是 8), 已改回 8 并复核: v1 与 T5d 全等。
- 交叉核对: 在役生产者账本 82,728 次结算 **区间 0 不一致、费率 0 不一致**; T5d 区间源 46,311 次 0 不一致; REST 与 fund_aug 重叠段费率 0 不一致; 区间分布 1h 1,938 / 2h 8 / 4h 74,080 / 6h 2 / 8h 22,059。
- 死合约: 790 次结算落在该名最后一根有成交 bar + 24h 之后, 标 `after_last_trade`(只标不删; 4h 表另给 `next4h_sum_live` 排除它们)。
- 面板拼接(s9)对每个尾部事件检查: 账本必须有这次结算(缺 0)、费率必须与账本相同(差 0)。
- **4h 记账表**给出面板覆盖不到的最后 5 锚(09-18T04Z..20Z)的资金费: 面板 `pod_panel_ext.py` 要求锚后 288 行才出行, 所以面板止于 09-18T00Z(与九月同构: 缓存 09-01T00Z ⇒ 面板 08-31T00Z)。`f_fund_now`/`f_fund_iv` = 锚时刻生效的最近结算(>12h 置 NaN, 同构建器), `next4h_sum` = (A, A+4h] 内结算费率之和(持仓窗实付)。

## 5. 已知缺陷的处置

1. **pod_panel_ext 的 v1 自检 rc 3(X3 amihud)**: 在所有 holefix 谱系缓存上都是 `f_amihud_24h corr 0.054600`(r6 RESULT §X3 + `RECEIPT_r6_X3_amihud_diagnosis.json` 已诊断: 重尾比值, 逐锚 Spearman 中位 1.0)。链只在 7 行 parity 读数与 r6 **逐行相同**且面板已写出时接受 rc 3, 门未改阈值; 原始面板与 r6 原始面板在 10,099 个共同锚上 21 键全等。
2. **r6 区间缺陷**: 不用 `r6_panel_splice.py` 的取数时刻区间(§4); 差异逐数对上记忆记录(§3)。
3. **缓存 ret5 ±0.30 裁剪**: 记账 y4 只来自 RAW 目标构建器(补丁覆盖门 PASS: 960 个候选 = 959 个补丁行 + 1 个未裁剪, 0 未解释); 新增 4 个裁剪 bar: LSK 09-13 03:30 +46.6%、AIN 09-16 01:50 −55.0% / 02:25 −33.0% / 02:30 +34.4%。
4. **补洞 bar 不是活数据**: 判活掩码按补洞格判死; 新行没有任何补洞。唯一后果是 09-01T00Z 锚被丢(§0-1)。
5. **死合约冻结行**: 可交易性按成交数定义(log_cnt>0), 156 个死合约; 掩码在最后成交 + 24h 之后为真的格 = **0**(可交易掩码与判活掩码都为 0; `INVENTORY.json`)。每天有 bar 的 798 名里包含仍在写冻结行的死合约, 所以"798 名全 288 根"不是"798 名在交易"。
6. **king 构建器内存**: 单独运行, 启动前 cgroup anon 1.37 GB(memory.max 60,999,999,488 B; 仅另一流一个 1.8 GB 进程在跑); 峰值 RSS **50.24 GiB**(`logs/peak_s15_king.json`), cgroup `memory.current` 采样最高 56.81 GB(含页缓存, = 上限), `oom_kill` 计数前后都是 3(未新增)。
7. **磁盘**: `statvfs` 只报共享 MooseFS 的 559 TiB(配额不可见), 1 GiB 写探针成功; 本根全部 11 GB(含 5.2 GB 演练目录)。

## 6. 过程中的发现与更正(按时间)

- 07:02Z 演练 1 在缓存奇偶校验 FAIL: 798 格 NaN 模式差 = 窗口第 2 行(其前一根 bar 在未载入的前一天日档里, ret5 构造上为 NaN)。改的是装置参数(奇偶窗从第 3 行起), 门本身不变; 文档串写明原因。
- 07:36Z 演练 s8 rc 3 = 已知 X3 读数(§5.1), 为此在链里加了"逐行等于 r6 读数才接受"的条件。
- 07:48Z 首次抓 09-18 日档时有 16 个名 404, 全部是字母表末尾(U–Z): 发布还在进行中。等到锚窗结束 08:57Z 重抓, 16/16 成功, 09-18 的 404 集合与之前每天相同的 31 个。若不核对 404 集合, 这会成为 16 个活名在 09-18 整天"停牌"。
- 08:1xZ 区间回退规则由"下一个时间差"改回构建器的 8(§4)。
- 09:0xZ 比较器在 NpzFile 上逐锚取 `A["members"]` 导致每次整表重读(极慢), 改为一次物化; 结果不受影响。

## 7. 没有做 / 做不了的

- **legs(`f10v2_legs.npz`)**: 需要 king 预测(`slow_pred_pinned`), 属流 O。
- **F10 / king 预测、dev 树(SLOW/FPRED 文件)**: 流 O / R。
- **FUND_AUG 兼容文件、October env / ROLL_PATHS / PREV_SHA_JSON、UMASK(UPIT_CRYPTO ∧ tradable)延长**: 不在本任务; UPIT_CRYPTO 宇宙掩码本身止于 08-31T00Z, 延长它是宇宙政策问题。
- **09-01T00Z 锚的回填**: 需裁定是否用已存在的 08-31 真实日档替换补洞行(违反仅追加, 需新预注册)。

## 8. 复跑命令(逐字)

```
# 下载(需网络; 已完成)
AX_ROOT=/workspace/axis_0919 AX_TAG=d0911_0917 AX_DAYS=2026-09-11,...,2026-09-17 AX_CHECK_ONLY_DAYS=2026-09-10 AX_CHECK_ONLY_DIR=/workspace/uplift_2026-09-11/r6/dl/klines AX_RPS=5 python devices/ax01_fetch_klines5m.py
AX_ROOT=/workspace/axis_0919 AX_TAG=d0918 AX_DAYS=2026-09-18 AX_RPS=5 python devices/ax01_fetch_klines5m.py            # 版本 r1_3d9804f4
AX_ROOT=/workspace/axis_0919 AX_TAG=d0918_retry1 AX_DAYS=2026-09-18 AX_SYMS=<16 名> AX_RPS=5 python devices/ax01_fetch_klines5m.py
AX_ROOT=/workspace/axis_0919 AX_TAG=fund_rest_20260820_20260919T00 AX_START_MS=1787270400000 AX_END_MS=1789862459999 AX_RPS=1.4 python devices/ax02_fetch_funding.py
AX_T7_IN=/workspace/fx_data_2026-09-13/t7_klines_1h AX_T7_OUT=/workspace/axis_0919/t7_klines_1h_x0918 AX_T7_END_OPEN_S=1789772400 AX_T7_RECEIPT=/workspace/axis_0919/receipts/T7_EXTEND_RECEIPT.json AX_RPS=3 python devices/ax06a_t7_extend.py
# 构建(pod2, cd /workspace/axis_0919)
AXR=/workspace/axis_0919 AX_NEW_DAYS=2026-09-11,2026-09-12,2026-09-13,2026-09-14,2026-09-15,2026-09-16,2026-09-17,2026-09-18 AX_IDX_END="2026-09-19 00:00" AX_HI_S=1789776000 STAGES=s1,s2,s3,s4,s5,s6,s7,s8,s9 bash devices/ax_chain.sh
AXR=... (同上) bash devices/ax_king_guarded.sh           # s15, 单独
AXR=... (同上) STAGES=s10,s11,s12,s16 bash devices/ax_chain.sh
# 证明
AX_SPEC="$(cat receipts/ax10_spec_part1.json)" AX_RECEIPT=.../receipts/PREFIX_PROOF_part1.json python devices/ax10_prefix_proof.py
AX_SPEC="$(cat receipts/ax10_spec_part2a.json)" AX_RECEIPT=.../receipts/PREFIX_PROOF_part2a.json python devices/ax10_prefix_proof.py   # 目标 / y4s / king
AX_SPEC="$(cat receipts/ax10_spec_part2b.json)" AX_RECEIPT=.../receipts/PREFIX_PROOF_part2b.json python devices/ax10_prefix_proof.py   # fea82 / fea89
META=.../meta/meta_newprod_v4_x0918.npz REF_META=/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz CACHE=.../data/dlnative_5m_wide829_f16_holefix2_x0918.npz HOLE_CELLS=.../inputs/holefix2_cells.npz MEMBER_MASK=.../masks/member_mask_tradable_AND_live_W24H_cachegrid.npz GATE_LIB_DIR=/workspace/axis_0919/devices/v4chain RECEIPT=.../receipts/META_MEMBER_RULE.json python devices/ax09b_member_rule.py
AX_PANEL=.../panels/wide_panel_4h_v2ext_x0918.npz AX_IVFIX=/workspace/uplift_r2_2026-09-13/T5d/panel/wide_panel_4h_v2ext_x0910_ivfix.npz AX_BASE=/workspace/data/wide_panel_4h_v2ext.npz AX_LEDGER=.../funding/funding_ledger.npz AX_T5D_STREAM_END=1789138800 AX_RECEIPT=.../receipts/V2SPAN_ATTRIBUTION.json python devices/ax12_v2span_attribution.py
AXR=/workspace/axis_0919 AX_X4_FROM=1788148800 AX_RECEIPT=.../receipts/INVENTORY.json python devices/ax11_inventory.py
```

## 9. 墙钟与内存

| 阶段 | 起止(UTC, 09-19) | 墙钟 | 峰值 RSS |
|---|---|---|---|
| 5m 日档 09-11..09-17(+09-10 校验) | 06:18–07:00 | 2,520 s | — |
| 5m 日档 09-18 首抓 / 重抓 16 名 | 07:48–07:54 / 08:57 | 360 s / 数秒(其余是锚窗等待) | — |
| 资金费 REST / T7 1h 延长 | 06:24–06:34 / 06:3x | 601 s / 187 s | — |
| s1 缓存追加 / s2 逐位门 / s3 覆盖门 | 08:58–09:04 | 149 s / 169 s / 46 s | — |
| s4 补丁 / s5 可交易性 / s6 掩码 / s7 账本 | 09:04–09:12 | 96 s / 130 s / 26 s / 236 s | — |
| s8 原始面板 | 09:12–09:20 | 483 s | 未包装; 演练中 ps 观测 31.2 GB(非峰值) |
| s9 两个拼接 | 09:20–09:43 | 1,366 s | — |
| s15 king(单独) | 09:44–09:54 | 588.5 s | **50.24 GiB**(cgroup anon 采样最高 51.03 GB, memory.current 56.81 GB 含页缓存; oom_kill 未增) |
| s10 目标 RAW / CLIP | 09:54–09:59 | 162 s / 108 s | 27.44 / 27.28 GiB |
| s11 fea82 / s12 fea89 / s16 元 | 09:59–10:15 | 142 s / 827 s / 5 s | 18.12 / 25.60 GiB / — |

正式构建从 08:58 到 10:15(1 h 17 min, 含 king); 整个任务 06:11 → 10:20 约 4 h, 其中约 1 h 在等 09-18 日档发布(07:40:01Z 才上线)和 08:00 锚窗。峰值 RSS 由 `devices/ax_peakrss.py`(getrusage RUSAGE_CHILDREN)测得, 收据 `logs/peak_*.json`。

## 10. 限定

- 所有"逐位相同"都是**在 pod2 上重新读写出的文件**上算的; 比较器、门的判词行都在 `receipts/`。
- 前缀参照选的是**同构建器同规则**的最近构建(FP3-live / FP2 / 正典面板 / 已认证可交易性); 与无掩码 v1 构建(九月 dlw_v4raw、r6 x0910)只比标签 y4s 和记账元 y4(成员规则不同, 成员集本就不该相同)。
- 09-11..09-18 的新行只经 T7(1h 成交数, 362 名)第三方对照, 没有与实盘成交或另一家数据源逐 bar 对账。
- 面板 `f_fund_ema_v2` 的整尾 span(§0-4)是既有算法的性质, 本轮未改; 下游若把它当因果特征用, 会有前视。
