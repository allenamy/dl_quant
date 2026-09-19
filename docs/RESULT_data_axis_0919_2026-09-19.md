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


---

## 11. 附录(2026-09-19 lead 裁定, 追加; 上文字节不动): 08-31 官方日档修正变体 `x0918r`

**裁定原文要点**(lead, 用户授权「修复不用等我裁定 / 按最佳建议」): 修 09-01T00Z 缺锚, 但不破坏既有文件的仅追加; 在 x0918 旁建**新文件**变体 `x0918r`: 08-31 补洞行换成 data.binance.vision 官方日档(校验和核过、同构建器约定), 下游重建; x0918 字节不动; 这是具名、有文档的偏差。

### 11.1 08-31 为什么被补洞(溯源, 读源码与日志)

1. `pod_merge_cache_ext.py` 在 2026-09-01 01:52Z 构建 `_ext` 缓存时, 08-31 的日档还没发布(`wide_multisrc/klines5m_daily/<SYM>/2026-08-31.zip.404` 标记至今还在) ⇒ `_ext` 里 08-31 整天为 NaN。
2. `review_scratch/holefix_build.py`(Task A, 09-08)用官方 **2026-08 月档** 5m 按「只填 NaN」补了整个八月; 日志 `holefix_build.log`: `2026-08-31(D2) 1478732` 个通道格。
3. `v4_hole_cells.py` 把「holefix2 有限且 `_ext` 全 NaN」的每个 (行, 名) 记为补洞格 ⇒ 08-31 成为第 4 个补洞段 `[490465, 490752]`(229,824 格 / 798 名), 邻域 `[490417, 499392]` = [段首−48, 段尾+8640]。
4. MEMBER_LIVENESS 把补洞格一律视为「非真实 bar」⇒ 锚 09-01T00Z 的 24h 窗恰好就是 08-31 的 288 行 ⇒ 无活名 ⇒ 成员 < 50 ⇒ 构建器丢锚。

也就是说, 那一天的数其实来自官方月档, 只是被登记成补洞。

### 11.2 替换了什么(逐格)

装置 `devices/ax13_d31_replace.py`(收据 `receipts/pod2/x0918r/receipts/D31_REPLACE.json`):
- **校验和**: 读到的 1,596 个日档(08-30 连续性 798 个 + 08-31 798 个)逐个与场所 `.CHECKSUM` 相符(`KLINES5M_check_d0830_shared.json` / `KLINES5M_check_d0831_r6.json`: 798 OK / 31 个 404 / 0 失败; 08-31 的 31 个无档名 = 09-11..09-18 每天相同的 31 个)。
- **范围**: 行 490465..490752 = 2026-08-31 00:05Z .. 09-01 00:00Z 收盘(即 08-31 开盘的 288 根 bar), 829 名 × 7 通道 = 1,671,264 个通道格。
- **数值**: 用与 merge / holefix 逐字相同的 7 行通道公式从日档重建; 与 x0918 比: 7 个通道的**有限格全部逐位相同**(ret5 / range / log_qv / log_cnt 各 229,824, cpos 186,275, log_avgsz / tbf 各 189,138), **NaN 图样完全相同**, max|Δ| 0.0。(= r6 X2-B 的结论在新文件上重做一次。)
- **唯一的位级差**: 84,235 个 NaN 格的符号位(cpos 43,549 + tbf 40,686): x0918 里是 +NaN(0x7e00), 官方重建是 −NaN(0xfe00)。原因: holefix 只写「新值有限」的格, 0/0 得到的 NaN 格从未被写, 保留了 `_ext` 的初始 +NaN; 而所有正常按日档构建的行(08-30、09-01、09-15 实测)里 0/0 的 NaN 都是 −NaN, 只有 31 个缺档名 × 288 = 8,928 格是 +NaN。**x0918r 让 08-31 与其余各天的编码一致**; 所有构建器都经 `isfinite` 读缓存, 这个位差不会传到任何下游数值(C5 实测)。
- **补洞格**: 229,824 个 (行, 名) 全部有官方 bar(798 名 × 288 根, 每名满 288)⇒ **全部移出补洞表, 0 格因无官方数据而保留**。31 个无档名在 08-31 本来就没被补(整天 NaN), 在 x0918r 里仍是 NaN, 不在补洞表里。
- **写出方式**: 因为 NaN 位不同, x0918r 缓存是新 npz(`08bb2957…`), 不是 x0918 的字节拷贝。

