> **创建:** 2026-09-27 16:41:33 UTC | **Session:** acting_lead/funding_mechanism_0927 | **状态:** draft | **作废条件:** 固定source/calibration/manifest不符；现金或window与认证基准不闭合；不能把同路径局部导数升级为模型收益

# 持久镜像恢复后的真实固定路径现金控制（见新读数前）

前轮遗漏MIRROR_DURABLE_COPIES_2026-09-19.json持久副本收据；现已定位本地 `/Users/haosiyu/quant_mirrors/replay_exec_mirror_59875e5a` 与pod2同名根。不是从实时状态重新拼旧镜像。先按INPUT_MANIFEST sha59875e5a69db415f5ce20b35b888f2d49a31427fdde8b7b847a9645ee135a5ae定点核505个257MB输入，再核executor树固定代码，非全盘哈希。

原exec_sim v3.1 SHA29679672e68d4842a62616e40c5fc57143f724b9ebfa6bbde927670624247c24、calibration fda342431d39703e8a2cc49d566f0cdd89155248c1f7bd46a6e46b3ffbc937e6、seed02、live模式、CAL起点1787702400，只跑认证seed02前六个4h窗（初始readback 08-26 00:40:08至08-27 00:41:20）。参数/价格panel/真实cfg决策钟/各fill offset/秒级FundingBook来源原样，不接D10毫秒，不重训，不改撮合。windows所有数值需对同seed认证prefix误差≤1e−8美元、sealed初始state SHA相同。保留全部trade_log/fund_log/初始state的小型导出。

独立现金控制：从初始q出发只累计原引擎实际trade_log的dq。每个fund事件前仅计严格早于该事件的fill（同刻fund优先）；独立计算q(t−)*panel.px(floor5m(t))*FundingBook.rate，而不是采用fund_log自报q或现金。数量误差≤1e−8、现金逐笔≤1e−8USD、逐窗≤1e−8USD。未知price/rate禁止置0，发生即不可闭合。将同刻优先级和不可达A+ms归属的合成控制作为已冻结前置，不重设门。

固定路径线性通路：对每笔实际fill，后续fund现金关于该笔dq的导数为−Σ_{t_fund>t_fill} P(t_fund)*rate；t_fund≤t_fill导数0。从按时间排列的第一笔具有后续结算的fill取epsilon=1e−4数量单位，独立重算现金有限差分误差≤1e−8。价格通路同钟为该fill后持有至窗尾的[P_end−P_fill]，只说明固定后续成交下的局部数量扰动，不含策略重规划/止损反馈；不据此宣布可训练模型收益。cash目标与price通路必须使用同一实际fill钟。

CPU1，预算≤2GiB、5分钟，输出预计<5MB；直接本地持久镜像只读计算，零远端写、零GPU，用户已取消先前GPU额度续期。若原认证prefix不能复现，先报机械差异，不扩大到全史或新候选。
