> **创建:** 2026-09-27 17:19 UTC | **Session:** acting_lead/research_resume_0927 | **状态:** final（有界静态审阅，未执行首span） | **作废条件:** PLAN或下列源码/收据SHA改变；D10共同输入/adapter未与首span绑定时不能沿用为执行验收

# 资金费同钟代理：独立静态复核

审阅范围是首120锚实现的实质前置，不是收益判定。读取源码和既有收据；与 funding_mechanism_0927 直接核对，其已在 `0507907f1`、`82f3f0971` 修正文档。本轮未执行本地/远程执行器、训练、GPU作业、等待器或交易所调用，未读取KSR未终态候选。

结论：已发现的合同缺项均已在当前PLAN明确；可以按此合同编写首span实现，不能跳过实际接口、绑定和现金控制就进入训练。没有依据把旧HistFunding源码的缺陷直接归为当前D10实际运行错误。

| 首span前必须固定的项 | 具体问题与修订核验 |
|---|---|
| ms事件压缩 | 原“fund事件之间无fill”不充分：同秒 .100 fill、.900 唯一fund，floor到整秒会换持仓。PLAN:28已要求从秒桶首到最后ms事件全区间q恒定、同price与窗口归属，覆盖fill/flatten；否则保留ms+逐事件rate接口。canonical `on_funding` 使用 `(sym,int(t))`，旧RateMap整秒dict会覆盖重复symbol，实际D10适配须独立确认。 |
| A+24m与成交价格 | CfgMap31使用A+1440，tau有小数。canonical `schedule`保存decision ref，`book`价格为ref*(1+side*slip)，不是未来fill-time价格。PLAN:21保留两个负signed slip；PLAN:23固定B=A_last+14400，max offset2638.259s小于4h，不延长末端等carry。 |
| producer与库存 | 部分成交只能改变q；producer h仍按原EMA推进，不能再乘r1+r2。PLAN:17明确双状态与24burn后不断开。 |
| 单位/重复成本 | PLAN:17/21选固定V0，GM仅进入目标q一次，price/fee/carry均按1e4/V0归一；移除旧3.52罚项避免叠收fee/slip。fixed NAV与canonical动态equity sizing差异明示为代理假设，不能宣称逐位复现。 |
| V0缩放假PASS | 代理V0=1若也作为canonical初始NAV，会受lot/min-notional抑制而零成交。PLAN:17保留真实config NAV0后再归一，:27要求非零实际fill及fill后非零rate结算，否则UNAVAILABLE且不另挑窗。`bt_driver_lib.py:157,190–194`证实config NAV0确传给HistSim31。NAV0=100000由funding代理只读Pod config确认，本审阅未独立再读该Pod文件。 |
| D10共同基线 | PLAN:12/13/34承认ad80d50d特征、76b777bf事件账仍需当前共同主线接受，并绑定完整adapter/成员/King/fund输出。NC参照config或17555e56 adapter收据不能替代新的D10候选身份。扩展universe应3ee838cf，不能沿旧6322b573。 |

尚未验收、会阻止从首span检查继续到训练的事项：

1. 实際D10共同run config、adapter、members/UNAVAILABLE、King/资金费席位/特征/ledger的SHA与首span统一绑定；当前PLAN只列定位和冻结步骤，无新完整收据。
2. 实际ms消费者的逐事件现金与window归属对账；若不能安全合并必须用专属rate接口，不能把旧整秒int字典直接当ms兼容。
3. 第一合法120span的非零fill与可达结算、raw价可观测、最大消费时刻/训练cutoff，以及F=0恒等/反号/new回溯红控/fill前零/fill后有限差分。现有六窗fixed-tape现金重构只覆盖导出tape，不能替代新代理。

没有新增窗口或阈值；固定十atom、忽略保护反馈、固定V0、历史统一成本校准均为已明示近似，最终仍需canonical全书。第一span若无可达结算是UNAVAILABLE，不是机制无效。

# 实际源码与收据SHA

本地worktree `/Users/haosiyu/.codex/worktrees/acting-lead-20260927/quant_research`，审阅时HEAD `a2ba120589ef4b57449f4507febcd07bcda9ec7c`。

- PLAN: `docs/PLAN_acting_funding_fold_clock_2026-09-27.md` SHA `04a4c43496527a3d42c1e58440e869c92237736347d7595b5c9f7d715a8965b4`
- canonical: `multi_asset/exports/research/replay_exec_2026-09-19/exec_sim.py` SHA `29679672e68d4842a62616e40c5fc57143f724b9ebfa6bbde927670624247c24`
- HistSim31: `multi_asset/exports/research/baseline_tables_2026-09-19/devices/bt_hist_sim31.py` SHA `8ae6e2a441d700824372784b1bc0bd9e0ee2f686a3c22f522b6bb962911022a1`
- driver: `multi_asset/exports/research/baseline_tables_2026-09-19/devices/bt_driver_lib.py` SHA `ba3bc2610b12a3f0280ff8f03c039ff5c2e81b8c05789183fd2b1acab661bddb`
- calibration: `multi_asset/exports/research/replay_exec_2026-09-19/CALIBRATION_v3_POOLED_20260826_20260910.json` SHA `fda342431d39703e8a2cc49d566f0cdd89155248c1f7bd46a6e46b3ffbc937e6`
- NEWS2_adapter_receipt: `multi_asset/exports/research/news2_2026-09-23/receipts/engine/NEWS2_ADAPTER_TEST_s42.json` SHA `80c07141df538b73d36f5e4c633b7d990ad60742bb9aed2de856597eab79627a`
- fixed_cash_receipt: `multi_asset/exports/research/acting_lead_2026-09-27/receipts/ROOT_fixed_cash_tape_20260927.json` SHA `2348175c0d4845d177c48590a2647c50ba3a8b069186f3dbdf4d05914b817959`

关键源码定位：exec_sim.py 的事件优先级72、book371、schedule403、funding421、equity sizing528；bt_hist_sim31.py 的FullPanel119、RateMap157、HistFunding170、CfgMap31 181、历史USDT费用225；driver157/190–194。既有ROOT固定tape收据为PASS_RECONSTRUCTION_FROM_EXPORTED_TAPE，不等于新同钟网络或OOS有效。