补洞表 `x0918r/inputs/holefix2r_cells_x0918r.npz`(`d524f819…`): 1,422,720 → **1,192,896** 格; 第 4 段及其邻域 `[490417, 499392]` 删除; 其余 3 段与邻域不变(第 3 段 08-13..08-24 的邻域 `[484945, 497136]` 本来就覆盖到 09-23, 所以 08-31 之后的锚在月门的邻域豁免上不变)。新增字段 `removed_row/removed_col/provenance/source_holes_sha256`。

### 11.3 下游重建与逐项差异证明

驱动 `devices/ax_chain_r.sh`(r2–r8 跑的是 `ax_chain_r.r1_06469425.sh`; r9 第 2 次尝试是 `ax_chain_r.r2_0ea4279b.sh`; 在飞的 r9–r11 是现版 `46f23676`, 只改了 r9 的重试编号、24 h 等待上限并加了 r11 最终证明); 构建器与 x0918 链逐 sha 相同。差异证明 `devices/ax14_variant_diff.py`(收据 `…/x0918r/receipts/VARIANT_DIFF.json`):

部分证明收据 `VARIANT_DIFF_partial_preking.json`(king / 记账元未出, 标 PENDING); 全量证明由在飞的 r11 写 `VARIANT_DIFF.json`。

| 项 | x0918r vs x0918 | 结果 |
|---|---|---|
| C1 缓存 | 替换区间外 2,876,251,147 个通道格按 uint16 比(含 NaN 位) | **差 0** |
| C1 缓存 | 区间内 1,671,264 格 | 有限格位差 0, NaN 图样差 0; 只有 NaN 符号位 84,235 格(cpos 43,549 / tbf 40,686), 见 §11.2 |
| C2 补洞表 | 1,422,720 → 1,192,896 | 移除 229,824 格全在区间内, 新增 0, 区间内余 0 |
| C3 可交易性 / 可交易掩码 | 构建器在 x0918r 上重跑 | **字节相同**(`bebf69ab…` / `9793722e…`) |
| C4 判活掩码 | 10,333 锚 × 829 | 只有 **09-01T00Z 一行**变: 0 → 669 个真(false→true 669, true→false 0)。另外 10 个窗口碰到 08-31 的锚(08-31T04Z..20Z、09-01T04Z..20Z)一格不变: 那些名在窗口里 08-31 之外本来就有真实 bar |
| C5 原始面板 | 面板构建器在 x0918r 上重跑 | **字节相同**(`fe4c77c1…`)⇒ x0918 的 v2ext / v3splice 面板就是 x0918r 的面板, 不重建 |
| DL 目标 RAW / CLIP | 10,319 个共同锚 × 9 键 | **全部 0 差**(成员、y4s、y4old、qvk、btcv、YR4s、YRZ、has_panel、yrs); 唯一变化 = 新增锚 09-01T00Z(成员 400, y4s 与 YR4s 在 400 个成员上全有限, has_panel 真) |
| fea82 | 10,319 个共同锚 | **0 差**; 只多了 09-01T00Z |
| fea89 | 10,319 个共同锚 | 成员 0 差; 变化只在按锚**序号**取窗的两族(全部解释, 0 未解释): **J `drank_m7_1d / drank_v7_1d / drank_r24_1d`**(各约 2,345 格, 6 个锚 09-01T04Z..09-02T00Z: 「i−6 锚」现在恰好是 24h 前, 原先因缺 09-01T00Z 而错位)和 **H 族 10 列**(`disp_z, btcv_z` 及其与 r4/r24/m7/v7 秩的乘积, 各 42,800 格, 09-01T04Z..09-18T20Z 全部 107 锚: `causal_z` 是按位置的 180 锚滚动窗, 插入一锚后之后每个窗都移了一位)。两者都是更正, 不是新误差 |
| king 特征 + 元 / 记账元 | — | **PENDING**(r9 king 等内存, 见 §11.5) |

**lead 预期的「08-31 之后约 24h 的特征窗会变」没有发生**: 缓存数值没有变, 所以所有按缓存行取窗的特征(含 30 天窗)逐位不变; 变化只经判活掩码进入(新锚)以及 fea89 两族按锚序号取窗的量。

### 11.4 轴

- DL 目标 RAW / CLIP、fea82、fea89: **10,320 锚, 2022-01-03T00:00Z → 2026-09-18T20:00Z, 格点 10,320, 缺 0**(含 09-01T00Z)。
- 判活规则**不再**丢 09-01T00Z: 该锚窗口 = 08-31 的 288 行, 这些格已不在补洞表 ⇒ 669 个名可交易且判活 ⇒ 按 qv 取前 400 名 ⇒ 成员 400。
- king 特征 / 记账元: PENDING(预期同为 10,320, 因为同一掩码、同一成员规则; **未实测前不写成结果**)。

