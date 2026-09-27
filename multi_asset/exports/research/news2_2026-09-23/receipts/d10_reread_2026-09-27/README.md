> **创建:** 2026-09-27 11:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 描述性重读的逐步收据(计划 docs/PLAN_d10_reread_past_cut_2026-09-27.md);冻结判词 UNDECIDED(6838a219a)不改 | **作废条件:** 计划被改写

# D10 描述性重读:收据(逐步追加)

## R1 九月 API 毫秒源
- COMPLETE:829 个名,92,040 行,153 个名为空,失败 0。输出 sha 08fdd1c2178881a4423b3803d08f30363011339cba7df9f981726971e42e6f33。
- 空名普查(`r1/EMPTY_SYMBOLS_VS_UNIVERSE.json`):与切点之后 108 个锚上的书成员(469 个名)交集为 0;与十月 legs 切点之后 KZ 有限的名交集也为 0 ⇒ 不影响重读。

## R2 账本延长(d10_build_ledger_ms rev 2.2 → 2.3)
- **第一轮**(`r2_first/`,11:30:05Z):NOT_RECONCILED,原因只是计数缺陷:fold_removed 把窗口之后的 87,962 行算成了折叠删掉的行。
  - 数据本身没问题:五列逐位相同,PREFIX_BITWISE,升级 0,overlap 0。
  - 修复为 rev 2.3(bd6d2bdd7),属于**读数后修订(解释性)**。
- **rev 2.3 重跑**(`r2b/`):
  - **V1**:npz 数组与 e179071d 逐位 IDENTICAL。收据比较的字面判词如下(lead 原文):
    「V1 比较器字面判词为 DIFFERS:新增单向键 positive_control_reconciliation.rows_in_old_window。lead 解读:行为不变。依据是 npz 数组逐位相同、139 个旧键全同;唯一的差异是 rev 2.3 修复本身新增的诊断计数,值自洽(2,633,090 + 18 = 2,633,108)。预声明写 IDENTICAL 是预声明时的疏漏,具名记录。」
  - **R2**:RECONCILED;fold_removed 18,等于派生集合 18;ALL_BITWISE;不允许的差异 0;api_overlap_unequal 0;PREFIX_BITWISE,升级 0;切点之后 87,962 行;最后一行 09-27T07:00Z。账本 sha 76b777bf07d5b3630e9d4818b562cd798f1ca495af8af190c8f24421c9b538db,与第一轮相同。
  - **same_second_extra 变异**:RECONCILED,fold_removed 19 等于派生集合 19,与预声明一致。前缀判 DIFFERS 是这个变异按构造必然出现的。

## R3 第一阶段重建
- 产物 rebuilt_features_d10ext.npz,sha b8659396102eef2f53c6fb7c44be8162eb2a1f4f2f648beb5015a224d7e05134。
- 控制:平价门 `--anchor-max-utc 2026-09-01T02:00Z` 对照 2be2d7c8,**PARITY_GREEN**:2,742,554 个成员格上 fund_now、fund_ema、iv 差异 0。
- 全轴(只作描述):切点之后 42,000 格由 NaN 变为有值;两端都有值但不同的格,fund_now 469 格、fund_ema 1,113 格。

## R4 fund_state(d10 模式)
- 产物 fund_state_d10ext.npz,sha 49ce0faca521906baa3057d3901742689c7d1a95a87c3661155c7ef6a8a7268d。
- 控制:前缀恒等对照 f07e4ebd,**PASS**:切点之前 ft、rate、iv、ema、prev 差异 0,kidx 差异 0;切点之后新增 75,065 个事件。
- 恒等装置第一次运行过慢(npz 每次访问都重读),在产出任何读数之前已停,改为一次加载(d5c1fa2d1);合成用例结果不变。

## R5 pass1
- 24/24 片,0 片失败,12:24:03Z 完成。merge1:锚 10,333,带 King 特征的锚 10,293,配对 2,785,890,与线 D 相同。
- 实际执行的代码是 NC 复制件 nc_p2_build.py,未改动。

## R6 装配
- 产物 NEWS_FEATURES_D10EXT.npz,sha ad80d50d1f8b953a317845a88ff2ae7399ad8cfdd967a49f492cb8094a6314c1。
- G1 差异 0;G2 只动了资金费相关列;切点之前交叉核对 0。
- 控制:平价门对照 f1cd3fa2(切点之前),**PARITY_GREEN**,2,742,554 格差异 0。
- 键、锚(10,333)、symbols(829)、m、off、count 都与 f1cd3fa2 相同;X78 全部有限。
- 描述:切点之后,fn_v 与在役 NC 的 NEWS_FEATURES 差异 0。

## R6b King 重新预测(fresh2)
- 用冻结的 release m0 booster,不重训。
- 恒等控制 C0:在 f1cd3fa2 上重预测,逐字节复现 274ba08a,PASS。
- 新 OOF sha 6579bc4e390493a31873d790bdbc366c48bfddc9c06b79c24eef73bc8b911e18;对比 release m0,切点之前差异 0,切点之后差异 38,853 格(fresh2 的收据在 43e43f31b)。

## R7 legs
- 驱动 d10_stage2_legs_oct.sh rev 1。输入:King OOF 6579bc4e;特征 ad80d50d;NC_W r5_R2ext。
- 产物 legs.npz,sha 37c0b5d373af18e24fa0ad0961ad60a4ecec8fda07c2e6fe1c09368c1ab536c3。
- ready 9,247,not_ready 1,086(原来是 9,142 与 1,191)。「fund_base<10」这一类不再出现:切点之后的锚现在有资金费基底了。
- 控制:前缀恒等对照 383e3ddc,**PASS**:切点之前 10,225 行、每个键差异 0。切点之后 108 行(只作描述):KZ 42,991 格、RN8 42,469 格、QV 42,000 格不同,LR 与 WL 也有变化。
- **实际执行的代码**:nc_legs.py sha 18387627…,nc_hist_features.py sha 3eee6e88…,都来自 pod2 上 /dev/shm/news2_2026-09-23/devices。它们的仓库副本先在 mretrain_2026-09-26/devices/(fresh2 9043ea94e);按 lead 裁定,之后会以带 sha 的文件名放进 nc_2026-09-23/devices/。

## R8 交付检查
- d10_legs_delivery_check rev 1,**L1–L4 全 PASS**,检查所用期望值为特征 ad80d50d、fund_state 49ce0fac、King OOF 6579bc4e。
