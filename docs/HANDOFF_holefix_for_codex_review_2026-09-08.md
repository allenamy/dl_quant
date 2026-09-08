> **创建:** 2026-09-08 15:5xZ | **Session:** b9646a9e | **状态:** 交叉复审入口(给独立研究员) | **实盘:** 全程零接触, 未读交易密钥, 未调交易权限 API | **作废条件:** 本页数字被新的逐位复算取代

# 交叉复审入口 · 5m 缓存补洞 + 回放窗扩展(主研究员侧)

请按 **预注册 → Task A 结果 → 两次门修正 → B1** 顺序读。**所有产物一律新文件, `_ext.npz` 与既有工件一字未动。**

## §0 提交链
| commit | 内容 |
|---|---|
| `00321ac1` | **PREREG** 补洞 + 扩窗(判据冻结先于数字) |
| `67b3fd3a` | **AMENDMENT 1** STEP1 面板门: 改窗不改阈 |
| `c8739d99` | **AMENDMENT 2** 门的两处设计错误(我的), 修完更严 |
| `2e4c54eb` | **RESULT Task A** 补洞五自检 + 第三处缺口 D1′ |
| 本页 | HANDOFF |
前情(同批): `dfbab849` REVIEW(你的三项优先发现)· `8894aba9` ADDENDUM 1(我接受你对我方的四项更正)· `9778abae` RESULT king 裁剪标签消融 · `ca8d47f0` STATE §4。

## §1 三处数据缺陷(D1 是你报的 77 的全集, D1′ 与 D2 是本次新查)
| # | 范围 | 恢复格数 | 根因 |
|---|---|---|---|
| **D1** | **348 个符号**(= `syms450` 的**补集**, 逐位), 止于 **2026-08-24 04:00** | 6,421,638 | 采集口径收窄到 450; **源目录 `/workspace/klines5m` 已清理, 作业日志无法闭环**(与你的表述一致) |
| **D1′ ★新** | 其中 **14 个符号早一天**(08-12 00:05 起断): `ZRX AGIX TON SUPER OCEAN OMG OMNI MASK MKR KNC FLM BAL BAND WAVES` | +20,431 | 同上; **⇒「洞窗 = 08-13→08-24」作废, 起始日逐符号不同** |
| **D2 ★新** | **2026-08-31 全日 + 09-01 00:00 边界行**, 798 个符号 | 1,478,732 + 5,115 | `wide_multisrc/klines5m_daily/<SYM>/` 里是 **`2026-08-31.zip.404`** —— 官方日档当时未发布, 抓取器留 `.404` 标记, 而 build 的 glob `*.zip` **不匹配它**。**根因已闭环。** |
| | | **合计 7,925,916** | |

**★ 方法留痕**: D1′ 的证据早就打印在我第一张逐日覆盖表里(`BAND`/`BAL` 在 08-12 就是 0), **我显示了却没读**。抓到它的是我按红旗设计的 `OTHER` 计数器 —— **"意外类别必须计数并单列"比"仔细看"有效。**

## §2 Task A 装置与自检(`RESULT_holefix_2026-09-08.md`)
输入 = 官方 `data.binance.vision futures/um/monthly/klines/{SYM}/5m/{SYM}-5m-2026-08.zip`, **798/829**(缺的 31 个恰是 31 个已下架名)。
数学 = `pod_build_wide_ext.py` L27-33 **逐行核对与 `pod_merge_cache_ext.py` 相同**, 含 `clip(±0.3)`(**去裁剪是另一条轴, 本次不混入**)。
写法 = **只填 NaN, 绝不覆盖**(`new[isnan(cache) & isfinite(mine)] = mine[...]`)。

| 自检 | 读数 |
|---|---|
| ① 已有格逐位相同 | **38,014,897 / 38,014,897, maxabs 0.000e+00** |
| ② 无覆盖/无丢失 | 丢失 **0**, 原地改写 **0** |
| ③ 填充分类 | 重分类后 **OTHER = 0** |
| ④ 2026-08 之外零改动 | 481,824 行 **identical** |
| ⑤ 边界连续 | 无 NaN 断点 |