### 11.5 内存检查(lead 规则: 共享 pod, 峰值后可用 ≥ 20 GiB, 不杀别人, 不按名杀)

守卫 `devices/ax_memguard.py`: 每个重构建器启动前同时查 **主机**(`free -g` 的 available = /proc/meminfo MemAvailable)和**容器 cgroup**(memory.max 61 GB = 56.8 GiB, 用 anon+shmem)。两者都要求「峰值后仍 ≥ 20 GiB」; king 的 50 GiB 峰值在 56.8 GiB 的 cgroup 里即使空载也只剩 6.6 GiB, 按字面规则永远不能启动, 所以对它规则退化为「单独运行」(他人用量 ≤ 2 GiB)。每次检查写入 `logs/mem_*.json`。

| 阶段 | 声明峰值 GiB | 实测峰值 GiB | 准入时 cgroup 他人用量 GiB | 主机可用 GiB | 等待 | oom_kill 前→后 |
|---|---|---|---|---|---|---|
| r6 面板构建器 | 32 | **39.48** | 0.13 | 137.9 | 0 | 3→3 |
| r7 目标 RAW | 28 | 27.44 | 0.13 | — | 0 | 3→3 |
| r7 目标 CLIP | 28 | 27.28 | 4.81 | — | 0 | 3→3 |
| r8 fea82 | 19 | 18.12 | 5.82 | — | 0 | 3→3 |
| r8 fea89 | 27 | 25.58 | 0.94 | — | 0 | 3→3 |
| r9 king 第 1 次(v1) | 51 | 50.24 | 0.13 | 206.6 | 0 | **3→4(本进程被杀)** |
| r9 king 第 2 次(v2, try1) | 51 | — | 6.6–17.4(60 s 一查, 11:18–11:47Z 共 30 次, 一次也没满足 ≤ 2 GiB) | — | 被我按自己的进程组停下以延长等待上限 | — |
| r9 king 第 3 次起(v2, try2…) | 51 | PENDING | 在飞: 11:48Z 起等待, 每次最长 24 h | — | — | — |

每次检查的完整记录在 `x0918r/logs/mem_*.json`(时间、主机可用、cgroup 用量、当时 >256 MiB 的进程)。**调度**(coordinator 11:4xZ): pod2 优先级 1 = object-B A0 链(PGID 1269476, 预计 18–19Z)及其 v4 臂, 2 = baseline runner(PGID 1265729), 3 = x0918r; 不请别人让路。king / 记账元 / 最终证明因此在后台排队, 由 r9→r10→r11 自动完成; 进度与复跑命令在 `x0918r/receipts/PROGRESS.json`。

两处需要如实说明:
1. **面板构建器 r6 我声明的峰值(32 GiB)低于实测(39.48 GiB)**: 我手上只有演练时 `ps` 的 31 GB 观测。准入时 cgroup 他人用量 0.13 GiB, 实际峰值时 cgroup 余量约 17 GiB(不是 20), 主机余量约 98 GiB; 无 OOM。之后的声明峰值都改用 getrusage 实测值。
2. **king 第 1 次(11:08Z, 守卫 v1)在 11:16Z 被 OOM 杀掉**(rc −9, cgroup oom_kill 3→4; 牺牲者就是我的 king 进程, 另一代理的进程都还在跑)。原因: 另一代理的 object_b 批(PGID 1263453, 含 /dev/shm 里的 venv 副本)在 11:12:03 启动, 我的 king 正爬向 50 GiB。v1 只在启动时检查。**v2** 加了 ① 启动前连续 5 次(60 s 间隔)都满足的安静期; ② 运行中每 2 s 的让路看门狗: 他人用量 + 我的声明峰值一旦超过上限, 就按**我自己记录的进程组**把 king 杀掉并记为 YIELDED(退出码 76), 然后 5 分钟后重试, 最多 8 次。这样别人的新批次不会成为我的 OOM 牺牲者, 也不会拖着我一起被杀。第 1 次的收据和日志保留为 `*.attempt1_oom.*`。

### 11.6 已知隐患: `f_fund_ema_v2` 前视(文档化, 未改)

