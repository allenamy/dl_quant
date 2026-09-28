> **创建:** 2026-09-28 21:16 UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** final | **作废条件:** 引用源码、固定20锚来源或诊断假设改变

# 20锚执行证据与条件化计划目标

承接 [独立LR连续目标](RESULT_independent_LR_recurrence_2026-09-28.md)：前件从一次起点自行递推LR/席位/H，并重放实际09-26安装事件，目标20/20在固定容差内。本件把该20锚对应的**原生产文件**连到执行日志，未再训练、未产出新收益/夏普、未部署。

## 接受的事实

- 09-24 08至09-28 00固定20个发布锚，消费文件的**原字节SHA**20/20相同；每锚唯一anchor/RID/phase_A，计划prev_w、target_w与决策价全部有限，定仓权益/规模在册。
- 10,885订单日志行、4,306请求条目（4,306个不同的锚×client_id），请求数量与身份均有记录，承载请求的行side全部可用；不能把日志行数当成交笔数。
- 6,579行request_ledger明确为null，这不自动表示漏单；2锚opening_halted，计算出计划也不等于执行。10,885行均未保存reduce_only；6,133条持仓回读属于post_anchor，不能冒充决策前数量。
- 8,833个独立重算/身份检查通过，篡改消费SHA和重写目标后同步更新普通文件SHA两个反例仍被原始目标档案拒绝。输入装置13格、映射装置11格；只有这两个研究装置，不是生产全电池。
- 历史版本用发布原件绑定：5d3029c 8锚、96acfdd 3锚、d01e35d 9锚，三套源码/合同归档，23件SHA复核。不是用当前代码覆盖历史，也不是逐锚运行时的代码签名证明。09-26 W3有pair-check命令错误，后续W6独立给出refs/代码清洁/漂移通过；不能把W3整份称全绿。

## 实测发现：phase_A清单是显示摘要

三个执行器源码中phase_A的untradable_names每类最多12名，untradable_held最多6名。最初据摘要重算11/20相同，九差锚最大29.1440017115USDT；缺的STAR/TIA/SOLV恰在完整popped名单的尾部。补齐此前遗漏的venue tradable及external元数据并未改变11/20，说明那项修补不能解释本批差异。

随后**事后登记了诊断补充**，从同锚reshape.popped_names取完整撤名集，逐个验证n_popped、前12项与其它分类计数，超过仍可观测的完整性边界就拒算。没有变更人口或1e-6USDT容差。

结果：20/20条件化计划目标相同，最大差9.09494701773e-13USDT；原11/20结果保留。固定09-28 00锚一名目标增加100USDT，20/20→19/20，最大差104.1026USDT。该反例证明比较器能抓到目标值差，不证明约束生成、逐请求及现金全链正确。

**承重限制**：补充诊断使用实盘已记录的撤名结果；它没有独立证明“该不该撤名”。当前场所filters被显式用作历史假设；缺少计划行的撤名对象按0作为条件化输入并逐锚点名；使用订单prev_w重建决策名义，而非独立账户快照；STOP集延续最近phase_C并列出原时刻。没有逐请求reduce_only证据，没有完整执行前数量，因此不能升级成完整历史执行平价、现金闭合或候选可发布。新候选必须自行推进持仓、止损、限制，不能借用这里的实盘决策结果。

## 20Z运行核验

21:00Z静默窗、确认20:53:12Z rc0后只读核验。运行树d01e35d、代码无修改、配置与HEAD一致；King700d9e7b/F10 3d7d050f与钉/目标相同；322名生产重放逐位PARITY、消费文件SHA相符、未停开仓/未再跳闸，毛持仓/目标毛额99.21542700%（非逐名到位率）。M3仍shadow，未见对冲订单标记。

看门狗cond2_day_loss、cond4_drawdown保持既有partial，未新增trigger/error/blind/degraded。因此判词仍LOCAL_FINISHED_WITH_EXISTING_PARTIAL，不称风险监控全绿。没有重复K1交易所查询、没有自动resume、Telegram、配置/模型/杠杆改变。下一00Z须01Z静默窗且done后再核。

## 可复跑与归档

- 计划链2d9a644ce → 实现6408b95f3/ac21b15c4/4e315636f；条件化计划09a9d48ca/3c7315d10 → 源0d099be76 → 输入修补1aca97319 → 事后补充6f7a55dc1 → 全清单源8e3d6a1a9。
- 装置目录：multi_asset/exports/research/acting_lead_2026-09-27/devices/；收据目录：multi_asset/exports/research/acting_lead_2026-09-27/receipts/EXECUTION_INPUTS_20260928。
- RESULT SHA013971851550b68371f196ba5f2b604f3b0b66c9a4b4e2b1c8fa01d09779d8dc；来源绑定369ac538a83cb16143637d8a100fb916348db1eb205f14644c0068fe5a010aec；完整映射源码5470a486bf9ce03d3e3bcf9f1a839aabd3fc39de37cb2ab100dfe71ac03ed3d2。
- 完整76件包：/Users/haosiyu/.codex/tmp/pod_archive_20260928/execution_input_census.zip，1806343字节，SHAab7be1f97eca6989b63a61c65c05554a95c77edb93c232ac22d21cd23b2965fb，全部成员SHA复核，源未删。原生产目标字节仍在父PRODUCTION_INPUTS.zip，父SHA在RESULT source_files里；本包TARGET_JSON为格式化副本，不能拿其文件SHA冒充原字节。
- 本地复核：`/usr/bin/python3 -B devices/verify_execution_census.py <capture>`；运行根已含输出则独立复制到新根并移走该副本内VERIFY.json后执行（不覆写原件）。映射用`/opt/homebrew/opt/python@3.14/bin/python3.14`、numpy2.4.4，`conditional_execution_book.py <capture> --full-recorded-restrictions`，输出同样要求不存在；加`--mutate`运行负控。capture路径和全部输入SHA见ARCHIVE.json。本次不使用GPU/Pod、不需要API。

## 本次自身错误与边界

临时20Z脚本首次把VERDICT猜成小写verdict，造成自己的假红，原件留存，按真实schema修后所有核验项为真。普查首次未接显式null，第二次误用读回文件没有的RID连接；先保留失败，再加反例按精确execution anchor_ts修正。独立复算首次比较格式化副本与原文件SHA被拒，后改为从父档案读取原字节并另核语义。来源绑定首版误要求每张辅助票据都含commit、并误写legs路径，失败目录保留；最终按整组发布证据绑定并由git ls-tree确认signal/legs.py。手填计划时间错误已在出数前更正；不把上述工具失败当生产故障。

下一承重工作：把条件化已对齐的目标路径接真实成交/费用/资金费，按订单身份分离09-27双机平仓、停机和人工恢复；先复用已有现金闭合装置与档案，补未闭合输入，避免重复取数/全史训练。严格执行回放仍需历史限制与决策前仓位证据；没有这些不能凭本件宣布新夏普或换装。
