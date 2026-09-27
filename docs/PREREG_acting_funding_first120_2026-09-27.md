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