- **定义**: 结算空间 EMA, adjust=False, `span = max(2, round(24 / median(区间)))`。这个中位数取在**整段**上:
  - `pod_panel_ext.py` L145: `np.median(iv_full)` = 该名**全部历史**结算区间的中位数(构建时刻为止)⇒ 正典面板前缀里每一格 v2 都用到了之后的区间结构;
  - `pod_panel_splice.py` L87 / `r6_panel_splice.py` L108 / 本轮 `ax05`: `np.median(ivv[sel])` = 拼接**整个尾部**的中位数 ⇒ 数据延长会改变更早尾部锚的 v2(§3: 相对 T5d 的 581 格 / 10 名, `V2SPAN_ATTRIBUTION.json` 逐格证明)。
  - 区间在样本中变过的名(代币化股票永续、改过结算频率的名)v2 不是因果特征; 区间从未变过的名 span 恒定, 不受影响。v0(`f_fund_ema`)与 v1(`f_fund_ema_v1`)用墙钟半衰期, 无此问题。
- **谁在用(按 grep, 不是推测)**: 在 git 仓库全部 `.py/.sh` 与 pod 的 `/workspace/*.py`、`port_w10/*.py`、`review_scratch/*.py`、链装置目录里查 `fund_ema_v2`:
  - **生产列的**: `pod_panel_ext.py`、`pod_panel_splice.py`、`r6_panel_splice.py`、`ax05_panel_splice_ivledger.py`(本轮)、`t5d_ivfix_panel.py`、`fx_fnd_hol_rebuild(_v2).py`(FX_DATA 面板重建, 复算这列)。
  - **读的(全部是研究装置)**: `retrain_2026-09/pod_femat_build.py` → `femat_A1_v2cal.npz`(PREREG_fundleg_engineering_2026-09-01 的 A1_v2cal 资金费腿臂, `jp_fundleg_*`); `uplift_2026-09-11/trackD_v4/drive_sleeves.py`; `uplift_2026-09-11/r2_horizon/devices/drive_ABCD.py`; `r10_screen/SLOW_CLOCK/devices/{reprice,offspec}.py`; `runpod_scripts/workspace_mirror/pod_extweek.py`; `T5d/devices/t5d_posthoc.py`; `eda/kcurve_2026-08-21/devices_2026-08-22/{f7_multiangle_prescreen,funding_factor_deepdive}.py`; 审计 `ad_panel_holes.py`、`fx_k3_nan_legitimacy.py`、`fx_hol01_provenance.py`、`tests_fnd_hol_checks.py`。
  - **king / DL 链不读 v2**: king 特征 `pod_fea_ext_clamp(_v2).py` 读 `f_fund_ema`(v0)+`f_fund_now`; DL 目标 `pod_dlw_targets_raw(_v2).py` 的 F6 用 `f_fund_ema`(v0); fea82 `pod_dlw_features_ext.py` 读 `f_fund_ema`+`f_fund_now`; fea89 `pod_f8_build_ext.py` 不读面板资金费; F10 训练 `pod_f10_train_ext.py`、`pod_f10_train_monthly_v4.py`、`pod_f10_refit_v4.py` 不读面板资金费列; 腿 / 出货 / 门 / 回放(`pod_legs_v4b.py`、`pod_export_bundle_v4.py`、`v4e_gate_export_v2.py`、`guard_*`、`port_w10/w10_universe.py`)读 `f_fund_ema_v1`; 生产者 `~/wide_shadow/*.py` 与执行器 `~/dl_quant_live/**/*.py` 里没有 `fund_ema_v2`。
  - 结论: 这个前视只影响上面列出的研究臂(以 A1_v2cal 为主), 不进在役书与 v4 链的 king/DL 特征。

### 11.7 变体文件清单(pod `/workspace/axis_0919/x0918r/`)

