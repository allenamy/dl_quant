> **创建:** 2026-09-27 17:41 UTC | **Session:** acting_lead/research_resume_0927 | **状态:** final（身份/输入门交付；首120未运行） | **作废条件:** 绑定输入/代码SHA、D10共同合同或新consumer设计改变；不作为候选或现金PASS

# D10 首120锚的真实共同输入与现金入口

对应 `docs/PLAN_acting_funding_fold_clock_2026-09-27.md`，文件范围已与funding_mechanism_0927确认。本件仅身份和输入门，不修改原D10 213 pins、KSR装置/数据、NC配置或ACTING主台账。没有训练、执行器模拟、GPU或第三等待器。

最早的身份分叉在实际D10RR配置 `pins.ledger_full`：**特征使用76b777bf毫秒账；现金执行仍使用073088e5秒账。** rerun6是16行重建干跑，其目录无RUN_CONFIG，不能验收新的ms现金消费者。既有D10RR配置也不能直接作为新首120配置：其TARGETS NPZ已在留存流程后缺失，只剩身份收据，必须UNAVAILABLE，不能借另一份替代。

## 已实际读取/哈希的入口

- config: `/workspace/dlarch_2026-09-24/chain/d10rr_s42/configs/RUN_CONFIG_DLARCH_D10RR_s42.json` SHA `7f71cfa4fccb53996183cb572eff577f96065992fbe577151bff2e0347c3b5c4`。
- launch receipt: `/workspace/dlarch_2026-09-24/chain/d10rr_s42/receipts/BT_LAUNCH_full_DLARCH_D10RR_s42.json` SHA `1e22d40152bc2bbd336f48a40a5a64bb3227078f2f4c804df8dd0ca8b5686fba`；只提取device/config/pin checks与输入身份，未读取runs业绩/env。
- adapter spec: `/workspace/dlarch_2026-09-24/chain/d10rr_s42/configs/ADAPTER_SPEC_DLARCH_D10RR_s42.json` SHA `e89c7ceca31ce9c470ebf14e3816d67bb52aa7116e92176c95720de33199149a`。
- target receipt: `/workspace/dlarch_2026-09-24/chain/d10rr_s42/targets/TARGETS_DLARCH_D10RR_s42.json` SHA `5096601e6dd14a8cd2ad8403cd4c86ee20df7b708d173f5de504e057836c9c02`。对应npz **当前缺失**，不能沿用。

实际文件均匹配：D10EXT features `ad80d50d`、legs `37c0b5d3`、King OOF `6579bc4e`、fund_state `49ce0fac`、F10 OOF `081bd6e6`；F10收据明确RESCORE_FROZEN_MODELS，不称重新训练。新ms账 `76b777bf`、raw价格 `23af32bd`、meta `d1e49cc9`、扩展universe `3ee838cf`、book member mask `f752d8ae`、P1 members `2323623f`、tradability `bebf69ab`、pooled calibration `fda34243`均当前实hash通过。完整路径/全SHA见IDENTITY_MANIFEST。

可复用的是这些已绑定输入、NAV0=100000/GM=2、A+24m、当前USDT费用、原UNKNOWN集与规则。旧RUN_CONFIG的new_lineage/data/object等部分描述仍继承NC文案；应以真正sources/receipt和代码加载路径判断，不按文字标签认定身份。

## 两条资金费通路，含精确源码

特征通路：`76b777bf ft_ms` → `d10_rebuild_funding_features.py a1015980` 的LedgerMs（:150–185）/重建（:303–335），实际阈值为 **ft_ms≤A*1000+999**，再调用producer原EMA/interval秒算术。`d10_build_fund_state.py e90addf6`（:45–77、:99–111）保持各事件行，输出秒ft与kidx side=right；调用 `funding_interval.py 5d5bf207` 与 `nc_contract.py 316a0b9b`，两者Pod当前SHA与R4收据一致。经R5/R6装配得到ad80特征，R7用49ce状态生成RN8/资金费腿。**fund_state不是现金账。** A整锚秒截至+999ms的可知信息在A+1440决策前已知，不能错判为决策泄漏；现金经济时刻仍保留原ms。

现金通路：

1. 部署 `bt_launch.py 393a8dc8` :45读上述config，:71验pin，:73导入模块，:84调用load_context；:98 run_one没有fund override。
2. `bt_driver_lib.py ba3bc261` :64–72导入既有ES/BH；:117 **BH.HistFunding(CFG[pins][ledger_full][path],...)**；:240–243 run_one→make_sim；:193默认fund or c.fund。
3. `bt_hist_sim31.py 8ae6e2a4` :170–178读取 **ft** int64，区间(t_lo,t_hi]；:155–167 RateMap以int秒为key，每symbol一rate；:450–451按F.times推funding事件。
4. `exec_sim.py 29679672` :421–434原on_funding按(s,int(t))取rate、floor5m价格，现金−qPr；同刻funding优先级2，fill3，窗口9。BH未覆盖on_funding。此链没有把76b7自动接到cash。

