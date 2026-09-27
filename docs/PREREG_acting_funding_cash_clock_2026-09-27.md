> **创建:** 2026-09-27 16:19:00 UTC | **Session:** acting_lead/funding_mechanism_0927 | **状态:** draft | **作废条件:** 读数后改变事件/阈值/归属；源码SHA变；真实输入无法定位时不得升级为现金平价通过

# 最小现金事件钟控制与有条件两臂冒烟

本轮总wall截至16:30:04Z（资源授权后16:15:04Z开始），不搜索规格、不抢KSR/D10。当前只有合成控制可以独立执行：v3固定seed02路径窗在仓，但其manifest镜像不在原路径；pod2 R mirror只有executor代码/filters，非v3 live轨迹。真实路径cash平价门因此暂UNAVAILABLE。

第一包原样AST提取 exec_sim.py SHA29679672e68d4842a62616e40c5fc57143f724b9ebfa6bbde927670624247c24的on_funding/push/step_until以及PRI。控制夹具只提供固定q、P、已知fill，不实现模型/撮合。A取整5m；held=100单位，P初始10；A+1ms rate+.0001；A+24m+10s已知fill增加100*x；A+60m rate−.0002、P12，同刻另一个fill减少50单位（funding优先）；B+1ms rate+.0003、P11。先把实际事件逐个送入canonical on_funding：旧秒接口按int键加载，但每事件执行时取当时q，现金分别−.10、+.48、−.495（x=1）。独立解析cash与x线性导数，负控①把第一事件归new，负控②把同刻fill排fund前，两者必须红；x±1e−4有限差分导数须误差<1e−9。F=0、费率反号独立对照。额外合成同一秒两笔不同rate，演示旧接口若未适配不能直接接ms；只标本轮接入风险，不据此认定现有seconds合同错。

控制通过只叫IMPLEMENTATION_CONTROL_PASS，真实路径尚缺时不得发训练。恢复固定v3镜像或从已认证同版本run导出trade_log/fund_log/初始state后，只加只读导出、不重写模拟器：逐事件q、price、rate独立重建cash；已有结果必须同源闭合，然后对old-held/new-target线性carry通路测量。允许明示因果可达代理，不要求整个非线性撮合梯度与引擎逐位一致；最终整书仍canonical。

条件训练（须上述实际cash门通过再冻结输入SHA和具体臂文件）：2臂、同s42初始化、同202608 fold、同batch/tau、各1epoch，A0无carry/A1仅加事件时持有carry。若price时钟修改则A0/A1共同改并保留NC原参照，不称对在役单变量。NC输入只能IMPLEMENTATION_SMOKE；候选有效性须正确D10共同特征/事件账/合法成员/raw价标签重训，两臂之外无系数扫描。CPU1，RSS≤6GiB，GPU≤8GiB；启动cgroup余量≥14GiB且GPU空闲、同UID RSS+6GiB≤30GiB；输出先实际quota probe；不复制全量features，不改D10冻结213件。预计两臂45–60GPU秒，含控制、加载、检查总wall≤8分钟；若余下时限不足或任一资源门失败就排队。只可停止本任务自己的PGID并留日志。
