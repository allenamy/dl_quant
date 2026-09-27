> **创建:** 2026-09-27 17:49 UTC | **Session:** acting_lead/funding_mechanism_0927 | **状态:** in-progress | **作废条件:** 共同输入/consumer/checker SHA或冻结首窗发生变化；无新GPU授权，六窗旧预算永不重开

# D10共同输入首120锚现金接口

本件落实已审阅`PLAN_acting_funding_fold_clock_2026-09-27.md`，接在原六窗实现尝试封账之后；不是其重试。先证明新毫秒消费者，再恢复原202608训练admission时间上第一条合法120锚，首窗必须非零fill及可达非零结算。若该首窗不在完整书King/F10/fund共同覆盖内，则明确UNAVAILABLE，不在看到成交或现金后换窗，不用未来训练模型补造早期OOF。

## 已冻结接口与控制

身份manifest `9a7de4e6cb0a02b9b8fff94c232635bce6aec8ba15ba06cb2baca3522c920b78`；修后checker `5f1ba04e22ac45ae4b7c632a9df1ae11f8f55b164c59ba33e7bc0fc62800c104`（844de1505）。只消费check_and_load返回的精确ft_ms/symbol/rate。新`funding_exact_ms_consumer.py`对每精确时刻激活一次rate视图后调用原canonical SHA29679672的on_funding；不改价格、费用、数量、优先级。原int(t)查询只在激活事件内解释，非事件/错秒查询拒绝，同symbol同ms重复拒绝，同ms多symbol一次调度。

小型固定数量测试先因装置未实现而9项失败，后9项通过；这证明消费者最小现金路径，不等于首120已跑。覆盖.100 fill/.900单fund、同秒双fund夹fill、同ms多symbol、fund先同刻fill、(start,end]和B+1ms、F=0/反号、fill前导数0及后可达有限差分、baseline q=0后新数量仍需收费、inactive视图拒绝。测试采用原on_funding源码AST和独立手算金额，不复制其现金公式作为实际消费者。完整HistSim31的事件队列及真实目标仍需首span现金收据。

## 首窗恢复和完整书目标

先用原NC202608 admission的现存输入、原span_admissible条件和原48锚步长恢复全部accepted/rejected计数，必须等于原149/6，然后取第一条accepted的120锚。标签只取isfinite掩码；不统计其收益、优化目标或候选分数。此步骤仅恢复已冻结坐标，不以旧labels替代后续raw价同钟账。

完整书原状态起点为2023-01-01零状态，之后continuous_combo.evolve连续递推。检查固定首窗与D10共同OOF/合法成员/legs覆盖；早于起点或输入缺失即UNAVAILABLE，不能在首窗无声明重置producer状态。若覆盖，按原news2_combo/continuous_combo/combo_target源码和必要前缀重建新独立targets；原TARGETS NPZ已缺失，旧收据不作可读目标替身。新config只引用新targets与显式ms consumer，沿NAV100000、GM2、A+24m、原费用/UNKNOWN/执行规则，原213 pins不改。

首span终端固定B=lastA+14400，现金(start,B]、fund先同刻fill；初始canonical库存为0，保留非线性原引擎。逐笔从原initial q与实际fill独立重建q(t−)，以原price panel和ms ledger核每次cash，并核窗口price−fee+fund=equity差。每笔所用经济时间/实际float事件时刻/int64ms及数量、价格、费率均导出。此处未证明外部venue成交真值。

CPU小窗上限1线程/2GiB/5分钟，启动cgroup余量至少10GiB（2+8）且同UID RSS+2GiB≤30GiB；不启动GPU，不清共享cache，不改共享cgroup。元数据恢复阶段采用2GiB地址空间上限且不mmap整价格/特征；后续raw价格只在已授权范围按行块读取。输出预计KB/MB，不超过64MiB；实际输出小probe后写，仅本任务新根。新GPU/两臂训练不在本件授权内。

## 支持域机械修订（原失败已封存，尚未见新窗现金/成交）

原门实测为UNAVAILABLE_BEFORE_FULL_BOOK_STATE_ORIGIN：完全复现149 accepted/6 rejected，第一窗A=2022-07-01T00Z、B=2022-07-21T00Z，King在16,680个成员格全部有预测，F10为0格。F10首非空与完整producer状态起点均2023-01-01。原收据c2bb21fd1保持不变；这不是现金或信号负面证据。

主审在见这些坐标之前已授权支持域修订。现在固定：仍只在原149个accepted窗中，按时间取第一个A≥2023-01-01、全部120锚被当前D10共同轴覆盖、当前D10合法producer成员上King与F10预测均有限、D10 legs ready全真的窗口。只读有限性/成员/轴，不读回报、现金、是否成交或是否触及资金费；不以publish、gross、成交或收益来排序。不存在就UNAVAILABLE，不放宽。新旧成员如有差异逐格报告，原admission不冒称D10新raw价准入；新窗仍需后续同钟raw价/UNKNOWN门。

完整书state仍从2023-01-01连续递推到该窗，绝不在新窗重置producer。若存在已认证、SHA一致且来源就是这组共同D10输入的连续combo数组，可从中提取独立目标并保留其状态来源；否则用原生成器及必要前缀重建。canonical执行库存仍按该小窗已冻结的cash初始化，不声称这是原全史账户库存。先固定窗口后再看publish/fill/结算，若无非零fill或可达费则本窗UNAVAILABLE，不再搜索下一窗。

18:01Z读数前实施固定：机械修订选择rows2190–2309，A=1672531200（2023-01-01T00Z）、B=1674259200（01-21T00Z），拒绝前23窗仅因早于状态起点；当前成员17,520格、与原成员一致，producer prefix=0。现有scaled/literal数组均缺失，采用首120完整evolve重建，未读任何新窗收益/成交。构建器SHA `118a12b187a715994c5e2dcc7951e49108d7d52bc07e086802d5fd9837af9053`。主书沿原scaled reading，literal只作适配接口对照；固定执行路径seed=0，模型来源s42。原ovn_adapter build/write/verify_roundtrip逐位核新targets，禁止选不同路径或publication策略求非零现金。构建与cash tap合计CPU预算5分钟，RSS≤2GiB；原GPU禁启继续。