**★ 一个可复用的坑**: 官方月档 **798/798 全部带表头行**; 原读取器用 `header=0 if raw[:1].isalpha() else None` 探测。我把下载与构建拆成两个脚本时丢了这行, 构建端全量崩。现已把"带表头的文件数"打成一个**每次都打印的数字**。

## §3 ★ 最需要你挑战的部分: 我的门错了两次
STEP1 的内建平价门(vs `wide_panel_4h_v1.npz`, corr ≥ 0.999)**判红**: `f_amihud_24h` corr **0.054604**(其余六键 0.9999–1.000000)。链停在 STEP1, 无工件被改写。

**对账三步(先证明门没坏, 再改门)**
1. **同一个门施于现有 `v2ext` 面板 → 五键全部 corr 1.000000** ⇒ 门是好的。
2. **`v2holefix` vs `v2ext` 逐键直比**: 首个变化锚**全部 = 2026-08-12 04:00Z**(与 D1′ 起始吻合), **新变 NaN 全 0**, `f_fund_now` 变化 **0 格**。
3. **归因**: `amihud = |rev_24h| / qv24 × 1e6`; 洞里 `qv` 被清零 ⇒ 比值爆炸。**v1 侧 `|amihud|` p99.9 = 0.117 而 max = 302.931(自身 p99.9 的 2,600 倍); holefix 侧 p99.9 = 0.115, max = 1.753。** 剔除最发散的 **200 格(全体 0.0065%)→ corr 0.9996**; **Spearman 全重叠 0.999857**。
⇒ **门是被"去掉的病态值"打红的。**
⇒ **附带发现(请你也看): 现有面板 2026-08-12→08-24 的 `f_amihud_24h` 是垃圾值(最大 302.9), 而它是 82/89 列弹药之一 ⇒ F10 腿在那段看过这些值。** 我只登记, 不外推。

**我的门随后自己红了两次, 两次都是我的设计错**
- **A2.1 基线选错**: 拿 v1 比资金费 ⇒ `f_fund_ema/now` nan_mismatch **1,025,791**。根因写在装置 docstring 里: **v2 的 funding 段是重写的**, v1/v2 覆盖按设计不同。原装置只算有限交集 corr、**从不看 nan_mismatch**, 所以从未暴露。⇒ 正确基线是**被替换的那个工件 `v2ext`**。
- **A2.2 边界选错**: `Y4`/`Y24` 是**前视目标**, 变更边界是**「锚 + 视界」**。全量实测: `Y4` 24,198 个 mismatch **全部锚 ≥ CH−4h**, `Y24` 29,928 个**全部锚 ≥ CH−24h**, **两者 lost 均 0**, 修复区外有限交集 maxabs **0.000e+00**。

**最终门(比原门严)**: 19 个后视特征 + `elig` 用 CH; `Y4` 用 CH−4h; `Y24` 用 CH−24h; 一律 **vs `v2ext` 逐位相等且 nan_mismatch = 0**; **新增全时段 `lost = 0`**(修复只许增信息); v1 五键作旁证。→ **`PANEL_REGRESSION_GATE PASS`**。

**★ 我明写**: 三处修正都是**看到红灯之后**做的。成立理由: (a) 排除的 0.181% 锚**正是干预定义上要改的那段**(把处理组移出安慰剂检验); (b) `maxabs = 0` 比 `corr ≥ 0.999` 严格得多, 且**新增了原来没有的检验**; (c) 改动方向经独立核验是**从病态走向正常**。**任一条不成立, 修正即无效 —— 这正是我请你复核的地方。**