以上源码当前均独立hash。实跑launch收据绑定config及旧ledger pin。已删除的逐PATH文件未重建，因此不额外宣称已逐路径重验历史加载模块。

## 覆盖期与精度分开

旧073088账：2020-01-01T00Z→2026-09-19T00Z，2693666行，ft秒。新76b777账：2020-01-01T00Z→2026-09-27T07Z，2721070行，ft_ms。仅对两个时间列读取min/max，没有重复大文件hash。

行数差含延长覆盖期，**不能据此推断丢事件、损坏或现金偏差**。未做共同时间段的(symbol,exact time,rate)集合对照、同秒归并对账或真实q路径现金差；cashbug verdict是NOT_ESTABLISHED。确认的是新旧接口/字段/时钟不同，新ms数据尚未进入该现金链。

## 独立输入检查器，先防错接

`../../devices/d10_first_span_identity.py` sourceSHA `0d2556e1e322611c221673952ec25175f41256f6bfd1a025a5d36ea10496abee`。
`check_and_load(contract, identity_path, identity_sha)`供未来独立adapter直接调用，**必须使用返回事件，不能再开另一未绑定账本**。

门要求：120连续4h整数锚；终端恰(last+14400)*1000；现金(start,end]；feature known offset999ms与decision offset1440000ms；fund-before-fill；资金费ft_ms/<i8/ms/economic_settlement且不折秒；声明path/SHA、实际resolved路径、同文件句柄SHA与读取schema一致；每symbol时间严格递增，允许同秒不同ms和同ms不同symbol，不合并；费率有限；consumer源码与新独立targets真实存在并匹配SHA。字段错、秒冒充ms、终点错、文件改变、旧/缺目标均UNAVAILABLE。

返回仅 `INPUT_CONTRACT_PASS_CASH_UNVALIDATED`、execution_ready=false。消费者是否真正调用原现金路径、target完整组合来源、第一合法admission、价/UNKNOWN/cutoff、非零fill及可达结算仍须首span收据；输入门不替代这些验证。当前尚无新consumer/config/targets，因此没有对真实首span执行此门。

合同schema是 `d10-first-120-contract/1`；完整最小字段用专属测试setUp作可执行示例，其目标/consumer是合成输入。真实新合同必须由funding代理按实际新文件生成，禁止复制示例的虚拟文件。输入manifest SHA `9a7de4e6cb0a02b9b8fff94c232635bce6aec8ba15ba06cb2baca3522c920b78`。

本地仅小输入控制：
```sh
python3 -B multi_asset/exports/research/acting_lead_2026-09-27/devices/test_d10_first_span_identity.py
```
10/10通过；含缺装置红、ft字段/float时间、ms错标秒、终点+1ms、错path/内容、missing/borrowed target、精确ms重复、NaN rate、consumer/manifest变化，以及同秒多个ms保留、同ms多symbol保留、t0排除/B包含/B+1ms排除。无执行器导入或模拟。原红/绿日志及sha在VERIFICATION.json。

新合同/consumer就绪后，仅人工输入预检（本次未执行/未部署；不要起等待器）：
```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python3 -B d10_first_span_identity.py \
  --contract <new-first120-contract.json> --identity IDENTITY_MANIFEST.json \
  --identity-sha 9a7de4e6cb0a02b9b8fff94c232635bce6aec8ba15ba06cb2baca3522c920b78 --out <new-input-receipt.json>
```
预检只加载57MB ms账，不加载3GB特征/价格，不生成targets；建议CPU1、RSS≤512MiB、wall≤60s，由调用者资源门限制。已做身份collector约13.32s/RSS18MiB/nice19，只流式SHA与NPZ头；没有重复运行。

## ms消费者的最小独立接法与未跑控制

可在新HistSim31子类的on_funding(t)先激活**精确ms事件**的rate视图，再调用原super.on_funding(t)；原int(t)查询仅在该激活事件内查rate，不能跨事件缓存last-write。F.times用可回转到原int64 ms的时刻；FundAudit保留float t，无需改原资金费符号/现金代码。只是一项待实现设计，不是已验证设备。

具体必测：同秒.100 fill与.900 fund；同symbol同秒两fund夹fill；同ms多symbol；同刻fund先于fill；锚整点与+1ms各自窗口；span B与B+1ms；旧held→partial→new-held；零费严格恒等与非零fill后可达结算。先在固定q/price已知答案上验精确金额，再首120；不为无可达结算另挑有利span。此时才有依据报告某实现的实际时钟/金额bug。