| 组件 | 路径 | sha256 | 状态 |
|---|---|---|---|
| 5m 缓存 | `data/dlnative_5m_wide829_f16_holefix2_x0918r.npz` | `08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75` | 完成 |
| 补洞表 | `inputs/holefix2r_cells_x0918r.npz` | `d524f819280384694cff6a36d684569d98ce18fa3ff04ceee562a54022afa612` | 完成 |
| RAW 补丁 / manifest | `data/raw_patch.npz` / `data/raw_patch.manifest.json` | `0a4cfb59…`(= x0918)/ `e5ac25fe…`(绑定新缓存 sha; 覆盖门 PASS 960 = 959 + 1) | 完成 |
| 可交易性 | `trd/tradability_v1.npz` | `bebf69ab…`(= x0918) | 完成 |
| 可交易掩码 | `masks/member_mask_tradable_W24H_cachegrid.npz` | `9793722e…`(= x0918) | 完成 |
| 可交易 ∧ 判活掩码 | `masks/member_mask_tradable_AND_live_W24H_cachegrid.npz` | `f752d8ae3bf92f001fcb5d6f83a7e4ae286d9f11f7548c2e965305615aa9ae51` | 完成 |
| 原始面板(证明用) | `panels/wide_panel_4h_rawbuild_x0918r.npz` | `fe4c77c1…`(= x0918) | 完成 |
| DL 目标 RAW | `dlw_v4raw/data/dlw_targets.npz` | `eda429829420e2529b1d7fa438e8044d8ea25ceeeef66448cea1f0854f1b96b5` | 完成, 10,320 锚 |
| DL 目标 CLIP | `dlw_hf3/data/dlw_targets.npz` | `309562c02a4f6a7ae18f1eb1da2f71125ae6e95189263d8bdcf1ba156e20770d` | 完成, 10,320 锚 |
| fea82(两处逐字节相同) | `dlw_hf3/data/dlw_fea82.npz` | `f6078393b6364684655798a82120bc1253a80a8076fa159f4485083684e7b9f7` | 完成, X (2,793,291, 82) |
| fea89 | `f8_v4/data/f8_fea89.npz` | `7b02c01ec731782c32aa704445624a463e750830743d0d8b94c93ed354235afa` | 完成, X (2,793,291, 89) |
| king 特征 + 元 | `data/wide_fea_v4.npy` / `_meta.npz` | — | **PENDING** |
| 记账元 | `meta/meta_newprod_v4_x0918r.npz` | — | **PENDING** |
| 面板 v2ext / v3splice、资金费账本 | x0918 原文件(`e5fcb419…` / `293a14cf…` / `74b69e63…`) | 同 x0918 | 复用(C5) |

### 11.8 x0918 未被改动

`devices/ax15_x0918_integrity.py` 对 `receipts/INVENTORY.json`(10:2xZ, 变体工作开始之前写)里的 22 个 x0918 文件重算 sha256: **22 / 22 相等**(`X0918_INTEGRITY_preking.json`, 11:4xZ)。r11 结束时再查一次(`X0918_INTEGRITY.json`)。

### 11.9 复跑命令

```
# 校验和(只取 .CHECKSUM, 与本地 zip 比)
AX_ROOT=/workspace/axis_0919 AX_TAG=check_d0830_shared AX_CHECK_ONLY_DAYS=2026-08-30 AX_CHECK_ONLY_DIR=/workspace/wide_multisrc/klines5m_daily AX_RPS=5 python devices/ax01_fetch_klines5m.py
AX_ROOT=/workspace/axis_0919 AX_TAG=check_d0831_r6 AX_CHECK_ONLY_DAYS=2026-08-31 AX_CHECK_ONLY_DIR=/workspace/uplift_2026-09-11/r6/dl/klines AX_RPS=5 python devices/ax01_fetch_klines5m.py
# 08-31 替换 + 补洞表
AX_CACHE=/workspace/axis_0919/data/dlnative_5m_wide829_f16_holefix2_x0918.npz AX_OUT_CACHE=/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz AX_HOLES=/workspace/axis_0919/inputs/holefix2_cells.npz AX_OUT_HOLES=/workspace/axis_0919/x0918r/inputs/holefix2r_cells_x0918r.npz AX_DAY=2026-08-31 AX_PREV_DAY=2026-08-30 AX_DAY_DIR=/workspace/uplift_2026-09-11/r6/dl/klines AX_PREV_DIR=/workspace/wide_multisrc/klines5m_daily AX_LO=490465 AX_HI=490752 AX_CHECKSUM_RECEIPTS=<两份校验收据> AX_RECEIPT=/workspace/axis_0919/x0918r/receipts/D31_REPLACE.json python devices/ax13_d31_replace.py
# 下游
STAGES=r2,r3,r4,r5 bash devices/ax_chain_r.sh ; STAGES=r6,r7,r8 bash devices/ax_chain_r.sh ; STAGES=r9,r10,r11 AX_R9_TRY0=<下一个未用的尝试号> bash devices/ax_chain_r.sh
# 证明
AX_X=/workspace/axis_0919 AX_R=/workspace/axis_0919/x0918r AX_LO=490465 AX_HI=490752 AX_RECEIPT=/workspace/axis_0919/x0918r/receipts/VARIANT_DIFF.json python devices/ax14_variant_diff.py
AX_INVENTORY=/workspace/axis_0919/receipts/INVENTORY.json AX_RECEIPT=/workspace/axis_0919/x0918r/receipts/X0918_INTEGRITY.json python devices/ax15_x0918_integrity.py
```