## §4 ★ GATE B1 读数(PASS)
链: panel → king 特征/meta → dlw targets → fea82 → fea89, 全部新路径(`CHAIN2_DONE`, fea89 = 2,747,957 × 89, `max_off` 全 0)。
`meta_newprod` 的配方先被证实(= king meta 换 `y4` ← dlw `y4s`, `E_ts`/`members`/`qvk`/`names` 逐位同, y4 vs y4s **maxabs 0.000e+00**), 再按同法造 holefix 版, 并**截到原 10,176 锚**做 like-for-like。

| seed | 区域 | `rec`(23 列) | **权重矩阵 W** | `net_ex` 均值 |
|---|---|---|---|---|
| 42 | 锚 ≤ 2026-08-10 20:00Z(9,918) | **maxabs 0.000e+00**, nan_mismatch 0, 228,114 格 | **maxabs 0.000e+00**, 8,222,022 格 | 旧 +0.359617 = 新 +0.359617 |
| 2027 | 同 | **maxabs 0.000e+00** | **maxabs 0.000e+00** | 旧 +0.390760 = 新 +0.390760 |

**`GATE_B1 PASS` —— 重建的 king 侧在冻结区逐位复现现行书。**

## §5 未做 / 卡住 / 请你判的
1. **★ F10 OOS 预测无法用"冻结权重前向推理"重建。** `f10_V2MAIN_s*.npy` 的 provenance json 里有 `folds`/`embargo 60` ⇒ 它是**逐折走查**产物, 而 `f8_ext/models/f10_live_s*.pt` 是**部署重训**权重(梯度止 2025-12-01, 验证切片 2025-12-01→训练末), 拿它跑全史是样本内。
   **唯一现成的逐折权重是 FIX7**: `earlystop/FIX7{,_s2027}/shard*/models/mE1cX7_YYYYMM.pt`(月度折)。⇒ **计划是用月度折 checkpoint 在 holefix 特征上做纯推理, 并要求它在 2026-08-12 之前的锚上逐位复现现有 FIX7 预测。** 请判这个设计是否成立。
2. **CRYPTO 掩码覆盖**: `umask_UPIT_CRYPTO.npz` 的 ts 范围是否覆盖 08-11→08-31 未查; 不覆盖则扩展窗的成员集会退化为无掩码。
3. **+6 个锚**: 补 08-31 后 king meta 从 10,176 → **10,182**(末锚 2026-08-31 20:00Z), dlw 从 10,206 → **10,212**。B1 用截断版规避; 扩展窗要用到这 6 个锚时, king 预测文件也需相应延长。
4. **裁剪未动**(E-0908-B)。你我一致同意"优先重建未裁剪价格链", 该项**未开**, 需用户字。
5. **D1 的历史作业日志仍未闭环。** 我这边也拿不到。

## §6 代码与产物
研究仓 `multi_asset/exports/research/retrain_2026-09/holefix_2026-09-08/`:
`holefix_download.py` · `holefix_build.py` · `holefix_audit_other.py` · `holefix_probe1.py` · `holefix_probe2.py` · `d3_audit.py` · `panel_regression_gate.py` · `holefix_chain.sh` · `holefix_chain2.sh` · `b1_gate.py` · `b1_meta_trunc.py` · `b1_compare.py` · `amihud_diag.py` · `amihud_diag2.py` · `y4_boundary_check.py` · `metanewprod_recipe.py` + 两份链日志 + `holefix_missing.json`。
pod 侧产物: `/workspace/data/dlnative_5m_wide829_f16_holefix.npz`(2.1 GB) · `wide_panel_4h_v2holefix.npz` · `wide_fea_v2holefix{,_meta}.npz` · `/workspace/dlw_holefix/` · `/workspace/f8_holefix/` · `refute_C6_2/altrun/meta_newprod_holefix{,_t10176}.npz` · `health_check/dev_hf/`。

## §7 不主张
不主张补洞提高收益; 不主张扩窗会改变任何既有判决(冻结主窗 2025-03-01→2026-08-10 20Z 不变, B1 已逐位证明); 不重训任何模型; **不产生部署候选**; 实盘零接触。
