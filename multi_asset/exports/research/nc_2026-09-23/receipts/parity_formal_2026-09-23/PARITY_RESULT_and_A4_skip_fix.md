> **创建:** 2026-09-23 23:0xZ | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(集成代理 C-4) | **状态:** 平价门收据(判词 + 修复 + 变异对照) | **作废条件:** treeNC5 PATCH_RECEIPT(3135cf8b…)、平价包 290ebcc9、平价门装置 deefe360 任一改动。冻结修订 2 = lead 778ba7324;错误台账 E-0923-I

# 平价门:treeNC4 判 FAIL_PARITY → A4 资金费跳过规则修复 → treeNC5 判 PASS

前置附注 `PRE_VERDICT_NOTE_unresolved_cells.md`(44d9f3c7d)写于读任何结果之前,内容是:3 个未决界值格都在轴末 E 之后,不在这 6 个锚的窗内。

## 1. 三次运行(同一平价包 290ebcc9、同一 6 个锚、exinfo = w24h)

| 运行 | 树 | 判词行原文(开头) | 1789704000 · ONEUSDT | 其余 5 个锚 |
|---|---|---|---|---|
| 首跑 22:40:37–22:45:06Z | treeNC4(46c52d94) | `NC_PARITY_GATE FAIL_PARITY` | fe_v、fn_v、iv_v、base_val 各 1 格;X78、X82 各 2 格(资金费列) | 11 个量全部 0 格 |
| **基线** 22:48:45–22:54:41Z | **treeNC5(a68c7a5f)** | **`NC_PARITY_GATE PASS`**,baseline_green True | **0 格** | 11 个量全部 0 格 |
| **变异臂** 22:54–22:59:43Z | treeNC4 = treeNC5 撤掉这一处改动 | `NC_PARITY_GATE FAIL_PARITY` | 与首跑逐格相同:fn_v 服务端 −0.02 对参照 −0.00052714;iv 8 对 1;fe_v −0.0022160 对 −0.0025649 | 11 个量全部 0 格 |

- 变异守卫的顺序:先断言基线为绿(treeNC5 上该格 0),再跑变异(treeNC4 上该格变红)。两次测量值见上表。首跑与变异臂在同一格上逐位相同,说明结果是确定性的。
- 负控(只在基线 treeNC5 绿时计数):
  - NC_F:0GUSDT 的 rate 加 1 ulp,fn_v 出现 1 格不同,测出;
  - NC_R:0GUSDT 的 ch0 加一个 f16 步长,X78 5 格、rev24 1 格、X82 7 格不同,测出。
- 覆盖:6 个锚在两种树上都 returned、combo rc 0;w24h 列 649 名,覆盖率 1.0,没有锚被跳过;每个量都有实测,n > 0,`_no_measurement` 为空。

## 2. 根因与修复(lead 批准)

- 根因:生产者资金费循环里有一行跳过规则 `if anchor - last_ts < exp_iv * 3600 * 0.9: continue`,生产在役 60800739 版第 455–456 行就有,NC 版原样继承。它用**上一次**的周期去预测下一次结算。
- 触发实例:ONEUSDT 在 09-18 00Z 以 8h 周期结算,费率 −0.02,触到下限;交易所随后改为 1h 周期,01Z、02Z、03Z、04Z 各结算一次。服务端在 04Z 按「距上次 8h 结算才 4h」把它跳过,训练则吃进了这四次。
- 修复:派生器新增编辑 `A4:funding_no_expected_interval_skip_under_bulk`,只改 shadow_loop 第 633 行:`if not _bulk_ok and anchor - last_ts < exp_iv * 3600 * 0.9:`。treeNC5 与 treeNC4 的 diff 只有这一行,其余输出 sha 全部不变。

## 3. lead 要求照写的五点

1. **请求数不增加。**
   - IV_GRID 最大为 8h,所以原先被跳过的名 last_ts 都在 anchor − 7.2h 以内。BULK_HOURS = 26,这些名全部落进本地批量过滤那一支,不发逐名请求。
   - 实测同一锚上两棵树的计数:6 个锚都是 fund_bulk_ok True、fund_bulk_pages 1、`_fund_per_symbol` treeNC5 = 129 = treeNC4,**断言 treeNC5 ≤ treeNC4 在全部 6 个锚上成立**。
   - 129 这个数是 w24h 代理在研究行上的伪迹:这 129 个名在研究数据里有有限的(冻结的)bar,但最近 26h 没有结算,例如 AGIXUSDT、AI16ZUSDT、1000XUSDT。实盘 exchangeInfo 不会列这些名;F-1 实盘测得 520 个名的逐名查询为 0。
2. **批量不完整时的保护**:10 页全满时走 for-else,_ok 置为 False,回退到逐名查询。这条保持不变。回退时仍会跳过的部分记为**具名残余**:「批量失败,且该锚恰有名字缩短了结算周期,则这些名滞后一个旧周期」。按冻结修订 1 §2-4 的格式,写进首锚验收与月度报告,逐事件计数。
3. **变异守卫**:见 §1。基线格 0 → 变异格红。两个实测值都已列出。
4. **训练侧不动,NC_FEATURES 3c886a2b 仍然有效**,证据如下:
   - 重放装置只编译 King 块。`nc_hist_features.py` 第 53–56 行按两个字面标记定位这一段:`diag.phase("feature_inference")` 到 `X = FE_ANCH[:, keep]`。
   - 在 treeNC5 里,这两个标记在第 658 行和第 746 行;被修改的跳过行在**第 633 行**,落在 King 块之前,不在重放编译的范围内。
   - treeNC5 的 King 块(L658–L746)与 pod2 重放树 treeNC(L538–L626)**逐字节相同**,span sha 都是 5d75872411b19096。
   - 训练的资金费输入直接取研究员账本(fund_state.npz),从不经过生产者的资金费循环。
5. 时间:基线 6 分钟,变异臂 5 分钟。E3 与 F-2 在 treeNC5 上依次整轮重跑,判词只认 treeNC5。任何一步越过 23:40Z 窗口,就从 01:00Z 起整轮重跑,不拼接。

## 4. 与 3 个未决界值格的关系

没有重合。差异只出在一个名的资金费入账,与收益通道无关;那 3 格都在 E 之后(见前置附注)。
